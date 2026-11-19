"""Plotly views for the reproducible IMU attitude study."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import plotly.graph_objects as go  # type: ignore[import-untyped]  # Plotly 6 has no stubs.
from plotly.subplots import make_subplots  # type: ignore[import-untyped]  # Plotly 6 has no stubs.

if TYPE_CHECKING:
    from attitude_sim import ControlRun, Replay

_COLORS = {
    "truth": "#222222",
    "gyro": "#0072B2",
    "complementary": "#D55E00",
    "ekf": "#009E73",
    "accel": "#CC79A7",
    "mag": "#E69F00",
}
_DASHES = {"truth": "solid", "gyro": "dot", "complementary": "dash", "ekf": "solid"}


def _base(figure: go.Figure, title: str, height: int) -> go.Figure:
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=height,
        autosize=True,
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        margin={"l": 64, "r": 24, "t": 92, "b": 48},
        font={"family": "Arial, sans-serif", "size": 12, "color": "#202124"},
    )
    figure.update_xaxes(showgrid=True, gridcolor="#e7eaed")
    figure.update_xaxes(title_text="Time (s)", row=3, col=1)
    figure.update_yaxes(showgrid=True, gridcolor="#e7eaed", zeroline=True)
    return figure


def _unwrap_near(values: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Unwrap angles by choosing the nearest 360-degree branch to truth."""
    return np.asarray(values + 360.0 * np.round((reference - values) / 360.0))


def _line(
    figure: go.Figure,
    x: np.ndarray,
    y: np.ndarray,
    name: str,
    color: str,
    dash: str = "solid",
    row: int = 1,
    col: int = 1,
    showlegend: bool = True,
) -> None:
    figure.add_trace(
        go.Scatter(
            x=x.tolist(),
            y=y.tolist(),
            mode="lines",
            name=name,
            legendgroup=name,
            showlegend=showlegend,
            line={"color": color, "dash": dash, "width": 2},
            hovertemplate=f"{name}: %{{y:.2f}}<extra></extra>",
        ),
        row=row,
        col=col,
    )


def estimate_figure(run: Replay) -> go.Figure:
    """Compare truth and three attitude estimates across roll, pitch and yaw."""
    figure = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.055,
        subplot_titles=("Roll", "Pitch", "Yaw"),
    )
    truth = run.truth_euler
    traces = (
        ("Truth", truth, _COLORS["truth"], _DASHES["truth"]),
        ("Gyro only", run.gyro.euler, _COLORS["gyro"], _DASHES["gyro"]),
        (
            "Complementary",
            run.complementary.euler,
            _COLORS["complementary"],
            _DASHES["complementary"],
        ),
        ("Error-state EKF", run.ekf.euler, _COLORS["ekf"], _DASHES["ekf"]),
    )
    for axis, title in enumerate(("Roll", "Pitch", "Yaw"), start=1):
        reference = np.unwrap(np.deg2rad(truth[:, axis - 1])) * (180.0 / np.pi)
        for name, angles, color, dash in traces:
            values = _unwrap_near(angles[:, axis - 1], reference)
            _line(
                figure,
                run.time,
                values,
                name,
                color,
                dash,
                row=axis,
                showlegend=axis == 1,
            )
        figure.update_yaxes(title_text=f"{title} (deg)", row=axis, col=1)
    return _base(figure, "Attitude estimates", 690)


def diagnostic_figure(run: Replay) -> go.Figure:
    """Show geodesic error, local EKF uncertainty and aiding diagnostics."""
    figure = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.075,
        subplot_titles=(
            "Geodesic attitude error",
            "EKF local 1-sigma uncertainty",
            "Sensor and innovation diagnostics",
        ),
        specs=[[{}], [{}], [{"secondary_y": True}]],
    )
    for name, trace, color, dash in (
        ("Gyro only", run.gyro, _COLORS["gyro"], _DASHES["gyro"]),
        ("Complementary", run.complementary, _COLORS["complementary"], _DASHES["complementary"]),
        ("Error-state EKF", run.ekf, _COLORS["ekf"], _DASHES["ekf"]),
    ):
        _line(figure, run.time, trace.error, name, color, dash, row=1)
    figure.update_yaxes(title_text="Error (deg)", rangemode="tozero", row=1, col=1)

    colors = ("#0072B2", "#D55E00", "#009E73")
    for axis, label in enumerate(("Body x", "Body y", "Body z")):
        _line(
            figure,
            run.time,
            run.sigma[:, axis],
            f"{label} sigma",
            colors[axis],
            row=2,
        )
    figure.update_yaxes(title_text="1-sigma (deg)", rangemode="tozero", row=2, col=1)

    for name, values, color in (
        ("Accel |f| / g", run.accel_norm, _COLORS["accel"]),
        ("Mag |m| / nominal", run.mag_norm, _COLORS["mag"]),
    ):
        _line(figure, run.time, values, name, color, row=3)
    for name, values, color, dash in (
        ("Accel NIS", run.accel_nis, _COLORS["gyro"], "dash"),
        ("Mag NIS", run.mag_nis, _COLORS["ekf"], "dot"),
    ):
        figure.add_trace(
            go.Scatter(
                x=run.time.tolist(),
                y=values.tolist(),
                mode="lines",
                name=name,
                line={"color": color, "dash": dash, "width": 1.5},
                connectgaps=False,
                hovertemplate=f"{name}: %{{y:.2f}}<extra></extra>",
            ),
            row=3,
            col=1,
            secondary_y=True,
        )
    figure.update_yaxes(title_text="Norm ratio", row=3, col=1, secondary_y=False)
    figure.update_yaxes(title_text="NIS", rangemode="tozero", row=3, col=1, secondary_y=True)
    return _base(figure, "Estimator diagnostics", 700)


def control_figure(run: ControlRun) -> go.Figure:
    """Compare closed-loop pointing error, attitude response and torque."""
    figure = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.065,
        subplot_titles=("Pointing error", "Attitude response", "Control torque"),
    )
    for name, trace, color, dash in (
        ("Complementary", run.complementary, _COLORS["complementary"], _DASHES["complementary"]),
        ("Error-state EKF", run.ekf, _COLORS["ekf"], _DASHES["ekf"]),
    ):
        _line(figure, run.time, trace.error, f"{name} error", color, dash, row=1)
    figure.update_yaxes(title_text="Error (deg)", rangemode="tozero", row=1, col=1)

    for axis, label in enumerate(("Roll", "Pitch", "Yaw")):
        series = (
            ("Target", run.target[:, axis], _COLORS["truth"], "dot"),
            (
                "Complementary",
                run.complementary.euler[:, axis],
                _COLORS["complementary"],
                _DASHES["complementary"],
            ),
            ("Error-state EKF", run.ekf.euler[:, axis], _COLORS["ekf"], _DASHES["ekf"]),
        )
        for name, values, color, dash in series:
            _line(
                figure,
                run.time,
                values,
                f"{name} {label}",
                color,
                dash,
                row=2,
            )
    figure.update_yaxes(title_text="Angle (deg)", row=2, col=1)

    for axis, label in enumerate(("roll", "pitch", "yaw")):
        for name, trace, color, dash in (
            (
                "Complementary",
                run.complementary,
                _COLORS["complementary"],
                _DASHES["complementary"],
            ),
            ("Error-state EKF", run.ekf, _COLORS["ekf"], _DASHES["ekf"]),
        ):
            _line(
                figure,
                run.time,
                trace.torque[:, axis],
                f"{name} torque {label}",
                color,
                dash,
                row=3,
            )
    figure.update_yaxes(title_text="Torque (N·m)", row=3, col=1)
    return _base(figure, "Closed-loop attitude control", 720)


def _axes(rotation: np.ndarray, origin: np.ndarray, prefix: str, dash: str) -> list[go.Scatter3d]:
    """Create RGB body-axis line segments from an origin and rotation."""
    result = []
    for index, color in enumerate(("#D55E00", "#009E73", "#0072B2")):
        end = origin + rotation[:, index] * 0.35
        result.append(
            go.Scatter3d(
                x=[origin[0].item(), end[0].item()],
                y=[origin[1].item(), end[1].item()],
                z=[origin[2].item(), end[2].item()],
                mode="lines+markers",
                name=f"{prefix} {'XYZ'[index]} axis",
                legendgroup=prefix,
                line={"color": color, "width": 6, "dash": dash},
                marker={"size": 3, "color": color},
                hovertemplate=f"{prefix} {'XYZ'[index]} axis<extra></extra>",
            )
        )
    return result


def pose_figure(run: Replay, index: int) -> go.Figure:
    """Compare true and estimated body/mount axes at a replay sample."""
    if not 0 <= index < run.time.size:
        raise IndexError("replay index is out of range")
    truth_rotation = run.truth[index]
    estimate_rotation = run.ekf.rotations[index]
    sensor_position = truth_rotation @ run.offset_body
    estimated_sensor_position = estimate_rotation @ run.offset_body
    figure = go.Figure()
    figure.add_traces(_axes(truth_rotation, np.zeros(3), "True body", "solid"))
    figure.add_traces(_axes(estimate_rotation, np.zeros(3), "EKF body", "dash"))
    figure.add_traces(_axes(truth_rotation @ run.mount, sensor_position, "True IMU", "solid"))
    figure.add_traces(
        _axes(
            estimate_rotation @ run.mount,
            estimated_sensor_position,
            "EKF IMU",
            "dash",
        )
    )
    figure.add_trace(
        go.Scatter3d(
            x=[sensor_position[0].item()],
            y=[sensor_position[1].item()],
            z=[sensor_position[2].item()],
            mode="markers",
            name="True IMU position",
            marker={"size": 6, "color": "#222222", "symbol": "diamond"},
            hovertemplate="True IMU position<extra></extra>",
        )
    )
    figure.update_layout(
        title=f"Body and sensor frames at {run.time[index]:.2f} s",
        template="plotly_white",
        height=590,
        autosize=True,
        margin={"l": 10, "r": 10, "t": 74, "b": 10},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        scene={
            "aspectmode": "data",
            "xaxis_title": "World east (m)",
            "yaxis_title": "World north (m)",
            "zaxis_title": "World up (m)",
        },
    )
    return figure
