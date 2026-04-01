# 🚀 QUICK START — Frontend to Render Backend

## What Changed (Already Done ✅):
```
frontend/.env.local                    ✅ Created
frontend/.env.production               ✅ Created
frontend/vite.config.ts                ✅ Updated (server proxy)
frontend/src/utils/constants.js        ✅ Updated (removed /api)
frontend/src/api/client.js             ✅ Updated (withCredentials)
backend/main.py                        ✅ Updated (CORS config)
backend/config/settings.py             ✅ Updated (frontend URLs)
```

---

## What YOU Need to Do (Right Now):

### Step 1️⃣: Get Your Render Backend URL
```
Go to: https://dashboard.render.com
Copy URL from your service (e.g., https://gigkavach-api.onrender.com)
```

### Step 2️⃣: Update Files (Replace `YOUR-APP-NAME`)

#### Update: `frontend/.env.local`
```properties
VITE_API_BASE_URL=https://YOUR-APP-NAME.onrender.com
VITE_WS_BASE_URL=wss://YOUR-APP-NAME.onrender.com
```

#### Update: `frontend/.env.production`
```properties
VITE_API_BASE_URL=https://YOUR-APP-NAME.onrender.com
VITE_WS_BASE_URL=wss://YOUR-APP-NAME.onrender.com
```

### Step 3️⃣: Test Locally
```bash
cd frontend
npm install
npm run dev
# Opens http://localhost:5173
# Connects to Render backend automatically
```

### Step 4️⃣: Deploy to Vercel
```bash
git add .
git commit -m "Connect to Render backend"
git push origin main
# Vercel auto-deploys in ~2-3 minutes
```

### Step 5️⃣: Set Vercel Environment Variables
```
Go to: https://vercel.com/dashboard
Select your project → Settings → Environment Variables
Add:
  VITE_API_BASE_URL = https://YOUR-APP-NAME.onrender.com
  VITE_WS_BASE_URL = wss://YOUR-APP-NAME.onrender.com
```

### Step 6️⃣: Update Backend CORS (On Render)
```
Go to: https://dashboard.render.com
Select backend service → Settings → Environment
Update:
  FRONTEND_PRODUCTION_URL = https://YOUR-VERCEL-URL.vercel.app
  APP_ENV = production
```

---

## Test It Works

### In Browser Console:
```javascript
// Test backend is reachable
fetch('https://YOUR-APP-NAME.onrender.com/health')
  .then(r => r.json())
  .then(d => console.log('✅ Connected:', d))
  .catch(e => console.error('❌ Error:', e))

// Should return: {status: "ok"}
```

---

## By the Numbers 📊

| Step | Time | Action |
|------|------|--------|
| 1 | 1 min | Copy Render URL |
| 2 | 2 min | Update 2 .env files |
| 3 | 30 sec | npm install + npm run dev |
| 4 | 30 sec | npm run build (optional) |
| 5 | 3 min | git push (auto-deploys) |
| 6 | 1 min | Set Vercel env vars |
| **Total** | **~8 min** | Full integration complete ✅ |

---

## Files Modified (Reference)

```
frontend/
├── .env.local .......................... ✨ NEW
├── .env.production ..................... ✨ NEW
├── vite.config.ts ...................... 🔄 MODIFIED
├── src/
│   ├── utils/constants.js .............. 🔄 MODIFIED
│   └── api/client.js ................... 🔄 MODIFIED
│
backend/
├── main.py ............................. 🔄 MODIFIED
└── config/settings.py .................. 🔄 MODIFIED
```

---

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "CORS error" | Update `FRONTEND_PRODUCTION_URL` on Render, redeploy |
| "Failed to fetch" | Check URL in `.env` (no typos, no trailing `/`) |
| "Blank page" | Check Vercel build logs, run `npm run build` locally |
| "404 on /api/*" | Endpoint paths may not match; check backend route |
| "Render backend sleeping" | Free tier sleeps after 15 min idle; make request to wake |

---

## Verify Everything

Run this checklist:

- [ ] `ls -la frontend/.env*` (files exist)
- [ ] `npm run build` (no errors)
- [ ] `npm run dev` (starts on :5173)
- [ ] Open http://localhost:5173 in browser
- [ ] Open DevTools Console
- [ ] Paste: `fetch('https://YOUR-APP.onrender.com/health').then(r => r.json()).then(console.log)`
- [ ] Should print: `{status: "ok"}`

If all ✅, you're connected!

---

🎯 **Need Help?** Check: `FRONTEND_BACKEND_CONNECTION.md` for detailed troubleshooting
