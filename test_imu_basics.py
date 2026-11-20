"""Physics anchors for the IMU foundations helpers; each test pins one lesson's claim."""

import numpy as np
import pytest

import imu_basics as b
from imu_sensor import magnetic_field, rotation


def test_counts_lsb_and_clipping() -> None:
    assert b.lsb_size(4.0) == pytest.approx(4.0 / 32768)
    assert b.lsb_size(4.0) * 1000 == pytest.approx(0.1220703125)
    np.testing.assert_allclose(b.counts_to_units(np.array([16384, -32768]), 2.0), [1.0, -2.0])
    d = b.digitize(np.array([0.0, 1.00003, 2.5, -2.5]), 2.0)
    assert d.counts.tolist() == [0, 16384, 32767, -32768]
    assert d.clipped.tolist() == [False, False, True, True]
    with pytest.raises(ValueError):
        b.lsb_size(0.0)


@pytest.mark.parametrize(("roll", "pitch"), [(0, 0), (25, -40), (-60, 30), (170, 10)])
def test_tilt_round_trip_and_yaw_blindness(roll: float, pitch: float) -> None:
    f = b.gravity_reading_g(roll, pitch)
    assert np.linalg.norm(f) == pytest.approx(1.0)
    np.testing.assert_allclose(b.accel_tilt_deg(f), (roll, pitch), atol=1e-9)
    np.testing.assert_allclose(b.gravity_reading_g(roll, pitch, 123.0), f, atol=1e-12)


def test_linear_acceleration_corrupts_tilt() -> None:
    # Level, accelerating forward at 0.2 g: specific force [0.2, 0, 1].
    _, pitch = b.accel_tilt_deg(np.array([0.2, 0.0, 1.0]))
    assert pitch == pytest.approx(-11.3099, abs=1e-3)


def test_gyro_drift_mean_and_sqrt_t_spread() -> None:
    t, err = b.gyro_drift_runs(60.0, 100.0, 0.5, 0.02, runs=400, seed=1)
    mean, std = b.gyro_drift_bounds(t, 0.5, 0.02)
    assert err[:, 0].tolist() == [0.0] * 400
    assert float(np.mean(err[:, -1])) == pytest.approx(mean[-1], abs=0.03)
    assert float(np.std(err[:, -1])) == pytest.approx(std[-1], rel=0.12)
    assert mean[-1] == pytest.approx(30.0)


def test_allan_white_noise_slope_and_random_walk_rise() -> None:
    rate = b.simulate_rest_gyro(600.0, 100.0, 0.3, 0.01, seed=2)
    tau, adev = b.allan_deviation(rate, 0.01)
    i = int(np.argmin(np.abs(tau - 1.0)))
    assert adev[i] == pytest.approx(0.01 / np.sqrt(tau[i]), rel=0.1)
    walk = b.simulate_rest_gyro(600.0, 100.0, 0.0, 0.0, rate_random_walk=0.002, seed=3)
    _, adev_w = b.allan_deviation(walk, 0.01)
    assert adev_w[-1] > adev_w[len(adev_w) // 2]
    with pytest.raises(ValueError):
        b.allan_deviation(np.zeros(2), 0.01)


def test_aliasing_and_filter() -> None:
    assert b.alias_frequency_hz(180.0, 200.0) == pytest.approx(20.0)
    assert b.alias_frequency_hz(95.0, 100.0) == pytest.approx(5.0)
    assert b.alias_frequency_hz(30.0, 100.0) == pytest.approx(30.0)
    assert b.first_order_gain(20.0, 20.0) == pytest.approx(1 / np.sqrt(2))
    _, _, ts, xs = b.sample_tone(5.0, 1.0, 100.0, 1.0, cutoff_hz=5.0)
    assert ts.size == 101
    assert float(np.max(np.abs(xs))) <= 1 / np.sqrt(2) + 1e-9


def test_accel_six_position_and_gyro_bias() -> None:
    scale, offset = b.axis_scale_offset(1.03, -0.97)
    assert (scale, offset) == pytest.approx((1.0, 0.03))
    with pytest.raises(ValueError):
        b.axis_scale_offset(-1.0, 1.0)
    rest = np.array([[0.4, -0.3, 0.2]]) + np.zeros((50, 3))
    np.testing.assert_allclose(b.gyro_bias_from_rest(rest), [0.4, -0.3, 0.2])


def test_ellipse_fit_restores_circle_up_to_constant_rotation() -> None:
    angles = np.radians(np.linspace(0, 360, 145, endpoint=False))
    ideal = 30.0 * np.column_stack((np.cos(angles), np.sin(angles)))
    d = 1.3
    soft = np.array([[d, 0.12 * (d - 1)], [0, 1 / d]])
    hard = np.array([12.0, -5.4])
    raw = ideal @ soft.T + hard
    fit = b.fit_ellipse_2d(raw)
    np.testing.assert_allclose(fit.center, hard, atol=1e-8)
    fixed = b.apply_mag_fit(raw, fit)
    radii = np.linalg.norm(fixed, axis=1)
    assert float(np.std(radii) / np.mean(radii)) < 1e-8
    offset = np.degrees(np.arctan2(fixed[:, 1], fixed[:, 0]) - angles)
    offset = (offset + 180) % 360 - 180
    assert float(np.ptp(offset)) < 1e-6
    noisy = raw + 0.5 * np.random.default_rng(4).standard_normal(raw.shape)
    radii_n = np.linalg.norm(b.apply_mag_fit(noisy, b.fit_ellipse_2d(noisy)), axis=1)
    assert float(np.std(radii_n) / np.mean(radii_n)) < 0.03
    with pytest.raises(ValueError):
        b.fit_ellipse_2d(np.zeros((4, 2)))


@pytest.mark.parametrize(("roll", "pitch", "yaw"), [(0, 0, 30), (20, -30, 100), (-35, 25, 250)])
def test_tilt_compensated_heading(roll: float, pitch: float, yaw: float) -> None:
    mag_body = rotation(roll, pitch, yaw).T @ magnetic_field(0.0, 60.0, 48.0)
    expected = (90.0 - yaw) % 360
    assert b.angle_diff_deg(b.tilt_compensated_heading_deg(mag_body, roll, pitch), expected) == (
        pytest.approx(0.0, abs=1e-9)
    )
    if pitch:
        assert abs(b.angle_diff_deg(b.naive_heading_deg(mag_body), expected)) > 5.0
    assert b.true_heading_deg(350.0, 15.0) == pytest.approx(5.0)
    assert b.angle_diff_deg(10.0, 350.0) == pytest.approx(20.0)


def test_complementary_tau_and_bias_error() -> None:
    assert b.complementary_tau(0.98, 0.01) == pytest.approx(0.49)
    assert b.complementary_alpha(0.49, 0.01) == pytest.approx(0.98)
    n = 2000
    est = b.complementary_1d(np.full(n, 0.5), np.full(n, 10.0), 0.01, 0.98)
    assert est[-1] == pytest.approx(10.0 + 0.49 * 0.5, abs=1e-6)


def test_gimbal_lock_and_quaternions() -> None:
    m = b.euler_rate_matrix(0.0, 89.0)
    assert float(np.max(np.abs(m))) == pytest.approx(1 / np.cos(np.radians(89.0)), rel=1e-9)
    with pytest.raises(ValueError):
        b.euler_rate_matrix(10.0, 90.0)
    q = b.quat_from_euler(25, -40, 100)
    assert np.linalg.norm(q) == pytest.approx(1.0)
    np.testing.assert_allclose(b.quat_to_rotation(q), rotation(25, -40, 100), atol=1e-12)
    q = np.array([1.0, 0.0, 0.0, 0.0])
    for _ in range(100):
        q = b.quat_integrate(q, np.array([0.0, 0.0, 90.0]), 0.01)
    np.testing.assert_allclose(b.quat_to_rotation(q), rotation(0, 0, 90), atol=1e-9)


def test_position_drift() -> None:
    assert b.position_error_m(0.1, 10.0) == pytest.approx(5.0)
    assert b.tilt_leak_m_s2(1.0) == pytest.approx(0.17115, abs=1e-4)
    vel, pos = b.double_integrate(np.full(1001, 0.1), 0.01)
    assert vel[-1] == pytest.approx(1.0)
    assert pos[-1] == pytest.approx(5.0)


def test_csv_round_trip_and_summary() -> None:
    log = b.load_imu_csv(b.example_imu_csv())
    assert log.accel_unit_detected == "g" and log.mag is not None
    s = b.summarize_log(log, rest_s=4.0)
    assert s.rate_hz == pytest.approx(100.0, rel=1e-3)
    assert s.dt_jitter_ms < 0.01
    np.testing.assert_allclose(s.gyro_bias_deg_s, [0.4, -0.3, 0.2], atol=0.02)
    assert s.accel_norm_mean_g == pytest.approx(1.0, abs=0.01)
    # Noise widens the single-sample maximum; the 99th percentile is the honest peak.
    assert float(np.percentile(s.pitch_deg, 99)) == pytest.approx(20.0, abs=0.75)


def test_csv_units_and_errors() -> None:
    rows = "\n".join(f"{k * 10},0,0,9.80665,0.01,0,0" for k in range(12))
    log = b.load_imu_csv("time_ms,AX,ay,az,gx,gy,gz\n" + rows, gyro_unit="rad/s")
    assert log.accel_unit_detected == "m/s^2" and log.mag is None
    assert log.t[1] == pytest.approx(0.01)
    assert log.accel_g[0, 2] == pytest.approx(1.0)
    assert log.gyro_deg_s[0, 0] == pytest.approx(np.degrees(0.01))
    with pytest.raises(b.ImuCsvError, match="missing"):
        b.load_imu_csv("t,ax,ay\n1,2,3")
    with pytest.raises(b.ImuCsvError, match="at least 10"):
        b.load_imu_csv("t,ax,ay,az,gx,gy,gz\n0,0,0,1,0,0,0")
    with pytest.raises(b.ImuCsvError, match="increase"):
        b.load_imu_csv("t,ax,ay,az,gx,gy,gz\n" + "\n".join("0,0,0,1,0,0,0" for _ in range(12)))
    with pytest.raises(b.ImuCsvError, match="norm"):
        b.load_imu_csv("t,ax,ay,az,gx,gy,gz\n" + "\n".join(f"{k},0,0,3,0,0,0" for k in range(12)))
    with pytest.raises(b.ImuCsvError, match="row 3"):
        b.load_imu_csv("t,ax,ay,az,gx,gy,gz\n0,0,0,1,0,0,0\n1,x,0,1,0,0,0")


def test_grading() -> None:
    assert b.grade_numeric(29.0, 30.0).correct
    assert not b.grade_numeric(20.0, 30.0).correct
    assert b.grade_numeric(0.04, 0.0, abs_tol=0.05).correct
    assert "model says" in b.grade_numeric(1.0, 2.0).message
