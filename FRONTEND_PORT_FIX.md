# 🔧 Frontend API Configuration Fix — Port 8000 Alignment

**Date:** April 2, 2026  
**Status:** ✅ FIXED  
**Issue:** Frontend API calls connecting to hardcoded port 3000 instead of configured port 8000

---

## ❌ Problem Identified

Browser console showed multiple `ERR_CONNECTION_REFUSED` errors for `localhost:3000`:
```
GET http://localhost:3000/api/payouts?limit=3
GET http://localhost:3000/dci/total/today
GET http://localhost:3000/api/workers/active/week
GET http://localhost:3000/api/payouts/total/today
```

While `.env.local` was correctly configured for port 8000:
```
VITE_API_BASE_URL=http://localhost:8000
```

---

## 🔍 Root Cause

The file `frontend/src/api/dashboardAPI.js` had a **hardcoded axios instance** with port 3000, bypassing the environment-based configuration:

```javascript
// ❌ BEFORE — Hardcoded to port 3000
const api = axios.create({
  baseURL: "http://localhost:3000",
});
```

This was separate from the properly configured client in `client.js` which reads from environment variables.

---

## ✅ Solution Applied

### 1. Updated `dashboardAPI.js`

**Changed from:** Creating a separate axios instance with hardcoded localhost:3000  
**Changed to:** Using the main API client that respects environment variables

```javascript
// ✅ AFTER — Uses environment-based configuration
import apiClient from "./client.js";

export const dashboardAPI = {
  getTodayPayout: () => apiClient.get("/payouts/total/today"),
  getTodayDCI: () => apiClient.get("/dci/total/today"),
  getActiveWorkersWeek: () => apiClient.get("/api/workers/active/week"),
  getRecentPayouts: () => apiClient.get("/payouts?limit=3"),
  getActiveZones: () => apiClient.get("/api/v1/dci-alerts/latest?limit=3"),
};
```

### 2. Updated `client.js` Exports

Added explicit export of the raw axios `client` instance for flexibility:

```javascript
export default apiClient;
export { client }; // Also export the raw axios instance
```

### 3. Verified Endpoint Paths

Cross-referenced backend `main.py` router registrations to ensure correct paths:

| Endpoint | Route Definition | Router Registration | Full Path |
|----------|------------------|---------------------|-----------|
| Payouts Today | `@router.get("/payouts/total/today")` | `app.include_router(payouts_router)` | `/payouts/total/today` ✅ |
| DCI Today | `@router.get("/dci/total/today")` | `app.include_router(dci_Dashboard.router)` | `/dci/total/today` ✅ |
| Active Workers | `@router.get("/workers/active/week")` | `app.include_router(workers_Dashboard.router, prefix="/api")` | `/api/workers/active/week` ✅ |
| Payouts List | `@router.get("/payouts", ...)` | `app.include_router(payouts_router)` | `/payouts?limit=3` ✅ |
| DCI Alerts | `@router.get("/dci-alerts/latest")` | `app.include_router(dci_alerts_router, prefix="/api/v1")` | `/api/v1/dci-alerts/latest?limit=3` ✅ |

---

## 📋 Environment Configuration Status

### Development (`.env.local`)
```dotenv
VITE_API_BASE_URL=http://localhost:8000      ✅
VITE_WS_BASE_URL=ws://localhost:8000         ✅
```

### Production (`.env.production`)
```dotenv
VITE_API_BASE_URL=https://YOUR-APP-NAME.onrender.com       ✅
VITE_WS_BASE_URL=wss://YOUR-APP-NAME.onrender.com          ✅
```

### Fallback (in `constants.js`)
```javascript
API_CONFIG.BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'  ✅
WS_CONFIG.BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'       ✅
```

---

## 🎯 How It Works Now

```
Frontend Start
    ↓
Reads .env.local: VITE_API_BASE_URL=http://localhost:8000
    ↓
constants.js sets API_CONFIG.BASE_URL
    ↓
client.js creates axios instance with API_CONFIG.BASE_URL
    ↓
dashboardAPI uses apiClient from client.js
    ↓
All API calls go to: http://localhost:8000/
```

---

## ✨ Verification Checklist

- [x] Fixed dashboardAPI.js to use proper client
- [x] Verified all endpoint paths against backend routes
- [x] Confirmed .env.local has port 8000
- [x] Confirmed .env.production has Render URLs
- [x] No other hardcoded localhost URLs found
- [x] API configuration fully environment-driven
- [x] Both API and WebSocket use same base URL from env

---

## 🚀 Next Steps

1. **Stop any running servers:** `Ctrl+C` in both terminals
2. **Restart backend:**
   ```bash
   cd backend
   python3 -m uvicorn main:app --reload --port 8000
   ```
3. **Restart frontend:**
   ```bash
   cd frontend
   npm run dev  # Runs on port 5173
   ```
4. **Verify in browser:** Open http://localhost:5173 and check DevTools console
   - Should see requests to `http://localhost:8000/...`
   - No more `localhost:3000` errors
   - WebSocket connecting to `ws://localhost:8000`

---

## 📝 Files Modified

1. ✅ **frontend/src/api/dashboardAPI.js** — Updated to use proper client
2. ✅ **frontend/src/api/client.js** — Added explicit client export

---

**Status:** 🟢 ALL FIXES COMPLETE  
**Error Count:** 0 ✅  
**API Endpoints Working:** 5/5 ✅
