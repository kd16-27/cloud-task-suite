import time
from sqlalchemy import (MetaData, Table, Column, Integer, String, Text,
                        ForeignKey, UniqueConstraint, CheckConstraint, create_engine, event)
from sqlalchemy.pool import StaticPool

metadata = MetaData()
users = Table('users', metadata,
    Column('id', Integer, primary_key=True),
    Column('email', String(254), nullable=False, unique=True),
    Column('password_hash', String(512), nullable=False),
    Column('role', String(20), nullable=False, default='user'))
tokens = Table('tokens', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', ForeignKey('users.id'), nullable=False),
    Column('token_hash', String(64), unique=True, nullable=False),
    Column('scopes', Text, nullable=False),
    Column('expires_at', Integer, nullable=False))
records = Table('records', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', ForeignKey('users.id'), nullable=False),
    Column('external_id', String(80), nullable=False),
    Column('name_key', String(160), nullable=False),
    Column('fingerprint', String(64), nullable=False),
    Column('encrypted_data', Text, nullable=False),
    UniqueConstraint('user_id', 'external_id', name='uq_record_identity'),
    UniqueConstraint('user_id', 'fingerprint', name='uq_record_content'))
vault = Table('vault', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', ForeignKey('users.id'), nullable=False),
    Column('label', String(80), nullable=False),
    Column('encrypted_data', Text, nullable=False))
routes = Table('routes', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(120), nullable=False),
    Column('fare_cents', Integer, nullable=False),
    Column('capacity', Integer, nullable=False),
    Column('remaining', Integer, nullable=False),
    Column('departure', String(40), nullable=False),
    CheckConstraint('remaining >= 0 AND remaining <= capacity', name='valid_remaining'),
    CheckConstraint('fare_cents > 0', name='positive_fare'))
bookings = Table('bookings', metadata,
    Column('id', String(36), primary_key=True),
    Column('user_id', ForeignKey('users.id'), nullable=False),
    Column('route_id', ForeignKey('routes.id'), nullable=False),
    Column('fare_cents', Integer, nullable=False),
    Column('status', String(20), nullable=False),
    Column('idempotency_key', String(80), nullable=False),
    Column('issued_at', Integer, nullable=False),
    UniqueConstraint('user_id', 'idempotency_key', name='uq_booking_request'))
audit = Table('audit_events', metadata,
    Column('id', Integer, primary_key=True),
    Column('timestamp', Integer, nullable=False),
    Column('user_id', Integer),
    Column('event', String(80), nullable=False),
    Column('detail', String(160), nullable=False))
login_failures = Table('login_failures', metadata,
    Column('id', Integer, primary_key=True),
    Column('subject_hash', String(64), nullable=False, index=True),
    Column('timestamp', Integer, nullable=False))

def make_engine(url):
    opts = dict(pool_pre_ping=True)
    is_sqlite = str(url).startswith('sqlite')
    if is_sqlite:
        opts['connect_args'] = {'check_same_thread': False, 'timeout': 20}
        if ':memory:' in str(url):
            opts['poolclass'] = StaticPool
    engine = create_engine(url, **opts)
    if is_sqlite:
        @event.listens_for(engine, 'connect')
        def sqlite_settings(conn, _):
            conn.execute('PRAGMA foreign_keys=ON')
    return engine


def seed(engine):
    from sqlalchemy import select
    from datetime import datetime, timedelta, timezone
    with engine.begin() as conn:
        if conn.execute(select(routes.c.id).limit(1)).first():
            return
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime('%Y-%m-%d')
        conn.execute(routes.insert(), [
            {'id': 1, 'name': 'Demo Central → Campus', 'fare_cents': 450,
             'capacity': 30, 'remaining': 30, 'departure': tomorrow + 'T09:00:00Z'},
            {'id': 2, 'name': 'Demo Central → Airport', 'fare_cents': 1200,
             'capacity': 12, 'remaining': 12, 'departure': tomorrow + 'T10:30:00Z'}])
