"""Generate an ignored local encryption secret; never overwrite an existing key."""
from pathlib import Path
import secrets

if __name__ == '__main__':
    p = Path(__file__).resolve().parent / '.env'
    if p.exists():
        print('.env already exists. Existing encryption key preserved.')
    else:
        with p.open('x') as f:
            f.write('ENCRYPTION_SECRET=' + secrets.token_urlsafe(48) + '\n')
            f.write('AUTO_INIT=true\n')
        try:
            p.chmod(0o600)
        except OSError:
            pass
        print('Created local .env. Keep it private; losing its key makes encrypted data unreadable.')
