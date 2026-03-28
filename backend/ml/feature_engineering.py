"""
ml/feature_engineering.py
────────────────────────────────────────────────────
Generates a synthetic historical dataset for GigKavach DCI events,
performs scikit-learn feature engineering, and splits it for the XGBoost payout model.

KEY FIXES (v2):
  ✅ Data Leakage: Scaler fitted ONLY on training data (fit_transform → fit, then transform)
  ✅ Feature Design: Removed duration from features (applied post-multiplier in formula)
  ✅ Interactions: Added DCI × disruption_type & DCI × shift interactions
  ✅ Granularity: Added zone_density feature (high/mid/low based on pin-code)
"""

import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer

# Paths
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data")
os.makedirs(DATA_DIR, exist_ok=True)

def generate_synthetic_data(num_records=5000) -> pd.DataFrame:
    """Creates synthetic disruption data mapping parameters to payout multipliers.
    
    ENHANCED (v3): Richer patterns for more realistic modeling
      • Monsoon seasonality (June-Sept higher for Bengaluru)
      • Time-of-day demand curves (12-2pm, 7-9pm peak hours)
      • Day-of-week effects (Friday night disruption > Tuesday morning)
      • Zone × disruption_type interactions (waterlogging hits low-density, 
        traffic gridlock hits CBD harder)
      • Baseline earnings tiers (lower earnings = higher vulnerability)
    
    NEW: Includes zone_density and removes duration from features
    (duration is applied post-multiplier in the formula).
    """
    print(f"Generating {num_records} synthetic records with ENHANCED patterns...")
    
    cities = ['Bengaluru', 'Mumbai', 'Delhi', 'Chennai']
    shifts = ['Morning', 'Evening', 'Night']
    disruption_types = ['Rain', 'Heatwave', 'Flood', 'Traffic_Gridlock']
    zone_densities = ['High', 'Mid', 'Low']  # NEW: CBD vs suburb vs outskirts
    
    np.random.seed(42)
    
    # Generate month data to model seasonality
    months = np.random.randint(1, 13, num_records)  # 1-12
    
    data = {
        'dci_score': np.random.randint(0, 101, num_records), # 0-100
        'disruption_duration': np.random.randint(15, 360, num_records), # 15 to 360 mins (NOT in features)
        'baseline_earnings': np.random.uniform(100.0, 2500.0, num_records), # INR
        'city': np.random.choice(cities, num_records),
        'zone_density': np.random.choice(zone_densities, num_records),  # NEW: Geographic granularity
        'shift': np.random.choice(shifts, num_records),
        'disruption_type': np.random.choice(disruption_types, num_records),
        'hour_of_day': np.random.randint(0, 24, num_records),
        'day_of_week': np.random.randint(0, 7, num_records),
        'month': months,  # For seasonality
    }
    
    df = pd.DataFrame(data)
    
    # Calculate a synthetic TARGET variable (payout_multiplier)
    def calculate_synthetic_target(row):
        base = 1.0
        
        # Non-linear DCI weight (exponential curve)
        base += (row['dci_score'] / 100.0) ** 1.5 * 1.2
        
        # ──────────────────────────────────────────────────────
        # ENHANCED: Category 1 - Richer Synthetic Patterns
        # ──────────────────────────────────────────────────────
        
        # 1. MONSOON SEASONALITY (Jun-Sep higher disruption for Bengaluru)
        # During monsoon months, disruptions are more impactful
        if row['city'] == 'Bengaluru' and 6 <= row['month'] <= 9:  # June-September
            # Higher baseline risk during monsoon
            base *= 1.15
            # Monsoon-specific disruptions (rain/flood) much worse
            if row['disruption_type'] in ['Rain', 'Flood']:
                base += 0.35
        elif row['month'] in [6, 7, 8, 9]:  # Monsoon for other cities too
            if row['disruption_type'] in ['Rain', 'Flood']:
                base += 0.20
        
        # 2. TIME-OF-DAY DEMAND CURVES (Peak delivery hours: 12-2pm, 7-9pm)
        # Deliveries spike at lunch and dinner, so disruption hits worse then
        peak_hours = [12, 13, 14, 19, 20, 21]  # 12-2pm and 7-9pm
        off_peak_hours = [2, 3, 4, 5]  # 2-5am lowest demand
        
        if row['hour_of_day'] in peak_hours:
            base *= 1.25  # Peak hours: disruption costs more income
        elif row['hour_of_day'] in off_peak_hours:
            base *= 0.75  # Off-peak: less impact
        
        # 3. DAY-OF-WEEK EFFECTS (Friday night >> Tuesday morning economically)
        # Friday-Sunday = higher delivery demand
        # Monday = recovery day
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_of_week_weights = {
            0: 0.90,  # Monday: low demand (recovery)
            1: 0.95,  # Tuesday
            2: 1.00,  # Wednesday: baseline
            3: 1.05,  # Thursday
            4: 1.25,  # Friday: high demand
            5: 1.20,  # Saturday: high demand
            6: 1.15,  # Sunday: medium-high
        }
        base *= day_of_week_weights.get(row['day_of_week'], 1.0)
        
        # 4. ZONE × DISRUPTION TYPE INTERACTIONS (NEW pattern)
        # Waterlogging (rain/flood) hits low-density areas harder (poor drainage)
        # Traffic gridlock hits high-density CBD areas harder (congestion-sensitive)
        if row['zone_density'] == 'Low':
            if row['disruption_type'] in ['Rain', 'Flood']:
                base += 0.40  # Low-density areas: poor drainage, high impact
        elif row['zone_density'] == 'High' and row['dci_score'] > 50:
            if row['disruption_type'] == 'Traffic_Gridlock':
                base += 0.45  # High-density CBD: traffic gridlock devastating
        
        # Original zone multiplier (resilience factor)
        zone_multipliers = {'High': 1.15, 'Mid': 1.0, 'Low': 0.85}
        base *= zone_multipliers.get(row['zone_density'], 1.0)
        
        # 5. BASELINE EARNINGS TIERS (Vulnerability gradient)
        # Workers earning <₹500/day more vulnerable to disruptions
        # Workers earning >₹2000/day have buffer
        if row['baseline_earnings'] < 500:
            base *= 1.20  # Very vulnerable
        elif row['baseline_earnings'] < 1000:
            base *= 1.10  # Somewhat vulnerable
        elif row['baseline_earnings'] > 2000:
            base *= 0.90  # Less vulnerable (financial buffer)
        
        # ──────────────────────────────────────────────────────
        # Original patterns (still important)
        # ──────────────────────────────────────────────────────
        
        # Disruption type effects
        if row['disruption_type'] == 'Heatwave' and 10 <= row['hour_of_day'] <= 16:
            base += 0.5  # Peak heat hours
        if row['disruption_type'] in ['Rain', 'Flood'] and row['shift'] == 'Night':
            base += 0.7
        
        # DCI × Shift interaction: Night shifts amplify high DCI impact
        if row['shift'] == 'Night' and row['dci_score'] > 70:
            base += 0.2
        
        # DCI × Disruption Type interactions (explicit)
        if row['disruption_type'] == 'Traffic_Gridlock' and row['dci_score'] > 75:
            base += 0.25  # Traffic gridlock at high DCI = very high impact
        if row['disruption_type'] == 'Flood' and row['dci_score'] > 80:
            base += 0.3   # Floods at high DCI = severe
        
        # 2% chance of random edge cases (manager overrides, emergencies)
        if np.random.random() < 0.02:
            base += np.random.uniform(1.0, 2.5)
            
        # Moderate gaussian noise (realistic variance)
        base += np.random.normal(0, 0.15)
        
        # Bound the multiplier between 1.0 and 5.0
        return round(float(np.clip(base, 1.0, 5.0)), 2)
        
    df['target_payout_multiplier'] = df.apply(calculate_synthetic_target, axis=1)
    
    # Drop the month column before returning (used only for synthetic generation)
    df = df.drop(columns=['month'])
    
    return df

def process_data(df: pd.DataFrame):
    """
    Normalizes, encodes, and splits the data.
    
    ⚠️ CRITICAL FIX: Scaler fitted ONLY on training data to prevent data leakage!
    """
    print("="*70)
    print("📊 FEATURE ENGINEERING PIPELINE (v2 - Data Leakage Fixed)")
    print("="*70)
    
    # Define feature categories (EXCLUDING disruption_duration)
    # Duration is applied post-multiplier in the payout formula
    numerical_features = ['dci_score', 'baseline_earnings', 'hour_of_day', 'day_of_week']
    categorical_features = ['city', 'zone_density', 'shift', 'disruption_type']
    target = 'target_payout_multiplier'
    
    # ✅ CRITICAL: Train/Test split FIRST (before any preprocessing)
    print("\n1️⃣  Splitting train/test (80/20) BEFORE preprocessing...")
    X_raw = df[numerical_features + categorical_features + ['disruption_duration']]
    y = df[target]
    
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X_raw, y, test_size=0.20, random_state=42
    )
    
    print(f"   X_train: {X_train_raw.shape[0]} samples")
    print(f"   X_test: {X_test_raw.shape[0]} samples")
    
    # ✅ CRITICAL: Fit preprocessor ONLY on training data
    print("\n2️⃣  Fitting preprocessor on TRAINING SET ONLY...")
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numerical_features),
            ('cat', OneHotEncoder(sparse_output=False, drop='first'), categorical_features)
        ]
    )
    
    # Fit only on training data
    X_train_base = X_train_raw[numerical_features + categorical_features]
    X_train_processed = preprocessor.fit_transform(X_train_base)
    
    # ✅ CRITICAL: Transform test set with FITTED preprocessor (never fit_transform)
    print("3️⃣  Transforming test set with fitted preprocessor...")
    X_test_base = X_test_raw[numerical_features + categorical_features]
    X_test_processed = preprocessor.transform(X_test_base)
    
    # Get feature names
    cat_enc = preprocessor.named_transformers_['cat']
    encoded_cat_names = cat_enc.get_feature_names_out(categorical_features)
    base_feature_names = numerical_features + list(encoded_cat_names)
    
    # ✅ NEW: Add explicit interaction features
    print("4️⃣  Adding interaction features (DCI × type, DCI × shift)...")
    
    # Convert to DataFrames for interaction engineering
    X_train_df = pd.DataFrame(X_train_processed, columns=base_feature_names)
    X_test_df = pd.DataFrame(X_test_processed, columns=base_feature_names)
    
    # Get back raw features for interactions
    X_train_raw_reset = X_train_raw[numerical_features + categorical_features].reset_index(drop=True)
    X_test_raw_reset = X_test_raw[numerical_features + categorical_features].reset_index(drop=True)
    
    # Add interaction features based on raw data
    # DCI × Disruption Type interactions
    for disruption_type in ['Rain', 'Heatwave', 'Flood', 'Traffic_Gridlock']:
        col_name = f'disruption_type_{disruption_type}'
        if col_name in base_feature_names:
            # Create interactions: dci_score × disruption_type
            X_train_df[f'dci_x_{col_name}'] = (
                X_train_df['dci_score'] * X_train_df[col_name]
            )
            X_test_df[f'dci_x_{col_name}'] = (
                X_test_df['dci_score'] * X_test_df[col_name]
            )
    
    # DCI × Shift interactions
    for shift in ['Morning', 'Night']:
        col_name = f'shift_{shift}'
        if col_name in base_feature_names:
            X_train_df[f'dci_x_{col_name}'] = (
                X_train_df['dci_score'] * X_train_df[col_name]
            )
            X_test_df[f'dci_x_{col_name}'] = (
                X_test_df['dci_score'] * X_test_df[col_name]
            )
    
    # Zone Density × DCI (high density areas are more resilient to disruptions)
    for zone in ['High', 'Mid']:
        col_name = f'zone_density_{zone}'
        if col_name in base_feature_names:
            X_train_df[f'{col_name}_x_dci'] = (
                X_train_df[col_name] * (1.0 - X_train_df['dci_score'] / 100.0)
            )
            X_test_df[f'{col_name}_x_dci'] = (
                X_test_df[col_name] * (1.0 - X_test_df['dci_score'] / 100.0)
            )
    
    final_feature_names = list(X_train_df.columns)
    
    print(f"   Total features: {len(final_feature_names)}")
    print(f"   Base features: {len(base_feature_names)}")
    print(f"   Interaction features: {len(final_feature_names) - len(base_feature_names)}")
    print(f"\n   New features added:")
    for feat in final_feature_names[len(base_feature_names):]:
        print(f"     • {feat}")
    
    # Save to data folder
    print("\n5️⃣  Saving processed datasets...")
    X_train_df.to_csv(os.path.join(DATA_DIR, "X_train.csv"), index=False)
    X_test_df.to_csv(os.path.join(DATA_DIR, "X_test.csv"), index=False)
    y_train.to_csv(os.path.join(DATA_DIR, "y_train.csv"), index=False)
    y_test.to_csv(os.path.join(DATA_DIR, "y_test.csv"), index=False)
    
    print(f"✅ Processed datasets saved to {DATA_DIR}")
    print(f"   X_train: {X_train_df.shape}")
    print(f"   X_test: {X_test_df.shape}")
    
    # Sanity check
    print("\n6️⃣  Evaluating synthetic data realism...")
    from sklearn.ensemble import RandomForestRegressor
    rf = RandomForestRegressor(n_estimators=20, max_depth=6, random_state=42)
    rf.fit(X_train_df, y_train)
    r2_score = rf.score(X_test_df, y_test)
    
    print("─"*70)
    print(f"📊 Random Forest Benchmark R² Score: {r2_score:.3f}")
    if 0.70 <= r2_score <= 0.88:
        print("✅ PERFECT: Realistic synthetic data with natural noise")
    else:
        print("⚠️  WARNING: R² outside expected range")
    print("─"*70)
    
    return X_train_df.values, X_test_df.values, y_train.values, y_test.values, final_feature_names, preprocessor

if __name__ == "__main__":
    raw_df = generate_synthetic_data()
    process_data(raw_df)
