# Primary references

Implementation decisions were checked against primary documentation available on 28 September 2026. Versions, account availability, interface labels, pricing, and supported platform details can change; recheck the relevant provider page when deploying.

- OWASP, [SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html): parameterized statements, restricted database access.
- OWASP, [Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html): one-way password hashing rather than reversible password storage.
- OWASP, [Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html): authenticated encryption and key management considerations.
- Cryptography, [AESGCM API](https://cryptography.io/en/latest/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM): AES-GCM and nonce handling.
- AWS, [ECS automatic service scaling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html) and [target tracking](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-autoscaling-targettracking.html).
- AWS, [ECS CloudFormation console workflow](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-cloudformation-console.html).
- AWS, [Pushing an image to ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html).
- AWS, [Using SSL with PostgreSQL RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html).
- AWS, [RDS public CA bundle](https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem), included under `cloud/global-bundle.pem`. This is a public trust bundle, not a private key.
- AWS, [Secrets Manager values in ECS environment variables](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/secrets-envvar-secrets-manager.html).
- Python, [Windows downloads](https://www.python.org/downloads/windows/).
- Playwright, [Library usage](https://playwright.dev/docs/library).

These references inform the design. They do not certify this application or replace its local and deployment tests.
