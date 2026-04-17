# WhatsApp Bot Integration Architecture

## 🎯 Architecture Overview

### Clear Bifurcation

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend App                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────┐      ┌──────────────────────┐     │
│  │  ADMIN DASHBOARD    │      │   WORKER PWA         │     │
│  │  /                  │      │   /worker/*          │     │
│  ├─────────────────────┤      ├──────────────────────┤     │
│  │ • Dashboard         │      │ • Profile (PWA)      │     │
│  │ • Workers List      │      │ • Status (PWA)       │     │
│  │ • Payouts          │      │ • History (PWA)      │     │
│  │ • Fraud Detection  │      │ Requires Auth        │     │
│  │ • Analytics        │      │ (Session-based)      │     │
│  │ • Settings         │      └──────────────────────┘     │
│  │ Requires Auth      │                                    │
│  │ (Admin role)       │      ┌──────────────────────┐     │
│  └─────────────────────┘      │ SHAREABLE LINKS      │     │
│                                │ /link/:shareToken/*  │     │
│                                ├──────────────────────┤     │
│                                │ • Profile (Public)   │     │
│                                │ • Status (Public)    │     │
│                                │ • History (Public)   │     │
│                                │ Token-based Auth     │     │
│                                │ (WhatsApp links)     │     │
│                                └──────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
           ↓                              ↓
     ┌──────────────┐       ┌────────────────────────┐
     │  Supabase    │       │  WhatsApp Bot          │
     │  Auth        │       │  (Node.js)             │
     │  (JWT)       │       │  Sends Share Links     │
     └──────────────┘       └────────────────────────┘
```

---

## 🔗 Route Structure

### Admin Routes (Protected - Admin Role)
```
/                          → Dashboard
/workers                   → Workers Management
/payouts                   → Payout Management
/fraud                     → Fraud Detection
/analytics                 → Analytics
/settings                  → Settings
/login                     → Admin Login
```

### Worker PWA Routes (Protected - Session Auth)
```
/worker/profile           → Worker profile page
/worker/status            → Zone status dashboard
/worker/history           → Payout history
/worker/login             → Worker login (optional)
```

### Public Shareable Routes (Token-based Auth)
```
/link/:shareToken/profile     → Worker profile via WhatsApp link
/link/:shareToken/status      → Zone status via WhatsApp link
/link/:shareToken/history     → Payout history via WhatsApp link
```

---

## 🔐 Authentication Methods

### 1. Admin Dashboard
- **Method**: JWT + Session via Supabase Auth
- **Storage**: localStorage + session
- **Duration**: Long-lived (24-48 hours)
- **Scope**: Full dashboard access (requires admin role)

### 2. Worker PWA (Session)
- **Method**: JWT via login or app credentials
- **Storage**: localStorage + session
- **Duration**: Medium-lived (8-12 hours)
- **Scope**: Own worker data only

### 3. Shareable Links (WhatsApp)
- **Method**: Share Token (short-lived JWT variant)
- **Storage**: URL parameter + localStorage
- **Duration**: Short-lived (7 days, single-use or limited uses)
- **Scope**: Read-only access to specific worker's data
- **Generation**: Backend generates token, bot sends URL

---

## 📱 WhatsApp Bot Message Flow

```
[Worker on WhatsApp]
        ↓
[Types: "STATUS" or "PROFILE"]
        ↓
[Bot Handler]
        ↓
[If Worker Onboarded]
    ├─ Fetch worker ID from phone
    ├─ Request backend to generate share token
    ├─ Create shareable URL: 
    │  https://app.gigkavach.com/link/{shareToken}/status
    └─ Send link with message
        ↓
[Worker Clicks Link]
        ↓
[Browser opens /link/{shareToken}/status]
        ↓
[Frontend validates token]
        ├─ If valid: Load status page with data
    └─ If invalid: Redirect to /link-expired or /login
```

---

## 🔧 Database Integration Points

### Current Worker Data Needs
```javascript
// Profile Page needs:
{
  id,                    // Worker ID (from Supabase auth)
  name,                  // From workers table
  phone,                 // From workers table
  gig_score,            // Computed from GigScore model
  plan,                 // Shield Basic/Plus/Pro
  pin_codes,            // Working zones
  upi_id,               // Payment UPI
  account_status,       // active/inactive
  current_zone_dci,     // Real-time from dci_logs table
  recent_payouts        // From payouts table
}

// Status Page needs:
{
  zones: [
    {
      pincode,
      city,
      current_dci,
      severity,
      components: {
        weather: score,
        aqi: score,
        heat: score,
        social: score,
        platform: score
      },
      city_weights: {...},
      payout_triggered: boolean
    }
  ]
}

// History Page needs:
{
  payouts: [
    {
      id,
      amount,
      status,
      triggered_at,
      dci_score,
      pincode
    }
  ]
}
```

---

## 🛠️ Implementation Checklist

### Phase 1: Backend Modifications
- [ ] Create `/api/v1/workers/generate-share-token` endpoint
  - **Input**: `{worker_id}`
  - **Output**: `{share_token, share_url, expires_at}`
  - **Token Duration**: 7 days
  - **Scope**: Single worker's read-only data

- [ ] Create `/api/v1/workers/verify-share-token` endpoint
  - **Input**: `{share_token}`
  - **Output**: `{worker_id, is_valid, expires_in}`
  - **Validation**: Check expiry, validate signature

- [ ] Add share token table to Supabase
  ```sql
  share_tokens
  ├─ id UUID
  ├─ worker_id UUID (FK)
  ├─ token TEXT UNIQUE
  ├─ created_at TIMESTAMP
  ├─ expires_at TIMESTAMP
  ├─ is_used BOOLEAN
  └─ use_count INTEGER
  ```

### Phase 2: Frontend Modifications
- [ ] Create `/link/:shareToken/profile` route
  - [ ] Extract token from URL
  - [ ] Verify token with backend
  - [ ] Load profile data
  - [ ] Show different UI for shared links (no admin features)

- [ ] Create `/link/:shareToken/status` route
  - [ ] Token validation
  - [ ] Load zone status data
  - [ ] Real-time updates every 5 min

- [ ] Create `/link/:shareToken/history` route
  - [ ] Token validation
  - [ ] Load payout history

- [ ] Create `SharedLinkRoute` wrapper component
  ```jsx
  // Wraps all shareable link routes
  // Handles token validation
  // Different from ProtectedRoute
  ```

- [ ] Create token validation hook
  ```javascript
  useShareToken(shareToken)
  // Returns: { isValid, workerId, loading, error }
  ```

### Phase 3: WhatsApp Bot Integration
- [ ] Update message handler for "PROFILE", "STATUS", "HISTORY" commands
- [ ] Add function to generate and send share links
- [ ] Store last generated link with expiry
- [ ] Handle link clicks (optional, track via URL params)

### Phase 4: Database Integration
- [ ] Ensure all worker PWA pages use Supabase queries
- [ ] Add database connection layer for real-time listening
- [ ] Cache strategies for DCI zone data
- [ ] Error handling for missing/invalid worker data

---

## 📊 Database Schema Requirements

```sql
-- Existing tables to use
workers          -- Worker profiles
payouts          -- Payout history
dci_logs         -- Zone DCI readings
policies         -- Worker policies

-- New table for share tokens
CREATE TABLE share_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  worker_id UUID NOT NULL REFERENCES workers(id),
  token TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT now(),
  expires_at TIMESTAMP NOT NULL,
  is_used BOOLEAN DEFAULT false,
  use_count INTEGER DEFAULT 0,
  max_uses INTEGER DEFAULT NULL, -- NULL = unlimited
  created_by TEXT, -- 'bot' or 'web'
  notes TEXT
);

-- Index for fast lookups
CREATE INDEX idx_share_tokens_token ON share_tokens(token);
CREATE INDEX idx_share_tokens_worker_id ON share_tokens(worker_id);
CREATE INDEX idx_share_tokens_expires_at ON share_tokens(expires_at);
```

---

## 🔄 Data Flow Diagram

### Worker Initiates Status Check
```
Worker: "STATUS"
    ↓
Bot Handler
    ├─ Get phone → Look up worker_id
    ├─ POST /api/v1/workers/generate-share-token
    │  → Get shareToken & shareUrl
    ├─ Send WhatsApp message with link:
    │  "📊 Your current status:
    │   https://app.gigkavach.com/link/{shareToken}/status"
    └─ Store link in session (optional)
    
Worker clicks link
    ↓
Frontend: /link/{shareToken}/status
    ├─ Extract shareToken from URL
    ├─ POST /api/v1/workers/verify-share-token
    │  → Validate token, get worker_id
    ├─ Fetch real-time zone data
    │  GET /api/v1/dci/pincode/{pincode}
    └─ Display status page
```

---

## 🎨 UI Differentiation

### Admin Dashboard
- Full navigation sidebar
- Admin-only features (Fraud, Analytics)
- Worker management features
- Settings & configuration

### Worker PWA (Session Auth)
- Simplified mobile-first UI
- Back button to previous page
- Read-only view of own data
- Account summary

### Shareable Links (Token Auth)
- **Same as Worker PWA BUT:**
- No account/profile navigation
- No settings or preferences
- Clear expiry warning if link near expiration
- Watermark: "Shared Link - Expires {date}"
- Option to login and create session

---

## 🚀 Implementation Priority

### Priority 1: Critical (v1)
1. Create share token endpoints (backend)
2. Create shareable link routes (frontend)
3. Update WhatsApp bot message handler
4. Database integration for worker data

### Priority 2: Important (v2)
1. Share token analytics (track uses)
2. Link expiry warnings
3. Session upgrade from share link to full login
4. Real-time updates optimization

### Priority 3: Nice-to-Have (v3)
1. QR codes for direct access
2. Share link revocation
3. Multiple active links per worker
4. Link usage analytics & notifications

---

## 🧪 Testing Scenarios

### Scenario 1: Valid Share Link
```
1. Generate share token for worker
2. Click link before expiry
3. Verify page loads correctly
4. Verify only worker's data shows
5. Verify data is current
```

### Scenario 2: Expired Share Link
```
1. Generate share token (set to expire in 1 hour)
2. Wait for expiry
3. Click link
4. Verify expires message and login option
```

### Scenario 3: WhatsApp Integration
```
1. Worker sends "STATUS" on WhatsApp
2. Bot generates share link
3. Worker receives message with link
4. Click link and verify data loads
5. Back button returns to WhatsApp
```

### Scenario 4: Session Upgrade
```
1. Worker accessing via share link
2. Click "Get Full Access" or "Login"
3. Redirect to /login
4. After login, maintain data viewing
5. User can now access other features
```

---

## 🔐 Security Considerations

1. **Token Expiry**: Short-lived (7 days default, configurable)
2. **Single-Use Tokens**: Optional feature (use_count tracking)
3. **Rate Limiting**: Prevent share token generation spam
4. **Scope**: Tokens only allow read access to specific worker's data
5. **HTTPS Only**: All share links must use HTTPS
6. **Referrer Policy**: Prevent leaking share tokens in referrer headers

---

## 📈 Metrics to Track

1. Share token generation count
2. Share link click-through rate
3. Time from generation to first click
4. Conversion rate: Share link → Login → Full session
5. Error rate for expired/invalid tokens
6. Average session duration from share links
