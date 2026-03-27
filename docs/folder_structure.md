# GigKavach Phase 2 — Complete Folder Structure

```
gigkavach/
│
├── README.md                          # Main project documentation with setup instructions
├── .gitignore                         # Git ignore file (node_modules, .env, __pycache__, etc.)
├── LICENSE                            # MIT or Apache 2.0 license
├── requirements.txt                   # Python dependencies (FastAPI, scikit-learn, etc.)
├── package.json                       # Node.js dependencies for frontend
│
├── .env.example                       # Example environment variables (no secrets)
├── .env                               # Actual environment variables (GITIGNORED)
│
├── docker-compose.yml                 # Optional: Docker setup for local development
├── render.yaml                        # Render deployment configuration
├── vercel.json                        # Vercel deployment configuration
│
├── backend/                           # FastAPI backend application
│   ├── main.py                        # Entry point - FastAPI app initialization
│   ├── __init__.py
│   │
│   ├── api/                           # API route handlers
│   │   ├── __init__.py
│   │   ├── workers.py                 # Worker registration, profile management endpoints
│   │   ├── policies.py                # Policy CRUD, tier updates, coverage status
│   │   ├── dci.py                     # DCI status endpoint, component breakdown
│   │   ├── payouts.py                 # Payout calculation, execution, history
│   │   ├── fraud.py                   # Fraud detection, flag management, appeals
│   │   ├── whatsapp.py                # WhatsApp webhook handler, message routing
│   │   └── health.py                  # Health check, system status endpoints
│   │
│   ├── models/                        # Pydantic models for request/response validation
│   │   ├── __init__.py
│   │   ├── worker.py                  # Worker registration, profile schemas
│   │   ├── policy.py                  # Policy creation, update schemas
│   │   ├── payout.py                  # Payout request, response schemas
│   │   ├── dci.py                     # DCI score, component breakdown schemas
│   │   └── fraud.py                   # Fraud score, signal breakdown schemas
│   │
│   ├── services/                      # Business logic layer
│   │   ├── __init__.py
│   │   ├── dci_engine.py              # DCI composite score calculation, caching
│   │   ├── weather_service.py         # Tomorrow.io, Open-Meteo integration, fallback
│   │   ├── aqi_service.py             # AQICN, CPCB integration, caching
│   │   ├── social_service.py          # RSS parsing, NLP classification
│   │   ├── payout_service.py          # Payout calculation logic, XGBoost inference
│   │   ├── fraud_service.py           # Fraud scoring, tier assignment, GPS validation
│   │   ├── eligibility_service.py     # Worker eligibility checks, shift matching
│   │   ├── whatsapp_service.py        # WhatsApp message sending, template rendering
│   │   ├── payment_service.py         # Razorpay integration, UPI payouts
│   │   └── baseline_service.py        # Earnings fingerprint calculation
│   │
│   ├── ml/                            # Machine learning models and utilities
│   │   ├── __init__.py
│   │   ├── xgboost_payout.py          # XGBoost payout model training & inference
│   │   ├── isolation_forest.py        # Fraud detection model training & inference
│   │   ├── earnings_fingerprint.py    # Baseline earnings calculation logic
│   │   ├── nlp_classifier.py          # HuggingFace social disruption classifier
│   │   └── feature_engineering.py     # Feature extraction for ML models
│   │
│   ├── utils/                         # Utility functions
│   │   ├── __init__.py
│   │   ├── redis_client.py            # Redis connection, caching utilities
│   │   ├── supabase_client.py         # Supabase connection, query helpers
│   │   ├── validators.py              # Input validation (UPI, phone, pin code)
│   │   ├── datetime_utils.py          # Timezone handling, shift window checks
│   │   ├── geocoding.py               # Pin code to lat/lng, zone mapping
│   │   └── logger.py                  # Logging configuration
│   │
│   ├── database/                      # Database schemas and migrations
│   │   ├── schema.sql                 # Complete database schema (8 tables)
│   │   ├── seed.sql                   # Test data seeding script
│   │   └── migrations/                # Future: Database migration scripts
│   │       └── .gitkeep
│   │
│   ├── config/                        # Configuration files
│   │   ├── __init__.py
│   │   ├── settings.py                # App settings, env variable loading
│   │   ├── constants.py               # Constants (DCI weights, thresholds, tiers)
│   │   └── api_keys.py                # API key management (loads from .env)
│   │
│   ├── cron/                          # Background jobs and schedulers
│   │   ├── __init__.py
│   │   ├── claims_trigger.py          # Every 5 min: Check DCI, trigger eligible payouts
│   │   ├── dci_poller.py              # Every 5 min: Poll weather/AQI APIs, compute DCI
│   │   ├── rss_parser.py              # Every 30 min: Parse RSS feeds for social disruption
│   │   └── scheduler.py               # APScheduler configuration
│   │
│   └── tests/                         # Backend unit and integration tests
│       ├── __init__.py
│       ├── test_dci_engine.py         # DCI calculation tests
│       ├── test_payout_service.py     # Payout calculation tests
│       ├── test_fraud_detection.py    # Fraud scoring tests
│       ├── test_eligibility.py        # Eligibility check tests
│       └── test_api_endpoints.py      # API endpoint integration tests
│
├── frontend/                          # React frontend application
│   ├── index.html                     # HTML entry point
│   ├── vite.config.js                 # Vite build configuration
│   ├── tailwind.config.js             # TailwindCSS configuration
│   ├── postcss.config.js              # PostCSS configuration
│   │
│   ├── public/                        # Static assets
│   │   ├── favicon.ico
│   │   ├── logo.png
│   │   ├── manifest.json              # PWA manifest for worker interface
│   │   └── robots.txt
│   │
│   ├── src/                           # React source code
│   │   ├── main.jsx                   # React app entry point
│   │   ├── App.jsx                    # Root component with routing
│   │   ├── index.css                  # Global styles and Tailwind imports
│   │   │
│   │   ├── components/                # Reusable UI components
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.jsx        # Dashboard sidebar navigation
│   │   │   │   ├── Header.jsx         # Dashboard header with search
│   │   │   │   └── Layout.jsx         # Main layout wrapper
│   │   │   │
│   │   │   ├── workers/
│   │   │   │   ├── WorkerTable.jsx    # Worker list table with filters
│   │   │   │   ├── WorkerCard.jsx     # Individual worker card
│   │   │   │   ├── WorkerModal.jsx    # Worker detail modal
│   │   │   │   └── WorkerFilters.jsx  # Filter controls for worker list
│   │   │   │
│   │   │   ├── dci/
│   │   │   │   ├── DCIHeatmap.jsx     # Leaflet.js heatmap component
│   │   │   │   ├── DCIBreakdown.jsx   # DCI score component breakdown
│   │   │   │   ├── DCIChart.jsx       # Historical DCI chart (24 hours)
│   │   │   │   └── ForecastOverlay.jsx # 24-hour DCI forecast layer
│   │   │   │
│   │   │   ├── payouts/
│   │   │   │   ├── PayoutFeed.jsx     # Real-time payout feed
│   │   │   │   ├── PayoutCard.jsx     # Individual payout card with breakdown
│   │   │   │   ├── PayoutHistory.jsx  # Payout history table
│   │   │   │   └── PayoutStats.jsx    # Aggregate payout statistics
│   │   │   │
│   │   │   ├── fraud/
│   │   │   │   ├── FraudTable.jsx     # Flagged claims table
│   │   │   │   ├── FraudScoreCard.jsx # Fraud score breakdown card
│   │   │   │   ├── SignalIndicator.jsx # Individual signal status indicator
│   │   │   │   └── TierBadge.jsx      # Tier 1/2/3 visual badge
│   │   │   │
│   │   │   ├── policies/
│   │   │   │   ├── PolicyForm.jsx     # Policy edit form
│   │   │   │   ├── PolicyCard.jsx     # Policy status card
│   │   │   │   └── TierSelector.jsx   # Plan tier selection component
│   │   │   │
│   │   │   └── common/
│   │   │       ├── Button.jsx         # Reusable button component
│   │   │       ├── Input.jsx          # Reusable input component
│   │   │       ├── Modal.jsx          # Generic modal wrapper
│   │   │       ├── LoadingSpinner.jsx # Loading state component
│   │   │       ├── Toast.jsx          # Toast notification component
│   │   │       └── Badge.jsx          # Status badge component
│   │   │
│   │   ├── pages/                     # Page components (routes)
│   │   │   ├── Dashboard.jsx          # Main dashboard with stats overview
│   │   │   ├── Workers.jsx            # Workers list and management page
│   │   │   ├── LiveMap.jsx            # Full-screen DCI heatmap page
│   │   │   ├── Payouts.jsx            # Payouts management page
│   │   │   ├── Fraud.jsx              # Fraud detection dashboard page
│   │   │   ├── Settings.jsx           # System settings page
│   │   │   │
│   │   │   └── worker-pwa/            # Worker-facing PWA pages
│   │   │       ├── Status.jsx         # Worker status page (DCI, coverage)
│   │   │       ├── History.jsx        # Payout history for worker
│   │   │       └── Profile.jsx        # Worker profile edit page
│   │   │
│   │   ├── hooks/                     # Custom React hooks
│   │   │   ├── useWebSocket.js        # WebSocket hook for real-time updates
│   │   │   ├── usePolling.js          # Polling hook (auto-refresh every N seconds)
│   │   │   ├── useApi.js              # API call wrapper with error handling
│   │   │   └── useLocalStorage.js     # LocalStorage persistence hook
│   │   │
│   │   ├── api/                       # API client functions
│   │   │   ├── client.js              # Axios configuration, base URL, interceptors
│   │   │   ├── workers.js             # Worker API calls (GET, POST, PATCH)
│   │   │   ├── policies.js            # Policy API calls
│   │   │   ├── dci.js                 # DCI API calls
│   │   │   ├── payouts.js             # Payout API calls
│   │   │   └── fraud.js               # Fraud API calls
│   │   │
│   │   ├── utils/                     # Frontend utilities
│   │   │   ├── formatters.js          # Date, currency, number formatters
│   │   │   ├── validators.js          # Client-side form validation
│   │   │   ├── constants.js           # Frontend constants (API URLs, colors)
│   │   │   └── helpers.js             # Miscellaneous helper functions
│   │   │
│   │   └── assets/                    # Images, icons, fonts
│   │       ├── icons/
│   │       ├── images/
│   │       └── fonts/
│   │
│   └── tests/                         # Frontend tests (optional for Phase 2)
│       └── .gitkeep
│
├── models/                            # Trained ML model artifacts
│   ├── v1/
│   │   ├── xgboost_payout_v1.pkl      # Trained XGBoost model for payout calculation
│   │   ├── xgboost_metadata.json      # Model metadata (features, performance)
│   │   ├── isolation_forest_fraud_v1.pkl # Trained Isolation Forest fraud model
│   │   └── fraud_metadata.json        # Fraud model metadata
│   │
│   └── README.md                      # Model versioning documentation
│
├── data/                              # Data files for training and reference
│   ├── synthetic_workers.csv          # Generated synthetic training data (500 workers × 30 days)
│   ├── processed/                     # Processed data for ML training
│   │   ├── train_features.csv         # Training features for XGBoost
│   │   ├── test_features.csv          # Test features
│   │   └── fraud_train.csv            # Fraud detection training data
│   │
│   ├── messages.json                  # Multilingual message templates (5 languages)
│   ├── pin_codes_karnataka.json       # Karnataka pin code to lat/lng mapping
│   ├── zones_geojson.json             # Karnataka zones GeoJSON for heatmap
│   │
│   └── README.md                      # Data source documentation
│
├── scripts/                           # Utility scripts
│   ├── generate_synthetic_data.py     # Script to generate synthetic worker data
│   ├── train_xgboost.py               # Script to train XGBoost payout model
│   ├── train_fraud_model.py           # Script to train Isolation Forest model
│   ├── seed_database.py               # Script to seed database with test data
│   ├── test_apis.py                   # Script to test all external API integrations
│   ├── export_messages.py             # Script to export/import multilingual messages
│   └── migrate_database.py            # Database migration runner
│
├── docs/                              # Documentation
│   ├── API.md                         # API endpoint documentation
│   ├── ARCHITECTURE.md                # System architecture overview
│   ├── DATABASE_SCHEMA.md             # Database schema documentation
│   ├── ML_MODELS.md                   # ML model documentation
│   ├── DEPLOYMENT.md                  # Deployment instructions (Render, Vercel)
│   ├── WHATSAPP_FLOW.md               # WhatsApp conversation flow documentation
│   ├── DCI_CALCULATION.md             # DCI formula and component explanation
│   ├── FRAUD_DETECTION.md             # Fraud detection architecture
│   ├── EDGE_CASES.md                  # 27 edge cases documentation
│   ├── API_INTEGRATIONS.md            # External API integration details
│   │
│   ├── diagrams/                      # Architecture diagrams
│   │   ├── system_architecture.png
│   │   ├── dci_engine_flow.png
│   │   ├── payout_pipeline.png
│   │   └── fraud_detection_flow.png
│   │
│   └── screenshots/                   # UI screenshots for documentation
│       ├── dashboard.png
│       ├── heatmap.png
│       ├── worker_modal.png
│       └── whatsapp_conversation.png
│
├── tests/                             # Integration and E2E tests
│   ├── api_tests.json                 # Postman/Thunder Client collection
│   ├── fraud_test_results.md          # Fraud detection test results
│   └── e2e_test_scenarios.md          # End-to-end test scenarios
│
├── demo/                              # Demo materials for submission
│   ├── script.txt                     # Demo video narration script
│   ├── gigkavach_phase2_demo.mp4      # Final demo video (2 minutes)
│   ├── voiceover.mp3                  # Recorded voiceover audio
│   │
│   ├── recordings/                    # Raw screen recordings
│   │   ├── backend_demo.mp4           # Backend API demonstration
│   │   ├── frontend_demo.mp4          # Dashboard demonstration
│   │   ├── whatsapp_demo.mp4          # WhatsApp flow demonstration
│   │   └── ml_demo.mp4                # ML model demonstration
│   │
│   └── assets/                        # Demo assets (thumbnails, overlays)
│       ├── thumbnail.png
│       └── title_overlay.png
│
└── logs/                              # Application logs (GITIGNORED)
    ├── app.log                        # General application logs
    ├── dci_engine.log                 # DCI calculation logs
    ├── payout.log                     # Payout execution logs
    ├── fraud.log                      # Fraud detection logs
    └── api_calls.log                  # External API call logs
```

---

## 📁 Detailed File Descriptions

### **Root Level Files**

| File | Purpose | What Goes Here |
|------|---------|----------------|
| `README.md` | Main project documentation | Project overview, setup instructions, API documentation, demo links, team info |
| `.gitignore` | Git ignore rules | `node_modules/`, `.env`, `__pycache__/`, `*.pyc`, `logs/`, `.DS_Store`, `dist/`, `build/` |
| `LICENSE` | Software license | MIT or Apache 2.0 license text |
| `requirements.txt` | Python dependencies | `fastapi`, `uvicorn`, `supabase`, `redis`, `scikit-learn`, `xgboost`, `transformers`, `twilio`, `razorpay`, `requests`, `python-dotenv`, `pandas`, `numpy` |
| `package.json` | Node.js dependencies | `react`, `react-dom`, `react-router-dom`, `axios`, `leaflet`, `react-leaflet`, `tailwindcss`, `vite` |
| `.env.example` | Example environment variables | Template showing all required env vars (no actual secrets) |
| `.env` | Actual secrets (GITIGNORED) | `SUPABASE_URL`, `SUPABASE_KEY`, `REDIS_URL`, `TWILIO_SID`, `TWILIO_TOKEN`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `TOMORROW_IO_KEY`, etc. |

---

### **Backend Structure**

#### **`backend/api/`** — API Route Handlers
Each file defines FastAPI router with related endpoints:

- **`workers.py`**: `POST /api/register`, `GET /api/workers`, `GET /api/worker/:id`, `PATCH /api/worker/:id`
- **`policies.py`**: `GET /api/policy/:id`, `PATCH /api/policy/:id`, `POST /api/policy/renew`
- **`dci.py`**: `GET /api/dci/:pincode`, `GET /api/dci/history/:pincode`
- **`payouts.py`**: `POST /api/calculate_payout`, `POST /api/payout`, `GET /api/payouts`, `GET /api/payout/:id`
- **`fraud.py`**: `POST /api/fraud/score`, `GET /api/fraud/flags`, `POST /api/fraud/appeal`
- **`whatsapp.py`**: `POST /api/whatsapp/webhook` (Twilio webhook handler)
- **`health.py`**: `GET /api/health`, `GET /api/status`

#### **`backend/services/`** — Business Logic
Core logic separated from API handlers for testability:

- **`dci_engine.py`**: Main DCI calculation — aggregates all 5 components, applies weights, returns score 0-100
- **`weather_service.py`**: Fetches rainfall/temperature from Tomorrow.io → Open-Meteo fallback → Redis cache → IMD RSS
- **`aqi_service.py`**: Fetches AQI from AQICN → CPCB fallback
- **`social_service.py`**: Parses RSS feeds, runs HuggingFace NLP classifier, extracts zones, updates DCI
- **`payout_service.py`**: Loads XGBoost model, calculates payout based on baseline, DCI score, disruption duration
- **`fraud_service.py`**: Calculates fraud score (0-6 signals), assigns tier, validates GPS
- **`eligibility_service.py`**: Checks if worker qualifies for payout (active policy, shift match, coverage delay)
- **`whatsapp_service.py`**: Sends messages via Twilio, handles language selection, formats templates
- **`payment_service.py`**: Razorpay integration, initiates UPI payouts, handles callbacks
- **`baseline_service.py`**: Calculates worker's expected daily earnings using 4-week rolling median

#### **`backend/ml/`** — Machine Learning
Model training and inference code:

- **`xgboost_payout.py`**: Train XGBoost on synthetic data, save model, inference function
- **`isolation_forest.py`**: Train fraud detection model, anomaly scoring function
- **`earnings_fingerprint.py`**: Baseline calculation logic (4-week median, city blending for new workers)
- **`nlp_classifier.py`**: HuggingFace zero-shot classifier for social disruption detection
- **`feature_engineering.py`**: Feature extraction and preprocessing for both models

#### **`backend/database/`** — Database Schema
- **`schema.sql`**: CREATE TABLE statements for all 8 tables (workers, policies, payouts, dci_logs, fraud_flags, activity_log, premium_payments, disruption_events)
- **`seed.sql`**: INSERT statements for 5 test workers with sample data

#### **`backend/cron/`** — Background Jobs
- **`claims_trigger.py`**: Runs every 5 minutes, queries DCI >= 65, triggers eligible payouts
- **`dci_poller.py`**: Runs every 5 minutes, polls all APIs, computes DCI, caches results
- **`rss_parser.py`**: Runs every 30 minutes, fetches RSS, classifies headlines, updates social component
- **`scheduler.py`**: APScheduler configuration to run all cron jobs

---

### **Frontend Structure**

#### **`frontend/src/components/`** — Reusable Components
Organized by feature domain:

- **`layout/`**: Sidebar, Header, Layout wrapper
- **`workers/`**: Worker table, cards, filters, modal
- **`dci/`**: Heatmap, breakdown chart, forecast overlay
- **`payouts/`**: Live feed, payout cards, history table, stats
- **`fraud/`**: Fraud table, score breakdown, signal indicators, tier badges
- **`policies/`**: Policy form, tier selector
- **`common/`**: Generic reusable components (Button, Input, Modal, Toast, Badge, Spinner)

#### **`frontend/src/pages/`** — Page Components
One component per route:

- **`Dashboard.jsx`**: Overview with stats cards, recent payouts, active disruptions
- **`Workers.jsx`**: Full worker management page with table and filters
- **`LiveMap.jsx`**: Full-screen DCI heatmap with forecast overlay
- **`Payouts.jsx`**: Payout management dashboard
- **`Fraud.jsx`**: Fraud detection monitoring dashboard
- **`worker-pwa/`**: Mobile-first worker interface (Status, History, Profile pages)

#### **`frontend/src/api/`** — API Client
Axios-based API calls organized by domain:

- **`client.js`**: Base Axios configuration with interceptors (auth, error handling)
- **`workers.js`**: `fetchWorkers()`, `fetchWorkerById()`, `updateWorker()`
- **`dci.js`**: `fetchDCIByPincode()`, `fetchDCIHistory()`
- **`payouts.js`**: `fetchPayouts()`, `calculatePayout()`, `executeP ayout()`

---

### **Models Directory**

Store trained ML models with versioning:

```
models/
└── v1/
    ├── xgboost_payout_v1.pkl          # Pickled XGBoost model
    ├── xgboost_metadata.json          # {"features": [...], "performance": {"mae": 45, "r2": 0.89}, "training_date": "2025-03-29"}
    ├── isolation_forest_fraud_v1.pkl  # Pickled Isolation Forest model
    └── fraud_metadata.json            # {"contamination": 0.05, "precision": 0.92, "training_date": "2025-03-31"}
```

**Why versioning?** When you retrain models, save as `v2/`, keep old versions for rollback.

---

### **Data Directory**

All data files for training and reference:

- **`synthetic_workers.csv`**: Generated by `scripts/generate_synthetic_data.py`. Columns: `worker_id`, `date`, `earnings`, `dci_score`, `disruption_type`, `shift`, `zone`
- **`messages.json`**: 
```json
{
  "onboarding_welcome": {
    "en": "Welcome to GigKavach! Choose your language:",
    "hi": "गिगकवच में आपका स्वागत है! अपनी भाषा चुनें:",
    "kn": "ಗಿಗ್‌ಕವಾಚ್‌ಗೆ ಸ್ವಾಗತ! ನಿಮ್ಮ ಭಾಷೆಯನ್ನು ಆರಿಸಿ:",
    "ta": "GigKavach-க்கு வரவேற்கிறோம்! உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்:",
    "te": "GigKavach కి స్వాగతం! మీ భాషను ఎంచుకోండి:"
  },
  "disruption_alert": {
    "en": "Disruption detected in your zone (DCI: {dci_score}). Your coverage is active.",
    "hi": "आपके ज़ोन में रुकावट डिटेक्ट हुई (DCI: {dci_score})। आपका कवरेज सक्रिय है।",
    ...
  }
}
```
- **`pin_codes_karnataka.json`**: Mapping of Karnataka pin codes to lat/lng coordinates
- **`zones_geojson.json`**: GeoJSON file for Karnataka zones to render on Leaflet map

---

### **Scripts Directory**

Standalone utility scripts:

- **`generate_synthetic_data.py`**: 
```python
# Generates 500 workers × 30 days of synthetic earnings data
# Includes realistic disruption events (rain, AQI, heat)
# Saves to data/synthetic_workers.csv
```
- **`train_xgboost.py`**: Loads `synthetic_workers.csv`, trains XGBoost, saves to `models/v1/`
- **`train_fraud_model.py`**: Trains Isolation Forest on synthetic fraud data
- **`seed_database.py`**: Runs `database/seed.sql` to populate Supabase with test data
- **`test_apis.py`**: Tests all external APIs (Tomorrow.io, AQICN, etc.) and logs results

---

### **Documentation Directory**

Comprehensive documentation for the project:

- **`API.md`**: All API endpoints with request/response examples, curl commands
- **`ARCHITECTURE.md`**: System architecture diagram, component interaction, data flow
- **`DATABASE_SCHEMA.md`**: Full schema with table descriptions, relationships, indexes
- **`ML_MODELS.md`**: Model architectures, features, training process, performance metrics
- **`DEPLOYMENT.md`**: Step-by-step deployment to Render (backend) and Vercel (frontend)
- **`WHATSAPP_FLOW.md`**: Complete WhatsApp conversation flow with screenshots
- **`DCI_CALCULATION.md`**: DCI formula breakdown, component weights, severity tiers
- **`FRAUD_DETECTION.md`**: 6 fraud signals, 3-tier penalization logic, appeal process
- **`EDGE_CASES.md`**: All 27 edge cases with handling logic (e.g., multi-day disasters, same-day registration, night shift workers)

---

### **Demo Directory**

All materials for the 2-minute demo video:

- **`script.txt`**: Word-for-word narration script (120-150 words per minute = ~250-300 words total)
- **`gigkavach_phase2_demo.mp4`**: Final edited video (under 2 minutes, 1080p)
- **`voiceover.mp3`**: Recorded narration audio
- **`recordings/`**: Raw screen captures before editing
  - `backend_demo.mp4`: Postman API calls, logs, DCI engine running
  - `frontend_demo.mp4`: Dashboard interactions, heatmap, payout cards
  - `whatsapp_demo.mp4`: Full onboarding conversation + alerts
  - `ml_demo.mp4`: Jupyter notebook showing model training

---

## 🎯 Key Principles

1. **Separation of Concerns**: API routes → Services → Database. Never write business logic in route handlers.

2. **Environment Variables**: ALL secrets in `.env` (never commit). Use `.env.example` as template.

3. **Versioning**: Models in `models/v1/`, `v2/`, etc. Easy rollback if new model underperforms.

4. **Testing**: Unit tests alongside code (`backend/tests/`, `frontend/tests/`). Integration tests in root `tests/`.

5. **Documentation**: Every complex function has docstring. Every API endpoint documented in `docs/API.md`.

6. **Logging**: Structured logging to separate files (`logs/dci_engine.log`, `logs/fraud.log`). NEVER commit logs (`.gitignore`).

7. **Data Privacy**: No real user data in repo. Only synthetic data for ML training.

---

## 🚀 Quick Start After Setup

```bash
# 1. Clone and install
git clone https://github.com/VG2476/DEVTrails.git
cd gigkavach
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. Setup environment
cp .env.example .env
# Fill in all API keys in .env

# 3. Setup database
python scripts/seed_database.py

# 4. Run backend
cd backend
uvicorn main:app --reload --port 3000

# 5. Run frontend (new terminal)
cd frontend
npm run dev

# 6. Access
# Backend: http://localhost:3000
# Frontend: http://localhost:5173
# API Docs: http://localhost:3000/docs
```

---

This folder structure is production-ready, scalable, and follows industry best practices. Each directory has a clear purpose, making it easy for new developers to navigate the codebase.