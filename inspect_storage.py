"""Read-only ciphertext inspection for fictional local lab data; never decrypts."""
import sqlite3
from pathlib import Path
path = Path(__file__).resolve().parent / 'instance' / 'cloudlab.db'
if not path.exists():
    raise SystemExit('Start the local app and create a fictional vault entry first.')
with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as conn:
    for table in ('records', 'vault'):
        rows = conn.execute(f'SELECT id, encrypted_data FROM {table} ORDER BY id DESC LIMIT 3').fetchall()
        # Table names are fixed program constants, never user-supplied identifiers.
        print(f'{table}: {len(rows)} recent sample(s)')
        for row_id, ciphertext in rows:
            print(f'  row={row_id} ciphertext_prefix={ciphertext[:72]}...')
    for row_id, hashed in conn.execute('SELECT id, password_hash FROM users ORDER BY id DESC LIMIT 3'):
        print(f'user row={row_id} password_algorithm={hashed.split("$")[0]}')
