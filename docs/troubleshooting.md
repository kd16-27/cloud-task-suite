# Troubleshooting

## PowerShell shows `>>`

PowerShell is waiting for the rest of an unfinished command, usually an unmatched quote, bracket, or pasted backtick. Press **Ctrl+C** once. Copy one complete command box from the guide, excluding the Markdown fences. Run it again. Do not type more installation commands into the unfinished prompt.

## “File or directory does not exist” / `Test-Path` is False

Run `Get-Location` and `Get-ChildItem`. The current folder must directly contain `run.py`. In File Explorer, find that file and copy its containing folder's path. Then run:

```powershell
Set-Location -LiteralPath (Read-Host 'Paste the folder path without surrounding quotes')
```

Use the Windows extracted folder, not `/home/...` from WSL. Do not run from inside the ZIP preview.

## Running scripts is disabled

These instructions run `.exe` and `.py` files, not a PowerShell activation script. Skip `Activate.ps1` and use:

```powershell
.\.venv\Scripts\python.exe run.py
```

No execution-policy change is needed. If your organization blocks Python itself, use its approved software process.

## `py` is missing

Install Python through the official Windows instructions in START_HERE. Close and reopen PowerShell. If `python --version` works, `python -m venv .venv` can create the environment instead. Do not use the Microsoft Store launcher stub if it merely opens the store and does not run Python.

## A Python package will not install

First confirm the environment interpreter:

```powershell
.\.venv\Scripts\python.exe -c "import sys, platform; print(sys.version); print(platform.machine())"
```

Then update its package installer and retry:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

If it still fails, preserve the full error. Common causes are blocked internet, missing compatible wheels for the interpreter/CPU, or using a Python version other than the tested 3.12 environment. Do not remove encryption or change dependency versions blindly just to suppress an error.

## It cannot import `suite` or `flask`

Run from the folder containing `run.py` and use the `.venv` Python executable. Install `requirements-dev.txt` into that same environment. Avoid a different global Python interpreter selected by VS Code.

## Missing encryption secret

Run `setup_local.py` once from the project folder before `run.py`. It preserves an existing key. Do not paste a secret into code or GitHub.

## InvalidTag / encrypted records cannot be read

The key and encrypted database no longer match, or ciphertext was corrupted. Restore the matching original `.env` and database backup. A new random key cannot decrypt old data. If the data is disposable, stop the app and move both `.env` and `instance` to a private backup folder before generating a completely fresh lab; do not erase valued data.

## Port 8080 is already in use

Close the earlier lab terminal with Ctrl+C. If another application intentionally uses 8080, choose another local port:

```powershell
$env:PORT = '8081'
.\.venv\Scripts\python.exe run.py
```

Open `http://127.0.0.1:8081`. The optional browser smoke test expects 8080 unless you adapt its URL.

## Browser cannot connect

The server PowerShell window must stay running. Use the exact HTTP localhost address printed by `run.py`. Check the server's error output. Do not open ports to the internet or turn off your firewall to fix a local setup problem.

## Token expired / a refresh signs you out

This is expected: tokens stay in memory and expire after one hour. Sign in again; data persists in the database. If five failed logins triggered a block, wait five minutes before retrying the correct credentials.

## Create account says it cannot be created

That email may already exist. Use Sign in with the password you chose. If using a brand-new disposable demo, choose another fictional `example.test` address. Password recovery is not implemented.

## Duplicate / conflicting ID / possible false positive

These are intentional classifications, not crashes. Follow Task 1. Repeated exact content does not add a row. An existing source ID cannot silently become a different record. Only confirm distinct after reviewing a same-name match.

## Bus route departure has passed

Use `manage.py refresh-demo-departures` as described in Task 3 for the local fictional lab. Production route scheduling would require its own authorized administrative workflow.

## GitHub only shows `.gitattributes`

You likely opened an empty repository folder rather than the folder with the code. In GitHub Desktop, choose Repository → Show in Explorer. Compare that folder with the one that directly contains `run.py`. Follow the publishing guide carefully; do not create repeated nested repository folders.

## Cloud stack fails

Read CloudFormation → stack → Events and find the first failure, then ECS → service → Events and task logs. Typical causes: mismatched region/certificate, unvalidated domain certificate, unavailable instance type/quota, missing ECR image, image built for ARM while task expects x86_64, missing IAM permissions, or a database initializer error. Template lint success does not rule these out. Preserve the exact error and stop before retrying changes that might create additional resources.
