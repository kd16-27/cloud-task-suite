# Task 3 — Recoverable bus passes

## What you built

A fictional ticket-booking system with server-controlled prices, database seat reservations, account-owned bookings, signed verification codes, recovery after sign-in, and cancellation. It collects no payment. Cloud deployment adds an HTTPS load balancer, shared PostgreSQL database, and CPU-driven application autoscaling.

## A. Book a pass

1. Start the app and sign in.
2. Open **03 · Bus passes**.
3. Click **Refresh routes**.
4. Note the Central → Campus fare ($4.50) and remaining seats. Routes are fictional.
5. Click **Book pass** once for Campus.
6. Expected: `Pass issued: ...`, an active booking, and one fewer available seat.
7. The displayed fare comes from the database. The API rejects a browser-supplied `fare_cents` field.

If you see `This demonstration departure has passed`, stop the server with Ctrl+C, then run:

```powershell
.\.venv\Scripts\python.exe manage.py refresh-demo-departures
```

Restart it:

```powershell
.\.venv\Scripts\python.exe run.py
```

This resets fictional route dates to tomorrow; it is a lab maintenance action, not a real transit scheduling tool.

## B. Verify the pass

1. Copy the full verification code displayed under the active booking.
2. Paste it into **Signed verification code**.
3. Click **Verify ownership and status**.
4. Expected: `Valid active pass owned by your account.`
5. Add an extra character to the beginning of the code and verify again.
6. Expected: invalid/expired verification code. Editing a pass does not produce a valid signature.
7. Restore the original code if you want to repeat the valid check.

Verification checks the signature, account owner, active database status, and departure window. A signed code is not a transferable bearer ticket in this lab; the owning account must be signed in. A real conductor/scanner role is outside this demonstration.

## C. Recover a lost pass

1. Refresh the browser. The access token clears because it is held only in memory.
2. Sign in again with the same account.
3. Open Bus passes → **My passes**.
4. Expected: the same booking returns from storage. You did not need a saved screenshot.
5. Close the tab, reopen `http://127.0.0.1:8080`, and repeat if desired.

This recovers the booking after loss of the local display. It does not provide account password recovery or protection if an attacker obtains the account credentials.

## D. Check another account

1. Copy the signed code temporarily for your local check; do not commit it to GitHub.
2. Sign out; sign in with your second fictional account.
3. Click **My passes**.
4. Expected: the first account's booking is absent.
5. Paste the first account's code into verification.
6. Expected: `This code belongs to another account.`
7. Sign back into the owner account.

## E. Cancel and release the seat

1. Click **My passes** and choose **Cancel pass** on the active booking.
2. Expected: status becomes `cancelled`, with its seat restored.
3. Try verifying the old copied code again.
4. Expected: `Pass is not active.`
5. The API also prevents repeated cancellations from adding extra seats; this is covered by tests even though the UI removes the cancel button afterward.

## F. Verify retries and concurrent demand

Open another PowerShell window in the project folder:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -k 'booking or pass or idempotency or departure'
```

Included checks demonstrate:

- Twelve concurrent booking attempts against three seats yield three successes and nine sold-out responses.
- Eight requests sharing one idempotency key produce one booking and consume one seat.
- The same retry behavior works when only the final seat remains.
- Forged client fares, altered pass codes, another account's cancellation, repeated cancellations, and expired departures are rejected or safely handled.

An idempotency key identifies **one attempted booking**. Retrying the same action with that key returns the original result. Choosing Book pass again after success intentionally starts a new booking. The browser retains the key for a failed click while its route tile remains loaded; a full page refresh can create a new key, so check My passes after an uncertain network outcome before booking again.

These are small local correctness checks, not a throughput benchmark. They do not establish a maximum requests-per-second capacity.

## G. Complete cloud hosting and scalability evidence

Follow `cloud-deployment.md`, then repeat A–E on the HTTPS hostname. The template begins with two tasks and scales between two and four based on 60% average CPU. It shares state in RDS so accounts and passes do not depend on one container.

Use the scaling section of the cloud guide to inspect desired/running task counts, healthy targets, and CPU metrics. Multi-AZ database failover is optional and costs more. Autoscaling is a configuration until you observe it respond to load; do not label it verified before that observation.

## Evidence to save

Capture server-supplied fares, an active recovered booking, a tampered-code rejection, another account's access rejection, cancelled status/seat restoration, and test output. Redact signed codes in public screenshots. Later add the HTTPS hostname, two healthy targets, and actual scaling observations with timestamps.
