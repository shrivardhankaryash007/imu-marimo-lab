"""Small, exact models behind the IMU foundations notebook.

Conventions match ``imu_sensor``: ENU world, body x-forward / y-left / z-up,
angles in degrees at public interfaces, accelerometer readings in g unless a
name says ``_m_s2``, gyro rates in deg/s. Every function is deterministic for
a given seed so notebook self-checks can compute the true answer.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from math import atan2, cos, degrees, floor, hypot, radians, sin, sqrt, tan
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from imu_sensor import compass_heading_deg, magnetic_field, rotation

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

G0 = 9.80665


class ImuCsvError(ValueError):
    """An uploaded IMU log cannot be parsed or is physically implausible."""


# --- 1. Raw counts -------------------------------------------------------


@dataclass(frozen=True)
class Digitized:
    """ADC view of a signal: integer codes, the value they stand for, and clipping."""

    counts: IntArray
    units: FloatArray
    clipped: BoolArray


def lsb_size(full_scale: float, bits: int = 16) -> float:
    """Return one ADC step for a signed two's-complement output spanning +/-full_scale."""
    if full_scale <= 0 or bits < 2:
        raise ValueError("full_scale must be positive and bits >= 2")
    return full_scale / float(2 ** (bits - 1))


def counts_to_units(counts: IntArray | int, full_scale: float, bits: int = 16) -> FloatArray:
    """Convert raw register codes to physical units (what a driver does)."""
    return np.asarray(counts, dtype=np.float64) * lsb_size(full_scale, bits)


def digitize(value: FloatArray | float, full_scale: float, bits: int = 16) -> Digitized:
    """Quantize to the nearest code and saturate at the register limits."""
    step = lsb_size(full_scale, bits)
    lo, hi = -(2 ** (bits - 1)), 2 ** (bits - 1) - 1
    raw = np.rint(np.asarray(value, dtype=np.float64) / step)
    counts = np.clip(raw, lo, hi).astype(np.int64)
    return Digitized(counts, counts.astype(np.float64) * step, (raw < lo) | (raw > hi))


# --- 2. Tilt from gravity --------------------------------------------------


def gravity_reading_g(roll_deg: float, pitch_deg: float, yaw_deg: float = 0.0) -> FloatArray:
    """Return the at-rest accelerometer reading in g; yaw has no effect by physics."""
    return np.asarray(rotation(roll_deg, pitch_deg, yaw_deg).T @ np.array([0.0, 0.0, 1.0]))


def accel_tilt_deg(specific_force: FloatArray) -> tuple[float, float]:
    """Return (roll, pitch) from one accelerometer sample, valid for |pitch| < 90 deg."""
    fx, fy, fz = (float(v) for v in specific_force)
    return degrees(atan2(fy, fz)), degrees(atan2(-fx, hypot(fy, fz)))


# --- 3. Gyro drift ---------------------------------------------------------


def gyro_drift_runs(
    duration_s: float,
    rate_hz: float,
    bias_deg_s: float,
    noise_density: float,
    runs: int,
    seed: int = 0,
) -> tuple[FloatArray, FloatArray]:
    """Integrate a stationary gyro many times; return time and angle error per run.

    ``noise_density`` is deg/s/sqrt(Hz); the per-sample sigma is that times
    sqrt(rate_hz), so the integrated error spreads as noise_density*sqrt(t).
    """
    n = round(duration_s * rate_hz) + 1
    dt = 1.0 / rate_hz
    rng = np.random.default_rng(seed)
    rate = bias_deg_s + noise_density * sqrt(rate_hz) * rng.standard_normal((runs, n - 1))
    error = np.zeros((runs, n))
    error[:, 1:] = np.cumsum(rate * dt, axis=1)
    return np.arange(n, dtype=np.float64) * dt, error


def gyro_drift_bounds(
    t: FloatArray, bias_deg_s: float, noise_density: float
) -> tuple[FloatArray, FloatArray]:
    """Return the analytic mean (bias*t) and one-sigma spread (N*sqrt(t)) of drift."""
    return bias_deg_s * t, noise_density * np.sqrt(t)


# --- 4. Noise and Allan deviation -----------------------------------------


def simulate_rest_gyro(
    duration_s: float,
    rate_hz: float,
    bias_deg_s: float,
    noise_density: float,
    rate_random_walk: float = 0.0,
    seed: int = 0,
) -> FloatArray:
    """Return one axis of stationary gyro output: bias + white noise + bias random walk.

    ``rate_random_walk`` K is deg/s/sqrt(s); its Allan deviation rises as K*sqrt(tau/3).
    """
    n = round(duration_s * rate_hz)
    dt = 1.0 / rate_hz
    rng = np.random.default_rng(seed)
    white = noise_density * sqrt(rate_hz) * rng.standard_normal(n)
    walk = np.cumsum(rate_random_walk * sqrt(dt) * rng.standard_normal(n))
    return np.asarray(bias_deg_s + white + walk, dtype=np.float64)


def allan_deviation(
    rate: FloatArray, dt: float, num_taus: int = 40
) -> tuple[FloatArray, FloatArray]:
    """Return (tau, overlapping Allan deviation) for evenly sampled rate data."""
    n = rate.size
    if n < 3:
        raise ValueError("need at least 3 samples")
    theta = np.concatenate(([0.0], np.cumsum(rate) * dt))
    max_m = (n - 1) // 2
    ms = np.unique(np.logspace(0, np.log10(max_m), num_taus).astype(np.int64))
    taus, adev = [], []
    for m in ms:
        tau = m * dt
        d = theta[2 * m :] - 2 * theta[m:-m] + theta[: -2 * m]
        taus.append(tau)
        adev.append(sqrt(float(np.mean(d**2)) / (2 * tau**2)))
    return np.array(taus), np.array(adev)


# --- 5. Sampling -----------------------------------------------------------


def alias_frequency_hz(freq_hz: float, odr_hz: float) -> float:
    """Return the frequency a tone appears at after sampling at ``odr_hz``."""
    return abs(freq_hz - odr_hz * floor(freq_hz / odr_hz + 0.5))


def first_order_gain(freq_hz: float, cutoff_hz: float) -> float:
    """Return the magnitude response of a one-pole low-pass filter."""
    return 1.0 / sqrt(1.0 + (freq_hz / cutoff_hz) ** 2)


def sample_tone(
    freq_hz: float,
    amplitude: float,
    odr_hz: float,
    duration_s: float,
    cutoff_hz: float | None = None,
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    """Return (t_true, true signal, t_samples, samples) with an optional steady-state DLPF."""
    t_true = np.linspace(0.0, duration_s, max(2000, int(duration_s * freq_hz * 40)))
    t_s = np.arange(0.0, duration_s + 1e-12, 1.0 / odr_hz)
    gain, phase = 1.0, 0.0
    if cutoff_hz is not None:
        gain, phase = first_order_gain(freq_hz, cutoff_hz), -atan2(freq_hz, cutoff_hz)
    w = 2 * np.pi * freq_hz
    true = amplitude * np.sin(w * t_true)
    samples = amplitude * gain * np.sin(w * t_s + phase)
    return t_true, true, t_s, samples


# --- 6. Calibration --------------------------------------------------------


def gyro_bias_from_rest(samples: FloatArray) -> FloatArray:
    """Estimate per-axis gyro bias as the mean of a stationary (n, 3) recording."""
    return np.asarray(np.mean(samples, axis=0), dtype=np.float64)


def axis_scale_offset(plus_reading: float, minus_reading: float) -> tuple[float, float]:
    """Return (scale, offset) for one accel axis from +1 g and -1 g readings."""
    if plus_reading <= minus_reading:
        raise ValueError("the +1 g reading must exceed the -1 g reading")
    return (plus_reading - minus_reading) / 2, (plus_reading + minus_reading) / 2


@dataclass(frozen=True)
class MagFit:
    """Hard-iron centre and symmetric soft-iron matrix that map an ellipse to a circle."""

    center: FloatArray
    soft_iron: FloatArray
    radius: float


def fit_ellipse_2d(points: FloatArray) -> MagFit:
    """Least-squares conic fit of a horizontal magnetometer sweep.

    Fits A x^2 + B xy + C y^2 + D x + E y = 1. A symmetric fit cannot see a
    pure rotation, so a corrected sweep can keep one constant heading offset.
    """
    if points.ndim != 2 or points.shape[1] != 2 or points.shape[0] < 5:
        raise ValueError("need an (n>=5, 2) array of points")
    x, y = points[:, 0], points[:, 1]
    design = np.column_stack((x * x, x * y, y * y, x, y))
    coef, *_ = np.linalg.lstsq(design, np.ones_like(x), rcond=None)
    a, b, c, d, e = (float(v) for v in coef)
    shape = np.array([[a, b / 2], [b / 2, c]])
    if np.any(np.linalg.eigvalsh(shape) <= 0):
        raise ValueError("points do not form an ellipse; sweep a full turn")
    center = -0.5 * np.linalg.solve(shape, np.array([d, e]))
    k = 1.0 + float(center @ shape @ center)
    values, vectors = np.linalg.eigh(shape / k)
    radius = 1.0 / sqrt(sqrt(float(np.prod(values))))
    soft = radius * (vectors @ np.diag(np.sqrt(values)) @ vectors.T)
    return MagFit(center, soft, radius)


def apply_mag_fit(points: FloatArray, fit: MagFit) -> FloatArray:
    """Remove hard iron, then undo soft iron."""
    return np.asarray((points - fit.center) @ fit.soft_iron.T, dtype=np.float64)


# --- 7. Heading ------------------------------------------------------------


def naive_heading_deg(mag_body: FloatArray) -> float:
    """Return heading using body x/y only, as if the device were level."""
    return compass_heading_deg(mag_body[:2])


def tilt_compensated_heading_deg(mag_body: FloatArray, roll_deg: float, pitch_deg: float) -> float:
    """Rotate the field into the level frame with known roll/pitch, then take heading."""
    level = rotation(roll_deg, pitch_deg, 0.0) @ mag_body
    return compass_heading_deg(level[:2])


def true_heading_deg(magnetic_heading_deg: float, declination_deg: float) -> float:
    """Convert magnetic to true heading; east declination is positive."""
    return (magnetic_heading_deg + declination_deg) % 360


def angle_diff_deg(a: float, b: float) -> float:
    """Return the signed smallest difference a - b in (-180, 180]."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return 180.0 if d == -180.0 else d


# --- 8. One-axis complementary filter --------------------------------------


def complementary_alpha(tau_s: float, dt: float) -> float:
    """Return the per-step gyro weight for time constant ``tau_s``."""
    return tau_s / (tau_s + dt)


def complementary_tau(alpha: float, dt: float) -> float:
    """Return the time constant that a per-step gyro weight implies."""
    return alpha * dt / (1.0 - alpha)


def complementary_1d(
    gyro_rate_deg_s: FloatArray,
    accel_angle_deg: FloatArray,
    dt: float,
    alpha: float,
    initial_deg: float | None = None,
) -> FloatArray:
    """Run theta_k = alpha (theta_{k-1} + w_{k-1} dt) + (1 - alpha) a_k.

    With a constant gyro bias b the steady-state error is tau * b.
    """
    est = np.empty_like(accel_angle_deg, dtype=np.float64)
    est[0] = accel_angle_deg[0] if initial_deg is None else initial_deg
    for k in range(1, est.size):
        prediction = est[k - 1] + gyro_rate_deg_s[k - 1] * dt
        est[k] = alpha * prediction + (1.0 - alpha) * accel_angle_deg[k]
    return est


# --- 9. Rotations ----------------------------------------------------------


def euler_rate_matrix(roll_deg: float, pitch_deg: float) -> FloatArray:
    """Map body rates [p, q, r] to ZYX Euler rates; singular at pitch = +/-90 deg."""
    phi, theta = radians(roll_deg), radians(pitch_deg)
    if abs(cos(theta)) < 1e-12:
        raise ValueError("gimbal lock: Euler rates undefined at pitch = +/-90 deg")
    return np.array(
        [
            [1.0, sin(phi) * tan(theta), cos(phi) * tan(theta)],
            [0.0, cos(phi), -sin(phi)],
            [0.0, sin(phi) / cos(theta), cos(phi) / cos(theta)],
        ]
    )


def quat_from_euler(roll_deg: float, pitch_deg: float, yaw_deg: float) -> FloatArray:
    """Return unit quaternion [w, x, y, z] equal to rotation(roll, pitch, yaw)."""
    cr, sr = cos(radians(roll_deg) / 2), sin(radians(roll_deg) / 2)
    cp, sp = cos(radians(pitch_deg) / 2), sin(radians(pitch_deg) / 2)
    cy, sy = cos(radians(yaw_deg) / 2), sin(radians(yaw_deg) / 2)
    return np.array(
        [
            cr * cp * cy + sr * sp * sy,
            sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
        ]
    )


def quat_multiply(q: FloatArray, r: FloatArray) -> FloatArray:
    """Return the Hamilton product q * r."""
    w1, x1, y1, z1 = q
    w2, x2, y2, z2 = r
    return np.array(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ]
    )


def quat_to_rotation(q: FloatArray) -> FloatArray:
    """Return the body-to-world rotation matrix of a unit quaternion."""
    w, x, y, z = q / np.linalg.norm(q)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ]
    )


def quat_integrate(q: FloatArray, omega_body_deg_s: FloatArray, dt: float) -> FloatArray:
    """Advance attitude by a constant body rate over ``dt`` (exact for constant rate)."""
    angle = radians(float(np.linalg.norm(omega_body_deg_s))) * dt
    if angle < 1e-15:
        return q.copy()
    axis = np.asarray(omega_body_deg_s, dtype=np.float64) / np.linalg.norm(omega_body_deg_s)
    dq = np.concatenate(([cos(angle / 2)], sin(angle / 2) * axis))
    out = quat_multiply(q, dq)
    return np.asarray(out / np.linalg.norm(out), dtype=np.float64)


# --- 10. Why position drifts ----------------------------------------------


def position_error_m(bias_m_s2: float, t_s: float) -> float:
    """Return the position error from double-integrating a constant accel bias."""
    return 0.5 * bias_m_s2 * t_s**2


def tilt_leak_m_s2(tilt_error_deg: float) -> float:
    """Return the false horizontal acceleration a tilt error leaks from gravity."""
    return G0 * sin(radians(tilt_error_deg))


def double_integrate(accel: FloatArray, dt: float) -> tuple[FloatArray, FloatArray]:
    """Trapezoid-integrate acceleration twice from rest; return (velocity, position)."""
    vel = np.zeros_like(accel, dtype=np.float64)
    pos = np.zeros_like(accel, dtype=np.float64)
    for k in range(1, accel.size):
        vel[k] = vel[k - 1] + 0.5 * (accel[k - 1] + accel[k]) * dt
        pos[k] = pos[k - 1] + 0.5 * (vel[k - 1] + vel[k]) * dt
    return vel, pos


# --- 11. Real data ---------------------------------------------------------

_TIME = ("t", "time", "time_s", "timestamp")
_TIME_MS = ("t_ms", "time_ms")


@dataclass(frozen=True)
class ImuLog:
    """A parsed IMU recording in the notebook's units."""

    t: FloatArray
    accel_g: FloatArray
    gyro_deg_s: FloatArray
    mag: FloatArray | None
    accel_unit_detected: str


@dataclass(frozen=True)
class LogSummary:
    """First things to check in any IMU log."""

    rate_hz: float
    dt_jitter_ms: float
    gyro_bias_deg_s: FloatArray
    accel_norm_mean_g: float
    roll_deg: FloatArray
    pitch_deg: FloatArray


def load_imu_csv(text: str, gyro_unit: Literal["deg/s", "rad/s"] = "deg/s") -> ImuLog:
    """Parse a CSV with time, ax..az and gx..gz columns (mx..mz optional).

    Accelerometer units are detected from the median norm (g or m/s^2).
    """
    reader = csv.reader(io.StringIO(text.strip()))
    try:
        header = [h.strip().lower() for h in next(reader)]
    except StopIteration as exc:
        raise ImuCsvError("the file is empty") from exc
    index = {name: i for i, name in enumerate(header)}
    time_col = next((n for n in _TIME + _TIME_MS if n in index), None)
    needed = ["ax", "ay", "az", "gx", "gy", "gz"]
    missing = [n for n in needed if n not in index] + ([] if time_col else ["t"])
    if missing:
        raise ImuCsvError(f"missing column(s): {', '.join(missing)}; header was {header}")
    has_mag = all(n in index for n in ("mx", "my", "mz"))
    cols = [time_col, *needed] + (["mx", "my", "mz"] if has_mag else [])
    rows: list[list[float]] = []
    for line_no, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            continue
        try:
            rows.append([float(row[index[c]]) for c in cols if c is not None])
        except (ValueError, IndexError) as exc:
            raise ImuCsvError(f"row {line_no} is not numeric: {row}") from exc
    if len(rows) < 10:
        raise ImuCsvError(f"need at least 10 rows, found {len(rows)}")
    data = np.array(rows, dtype=np.float64)
    t = data[:, 0] / (1000.0 if time_col in _TIME_MS else 1.0)
    if np.any(np.diff(t) <= 0):
        raise ImuCsvError("time must strictly increase")
    accel = data[:, 1:4]
    norm = float(np.median(np.linalg.norm(accel, axis=1)))
    if 0.5 <= norm <= 1.5:
        unit = "g"
    elif 5.0 <= norm <= 15.0:
        unit, accel = "m/s^2", accel / G0
    else:
        raise ImuCsvError(f"median accel norm {norm:.3g} is neither ~1 g nor ~9.8 m/s^2")
    gyro = data[:, 4:7] * (degrees(1.0) if gyro_unit == "rad/s" else 1.0)
    mag = data[:, 7:10] if has_mag else None
    return ImuLog(t - t[0], accel, gyro, mag, unit)


def summarize_log(log: ImuLog, rest_s: float = 2.0) -> LogSummary:
    """Estimate rate, timing jitter, rest gyro bias, gravity norm and tilt."""
    dt = np.diff(log.t)
    rest = log.t <= rest_s
    if np.count_nonzero(rest) < 2:
        rest = np.zeros_like(log.t, dtype=np.bool_)
        rest[:2] = True
    tilt = np.array([accel_tilt_deg(f) for f in log.accel_g])
    return LogSummary(
        1.0 / float(np.median(dt)),
        float(np.std(dt)) * 1000.0,
        gyro_bias_from_rest(log.gyro_deg_s[rest]),
        float(np.mean(np.linalg.norm(log.accel_g, axis=1))),
        tilt[:, 0],
        tilt[:, 1],
    )


def example_imu_csv(seed: int = 7) -> str:
    """Return a synthetic 100 Hz, 20 s log: 5 s at rest, then a pitch oscillation."""
    rng = np.random.default_rng(seed)
    t = np.arange(0.0, 20.0, 0.01)
    pitch = np.where(t < 5.0, 0.0, 20.0 * np.sin(0.8 * (t - 5.0)))
    pitch_rate = np.where(t < 5.0, 0.0, 16.0 * np.cos(0.8 * (t - 5.0)))
    bias = np.array([0.4, -0.3, 0.2])
    field = magnetic_field(0.0, 60.0, 48.0)
    out = io.StringIO()
    out.write("t,ax,ay,az,gx,gy,gz,mx,my,mz\n")
    for k, tk in enumerate(t):
        accel = gravity_reading_g(0.0, float(pitch[k])) + 0.004 * rng.standard_normal(3)
        gyro = np.array([0.0, pitch_rate[k], 0.0]) + bias + 0.05 * rng.standard_normal(3)
        mag = rotation(0.0, float(pitch[k]), 30.0).T @ field + 0.3 * rng.standard_normal(3)
        values = [tk, *accel, *gyro, *mag]
        out.write(",".join(f"{v:.6f}" for v in values) + "\n")
    return out.getvalue()


# --- 12. Self-check grading ------------------------------------------------


@dataclass(frozen=True)
class Verdict:
    """Result of comparing a committed prediction with the model's answer."""

    correct: bool
    truth: float
    error: float
    message: str


def grade_numeric(
    guess: float, truth: float, rel_tol: float = 0.1, abs_tol: float = 0.0
) -> Verdict:
    """Accept a guess within max(abs_tol, rel_tol*|truth|) of the truth."""
    error = guess - truth
    allowed = max(abs_tol, rel_tol * abs(truth))
    ok = abs(error) <= allowed
    tag = "Correct" if ok else "Not yet"
    return Verdict(ok, truth, error, f"{tag}: you said {guess:.4g}, the model says {truth:.4g}.")
