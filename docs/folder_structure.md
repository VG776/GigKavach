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
├── .env.example                       # Example environment variables (no secrets) ✅ COMMITTED
├── .env                               # Actual environment variables (GITIGNORED) ⚠️ NEVER COMMIT
│
├── Dockerfile                         # Docker image for backend (optional, for local testing)
├── docker-compose.yml                 # Optional: Docker setup for local development
│
├── render.yaml                        # 🟢 Render deployment configuration (REQUIRED)
├── vercel.json                        # 🟢 Vercel deployment configuration (REQUIRED)
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
├── whatsapp-bot/                      # WhatsApp Bot Service (Node.js + whatsapp-web.js)
│   ├── package.json                   # Node.js dependencies (whatsapp-web.js, express, axios, etc.)
│   ├── .env.example                   # Environment template (BACKEND_URL, BOT_PORT, LOG_LEVEL)
│   ├── README.md                      # Complete setup guide, API docs, troubleshooting
│   │
│   ├── bot.js                         # Main WhatsApp client (300+ lines)
│   │                                  # - Initializes whatsapp-web.js WebSocket client
│   │                                  # - Handles QR code authentication with LocalAuth
│   │                                  # - Routes inbound messages to message-handler
│   │                                  # - Runs Express API server on port 3001
│   │                                  # - Graceful shutdown on SIGINT
│   │
│   ├── config/                        # Configuration files
│   │   ├── messages.json              # Multilingual message templates (5 languages: en, kn, hi, ta, te)
│   │   │                              # - 30+ messages (onboarding, alerts, payouts, errors, commands)
│   │   │                              # - Template substitution: {dci}, {amount}, {plan}, etc.
│   │   └── constants.js               # Constants (language codes, command names, API endpoints)
│   │
│   ├── services/                      # Core service layer
│   │   ├── session-manager.js         # Session persistence and user context management
│   │   │                              # - CRUD: getOrCreateSession(), updateSession(), nextStep()
│   │   │                              # - File-based persistence: ./data/sessions/{phone}.json
│   │   │                              # - User registry: ./data/users.json (phone → UUID lookup)
│   │   │                              # - Session schema: userId, language, onboardingStep, tempData, isOnboarded, workerData
│   │   │                              # - Handles 4-level directory creation for session files
│   │   │
│   │   └── message-handler.js         # Main message router based on command and session state
│   │                                  # - Routes commands (HELP, LANG, STATUS, RENEW, SHIFT, APPEAL)
│   │                                  # - Routes onboarding step progression
│   │                                  # - Calls appropriate handler based on current state
│   │                                  # - Provides localized message retrieval with template substitution
│   │
│   ├── handlers/                      # Business logic handlers for each workflow
│   │   ├── onboarding.js              # 7-step onboarding pipeline
│   │   │                              # - Step 1: Language selection (en, kn, hi, ta, te)
│   │   │                              # - Step 2: Platform selection (delivery, ride-sharing)
│   │   │                              # - Step 3: Shift selection (morning 6-12, afternoon 12-6, evening 6-12)
│   │   │                              # - Step 4: UPI entry (regex validation)
│   │   │                              # - Step 5: Pincode entry (6-digit validation)
│   │   │                              # - Step 6: Plan selection (bronze, silver, gold)
│   │   │                              # - Step 7: Complete onboarding (POST /api/v1/register to backend)
│   │   │                              # - Each step validates input, updates session, handles errors gracefully
│   │   │                              # - Stores registration response (UUID, policy start date) in session.workerData
│   │   │
│   │   └── commands.js                # Stateful command handlers for post-onboarding
│   │                                  # - STATUS: Fetches current DCI from /dci/{pincode}, calculates severity tier
│   │                                  # - RENEW: Patches policy endpoint (action=renew), handles renewal window validation
│   │                                  # - SHIFT: Sets commandState=awaiting_shift, collects shift update via followup message
│   │                                  # - APPEAL: Sets commandState=filing_appeal, collects fraud appeal with 48-hour window
│   │                                  # - LANG: Changes session.language, confirms with translated message
│   │                                  # - All commands include error handling and API fallback behavior
│   │
│   ├── utils/                         # Utility functions
│   │   └── validators.js              # Input validation utilities
│   │                                  # - validateUPI() - Regex check for valid UPI format
│   │                                  # - validatePincode() - 6-digit validation with leading zero support
│   │                                  # - validatePhone() - 10-digit Indian phone number
│   │                                  # - validatePincodes() - Array validator (1-5 pin codes)
│   │                                  # - validatePlan() - Plan selection from fixed set (bronze, silver, gold)
│   │                                  # - validatePlatform() - Platform selection (delivery, ride-sharing)
│   │                                  # - validateShift() - Shift window validation
│   │
│   ├── data/                          # Runtime session and user data (GITIGNORED)
│   │   ├── sessions/                  # Directory for session files (created on first use)
│   │   │   └── {phone}.json           # Example: 9876543210.json
│   │   │                              # Content: { "userId": "uuid-123", "language": "en", "onboardingStep": 3, ... }
│   │   │
│   │   └── users.json                 # Global user registry for quick lookups
│   │                                  # Content: { "9876543210": { "uuid": "uuid-123", "language": "en", ... } }
│   │
│   └── .gitignore                     # Ignores node_modules, .env, data/, logs/
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

└── .github/                           # GitHub configuration
    └── workflows/
        └── deploy.yml                 # 🟢 CI/CD automation (optional, GitHub Actions)
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

#### **`backend/api/whatsapp_integration.py`** — WhatsApp Bot Integration Layer
Backend endpoints that forward requests to the WhatsApp bot service (running on port 3001):

- **`POST /api/v1/whatsapp/send-message`**: Send direct message to worker via WhatsApp
  - Body: `{"phone": "919876543210", "message": "Your payout has been sent", "language": "en"}`
  - Called by payout service when processing payments
  
- **`POST /api/v1/whatsapp/broadcast-dci-alert`**: Broadcast DCI-triggered disruption alert to all active workers in a zone
  - Body: `{"pincode": "560001", "dci_score": 75, "severity": "high", "workers": [...]}`
  - Called by DCI poller when DCI >= 65
  
- **`POST /api/v1/whatsapp/send-payout-confirmation`**: Send detailed payout confirmation with receipt
  - Body: `{"phone": "919876543210", "amount": 450, "upi": "user@upi", "reference": "RAZ123"}`
  - Called by payment service after Razorpay transaction succeeds
  
- **`GET /api/v1/whatsapp/health`**: Check bot service health status
- **`GET /api/v1/whatsapp/sessions`**: List all active WhatsApp sessions (DEBUG only)

---

### **WhatsApp Bot Structure**

The WhatsApp bot is a separate Node.js service that runs independently on port 3001. It manages worker communication via WhatsApp Web (no Twilio dependency).

#### **`whatsapp-bot/bot.js`** — Main WhatsApp Client (300+ lines)
Core WhatsApp connection and Express API server:

- **WhatsApp Events**:
  - `ready`: Connection established, bot is ready to receive messages
  - `qr`: QR code generated for user to scan (first-time setup only)
  - `message`: Inbound message from worker → routes to message-handler
  - `authenticated`: Session persisted via LocalAuth
  
- **Express API Endpoints**:
  - `POST /send-message`: Direct message to phone
  - `POST /broadcast-dci-alert`: Alert all workers in zone
  - `POST /send-payout-confirmation`: Payout receipt message
  - `GET /health`: Service health check
  - `GET /sessions`: List active sessions (returns users.json)

- **Session Persistence**:
  - Uses `whatsapp-web.js` LocalAuth (browser session file)
  - Survives bot restart without re-scanning QR code
  - Sessions stored in `.wwebjs_auth/` directory

#### **`whatsapp-bot/services/session-manager.js`** — Session Persistence
File-based user context management:

- **CRUD Operations**:
  - `getOrCreateSession(phone)`: Returns session or creates new one with UUID
  - `updateSession(phone, data)`: Merges data into existing session
  - `updateTempData(phone, key, value)`: Stores temporary data during onboarding
  - `nextStep(phone)`: Increments onboardingStep counter
  - `completeOnboarding(phone)`: Sets isOnboarded = true after step 7
  - `registerWorker(phone, workerData)`: Stores backend registration response

- **Session Schema**:
```json
{
  "userId": "a1b2c3d4-e5f6-7890...",
  "language": "en",
  "onboardingStep": 0,
  "tempData": { "platform": "delivery", "shift": "morning" },
  "isOnboarded": false,
  "workerData": { "policy_id": "POL123", "start_date": "2025-03-29" },
  "createdAt": "2025-03-29T10:30:00Z",
  "lastMessageAt": "2025-03-29T10:35:00Z"
}
```

- **Persistence Strategy**:
  - Each phone number gets a JSON file: `./data/sessions/{phone}.json`
  - User registry at `./data/users.json` for quick lookups
  - 4-level directory creation (handles edge cases)
  - Session survives bot restart (critical for reliability)

#### **`whatsapp-bot/services/message-handler.js`** — Message Router
Main logic to route messages to appropriate handler:

**Command Processing** (checked first):
- `HELP`: Displays available commands and onboarding instructions
- `LANG`: Changes worker language preference
- `STATUS`: Fetch current DCI score and severity level
- `RENEW`: Renew weekly policy (if renewalable)
- `SHIFT`: Update working shift
- `APPEAL`: File fraud appeal against suspension
- `JOIN`: Start/restart onboarding

**Onboarding Routing** (if not onboarded):
- Routes to `onboarding.js` based on current step (0-6)

**Command Routing** (if onboarded):
- Routes to `commands.js` for STATUS, RENEW, SHIFT, APPEAL processing

**Fallback**:
- If message doesn't match commands, sends help text

#### **`whatsapp-bot/handlers/onboarding.js`** — 7-Step Onboarding Pipeline

| Step | Handler | Validation | Backend Call |
|------|---------|------------|--------------|
| 0 | `handleLanguageSelection()` | Must match: en, kn, hi, ta, te | None (local) |
| 1 | `handlePlatformSelection()` | Must match: delivery, ride-sharing | None (local) |
| 2 | `handleShiftSelection()` | Must match: morning, afternoon, evening | None (local) |
| 3 | `handleUPIEntry()` | Regex: valid UPI format (user@upi) | None (validation only) |
| 4 | `handlePincodeEntry()` | Regex: 6 digits, valid Karnataka pincode | None (validation only) |
| 5 | `handlePlanSelection()` | Must match: bronze, silver, gold | None (local) |
| 6 | `completeOnboarding()` | Call backend registration | `POST /api/v1/register` → stores response |

**Each Step**:
1. Validates user input against rules
2. Updates `session.tempData` with validated value
3. Calls `nextStep()` to increment counter
4. At step 6: Calls backend `/api/v1/register` with complete workerData
5. Stores registration response (UUID, policy start) in `session.workerData`
6. Sets `session.isOnboarded = true`

**Error Handling**:
- Invalid input: Localized error message + retry prompt
- Backend registration failure: Detailed error message + grace period retry

#### **`whatsapp-bot/handlers/commands.js`** — Post-Onboarding Commands

| Command | Action | Backend Endpoint | Response |
|---------|--------|------------------|----------|
| `STATUS` | Fetch current DCI | `GET /api/v1/dci/{pincode}` | "DCI is {score} ({tier})" with guidance |
| `RENEW` | Renew weekly policy | `PATCH /api/v1/policy/{policy_id}` with action=renew | "Policy renewed until..." or error |
| `SHIFT` | Update working shift | Awaits followup message for shift selection | Calls handlers.updateShift() |
| `APPEAL` | File fraud appeal | Awaits followup with appeal details | Submits to `/api/v1/fraud/appeal` |

**All Commands**:
- Check `session.isOnboarded == true` (reject if false)
- Make API call to backend with worker context
- Include error handling (API timeout, network failure)
- Return localized response with actionable guidance

#### **`whatsapp-bot/config/messages.json`** — Multilingual Templates

5 languages supported: English (en), Kannada (kn), Hindi (hi), Tamil (ta), Telugu (te)

**30+ Message Keys** organized by flow:

**Onboarding Messages**:
- `welcome`: Initial greeting
- `ask_language`: Language selection menu
- `ask_platform`: Platform selection (delivery, ride-sharing)
- `ask_shift`: Shift selection (morning, afternoon, evening)
- `ask_upi`: UPI entry instruction
- `ask_pincode`: Pincode entry instruction
- `ask_plan`: Plan selection (bronze, silver, gold)
- `onboarding_complete`: Confirmation with policy details

**Alert Messages**:
- `disruption_alert`: DCI-triggered alert with severity and guidance
- `disruption_severe`: High DCI (>85) with precautions
- `disruption_warning`: Moderate DCI (65-85) with tips

**Payout Messages**:
- `payout_sent`: Confirmation with amount and UPI
- `payout_partial`: Partial payment notification
- `payout_failed`: Failure reason and retry options
- `payout_receipt`: Detailed receipt with reference number

**Command Messages**:
- `status_response`: Current DCI with severity tier
- `renewal_success`: Policy renewed confirmation
- `renewal_failed`: Renewal error message
- `appeal_submitted`: Appeal filed confirmation
- `help_message`: Available commands and usage

**Error Messages**:
- `invalid_upi`: UPI format error
- `invalid_pincode`: Pincode validation error
- `registration_failed`: Backend connection error
- `api_error`: Generic API failure message

**Each Message**:
- Fully translated in all 5 languages
- Supports template substitution: `{dci}`, `{amount}`, `{plan}`, `{policy_id}`, `{reference}`
- Optimized for WhatsApp format (short paragraphs, emoji where appropriate)

#### **`whatsapp-bot/utils/validators.js`** — Input Validation
Client-side validation before backend calls:

- **`validateUPI(upi)`**: Returns true if matches regex `^[a-zA-Z0-9._%-]+@[a-zA-Z]{3,}$`
- **`validatePincode(pincode)`**: Returns true if 6 digits, valid Karnataka pincode
- **`validatePhone(phone)`**: Returns true if 10 digits for Indian phone
- **`validatePincodes(pincodes)`**: Array validator for 1-5 pincodes
- **`validatePlan(plan)`**: Returns true if in ['bronze', 'silver', 'gold']
- **`validatePlatform(platform)`**: Returns true if in ['delivery', 'ride-sharing']
- **`validateShift(shift)`**: Returns true if in ['morning', 'afternoon', 'evening']

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

## � Deployment Configuration

### **Render (Backend Deployment)**

**File: `render.yaml`**

Specifies how Render should build and run your FastAPI backend:

```yaml
services:
  - type: web
    name: gigkavach-backend
    runtime: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Key Points:**
- ✅ Automatically detects `requirements.txt` and installs dependencies
- ✅ Starts FastAPI server on Render's provided port
- ✅ Health check endpoint: `GET /health`
- ✅ Environment variables set in Render dashboard (not in render.yaml)

---

### **Vercel (Frontend Deployment)**

**File: `vercel.json`**

Specifies how Vercel should build and deploy your React frontend:

```json
{
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/dist",
  "rewrites": [
    {
      "source": "/:path*",
      "destination": "/index.html"
    }
  ]
}
```

**Key Points:**
- ✅ Runs `npm run build` to create optimized production bundle
- ✅ Output directory: `frontend/dist` (Vite default)
- ✅ Rewrites all routes to `/index.html` for SPA routing
- ✅ Environment variables (VITE_API_BASE_URL, VITE_WS_BASE_URL) set in Vercel dashboard

---

### **Environment Variables**

**File: `.env.example`**

Template file that shows all required environment variables. Never commit actual `.env` file with secrets.

**Usage:**
1. Copy: `cp .env.example .env`
2. Fill in actual values
3. For Render: Add to Environment Variables in dashboard
4. For Vercel: Add to Project Settings → Environment Variables
5. For local dev: Load with `source .env` or use `python-dotenv`

---

### **GitHub Actions CI/CD (Optional)**

**File: `.github/workflows/deploy.yml`**

Automates testing and deployment when you push to main branch:

1. **Run Backend Tests**: `pytest tests/`
2. **Run Frontend Tests**: `npm run build && npm run lint`
3. **Deploy to Render**: If tests pass, auto-deploys backend
4. **Deploy to Vercel**: If tests pass, auto-deploys frontend

**Setup Required:**
- Add secrets to GitHub: `RENDER_API_KEY`, `VERCEL_TOKEN`
- Configure in repository Settings → Secrets → Actions

---

### **Docker Support (Optional)**

**File: `Dockerfile`**

Multi-stage Docker image for consistent development/production environments:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Usage:**
```bash
# Build image
docker build -t gigkavach-backend .

# Run container
docker run -p 8000:8000 --env-file .env gigkavach-backend
```

---


1. **Separation of Concerns**: API routes → Services → Database. Never write business logic in route handlers.

2. **Environment Variables**: ALL secrets in `.env` (never commit). Use `.env.example` as template.

3. **Versioning**: Models in `models/v1/`, `v2/`, etc. Easy rollback if new model underperforms.

4. **Testing**: Unit tests alongside code (`backend/tests/`, `frontend/tests/`). Integration tests in root `tests/`.

5. **Documentation**: Every complex function has docstring. Every API endpoint documented in `docs/API.md`.

6. **Logging**: Structured logging to separate files (`logs/dci_engine.log`, `logs/fraud.log`). NEVER commit logs (`.gitignore`).

7. **Data Privacy**: No real user data in repo. Only synthetic data for ML training.

---

## 🚀 Quick Start After Setup

### **Backend + Frontend + WhatsApp Bot**

```bash
# 1. Clone and install
git clone https://github.com/VG2476/DEVTrails.git
cd DEVTrails
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. Setup environment
cp .env.example .env
# Fill in all API keys in .env

# 3. Setup database
python scripts/seed_database.py

# 4. TERMINAL 1: Run WhatsApp Bot Service (Node.js, port 3001)
cd whatsapp-bot
npm install
npm start
# Scan QR code with WhatsApp on first run (use your personal phone)
# Sessions persist in .wwebjs_auth/ and ./data/sessions/

# 5. TERMINAL 2: Run FastAPI Backend (port 8000, NOT 3001!)
cd backend
uvicorn main:app --reload --port 8000

# 6. TERMINAL 3: Run Frontend (port 5173)
cd frontend
npm run dev

# 7. Access Services
# Backend API: http://localhost:8000
# Backend Docs: http://localhost:8000/docs
# Frontend: http://localhost:5173
# WhatsApp Bot Health: http://localhost:3001/health
```

### **Architecture Notes**

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Port 5173)                     │
│                   React + TailwindCSS                        │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│               Backend API (Port 8000)                        │
│              FastAPI + Pydantic + Supabase                   │
│         handles workers, policies, payouts, fraud            │
└──────────┬──────────────────────────────────────┬────────────┘
           ↓                                      ↓
    ┌─────────────┐                  ┌────────────────────────┐
    │  Supabase   │                  │  WhatsApp Bot (Port 3001)
    │  Database   │                  │  Node.js + Express      │
    │             │                  │  Manages worker comms   │
    └─────────────┘                  │  Sessions + handlers    │
                                     └────────────────────────┘
```

**Key Point**: WhatsApp Bot runs on port **3001**, Backend on port **8000**. Frontend calls Backend, Backend calls Bot service. They communicate via REST API (/api/v1/whatsapp/* endpoints).

---

This folder structure is production-ready, scalable, and follows industry best practices. Each directory has a clear purpose, making it easy for new developers to navigate the codebase.