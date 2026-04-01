# 🚀 Deployment Configuration Guide
# 
# This document explains folder structure and deployment configuration for:
# - Backend: Render (https://render.com)
# - Frontend: Vercel (https://vercel.com)

---

## 📁 Root Directory Structure

```
DEVTrails/
├── backend/              # FastAPI backend (Deploy to Render)
├── frontend/             # React + Vite (Deploy to Vercel)
├── data/                 # Training & reference data
├── models/               # Trained ML model artifacts
├── docs/                 # Documentation
│
├── requirements.txt      # Python dependencies
├── package.json          # Node.js dependencies (root, optional)
│
├── render.yaml           # Render deployment config
├── vercel.json           # Vercel deployment config
├── Dockerfile            # Docker image for backend (optional)
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
│
├── .github/
│   └── workflows/
│       └── deploy.yml    # CI/CD automation (Github Actions)
│
└── README.md             # Main project documentation
```

---

## 🐍 Backend Deployment (Render)

### Folder: `backend/`

The backend is self-contained and ready for Render deployment:

```
backend/
├── main.py                          # Entry point (Render starts this)
├── requirements.txt                 # Python dependencies ✅
├── server.py                        # Fast API server configuration
├── __init__.py
│
├── api/                             # Route handlers
│   ├── workers.py                   # Worker endpoints
│   ├── policies.py                  # Policy endpoints
│   ├── dci.py                       # DCI engine endpoints
│   ├── payouts.py                   # Payout endpoints
│   ├── fraud.py                     # Fraud detection endpoints
│   ├── whatsapp.py                  # WhatsApp webhook handler
│   ├── health.py                    # Health check endpoint
│   └── ...
│
├── models/                          # Pydantic models
│   ├── worker.py
│   ├── policy.py
│   ├── fraud.py
│   ├── payout.py
│   └── dci.py
│
├── services/                        # Business logic
│   ├── dci_engine.py                # DCI calculation
│   ├── fraud_service.py             # Fraud detection
│   ├── payout_service.py            # Payout calculation
│   ├── baseline_service.py          # Earnings baseline
│   ├── weather_service.py           # Weather APIs
│   ├── aqi_service.py               # AQI data
│   ├── social_service.py            # NLP social disruption
│   └── ...
│
├── ml/                              # ML models
│   ├── xgboost_loader.py
│   ├── fraud_detector.py
│   ├── earnings_fingerprint.py
│   ├── nlp_classifier.py
│   └── feature_engineering.py
│
├── cron/                            # Background jobs
│   ├── dci_poller.py                # Polls every 5 min
│   ├── claims_trigger.py            # Processes claims
│   ├── settlement_service.py        # Daily settlement (11:55 PM)
│   ├── rss_parser.py                # RSS feed parsing
│   └── scheduler.py
│
├── database/
│   ├── schema.sql                   # Database tables
│   └── seed.sql                     # Test data
│
├── config/
│   ├── settings.py                  # Environment configuration
│   ├── constants.py                 # Constants
│   └── api_keys.py                  # API key management
│
├── utils/
│   ├── supabase_client.py           # Database client
│   ├── redis_client.py              # Cache client
│   ├── validators.py                # Validation functions
│   ├── datetime_utils.py            # Time utilities
│   ├── geocoding.py                 # Location utilities
│   └── logger.py
│
├── tests/                           # Unit tests
│   ├── test_dci_engine.py
│   ├── test_payout_service.py
│   ├── test_fraud_detection.py
│   └── ...
│
└── .gitignore                       # Backend-specific excludes
```

### Render Deployment Configuration

**File: `render.yaml`**

```yaml
services:
  - type: web
    name: gigkavach-backend
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    rootDir: backend
    envVars:
      - key: APP_ENV
        value: production
      - key: SUPABASE_URL
        sync: false  # Set in Render dashboard
      # ... more variables
```

### Environment Variables (Set in Render Dashboard)

```
APP_ENV                  = production
SUPABASE_URL            = https://your-project.supabase.co
SUPABASE_ANON_KEY       = your-key
TWILIO_ACCOUNT_SID      = your-sid
RAZORPAY_KEY_ID         = your-key
TOMORROW_IO_API_KEY     = your-key
FRONTEND_PRODUCTION_URL = https://your-frontend.vercel.app
```

### Deployment Steps

1. Push code to GitHub (main branch)
2. Go to [https://dashboard.render.com](https://dashboard.render.com)
3. Create new "Web Service"
4. Connect GitHub repository
5. Configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Root Directory: `backend`
6. Add environment variables
7. Click "Deploy"

**Result:** Backend running at `https://your-app.onrender.com`

---

## ⚛️ Frontend Deployment (Vercel)

### Folder: `frontend/`

The frontend is ready for Vercel deployment:

```
frontend/
├── package.json                     # Node dependencies ✅
├── package-lock.json                # Lock file for consistency
├── vite.config.ts                   # Vite bundler config
├── tsconfig.json                    # TypeScript config
├── tailwind.config.js               # TailwindCSS config
│
├── index.html                       # HTML entry point
│
├── src/
│   ├── main.tsx                     # React entry
│   ├── App.tsx                      # Root component
│   ├── index.css                    # Global styles
│   │
│   ├── api/                         # API clients
│   │   ├── client.js                # Axios configuration
│   │   ├── workers.js               # Worker endpoints
│   │   ├── policies.js              # Policy endpoints
│   │   ├── dci.js                   # DCI endpoints
│   │   ├── payouts.js               # Payout endpoints
│   │   └── fraud.js                 # Fraud endpoints
│   │
│   ├── components/
│   │   ├── common/                  # Reusable components
│   │   ├── layout/                  # Layout components
│   │   ├── workers/                 # Worker components
│   │   ├── dci/                     # DCI visualizations
│   │   ├── payouts/                 # Payout components
│   │   └── fraud/                   # Fraud components
│   │
│   ├── pages/                       # Page components
│   │   ├── Dashboard.tsx
│   │   ├── Workers.tsx
│   │   ├── Payouts.tsx
│   │   ├── Fraud.tsx
│   │   └── Settings.tsx
│   │
│   ├── hooks/                       # Custom React hooks
│   │   ├── useApi.js
│   │   ├── usePolling.js
│   │   └── useWebSocket.js
│   │
│   ├── utils/
│   │   ├── constants.js             # API URLs from env
│   │   ├── formatters.js
│   │   └── validators.js
│   │
│   └── assets/                      # Images, icons
│
├── public/                          # Static files
│   ├── favicon.ico
│   └── manifest.json
│
├── .env.local                       # Dev environment (localhost:8000)
├── .env.production                  # Prod environment (Render backend)
├── .gitignore                       # Node/build excludes
│
└── tests/
    └── .gitkeep
```

### Vercel Deployment Configuration

**File: `vercel.json`**

```json
{
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/dist",
  "rewrites": [
    {
      "source": "/:path*",
      "destination": "/index.html"
    }
  ],
  "env": {
    "VITE_API_BASE_URL": "@gigkavach-api-url",
    "VITE_WS_BASE_URL": "@gigkavach-ws-url"
  }
}
```

### Environment Variables (Set in Vercel Dashboard)

```
VITE_API_BASE_URL  = https://your-backend.onrender.com
VITE_WS_BASE_URL   = wss://your-backend.onrender.com
```

### Deployment Steps

1. Push code to GitHub (main branch)
2. Go to [https://vercel.com/dashboard](https://vercel.com/dashboard)
3. Click "Add New" → "Project"
4. Import GitHub repository
5. Configure:
   - Framework Preset: Vite
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Root Directory: `frontend`
6. Add environment variables from Vercel dashboard
7. Click "Deploy"

**Result:** Frontend running at `https://your-app.vercel.app`

---

## 📦 Data & Models

### `data/` Folder

```
data/
├── synthetic_workers.csv            # Training data
├── fraud_training_v3_labeled.csv    # Fraud training data
├── X_train.csv, X_test.csv          # Feature matrices
├── y_train.csv, y_test.csv          # Labels
├── pin_codes_mapping.json           # Zone data
└── messages.json                    # Multilingual templates
```

**Note:** Large data files can be stored in Supabase or use Git LFS for efficiency.

### `models/` Folder

```
models/
├── v3/                              # Production models
│   ├── xgboost_metadata_v3.json
│   └── fraud_detection_v3.pkl
└── v2/                              # Previous versions
```

**Note:** ML models loaded at runtime from `backend/ml/xgboost_loader.py`

---

## 🔧 Configuration Files

### `.env.example`
Template for all environment variables. **Never commit actual `.env`**

### `render.yaml`
Render deployment configuration. Specifies:
- Python runtime
- Build & start commands
- Environment variables
- Resource allocation

### `vercel.json`
Vercel deployment configuration. Specifies:
- Build output directory
- Rewrite rules for SPA
- Environment variables

### `.gitignore`
Prevents committing:
- `.env` files (secrets)
- `node_modules/`, `venv/`
- Build artifacts (`dist/`, `build/`)
- Cache files (`__pycache__/`, `.next/`)
- Logs

### `Dockerfile` (Optional)
Docker image for backend. Useful for:
- Local development with Docker
- Custom deployment platforms
- Consistent environments

---

## 🔄 CI/CD Pipeline

**File: `.github/workflows/deploy.yml`**

Automated workflow:
1. On `git push` to `main`:
   - Run backend tests (pytest)
   - Run frontend tests & build
   - If tests pass: Deploy to Render (backend)
   - If tests pass: Deploy to Vercel (frontend)

**Secrets needed in GitHub:**
```
RENDER_API_KEY          - From Render dashboard
RENDER_SERVICE_ID       - Your backend service ID
VERCEL_TOKEN            - From Vercel account settings
VERCEL_ORG_ID           - Your Vercel organization ID
VERCEL_PROJECT_ID       - Your frontend project ID
```

---

## ✅ Deployment Checklist

### Before Rendering (Backend Deployment)

- [ ] `requirements.txt` includes all Python packages
- [ ] `backend/main.py` is the entry point
- [ ] All environment variables in `.env.example`
- [ ] Database migrations applied (`schema.sql`)
- [ ] Health check endpoint at `/health` works
- [ ] No hardcoded secrets in code
- [ ] Render service configured in `render.yaml`

### Before Vercel (Frontend Deployment)

- [ ] `frontend/package.json` has all dependencies
- [ ] `npm run build` works locally (no errors)
- [ ] `.env.production` has correct Render backend URL
- [ ] Environment variables set in Vercel dashboard
- [ ] No hardcoded secrets in code
- [ ] `vite.config.ts` configured properly

### After Deployment

- [ ] Backend health check: `https://your-app.onrender.com/health` → `{status: ok}`
- [ ] Frontend loads: `https://your-app.vercel.app` → Dashboard visible
- [ ] API calls work: Browser DevTools → Console → Test API call
- [ ] WebSocket connects: Check browser Network tab
- [ ] Logs accessible: Render & Vercel dashboards

---

## 🚨 Common Deployment Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "Build failed" on Render | Missing dependencies | Add to `requirements.txt` |
| "Module not found" | Wrong Python path | Check `rootDir: backend` in `render.yaml` |
| "CORS error" | Frontend URL not in backend CORS | Update `FRONTEND_PRODUCTION_URL` on Render |
| "Build timeout" on Vercel | Large dependencies | Optimize `package.json` or split code |
| "Cannot find module" | Missing `node_modules` | Run `npm install` before build |
| "API 502 Bad Gateway" | Backend crashing | Check Render logs for errors |

---

## 📚 References

- **Render Docs:** https://render.com/docs
- **Vercel Docs:** https://vercel.com/docs
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment
- **Vite Guide:** https://vitejs.dev/guide

---

**Last Updated:** April 2, 2026  
**Status:** Production-Ready
