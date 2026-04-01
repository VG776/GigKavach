"""
EARNINGS FINGERPRINT — Implementation & Usage Guide
════════════════════════════════════════════════════════

This is a quick reference for the GigKavach Earnings Fingerprint module,
which calculates worker baseline earnings for payout determination.

File: /backend/ml/earnings_fingerprint.py
Tests: /backend/tests/test_earnings_fingerprint.py (46 comprehensive unit tests)

───────────────────────────────────────────────────────────────────────────────
WHAT IS THE EARNINGS FINGERPRINT?
───────────────────────────────────────────────────────────────────────────────

The Earnings Fingerprint computes a worker's expected daily earnings baseline
using a rolling 4-week median, per day-of-week. It's used by the payout engine
to calculate how much a worker should receive during income disruption.

Key Features:
  ✓ Rolling 4-week median (not mean) → Robust to outlier days
  ✓ Per-day-of-week calculation → Monday earnings ≠ Friday earnings
  ✓ Disruption filtering (DCI > 65) → Excludes crisis earnings patterns
  ✓ Festival week filtering → Excludes surge periods
  ✓ New worker blending → Gradual transition from city average to personal data
  ✓ Database persistence → Saved to workers table for payout reference

───────────────────────────────────────────────────────────────────────────────
QUICK START
───────────────────────────────────────────────────────────────────────────────

1. CALCULATE & PERSIST BASELINE

    from ml.earnings_fingerprint import compute_and_persist_baseline

    success, baseline = compute_and_persist_baseline("worker_12345")

    if success:
        print(f"Baseline saved: {baseline}")
        # Output: {
        #   "monday": 750,
        #   "tuesday": 780,
        #   "wednesday": 800,
        #   "thursday": 820,
        #   "friday": 880,
        #   "saturday": 920,
        #   "sunday": 900,
        #   "overall_daily_avg": 835
        # }


2. GET BASELINE ONLY (without persistence)

    from ml.earnings_fingerprint import calculate_baseline

    baseline = calculate_baseline("worker_12345")
    print(baseline["monday"])  # ₹750
    print(baseline["overall_daily_avg"])  # ₹835


3. SAVE BASELINE MANUALLY

    from ml.earnings_fingerprint import calculate_baseline, save_baseline_to_workers_table

    baseline = calculate_baseline("worker_12345")
    save_baseline_to_workers_table("worker_12345", baseline)


───────────────────────────────────────────────────────────────────────────────
HOW THE BASELINE IS CALCULATED
───────────────────────────────────────────────────────────────────────────────

STEP 1: Fetch Activity Data
  → Query activity_log table for 28 days of earnings history
  → Columns: date, daily_earnings, dci_score, platform, shift

STEP 2: Filter Disruption Days
  → Remove all days where DCI_score > 65
  → These are crisis days with abnormal earnings patterns
  → Prevents skewing baseline with one-off income loss events

STEP 3: Filter Festival Weeks
  → Remove known festival/holiday weeks (Holi, Diwali, New Year, etc.)
  → These weeks have surge pricing and abnormal earnings patterns
  → Defined in FESTIVAL_WEEKS constant (month, week_number tuples)

STEP 4: Remove Outliers
  → Use IQR method: Remove values outside [Q1-1.5×IQR, Q3+1.5×IQR]
  → Prevents single abnormally high/low days from skewing median
  → Median is naturally outlier-robust, but we still filter

STEP 5: Calculate Median Per Day-of-Week
  → For each day (Monday-Sunday): median(earnings for that day)
  → Example: All Mondays in 4 weeks → median → Monday baseline
  → Days with no data → baseline = 0
  → Overall average = median of all remaining days

STEP 6: Check Worker Age & Blend (if < 5 weeks registered)
  → Week 1-2: 100% city-average (worker too new)
  → Week 3: 30% personal + 70% city
  → Week 4: 60% personal + 40% city
  → Week 5+: 100% personal

STEP 7: Save to Database
  → Update workers table: baseline_earnings column
  → Also record baseline_updated_at timestamp
  → Used by payout_service.py for calculating payouts

───────────────────────────────────────────────────────────────────────────────
INTEGRATION WITH PAYOUT SERVICE
───────────────────────────────────────────────────────────────────────────────

When a disruption triggers a payout (DCI ≥ 65), the payout service:

    1. Fetches baseline from workers table
    2. Calculates disrupted_hours = time DCI was ≥ 65 during worker's shift
    3. lost_earnings = baseline[day_of_week] * (disrupted_hours / shift_hours)
    4. payout_amount = lost_earnings * coverage_percentage[plan]
    5. Sends payout via Razorpay UPI

Example:
    Baseline Monday: ₹750
    Coverage: Shield Plus (50%)
    Disrupted: 4 hours out of 12-hour shift
    Lost earnings: ₹750 × (4/12) = ₹250
    Actual payout: ₹250 × 50% = ₹125 sent to UPI

───────────────────────────────────────────────────────────────────────────────
KEY CONSTANTS & CONFIGURATION
───────────────────────────────────────────────────────────────────────────────

LOOKBACK_DAYS = 28
  → 4-week rolling window for baseline calculation
  → Matches database activity_log retention period

DCI_DISRUPTION_THRESHOLD = 65
  → DCI score above this indicates significant disruption
  → Days with DCI > 65 are filtered from baseline

FESTIVAL_WEEKS = {...}
  → Tuples of (month, week_number) for major Indian holidays
  → (1, 1) = first week of January (New Year)
  → (3, 2) = second week of March (Holi)
  → etc.

NEW_WORKER_BLEND_SCHEDULE = {1: (0%, 100%), 2: (0%, 100%), ...}
  → Week-by-week blending percentages (personal%, city%)

───────────────────────────────────────────────────────────────────────────────
NEW WORKER BLENDING LOGIC
───────────────────────────────────────────────────────────────────────────────

Why blend?
  New workers have incomplete earning history.
  Using only their personal data (1-4 days) is unreliable.
  Blending with city-average provides reasonable baseline until personal data is sufficient.

Transition Timeline:
  Week 1 start:  JOIN via WhatsApp → 24-hour coverage delay begins
  Day 2 start:   Coverage activates → Start earning history
  Week 1 data:   Can't process payout yet (< 24 hours old)
  Week 2 data:   First disruption payout possible
               → Use 100% city-average (only 7-14 days personal data)
  Week 3 start:  Use 30% personal + 70% city-average
  Week 4 start:  Use 60% personal + 40% city-average
  Week 5 start:  Use 100% personal baseline (28+ days of history)

───────────────────────────────────────────────────────────────────────────────
UNIT TESTS (46 Total)
───────────────────────────────────────────────────────────────────────────────

Run tests:
    pytest backend/tests/test_earnings_fingerprint.py -v

Test Coverage:
  ✓ Festival week detection (4 tests)
  ✓ Disruption day filtering (5 tests)
  ✓ Activity data filtering (5 tests)
  ✓ Rolling median calculation (4 tests)
  ✓ New worker blending (5 tests)
  ✓ Weeks-since-registration (5 tests)
  ✓ City-average fallback (5 tests)
  ✓ Main baseline calculation (3 tests)
  ✓ Database persistence (3 tests)
  ✓ Orchestration workflows (3 tests)
  ✓ Edge cases & boundaries (4 tests)

───────────────────────────────────────────────────────────────────────────────
COMMON USAGE PATTERNS
───────────────────────────────────────────────────────────────────────────────

Pattern 1: Calculate baseline only (read-only)
    
    baseline = calculate_baseline("w_123")
    monday_baseline = baseline.get("monday", 0)
    overall_baseline = baseline["overall_daily_avg"]

Pattern 2: Full workflow (calculate + persist)

    success, baseline = compute_and_persist_baseline("w_123")
    if success:
        log.info(f"Baseline calculated for worker: {baseline}")
    else:
        log.error("Failed to calculate baseline")

Pattern 3: Custom Supabase client (testing/specific env)

    from utils.supabase_client import get_supabase
    sb = get_supabase()
    baseline = calculate_baseline("w_123", supabase_client=sb)

Pattern 4: Get city average for reference

    city_avg = fetch_city_segment_average("Bengaluru", "food_delivery")
    print(city_avg["overall_daily_avg"])  # ₹743

Pattern 5: Check if worker is new and needs blending

    metadata = fetch_worker_metadata("w_123")
    weeks = get_weeks_since_registration(metadata["registration_date"])
    if weeks < 5:
        print(f"Worker still in blending (Week {weeks})")

───────────────────────────────────────────────────────────────────────────────
DEBUGGING & TROUBLESHOOTING
───────────────────────────────────────────────────────────────────────────────

Issue: Baseline is 0 for all days
Solution:
  1. Check activity_log has data for worker (must have 7+ days)
  2. Ensure DCI scores exist (not all null)
  3. Verify dates are valid ISO format (YYYY-MM-DD)
  4. Check for festival weeks removing all data

Issue: Baseline unexpectedly low
Causes:
  1. Recent disruption days (DCI > 65) included in data
  2. Worker on planned leave (zero earnings days)
  3. Festival week inflating or skewing data
  4. Small sample size (< 1 week) for some days of week

Solution:
  → Check activity_log directly for data quality
  → Review DCI scores during the lookback period
  → Verify festival week calendar is correct for region

Issue: New worker baseline not blending correctly
Debug:
  1. Check registration_date in workers table
  2. Verify get_weeks_since_registration() returns correct week
  3. Ensure city-average exists: fetch_city_segment_average()
  4. Check blend percentages: NEW_WORKER_BLEND_SCHEDULE

───────────────────────────────────────────────────────────────────────────────
PERFORMANCE NOTES
───────────────────────────────────────────────────────────────────────────────

Function                           Time Complexity    Notes
─────────────────────────────────────────────────────────────────────────────
calculate_baseline()               O(N) N=28 days     Fetches & filters 4 weeks
calculate_rolling_median_per_dow() O(N log N)         Median calculation
filter_activity_data()             O(N)               Single pass filtering
blend_baselines_for_new_worker()   O(1)               Simple arithmetic

Typical execution time: < 200ms for a single worker

Optimization:
  → Baselines are cached in workers.baseline_earnings
  → Only recalculate daily or after disruption events
  → Batch calculate for multiple workers if needed

───────────────────────────────────────────────────────────────────────────────
DATABASE SCHEMA REQUIREMENTS
───────────────────────────────────────────────────────────────────────────────

Tables required:

1. workers
   - id (TEXT, PRIMARY KEY)
   - baseline_earnings (JSONB) ← Updated by save_baseline_to_workers_table()
   - baseline_updated_at (TIMESTAMP)
   - registration_date (DATE)
   - city (TEXT)
   - segment (TEXT)
   - ... other fields

2. activity_log
   - worker_id (TEXT, FOREIGN KEY)
   - date (DATE)
   - daily_earnings (NUMERIC)
   - dci_score (NUMERIC)
   - platform (TEXT)
   - shift (TEXT)

3. dci_events (for DCI scores during activity period)
   - pincode (VARCHAR)
   - total_score (INTEGER)
   - created_at (TIMESTAMP)

───────────────────────────────────────────────────────────────────────────────
EXTENDING THE MODULE
───────────────────────────────────────────────────────────────────────────────

To add support for monthly seasonal adjustment:

    def apply_seasonal_adjustment(baseline, month):
        \"\"\"Scale baseline by seasonal factors\"\"\"
        seasonal_factors = {
            1: 0.9,   # January is slower
            6: 1.1,   # June has monsoon surge
            12: 0.8,  # December holiday effects
        }
        factor = seasonal_factors.get(month, 1.0)
        return {k: v * factor for k, v in baseline.items()}

To add skill-level weighting:

    def weight_by_skill_level(baseline, skill_level):
        \"\"\"New workers on salary vs experienced (independent)\"\"\"
        if skill_level == "new":
            return baseline * 0.8  # New workers earn less
        return baseline  # Experienced workers use full baseline

...and remember to add unit tests!

═════════════════════════════════════════════════════════════════════════════════
"""
