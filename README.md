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
- [ ] Mobile app
- [ ] Integration with local lab providers
- [ ] Latin America expansion

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

> *Built with ❤️ and Claude Code*
