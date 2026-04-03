"""
Local scikit-learn helpers for offline work on exported tabular data.
The production pipeline trains **Random Forest** inside Google Earth Engine
(see ``analysis_service.run_extended_analysis``).
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier


def train_rf_from_arrays(X: np.ndarray, y: np.ndarray, n_trees: int = 50) -> RandomForestClassifier:
    """Fit a RandomForestClassifier on user-supplied feature matrix and labels."""
    clf = RandomForestClassifier(n_estimators=n_trees, random_state=42)
    clf.fit(X, y)
    return clf
