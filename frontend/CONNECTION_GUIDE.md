# 🔗 Frontend-Backend Connection Setup Guide

## ⚡ Quick Start

### For Local Development:
```bash
cd frontend
npm install
npm run dev  # Runs on http://localhost:5173
```

✅ Backend will be at: `http://localhost:8000`  
✅ Uses `.env.local` file automatically  

---

## 🌍 For Production (Render Backend)

### Step 1: Get Your Render Backend URL
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Find your deployed backend service
3. Copy the URL (looks like: `https://gigkavach-api.onrender.com`)

### Step 2: Update Environment Files

#### For Local Testing with Render Backend:
```bash
# frontend/.env.local
VITE_API_BASE_URL=https://YOUR-APP-NAME.onrender.com
VITE_WS_BASE_URL=wss://YOUR-APP-NAME.onrender.com
```

#### For Production Deployment:
```bash
# frontend/.env.production
VITE_API_BASE_URL=https://YOUR-APP-NAME.onrender.com
VITE_WS_BASE_URL=wss://YOUR-APP-NAME.onrender.com
```

### Step 3: Deploy Frontend to Vercel

```bash
# Build locally
npm run build

# Or connect Git to Vercel
# Vercel will automatically:
# 1. Build: npm run build
# 2. Deploy to: https://your-frontend.vercel.app
```

#### Set Environment Variables in Vercel:
```
VITE_API_BASE_URL = https://YOUR-APP-NAME.onrender.com
VITE_WS_BASE_URL = wss://YOUR-APP-NAME.onrender.com
```

---

## 📋 Complete Environment Setup

### `.env.local` (Local Development)
```properties
# 🛡️ GigKavach Frontend — LOCAL DEVELOPMENT
# Used when running: npm run dev

# Backend API Configuration (Local)
VITE_API_BASE_URL=http://localhost:8000

# WebSocket Configuration (Local)
VITE_WS_BASE_URL=ws://localhost:8000

# Feature Flags
VITE_ENABLE_MOCK_DATA=true
VITE_DEBUG_MODE=true
```

### `.env.production` (Production)
```properties
# 🛡️ GigKavach Frontend — PRODUCTION (Render Deployment)
# ⚠️ UPDATE: Replace YOUR-APP-NAME with your actual Render app name
# Example: https://gigkavach-api.onrender.com

# Backend API Configuration (Production - Render)
VITE_API_BASE_URL=https://YOUR-APP-NAME.onrender.com

# WebSocket Configuration (Production - Render)
VITE_WS_BASE_URL=wss://YOUR-APP-NAME.onrender.com

# Feature Flags
VITE_ENABLE_MOCK_DATA=false
VITE_DEBUG_MODE=false
```

---

## 🔍 How Frontend Connects to Backend

### 1. API Configuration (`src/utils/constants.js`)
```javascript
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  // ✅ NO /api suffix here — endpoints add their own paths
};
```

### 2. Axios Client Setup (`src/api/client.js`)
```javascript
const client = axios.create({
  baseURL: API_CONFIG.BASE_URL,  // http://localhost:8000
  timeout: 30000,
  withCredentials: true,  // ✅ For CORS with auth
  headers: {
    'Content-Type': 'application/json',
  },
});

// ✅ Auto-adds Authorization header from localStorage
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('gigkavach_auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### 3. API Service Calls (`src/api/workers.js`)
```javascript
// Example: Get workers
export const workersAPI = {
  getWorkers: (filters) => 
    client.get('/api/workers', { params: filters })
    // Full URL: http://localhost:8000 + /api/workers
};
```

### 4. Backend Routes (FastAPI, `backend/api/workers.py`)
```python
@router.get('/api/workers')
async def get_workers(db):
    # Receives request from:
    # GET http://localhost:8000/api/workers
    return { "workers": [...] }
```

### 5. React Component Usage (`src/pages/Workers.tsx`)
```typescript
const { data: workers, loading } = useApi(
  () => workersAPI.getWorkers({ city: 'mumbai' }),
  ['mumbai']
);
```

---

## ✅ Verification Checklist

- [ ] `.env.local` created with `VITE_API_BASE_URL=http://localhost:8000`
- [ ] `.env.production` created with `VITE_API_BASE_URL=https://YOUR-APP.onrender.com`
- [ ] Updated `frontend/vite.config.ts` with server proxy
- [ ] Updated `frontend/src/utils/constants.js` to remove `/api` from base URL
- [ ] Updated `frontend/src/api/client.js` to include `withCredentials: true`
- [ ] Backend running on Render: https://dashboard.render.com
- [ ] Frontend `.env` variables match backend URL (no trailing slash)
- [ ] API endpoints tested in browser console:
  ```javascript
  // Open DevTools > Console on http://localhost:5173
  fetch('http://localhost:8000/health').then(r => r.json()).then(console.log)
  // Should return: { "status": "ok" }
  ```

---

## 🚀 Deployment Checklist

### Backend (Already on Render)
- ✅ Running on: `https://YOUR-APP-NAME.onrender.com`
- ✅ Health check available at: `https://YOUR-APP-NAME.onrender.com/health`
- ✅ CORS enabled for: `https://your-frontend.vercel.app`

### Frontend (Deploy to Vercel)
```bash
# 1. Build
npm run build

# 2. Preview locally
npm run preview

# 3. Git push (if connected to Vercel)
git add .
git commit -m "Connect frontend to Render backend"
git push origin main

# 4. Vercel automatically deploys
# Check: https://your-frontend.vercel.app
```

### Set Vercel Environment Variables
1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables
2. Add:
   ```
   VITE_API_BASE_URL = https://YOUR-APP-NAME.onrender.com
   VITE_WS_BASE_URL = wss://YOUR-APP-NAME.onrender.com
   ```
3. Redeploy

---

## 🐛 Troubleshooting

### Problem: "ERR_FAILED (net::ERR_NAME_NOT_RESOLVED)"
**Cause:** Backend URL is wrong or backend is down  
**Fix:** 
- Check URL in `.env.local` (no typos, no trailing slash)
- Verify backend is running: `curl https://YOUR-APP.onrender.com/health`

### Problem: "CORS error: Access-Control-Allow-Origin missing"
**Cause:** Backend CORS not configured for frontend URL  
**Fix:** Backend needs:
```python
# In main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Problem: "Failed to fetch" in production
**Cause:** WebSocket URL format wrong  
**Fix:**
- HTTP: `https://...` (not `http://`)
- WebSocket: `wss://...` (not `ws://`)

### Problem: "401 Unauthorized" on API calls
**Cause:** Auth token missing or expired  
**Fix:**
- Check `localStorage.getItem('gigkavach_auth_token')`
- Token should be set after login
- Check browser DevTools → Application → Local Storage

---

## 📞 API Endpoints Summary

All endpoints use the configured base URL:

| Endpoint | Method | Base + Path |
|----------|--------|-----------|
| Get Workers | GET | `{BASE_URL}/api/workers` |
| Register Worker | POST | `{BASE_URL}/api/workers/register` |
| Get Policies | GET | `{BASE_URL}/api/policies` |
| Get DCI | GET | `{BASE_URL}/api/dci/{zone}` |
| Get Payouts | GET | `{BASE_URL}/api/payouts` |
| Check Fraud | GET | `{BASE_URL}/api/fraud/check` |

---

## 🎯 Next Steps

1. Replace `YOUR-APP-NAME` with your actual Render app name in `.env.production`
2. Test locally with `npm run dev` (uses `.env.local`)
3. Deploy to Vercel with git push (uses `.env.production`)
4. Verify connection:
   ```bash
   # In Vercel deployment logs:
   # Should see: "API Base URL: https://YOUR-APP.onrender.com"
   ```

---

**Last Updated:** April 1, 2026
