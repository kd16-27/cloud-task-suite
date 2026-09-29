# AWS implementation — complete deployment path

## Status and prerequisites

The code and CloudFormation template are supplied; **no live AWS deployment has been performed**. The template passed static cfn-lint validation. Linux application tests used SQLite. AWS provisioning, the PostgreSQL initialization/permissions, HTTPS, health checks, and actual autoscaling still need the target environment checks below.

Use a dedicated, authorized lab account/profile. Your earlier GCA account setup was on hold; wait for that access to be settled rather than guessing which corporate account to use. This guide does not require sending AWS keys to anyone.

This configuration creates billable resources: two or more Fargate tasks, an Application Load Balancer, RDS PostgreSQL, public IPv4 addresses, Secrets Manager secrets, ECR image storage, CloudWatch logs/metrics, backups, and data transfer. A domain/DNS may also cost money. Review current regional estimates at https://calculator.aws/ and create an AWS Budget before launching. A budget alert is not an automatic spending cap. This is intentionally a realistic cloud architecture; it is not advertised as free.

Required before proceeding:

- Local tests and demonstrations completed.
- Authorized AWS account with the permissions to create the stack's VPC, RDS, ECS, ALB, IAM, Secrets Manager, logging, and scaling resources. Use your approved deployment role, not a root account access key.
- AWS CLI v2 installed using https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html.
- Docker Desktop working with Linux containers, installed through https://docs.docker.com/desktop/setup/install/windows-install/. Follow your device's approved installation process and architecture requirements.
- An owned DNS hostname, such as `lab.your-domain.example`, and permission to add DNS records.
- One AWS region that supports these services and the selected database class. The example below uses `us-east-1`; use your approved region consistently.

## 1. Sign in to the AWS CLI and verify the account

If your organization uses IAM Identity Center, use its supplied start URL/region:

```powershell
aws configure sso --profile cloudlab
aws sso login --profile cloudlab
```

For another account login method, use the administrator's approved CLI configuration. Do not invent SSO values or create permanent access keys merely to follow this example.

Set the profile and region in PowerShell:

```powershell
$labProfile = 'cloudlab'
$labRegion = 'us-east-1'
aws sts get-caller-identity --profile $labProfile --region $labRegion
```

Read the Account and Arn output. Confirm it is the intended lab account before creating anything. If access is expired, refresh the approved login. Keep this PowerShell window open so its variables remain defined.

In the AWS console, select the same region. Open Billing → Budgets and create an alert appropriate to your own budget. Review the calculator estimate for the resources listed above.

## 2. Obtain a certificate for your hostname

1. In that region, open **AWS Certificate Manager (ACM)**.
2. Choose **Request certificate → Request a public certificate**.
3. Enter your owned full hostname, for example `lab.yourdomain.com`.
4. Choose DNS validation and request it.
5. Open the certificate's details and copy the required CNAME validation record into your DNS provider's record editor. Use ACM's Create records in Route 53 button if the domain is hosted there and you have permission.
6. Wait until status is **Issued**. DNS validation may take time.
7. Copy its certificate ARN. The ARN region must match your selected AWS region.

A certificate for a hostname you do not own cannot be substituted. This template requires HTTPS; an ALB's default AWS hostname will not match your certificate.

## 3. Build the container image

Open Docker Desktop and wait until its engine is running. In the same PowerShell window, change to the project folder containing `Dockerfile`.

```powershell
Test-Path .\Dockerfile
docker version
```

Expected: `True`, then both client and server Docker information. Build explicitly for the template's x86_64 platform, including on an ARM laptop:

```powershell
docker buildx build --platform linux/amd64 --load -t cloud-task-suite:1 .
```

Wait for a successful build. It downloads a base image and dependencies, so allow several minutes. Do not proceed after a failed build. No `.env` or local database is copied because `.dockerignore` excludes them.

## 4. Optional but recommended: verify PostgreSQL before AWS

This starts a disposable local test database in Docker. It is separate from your SQLite demo. Run it only when no container with this exact lab name is already needed.

```powershell
docker run --name cloudlab-postgres-test --rm -d -p 127.0.0.1:5433:5432 -e POSTGRES_DB=cloudlab_test -e POSTGRES_USER=labtest -e POSTGRES_PASSWORD=Local-Disposable-Test-Only-123 postgres:17
```

Check readiness:

```powershell
docker exec cloudlab-postgres-test pg_isready -U labtest -d cloudlab_test
```

If it is not accepting connections, wait briefly and repeat that check. Then:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-cloud.txt
$env:TEST_DATABASE_URL = 'postgresql+psycopg://labtest:Local-Disposable-Test-Only-123@127.0.0.1:5433/cloudlab_test'
$env:ALLOW_TEST_DATABASE_RESET = '1'
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass. These tests reset their schema, which is why they require the specifically named disposable `cloudlab_test` database and the reset flag. Never point this URL at a valued database. This optional test was not executable in the build environment and is not included in the verified claims.

Clean up the test environment after recording the result:

```powershell
Remove-Item Env:TEST_DATABASE_URL
Remove-Item Env:ALLOW_TEST_DATABASE_RESET
docker stop cloudlab-postgres-test
```

This stops and removes the disposable container; it has no persistent volume. These checks exercise PostgreSQL queries, but the AWS initializer and RDS TLS still require the live checks below.

## 5. Publish the image to ECR

Capture the already-verified account ID:

```powershell
$labAccount = (aws sts get-caller-identity --profile $labProfile --region $labRegion --query Account --output text).Trim()
$labRegistry = "${labAccount}.dkr.ecr.${labRegion}.amazonaws.com"
$labImage = "${labRegistry}/cloud-task-suite:1"
```

Create a new, immutable-tag lab repository:

```powershell
aws ecr create-repository --repository-name cloud-task-suite --image-tag-mutability IMMUTABLE --image-scanning-configuration scanOnPush=true --profile $labProfile --region $labRegion
```

If AWS says it already exists, confirm it is your intended lab repository. Do not delete or overwrite someone else's repository. For later versions use a fresh tag such as `:2`.

Log Docker in without printing the temporary registry password:

```powershell
aws ecr get-login-password --profile $labProfile --region $labRegion | docker login --username AWS --password-stdin $labRegistry
```

Expected: `Login Succeeded`.

```powershell
docker tag cloud-task-suite:1 $labImage
docker push $labImage
```

Wait for a completed push. In ECR → repository → image, review scan results before exposing the app. Resolve material findings rather than assuming pinned libraries are permanently safe.

Capture the immutable image digest:

```powershell
$labDigest = (aws ecr describe-images --repository-name cloud-task-suite --image-ids imageTag=1 --query 'imageDetails[0].imageDigest' --output text --profile $labProfile --region $labRegion).Trim()
$labImageDigestUri = "${labRegistry}/cloud-task-suite@${labDigest}"
$labImageDigestUri
```

The printed URI is not a secret. You will paste it into CloudFormation.

## 6. Validate and create the stack

Validate syntax with AWS:

```powershell
aws cloudformation validate-template --template-body file://cloud/cloudformation.json --profile $labProfile --region $labRegion
```

Then use the console for the reviewable deployment:

1. Open **CloudFormation** in the same account/region.
2. Choose **Create stack → With new resources (standard)**.
3. Choose **Choose an existing template → Upload a template file**.
4. Upload `cloud/cloudformation.json` from this project.
5. Choose Next. Set Stack name to `kaden-cloud-task-lab`.
6. Fill the parameters:

| Parameter | Value |
|---|---|
| `ImageUri` | The ECR digest URI printed in Step 5 |
| `CertificateArn` | The issued ACM ARN from Step 2 |
| `DomainName` | Your full hostname, without `https://` or a path |
| `AdminEmail` | `kaden@example.test`, or another fictional demonstration account identifier |
| `DatabaseMultiAZ` | `false` for the lower-cost single-database lab; `true` to provision database failover at additional cost |

7. On stack options, add a tag such as `Project=KadenCloudTaskLab` for tracking. Use any deployment role required by your account administrator.
8. Review the template and resources. Acknowledge that it creates IAM resources.
9. Choose **Submit/Create stack**. This is the point where AWS resources and charges begin.
10. Watch the Events tab until **CREATE_COMPLETE**. RDS can make this take tens of minutes. Do not repeatedly submit duplicate stacks while waiting.

If it fails, inspect the first failing event and ECS initialization logs. Do not claim deployment success until the stack and application are healthy. See troubleshooting for likely causes.

## 7. Connect DNS and verify HTTPS

1. Open the stack's **Outputs** tab.
2. Copy `LoadBalancerDns`.
3. At your DNS provider, create a CNAME from your chosen subdomain (for example `lab`) to that ALB DNS hostname. Use only the hostname as the CNAME target, not `https://...`.
4. If using Route 53, an A alias record to the ALB is also suitable. Avoid trying to use a CNAME at a bare root domain if your DNS service does not support it.
5. Wait for DNS propagation.
6. Open `https://YOUR-HOSTNAME/health`. Expected: `{"status":"ok"}` and a valid certificate.
7. Open `http://YOUR-HOSTNAME`; expected: redirect to HTTPS.
8. Open `https://YOUR-HOSTNAME` and verify the application page.

The application containers have public IPs for image/log/secret egress without a NAT gateway, but their security group accepts port 8080 only from the load balancer. The database is private and reachable only from the application security group.

## 8. Sign in and test all four modules

Cloud accounts/data are separate from local SQLite. No private local data is uploaded automatically.

1. Open the CloudFormation `AdminPasswordSecretArn` output in Secrets Manager.
2. Retrieve the initial demonstration admin password privately. Do not screenshot, commit, or send it.
3. On the app, sign in with the `AdminEmail` you configured and that password. Do not use Create account for this already-created administrator.
4. Run the Task 1–4 walkthroughs at the cloud hostname, substituting this cloud account.
5. Create an ordinary second account to repeat ownership/scope checks.
6. In ECS → cluster → service, verify desired count 2 and running count 2.
7. In EC2 → Target groups → your stack's target group → Targets, confirm healthy application targets.
8. Read CloudWatch logs for both `initialize` and `web`. The initializer should say the schema and restricted app role are ready. There must be no repeated initialization or TLS errors.
9. Refresh/reopen the browser and sign back in; records and bookings should persist in RDS.

These live checks, together with the local PostgreSQL tests when possible, are the evidence that completes the cloud portion. Include the account-isolation and injection demonstrations here; a healthy landing page alone does not verify data security.

## 9. Observe scalability without inventing a benchmark

First record the timestamp, running tasks, healthy targets, CPU utilization, and error rate at idle. In ECS → service → Auto Scaling, confirm minimum 2, maximum 4, and CPU target 60%. Standard CloudWatch metrics and scaling cooldowns mean changes are not instantaneous.

The included load generator sends only bounded requests to the public chatbot route and performs no account creation or writes. Use it solely against your own authorized deployment:

```powershell
.\.venv\Scripts\python.exe load_lab.py --base-url https://YOUR-HOSTNAME --seconds 120 --workers 5 --rps 10
```

Replace `YOUR-HOSTNAME` with your actual hostname. Expected: a JSON summary with request count, HTTP errors, and observed latency. Start at this modest rate, inspect metrics/costs, and stop with Ctrl+C if errors or unexpected costs appear.

If the service is healthy and your account owner permits a longer lab load, you can adjust duration up to 600 seconds and rate up to 100 requests/second. This built-in cap keeps the exercise bounded; the small chatbot route may never consume enough CPU to trigger scaling. **No scale-out under a low-CPU workload is inconclusive, not proof of broken scaling.** Do not keep increasing traffic indefinitely.

Capture an actual increase in desired/running task count only if it happens, then stop load and observe return toward the minimum after cooldown. Record failures, load level, and timing honestly. This is not a production capacity certification. PostgreSQL capacity is not automatically scaled by the ECS policy; raising application task count alone does not remove database bottlenecks.

## 10. Update the code later

1. Make changes and rerun the tests.
2. Build a new image/tag, for example `cloud-task-suite:2`.
3. Push it to the same ECR repository using a new immutable tag.
4. Get its digest as in Step 5.
5. CloudFormation → stack → **Update** → use the same template, change `ImageUri` to the new digest, and review the change set before execution.
6. Wait for successful rollout and repeat health/module checks.

Schema creation is intentionally simple, not a migration framework. A schema-changing update to a populated database needs a reviewed migration and backup/restore plan; `create_all` does not transform existing tables. Secrets must remain stable for old ciphertext and pass signatures to stay usable. Do not rotate the encryption secret by replacing it without a data re-encryption strategy.

## 11. Maintain fictional departures in AWS

After a day the seeded routes expire. To move fictional demo dates without deleting the database:

1. Open ECS → the stack's cluster → **Run task**.
2. Choose the same task definition/revision as the service, Fargate, and the same VPC/public subnets/application security group. Enable a public IP as in the service.
3. In container overrides, choose container `web` and replace its command with `python,manage.py,refresh-demo-departures` (use the console's command-list format).
4. Leave the initializer unchanged; its successful completion is still required.
5. Run one task, inspect its logs for `Demo departures moved to tomorrow`, and wait for it to stop.
6. Refresh routes in the app. Only do this for fictional demonstration bookings.

A one-off task incurs a small amount of additional runtime. Do not change the permanent web container command to the maintenance command.

## 12. Clean up charges when finished

Preserve any wanted evidence first. If you need to restore encrypted records later, preserve both the database snapshot and its matching encryption secret.

1. Confirm the exact lab stack name/account/region.
2. CloudFormation → `kaden-cloud-task-lab` → Delete → review and confirm.
3. Wait until deletion completes. Inspect failures if any rather than assuming cleanup succeeded.
4. The template intentionally retains the encryption secret and takes an RDS snapshot. **Both can continue to cost money.** Find them using the output ARN saved before deletion and the RDS Snapshots list. Keep them only if you need restoration; otherwise delete the lab snapshot and schedule deletion of the retained secret through the relevant console after confirming the data is disposable.
5. Delete the dedicated ECR repository/images if no longer needed; they were created outside the stack.
6. Remove the application DNS record. Keep ACM validation records/certificates only as appropriate for other uses; do not remove shared resources.
7. Check for remaining lab log groups, orphaned failed-stack resources, and ongoing charges in the billing console.
8. Domain registration/DNS charges are independent of stack deletion. Budgets do not remove resources.

This cleanup is intentionally manual so you can review what you are deleting. No cleanup command in the local setup deletes cloud resources automatically.
