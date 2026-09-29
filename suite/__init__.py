import base64
import functools
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv
from flask import Flask, g, jsonify, render_template, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select, update, delete, func, and_, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from . import models as m
from .chat import Retriever

USER_SCOPES = {'records:read', 'records:write', 'vault:read', 'vault:write', 'passes:read', 'passes:write'}
SUSPICIOUS = re.compile(r'(?:union\s+select|\bor\s+[\'\"]?1[\'\"]?\s*=\s*[\'\"]?1|;\s*(?:drop|delete|update)\b|--|/\*)', re.I)

def db_url():
    if os.getenv('DATABASE_URL'):
        return os.environ['DATABASE_URL']
    if os.getenv('DB_HOST'):
        return URL.create('postgresql+psycopg', username=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'], host=os.environ['DB_HOST'],
            database=os.environ.get('DB_NAME', 'cloudlab'), query={'sslmode': 'verify-full', 'sslrootcert': os.environ['DB_SSLROOTCERT']})
    Path('instance').mkdir(exist_ok=True)
    return 'sqlite:///instance/cloudlab.db'

class APIError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status

def create_app(config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=16 * 1024, TESTING=False)
    if config:
        app.config.update(config)
    secret = app.config.get('ENCRYPTION_SECRET') or os.getenv('ENCRYPTION_SECRET')
    if not secret or len(secret) < 32:
        raise RuntimeError('Set ENCRYPTION_SECRET with setup_local.py before starting.')
    cipher = AESGCM(hashlib.sha256(secret.encode()).digest())
    signer = URLSafeTimedSerializer(hashlib.sha256(('passes:' + secret).encode()).hexdigest(), salt='bus-pass-v1')
    engine = m.make_engine(app.config.get('DATABASE_URL') or db_url())
    app.extensions['engine'] = engine
    retriever = Retriever()
    if app.config.get('AUTO_INIT', os.getenv('AUTO_INIT', 'true').lower() == 'true'):
        m.metadata.create_all(engine)
        m.seed(engine)
    if os.getenv('TRUST_PROXY') == 'true':
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    dummy_hash = generate_password_hash(secrets.token_urlsafe(24))

    def encrypt(value, owner):
        nonce = os.urandom(12)
        payload = json.dumps(value, ensure_ascii=False).encode()
        return base64.b64encode(nonce + cipher.encrypt(nonce, payload, str(owner).encode())).decode()

    def decrypt(value, owner):
        raw = base64.b64decode(value)
        return json.loads(cipher.decrypt(raw[:12], raw[12:], str(owner).encode()))

    def audit(conn, event, detail='', user=None):
        conn.execute(m.audit.insert().values(timestamp=int(time.time()), user_id=user,
            event=event, detail=detail[:160]))

    def payload(allowed, required=()):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise APIError('Send a JSON object.')
        if set(data) - set(allowed):
            raise APIError('Unexpected fields: ' + ', '.join(sorted(set(data) - set(allowed))))
        if any(k not in data for k in required):
            raise APIError('Missing required fields.')
        return data

    def string(data, name, limit=160):
        v = data.get(name)
        if not isinstance(v, str) or not v.strip() or len(v) > limit:
            raise APIError(f'{name} must contain 1–{limit} characters.')
        return unicodedata.normalize('NFKC', v.strip())

    def email(value):
        value = value.casefold()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise APIError('Enter a valid-format email address.')
        return value

    def required(scope):
        def decorate(fn):
            @functools.wraps(fn)
            def wrapped(*args, **kwargs):
                header = request.headers.get('Authorization', '')
                if not header.startswith('Bearer ') or len(header) > 512:
                    raise APIError('Sign in to access this feature.', 401)
                digest = hashlib.sha256(header[7:].encode()).hexdigest()
                with engine.connect() as conn:
                    token = conn.execute(select(m.tokens).where(m.tokens.c.token_hash == digest,
                        m.tokens.c.expires_at > int(time.time()))).mappings().first()
                if not token:
                    raise APIError('Token expired or revoked. Sign in again.', 401)
                if scope and scope not in token['scopes'].split(','):
                    raise APIError('This capability token does not permit that action.', 403)
                g.user_id, g.token_hash = token['user_id'], digest
                return fn(*args, **kwargs)
            return wrapped
        return decorate

    @app.errorhandler(APIError)
    def api_error(e):
        return jsonify(error=e.message), e.status

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error='Request exceeds 16 KB.'), 413

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        if os.getenv('TRUST_PROXY') == 'true':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.before_request
    def injection_indicator():
        if request.path.startswith('/api/'):
            sample = request.get_data(cache=True, as_text=True)[:16384] + request.query_string.decode(errors='replace')
            if SUSPICIOUS.search(sample):
                with engine.begin() as conn:
                    audit(conn, 'suspicious_input', request.path)

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/health')
    def health():
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        return jsonify(status='ok')

    @app.post('/api/register')
    def register():
        data = payload({'email', 'password'}, {'email', 'password'})
        address = email(string(data, 'email', 254))
        password = data.get('password')
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            raise APIError('Use a password of 12–128 characters.')
        try:
            with engine.begin() as conn:
                conn.execute(m.users.insert().values(email=address, password_hash=generate_password_hash(password), role='user'))
                audit(conn, 'registration', 'demo account created')
        except IntegrityError:
            raise APIError('Account cannot be created; use another demo email or sign in.', 409)
        return jsonify(message='Demo account created. Sign in to continue.'), 201

    @app.post('/api/login')
    def login():
        data = payload({'email', 'password', 'scopes'}, {'email', 'password'})
        address = email(string(data, 'email', 254))
        password = data.get('password')
        if not isinstance(password, str) or len(password) > 128:
            raise APIError('Invalid credentials.', 401)
        now = int(time.time())
        subject = hashlib.sha256(address.encode()).hexdigest()
        with engine.connect() as conn:
            failures = conn.scalar(select(func.count()).select_from(m.login_failures).where(
                m.login_failures.c.subject_hash == subject, m.login_failures.c.timestamp > now - 300))
            user = conn.execute(select(m.users).where(m.users.c.email == address)).mappings().first()
        if failures >= 5:
            raise APIError('Too many failed attempts for this account. Wait five minutes.', 429)
        valid_password = check_password_hash(user['password_hash'] if user else dummy_hash, password)
        if not user or not valid_password:
            with engine.begin() as conn:
                conn.execute(m.login_failures.insert().values(subject_hash=subject, timestamp=now))
                audit(conn, 'login_failed', 'credentials rejected')
            raise APIError('Invalid credentials.', 401)
        allowed = USER_SCOPES | ({'audit:read'} if user['role'] == 'admin' else set())
        requested = data.get('scopes', sorted(allowed))
        if not isinstance(requested, list) or any(not isinstance(s, str) for s in requested) or not set(requested) <= allowed:
            raise APIError('Requested scopes are not permitted.', 403)
        token = secrets.token_urlsafe(32)
        with engine.begin() as conn:
            conn.execute(m.tokens.insert().values(user_id=user['id'], token_hash=hashlib.sha256(token.encode()).hexdigest(),
                scopes=','.join(sorted(set(requested))), expires_at=now + 3600))
            conn.execute(delete(m.login_failures).where(m.login_failures.c.subject_hash == subject))
            audit(conn, 'login_success', 'one-hour capability issued', user['id'])
        return jsonify(token=token, expires_in=3600, scopes=sorted(set(requested)), email=address)

    @app.post('/api/logout')
    @required(None)
    def logout():
        with engine.begin() as conn:
            conn.execute(delete(m.tokens).where(m.tokens.c.token_hash == g.token_hash))
        return jsonify(message='Token revoked.')

    @app.get('/api/records')
    @required('records:read')
    def list_records():
        with engine.connect() as conn:
            rows = conn.execute(select(m.records).where(m.records.c.user_id == g.user_id).order_by(m.records.c.id.desc()).limit(100)).mappings()
            return jsonify(records=[dict(id=r['id'], **decrypt(r['encrypted_data'], g.user_id)) for r in rows])

    @app.post('/api/records')
    @required('records:write')
    def add_record():
        data = payload({'external_id', 'name', 'email', 'confirm_distinct'}, {'external_id', 'name', 'email'})
        record = {'external_id': string(data, 'external_id', 80).casefold(),
                  'name': ' '.join(string(data, 'name', 160).split()),
                  'email': email(string(data, 'email', 254))}
        if not re.fullmatch(r'[a-z0-9_-]+', record['external_id']):
            raise APIError('external_id may contain letters, numbers, underscores and hyphens.')
        confirmed = data.get('confirm_distinct', False)
        if not isinstance(confirmed, bool):
            raise APIError('confirm_distinct must be true or false.')
        canonical = {**record, 'name': record['name'].casefold()}
        content = {'name': canonical['name'], 'email': canonical['email']}
        fingerprint = hmac.new(hashlib.sha256(('dedup:' + secret).encode()).digest(),
            json.dumps(content, sort_keys=True).encode(), hashlib.sha256).hexdigest()
        condition = and_(m.records.c.user_id == g.user_id, m.records.c.external_id == record['external_id'])
        same_content = and_(m.records.c.user_id == g.user_id, m.records.c.fingerprint == fingerprint)
        def existing_result(row):
            if row['fingerprint'] == fingerprint:
                return jsonify(classification='redundant', message='Identical record already exists; nothing inserted.', id=row['id']), 200
            return jsonify(classification='identity_conflict', error='This source ID already has different data; review it.'), 409
        try:
            with engine.begin() as conn:
                existing = conn.execute(select(m.records).where(condition)).mappings().first()
                if existing:
                    return existing_result(existing)
                duplicate = conn.execute(select(m.records).where(same_content)).mappings().first()
                if duplicate:
                    return existing_result(duplicate)
                similar = conn.execute(select(m.records.c.id).where(
                    m.records.c.user_id == g.user_id,
                    m.records.c.name_key == canonical['name'],
                    m.records.c.external_id != record['external_id'],
                    m.records.c.fingerprint != fingerprint
                ).limit(1)).first()
                if similar and not confirmed:
                    return jsonify(classification='possible_false_positive', error='Matching name with a different source ID. Review the details and confirm distinct only if appropriate.'), 409
                result = conn.execute(m.records.insert().values(user_id=g.user_id, external_id=record['external_id'],
                    name_key=canonical['name'], fingerprint=fingerprint, encrypted_data=encrypt(record, g.user_id)))
                audit(conn, 'record_created', 'distinct reviewed' if similar else 'unique validated', g.user_id)
                return jsonify(id=result.inserted_primary_key[0], classification='false_positive_resolved' if similar else 'unique', message='Validated record inserted.'), 201
        except IntegrityError:
            with engine.connect() as conn:
                existing = conn.execute(select(m.records).where(condition)).mappings().first()
                if existing is None:
                    existing = conn.execute(select(m.records).where(same_content)).mappings().first()
            if existing:
                return existing_result(existing)
            raise

    @app.post('/api/vault')
    @required('vault:write')
    def add_secret():
        data = payload({'label', 'secret'}, {'label', 'secret'})
        label, value = string(data, 'label', 80), string(data, 'secret', 2000)
        with engine.begin() as conn:
            result = conn.execute(m.vault.insert().values(user_id=g.user_id, label=label, encrypted_data=encrypt(value, g.user_id)))
            audit(conn, 'vault_created', 'encrypted field stored', g.user_id)
        return jsonify(id=result.inserted_primary_key[0], message='Stored with AES-256-GCM.'), 201

    @app.get('/api/vault')
    @required('vault:read')
    def list_secrets():
        query = request.args.get('q', '')
        if len(query) > 200:
            raise APIError('Search must be at most 200 characters.')
        with engine.connect() as conn:
            rows = conn.execute(select(m.vault).where(m.vault.c.user_id == g.user_id,
                m.vault.c.label.contains(query, autoescape=True)).limit(100)).mappings()
            result = [dict(id=r['id'], label=r['label'], secret=decrypt(r['encrypted_data'], g.user_id)) for r in rows]
        return jsonify(entries=result)

    @app.get('/api/audit')
    @required('audit:read')
    def get_audit():
        with engine.connect() as conn:
            result = [dict(r) for r in conn.execute(select(m.audit).order_by(m.audit.c.id.desc()).limit(100)).mappings()]
        return jsonify(events=result)

    @app.get('/api/routes')
    def list_routes():
        with engine.connect() as conn:
            result = [dict(r) for r in conn.execute(select(m.routes).order_by(m.routes.c.id)).mappings()]
        return jsonify(routes=result)

    def ticket(row):
        result = dict(row)
        result.pop('idempotency_key', None)
        result.pop('user_id', None)
        result['verification_code'] = signer.dumps({'booking_id': row['id'], 'user_id': row['user_id']}) if row['status'] == 'active' else None
        return result

    @app.post('/api/passes')
    @required('passes:write')
    def book():
        data = payload({'route_id'}, {'route_id'})
        route_id = data['route_id']
        if type(route_id) is not int:
            raise APIError('route_id must be an integer.')
        idem = request.headers.get('Idempotency-Key', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,80}', idem):
            raise APIError('Supply an Idempotency-Key of 8–80 letters, digits, hyphens or underscores.')
        same = and_(m.bookings.c.user_id == g.user_id, m.bookings.c.idempotency_key == idem)
        def replay(row):
            if row['route_id'] != route_id:
                raise APIError('Idempotency key already used for another route.', 409)
            return jsonify(booking=ticket(row), replayed=True)
        try:
            with engine.begin() as conn:
                old = conn.execute(select(m.bookings).where(same)).mappings().first()
                if old:
                    return replay(old)
                route = conn.execute(select(m.routes).where(m.routes.c.id == route_id)).mappings().first()
                if not route:
                    raise APIError('Route not found.', 404)
                if datetime.fromisoformat(route['departure'].replace('Z', '+00:00')) <= datetime.now(timezone.utc):
                    raise APIError('This demonstration departure has passed.', 409)
                result = conn.execute(update(m.routes).where(m.routes.c.id == route_id, m.routes.c.remaining > 0).values(remaining=m.routes.c.remaining - 1))
                if result.rowcount != 1:
                    # A concurrent identical request can consume the final seat.
                    old = conn.execute(select(m.bookings).where(same)).mappings().first()
                    if old:
                        return replay(old)
                    raise APIError('Route sold out.', 409)
                row = dict(id=str(uuid.uuid4()), user_id=g.user_id, route_id=route_id,
                           fare_cents=route['fare_cents'], status='active', idempotency_key=idem, issued_at=int(time.time()))
                conn.execute(m.bookings.insert().values(**row))
                audit(conn, 'pass_issued', row['id'], g.user_id)
                return jsonify(booking=ticket(row), replayed=False), 201
        except IntegrityError:
            with engine.connect() as conn:
                old = conn.execute(select(m.bookings).where(same)).mappings().first()
            if old:
                return replay(old)
            raise

    @app.get('/api/passes')
    @required('passes:read')
    def my_passes():
        with engine.connect() as conn:
            result = [ticket(r) for r in conn.execute(select(m.bookings).where(m.bookings.c.user_id == g.user_id).order_by(m.bookings.c.issued_at.desc()).limit(100)).mappings()]
        return jsonify(bookings=result)

    @app.post('/api/passes/<booking_id>/cancel')
    @required('passes:write')
    def cancel(booking_id):
        with engine.begin() as conn:
            row = conn.execute(select(m.bookings).where(m.bookings.c.id == booking_id, m.bookings.c.user_id == g.user_id)).mappings().first()
            if not row:
                raise APIError('Pass not found.', 404)
            changed = conn.execute(update(m.bookings).where(m.bookings.c.id == booking_id,
                m.bookings.c.status == 'active').values(status='cancelled'))
            if changed.rowcount == 1:
                conn.execute(update(m.routes).where(m.routes.c.id == row['route_id']).values(remaining=m.routes.c.remaining + 1))
                audit(conn, 'pass_cancelled', booking_id, g.user_id)
        return jsonify(message='Pass cancelled; seat restored once.')

    @app.post('/api/passes/verify')
    @required('passes:read')
    def verify():
        data = payload({'code'}, {'code'})
        code = string(data, 'code', 1000)
        try:
            claim = signer.loads(code, max_age=86400)
        except (BadSignature, SignatureExpired):
            raise APIError('Invalid or expired verification code.', 400)
        if claim.get('user_id') != g.user_id:
            raise APIError('This code belongs to another account.', 403)
        with engine.connect() as conn:
            row = conn.execute(select(m.bookings).where(m.bookings.c.id == claim.get('booking_id'), m.bookings.c.user_id == g.user_id)).mappings().first()
            if not row or row['status'] != 'active':
                raise APIError('Pass is not active.', 409)
            departure = conn.scalar(select(m.routes.c.departure).where(m.routes.c.id == row['route_id']))
            if datetime.now(timezone.utc).timestamp() > datetime.fromisoformat(departure.replace('Z', '+00:00')).timestamp() + 7200:
                raise APIError('Pass has expired for this departure.', 409)
        return jsonify(valid=True, booking=ticket(row))

    @app.post('/api/chat')
    def chat():
        data = payload({'question'}, {'question'})
        question = string(data, 'question', 500)
        return jsonify(retriever.answer(question))

    return app
