# Environment Files Organization

This document describes the consolidated and organized environment file structure for the GigKavach project across Vercel/Render workflow.

## 📁 File Structure

### Backend Configuration
```
backend/
├── .env                  ✅ ACTIVE: Actual configuration (local dev)
├── .env.example          ✅ ACTIVE: Template without secrets (for git)
└── config/settings.py    Reads from .env via pydantic BaseSettings
```

**backend/.env** (Local Development)
- Contains actual API keys, database URLs, Redis connection
- Used for local development and Docker Compose
- Format: `KEY=value` with real secrets from Supabase/API providers
- Example: `SUPABASE_URL=https://rwzjpuxyaxjymhjkpxrm.supabase.co`

**backend/.env.example** (Template for git)
- Same keys as .env but with placeholder values
- All secrets replaced with `your-xxx-key-here`
- Includes TODO comments for Render production URLs
- ALWAYS committed to git (since no secrets)
- Other developers copy this: `cp .env.example .env`

---

### Frontend Configuration
```
frontend/
├── .env                  ✅ ACTIVE: Local development
├── .env.example          ✅ ACTIVE: Template without secrets (for git)
├── .env.production       ⚠️  DEPRECATED: Remove or keep for reference
├── .env.server           ⚠️  DEPRECATED: Remove or keep for reference
└── src/utils/constants.js  Reads VITE_* env vars at build time
```

**frontend/.env** (Local Development)
- Backend URL: `http://localhost:8000` (when running backend locally)
- Supabase credentials: Uses actual values from `.supabase.co`
- Feature flags: `VITE_DEBUG_MODE=false`, etc.
- Used by: `npm run dev` (Vite dev server)

**frontend/.env.example** (Template for git)
- Same keys but with placeholder values
- Backend URL: `http://localhost:8000` (template value)
- Supabase: `https://your-project.supabase.co`
- All actual secrets removed
- ALWAYS committed to git

**frontend/.env.production & .env.server** (DEPRECATED)
- These files are now redundant
- Vercel uses environment variables from dashboard (not .env files)
- Recommendation: Delete or keep for historical reference only
- Production backend URL is set via Vercel dashboard env vars

---

### WhatsApp Bot Configuration
```
whatsapp-bot/
├── .env                  ✅ ACTIVE: Local development
├── .env.example          ✅ ACTIVE: Template without secrets (for git)
└── bot.js                Reads from .env
```

**whatsapp-bot/.env** (Local Development)
- Backend URL: `http://localhost:8000` (for local testing)
- Bot port: `3001`
- WhatsApp phone: `8792525542` (actual number)

**whatsapp-bot/.env.example** (Template for git)
- Backend URL: `http://localhost:8000` (same, since it's local reference)
- Bot port: `3001` (same, standard)
- WhatsApp phone: `your-phone-number-here` (placeholder)
- All actual values removed except non-sensitive config

---

## 📋 Key Properties

| File | Type | Git Committed? | Contains Secrets? | When Updated |
|------|------|----------------|-------------------|--------------|
| `backend/.env` | Actual | ❌ No (.gitignore) | ✅ Yes | Daily during dev |
| `backend/.env.example` | Template | ✅ Yes | ❌ No | When adding new keys |
| `frontend/.env` | Actual | ❌ No (.gitignore) | ✅ Yes | Daily during dev |
| `frontend/.env.example` | Template | ✅ Yes | ❌ No | When adding new keys |
| `whatsapp-bot/.env` | Actual | ❌ No (.gitignore) | ✅ Yes (phone) | Daily during dev |
| `whatsapp-bot/.env.example` | Template | ✅ Yes | ❌ No | When adding new keys |

---

## 🔄 Workflow: Adding a New Environment Variable

### Scenario: You add `NEW_API_KEY` to backend

1. **Add to code** (`backend/config/settings.py`):
   ```python
   NEW_API_KEY: str = ""
   ```

2. **Add to backend/.env** (YOUR LOCAL FILE - don't commit):
   ```
   NEW_API_KEY=sk-actual-key-12345...
   ```

3. **Add to backend/.env.example** (commit to git):
   ```
   NEW_API_KEY=your-new-api-key-here
   ```

4. **Notify team**: "New env var `NEW_API_KEY` added, run `cp backend/.env.example backend/.env` and fill in the value"

---

## 🚀 Deployment: Setting Production Variables

### For Render Backend
Go to **Render dashboard** → Project Settings → Environment Variables:
```
FRONTEND_PRODUCTION_URL = https://your-vercel-app.vercel.app
REDIS_URL = redis://:password@dpg-xxxxx.render.com:6379
SUPABASE_URL = https://your-project.supabase.co
SUPABASE_ANON_KEY = your-actual-key
... (add all from backend/.env)
```

### For Vercel Frontend
Go to **Vercel dashboard** → Settings → Environment Variables:
```
VITE_API_BASE_URL = https://gigkavach-backend.onrender.com
VITE_WS_BASE_URL = wss://gigkavach-backend.onrender.com
VITE_SUPABASE_URL = https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY = your-actual-key
```

---

## 📝 .gitignore Entries

Ensure these files are ignored (usually already set up):
```gitignore
# Environment files - never commit actual credentials
.env
.env.local
.env.*.local

# Keep these so others know what variables exist
!.env.example
!.env*.example
```

---

## ✅ Verification Checklist

- [ ] Only `.env.example` files committed to git (check git status)
- [ ] Actual `.env` files in `.gitignore`
- [ ] No hardcoded secrets in `.example` files
- [ ] All keys in `.env.example` have placeholder values
- [ ] `.env` and `.env.example` have same keys (just different values)
- [ ] Production URLs marked with `# TODO:` comments in `.example` files
- [ ] Each service has exactly 2 env files: `.env` and `.env.example`

---

## 🔍 Quick Reference

### Finding where env vars are used

**Backend**:
```bash
grep -r "SUPABASE_URL\|REDIS_URL" backend/config/settings.py
```

**Frontend** (build-time):
```bash
grep -r "VITE_" frontend/src/
```

**WhatsApp Bot**:
```bash
grep -r "process.env.BACKEND_URL" whatsapp-bot/
```

### Testing env loading locally

```bash
# Backend
cd backend && python -c "from config.settings import settings; print(settings.SUPABASE_URL)"

# Frontend (Vite dev server)
cd frontend && npm run dev  # Check console output for env vars

# WhatsApp Bot  
cd whatsapp-bot && echo $BACKEND_URL
```

---

## 📚 Examples

### Adding Redis configuration

**Step 1**: Add to `backend/config/settings.py`
```python
REDIS_URL: str = "redis://localhost:6379/0"
```

**Step 2**: Update `backend/.env.example`
```
REDIS_URL=redis://localhost:6379/0
# PRODUCTION: Render managed Redis - set in Render dashboard
```

**Step 3**: Update `backend/.env` (your local copy)
```
REDIS_URL=redis://localhost:6379/0
```

**Step 4**: Commit only `backend/.env.example`

---

## 🎯 Best Practices

1. **NEVER commit `.env`** - Always verify with `git status` before push
2. **Keep `.env.example` updated** - When you add new keys, add to `.example` immediately
3. **Use same structure** - Keep `.env` and `.env.example` keys in same order for easy comparison
4. **Comment production URLs** - Add `# TODO:` comments for URLs to be filled in tomorrow
5. **Document secrets location** - Leave comments like `# From Supabase dashboard` in `.example`
6. **Keep secrets out of code** - Always load from env, never hardcode keys/URLs
7. **Use environment-specific configs** - Switch behavior based on `APP_ENV` variable

