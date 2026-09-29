import argparse
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from suite import create_app
from suite import models as m

p = argparse.ArgumentParser()
p.add_argument('command', choices=['make-admin', 'refresh-demo-departures'])
p.add_argument('--email')
a = p.parse_args()
app = create_app()
with app.extensions['engine'].begin() as conn:
    if a.command == 'make-admin':
        if not a.email:
            p.error('--email is required')
        n = conn.execute(update(m.users).where(m.users.c.email == a.email.casefold()).values(role='admin')).rowcount
        print('Account promoted. Sign out and back in to get audit scope.' if n else 'No matching account.')
    else:
        for route in conn.execute(select(m.routes)).mappings():
            date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime('%Y-%m-%d')
            conn.execute(update(m.routes).where(m.routes.c.id == route['id']).values(departure=date + 'T09:00:00Z'))
        print('Demo departures moved to tomorrow. Use only with fictional lab bookings.')
