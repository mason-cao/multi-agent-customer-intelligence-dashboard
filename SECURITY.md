# Security Policy

## Supported Versions

This project is currently maintained as a single active codebase. Security fixes, when made, will be applied to the latest version on the `main` branch.

| Version | Supported |
| ------- | --------- |
| main    | ✅        |
| older commits / branches | ❌ |
| pre-release / experimental branches | ❌ |

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not open a public GitHub issue**.

Instead, report it privately by using one of these options:

- **GitHub Security Advisories** (preferred), if enabled for this repository
- Email the project maintainer directly

When reporting a vulnerability, please include:

- a clear description of the issue
- affected files, routes, or components
- steps to reproduce the problem
- potential impact
- screenshots, logs, or proof-of-concept details if relevant
- any suggested mitigation, if known

## What to Expect

After a report is received:

1. The maintainer will review the report and confirm whether it can be reproduced.
2. The maintainer will respond as soon as reasonably possible.
3. If the issue is confirmed, a fix will be prioritized and status updates will be shared when practical.
4. If the report is not accepted as a security issue, the maintainer will explain why when possible.

There is **no guaranteed response-time SLA**, but good-faith reports are appreciated and will be taken seriously.

## Scope

Examples of issues that may be considered security-related include:

- authentication or authorization bypass
- workspace token bypass or token leakage
- sensitive data exposure
- unsafe query execution
- injection vulnerabilities
- insecure file handling
- critical dependency vulnerabilities with real impact

Examples of issues that are usually **not** treated as security vulnerabilities for this project include:

- general bug reports
- UI/UX issues
- feature requests
- minor misconfigurations with no realistic security impact
- issues only affecting local development with no meaningful exploit path

## Disclosure Policy

Please allow time for the issue to be investigated and fixed before making any public disclosure.

Once a fix is available, the vulnerability may be documented publicly in a release note, commit message, or repository advisory, as appropriate.
