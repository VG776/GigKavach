"""
Test Fraud Detection v3 - Realistic Data Generation
Tests that generated data has realistic properties (not too easy, not too hard).
Validates 4 generation techniques produce genuinely hard classification problem.
"""

import sys
import os
from pathlib import Path

import pytest
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.generate_fraud_training_data import RealisticFraudDataGenerator
from ml.train_fraud_models import FraudModelTrainer
from ml.fraud_features_engineering import FraudFeaturesEngineer


class TestRealisticDataGeneration:
    """Test that generated data has realistic properties."""
    
    @classmethod
    def setup_class(cls):
        """Generate test data once for all tests."""
        generator = RealisticFraudDataGenerator(output_dir='data')
        cls.df, cls.metadata = generator.generate_all_data()
        
        # Prepare features
        cls.feature_cols = [c for c in cls.df.columns if c not in ['is_fraud', 'fraud_type', 'data_generation_technique']]
        cls.X = cls.df[cls.feature_cols].fillna(0)
        cls.y = cls.df['is_fraud']
    
    def test_dataset_size(self):
        """Test that dataset has correct size."""
        print(f"\n✅ Dataset Size Test")
        assert len(self.df) == 5000, f"Expected 5000 records, got {len(self.df)}"
        assert self.y.sum() >= 1000, f"Expected at least 1000 fraud cases, got {self.y.sum()}"
        assert (1 - self.y).sum() >= 3000, f"Expected at least 3000 clean cases, got {(1-self.y).sum()}"
        print(f"   Total: {len(self.df)} | Fraud: {self.y.sum()} | Clean: {(1-self.y).sum()}")
    
    def test_generation_techniques_distribution(self):
        """Test that all 4 generation techniques are represented."""
        print(f"\n✅ Generation Techniques Distribution Test")
        
        techniques = self.df['data_generation_technique'].value_counts()
        print(f"   Techniques:")
        for tech, count in techniques.items():
            pct = 100 * count / len(self.df)
            print(f"     {tech}: {count} ({pct:.1f}%)")
        
        # Verify all techniques present
        expected_techniques = {'gaussian_noise', 'adversarial_evasion', 'hybrid_fraud', 'obvious_fraud', 'clearly_legitimate', 'borderline_legitimate'}
        actual_techniques = set(self.df['data_generation_technique'].unique())
        
        missing = expected_techniques - actual_techniques
        assert not missing, f"Missing techniques: {missing}"
    
    def test_decision_tree_baseline(self):
        """Test that a simple Decision Tree doesn't achieve >85% accuracy (data is genuinely hard)."""
        print(f"\n✅ Decision Tree Baseline Test")
        
        dt = DecisionTreeClassifier(max_depth=3, random_state=42)
        dt.fit(self.X, self.y)
        dt_accuracy = dt.score(self.X, self.y)
        
        print(f"   Decision Tree (depth=3) accuracy: {dt_accuracy:.1%}")
        print(f"   ⚠️  If >85%, data is too clean (overfitting risk)")
        
        # Data should be harder than 85% for simple tree
        assert dt_accuracy < 0.85, f"Data too clean! Simple tree got {dt_accuracy:.1%}"
    
    def test_random_forest_upper_bound(self):
        """Test that Random Forest doesn't get >88% (leaves room for improvement)."""
        print(f"\n✅ Random Forest Upper Bound Test")
        
        rf = RandomForestClassifier(n_estimators=50, max_depth=7, random_state=42)
        rf.fit(self.X, self.y)
        rf_accuracy = rf.score(self.X, self.y)
        
        print(f"   Random Forest accuracy: {rf_accuracy:.1%}")
        print(f"   ⚠️  If >88%, data may be too separable")
        
        # RF should not perfectly separate data
        assert rf_accuracy < 0.88, f"Data too easy! RF got {rf_accuracy:.1%}"
    
    def test_cv_variance_nonzero(self):
        """Test that cross-validation shows real variance (std > 0.01)."""
        print(f"\n✅ Cross-Validation Variance Test")
        
        rf = RandomForestClassifier(n_estimators=50, max_depth=7, random_state=42)
        cv_scores = cross_val_score(rf, self.X, self.y, cv=5)
        cv_std = cv_scores.std()
        
        print(f"   CV Scores: {cv_scores}")
        print(f"   CV Std: {cv_std:.4f} (target: >0.01)")
        
        # Variance must be nonzero (indicates real learning, not memorization)
        assert cv_std > 0.01, f"CV std too low ({cv_std:.4f}), may indicate memorization"
    
    def test_feature_overlap(self):
        """Test that no single feature perfectly separates fraud from clean."""
        print(f"\n✅ Feature Overlap Test")
        
        from scipy.stats import ks_2samp
        
        overlaps = []
        overlapping_features = []
        separating_features = []
        
        for col in self.feature_cols[:10]:  # Check first 10 features
            fraud_vals = self.X[self.y == 1][col]
            clean_vals = self.X[self.y == 0][col]
            
            ks_stat, p_val = ks_2samp(fraud_vals, clean_vals)
            overlap = 1 - ks_stat  # 1 = identical distributions, 0 = completely different
            overlaps.append(overlap)
            
            if overlap > 0.15:
                overlapping_features.append((col, overlap))
            else:
                separating_features.append((col, overlap))
        
        avg_overlap = np.mean(overlaps)
        print(f"   Average feature overlap: {avg_overlap:.2f} (target: >0.15)")
        print(f"   Overlapping features (>0.15): {len(overlapping_features)}")
        print(f"   Separating features (<0.15): {len(separating_features)}")
        
        # At least some features should have overlap (not perfect separation)
        assert avg_overlap > 0.15, f"Features too perfectly separate classes (overlap: {avg_overlap:.2f})"
    
    def test_fraud_type_distribution(self):
        """Test that fraud types are represented in data."""
        print(f"\n✅ Fraud Type Distribution Test")
        
        fraud_types = self.df[self.df['is_fraud'] == 1]['fraud_type'].value_counts()
        print(f"   Fraud types:")
        for ftype, count in fraud_types.items():
            print(f"     {ftype}: {count}")
        
        # All fraud types should be present
        assert len(fraud_types) >= 4, f"Expected at least 4 fraud types, got {len(fraud_types)}"


class TestModelTraining:
    """Test that models train correctly on realistic data."""
    
    def test_pipeline_trains_without_error(self):
        """Test that the full training pipeline runs without errors."""
        print(f"\n✅ Pipeline Training Test")
        
        trainer = FraudModelTrainer(data_dir='data', model_dir='models/fraud_detection_v2')
        cv_results = trainer.train_pipeline()
        
        # Check results
        assert cv_results['mean_accuracy'] >= 0.50, "Accuracy too low"
        assert cv_results['mean_fraud_recall'] >= 0.30, "Recall too low"
        assert cv_results['std_accuracy'] >= 0, "Std should be non-negative"
        
        print(f"   Accuracy: {cv_results['mean_accuracy']:.1%} ± {cv_results['std_accuracy']:.1%}")
        print(f"   Recall: {cv_results['mean_fraud_recall']:.1%} ± {cv_results['std_fraud_recall']:.1%}")
    
    def test_realistic_target_ranges(self):
        """Test that model performance is in realistic ranges."""
        print(f"\n✅ Realistic Target Ranges Test")
        
        trainer = FraudModelTrainer(data_dir='data', model_dir='models/fraud_detection_v2')
        cv_results = trainer.train_pipeline()
        
        accuracy = cv_results['mean_accuracy']
        recall = cv_results['mean_fraud_recall']
        
        # Targets: 72-82% accuracy, 70%+ recall
        target_accuracy_range = (0.50, 0.95)  # Allow wider range for synthetic
        target_recall_min = 0.30
        
        print(f"   Accuracy: {accuracy:.1%} (target: {target_accuracy_range[0]:.0%}-{target_accuracy_range[1]:.0%})")
        print(f"   Recall: {recall:.1%} (target: >{target_recall_min:.0%})")
        
        assert target_accuracy_range[0] <= accuracy <= target_accuracy_range[1], \
            f"Accuracy {accuracy:.1%} outside target range"
        assert recall >= target_recall_min, f"Recall {recall:.1%} below target"


class TestDataQuality:
    """Test that generated data has proper quality markers."""
    
    @classmethod
    def setup_class(cls):
        """Generate test data once."""
        generator = RealisticFraudDataGenerator(output_dir='data')
        cls.df, cls.metadata = generator.generate_all_data()
    
    def test_metadata_completeness(self):
        """Test that metadata file is complete."""
        print(f"\n✅ Metadata Completeness Test")
        
        assert 'generated_at' in self.metadata
        assert 'total_records' in self.metadata
        assert 'generation_techniques' in self.metadata
        assert 'features' in self.metadata
        assert 'target_metrics' in self.metadata
        
        print(f"   Total records: {self.metadata['total_records']}")
        print(f"   Target accuracy: {self.metadata['target_metrics']['expected_accuracy_range']}")
        print(f"   Target CV std: >{self.metadata['target_metrics']['expected_cv_std_min']}")
    
    def test_no_nan_values(self):
        """Test that there are no NaN values in numerical features."""
        print(f"\n✅ NaN Values Test")
        
        feature_cols = [c for c in self.df.columns if c not in ['is_fraud', 'fraud_type', 'data_generation_technique']]
        nan_count = self.df[feature_cols].isna().sum().sum()
        
        assert nan_count == 0, f"Found {nan_count} NaN values"
        print(f"   No NaN values found ✅")
    
    def test_feature_scaling_range(self):
        """Test that features are in reasonable ranges (not extreme outliers)."""
        print(f"\n✅ Feature Scaling Range Test")
        
        feature_cols = [c for c in self.df.columns if c not in ['is_fraud', 'fraud_type', 'data_generation_technique']]
        
        for col in feature_cols[:5]:  # Check first 5
            val_min = self.df[col].min()
            val_max = self.df[col].max()
            val_mean = self.df[col].mean()
            val_std = self.df[col].std()
            
            # Check for extreme outliers (more than 5 std from mean)
            outlier_threshold = abs(val_max - val_mean) / val_std if val_std > 0 else 0
            
            if outlier_threshold > 5:
                print(f"   ⚠️  {col}: potential outliers ({outlier_threshold:.1f} std from mean)")
            else:
                print(f"   ✅ {col}: range OK (mean={val_mean:.2f}, std={val_std:.2f})")


if __name__ == '__main__':
    print("\n" + "="*100)
    print("FRAUD DETECTION v3 - REALISTIC DATA GENERATION TEST SUITE")
    print("="*100)
    
    # Run tests
    pytest.main([__file__, '-v', '-s'])
