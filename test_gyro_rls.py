"""Check RLS against a batch fit, a bias change, and rank-deficient motion."""

import numpy as np

from gyro_rls import calibrate_gyro


def test_unforgotten_rls_matches_regularized_batch_fit() -> None:
    result = calibrate_gyro(1.0, 0.0, "Varied rate", noise_sd=0)
    design = np.column_stack((result.reference, np.ones_like(result.reference)))
    information = np.diag([4.0, 0.01])
    expected = np.linalg.solve(
        design.T @ design + information,
        design.T @ result.measurement + information @ [1.0, 0.0],
    )
    np.testing.assert_allclose(result.estimates[-1], expected, atol=1e-10)
    np.testing.assert_allclose(result.estimates[-1], [1.08, 0.9], atol=1e-4)


def test_forgetting_follows_a_bias_step() -> None:
    slow = calibrate_gyro(1.0, 4.0, "Varied rate", noise_sd=0)
    fast = calibrate_gyro(0.98, 4.0, "Varied rate", noise_sd=0)
    error = abs(fast.estimates[-1, 1] - fast.true_bias[-1])
    assert error < 0.1
    assert error < abs(slow.estimates[-1, 1] - slow.true_bias[-1])


def test_perfect_constant_rate_cannot_separate_bias_from_scale() -> None:
    result = calibrate_gyro(1.0, 0.0, "Constant rate", noise_sd=0)
    design = np.column_stack((result.reference, np.ones_like(result.reference)))
    assert np.linalg.matrix_rank(design) == 1
    scale, bias = result.estimates[-1]
    assert abs((30 * scale + bias) - result.measurement[-1]) < 0.01
    assert abs(bias - result.true_bias[-1]) > 0.1
