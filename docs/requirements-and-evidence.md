# Requirements and evidence

Prepared from the two supplied assignment screenshots. The document allows two or three tasks; this package implements all four as modules of one application. Page-one instructions or submission rules not visible in the screenshots are not assumed.

## Requirement mapping

| Assignment requirement | Implementation | Verification / status |
|---|---|---|
| Task 1: identify redundant records and false positives | Normalized content fingerprint; identity/content uniqueness; explicit same-name review | Duplicate, changed-ID, identity-conflict, and false-positive tests passed locally |
| Validate incoming data against existing records | Typed/length/format checks plus owner-scoped comparison | Invalid-data and record tests passed |
| Prevent duplicate cloud database entries | Unique constraints on owner/source ID and owner/content fingerprint, with race handling | Eight parallel duplicate attempts tested on SQLite; same schema supplied for PostgreSQL; live cloud pending |
| Append only unique, verified records | Accepted new content is inserted transactionally; conflicts/review-needed entries are not inserted | Local API tests passed; “verified” means validation/review, not real identity proof |
| Improve data accuracy/efficiency by avoiding redundancy | Indexed uniqueness constraints and bounded reads; encrypted canonical payload | Functional result verified; no large-dataset performance benchmark |
| Task 2: secure cloud system against SQL injection | SQLAlchemy bound expressions, permitted API operations, scoped/owner authorization | Three SQL-like attack cases passed; cloud runtime still pending |
| AES-256 for credentials/sensitive info | AES-256-GCM for sensitive records/vault content; separate scrypt hashing for login passwords | Ciphertext/nonces/decryption/password-hash tests passed; safe correction to reversible password storage |
| Capability-code mechanism and server access | One-hour random bearer tokens, stored as hashes, requested scopes restricted to role | Scope, expiry, revocation, and privilege escalation tests passed |
| Double-layer security | Authorization/ownership plus parameterized SQL, with field encryption as additional defense | Ownership and injection tests passed; no general SQL execution endpoint |
| Internet access without heavy client requirements | Browser frontend; no local AI runtime; AWS HTTPS deployment template | Web routes served in application tests; actual internet hosting pending |
| Task 3: online cloud booking | Route list, server-priced booking, account retrieval, cancellation, verification | Local API checks passed; deployment pending |
| Prevent ticket loss/theft/incorrect pricing | Persistent owner-owned booking, signed code, live status check, server prices | Recovery, owner rejection, tamper rejection, pricing/cancel tests passed; stolen credentials remain a risk |
| Handle high traffic through dynamic provisioning | Fargate task target tracking: 2–4 tasks, 60% CPU | Template statically validated; actual scale-out and capacity not measured |
| Scalability/reliability | Shared RDS, multiple tasks/AZs, health checks, deployment rollback, optional RDS Multi-AZ, transactional state | Transactional race checks passed; failover/restore/load tests pending |
| Test and deploy booking system | Automated tests, four manual flows, Dockerfile, CloudFormation and deployment guide | Code/tests delivered; no AWS deployment claim |
| Task 4: retrieval or generative AI | TF-IDF/cosine retrieval over 30 patterns and 10 intents | Matched/fallback API tests and development evaluation passed |
| Instant website responses | Small in-process retrieval without external API calls | In-process timings recorded; full end-to-end/cloud latency unmeasured |
| Predefined commercial-use input patterns | Curated booking/security/data help intents; editable patterns/answers | Development cases and customization walkthrough supplied; client-specific validation still needed |
| Website integration | Same-origin `/api/chat`, safe text rendering, source labels, fallback | API exercised; browser test supplied but blocked in build environment |
| Optimize/test accuracy and engagement | Similarity/margin/coverage fallback; held-separate wording for development questions; engagement protocol/template | 25/25 tuned development cases; no independent accuracy benchmark or completed human engagement study |

## Executed checks

- `python -m pytest -q --junitxml=evidence/local-tests.xml`: 31 passed on Linux/Python 3.12 with isolated temporary SQLite databases.
- `python evaluate_chat.py`: 25/25 included development cases. See `evidence/chat-evaluation.json` for question-level predictions and in-process timing.
- `cfn-lint cloud/cloudformation.json`: exit 0, no errors or warnings. This is template validation only.
- Python files compiled and browser JavaScript syntax checked during packaging. These do not replace browser rendering or platform tests.

The booking race tests use 12 attempted bookings for 3 seats and repeated same-key requests, including a one-seat case. This supports correctness of the tested local behavior, not a production throughput estimate.

## Explicitly not verified in this build

- Windows installation/execution on Kaden's device.
- Chromium rendering, actual clicks, accessibility, and responsive visuals. Chromium was downloaded, but its launch failed because the execution environment did not permit its socket operation. The included `tests/browser_smoke.cjs` is a reproduction tool, not a passing result.
- A running PostgreSQL database, RDS role initialization/TLS, Docker image runtime, AWS provisioning, DNS/HTTPS, health targets, actual scaling, cloud availability, and disaster recovery.
- Penetration testing, broad adversarial coverage, external identity validation, real payments, independent chatbot accuracy, or measured human engagement.

These remaining checks are documented so the work can be implemented and reviewed honestly. No software package can be certified “absolutely perfect” from a finite local test suite.

## Your acceptance checklist

- [ ] Run all 31 checks on the Windows laptop and record the Python version/date.
- [ ] Run the chatbot evaluation and inspect each failed or unexpected answer.
- [ ] Complete the manual Task 1–4 demonstrations.
- [ ] Run the optional browser test and visually inspect its screenshots.
- [ ] Run optional PostgreSQL checks if Docker is available.
- [ ] Publish only code, fictional examples, and safe evidence.
- [ ] When authorized, deploy AWS and verify the HTTPS/database/module behavior.
- [ ] Observe and document actual scaling before claiming it worked.
- [ ] Complete human chatbot usability checks with fresh questions.
- [ ] Clean up billable cloud resources and retained artifacts when finished.
