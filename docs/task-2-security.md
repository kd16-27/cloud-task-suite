# Task 2 — SQL injection protection and encrypted storage

## Requirement interpretation

The assignment's phrase “inject SQL securely” is implemented as **executing predefined operations using bound parameters**. The app never offers a general-purpose SQL execution box. A capability code is a random, expiring bearer token with allowed actions such as `vault:read` or `records:write`.

Two principal protection layers are (1) scoped authorization plus owner checks and (2) parameterized database access. AES-256-GCM additionally protects stored sensitive contents. Passwords use salted scrypt hashes; reversible encryption would be the wrong storage model for login passwords. Sensitive notes, including fictional credential-like values, use AES-256-GCM.

## A. Store and retrieve an encrypted value

1. Start the server and sign in using the main guide.
2. Open **02 · Secure vault**.
3. Set Label to `Demo access note`.
4. Set fictional content to `Training value - never a real password`.
5. Click **Encrypt and save**.
6. Expected: `Stored with AES-256-GCM.`
7. Leave Search labels empty and click **Search my vault**.
8. Expected: your label and decrypted content appear. Decryption is permitted only after your account and scope checks succeed.
9. In a second PowerShell window in the project folder, run:

```powershell
.\.venv\Scripts\python.exe inspect_storage.py
```

10. Expected: record/vault storage samples show ciphertext and password storage shows the algorithm name, not your password. This command does not print your encryption key, bearer tokens, or decrypted notes. A screenshot of ciphertext alone is illustrative; the automated tests below verify encryption round trips and randomized nonces.

## B. Test SQL-like input safely

Use only this lab's own search field and fictional data.

1. In Search labels, enter:

```text
' OR 1=1 --
```

2. Click **Search my vault**.
3. Expected: `No matching entries.` The string is treated as a literal search value.
4. Try:

```text
' UNION SELECT password_hash FROM users --
```

5. Expected: no returned entries and no database error revealing credentials.
6. Clear Search labels and search again.
7. Expected: your original note still exists and decrypts correctly.
8. These examples demonstrate selected defenses; passing them is not a proof against every possible vulnerability.

## C. Prove account isolation

1. Click **Sign out**.
2. Register `second@example.test` with another demonstration password, then sign in.
3. Open Secure vault, leave search empty, and search.
4. Expected: no entries from the first account.
5. Store a separate fictional note if desired.
6. Sign out and sign back in as the first account; its own data is still available.

## D. Review security events as a local administrator

Normal users cannot read the global audit log. Promotion is a local administrative action, not a permission offered by the website.

1. Keep the server running.
2. Open a second PowerShell window and change to the project folder as in the main guide.
3. Run:

```powershell
.\.venv\Scripts\python.exe manage.py make-admin --email kaden@example.test
```

4. Expected: `Account promoted. Sign out and back in to get audit scope.`
5. In the browser, sign out and sign in again with that account.
6. Open Secure vault → **View audit events (admin)**.
7. Expected: recent events, including `suspicious_input` from your test searches. The audit records store the route and event classification, not the submitted secret or full attack text.
8. An ordinary second account should receive `This capability token does not permit that action.` when trying to read the audit.

## E. Run the security checks

In the second PowerShell window:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -k 'sql_injection or vault or token or scope or password or throttle or isolation or no_default_admin'
```

Checks include encrypted-at-rest values, different ciphertext for repeated values, ownership, expired tokens, scope restrictions, attempted privilege escalation, sign-out revocation, throttled failed logins, literal search wildcards, and parameterized SQL behavior.

## What to capture

Use a ciphertext inspection, a successful authorized lookup, a SQL-like lookup returning no results, a second account unable to see another account's data, and admin audit output. Crop out credentials and signed pass codes.

## Cloud implementation

Follow the AWS guide. It provides HTTPS at the load balancer, TLS verification to RDS, Secrets Manager delivery, encrypted RDS storage, and a restricted web database role. The initialization container uses separate schema-owner credentials; those are not passed to the web container.

This is a teaching implementation. Registration is open, email ownership is not verified, and there is no production identity provider, MFA, account recovery, WAF, or comprehensive abuse control. Keep the deployed demonstration temporary and use fictional data. See the limitations document before adapting it for clients.
