# GitHub, evidence, and portfolio use

## Publish without nested folders

First complete the local setup and tests. Use GitHub Desktop signed in as `kd16-27`.

1. Keep the extracted source folder as your working copy/backup.
2. In GitHub Desktop choose **File → New repository**.
3. Name: `cloud-task-suite`.
4. Description: `Four cloud engineering labs: record deduplication, encrypted SQL-safe storage, recoverable bus passes, and a retrieval-based support chatbot.`
5. Local path: choose the **parent** directory where the new repository should live, for example `C:\Users\KadenDiaz\Documents\GitHub`. Desktop appends the repository name.
6. Leave Initialize with README unchecked; this package already includes README and `.gitignore`. Leave Git ignore and License at None for creation. Choosing a public software license later is your decision.
7. Click **Create repository**.
8. Choose **Repository → Show in Explorer**. This is the actual repository folder.
9. Copy the project's files **into this folder**, so `run.py` is directly inside it. Do not copy the enclosing `cloud-task-suite` folder as another nested folder.
10. Include `suite`, `tests`, `cloud`, `docs`, `evidence`, the root `.py` files, requirement files, `Dockerfile`, `.dockerignore`, `.gitignore`, `README.md`, and `START_HERE.md`.
11. Do not copy `.env`, `.venv`, `instance`, caches, database files, cloud credentials, or private screenshots. File Explorer → View → Show → Hidden items may help you see dotfiles. Preserve `.gitignore` and `.dockerignore` from this package.
12. Return to GitHub Desktop. Review Changes. Expected: many code/document files, not just `.gitattributes`.
13. Search the list for `.env` and database files. Neither should be staged. If a secret appears, stop and remove it from the repository copy before committing. Rotate a secret if it was ever published; deleting it from the latest commit does not remove history.
14. Summary: `Add four tested cloud computing lab modules and setup guides`.
15. Click **Commit to main**.
16. Click **Publish repository**. Choose public only if you want the code visible. Review that the repository contains no secrets first.
17. Click **View on GitHub**. Verify that the README appears and links open.

Your URL should be `https://github.com/kd16-27/cloud-task-suite` if that name is available and you publish to that account. This package has not created or pushed that repository for you.

## Evidence folder

Keep the supplied build evidence. Add your own device/platform and test date when you rerun checks. Save screenshots with clear names, such as `task1-duplicate-rejected.png` and `task3-recovered-pass.png`. Public screenshots should not include passwords, tokens, private account details, encryption secrets, or signed pass verification codes.

Do not turn a failed or blocked test into a “passed” result. The supplied report says clearly which checks ran and which still require your laptop/AWS account.

## Optional browser verification

The Python app does not require Node. Only this optional automated UI test does.

1. Install an approved current Node LTS release from https://nodejs.org/.
2. In the project folder, install Playwright without creating a persistent package manifest:

```powershell
npm install --no-save --package-lock=false playwright
npx playwright install chromium
```

3. Start the Python app on port 8080 in one terminal and leave it running.
4. In a second terminal in the same folder, run:

```powershell
node tests/browser_smoke.cjs
```

5. Expected: `Browser smoke tests passed.` It creates a fictional account and checks registration, sign-in, records, vault, booking/verification/cancellation, chat, and mobile overflow. Screenshots and `browser-tests.json` are written to `evidence`.
6. Inspect the generated screenshots visually before publishing them, and redact the signed pass code in the bus-pass screenshot. A clean script exit is not a full accessibility audit or pixel-perfect design guarantee.
7. `node_modules` is ignored by Git; do not commit it.

The build environment could not start Chromium due to an OS permission restriction, so the supplied browser status is blocked rather than passed. This procedure lets you close that gap on your machine.

## Presenting the work accurately

After you have run and understood the projects, a resume entry can say:

**Cloud Engineering & Application Security Lab — Python, SQLAlchemy, Flask, AWS infrastructure as code**

- Implemented four integrated lab modules for record deduplication, AES-256-GCM protected data storage, transactional ticket booking, and retrieval-based support.
- Verified access boundaries, SQL injection defenses, duplicate-write handling, and concurrent seat reservation through 31 automated application checks.
- Authored an AWS CloudFormation deployment for HTTPS load balancing, ECS Fargate scaling, and private PostgreSQL storage.

Use “deployed” and describe actual cloud behavior only after the AWS walkthrough succeeds. If you run the optional PostgreSQL or browser tests, record their actual results. Do not call a local three-seat race test enterprise load testing, or a 25-question tuned development set production chatbot accuracy.

For a contract discussion, demonstrate the working scenario, explain the problem it solves, show the evidence, and state what further work a real client's environment needs. These are portfolio implementations, not certifications, work history, or production service guarantees.

Wait to do the full resume/LinkedIn refresh until your demonstrations and evidence are complete, so you update one main version with defensible claims.
