"""Numerical and physical anchors for the 3D attitude notebook."""

from dataclasses import replace

import numpy as np

from attitude_filters import Complementary, ErrorStateEKF, euler_deg, exp_so3, log_so3
from attitude_sim import Settings, run_control, run_replay
from imu_sensor import rotation


def _clean() -> Settings:
    return Settings(translation=0, magnetic_interference=0, offset_x=0, offset_y=0, offset_z=0)


def test_so3_and_euler_display() -> None:
    axis = np.array([0.4, -0.7, 0.5])
    increment = (np.pi - 1e-7) * axis / np.linalg.norm(axis)
    turned = exp_so3(increment)
    np.testing.assert_allclose(turned.T @ turned, np.eye(3), atol=1e-12)
    np.testing.assert_allclose(exp_so3(log_so3(turned)), turned, atol=1e-8)
    np.testing.assert_allclose(euler_deg(rotation(25, -40, 100)), [25, -40, 100])


def test_right_direction_update_and_innovation_gate() -> None:
    up = np.array([0.0, 0.0, 1.0])
    displaced = rotation(14, -8, 0)
    comp = Complementary(displaced, 3, 0.1)
    ekf = ErrorStateEKF(displaced, 0.003, 0.002)
    previous = np.linalg.norm(log_so3(displaced))
    comp.correct(up, up, 0.1)
    assert np.linalg.norm(log_so3(comp.rotation)) < previous
    _, accepted = ekf.correct(up, up, 0.05)
    assert accepted and np.linalg.norm(log_so3(ekf.rotation)) < previous
    cov = ekf.covariance.copy()
    old = ekf.rotation.copy()
    nis, accepted = ekf.correct(-up, up, 0.05, 9.21)
    assert nis > 9.21 and not accepted
    np.testing.assert_array_equal(ekf.covariance, cov)
    np.testing.assert_array_equal(ekf.rotation, old)
    assert np.linalg.eigvalsh(cov).min() >= 0
    np.testing.assert_allclose(cov, cov.T, atol=1e-14)


def test_gravity_has_no_absolute_yaw_and_clean_heading_aid_recovers() -> None:
    up = np.array([0.0, 0.0, 1.0])
    body = rotation(20, -15, 0)
    np.testing.assert_allclose(body.T @ up, (rotation(0, 0, 75) @ body).T @ up)
    clean = run_replay(_clean())
    no_mag = run_replay(replace(_clean(), heading_aid=False))
    assert clean.ekf.error[-1] < 1 and clean.complementary.error[-1] < 2
    assert no_mag.ekf.error[-1] > 10 and not no_mag.mag_accepted.any()
    assert no_mag.sigma[-1].max() > 5 * clean.sigma[-1].max()


def test_calibrated_mount_and_ideal_lever_correction() -> None:
    center = run_replay(_clean())
    offset = run_replay(
        replace(_clean(), offset_x=-0.38, offset_y=0.64, offset_z=0.89, ideal_lever_correction=True)
    )
    assert not np.allclose(center.raw_force, offset.raw_force)
    np.testing.assert_allclose(center.ekf.rotations, offset.ekf.rotations, atol=1e-9)
    wrong_mount = run_replay(replace(_clean(), mount_yaw_error=20))
    assert wrong_mount.ekf.error[-1] > 15


def test_disagreement_between_norm_and_innovation_gates() -> None:
    active = run_replay(Settings())
    quiet = active.time < 3.0
    pulse = (active.time >= 3.0) & (active.time < 5.7)
    assert active.accel_accepted[quiet].mean() > 0.95
    assert active.accel_accepted[pulse].mean() < 0.25
    assert np.any(active.accel_correction[quiet] > 0)
    assert np.all(active.accel_correction[~active.accel_accepted] == 0)
    assert np.all(active.mag_correction[~active.mag_accepted] == 0)


def test_true_closed_loop_tracking_and_saturation() -> None:
    run = run_control(_clean(), kp=0.8, kd=0.45, limit=0.35, disturbance=0.04)
    np.testing.assert_allclose(run.target[-1], [12, -18, 45])
    for estimate in (run.complementary, run.ekf):
        assert estimate.error[-1] < 2
        assert estimate.clipped.any()
        assert abs(estimate.torque).max() <= 0.35
    no_torque = run_control(_clean(), kp=0, kd=0, limit=0.35, disturbance=0)
    assert no_torque.ekf.error[-1] > 30
    assert not no_torque.ekf.clipped.any()
