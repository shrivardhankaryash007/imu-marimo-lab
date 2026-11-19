"""Generate one reproducible IMU replay and independent 3D controlled plants."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from attitude_filters import Complementary, ErrorStateEKF, euler_deg, exp_so3, log_so3
from imu_sensor import magnetic_field, rotation

Array = NDArray[np.float64]
Flags = NDArray[np.bool_]
G = 9.80665
DT = 0.02
DURATION = 12.0


@dataclass(frozen=True)
class Settings:
    """All hardware geometry, disturbance magnitudes, and filter choices for a run."""

    mount_roll: float = 30.0
    mount_pitch: float = -25.0
    mount_yaw: float = 40.0
    mount_yaw_error: float = 0.0
    offset_x: float = 0.46
    offset_y: float = -0.22
    offset_z: float = 0.20
    gyro_bias: float = 1.5
    initial_yaw_error: float = 20.0
    translation: float = 0.65
    magnetic_interference: float = 0.6
    heading_aid: bool = True
    reject_disturbance: bool = True
    ideal_lever_correction: bool = False
    complementary_kp: float = 2.0
    complementary_ki: float = 0.15
    accel_sigma: float = 0.045
    mag_sigma: float = 0.07
    kalman_gyro_density: float = 0.003
    kalman_bias_rw: float = 0.002


@dataclass(frozen=True)
class EstimatorTrace:
    """Body-frame estimates, gyro-bias estimates, and versioned observations."""

    rotations: Array
    euler: Array
    error: Array
    bias: Array


@dataclass(frozen=True)
class Replay:
    """Results for three algorithms exposed to exactly the same physical samples."""

    time: Array
    truth: Array
    truth_euler: Array
    gyro: EstimatorTrace
    complementary: EstimatorTrace
    ekf: EstimatorTrace
    # Small-angle uncertainty is expressed in local tangent coordinates.
    sigma: Array
    accel_norm: Array
    mag_norm: Array
    accel_nis: Array
    mag_nis: Array
    accel_correction: Array
    mag_correction: Array
    accel_accepted: Flags
    mag_accepted: Flags
    field_accepted_by_comp: Flags
    force_accepted_by_comp: Flags
    raw_gyro: Array
    raw_force: Array
    raw_mag: Array
    mount: Array
    offset_body: Array


@dataclass(frozen=True)
class ControlTrace:
    """True attitude error and actual torque from one independently controlled body."""

    euler: Array
    error: Array
    torque: Array
    clipped: Flags


@dataclass(frozen=True)
class ControlRun:
    """Two closed-loop plants with identical commands, geometry and disturbances."""

    time: Array
    target: Array
    complementary: ControlTrace
    ekf: ControlTrace


def _geometry(settings: Settings) -> tuple[Array, Array, Array, Array, Array]:
    mount = rotation(settings.mount_roll, settings.mount_pitch, settings.mount_yaw)
    assumed = rotation(
        settings.mount_roll, settings.mount_pitch, settings.mount_yaw + settings.mount_yaw_error
    )
    offset = np.array([settings.offset_x, settings.offset_y, settings.offset_z])
    magnetic = magnetic_field(8, 50, 1)
    bias = np.deg2rad(settings.gyro_bias) * np.array([0.38, -0.56, 1.0])
    return mount, assumed, offset, magnetic, bias


def _sample(
    settings: Settings,
    geometry: tuple[Array, Array, Array, Array, Array],
    attitude: Array,
    rate: Array,
    angular_accel: Array,
    time: float,
    noise: Array,
) -> tuple[Array, Array, Array, Array]:
    mount, _, offset, magnetic, bias = geometry
    sensor_to_world = attitude @ mount
    physical_lever = np.cross(angular_accel, offset) + np.cross(rate, np.cross(rate, offset))
    translation = np.zeros(3)
    if 3.0 <= time < 5.7:
        translation = settings.translation * G * np.array([0.89, -0.41, 0.20])
    gyro = mount.T @ rate + bias + noise[0] * 0.006
    force = sensor_to_world.T @ (translation + np.array([0.0, 0.0, G])) + mount.T @ physical_lever
    force = force + noise[1] * 0.06
    # The ideal toggle subtracts synthetic truth to isolate lever-arm effects.
    aided_force = force - mount.T @ physical_lever if settings.ideal_lever_correction else force
    mag = sensor_to_world.T @ magnetic + noise[2] * 0.005
    if 7.0 <= time < 9.2:
        mag = mag + settings.magnetic_interference * np.array([0.8, -0.55, 0.22])
    return gyro, force, aided_force, mag


def _direction(vector: Array, expected: float, tolerance: float, gate: bool) -> Array | None:
    norm = float(np.linalg.norm(vector))
    if norm < 1e-9 or (gate and abs(norm / expected - 1) > tolerance):
        return None
    return vector / norm


def _aiding(
    settings: Settings,
    magnetic_ref: Array,
    aided_force: Array,
    mag: Array,
) -> tuple[tuple[Array, Array, float, float, bool], ...]:
    force_dir = _direction(aided_force, G, 0.14, settings.reject_disturbance)
    field_dir = _direction(mag, 1, 0.23, settings.reject_disturbance)
    candidates = []
    if force_dir is not None:
        candidates.append((force_dir, np.array([0.0, 0.0, 1.0]), settings.accel_sigma, 1.0, False))
    if settings.heading_aid and field_dir is not None:
        candidates.append((field_dir, magnetic_ref, settings.mag_sigma, 0.65, True))
    return tuple(candidates)


def _errors(reference: Array, actual: Array) -> Array:
    return np.array(
        [
            np.rad2deg(np.linalg.norm(log_so3(r.T @ a)))
            for r, a in zip(reference, actual, strict=True)
        ]
    )


def _trace(truth: Array, rotations: Array, bias: Array) -> EstimatorTrace:
    return EstimatorTrace(
        rotations, np.array([euler_deg(r) for r in rotations]), _errors(truth, rotations), bias
    )


def run_replay(settings: Settings) -> Replay:
    """Estimate three attitudes from one 50 Hz trajectory with separate correction signals."""
    time = np.linspace(0, DURATION, round(DURATION / DT) + 1)
    n = time.size
    geometry = _geometry(settings)
    mount, assumed, offset, magnetic, _ = geometry
    rate = np.column_stack(
        (0.42 * np.sin(0.92 * time), 0.36 * np.cos(0.67 * time), 0.28 + 0.34 * np.cos(0.78 * time))
    )
    alpha = np.column_stack(
        (
            0.42 * 0.92 * np.cos(0.92 * time),
            -0.36 * 0.67 * np.sin(0.67 * time),
            -0.34 * 0.78 * np.sin(0.78 * time),
        )
    )
    truth = np.empty((n, 3, 3))
    truth[0] = rotation(8, -12, 20)
    for k in range(1, n):
        truth[k] = truth[k - 1] @ exp_so3(rate[k - 1] * DT)
    initial = rotation(8, -12, 20 + settings.initial_yaw_error) @ assumed
    gyro_only = initial.copy()
    comp = Complementary(initial, settings.complementary_kp, settings.complementary_ki)
    ekf = ErrorStateEKF(initial, settings.kalman_gyro_density, settings.kalman_bias_rw)
    gyro_r, comp_r, ekf_r = np.empty((3, n, 3, 3))
    comp_b, ekf_b, sigma, raw_gyro, raw_force, raw_mag = np.empty((6, n, 3))
    accel_norm, mag_norm = np.empty((2, n))
    accel_nis, mag_nis = np.full((2, n), np.nan)
    accel_correction, mag_correction = np.zeros((2, n))
    acc_ok, mag_ok, comp_acc_ok, comp_mag_ok = np.zeros((4, n), dtype=np.bool_)
    noise_series = np.random.default_rng(2026).standard_normal((n, 3, 3))
    for k, t in enumerate(time):
        if k:
            gyro_only = gyro_only @ exp_so3(raw_gyro[k - 1] * DT)
            comp.predict(raw_gyro[k - 1], DT)
            ekf.predict(raw_gyro[k - 1], DT)
        gyro, force, aided, mag = _sample(
            settings, geometry, truth[k], rate[k], alpha[k], t, noise_series[k]
        )
        raw_gyro[k], raw_force[k], raw_mag[k] = gyro, force, mag
        accel_norm[k], mag_norm[k] = np.linalg.norm(aided) / G, np.linalg.norm(mag)
        for measured, reference, noise, weight, is_mag in _aiding(settings, magnetic, aided, mag):
            comp.correct(measured, reference, DT, weight)
            prior = ekf.rotation.copy()
            if is_mag:
                comp_mag_ok[k] = True
                mag_nis[k], mag_ok[k] = ekf.correct(
                    measured, reference, noise, 9.21 if settings.reject_disturbance else None
                )
                mag_correction[k] = np.rad2deg(np.linalg.norm(log_so3(prior.T @ ekf.rotation)))
            else:
                comp_acc_ok[k] = True
                accel_nis[k], acc_ok[k] = ekf.correct(
                    measured, reference, noise, 9.21 if settings.reject_disturbance else None
                )
                accel_correction[k] = np.rad2deg(np.linalg.norm(log_so3(prior.T @ ekf.rotation)))
        gyro_r[k], comp_r[k], ekf_r[k] = (
            r @ assumed.T for r in (gyro_only, comp.rotation, ekf.rotation)
        )
        comp_b[k], ekf_b[k] = comp.bias, ekf.bias
        # Rotate local orientation error covariance into the assumed body frame.
        body_cov = assumed @ ekf.covariance[:3, :3] @ assumed.T
        sigma[k] = np.rad2deg(np.sqrt(np.maximum(0.0, body_cov.diagonal())))
    bias_zero = np.zeros_like(comp_b)
    return Replay(
        time,
        truth,
        np.array([euler_deg(r) for r in truth]),
        _trace(truth, gyro_r, bias_zero),
        _trace(truth, comp_r, comp_b),
        _trace(truth, ekf_r, ekf_b),
        sigma,
        accel_norm,
        mag_norm,
        accel_nis,
        mag_nis,
        accel_correction,
        mag_correction,
        acc_ok,
        mag_ok,
        comp_mag_ok,
        comp_acc_ok,
        raw_gyro,
        raw_force,
        raw_mag,
        mount,
        offset,
    )


def _controlled_plant(
    settings: Settings,
    time: Array,
    desired: Array,
    kp: float,
    kd: float,
    limit: float,
    disturbance_nm: float,
    *,
    kalman: bool,
) -> ControlTrace:
    geometry = _geometry(settings)
    _, assumed, _, magnetic, _ = geometry
    attitude = np.eye(3)
    rate = np.zeros(3)
    angular_accel = np.zeros(3)
    initial = rotation(0, 0, settings.initial_yaw_error) @ assumed
    comp = Complementary(initial, settings.complementary_kp, settings.complementary_ki)
    ekf = ErrorStateEKF(initial, settings.kalman_gyro_density, settings.kalman_bias_rw)
    estimator = ekf if kalman else comp
    previous_gyro = np.zeros(3)
    inertias = np.array([0.075, 0.09, 0.12])
    trace = np.empty((time.size, 3, 3))
    torque = np.empty((time.size, 3))
    clipped = np.zeros(time.size, dtype=np.bool_)
    noise_series = np.random.default_rng(301).standard_normal((time.size, 3, 3))
    for k, t in enumerate(time):
        if k:
            estimator.predict(previous_gyro, DT)
        gyro, _, force, mag = _sample(
            settings, geometry, attitude, rate, angular_accel, t, noise_series[k]
        )
        previous_gyro = gyro
        for z, d, sigma, weight, _ in _aiding(settings, magnetic, force, mag):
            if kalman:
                ekf.correct(z, d, sigma, 9.21 if settings.reject_disturbance else None)
            else:
                comp.correct(z, d, DT, weight)
        body = estimator.rotation @ assumed.T
        omega_hat = assumed @ (gyro - estimator.bias)
        error = log_so3(body.T @ desired[k])
        requested = kp * error - kd * omega_hat
        torque[k] = np.clip(requested, -limit, limit)
        clipped[k] = np.any(abs(requested) > limit)
        exterior = disturbance_nm * np.array([0.6, -0.8, 0.45]) if 5 <= t < 6 else np.zeros(3)
        trace[k] = attitude
        angular_accel = (torque[k] + exterior - np.cross(rate, inertias * rate)) / inertias
        attitude = attitude @ exp_so3(rate * DT)
        rate = rate + angular_accel * DT
    return ControlTrace(
        np.array([euler_deg(r) for r in trace]), _errors(desired, trace), torque, clipped
    )


def run_control(
    settings: Settings, kp: float, kd: float, limit: float, disturbance: float
) -> ControlRun:
    """Run each estimator's actuator loop with the same gains and a common torque pulse."""
    time = np.linspace(0, DURATION, round(DURATION / DT) + 1)
    target = np.array([np.eye(3) if t < 1 else rotation(12, -18, 45) for t in time])
    return ControlRun(
        time,
        np.array([euler_deg(r) for r in target]),
        _controlled_plant(settings, time, target, kp, kd, limit, disturbance, kalman=False),
        _controlled_plant(settings, time, target, kp, kd, limit, disturbance, kalman=True),
    )
