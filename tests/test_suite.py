import concurrent.futures
import hashlib
import json
import os
import time
import uuid
import pytest
from sqlalchemy import select, update, func
from sqlalchemy.engine import make_url
from suite import create_app
from suite import models as m
from suite.chat import Retriever

PASSWORD = 'Demo-Only-Passphrase-123!'

@pytest.fixture
def app(tmp_path):
    test_url = os.getenv('TEST_DATABASE_URL')
    if test_url:
        url = make_url(test_url)
        if os.getenv('ALLOW_TEST_DATABASE_RESET') != '1' or url.database != 'cloudlab_test':
            raise RuntimeError('External tests reset tables. Use only disposable cloudlab_test with ALLOW_TEST_DATABASE_RESET=1.')
        disposable = m.make_engine(test_url)
        m.metadata.drop_all(disposable)
        disposable.dispose()
    app = create_app({'TESTING': True, 'ENCRYPTION_SECRET': 'test-only-' + 'x' * 48,
                      'DATABASE_URL': test_url or 'sqlite:///' + str(tmp_path / 'test.db'), 'AUTO_INIT': True})
    yield app
    app.extensions['engine'].dispose()

@pytest.fixture
def client(app):
    return app.test_client()

def account(client, email='one@example.test', scopes=None):
    assert client.post('/api/register', json={'email': email, 'password': PASSWORD}).status_code == 201
    data = {'email': email, 'password': PASSWORD}
    if scopes is not None: data['scopes'] = scopes
    response = client.post('/api/login', json=data)
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json['token']}

def record(**kw):
    return {'external_id': 'customer-01', 'name': 'Alex Morgan', 'email': 'alex@example.test', **kw}

def book(client, headers, route=1, key=None, extra=None):
    return client.post('/api/passes', headers={**headers, 'Idempotency-Key': key or str(uuid.uuid4())},
                       json={'route_id': route, **(extra or {})})

def test_frontend_and_health(client):
    assert client.get('/').status_code == 200
    assert client.get('/health').json == {'status': 'ok'}
    assert b'Bus passes' in client.get('/').data
    assert client.get('/static/app.js').status_code == 200
    assert "frame-ancestors 'none'" in client.get('/').headers['Content-Security-Policy']

def test_registration_validation_and_password_hash(client, app):
    assert client.post('/api/register', json={'email': 'bad', 'password': 'short'}).status_code == 400
    account(client)
    with app.extensions['engine'].connect() as c:
        row = c.execute(select(m.users)).mappings().first()
        assert row['password_hash'].startswith('scrypt:')
        assert PASSWORD not in row['password_hash']

def test_no_default_admin_or_scope_escalation(client):
    h = account(client)
    assert client.get('/api/audit', headers=h).status_code == 403
    assert client.post('/api/login', json={'email': 'one@example.test', 'password': PASSWORD, 'scopes': ['audit:read']}).status_code == 403

def test_token_is_hashed_and_logout_revokes(client, app):
    h = account(client)
    with app.extensions['engine'].connect() as c:
        t = c.execute(select(m.tokens)).mappings().first()
        assert t['token_hash'] == hashlib.sha256(h['Authorization'][7:].encode()).hexdigest()
        assert t['token_hash'] != h['Authorization'][7:]
    assert client.post('/api/logout', headers=h).status_code == 200
    assert client.get('/api/records', headers=h).status_code == 401

def test_scope_and_expiry(client, app):
    h = account(client, scopes=['records:read'])
    assert client.get('/api/records', headers=h).status_code == 200
    assert client.post('/api/records', json=record(), headers=h).status_code == 403
    with app.extensions['engine'].begin() as c:
        c.execute(update(m.tokens).values(expires_at=1))
    assert client.get('/api/records', headers=h).status_code == 401

def test_login_throttle(client):
    account(client)
    for _ in range(5):
        assert client.post('/api/login', json={'email':'one@example.test','password':'wrong-password'}).status_code == 401
    assert client.post('/api/login', json={'email':'one@example.test','password':PASSWORD}).status_code == 429

def test_unique_and_normalized_duplicate(client):
    h = account(client)
    assert client.post('/api/records', json=record(), headers=h).json['classification'] == 'unique'
    d = client.post('/api/records', json=record(name='  ALEX   MORGAN ', email='ALEX@EXAMPLE.TEST'), headers=h)
    assert d.status_code == 200 and d.json['classification'] == 'redundant'
    assert len(client.get('/api/records', headers=h).json['records']) == 1

def test_identity_conflict(client):
    h = account(client)
    client.post('/api/records', json=record(), headers=h)
    d = client.post('/api/records', json=record(email='other@example.test'), headers=h)
    assert d.status_code == 409 and d.json['classification'] == 'identity_conflict'

def test_same_name_review_and_false_positive_resolution(client):
    h = account(client)
    client.post('/api/records', json=record(), headers=h)
    distinct = record(external_id='customer-02', email='another@example.test')
    r = client.post('/api/records', json=distinct, headers=h)
    assert r.status_code == 409 and r.json['classification'] == 'possible_false_positive'
    r = client.post('/api/records', json={**distinct, 'confirm_distinct':True}, headers=h)
    assert r.status_code == 201 and r.json['classification'] == 'false_positive_resolved'
    assert len(client.get('/api/records', headers=h).json['records']) == 2

def test_invalid_record_and_confirmation(client):
    h = account(client)
    assert client.post('/api/records', json=record(email='invalid'), headers=h).status_code == 400
    assert client.post('/api/records', json=record(confirm_distinct='false'), headers=h).status_code == 400

def test_record_isolation(client):
    a = account(client)
    client.post('/api/records', json=record(), headers=a)
    b = account(client, 'two@example.test')
    assert client.get('/api/records', headers=b).json['records'] == []
    assert client.post('/api/records', json=record(), headers=b).status_code == 201

def test_vault_encryption_random_nonce_and_ownership(client, app):
    a = account(client)
    for label in ['A','B']:
        assert client.post('/api/vault', json={'label':label, 'secret':'sensitive-demo-value'}, headers=a).status_code == 201
    with app.extensions['engine'].connect() as c:
        rows = list(c.execute(select(m.vault)).mappings())
        assert rows[0]['encrypted_data'] != rows[1]['encrypted_data']
        assert all('sensitive-demo-value' not in r['encrypted_data'] for r in rows)
    assert client.get('/api/vault', headers=a).json['entries'][0]['secret'] == 'sensitive-demo-value'
    b = account(client, 'two@example.test')
    assert client.get('/api/vault', headers=b).json['entries'] == []

@pytest.mark.parametrize('attack', ["' OR 1=1 --", "' UNION SELECT password_hash FROM users --", "'; DROP TABLE users; --"])
def test_sql_injection_cannot_leak_or_change_tables(client, app, attack):
    a = account(client)
    client.post('/api/vault', json={'label':'private', 'secret':'demo-only-secret'}, headers=a)
    res = client.get('/api/vault', query_string={'q':attack}, headers=a)
    assert res.status_code == 200 and res.json['entries'] == []
    assert client.get('/api/vault', headers=a).json['entries'][0]['secret'] == 'demo-only-secret'
    with app.extensions['engine'].connect() as c:
        assert c.scalar(select(func.count()).select_from(m.users)) == 1
        assert c.scalar(select(func.count()).select_from(m.audit).where(m.audit.c.event == 'suspicious_input')) >= 1

def test_search_wildcards_are_literal(client):
    h = account(client)
    client.post('/api/vault', json={'label':'private', 'secret':'demo'}, headers=h)
    assert client.get('/api/vault?q=%25', headers=h).json['entries'] == []

def test_booking_uses_server_price(client):
    h = account(client)
    assert book(client,h,extra={'fare_cents':1}).status_code == 400
    r = book(client,h)
    assert r.status_code == 201 and r.json['booking']['fare_cents'] == 450

def test_idempotency_and_conflicting_key(client):
    h = account(client)
    key = 'same-request-001'
    first, second = book(client,h,key=key), book(client,h,key=key)
    assert first.json['booking']['id'] == second.json['booking']['id']
    assert second.json['replayed'] is True
    assert book(client,h,route=2,key=key).status_code == 409
    assert client.get('/api/routes').json['routes'][0]['remaining'] == 29

def test_booking_validation(client):
    h = account(client)
    assert client.post('/api/passes', headers=h, json={'route_id':1}).status_code == 400
    assert book(client,h,route=True).status_code == 400
    assert book(client,h,route=999).status_code == 404

def test_pass_recovery_ownership_and_cancel_once(client):
    a = account(client)
    bid = book(client,a).json['booking']['id']
    b = account(client,'two@example.test')
    assert client.get('/api/passes',headers=b).json['bookings'] == []
    assert client.post(f'/api/passes/{bid}/cancel',headers=b).status_code == 404
    assert client.get('/api/passes',headers=a).json['bookings'][0]['id'] == bid
    for _ in range(2):
        assert client.post(f'/api/passes/{bid}/cancel',headers=a).status_code == 200
    assert client.get('/api/routes').json['routes'][0]['remaining'] == 30

def test_pass_signature_tamper_wrong_owner_and_revocation(client):
    a = account(client)
    p = book(client,a).json['booking']
    assert client.post('/api/passes/verify',headers=a,json={'code':p['verification_code']}).json['valid']
    assert client.post('/api/passes/verify',headers=a,json={'code':'x'+p['verification_code']}).status_code == 400
    b = account(client,'two@example.test')
    assert client.post('/api/passes/verify',headers=b,json={'code':p['verification_code']}).status_code == 403
    client.post(f"/api/passes/{p['id']}/cancel",headers=a)
    assert client.post('/api/passes/verify',headers=a,json={'code':p['verification_code']}).status_code == 409

def test_sold_out_and_parallel_booking(app,client):
    h=account(client)
    with app.extensions['engine'].begin() as c:
        c.execute(update(m.routes).where(m.routes.c.id==1).values(capacity=3,remaining=3))
    def one(_):
        with app.test_client() as local:
            return book(local,h).status_code
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(one,range(12)))
    assert results.count(201)==3
    assert results.count(409)==9
    assert client.get('/api/routes').json['routes'][0]['remaining']==0

def test_parallel_duplicate_insert(app,client):
    h=account(client)
    def one(_):
        with app.test_client() as local:
            return local.post('/api/records',headers=h,json=record()).status_code
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(one,range(8)))
    assert results.count(201)==1
    assert results.count(200)==7
    assert len(client.get('/api/records',headers=h).json['records'])==1

def test_parallel_idempotent_booking(app,client):
    h=account(client)
    def one(_):
        with app.test_client() as local:
            return book(local,h,key='parallel-same-001')
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(one,range(8)))
    assert sum(r.status_code==201 for r in results)==1
    assert len({r.json['booking']['id'] for r in results})==1
    assert client.get('/api/routes').json['routes'][0]['remaining']==29

def test_past_departure(client,app):
    h=account(client)
    with app.extensions['engine'].begin() as c:
        c.execute(update(m.routes).where(m.routes.c.id==1).values(departure='2020-01-01T09:00:00Z'))
    assert book(client,h).status_code==409

def test_chat_matched_and_abstains(client):
    r=client.post('/api/chat',json={'question':'How do I recover a lost bus ticket?'})
    assert r.status_code==200 and r.json['intent']=='recover'
    r=client.post('/api/chat',json={'question':'Explain intergalactic banana propulsion'})
    assert r.json['matched'] is False and r.json['source'] is None

def test_invalid_json_and_limits(client):
    assert client.post('/api/chat',json=[]).status_code==400
    assert client.post('/api/chat',json={'question':'x'*501}).status_code==400
    assert client.post('/api/chat',data='x'*17000,content_type='application/json').status_code==413

def test_no_login_and_unknown_input(client):
    assert client.get('/api/records').status_code==401
    assert client.post('/api/register',json={'email':'x@example.test','password':PASSWORD,'role':'admin'}).status_code==400


def test_sqlalchemy_url_object_supported():
    from sqlalchemy.engine import URL
    engine = m.make_engine(URL.create('sqlite', database=':memory:'))
    with engine.connect() as conn:
        from sqlalchemy import text
        assert conn.scalar(text('SELECT 1')) == 1
    engine.dispose()


def test_same_content_cannot_bypass_dedup_with_new_id(client):
    h = account(client)
    assert client.post('/api/records', json=record(), headers=h).status_code == 201
    r = client.post('/api/records', json=record(external_id='new-id', confirm_distinct=True), headers=h)
    assert r.json['classification'] == 'redundant'
    assert len(client.get('/api/records', headers=h).json['records']) == 1


def test_last_seat_parallel_idempotent_booking(app, client):
    h = account(client)
    with app.extensions['engine'].begin() as c:
        c.execute(update(m.routes).where(m.routes.c.id == 1).values(capacity=1, remaining=1))
    def one(_):
        with app.test_client() as local:
            return book(local, h, key='last-seat-same-001')
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(one, range(8)))
    assert sum(r.status_code == 201 for r in results) == 1
    assert all(r.status_code in (200, 201) for r in results)
    assert len({r.json['booking']['id'] for r in results}) == 1
    assert client.get('/api/routes').json['routes'][0]['remaining'] == 0
