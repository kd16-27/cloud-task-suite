# Task 1 — Data redundancy removal

## What you built

A validated record store that uses normalized names/emails, source identifiers, keyed content fingerprints, and database uniqueness constraints. Duplicate attempts return the existing record instead of adding another row. Different data under an existing source ID is rejected. A shared name with different details goes through explicit review.

The business rule is explicit: inside one account, an exact normalized name-and-email pair represents one record. Different people who share both values would need a richer identity model before production use. “Verified” here means valid format, checked identity/content, and human confirmation when requested; it is not external identity verification.

## Step-by-step demonstration

Complete `START_HERE.md` and sign in as `kaden@example.test`. Open **01 · Unique records**.

### A. Add a unique record

1. Enter Source record ID: `demo-001`.
2. Enter Name: `Alex Morgan`.
3. Enter Email: `alex@example.test`.
4. Leave the review checkbox unchecked.
5. Click **Validate and add**.
6. Expected: `unique: Validated record inserted.` One Alex Morgan record appears.

### B. Reject the same record

1. Keep the same fields and click **Validate and add** again.
2. Expected: `redundant: Identical record already exists; nothing inserted.` The count remains one.
3. Change the name to `ALEX MORGAN` and email to `ALEX@EXAMPLE.TEST` and submit again.
4. Expected: still redundant. Case normalization prevents a cosmetic change from creating another record.
5. Change only the source ID to `demo-099` and submit.
6. Expected: still redundant. A new ID cannot bypass the content uniqueness rule.

### C. Reject conflicting data under one identity

1. Restore source ID `demo-001` and name `Alex Morgan`.
2. Change the email to `changed@example.test`.
3. Click **Validate and add**.
4. Expected: an error explaining that this source ID already has different data. The original record remains unchanged. This project intentionally does not silently overwrite it.

### D. Resolve a possible false positive

1. Change the source ID to `demo-002`.
2. Keep the name `Alex Morgan`.
3. Use email `alex.second@example.test`.
4. Keep the review checkbox unchecked and submit.
5. Expected: `Matching name with a different source ID. Review the details...` No second row yet.
6. In this fictional example, assume your source confirms this is a different person.
7. Check **I reviewed the matching name and confirmed this is a distinct record**.
8. Submit again.
9. Expected: `false_positive_resolved: Validated record inserted.` Two records now exist with different IDs/emails.
10. Uncheck the review box before your next unrelated record.

### E. Validate input

1. Try source ID `bad id!`.
2. Expected: the API rejects it; IDs allow letters, numbers, underscores, and hyphens.
3. Try an invalid email. Your browser may reject it before submission; the API also validates it.
4. Click **Refresh my records** to confirm rejected entries were not stored.

## Automated verification

Open a second PowerShell window and change to the project folder. Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -k 'record or duplicate or identity or same_name or same_content'
```

The full test suite is authoritative. It also checks eight simultaneous attempts to insert the same record: exactly one insert is permitted.

## What to capture

Save screenshots of the unique result, redundant result, conflicting-ID rejection, review-required message, and two distinct same-name records. Include the passing test output. Avoid putting passwords, tokens, or `.env` in screenshots.

## How the cloud requirement is met

The same database constraints and API run against PostgreSQL through the included AWS deployment. Local SQLite is the first implementation stage. Complete the AWS guide and repeat A–E at the HTTPS hostname before claiming a deployed cloud database demonstration.

## Explain it in an interview

“I combine normalization and database constraints to stop duplicate writes, and use explicit review for ambiguous same-name matches. Application prechecks improve feedback; database uniqueness protects the result when requests arrive concurrently.”
