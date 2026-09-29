# Start here — complete Windows setup

Prepared for Kaden Diaz • Cloud Task Lab • 28 September 2026

This package contains the code for all four requested projects. First run it on your laptop. Then follow each task's demonstration. Cloud hosting is a separate, billable stage in `docs/cloud-deployment.md`.

Do these steps in **Windows PowerShell**, using Windows paths such as `C:\Users\KadenDiaz\...`. Do not use the VS Code WSL/Linux terminal for these Windows commands. Copy only the code inside each box, one box at a time; do not copy `PS>` or the Markdown backticks.

## 1. Extract the download

1. Download `Cloud_Task_Suite.zip`.
2. Open File Explorer → Downloads.
3. Right-click the ZIP → **Extract All** → choose a folder you can find, such as `Documents\Projects` → **Extract**.
4. Open the extracted `cloud-task-suite` folder. The correct folder directly contains `run.py`, `setup_local.py`, `requirements.txt`, and `START_HERE.md`.
5. Click the File Explorer address bar and copy the complete folder path. If extraction added another folder level, keep opening until you see `run.py`.
6. Open VS Code → File → Open Folder → select that same folder. Use VS Code to read and edit files; the commands below go in Windows PowerShell.

## 2. Open PowerShell in that folder

Press the Windows key, type **PowerShell**, and open it normally. Administrator mode is unnecessary.

Run:

```powershell
Set-Location -LiteralPath (Read-Host 'Paste the full extracted folder path, without surrounding quotes')
```

Paste the path when asked and press Enter. Then run:

```powershell
Test-Path .\run.py
```

Expected: `True`. If you see `False`, stop here and choose the folder containing `run.py` before continuing.

To confirm the files:

```powershell
Get-ChildItem
```

## 3. Check/install Python

Run:

```powershell
py --version
```

Use Python 3.12 for the closest match to the tested environment. If it is already installed, continue. If `py` is not recognized:

1. Open https://www.python.org/downloads/windows/ and choose an official Windows installer for a supported Python version. This build was tested with Python 3.12; other versions require rerunning the included tests.
2. Use the installer appropriate for your Windows processor. If your GCA laptop is managed, use the organization's approved installation process. Windows on ARM can need compatible wheels or the x64 Python installer under Windows emulation; do not mix ARM and x64 Python environments.
3. Install the Python launcher if the installer offers it. Enable the PATH option if offered.
4. Close PowerShell, reopen it, repeat Step 2, and rerun `py --version`.

If `python --version` works but `py --version` does not, replace **only the first `py` command below** with `python`. The later commands call the virtual environment directly.

## 4. Create the project environment

Run:

```powershell
py -m venv .venv
```

This creates a separate Python environment for the project. It may take a short while and normally prints nothing.

Check it:

```powershell
Test-Path .\.venv\Scripts\python.exe
```

Expected: `True`.

Install the libraries and test runner:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Wait for the prompt to return. First installation needs internet access and may take several minutes. An error is not successful installation; see `docs/troubleshooting.md`.

**You do not need to activate the environment or run `Activate.ps1`.** These commands call its Python executable directly, avoiding the script execution-policy issue from your earlier lab.

## 5. Generate the local secret

Run:

```powershell
.\.venv\Scripts\python.exe setup_local.py
```

Expected: `Created local .env...` on the first run, or `Existing encryption key preserved` later. This file holds your local encryption key. Keep it private. Do not delete or replace it while keeping the database; old encrypted records depend on it.

## 6. Run the checks

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: **31 passed**. Timing will vary by laptop. Tests create temporary databases and do not erase your app data. If a test fails, keep the complete failure text and resolve it before presenting the project as verified on your laptop.

Then evaluate the chatbot:

```powershell
.\.venv\Scripts\python.exe evaluate_chat.py
```

Expected: JSON containing `"cases": 25`, `"correct": 25`, and `"accuracy": 1.0`. This describes the included development examples only.

## 7. Start the website

Run:

```powershell
.\.venv\Scripts\python.exe run.py
```

Expected:

```text
Open http://127.0.0.1:8080 — Ctrl+C stops the application.
```

Leave that terminal open. It is now running the server; it is normal that the PowerShell prompt does not return.

Open Edge or Chrome and enter:

```text
http://127.0.0.1:8080
```

Do not use HTTPS for this local address. The local server binds only to your laptop. Cloud HTTPS is configured separately.

## 8. Create a fictional lab account

1. Enter `kaden@example.test` in the email box. This is a demonstration address; no email is sent.
2. Choose a new demonstration password of at least 12 characters. Do not reuse a personal or work password.
3. Click **Create account**. Look for `Demo account created. Sign in to continue.`
4. Click **Sign in** with the same email and password still entered.
5. Look for `Signed in as kaden@example.test`. The password field clears after successful login.

Refreshing the page clears the in-memory access token. Sign in again to retrieve your saved data. Tokens also expire after one hour. Creating an account again is unnecessary.

## 9. Complete all four walkthroughs

Open these files in VS Code. Right-click a Markdown file → **Open Preview**, or use `Ctrl+Shift+V`.

1. `docs/task-1-records.md`: unique records, duplicate rejection, conflicting identity, same-name review.
2. `docs/task-2-security.md`: encryption, safe injection tests, access isolation, audit events.
3. `docs/task-3-passes.md`: booking, recovery, tamper rejection, cancellation, race checks.
4. `docs/task-4-chat.md`: retrieval, fallback, evaluation, customization, engagement acceptance checks.

Each guide includes expected results and evidence to save. Use fake data throughout.

## 10. Stop and restart

To stop, return to the server PowerShell window and press **Ctrl+C** once.

Next time:

1. Open PowerShell.
2. Change to the same project folder using Step 2.
3. Run:

```powershell
.\.venv\Scripts\python.exe run.py
```

You do not need to reinstall packages or recreate the secret. Keep both `.env` and the `instance` folder to retain your local data.

## 11. Publish your work and deploy later

Follow `docs/github-and-portfolio.md` to put the code and truthful evidence on GitHub. The suggested repository name is **cloud-task-suite**.

Follow `docs/cloud-deployment.md` only when your authorized AWS setup, domain, and budget are ready. The AWS guide includes image publishing, infrastructure creation, verification, scaling checks, and cleanup. Nothing in the local setup creates cloud resources or charges.

Keep a single main resume and LinkedIn profile. After you have run the demonstrations and can explain the design, add these projects together using evidence you actually collected. Cloud deployment and load-test claims must wait for those steps to succeed.
