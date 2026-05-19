# NephroAI Security and SOC 2 Readiness Brief

Date: 2026-05-19  
Audience: investors, strategic partners, institutional customers

## Summary

NephroAI is preparing for SOC 2 readiness with controls focused on Security, Availability, and Confidentiality. The product handles sensitive medical laboratory data, so the current priority is to prove that data access, deployment, auditability, backup, and operational monitoring are controlled.

This is not a SOC 2 report. A formal SOC 2 Type I or Type II report requires an independent auditor. This brief summarizes the controls already implemented and the remaining path to audit.

## Implemented Controls

- Private repository with CI/CD-based deployment path.
- Backend test suite covering authentication, patient/doctor authorization, consultation permissions, V2 documents, notes, and extraction logic.
- GitHub Actions gates: backend tests, frontend build, frontend dependency audit, Python dependency audit, Docker Compose validation, backend image build, and container vulnerability scan.
- Production deploy checks: required environment variables, non-default database password, JWT secret visibility, local health, local readiness, public health, public readiness, and security headers.
- Authentication controls: hashed passwords, email verification, password reset controls, JWT production secret requirement.
- Authorization controls: doctors can access patient data only through active patient grants.
- Audit logging: sensitive auth events, V2 document events, doctor patient reads, grant changes, notes, consultations, and calls.
- Health and readiness endpoints: liveness plus dependency readiness for database and Redis.
- Security headers in nginx: HSTS, nosniff, frame deny, referrer policy, permissions policy.
- Encrypted backup and restore scripts for PostgreSQL and uploaded files.
- SOC 2 readiness binder: architecture, threat model, evidence index, incident response, CI/CD, observability, backup/restore, and security policies.

## Remaining Work Before Formal Audit

- Run and record the first production encrypted backup.
- Run and record a restore test.
- Enable external uptime monitoring and alerting.
- Collect production evidence: TLS headers, readiness output, GitHub branch protection, GitHub Actions run, access list, server `docker compose ps`, backup manifest.
- Document vendor reviews for OpenAI, SMTP/Resend, LiveKit, GitHub, and hosting provider.
- Confirm encryption-at-rest evidence for production host disks/volumes or implement encrypted storage.
- Establish recurring access reviews and monthly vulnerability review records.

## Readiness Position

NephroAI is not claiming SOC 2 certification yet. The current posture is:

- Strong engineering readiness foundation.
- Initial security controls implemented in code and CI/CD.
- Evidence collection path defined.
- Non-secret production evidence can be collected with `ops/evidence/collect_evidence.sh`.
- Formal audit readiness dependent on production evidence, monitoring, backup/restore proof, and auditor engagement.

## Next Milestone

The next practical milestone is a customer/investor due diligence package:

- SOC 2 readiness binder.
- Security brief.
- Evidence folder with screenshots and command outputs.
- Security roadmap with owners and target dates.
- Production backup and monitoring proof.
