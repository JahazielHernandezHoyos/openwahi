# Security policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report vulnerabilities privately through GitHub: go to the repository's **Security** tab and choose **Report a vulnerability** (GitHub private security advisories). Include:

- affected component (backend, frontend, widget, transcriber, compose setup) and version or commit;
- steps to reproduce or a proof of concept;
- the impact you expect.

We will acknowledge the report, investigate, and coordinate a fix and disclosure with you through the advisory.

## Supported versions

Security fixes are made on the `main` branch. Self-hosters should track the latest release.

## Operator responsibilities

openwahi is self-hosted: you are responsible for your deployment's secrets (`AI_ENCRYPTION_KEY`, database, storage and gateway passwords, the Firebase service account), TLS termination, backups, and keeping container images up to date.
