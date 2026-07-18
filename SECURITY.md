# Security Policy

## Supported Versions

Only the latest released version is supported with security fixes.

| Version | Supported |
| ------- | --------- |
| 1.3.x   | ✅        |
| < 1.3   | ❌        |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
privately rather than opening a public GitHub issue.

- Email: tkipper@epiphan.com
- Or use [GitHub's private vulnerability reporting](https://github.com/ScientiaCapital/epiphan-mcp-server/security/advisories/new)

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce (a minimal repro is ideal)
- Any relevant logs or configuration (redact credentials/IPs)

We aim to acknowledge reports within 5 business days and to ship a fix or
mitigation as soon as practical, depending on severity.

## Scope

This project handles Epiphan Pearl / EC20 device credentials and integration
API tokens (Panopto, Kaltura, Opencast, YuJa, Echo360, Q-SYS, YouTube, Epiphan
Cloud). Areas of particular interest for security reports:

- Credential handling and `.env` / `pydantic-settings` configuration
- SSRF and URL validation (`src/epiphan_mcp/validation.py`)
- Host/device identity validation (`src/epiphan_mcp/config.py`)
- Any path that accepts a user- or LLM-supplied URL or hostname

Dependency vulnerabilities in transitive packages should also be reported;
see `CHANGELOG.md` for known-CVE remediation history.
