# 🔗 GigKavach Frontend-Backend Connection Setup
## Complete Step-by-Step Guide (April 1, 2026)

---

## 📌 Overview

Your setup:
- **Backend:** Running on Render (`https://YOUR-APP-NAME.onrender.com`)
- **Frontend:** React + Vite (need to deploy to Vercel)
- **Database:** Supabase PostgreSQL
- **Messaging:** Twilio WhatsApp

This guide connects them all.

---

## 🚀 STEP 1: Get Your Render Backend URL

### Find Your Backend URL on Render

1. Go to [https://dashboard.render.com](https://dashboard.render.com)
2. Select your deployed backend service
3. Look under "Service Details" for the **URL** (e.g., `https://gigkavach-api.onrender.com`)
4. ✅ Save this URL (you'll need it multiple times)

### Test Your Backend is Running

```bash
# In terminal, test your backend
curl https://YOUR-APP-NAME.onrender.com/health

# Expected response:
# {"status": "ok"}
```

**If this fails:**
- Backend might be sleeping (free tier on Render sleeps after inactivity)
- Make a request to wake it up: `curl https://YOUR-APP-NAME.onrender.com`
- Wait 30 seconds and try again

---

## 🖥️ STEP 2: Update Frontend Environment Files

### File 1: `.env.local` (Local Development)

Open `frontend/.env.local` and update:

```properties
# 🛡️ GigKavach Frontend — LOCAL DEVELOPMENT

# Replace YOUR-APP-NAME with your actual Render app name
# Example: https://gigkavach-api.onrender.com
VITE_API_BASE_URL=https://YOUR-APP-NAME.onrender.com
VITE_WS_BASE_URL=wss://YOUR-APP-NAME.onrender.com

# Testing flags
VITE_ENABLE_MOCK_DATA=false
VITE_DEBUG_MODE=true
```

### File 2: `.env.production` (Production on Vercel)

Open `frontend/.env.production` and update:

```properties
# 🛡️ GigKavach Frontend — PRODUCTION (Vercel Deployment)

# Same Render backend URL (for production)
VITE_API_BASE_URL=https://YOUR-APP-NAME.onrender.com
VITE_WS_BASE_URL=wss://YOUR-APP-NAME.onrender.com

# Disable testing flags in production
VITE_ENABLE_MOCK_DATA=false
VITE_DEBUG_MODE=false
```

### Example (Actual Values)

If your Render backend is: `https://gigkavach-api.onrender.com`

Then set:
```properties
VITE_API_BASE_URL=https://gigkavach-api.onrender.com
VITE_WS_BASE_URL=wss://gigkavach-api.onrender.com
```

---

## 🔧 STEP 3: Update Backend Environment

### In Render Dashboard

1. Go to your backend service on Render
2. Click "Settings" → "Environment"
3. Add/Update these variables:

```
FRONTEND_PRODUCTION_URL = https://YOUR-FRONTEND-DOMAIN.vercel.app
APP_ENV = production
```

**Don't know your frontend domain yet?** You'll get it after deploying to Vercel. Come back and update this.

### Backend `.env` File (Local)

If running backend locally for testing, update `backend/.env`:

```properties
# Backend configuration for local testing with frontend
APP_ENV=development
FRONTEND_LOCAL_URL=http://localhost:5173
```

---

## 💨 STEP 4: Test Local Frontend with Render Backend

### Terminal 1: Start Frontend (connects to Render backend)

```bash
cd frontend
npm install  # Run once if you haven't already
npm run dev
```

You should see:
```
➜  Local:   http://localhost:5173/
➜  press h to show help
```

### Check Connection in Browser

1. Open browser DevTools (F12 / Cmd+Option+I)
2. Go to the **Console** tab
3. Paste this command:

```javascript
fetch('https://YOUR-APP-NAME.onrender.com/health')
  .then(r => r.json())
  .then(d => console.log('✅ Backend connected:', d))
  .catch(e => console.error('❌ Backend error:', e.message))
```

**Expected output:**
```
✅ Backend connected: {status: 'ok'}
```

**If you get CORS error:**
- Check that backend CORS includes `http://localhost:5173`
- The backend code should have been updated by our changes
- Restart the backend service on Render

### Check API Call in Browser

```javascript
// In DevTools Console, test a real API call:
const headers = {
  'Content-Type': 'application/json',
};

fetch('https://YOUR-APP-NAME.onrender.com/api/workers', { headers })
  .then(r => r.json())
  .then(d => console.log('✅ API works:', d))
  .catch(e => console.error('❌ API error:', e.message))
```

**Expected:**
- Either a list of workers, or `{"detail": "Not authenticated"}` (both mean API works)

---

## 🌐 STEP 5: Deploy Frontend to Vercel

### Option A: Git-Based Deployment (Recommended)

```bash
# 1. Commit your changes
cd frontend
git add .env.local .env.production vite.config.ts src/utils/constants.js src/api/client.js
git commit -m "Connect frontend to Render backend"

# 2. Push to GitHub
git push origin main

# 3. Vercel auto-deploys (if connected to GitHub)
# Check your Vercel dashboard in ~2-3 minutes
```

### Option B: Manual Deployment to Vercel

#### Step 1: Build Locally
```bash
cd frontend
npm run build
# Creates dist/ folder
```

#### Step 2: Deploy
```bash
# If you have Vercel CLI installed:
npm i -g vercel
vercel --prod

# Or upload dist/ folder manually on vercel.com
```

### After Deployment: Get Your Frontend URL

Once deployed, Vercel gives you a URL like:
```
https://gigkavach-frontend.vercel.app
```

✅ Save this URL

---

## 🔐 STEP 6: Update Backend CORS for Production

### In Render Dashboard

1. Go to your backend service
2. Settings → Environment Variables
3. Update:

```
FRONTEND_PRODUCTION_URL = https://YOUR-FRONTEND.vercel.app
APP_ENV = production
```

**Save and redeploy** the backend service.

---

## ✅ STEP 7: Test Production Connection

### Test Frontend → Backend Connection

```bash
# From your browser at https://YOUR-FRONTEND.vercel.app

# Open DevTools Console and run:
fetch('https://YOUR-APP-NAME.onrender.com/health')
  .then(r => r.json())
  .then(d => console.log('✅ Production connected:', d))
```

---

## 📋 Complete Configuration Checklist

### Frontend Configuration
- [ ] `.env.local` created with `VITE_API_BASE_URL=https://YOUR-APP.onrender.com`
- [ ] `.env.production` created with same backend URL
- [ ] `vite.config.ts` updated with proxy and  environment configuration
- [ ] `src/utils/constants.js` updated (no `/api` suffix in BASE_URL)
- [ ] `src/api/client.js` updated with `withCredentials: true`
- [ ] Built: `npm run build` (no errors)
- [ ] Deployed to Vercel
- [ ] Vercel environment variables set

### Backend Configuration
- [ ] Running on Render: `https://YOUR-APP-NAME.onrender.com`
- [ ] CORS updated in `main.py`
- [ ] Settings updated in `config/settings.py`
- [ ] Render environment variables set:
  - `FRONTEND_PRODUCTION_URL=https://YOUR-FRONTEND.vercel.app`
  - `APP_ENV=production`
- [ ] Health endpoint responds: `/health` → `{"status": "ok"}`

### Network Tests
- [ ] `curl https://YOUR-APP.onrender.com/health` ✅
- [ ] Browser console: `fetch to /health` ✅
- [ ] Browser console: `fetch to /api/workers` ✅ (doesn't return 500)

---

## 🐛 Troubleshooting

### Problem 1: "CORS error: Access-Control-Allow-Origin"

**Root Cause:** Backend doesn't know your frontend URL

**Fix:**
```bash
# On Render dashboard:
1. Go to backend service
2. Settings → Environment Variables
3. Update: FRONTEND_PRODUCTION_URL=https://exact-vercel-url.vercel.app
4. Click "Save" (triggers redeploy)
5. Wait for deployment to finish
6. Test again in browser
```

### Problem 2: "ERR_NAME_NOT_RESOLVED" or "Failed to fetch"

**Root Cause:** Wrong URL in `.env` files

**Fix:**
```bash
# Check your .env files:
cat frontend/.env.local
cat frontend/.env.production

# Should show:
# VITE_API_BASE_URL=https://gigkavach-api.onrender.com (NO trailing slash)
# VITE_WS_BASE_URL=wss://gigkavach-api.onrender.com

# If wrong, update and reload browser
# In development: npm run dev will auto-reload
# In production: wait for Vercel to redeploy
```

### Problem 3: "401 Unauthorized" on API calls

**Root Cause:** Authentication token missing

**Fix:**
```javascript
// In browser console:
console.log(localStorage.getItem('gigkavach_auth_token'))
// If empty, user needs to login first
```

### Problem 4: Backend returns "404 Not Found"

**Root Cause:** Endpoint path is wrong

**Check:** Make sure your API endpoints match the backend routes
- `GET /api/workers` ✅ (not `/api/v1/workers`)
- `GET /api/payouts` ✅
- `GET /api/dci/{zone}` ✅

**If endpoints differ:** Update the API service files in `frontend/src/api/*.js`

### Problem 5: "WebSocket connection failed"

**Root Cause:** WebSocket URL configured wrong

**Fix:**
```javascript
// Correct formats:
// Local dev: ws://localhost:8000
// Production: wss://your-app.onrender.com (NOT http://)

// Check in browser console:
console.log(import.meta.env.VITE_WS_BASE_URL)
```

---

## 🎯 Expected Behavior (Complete Flow)

### From User Opening Frontend

```
1. User visits: https://gigkavach-frontend.vercel.app
   ↓
2. Frontend loads .env.production from Vercel
   → VITE_API_BASE_URL = "https://gigkavach-api.onrender.com"
   ↓
3. API client configured with this base URL
   → axios.create({ baseURL: "https://gigkavach-api.onrender.com" })
   ↓
4. User clicks "Get Workers"
   ↓
5. Frontend calls: client.get('/api/workers')
   ↓
6. Full URL sent: GET https://gigkavach-api.onrender.com/api/workers
   ↓
7. Browser CORS check:
   - Origin: https://gigkavach-frontend.vercel.app
   - Backend allows this in CORS config ✅
   ↓
8. Backend receives request
   → Checks /api/workers route handler
   → Returns worker list
   ↓
9. Response sent back to frontend
   ↓
10. Frontend receives data
    → setWorkers(data)
    → Component re-renders
    → User sees worker table
```

---

## 📞 Quick Reference

| Component | Local Dev | Production |
|-----------|-----------|-----------|
| Frontend | `http://localhost:5173` | `https://xxx.vercel.app` |
| Backend | `http://localhost:8000` | `https://xxx.onrender.com` |
| Database | Supabase (cloud) | Supabase (cloud) |
| API Base URL Env | `.env.local` | Vercel Dashboard |
| CORS Setup | `main.py` | Render Env Vars |

---

## 🎓 Summary of Changes Made

### Frontend Changes:
1. ✅ Created `.env.local` (development environment)
2. ✅ Created `.env.production` (production environment)
3. ✅ Updated `vite.config.ts` (server proxy + env export)
4. ✅ Updated `src/utils/constants.js` (removed `/api` suffix)
5. ✅ Updated `src/api/client.js` (added `withCredentials`)

### Backend Changes:
1. ✅ Updated `main.py` (improved CORS configuration)
2. ✅ Updated `config/settings.py` (added FRONTEND_URL settings)

### What These Changes Do:
- **Frontend** now reads correct backend URL from environment
- **Backend** now correctly allows CORS from frontend
- **Both** properly configured for local dev + production

---

## 🚀 Next Steps

1. **Replace `YOUR-APP-NAME`** in all `.env` files with your actual Render URL
2. **Test locally:** `npm run dev` and check browser console
3. **Deploy to Vercel:** `git push` or manual upload
4. **Set Vercel env vars:** `VITE_API_BASE_URL=https://xxx.onrender.com`
5. **Update backend CORS:** Set `FRONTEND_PRODUCTION_URL` on Render
6. **Test production:** Visit your Vercel URL and verify API calls work

---

## 📚 Reference Files

| File | Purpose | Changes Made |
|------|---------|--------------|
| `frontend/.env.local` | Dev config | ✨ Created |
| `frontend/.env.production` | Prod config | ✨ Created |
| `frontend/vite.config.ts` | Vite config | Updated |
| `frontend/src/utils/constants.js` | API config | Updated |
| `frontend/src/api/client.js` | HTTP client | Updated |
| `backend/main.py` | FastAPI setup | Updated CORS |
| `backend/config/settings.py` | Backend config | Added frontend URLs |

---

**Created:** April 1, 2026  
**Last Updated:** April 1, 2026  
**Status:** Ready for Production Deployment
