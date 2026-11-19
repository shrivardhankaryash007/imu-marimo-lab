"""Plot the outputs of the IMU lab's deterministic experiments."""

from io import BytesIO

import numpy as np
from matplotlib.figure import Figure

from imu_navigation import ControlCase, FusionCase, MotionCase
from imu_sensor import ChipSample, Vector

INK = "#202f43"
BLUE = "#2473ba"
TEAL = "#167b75"
RUST = "#ae513d"
GRAY = "#62748a"


def png(figure: Figure) -> bytes:
    """Encode a plot without writing temporary files or relying on pyplot."""
    image = BytesIO()
    figure.savefig(image, format="png", dpi=132, facecolor="white")
    return image.getvalue()


def plot_chip(sample: ChipSample) -> Figure:
    """Plot channel clipping and one normalized period of gyro drive and sense."""
    fig = Figure(figsize=(9.2, 3.2), layout="constrained")
    accel, gyro = fig.subplots(1, 2)
    channels = np.arange(3)
    accel.bar(channels - 0.18, sample.specific_g, 0.36, color=GRAY, label="Ideal input")
    accel.bar(channels + 0.18, sample.measured_g, 0.36, color=TEAL, label="Clipped reading")
    accel.axhline(0, color=INK, lw=0.8)
    accel.set(
        xticks=channels,
        xticklabels=["x", "y", "z"],
        ylabel="Specific force (g)",
        title="Accelerometer channels",
    )
    accel.legend(frameon=False, fontsize=8)
    phase = np.linspace(0, 360, 181)
    sense = sample.coriolis_mm_s2 * np.cos(np.deg2rad(phase))
    gyro.plot(phase, sense, color=RUST, lw=2)
    gyro.scatter([0], [sample.coriolis_mm_s2], c=INK, label="Readout phase", s=23)
    gyro.axhline(0, color=INK, lw=0.8)
    gyro.set(
        xlabel="Drive phase (°)",
        ylabel="Sense acceleration (mm/s²)",
        title="Coriolis response at this rate",
    )
    gyro.legend(frameon=False, fontsize=8)
    for ax in (accel, gyro):
        ax.grid(axis="y", alpha=0.18)
    return fig


def plot_magnetic(ideal: Vector, raw: Vector, selected: Vector, selected_raw: Vector) -> Figure:
    """Plot level calibration sweep and the active heading sample."""
    fig = Figure(figsize=(7.1, 4.25), layout="constrained")
    ax = fig.subplots()
    ax.plot(*ideal.T, color=TEAL, lw=2, ls="--", label="Ideal calibrated sweep")
    ax.plot(*raw.T, color=RUST, lw=2, label="Raw sweep")
    ax.scatter(selected[0], selected[1], c=TEAL, s=45)
    ax.scatter(selected_raw[0], selected_raw[1], c=RUST, s=45)
    ax.axhline(0, lw=0.7, color=GRAY)
    ax.axvline(0, lw=0.7, color=GRAY)
    ax.set(xlabel="Forward component (µT)", ylabel="Left component (µT)", aspect="equal")
    ax.grid(alpha=0.18)
    ax.legend(frameon=False, loc="upper right")
    return fig


def plot_attitude(body: Vector, sensor: Vector) -> Figure:
    """Show body and mounted sensor axes in a common right-handed world."""
    fig = Figure(figsize=(7.1, 3.8), layout="constrained")
    ax = fig.add_subplot(projection="3d")
    for basis, label, length, linestyle in (
        (np.eye(3), "W", 0.7, ":"),
        (body, "B", 1.0, "-"),
        (sensor, "S", 1.16, "--"),
    ):
        for axis, (name, color) in enumerate(zip("xyz", (RUST, TEAL, BLUE), strict=True)):
            tip = length * basis[:, axis]
            ax.plot([0, tip[0]], [0, tip[1]], [0, tip[2]], lw=2, c=color, ls=linestyle)
            ax.scatter(*tip, s=10, c=color)
            label_tip = 1.08 * tip
            ax.text(*label_tip, f"{label}{name}", color=color, fontsize=8)
    ax.set(
        xlim=(-1.3, 1.3),
        ylim=(-1.3, 1.3),
        zlim=(-1.3, 1.3),
        xlabel="East",
        ylabel="North",
        zlabel="Up",
    )
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=23, azim=-58)
    return fig


def plot_motion(case: MotionCase, index: int) -> Figure:
    """Compare true paths and reference-point position errors over time."""
    fig = Figure(figsize=(9.2, 3.55), layout="constrained")
    path, err = fig.subplots(1, 2)
    path.plot(*case.truth_pos.T, c=INK, lw=2, label="Reference truth")
    path.plot(*case.sensor_pos.T, c=RUST, lw=1.55, label="Sensor truth")
    endpoints = np.stack((case.truth_pos[index], case.sensor_pos[index]))
    path.plot(*endpoints.T, "o-", c=BLUE, lw=1.4, ms=4, label="Current lever arm")
    path.set(xlabel="East (m)", ylabel="North (m)", title="Where each point travels")
    path.legend(frameon=False, fontsize=8)
    for positions, color, name in (
        (case.uncorrected_pos, RUST, "Ignore offset"),
        (case.corrected_pos, BLUE, "Correct offset"),
        (case.aided_pos, TEAL, "Correct + aid"),
    ):
        error = np.linalg.norm(positions - case.truth_pos, axis=1)
        err.plot(case.t, error, c=color, label=name, lw=1.65)
    err.axvline(case.t[index], c=GRAY, ls=":", lw=1)
    err.set(xlabel="Time (s)", ylabel="Position error (m)", title="Estimating the reference point")
    err.legend(frameon=False, fontsize=8)
    for ax in (path, err):
        ax.grid(alpha=0.18)
    return fig


def plot_fusion(case: FusionCase) -> Figure:
    """Compare gyroscope integration, acceleration tilt and fused pitch."""
    fig = Figure(figsize=(8.7, 3.55), layout="constrained")
    ax = fig.subplots()
    ax.axvspan(5.0, 5.5, facecolor=RUST, alpha=0.10, label="Translation interval")
    ax.plot(case.t, case.truth_deg, color=INK, lw=2, label="True tilt")
    ax.plot(case.t, case.gyro_only_deg, c=RUST, ls="--", label="Integrate gyro")
    ax.plot(case.t, case.accel_deg, c=GRAY, lw=1.2, label="Acceleration tilt")
    ax.plot(case.t, case.fused_deg, c=TEAL, lw=2, label="Complementary estimate")
    ax.set(xlabel="Time (s)", ylabel="Pitch (°)")
    ax.grid(alpha=0.18)
    ax.legend(frameon=False, ncols=2, fontsize=8)
    return fig


def plot_control(case: ControlCase) -> Figure:
    """Compare command following and applied feedback torque."""
    fig = Figure(figsize=(9.2, 3.5), layout="constrained")
    angle, effort = fig.subplots(1, 2)
    angle.plot(case.t, case.target_deg, c=INK, ls=":", lw=2, label="Target")
    angle.plot(case.t, case.open_deg, c=RUST, label="Open loop")
    angle.plot(case.t, case.closed_deg, c=TEAL, lw=2, label="PD feedback")
    angle.set(xlabel="Time (s)", ylabel="Attitude (°)")
    angle.legend(frameon=False, fontsize=8)
    effort.plot(case.t, case.torque, c=BLUE, lw=1.6)
    effort.set(xlabel="Time (s)", ylabel="Commanded torque (N·m)")
    for ax in (angle, effort):
        ax.axvspan(4.0, 4.5, color=RUST, alpha=0.10)
        ax.grid(alpha=0.18)
    return fig


def plot_pose(body: Vector, offset: Vector) -> Figure:
    """Show a rigid offset and recovered body axes relative to the reference origin."""
    fig = Figure(figsize=(7.2, 4.0), layout="constrained")
    ax = fig.add_subplot(projection="3d")
    for axis, (name, color) in enumerate(zip("xyz", (RUST, TEAL, BLUE), strict=True)):
        tip = body[:, axis]
        ax.quiver(0, 0, 0, *tip, color=color, arrow_length_ratio=0.12)
        ax.text(*(1.12 * tip), f"Body {name}", color=color, fontsize=8)
    ax.plot([0, offset[0]], [0, offset[1]], [0, offset[2]], "o--", c=INK, lw=1.7, ms=4)
    ax.scatter(*offset, s=38, c=INK, marker="D")
    ax.text(*offset, "  Sensor", color=INK, fontsize=9)
    ax.set(
        xlim=(-2, 2),
        ylim=(-2, 2),
        zlim=(-2, 2),
        xlabel="East from reference (m)",
        ylabel="North (m)",
        zlabel="Up (m)",
    )
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=24, azim=-56)
    return fig
