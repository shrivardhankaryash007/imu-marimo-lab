"""Online two-parameter calibration of one gyroscope axis using RLS."""

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]
SAMPLE_INTERVAL_S = 0.02
DURATION_S = 12.0


@dataclass
class RecursiveLeastSquares:
    """Fit measured rate = scale * reference rate + bias in degrees per second."""

    forgetting: float
    estimate: Array = field(default_factory=lambda: np.array([1.0, 0.0]))
    covariance: Array = field(default_factory=lambda: np.diag([0.25, 100.0]))

    def update(self, reference: float, measurement: float) -> tuple[float, float, Array]:
        """Assimilate one sample and return prediction, innovation, and gain."""
        if not 0 < self.forgetting <= 1:
            raise ValueError("Forgetting factor must be in (0, 1].")
        row = np.array([reference, 1.0])
        prediction = float(row @ self.estimate)
        residual = measurement - prediction
        prior = self.covariance / self.forgetting
        projected = prior @ row
        gain = projected / (1.0 + row @ projected)
        self.estimate = self.estimate + gain * residual
        # Joseph form is algebraically equivalent to the textbook rank-one update.
        contraction = np.eye(2) - np.outer(gain, row)
        self.covariance = np.asarray(
            contraction @ prior @ contraction.T + np.outer(gain, gain), dtype=np.float64
        )
        self.covariance = (self.covariance + self.covariance.T) * 0.5
        return prediction, residual, gain


@dataclass(frozen=True)
class CalibrationReplay:
    """Synthetic measurements, sequential parameter estimates, and update terms."""

    time: Array
    reference: Array
    measurement: Array
    prediction: Array
    residual: Array
    gain: Array
    estimates: Array
    true_bias: Array
    true_scale: float


def calibrate_gyro(
    forgetting: float, bias_step: float, excitation: str, noise_sd: float = 0.35
) -> CalibrationReplay:
    """Replay changing, briefly stationary, or constant reference-rate readings."""
    time = np.linspace(0, DURATION_S, round(DURATION_S / SAMPLE_INTERVAL_S) + 1)
    varied = 55 * np.sin(2 * np.pi * time / 2.7) + 18 * np.sin(2 * np.pi * time / 1.1)
    match excitation:
        case "Varied rate":
            reference = varied
        case "Pause, then resume":
            reference = np.where((time >= 4) & (time < 8), 0.0, varied)
        case "Constant rate":
            reference = np.full_like(time, 30.0)
        case _:
            raise ValueError("Choose a known excitation pattern.")
    true_bias = np.where(time < 6.0, 0.9, 0.9 + bias_step)
    true_scale = 1.08
    noise = np.random.default_rng(807).normal(0.0, noise_sd, time.size)
    measurement = true_scale * reference + true_bias + noise
    prediction, residual = np.empty((2, time.size))
    estimates, gain = np.empty((2, time.size, 2))
    state = RecursiveLeastSquares(forgetting)
    for j, (rate, observed) in enumerate(zip(reference, measurement, strict=True)):
        prediction[j], residual[j], gain[j] = state.update(float(rate), float(observed))
        estimates[j] = state.estimate
    return CalibrationReplay(
        time, reference, measurement, prediction, residual, gain, estimates, true_bias, true_scale
    )
