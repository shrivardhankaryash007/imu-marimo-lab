"""Ground-truth models for the chapter's sensor and frame experiments."""

from dataclasses import dataclass
from math import cos, radians, sin

import numpy as np
from numpy.typing import NDArray

Vector = NDArray[np.float64]


def rotation(roll_deg: float, pitch_deg: float, yaw_deg: float) -> Vector:
    """Return the active body-to-world right-handed matrix Rz(yaw) Ry(pitch) Rx(roll)."""
    roll, pitch, yaw = map(radians, (roll_deg, pitch_deg, yaw_deg))
    rx = np.array([[1, 0, 0], [0, cos(roll), -sin(roll)], [0, sin(roll), cos(roll)]])
    ry = np.array([[cos(pitch), 0, sin(pitch)], [0, 1, 0], [-sin(pitch), 0, cos(pitch)]])
    rz = np.array([[cos(yaw), -sin(yaw), 0], [sin(yaw), cos(yaw), 0], [0, 0, 1]])
    return np.asarray(rz @ ry @ rx, dtype=np.float64)


@dataclass(frozen=True)
class ChipSample:
    """Ideal force, clipped readout and transducer behavior in sensor coordinates."""

    specific_g: Vector
    measured_g: Vector
    displacement_um: float
    coriolis_mm_s2: float


def chip_sample(
    tilt_deg: float,
    linear_x_g: float,
    free_fall: bool,
    full_scale_g: float,
    drive_mm_s: float,
    rate_deg_s: float,
) -> ChipSample:
    """Generate signed specific force, clipping, and a Coriolis drive phase example."""
    # ENU gravity points down. A supported level sensor reads upward +1 g.
    specific_g = rotation(0, tilt_deg, 0).T @ [linear_x_g, 0, 0 if free_fall else 1]
    measured_g = np.clip(specific_g, -full_scale_g, full_scale_g)
    # The illustrative spring compliance is 0.18 µm/g, independent of ADC range.
    displacement_um = -0.18 * float(specific_g[0]) + 0.0
    coriolis_mm_s2 = -2 * drive_mm_s * radians(rate_deg_s)
    return ChipSample(specific_g, measured_g, displacement_um, coriolis_mm_s2)


def magnetic_field(declination_deg: float, inclination_deg: float, strength_ut: float) -> Vector:
    """Return an ENU magnetic vector with positive east declination and down dip."""
    declination, inclination = map(radians, (declination_deg, inclination_deg))
    return strength_ut * np.array(
        [
            sin(declination) * cos(inclination),
            cos(declination) * cos(inclination),
            -sin(inclination),
        ]
    )


def magnetic_sweep(
    yaw_deg: float, bias_ut: float, distortion: float, declination_deg: float
) -> tuple[Vector, Vector, Vector, Vector]:
    """Return ideal and raw sweep points, and the selected ideal/raw horizontal vectors."""
    angles = np.linspace(0, 360, 145)
    field = magnetic_field(declination_deg, 45, 48)
    ideal = np.array([(rotation(0, 0, theta).T @ field)[:2] for theta in angles])
    selected = (rotation(0, 0, yaw_deg).T @ field)[:2]
    transform = np.array([[distortion, 0.12 * (distortion - 1)], [0, 1 / distortion]])
    bias = np.array([bias_ut, -0.45 * bias_ut])
    return ideal, ideal @ transform.T + bias, selected, transform @ selected + bias


def compass_heading_deg(field_xy: Vector) -> float:
    """Return clockwise heading from magnetic north for a level forward/left body."""
    forward, left = field_xy
    if np.hypot(forward, left) < 1e-9:
        return float("nan")
    return float(np.degrees(np.arctan2(left, forward))) % 360


@dataclass(frozen=True)
class ReferencePose:
    """Reference-point kinematics and mounting-corrected attitude in world axes."""

    body_to_world: Vector
    position_m: Vector
    velocity_m_s: Vector
    acceleration_m_s2: Vector
    offset_world_m: Vector


def reference_pose(
    sensor_to_world: Vector,
    sensor_to_body: Vector,
    offset_in_body_m: Vector,
    sensor_position_m: Vector,
    sensor_velocity_m_s: Vector,
    specific_force_in_sensor_m_s2: Vector,
    omega_in_world_rad_s: Vector,
    alpha_in_world_rad_s2: Vector,
    gravity_in_world_m_s2: Vector,
) -> ReferencePose:
    """Map a known sensor state to an arbitrary reference fixed on the same rigid body."""
    body_to_world = sensor_to_world @ sensor_to_body.T
    r = body_to_world @ offset_in_body_m
    omega, alpha = omega_in_world_rad_s, alpha_in_world_rad_s2
    a_sensor = sensor_to_world @ specific_force_in_sensor_m_s2 + gravity_in_world_m_s2
    return ReferencePose(
        body_to_world,
        sensor_position_m - r,
        sensor_velocity_m_s - np.cross(omega, r),
        a_sensor - np.cross(alpha, r) - np.cross(omega, np.cross(omega, r)),
        r,
    )


def pose_trial(
    offset_in_body_m: Vector, yaw_deg: float, mount_yaw_deg: float, spin_scale: float
) -> tuple[ReferencePose, Vector, Vector, Vector]:
    """Synthesize an off-axis sensor snapshot and return its recovered reference state."""
    body_to_world = rotation(20, -30, yaw_deg)
    mount = rotation(10, 15, mount_yaw_deg)
    sensor_to_world = body_to_world @ mount
    r = body_to_world @ offset_in_body_m
    position, velocity, acceleration = np.array(
        [[2.0, -1.0, 1.5], [0.8, 0.3, 0.4], [0.1, 0.4, -0.2]]
    )
    omega = spin_scale * np.array([0.4, -0.7, 1.1])
    alpha = np.array([0.3, 0.2, -0.4])
    gravity = np.array([0.0, 0.0, -9.80665])
    p_sensor = position + r
    v_sensor = velocity + np.cross(omega, r)
    a_sensor = acceleration + np.cross(alpha, r) + np.cross(omega, np.cross(omega, r))
    f_sensor = sensor_to_world.T @ (a_sensor - gravity)
    ref = reference_pose(
        sensor_to_world,
        mount,
        offset_in_body_m,
        p_sensor,
        v_sensor,
        f_sensor,
        omega,
        alpha,
        gravity,
    )
    return ref, p_sensor, v_sensor, f_sensor
