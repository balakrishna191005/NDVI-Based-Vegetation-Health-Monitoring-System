import numpy as np

from app.services.ml_local import train_rf_from_arrays


def test_train_rf_from_arrays():
    rng = np.random.default_rng(0)
    X = rng.random((30, 4))
    y = rng.integers(0, 4, size=30)
    clf = train_rf_from_arrays(X, y, n_trees=10)
    pred = clf.predict(X)
    assert pred.shape == (30,)
