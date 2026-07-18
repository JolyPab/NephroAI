# 🩺 NephroAI

> **Intelligent platform for automated parsing, analysis, and visualization of medical laboratory reports.**

NephroAI transforms unstructured PDF lab results into interactive charts, tracking health metrics against reference ranges — bridging the gap between patients and their medical data.

---

## ✨ Features

- **PDF Parsing** — Automatically extracts lab values from unstructured medical PDF reports
- **Interactive Visualization** — Renders health metrics as dynamic charts with historical trends
- **Reference Range Tracking** — Highlights abnormal values against standard reference ranges
- **Patient Dashboard** — Patients can upload, track, and understand their own lab results over time
- **Doctor Dashboard** — Physicians can view patient data remotely with explicit patient permission
- **Doctor-Patient Interaction** — Secure access sharing between patients and their treating physicians

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Angular + TypeScript |
| Backend | Python (FastAPI) |
| Styling | SCSS |
| Infrastructure | Docker + Nginx |
| Database | PostgreSQL |

---

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- Node.js 18+
- Python 3.10+

### Run with Docker

```bash
git clone https://github.com/JolyPab/NephroAI.git
cd NephroAI
cp .env.example .env
docker-compose up --build
```

### Run locally

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
ng serve
```

### Optional calls setup

Doctor-patient video calls use LiveKit. Local Docker runs a self-hosted LiveKit server on `ws://localhost:7880` with the dev keypair from `livekit.yaml`.

```bash
docker compose up -d livekit
```

For production, put LiveKit behind TLS and override these variables:

```env
LIVEKIT_URL=wss://your-livekit-host
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
```

For local doctor registration tests, email delivery can be made non-blocking:

```env
SMTP_REQUIRE_DELIVERY=false
```

---

## 🌎 Mission

Kidney and metabolic diseases disproportionately affect populations in Latin America, where patients often lack accessible tools to understand their own medical data. NephroAI is built to change that — starting in Ecuador, expanding across Latin America and beyond.

We believe every patient deserves to understand their own health data, regardless of where they live.

---

## 📸 Screenshots

*Coming soon*

---

## 🗺️ Roadmap

- [x] PDF parsing engine
- [x] Interactive health charts
- [x] Patient & Doctor dashboards
- [x] Doctor-patient access sharing
- [x] Multi-language support (ES/EN)
- [ ] Complete and release the React Native mobile app
- [ ] Integration with local lab providers
- [x] Latin America expansion
=
---
## OpenAI Build Week

NephroAI was originally started before OpenAI Build Week and has continued to evolve during the event.

During Build Week, I used **Codex with GPT-5.6** as a core part of the engineering workflow to extend, review, test, and harden the project.

### How Codex was used

Codex was used across the repository for:

- Implementing and refining frontend and backend features
- Debugging application behavior across the Angular frontend and FastAPI backend
- Refactoring existing code and improving maintainability
- Writing and updating automated tests
- Reviewing architecture and data flows
- Performing repository-wide security analysis
- Identifying vulnerabilities and technical risks
- Planning and implementing remediation work
- Improving the React Native mobile application
- Reviewing privacy and biometric-lock behavior
- Preparing the repository and demo flow for judge testing

### How GPT-5.6 was used

GPT-5.6 powered the Codex sessions used for the Build Week development workflow.

It was used to reason about:

- Multi-file implementation tasks
- Backend and frontend integration
- Medical-data safety boundaries
- Authentication and authorization risks
- Privacy-sensitive mobile functionality
- Test failures and regression risks
- Security findings and remediation priorities
- Deployment and production-readiness improvements

The submitted `/feedback` Session ID corresponds to one of the primary Codex development sessions used during Build Week:

`019f551f-56a9-7393-b178-b310e7782f10`

### Pre-existing work

NephroAI existed before Build Week as a web-based platform for parsing and visualizing laboratory reports.

Earlier development involved manual engineering and multiple development tools. The Build Week submission highlights the substantial implementation, security, testing, mobile, and reliability work completed using Codex and GPT-5.6 during the event.

### Current submitted experience

The primary working product submitted for judging is the web application:

- Live application: https://app.nephroai.ec
- Landing page: https://nephroai.ec

A cross-platform React Native mobile application is also in active development but has not yet been released publicly.
## Security and Compliance

SOC 2 readiness materials and security architecture notes live in [`docs/compliance/`](docs/compliance/README.md).

---

## 🤝 Contributing

This project is in active pre-production development. Contributions, feedback, and issue reports are welcome!

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 👤 Author

**JolyPab** — Solo developer building healthcare tooling for Latin America.

> *Built and improved with Codex, GPT-5.6, and a lot of hands-on engineering.*
