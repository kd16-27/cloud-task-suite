# Security design and limits

## Intended use

A portfolio/assignment lab for fictional data. It is a functioning implementation with targeted local checks, not a production certification or a guarantee against all attacks. Do not use real credentials, passenger information, payments, or client records until a separate production design/review addresses their requirements.

## Controls implemented

- SQL statements use bound values through SQLAlchemy Core. The storage inspection helper interpolates only hardcoded table names; no user-controlled SQL identifiers or general SQL console exist.
- Sensitive record bodies and vault contents use AES-256-GCM, a random 96-bit nonce, and the owner ID as associated data. The AES key derives from a randomly generated high-entropy server secret; it is not derived from a user's password.
- Login passwords use Werkzeug scrypt hashes with individual salts. Capability tokens are random, expire in one hour, are stored as hashes, and support revocation on sign-out.
- Every records/vault/pass operation checks both a token scope and the resource owner. Request data cannot self-assign admin privileges.
- The browser stores tokens only in JavaScript memory. Protected calls use Authorization headers; no authentication cookies or cross-origin credentials are enabled. Content is rendered with text nodes rather than untrusted HTML.
- Request sizes/field lengths are bounded; known field names and types are checked. Content security policy, no-sniff, no-referrer, and no-store headers are sent. Cloud responses include HSTS behind the trusted ALB.
- Failed login attempts are counted in the shared database with a five-per-five-minute account limit. Suspicious SQL-like input is logged as an indicator, never used as the sole security defense.
- Bookings use a database transaction, conditional seat decrement, uniqueness on account/idempotency key, and signed pass verification with database state/owner checks. Cancellation restores a seat only on an actual active-to-cancelled transition.
- Cloud networking limits application ingress to the ALB and database ingress to the app security group. RDS storage is encrypted and application DB connections require certificate/hostname verification.
- The cloud web role receives table data permissions without owning the schema. Schema-owner credentials are given to a separate initialization container. Its execution role can retrieve the named task secrets; the application task role does not grant AWS service permissions.

## What remains visible in storage

Application encryption covers sensitive payloads, not the entire logical schema. User email addresses, source IDs, normalized name matching keys, vault labels, booking metadata, password hashes, token hashes, and audit metadata remain available to the database. Content fingerprints are keyed HMACs. RDS volume encryption adds cloud disk protection, but neither approach hides data from an authorized running app that holds its key.

Use generic vault labels. In a production privacy design, minimize or encrypt additional metadata and review search/index tradeoffs.

## Important limitations

- Registration is open and does not verify email ownership. There is no password reset, MFA, external identity provider, device trust, or production account lifecycle.
- The login limiter is a basic database counter, not a comprehensive distributed abuse defense. Concurrent failures may exceed the nominal limit, attackers can target many accounts, and it can cause short account lockouts. Anonymous endpoints and registration lack comprehensive rate limiting. Add gateway/WAF and identity controls for a public production service.
- Login tokens are bearer credentials. Theft, browser compromise, or an authorized user's device compromise can expose access. They are not hardware-bound or proof-of-possession capabilities.
- User-created data is owner-isolated through application logic; PostgreSQL row-level security is not enabled. A compromised application with DB/key access remains powerful.
- Audit entries intentionally exclude raw sensitive payloads, but the log is not immutable or independently monitored. Expired tokens/login counters/audit rows do not yet have scheduled retention cleanup.
- The deduplication identity rule is domain-specific. Same normalized name/email is one record in this lab. It is not fuzzy entity resolution, a global deduplication service, or external verification. Different accounts can legitimately store the same content. Existing legacy databases need a separate, reviewed cleanup/migration; the app does not destructively deduplicate external data.
- Reads are capped at 100 records/entries/bookings; production pagination, exports, account deletion, retention controls, and schema migrations are not implemented.
- Pass codes are signed, not secret/encrypted. They still require the owner account. This is not a transit scanner system, payment processor, real refund engine, or proof that ticket theft is impossible.
- The browser retains an idempotency key for a failed booking on the current route tile. A full refresh/new tile can start a new request; recover My passes before retrying after an uncertain response.
- AES key rotation and re-encryption are not automated. Backups require the matching key. The cloud template retains that secret on deletion so a retained snapshot is not automatically rendered unreadable, but restoration still needs a planned procedure.
- Cloud tasks scale; the database does not scale automatically with that policy. Default RDS is single-AZ; application replicas alone do not provide database failover. No availability/SLA, recovery-time, or recovery-point target has been demonstrated.
- The deployment initializes schema with `create_all`, suitable for a fresh lab. It does not migrate existing schemas or separate schema migration into a production release pipeline.
- The chatbot is English keyword/vector retrieval and can misclassify queries. It has no generative reasoning or tool access. A small tuned development set must not be marketed as universal accuracy. Human engagement is unmeasured until the provided protocol is run.
- Dependencies are pinned for this build, but transitive dependencies and the Docker base tag are not a fully reproducible audited supply-chain lock. Review image scans, resolve advisories, and rerun tests during maintenance.

## Before adapting it for a paying client

Gather the actual identity, privacy, uptime, scale, retention, payment, and access requirements. Add appropriate identity/MFA and abuse controls, proper migrations/rotation/restore procedures, independent security review, monitored deployment, real cloud/load/failure testing, and a domain-specific data model. Describe this repository as a lab implementation until those client-specific steps are complete.
