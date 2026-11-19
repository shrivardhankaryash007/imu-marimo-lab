"""Small deterministic planar models for IMU navigation lessons.

Angles are degrees at public interfaces. Planar vectors use x-forward, y-left
coordinates; the rotation matrix maps body vectors into the world frame.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


@dataclass(frozen=True)
class MotionCase:
    """Reference and displaced-sensor trajectories for known planar motion.

    ``radial_m_s2`` is signed centripetal acceleration along body x;
    ``tangential_m_s2`` is signed y acceleration. ``body_force`` is the
    sensor's horizontal acceleration rotated into body axes with x bias added.
    Gravity is omitted and yaw is assumed known.
    """

    t: FloatArray
    truth_pos: FloatArray
    sensor_pos: FloatArray
    uncorrected_pos: FloatArray
    corrected_pos: FloatArray
    aided_pos: FloatArray
    truth_vel: FloatArray
    uncorrected_vel: FloatArray
    corrected_vel: FloatArray
    aided_vel: FloatArray
    theta_deg: FloatArray
    radial_m_s2: FloatArray
    tangential_m_s2: FloatArray
    body_force: FloatArray


def _integrate(
    acceleration: FloatArray,
    dt: float,
    initial_pos: FloatArray,
    initial_vel: FloatArray,
) -> tuple[FloatArray, FloatArray]:
    """Integrate acceleration with the trapezoid rule from known initial state."""
    n = acceleration.shape[0]
    velocity = np.empty_like(acceleration)
    position = np.empty_like(acceleration)
    velocity[0] = initial_vel
    position[0] = initial_pos
    for k in range(1, n):
        velocity[k] = velocity[k - 1] + 0.5 * (acceleration[k - 1] + acceleration[k]) * dt
        position[k] = position[k - 1] + 0.5 * (velocity[k - 1] + velocity[k]) * dt
    return position, velocity


def motion_case(
    offset_m: float,
    rate_deg_s: float,
    angular_accel_deg_s2: float,
    bias_m_s2: float,
    aid_every_s: int,
    duration_s: int = 20,
) -> MotionCase:
    """Simulate strapdown horizontal propagation with a forward IMU offset.

    The reference point follows a smooth, nonzero analytic path. The sensor
    sits ``offset_m`` forward of it. A positive angular rate is CCW. Its
    lever-arm acceleration is ``alpha x r + omega x (omega x r)``. Uncorrected
    propagation interprets sensor acceleration as reference acceleration;
    corrected propagation subtracts both lever-arm terms but retains unknown
    bias. If
    ``aid_every_s`` is positive, position and velocity reset to truth at each
    such integer-second sample; zero disables aiding. Sampling is at 100 Hz.
    """
    dt = 0.01
    t = np.arange(0.0, float(duration_s) + dt / 2, dt, dtype=np.float64)
    theta = np.deg2rad(rate_deg_s) * t + 0.5 * np.deg2rad(angular_accel_deg_s2) * t**2
    omega = np.deg2rad(rate_deg_s + angular_accel_deg_s2 * t)
    alpha = np.full_like(t, np.deg2rad(angular_accel_deg_s2))

    truth_pos = np.column_stack((0.7 * t + 0.15 * np.sin(0.4 * t), 0.5 * np.sin(0.35 * t)))
    truth_vel = np.column_stack((0.7 + 0.06 * np.cos(0.4 * t), 0.175 * np.cos(0.35 * t)))
    truth_accel = np.column_stack((-0.024 * np.sin(0.4 * t), -0.06125 * np.sin(0.35 * t)))
    c, s = np.cos(theta), np.sin(theta)
    rotation = np.empty((t.size, 2, 2), dtype=np.float64)
    rotation[:, 0, 0], rotation[:, 0, 1] = c, -s
    rotation[:, 1, 0], rotation[:, 1, 1] = s, c

    # For r_body=[offset, 0], alpha x r=[0, alpha*r] and
    # omega x (omega x r)=[-omega**2*r, 0].
    radial = -(omega**2) * offset_m
    tangential = alpha * offset_m
    lever_body = np.column_stack((radial, tangential))
    lever_world = np.einsum("nij,nj->ni", rotation, lever_body)
    sensor_accel_world = truth_accel + lever_world
    sensor_pos = truth_pos + np.einsum("nij,j->ni", rotation, np.array([offset_m, 0.0]))
    body_force = np.einsum("nji,nj->ni", rotation, sensor_accel_world)
    body_force[:, 0] += bias_m_s2
    measured_world = np.einsum("nij,nj->ni", rotation, body_force)
    corrected_world = np.einsum("nij,nj->ni", rotation, body_force) - lever_world

    uncorrected_pos, uncorrected_vel = _integrate(measured_world, dt, truth_pos[0], truth_vel[0])
    corrected_pos, corrected_vel = _integrate(corrected_world, dt, truth_pos[0], truth_vel[0])
    aided_pos = np.empty_like(truth_pos)
    aided_vel = np.empty_like(truth_vel)
    aided_pos[0], aided_vel[0] = truth_pos[0], truth_vel[0]
    interval = round(aid_every_s / dt) if aid_every_s > 0 else t.size
    for k in range(1, t.size):
        if aid_every_s > 0 and k % interval == 0:
            aided_pos[k], aided_vel[k] = truth_pos[k], truth_vel[k]
            continue
        aided_vel[k] = aided_vel[k - 1] + 0.5 * (corrected_world[k - 1] + corrected_world[k]) * dt
        aided_pos[k] = aided_pos[k - 1] + 0.5 * (aided_vel[k - 1] + aided_vel[k]) * dt
    return MotionCase(
        t,
        truth_pos,
        sensor_pos,
        uncorrected_pos,
        corrected_pos,
        aided_pos,
        truth_vel,
        uncorrected_vel,
        corrected_vel,
        aided_vel,
        np.rad2deg(theta),
        radial,
        tangential,
        body_force,
    )


@dataclass(frozen=True)
class FusionCase:
    """One-axis pitch fusion example with gyro and gravity tilt feedback."""

    t: FloatArray
    truth_deg: FloatArray
    gyro_only_deg: FloatArray
    accel_deg: FloatArray
    fused_deg: FloatArray
    rejected: BoolArray


def fusion_case(
    gyro_bias_deg_s: float,
    accel_pulse_g: float,
    blend: float,
    reject: bool,
) -> FusionCase:
    """Compare gyro integration, accelerometer tilt, and complementary fusion.

    Sampling is 100 Hz for 12 s. The body pitch follows a smooth 1D trajectory.
    Accelerometer specific force uses ENU gravity projected into the pitched
    body, plus an x-axis pulse near mid-run. ``blend`` sets accelerometer
    correction weight each step. Rejection gates when measured force norm
    differs from 1 g by more than 0.12 g; this physical gate can miss a
    disturbance that preserves the norm. Tilt uses ``atan2(-ax, +az)``.
    """
    dt = 0.01
    t = np.arange(0.0, 12.0 + dt / 2, dt, dtype=np.float64)
    truth = 18.0 * np.sin(0.45 * t) + 4.0 * np.sin(0.13 * t)
    truth_rate = np.gradient(truth, dt)
    pulse = np.zeros_like(t)
    pulse[(t >= 5.0) & (t <= 5.5)] = accel_pulse_g
    theta = np.deg2rad(truth)
    ax = -np.sin(theta) + pulse
    az = np.cos(theta)
    accel_deg = np.rad2deg(np.arctan2(-ax, az))
    gyro_rate = truth_rate + gyro_bias_deg_s
    gyro_only, fused = np.zeros_like(t), np.zeros_like(t)
    rejected = np.zeros(t.shape, dtype=np.bool_)
    for k in range(1, t.size):
        gyro_only[k] = gyro_only[k - 1] + gyro_rate[k - 1] * dt
        prediction = fused[k - 1] + gyro_rate[k - 1] * dt
        measured_norm_g = np.hypot(ax[k], az[k])
        rejected[k] = bool(reject and abs(measured_norm_g - 1.0) > 0.12)
        correction = 0.0 if rejected[k] else blend * (accel_deg[k] - prediction)
        fused[k] = prediction + correction
    return FusionCase(t, truth, gyro_only, accel_deg, fused, rejected)


@dataclass(frozen=True)
class ControlCase:
    """Open- and closed-loop response of a saturated planar pitch plant."""

    t: FloatArray
    target_deg: FloatArray
    open_deg: FloatArray
    closed_deg: FloatArray
    torque: FloatArray


def control_case(kp: float, kd: float, disturbance: float) -> ControlCase:
    """Compare open-loop torque with saturated PD position control.

    Fixed ``dt=0.01 s``, unit inertia (1 kg m^2) and viscous damping
    0.25 N m s/rad. Target steps from zero to 20 degrees at t=1 s; external
    torque pulse acts from 4 to 4.5 s. Both actuators saturate at +/-4 N m.
    ``torque`` is the closed-loop command before disturbance; angles are
    returned in degrees while all plant calculations use radians.
    """
    dt, inertia, damping, limit = 0.01, 1.0, 0.25, 4.0
    t = np.arange(0.0, 8.0 + dt / 2, dt, dtype=np.float64)
    target_deg = np.where(t >= 1.0, 20.0, 0.0)
    target = np.deg2rad(target_deg)
    pulse = np.where((t >= 4.0) & (t <= 4.5), disturbance, 0.0)
    open_torque = np.where(t >= 1.0, 0.12, 0.0)
    torque = np.empty_like(t)
    open_angle, open_rate = np.zeros_like(t), np.zeros_like(t)
    closed_angle, closed_rate = np.zeros_like(t), np.zeros_like(t)
    for k in range(1, t.size):
        open_accel = (open_torque[k - 1] + pulse[k - 1] - damping * open_rate[k - 1]) / inertia
        open_rate[k] = open_rate[k - 1] + open_accel * dt
        open_angle[k] = open_angle[k - 1] + open_rate[k - 1] * dt
        command = np.clip(
            kp * (target[k - 1] - closed_angle[k - 1]) - kd * closed_rate[k - 1],
            -limit,
            limit,
        )
        torque[k - 1] = command
        closed_accel = (command + pulse[k - 1] - damping * closed_rate[k - 1]) / inertia
        closed_rate[k] = closed_rate[k - 1] + closed_accel * dt
        closed_angle[k] = closed_angle[k - 1] + closed_rate[k - 1] * dt
    torque[-1] = torque[-2]
    return ControlCase(
        t,
        target_deg,
        np.rad2deg(open_angle),
        np.rad2deg(closed_angle),
        torque,
    )
