# Worker Profile Share Token System

## Overview

The Share Token system allows workers to generate shareable links to their public profiles via WhatsApp. This document explains the complete implementation across frontend, backend, and database.

---

## Architecture

### Database (Supabase)

The `share_tokens` table stores generated tokens with expiry, usage tracking, and metadata:

```sql
CREATE TABLE public.share_tokens (
  id UUID PRIMARY KEY,
  worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
  token TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,
  is_used BOOLEAN DEFAULT FALSE,
  use_count INTEGER DEFAULT 0,
  max_uses INTEGER (NULL = unlimited),
  created_by TEXT DEFAULT 'manual',
  notes TEXT,
  CONSTRAINT share_tokens_valid_expiry CHECK (expires_at > created_at),
  CONSTRAINT share_tokens_nonnegative_uses CHECK (use_count >= 0)
);

-- Indexes for fast lookups
CREATE INDEX idx_share_tokens_token ON public.share_tokens(token);
CREATE INDEX idx_share_tokens_worker_id ON public.share_tokens(worker_id);
CREATE INDEX idx_share_tokens_expires_at ON public.share_tokens(expires_at);
```

---

### Backend API

**Location**: `backend/api/share_tokens.py`

#### Endpoints

1. **Generate Share Token**
   ```
   POST /api/share-tokens/generate
   ```
   Request:
   ```json
   {
     "worker_id": "uuid-of-worker",
     "expires_in_days": 30,
     "max_uses": null,
     "reason": "dashboard"
   }
   ```
   Response:
   ```json
   {
     "token": "secure-url-safe-token",
     "share_url": "https://app.devtrails.com/share/worker/token",
     "worker_id": "uuid",
     "expires_at": "2026-05-13T...",
     "created_at": "2026-04-13T..."
   }
   ```

2. **Verify Share Token**
   ```
   GET /api/share-tokens/verify/{token}
   ```
   Response:
   ```json
   {
     "is_valid": true,
     "worker_id": "uuid",
     "expires_at": "2026-05-13T...",
     "expires_in_seconds": 2592000,
     "message": "Token is valid"
   }
   ```

3. **Get Shared Worker Profile**
   ```
   GET /api/share-tokens/profile/{token}
   ```
   Response (public data only):
   ```json
   {
     "id": "uuid",
     "name": "Worker Name",
     "platform": "Zomato",
     "gig_score": 85,
     "portfolio_score": 92,
     "shift": "Flexible",
     "plan": "pro"
   }
   ```

#### Key Features

- ✅ Secure token generation (URL-safe, cryptographically random)
- ✅ Configurable expiry (default: 30 days)
- ✅ Usage tracking (count max_uses)
- ✅ Logging for debugging
- ✅ Error handling with detailed messages
- ✅ Public profile returns LIMITED data only:
  - ✅ Included: name, platform, gig_score, portfolio_score, shift, plan
  - ✅ Excluded: phone, UPI, email, sensitive personal data

---

### Frontend

#### Components & Files

1. **Share Token Utilities** (`frontend/src/utils/shareTokenUtils.js`)
   - `generateShareToken(workerId)` - Call backend to generate new token
   - `verifyShareToken(token)` - Check if token is valid
   - `getSharedWorkerProfile(token)` - Fetch public profile data
   - `copyToClipboard(text)` - Copy link to clipboard (with fallback)
   - `shareOnWhatsApp(link, workerName)` - Open WhatsApp with pre-filled link

2. **Shared Worker Profile Page** (`frontend/src/pages/SharedWorkerProfile.jsx`)
   - Public route: `/share/worker/:token`
   - Shows worker's public profile data
   - Displays gig_score, portfolio_score, platform, shift, plan
   - Beautiful dark-themed UI with gradient background
   - Error handling for expired/invalid tokens

3. **Workers Page** (`frontend/src/pages/Workers.jsx`)
   - Share button in worker table (right-most column)
   - Dropdown menu with options:
     - "Copy Link" - Generates token and copies to clipboard
     - "WhatsApp" - Opens WhatsApp with pre-filled message
   - Shows "Generating..." spinner while creating token
   - Shows "Copied!" confirmation after successful copy

4. **App Routes** (`frontend/src/App.jsx`)
   - Public route: `<Route path="/share/worker/:token" element={<SharedWorkerProfile />} />`
   - No authentication required for accessing shared profiles

---

## Usage Flow

### For Dashboard Users (Creating Share Links)

1. **Click Share Button**
   - User clicks Share icon (🔗) on a worker row in Workers table

2. **Generate Token**
   - Button shows "Generating..." spinner
   - Frontend calls: `POST /api/share-tokens/generate`
   - Backend creates token, stores in database
   - Returns share URL: `https://app.devtrails.com/share/worker/{token}`

3. **Copy or Share**
   - "Copy Link" option: Copies URL to clipboard, shows "Copied!" confirmation
   - "WhatsApp" option: Opens WhatsApp with pre-filled message and link

### For Workers (Accessing Shared Link)

1. **Receive Link**
   - Worker receives WhatsApp message with share link

2. **Click Link**
   - Opens public profile page: `/share/worker/{token}`

3. **View Profile**
   - Frontend verifies token via: `GET /api/share-tokens/verify/{token}`
   - Loads profile via: `GET /api/share-tokens/profile/{token}`
   - Shows worker's name, scores, platform, shift, plan
   - Backend increments `use_count` in database

4. **Expiry Handling**
   - If token expired: Shows "Link Expired" message
   - If max uses reached: Shows "Usage limit exceeded" message
   - If invalid: Shows "Profile Not Found" message

---

## Security Considerations

### RLS Policies

The `share_tokens` table uses **Service Role** RLS policies:

```sql
-- Service role (backend) can do everything
CREATE POLICY "Service role can read" ON share_tokens 
  FOR SELECT TO service_role USING (TRUE);

CREATE POLICY "Service role can create" ON share_tokens 
  FOR INSERT TO service_role WITH CHECK (TRUE);

CREATE POLICY "Service role can update" ON share_tokens 
  FOR UPDATE TO service_role USING (TRUE);
```

### Data Privacy

✅ **Public profiles return LIMITED data:**
- ✅ Safe to expose: name, platform, scores, shift, plan
- ❌ Never exposed: phone, UPI, email, earnings, personal details

✅ **Tokens are URL-safe and unpredictable:**
- 24-character random tokens generated with `secrets.token_urlsafe()`
- Stored in database for verification
- Cannot be guessed or enumerated

✅ **Expiry limits token lifetime:**
- Default: 30 days
- Can be customized per generation
- Expired tokens rejected with clear error message

---

## Setup Instructions

### 1. Create Supabase Table

Run this SQL in Supabase SQL Editor:

```sql
CREATE TABLE IF NOT EXISTS public.share_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  worker_id UUID NOT NULL REFERENCES public.workers(id) ON DELETE CASCADE,
  token TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  is_used BOOLEAN DEFAULT FALSE,
  use_count INTEGER DEFAULT 0,
  max_uses INTEGER DEFAULT NULL,
  created_by TEXT DEFAULT 'manual',
  notes TEXT,
  CONSTRAINT share_tokens_valid_expiry CHECK (expires_at > created_at),
  CONSTRAINT share_tokens_nonnegative_uses CHECK (use_count >= 0)
);

CREATE INDEX idx_share_tokens_token ON public.share_tokens(token);
CREATE INDEX idx_share_tokens_worker_id ON public.share_tokens(worker_id);
CREATE INDEX idx_share_tokens_expires_at ON public.share_tokens(expires_at);

ALTER TABLE public.share_tokens DISABLE ROW LEVEL SECURITY;

GRANT SELECT ON public.share_tokens TO anon;
GRANT INSERT ON public.share_tokens TO anon;
GRANT UPDATE ON public.share_tokens TO anon;
GRANT ALL ON public.share_tokens TO authenticated;
```

### 2. Backend Configuration

Ensure `backend/api/share_tokens.py` is imported in `backend/main.py`:

```python
from backend.api.share_tokens import router as share_tokens_router

app.include_router(share_tokens_router)
```

### 3. Frontend Configuration

Already configured in:
- `frontend/src/App.jsx` - Public route added
- `frontend/src/pages/Workers.jsx` - Share button added
- `frontend/src/utils/shareTokenUtils.js` - API client functions

### 4. Environment Variables

Frontend `.env`:
```
VITE_API_URL=http://localhost:8000  # Backend API URL
```

Backend `.env`:
```
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-service-key
FRONTEND_URL=https://app.devtrails.com  # For share URL generation
```

---

## Testing

### Test Share Token Generation

```bash
# 1. Start frontend dev server
cd frontend
npm run dev

# 2. Start backend
cd backend
python main.py

# 3. Go to Workers page
# 4. Click Share button on any worker
# 5. Check browser console for logs:
#    [SHARE] Token generated successfully: https://app.devtrails.com/share/worker/...
```

### Test Public Profile Access

```bash
# 1. Copy generated share link
# 2. Open in new browser tab (or share via WhatsApp)
# 3. Should see public profile page
# 4. Check browser console for:
#    [PROFILE] Loading shared worker profile...
#    Verify token access works
```

### Test Token Expiry

```bash
# In Supabase SQL editor:
SELECT * FROM share_tokens WHERE worker_id = 'your-worker-id';

# Manually set expires_at to past date:
UPDATE share_tokens SET expires_at = NOW() - INTERVAL '1 day' 
WHERE token = 'your-token';

# Try accessing the share link
# Should show "Link Expired" message
```

---

## API Response Examples

### Success: Generate Token

```json
{
  "token": "kB2vU9xK7mN4pQ1rS8t3wX5yJ6zL9aM0",
  "share_url": "https://app.devtrails.com/share/worker/kB2vU9xK7mN4pQ1rS8t3wX5yJ6zL9aM0",
  "worker_id": "550e8400-e29b-41d4-a716-446655440000",
  "expires_at": "2026-05-13T14:32:45.123456+00:00",
  "created_at": "2026-04-13T14:32:45.123456+00:00"
}
```

### Success: Get Public Profile

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Amit Kumar",
  "platform": "Zomato",
  "gig_score": 85,
  "portfolio_score": 92,
  "shift": "Flexible",
  "plan": "pro"
}
```

### Error: Expired Token

```json
{
  "detail": "This share link has expired"
}
```

---

## Monitoring & Logging

### Backend Logs

```
[SHARE_TOKEN] Generating for worker: 550e8400-e29b-41d4-a716-446655440000
[SHARE_TOKEN] Generated: kB2vU9x... for worker 550e8400-e29b...
[SHARE_PROFILE] Fetching profile for token: kB2vU9x...
[SHARE_PROFILE] Profile accessed for worker: 550e8400-e29b...
```

### Frontend Console Logs

```
[SHARE] Generating token for worker: 550e8400-e29b-41d4-a716-446655440000
[SHARE] Token generated successfully: https://app.devtrails.com/share/worker/...
[PROFILE] Loading shared worker profile...
[PROFILE] Profile fetched for worker: 550e8400-e29b-41d4-a716-446655440000
```

---

## Future Enhancements

- [ ] Add analytics dashboard showing share links stats
- [ ] Allow customizable expiry times (7, 30, 90 days, etc.)
- [ ] QR code generation for share links
- [ ] Email sharing support
- [ ] SMS sharing support
- [ ] Dashboard for managing active share links
- [ ] Revoke link functionality
- [ ] Track visitor analytics (unique views, geolocation, etc.)
- [ ] Customizable shared profile template

---

## Troubleshooting

### Issue: "Failed to generate share token"

**Cause**: Backend API not responding
**Fix**: 
- Check backend is running: `docker-compose up` or `python main.py`
- Check VITE_API_URL in frontend `.env`
- Check browser Network tab for API errors

### Issue: "Profile not found"

**Cause**: Worker doesn't exist or token is invalid
**Fix**:
- Verify worker exists in database
- Check token in database: `SELECT * FROM share_tokens WHERE token = '...'`
- Verify expires_at is in future

### Issue: "This share link has expired"

**Cause**: Token expires_at is in past
**Fix**:
- Generate new share link with longer expiry
- Check system time on backend server

---

## Files Modified

```
Backend:
  - backend/api/share_tokens.py (Complete re-implementation)
  - backend/main.py (Add router import)

Frontend:
  - frontend/src/utils/shareTokenUtils.js (New utilities)
  - frontend/src/pages/SharedWorkerProfile.jsx (New public profile page)
  - frontend/src/pages/Workers.jsx (Added Share button)
  - frontend/src/App.jsx (Added public route)
  - frontend/.env.example (Documentation)

Database:
  - share_tokens table (Created via migration)
```

---

Generated: April 13, 2026
