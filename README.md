# 🛡️ GigKavach: Zero-Touch Parametric Income Protection

---

## 📋 Table of Contents
1. [🧠 Project Overview](#-1-project-title--description)
2. [🛠 Tech Stack](#-2-tech-stack)
3. [🌐 Live Demo (AWS EC2)](#-3-live-demo-aws-ec2)
4. [🎥 Demo Video](#-4-demo-video)
5. [📸 Screenshots](#-5-screenshots)
6. [🚀 One-Command Setup](#-6-one-command-setup-master-suite)
7. [🧩 Local Setup (Failsafe)](#-7-local-setup-failsafe)
8. [🧪 API Endpoints](#-8-api-endpoints)
9. [🧱 Project Structure](#-9-project-structure)
10. [✨ Key Features](#-10-key-features)
11. [⚠️ Troubleshooting](#-11-troubleshooting)
12. [👥 Team Details](#-12-team-details)

---

## 🧠 1. Project Title + Description

# 🚀 GigKavach

**GigKavach** is an AI-powered parametric income protection platform designed for India's 10M+ gig workers (Zomato/Swiggy partners).

- **The Problem**: External disruptions (heavy rain, heatwaves, traffic gridlocks) can wipe out 20-30% of a worker's monthly income. Traditional insurance is too slow and complex.
- **The Solution**: We automatically detect disruption events using a real-time **Disruption Composite Index (DCI)** at the pin-code level. 
- **The Magic**: If the DCI crosses a threshold, payouts are calculated via **XGBoost ML** and sent to the worker's UPI by midnight — **zero claims required.**

---

## 🛠 2. Tech Stack

**Frontend:**
- React 19 (Vite), TypeScript, Tailwind CSS.
- Leaflet.js (Maps), Recharts (Charts)

**Backend (Python):**
- FastAPI, Uvicorn, Pydantic, APScheduler
- PostgreSQL (psycopg2), Redis (Mock/Caching)

**AI/ML:**
- XGBoost v3 (Adaptive Multiplier), Scikit-learn (Isolation Forest), HuggingFace NLP

**Infrastructure & Integrations:**
- **Cloud**: AWS EC2 (Ubuntu 24.04 LTS)
- **Messaging**: Twilio (WhatsApp/Node.js)
- **Payments**: Razorpay (UPI Payouts)
- **Data**: Tomorrow.io (Weather), AQICN (Air Quality), OpenStreetMap

---

## 🌐 3. Live Demo (AWS EC2)

The entire GigKavach ecosystem is hosted on a unified **AWS EC2 Production Server**.

- **🎨 Frontend Dashboard**: [http://13.51.165.52:3000](http://13.51.165.52:3000)
- **🐍 Backend API Docs**: [http://13.51.165.52:8000/docs](http://13.51.165.52:8000/docs)
- **📱 WhatsApp Bot**: Port 3001 (Internal Communication)
- To chat with our agent send `HELP` to `+91 8792525542`

---

## 🎥 4. Demo Video

[Click here to watch the full GigKavach walkthrough](https://1drv.ms/v/c/7bd7439be05079b7/IQDJxlimakBJQKvXDtoXzXlvAb_rSXevm4Kt59nV4PIHC6E?e=PCydFh)

---

## 📸 5. Screenshots

### 📊 Admin Dashboard
![Dashboard](./screenshots/dashboard.png)

### 🗺️ Live Disruption Heatmap
![Heatmap](./screenshots/heatmap.png)

---

## 🚀 6. One-Command Setup (Master Suite)

The easiest way to launch the **Frontend**, **Backend**, and **WhatsApp Bot** simultaneously on a Linux/Mac environment.

```bash
# 🛡️ Launch the entire GigKavach ecosystem
chmod +x startup_suite.sh
./startup_suite.sh
```
*Note: This script backgrounds the engines and presents the WhatsApp QR code directly in your terminal for immediate scanning.* 🤳✨

---

## 🧩 7. Local Setup (Detailed Guide)

### 🐍 Step 1: Backend (Python/FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### ⚛️ Step 2: Frontend (React)
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

### 📱 Step 3: WhatsApp Bot (Node.js)
```bash
cd whatsapp-bot
npm install
node bot.js
```

---

## 🧪 8. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health/` | Liveness health check (System Pulse) |
| `POST` | `/api/v1/workers/register` | WhatsApp Onboarding endpoint |
| `GET` | `/api/v1/dci/{pincode}` | Get real-time Disruption Index |
| `POST` | `/api/v1/payouts/calculate` | XGBoost Payout & Adaptive Multiplier |
| `POST` | `/api/v1/fraud/check` | ML-based Fraud Detection (XGBoost v3) |
| `POST` | `/api/v1/demo/trigger` | Trigger manual demo disruption (Judge Mode) |

---

## 🏗️ 9. DCI 5-Layer Redundancy
The **Disruption Composite Index (DCI)** is built for zero-downtime:
1. **Layer 1 (Live APIs)**: Direct Tomorrow.io & WAQI polling.
2. **Layer 2 (Backup Mocks)**: Automatic fallback if primary APIs rate-limit.
3. **Layer 3 (Social Intelligence)**: NLP extraction from RSS & NDMA feeds.
4. **Layer 4 (Platform Density)**: Real-time driver congestion data.
5. **Layer 5 (Redis Cache)**: Last-known-good state for offline resilience.

---

## ✨ 10. Key Features

| 🎯 | Feature | Description |
|----|---------|-------------|
| 🚨 | **DCI Score** | 5-factor risk scoring updated every 300s at pincode-level. |
| ⚡ | **Zero-Touch Payouts** | Disruption detected → Eligibility verified → Payout automted. |
| 💰 | **Smart Baseline** | AI-driven 4-week rolling median for fair earnings calculation. |
| 🧠 | **XGBoost v3 Fraud** | Detects location spoofing & device farming with 31+ features. |
| 🎮 | **Judge Console** | Simulation panel on dashboard to trigger disruptions in seconds. |

---

## ⚠️ 11. Troubleshooting

- **Port in use**: Run `pkill -f uvicorn` or `pkill -f vite` to clear old processes.
- **Logs**: Monitor everything in real-time with `tail -f backend/backend.log` 🐍.
- **WhatsApp QR**: Scan the code printed in the terminal after running `./startup_suite.sh`.

---

## 👥 12. Team Details

**Team Quadcore:**
- **Varshit**: WhatsApp & API Integration Lead
- **Vijeth**: Frontend & Dashboard Design
- **V Saatwik**: ML Models & Fraud Detection Lead
- **Sumukh Shandilya**: Backend & DCI Engine Architect
