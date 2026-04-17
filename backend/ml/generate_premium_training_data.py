#!/usr/bin/env python3
"""
ml/generate_premium_training_data.py
────────────────────────────────────────────────────────────
Generates 1000 synthetic workers with realistic distributions for
premium model training.

Features generated:
- Worker demographics: age (20-50), zones across Karnataka
- Work patterns: shifts (morning/day/night/flexible), platforms (70% Swiggy, 30% Zomato)
- Financial: monthly earnings (₹15K-₹30K), claim patterns
- Risk profile: 5% high-risk, 80% medium, 15% low-risk

Output: data/premium_training_data.csv

Run with:
    python ml/generate_premium_training_data.py
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("generate_premium_data")

# Get project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "premium_training_data.csv")

# Karnataka pincode zones (representative pincodes across Karnataka)
KARNATAKA_ZONES = {
    "560001": "Bangalore City",
    "560037": "Doddanekkundi",
    "560038": "Indiranagar",
    "560068": "Bommanahalli",
    "560095": "Mahadevapura",
    "570001": "Mysore",
    "575001": "Mangalore",
    "591204": "Belgaum",
    "580001": "Hubli",
    "563001": "Kolar",
}

SHIFTS = ["morning", "day", "night", "flexible"]
PLATFORMS = ["Swiggy", "Zomato"]
RISK_LEVELS = ["low", "medium", "high"]

def generate_synthetic_workers(n_samples: int = 1000) -> pd.DataFrame:
    """Generate 1000 synthetic workers with realistic distributions."""
    logger.info(f"Generating {n_samples} synthetic workers...")
    np.random.seed(42)
    
    data = {
        "worker_id": [f"worker_{i:04d}" for i in range(n_samples)],
        "age": np.random.uniform(20, 50, n_samples).astype(int),
        "zone": np.random.choice(list(KARNATAKA_ZONES.keys()), n_samples),
        "shift": np.random.choice(SHIFTS, n_samples, p=[0.2, 0.4, 0.3, 0.1]),
        "primary_platform": np.random.choice(PLATFORMS, n_samples, p=[0.7, 0.3]),
        "monthly_earnings": np.random.uniform(15000, 30000, n_samples).astype(int),
        "risk_level": np.random.choice(RISK_LEVELS, n_samples, p=[0.15, 0.80, 0.05]),
    }
    
    df = pd.DataFrame(data)
    
    # Derive additional features based on risk level
    logger.info("Deriving features based on risk profiles...")
    
    # GigScore: inversely correlated with risk level
    df["gig_score"] = df["risk_level"].apply(lambda x: {
        "high": np.random.normal(55, 10, 1)[0],
        "medium": np.random.normal(80, 8, 1)[0],
        "low": np.random.normal(90, 6, 1)[0],
    }[x])
    df["gig_score"] = np.clip(df["gig_score"], 20, 100).astype(float)
    
    # Claim frequency per month: based on earnings and accidents
    df["claims_per_month"] = df.apply(
        lambda row: np.random.poisson(
            0.1 if row["risk_level"] == "low" else
            0.3 if row["risk_level"] == "medium" else
            0.6
        ),
        axis=1
    )
    
    # Days worked per month
    df["days_worked"] = np.random.normal(22, 3, n_samples).astype(int)
    df["days_worked"] = np.clip(df["days_worked"], 10, 30)
    
    # Average DCI in their zone (30-day)
    df["zone_avg_dci_30d"] = np.random.uniform(20, 60, n_samples).astype(float)
    
    # Predicted 7-day max DCI for their zone
    df["zone_pred_dci_7d"] = df["zone_avg_dci_30d"] + np.random.uniform(10, 30, n_samples)
    df["zone_pred_dci_7d"] = np.clip(df["zone_pred_dci_7d"], 0, 100).astype(float)
    
    # Account tenure (months) - affects trust
    df["tenure_months"] = np.random.exponential(scale=12, size=n_samples).astype(int) + 1
    df["tenure_months"] = np.clip(df["tenure_months"], 1, 60)
    
    # Derive premium target: discount_multiplier based on business rules
    logger.info("Deriving discount multipliers...")
    
    discounts = []
    for idx, row in df.iterrows():
        score = row["gig_score"]
        avg_dci = row["zone_avg_dci_30d"]
        pred_dci = row["zone_pred_dci_7d"]
        shift_night = 1 if row["shift"] == "night" else 0
        risk_level = row["risk_level"]
        
        # Base rule: no trust = no discount
        if score < 70:
            discount = 0.0
        else:
            # Score-based discount: more trust = more discount
            base = ((score - 70) / 30.0) * 0.20
            
            # Zone safety bonus: lower avg_DCI = more discount
            zone_boost = max(0, (50 - avg_dci) / 50.0 * 0.10)
            
            # Risk penalty: predicted high DCI = less discount
            risk_penalty = max(0, (pred_dci - 40) / 60.0 * 0.25)
            
            # Night shift bonus: +5% for night workers (extra risk)
            night_bonus = 0.05 if shift_night else 0.0
            
            # Risk level adjustment
            risk_adj = {
                "high": -0.05,    # High-risk workers get less discount
                "medium": 0.0,    # Medium-risk baseline
                "low": 0.03       # Low-risk workers get slight bonus
            }[risk_level]
            
            discount = base + zone_boost - risk_penalty + night_bonus + risk_adj
        
        # Add realistic noise
        noise = np.random.normal(0, 0.032, 1)[0]
        discount = discount + noise
        
        # Clamp to valid range [0.0, 0.30]
        discount = np.clip(discount, 0.0, 0.30)
        discounts.append(discount)
    
    df["discount_multiplier"] = discounts
    
    # Shift one-hot encoding for training
    logger.info("Creating one-hot encoded shift features...")
    df["shift_morning"] = (df["shift"] == "morning").astype(int)
    df["shift_day"] = (df["shift"] == "day").astype(int)
    df["shift_night"] = (df["shift"] == "night").astype(int)
    df["shift_flexible"] = (df["shift"] == "flexible").astype(int)
    
    # Rename for compatibility with model training
    df = df.rename(columns={
        "gig_score": "worker_gig_score",
        "zone_avg_dci_30d": "pincode_30d_avg_dci",
        "zone_pred_dci_7d": "predicted_7d_max_dci",
    })
    
    return df

def main():
    """Main execution."""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Generate synthetic workers
    df = generate_synthetic_workers(1000)
    
    # Display statistics
    logger.info("\n" + "=" * 60)
    logger.info("Generated Synthetic Worker Dataset Statistics")
    logger.info("=" * 60)
    logger.info(f"Total workers: {len(df)}")
    logger.info(f"\nAge distribution:")
    logger.info(f"  Mean: {df['age'].mean():.1f} years")
    logger.info(f"  Range: {df['age'].min()}-{df['age'].max()} years")
    logger.info(f"\nMonthly earnings distribution:")
    logger.info(f"  Mean: ₹{df['monthly_earnings'].mean():.0f}")
    logger.info(f"  Range: ₹{df['monthly_earnings'].min()}-₹{df['monthly_earnings'].max()}")
    logger.info(f"\nGigScore distribution:")
    logger.info(f"  Mean: {df['worker_gig_score'].mean():.1f}")
    logger.info(f"  Median: {df['worker_gig_score'].median():.1f}")
    logger.info(f"  Range: {df['worker_gig_score'].min():.1f}-{df['worker_gig_score'].max():.1f}")
    logger.info(f"\nDiscount multiplier distribution:")
    logger.info(f"  Mean: {df['discount_multiplier'].mean():.4f}")
    logger.info(f"  Median: {df['discount_multiplier'].median():.4f}")
    logger.info(f"  Std Dev: {df['discount_multiplier'].std():.4f}")
    logger.info(f"  Range: {df['discount_multiplier'].min():.4f}-{df['discount_multiplier'].max():.4f}")
    
    logger.info(f"\nShift distribution:")
    for shift, count in df["shift"].value_counts().items():
        pct = 100 * count / len(df)
        logger.info(f"  {shift}: {count} ({pct:.1f}%)")
    
    logger.info(f"\nPlatform distribution:")
    for platform, count in df["primary_platform"].value_counts().items():
        pct = 100 * count / len(df)
        logger.info(f"  {platform}: {count} ({pct:.1f}%)")
    
    logger.info(f"\nRisk level distribution:")
    for level, count in df["risk_level"].value_counts().items():
        pct = 100 * count / len(df)
        logger.info(f"  {level}: {count} ({pct:.1f}%)")
    
    logger.info(f"\nZone distribution (top 5):")
    for zone, count in df["zone"].value_counts().head().items():
        logger.info(f"  {zone} ({KARNATAKA_ZONES.get(zone, 'Unknown')}): {count}")
    
    # Save to CSV
    logger.info(f"\nSaving to {OUTPUT_PATH}...")
    df.to_csv(OUTPUT_PATH, index=False)
    logger.info(f"✅ Dataset saved successfully!")
    
    # Display sample rows
    logger.info(f"\nSample rows (first 5):")
    sample_cols = [
        "worker_id", "worker_gig_score", "pincode_30d_avg_dci",
        "predicted_7d_max_dci", "shift_morning", "shift_day",
        "shift_night", "shift_flexible", "discount_multiplier"
    ]
    logger.info(f"\n{df[sample_cols].head().to_string()}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"✅ Premium training data generation complete!")
    logger.info(f"   Output: {OUTPUT_PATH}")
    logger.info(f"   Rows: {len(df)}")
    logger.info(f"   Columns: {len(df.columns)}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
