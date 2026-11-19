"""Pure NumPy attitude estimators for the IMU study.

Rotations map body vectors into world coordinates. All angles and angular
rates are in radians (and radians per second), and local attitude errors are
right-multiplicative: ``R_true = R_estimate @ Exp(delta_theta)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import atan2, cos, pi, sin, sqrt

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class ComplementaryUpdate:
    """Values used by one complementary direction correction."""

    observed: FloatArray
    predicted: FloatArray
    error: FloatArray
    rotation_delta: FloatArray
    bias_delta: FloatArray
    weight: float


@dataclass(frozen=True)
class KalmanUpdate:
    """Numeric intermediates and outcome of one EKF direction correction."""

    observed: FloatArray
    predicted: FloatArray
    residual: FloatArray
    innovation: FloatArray
    prior_covariance: FloatArray
    sigma: float
    nis: float
    accepted: bool
    gain: FloatArray | None
    correction: FloatArray | None


def skew(v: FloatArray) -> FloatArray:
    """Return the 3 by 3 cross-product matrix for a three-vector."""
    x, y, z = np.asarray(v, dtype=np.float64)
    return np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]], dtype=np.float64)


def exp_so3(v: FloatArray) -> FloatArray:
    """Map a rotation vector in radians to SO(3) using Rodrigues' formula."""
    vector = np.asarray(v, dtype=np.float64)
    theta = float(np.linalg.norm(vector))
    cross = skew(vector)
    if theta < 1e-8:
        # Series for sin(theta)/theta and (1-cos(theta))/theta**2.
        t2 = theta * theta
        a = 1.0 - t2 / 6.0 + t2 * t2 / 120.0
        b = 0.5 - t2 / 24.0 + t2 * t2 / 720.0
    else:
        a = sin(theta) / theta
        b = (1.0 - cos(theta)) / (theta * theta)
    result = np.eye(3, dtype=np.float64) + a * cross + b * (cross @ cross)
    return np.asarray(result, dtype=np.float64)


def log_so3(r: FloatArray) -> FloatArray:
    """Return the principal rotation vector, including a stable near-pi case."""
    matrix = np.asarray(r, dtype=np.float64)
    cosine = float(np.clip((np.trace(matrix) - 1.0) / 2.0, -1.0, 1.0))
    theta = float(np.arccos(cosine))
    vee = np.array(
        [matrix[2, 1] - matrix[1, 2], matrix[0, 2] - matrix[2, 0], matrix[1, 0] - matrix[0, 1]],
        dtype=np.float64,
    )
    if theta < 1e-7:
        return np.asarray(0.5 * vee, dtype=np.float64)
    if pi - theta < 1e-5:
        # Symmetric part is 2 aa^T at pi. Select the strongest diagonal to
        # avoid dividing by a small component, then recover the other signs.
        symmetric = 0.5 * (matrix + matrix.T)
        diagonal = np.maximum(np.diag(symmetric) + 1.0, 0.0)
        axis = np.zeros(3, dtype=np.float64)
        index = int(np.argmax(diagonal))
        axis[index] = sqrt(float(diagonal[index])) / 2.0
        if axis[index] > 1e-8:
            for j in range(3):
                if j != index:
                    axis[j] = symmetric[index, j] / (4.0 * axis[index])
        else:
            axis[index] = 1.0
        norm = float(np.linalg.norm(axis))
        axis /= norm
        # Resolve the otherwise ambiguous pi-axis sign from the skew part.
        if np.linalg.norm(vee) > 1e-10 and float(axis @ vee) < 0.0:
            axis = -axis
        return np.asarray(theta * axis, dtype=np.float64)
    return np.asarray((theta / (2.0 * sin(theta))) * vee, dtype=np.float64)


def euler_deg(r: FloatArray) -> FloatArray:
    """Return ZYX ``[roll, pitch, yaw]`` in degrees.

    At gimbal lock (|pitch|=90 degrees), roll and yaw are not separately
    observable; this convention sets roll to zero and returns the combined
    angle in yaw.
    """
    matrix = np.asarray(r, dtype=np.float64)
    pitch = atan2(-float(matrix[2, 0]), sqrt(float(matrix[0, 0] ** 2 + matrix[1, 0] ** 2)))
    if abs(cos(pitch)) < 1e-8:
        roll = 0.0
        yaw = atan2(-float(matrix[0, 1]), float(matrix[1, 1]))
    else:
        roll = atan2(float(matrix[2, 1]), float(matrix[2, 2]))
        yaw = atan2(float(matrix[1, 0]), float(matrix[0, 0]))
    return np.asarray(np.degrees([roll, pitch, yaw]), dtype=np.float64)


def _unit(v: FloatArray) -> FloatArray:
    vector = np.asarray(v, dtype=np.float64)
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        raise ValueError("direction vectors must be nonzero")
    return np.asarray(vector / norm, dtype=np.float64)


@dataclass
class Complementary:
    """Complementary attitude correction with an integral gyro-bias estimate."""

    rotation: FloatArray
    kp: float
    ki: float
    bias: FloatArray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))

    def predict(self, gyro: FloatArray, dt: float) -> None:
        """Integrate body-frame angular rate on the right of the rotation."""
        rate = np.asarray(gyro, dtype=np.float64) - self.bias
        self.rotation = np.asarray(self.rotation @ exp_so3(rate * dt), dtype=np.float64)

    def correct(
        self, observed_unit: FloatArray, world_unit: FloatArray, dt: float, weight: float = 1.0
    ) -> ComplementaryUpdate:
        """Use a measured body direction to pull the estimate toward world truth."""
        z = _unit(observed_unit)
        world = _unit(world_unit)
        h = np.asarray(self.rotation.T @ world, dtype=np.float64)
        error = np.cross(z, h)
        scale = weight * dt
        rotation_delta = np.asarray(self.kp * scale * error, dtype=np.float64)
        bias_delta = np.asarray(-self.ki * scale * error, dtype=np.float64)
        self.rotation = np.asarray(self.rotation @ exp_so3(rotation_delta), dtype=np.float64)
        self.bias = np.asarray(self.bias + bias_delta, dtype=np.float64)
        return ComplementaryUpdate(
            z.copy(), h.copy(), error.copy(), rotation_delta, bias_delta, float(weight)
        )


@dataclass
class ErrorStateEKF:
    """Six-state right-error attitude EKF with gyro-bias random walk.

    Covariance starts with 35-degree (one sigma) attitude uncertainty and
    4-degree/second bias uncertainty. Noise density arguments are continuous
    white-noise standard deviations in the matching SI units.
    """

    rotation: FloatArray
    gyro_density: float
    bias_rw: float
    bias: FloatArray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    covariance: FloatArray = field(
        default_factory=lambda: np.diag(
            [np.deg2rad(35.0) ** 2] * 3 + [np.deg2rad(4.0) ** 2] * 3
        ).astype(np.float64)
    )

    def predict(self, gyro: FloatArray, dt: float) -> None:
        """Propagate attitude, bias covariance and first-order error dynamics."""
        rate = np.asarray(gyro, dtype=np.float64) - self.bias
        self.rotation = np.asarray(self.rotation @ exp_so3(rate * dt), dtype=np.float64)
        f = np.zeros((6, 6), dtype=np.float64)
        f[:3, :3] = -skew(rate)
        f[:3, 3:] = -np.eye(3, dtype=np.float64)
        phi = np.eye(6, dtype=np.float64) + f * dt
        q = np.diag([self.gyro_density**2 * dt] * 3 + [self.bias_rw**2 * dt] * 3).astype(np.float64)
        self.covariance = np.asarray(phi @ self.covariance @ phi.T + q, dtype=np.float64)
        self.covariance = np.asarray(0.5 * (self.covariance + self.covariance.T), dtype=np.float64)

    def correct_inspected(
        self,
        observed_unit: FloatArray,
        world_unit: FloatArray,
        sigma: float,
        nis_limit: float | None = None,
    ) -> KalmanUpdate:
        """Correct one direction and retain the exact intermediates used."""
        if sigma <= 0.0:
            raise ValueError("sigma must be positive")
        z = _unit(observed_unit)
        world = _unit(world_unit)
        h = np.asarray(self.rotation.T @ world, dtype=np.float64)
        residual = np.asarray(z - h, dtype=np.float64)
        prior_covariance = self.covariance.copy()
        observation = np.zeros((3, 6), dtype=np.float64)
        observation[:, :3] = skew(h)
        noise = np.eye(3, dtype=np.float64) * sigma**2
        innovation = observation @ prior_covariance @ observation.T + noise
        solved_residual = np.linalg.solve(innovation, residual)
        nis = float(residual @ solved_residual)
        if nis_limit is not None and nis > nis_limit:
            return KalmanUpdate(
                z.copy(),
                h.copy(),
                residual.copy(),
                innovation.copy(),
                prior_covariance,
                float(sigma),
                nis,
                False,
                None,
                None,
            )
        gain = np.linalg.solve(innovation, observation @ prior_covariance).T
        delta = np.asarray(gain @ residual, dtype=np.float64)
        identity = np.eye(6, dtype=np.float64)
        remainder = identity - gain @ observation
        covariance = remainder @ self.covariance @ remainder.T + gain @ noise @ gain.T
        self.rotation = np.asarray(self.rotation @ exp_so3(delta[:3]), dtype=np.float64)
        self.bias = np.asarray(self.bias + delta[3:], dtype=np.float64)
        reset = np.eye(6, dtype=np.float64)
        reset[:3, :3] -= 0.5 * skew(delta[:3])
        self.covariance = np.asarray(reset @ covariance @ reset.T, dtype=np.float64)
        self.covariance = np.asarray(0.5 * (self.covariance + self.covariance.T), dtype=np.float64)
        return KalmanUpdate(
            z.copy(),
            h.copy(),
            residual.copy(),
            innovation.copy(),
            prior_covariance,
            float(sigma),
            nis,
            True,
            gain.copy(),
            delta.copy(),
        )

    def correct(
        self,
        observed_unit: FloatArray,
        world_unit: FloatArray,
        sigma: float,
        nis_limit: float | None = None,
    ) -> tuple[float, bool]:
        """Correct from one 3D direction; return NIS and whether it was accepted."""
        update = self.correct_inspected(observed_unit, world_unit, sigma, nis_limit)
        return update.nis, update.accepted
