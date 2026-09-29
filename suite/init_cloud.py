"""Cloud-only initializer: schema owner credentials never enter the web container."""
import os
import psycopg
from psycopg import sql
from sqlalchemy import select
from werkzeug.security import generate_password_hash
from suite import db_url
from suite import models as m

if __name__=='__main__':
    # Advisory lock serializes initializers started by multiple Fargate tasks.
    connection=psycopg.connect(host=os.environ['DB_HOST'],dbname=os.environ.get('DB_NAME','cloudlab'),
        user=os.environ['DB_USER'],password=os.environ['DB_PASSWORD'],
        sslmode='verify-full',sslrootcert=os.environ['DB_SSLROOTCERT'],autocommit=True)
    connection.execute('SELECT pg_advisory_lock(%s)',(734921,))
    engine=m.make_engine(db_url())
    try:
        m.metadata.create_all(engine)
        m.seed(engine)
        with engine.begin() as conn:
            address=os.environ['ADMIN_EMAIL'].casefold()
            if not conn.execute(select(m.users.c.id).where(m.users.c.email==address)).first():
                conn.execute(m.users.insert().values(email=address,password_hash=generate_password_hash(os.environ['ADMIN_PASSWORD']),role='admin'))
        username='labapp'
        if not connection.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(username,)).fetchone():
            connection.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(username),sql.Literal(os.environ['APP_DB_PASSWORD'])))
        else:
            connection.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(sql.Identifier(username),sql.Literal(os.environ['APP_DB_PASSWORD'])))
        connection.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(os.environ.get('DB_NAME','cloudlab')),sql.Identifier(username)))
        connection.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
        connection.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(username)))
        connection.execute(sql.SQL('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}').format(sql.Identifier(username)))
        connection.execute(sql.SQL('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}').format(sql.Identifier(username)))
        print('Schema initialized; restricted application role ready. No secrets logged.')
    finally:
        engine.dispose()
        connection.execute('SELECT pg_advisory_unlock(%s)',(734921,))
        connection.close()
