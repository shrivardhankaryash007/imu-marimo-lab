# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo==0.25.2", "numpy==2.4.6", "plotly==6.5.2"]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="3D IMU attitude lab")


@app.cell
def _():
    import asyncio
    import re
    from io import StringIO
    from pathlib import Path

    import marimo as mo
    import numpy as np

    import attitude_charts as charts
    import attitude_sim as sim
    import imu_tutor as tutor

    return Path, StringIO, asyncio, charts, mo, np, re, sim, tutor


@app.cell(hide_code=True)
def _(Path, mo, re, tutor):
    _text = Path(__file__).with_name("attitude-theory.md").read_text(encoding="utf-8")
    _parts = re.split(r"^## (.+)$", _text, flags=re.MULTILINE)[1:]
    equations = dict(zip(_parts[::2], _parts[1::2], strict=True))
    tutor_context = tutor.ExperimentContext("3D attitude estimation and control")
    mo.md(r"""
    # 3D IMU attitude lab

    Estimate **roll, pitch and yaw** from one synthetic sensor stream. Then see
    what happens when each estimator closes its own torque loop.

    **Predict first.** Turn off heading aid. Which angle can gravity still correct?
    Try a mount-yaw calibration error next, then scrub to the acceleration pulse.
    """)
    return equations, tutor_context


@app.cell(hide_code=True)
def _(mo, sim):
    _base = sim.Settings()

    def _slider(low: float, high: float, step: float, value: float, label: str):
        return mo.ui.slider(
            low,
            high,
            step=step,
            value=value,
            label=label,
            debounce=True,
            show_value=True,
            include_input=True,
        )

    experiment = mo.ui.dictionary(
        {
            "heading_aid": mo.ui.checkbox(
                value=_base.heading_aid, label="Magnetometer heading aid"
            ),
            "reject_disturbance": mo.ui.checkbox(
                value=_base.reject_disturbance, label="Reject suspect vectors"
            ),
            "ideal_lever_correction": mo.ui.checkbox(label="Ideal lever-arm correction"),
            "gyro_bias": _slider(0, 5, 0.1, _base.gyro_bias, "Gyro bias (°/s)"),
            "translation": _slider(0, 1.5, 0.05, _base.translation, "Translation pulse (g)"),
            "magnetic_interference": _slider(
                0,
                1.5,
                0.05,
                _base.magnetic_interference,
                "Magnetic disturbance (fraction of Earth's field)",
            ),
            "mount_roll": _slider(-180, 180, 5, _base.mount_roll, "Mount roll (°)"),
            "mount_pitch": _slider(-90, 90, 5, _base.mount_pitch, "Mount pitch (°)"),
            "mount_yaw": _slider(-180, 180, 5, _base.mount_yaw, "Mount yaw (°)"),
            "mount_yaw_error": _slider(
                -45, 45, 1, _base.mount_yaw_error, "Mount calibration yaw error (°)"
            ),
            "offset_x": _slider(-2, 2, 0.01, _base.offset_x, "IMU body x offset (m)"),
            "offset_y": _slider(-2, 2, 0.01, _base.offset_y, "IMU body y offset (m)"),
            "offset_z": _slider(-2, 2, 0.01, _base.offset_z, "IMU body z offset (m)"),
            "initial_yaw_error": _slider(
                -45, 45, 1, _base.initial_yaw_error, "Initial heading error (°)"
            ),
            "complementary_kp": _slider(
                0,
                8,
                0.1,
                _base.complementary_kp,
                "Complementary proportional gain (1/s)",
            ),
            "complementary_ki": _slider(
                0, 1, 0.01, _base.complementary_ki, "Complementary bias gain (1/s²)"
            ),
            "accel_sigma": _slider(
                0.01,
                0.2,
                0.005,
                _base.accel_sigma,
                "EKF accelerometer direction std. dev.",
            ),
            "mag_sigma": _slider(
                0.01,
                0.2,
                0.005,
                _base.mag_sigma,
                "EKF magnetometer direction std. dev.",
            ),
            "kalman_gyro_density": _slider(
                0.001, 0.04, 0.001, _base.kalman_gyro_density, "EKF gyro noise (rad/√s)"
            ),
            "kalman_bias_rw": _slider(
                0, 0.02, 0.001, _base.kalman_bias_rw, "EKF bias walk (rad/s/√s)"
            ),
        }
    )

    def _group(*names: str):
        return mo.hstack(
            [experiment[name] for name in names],
            justify="start",
            align="center",
            wrap=True,
            gap=0.9,
        )

    mo.vstack(
        [
            _group("heading_aid", "reject_disturbance", "ideal_lever_correction"),
            _group("gyro_bias", "translation", "magnetic_interference"),
            mo.accordion(
                {
                    "Mount and initial alignment": _group(
                        "mount_roll",
                        "mount_pitch",
                        "mount_yaw",
                        "mount_yaw_error",
                        "offset_x",
                        "offset_y",
                        "offset_z",
                        "initial_yaw_error",
                    ),
                    "Complementary and Kalman tuning": _group(
                        "complementary_kp",
                        "complementary_ki",
                        "accel_sigma",
                        "mag_sigma",
                        "kalman_gyro_density",
                        "kalman_bias_rw",
                    ),
                }
            ),
        ]
    )
    return (experiment,)


@app.cell(hide_code=True)
def _(experiment, sim):
    settings = sim.Settings(**experiment.value)
    replay = sim.run_replay(settings)
    return replay, settings


@app.cell(hide_code=True)
def _(charts, equations, mo, replay):
    replay_tabs = mo.ui.tabs(
        {
            "Roll · pitch · yaw": mo.ui.plotly(
                charts.estimate_figure(replay),
                config={"displaylogo": False, "responsive": True},
            ),
            "Error · confidence · innovation": mo.ui.plotly(
                charts.diagnostic_figure(replay),
                config={"displaylogo": False, "responsive": True},
            ),
            "Equations and derivations": mo.accordion(
                {name: mo.md(body) for name, body in equations.items()}
            ),
        }
    )
    mo.vstack([replay_tabs])
    return


@app.cell(hide_code=True)
def _(mo, sim):
    sample_time = mo.ui.slider(
        0,
        sim.DURATION,
        step=sim.DT,
        value=4.2,
        label="Inspect sample (s)",
        debounce=True,
        show_value=True,
        include_input=True,
        full_width=True,
    )
    mo.vstack([mo.md("## Inspect a sample"), sample_time])
    return (sample_time,)


@app.cell(hide_code=True)
def _(charts, mo, np, replay, sample_time, settings, sim):
    def _vec(value: sim.Array) -> str:
        return " / ".join(f"{x:+.2f}" for x in value)

    def _update(nis: float, accepted: bool, angle: float) -> str:
        if not np.isfinite(nis):
            return "Skipped before the EKF update"
        _decision = "accepted" if accepted else "rejected"
        return f"NIS {nis:.2f}, {_decision}, rotation {angle:.2f}°"

    _i = round(sample_time.value / sim.DT)
    _g, _c, _e = replay.gyro, replay.complementary, replay.ekf
    _accel_update = _update(
        replay.accel_nis[_i], replay.accel_accepted[_i], replay.accel_correction[_i]
    )
    _mag_update = _update(replay.mag_nis[_i], replay.mag_accepted[_i], replay.mag_correction[_i])
    sample_summary = (
        f"At **{replay.time[_i]:.2f} s**, heading aid "
        f"{'on' if settings.heading_aid else 'off'}, rejection "
        f"{'on' if settings.reject_disturbance else 'off'}.\n\n"
        "| Body attitude | Roll / pitch / yaw (°) | 3D attitude error (°) |\n"
        "|---|---:|---:|\n"
        f"| Truth | {_vec(replay.truth_euler[_i])} | 0.00 |\n"
        f"| Gyro only | {_vec(_g.euler[_i])} | {_g.error[_i]:.2f} |\n"
        f"| Complementary | {_vec(_c.euler[_i])} | {_c.error[_i]:.2f} |\n"
        f"| Error-state EKF | {_vec(_e.euler[_i])} | {_e.error[_i]:.2f} |\n\n"
        f"**EKF accelerometer:** {_accel_update}. "
        f"**Magnetometer:** {_mag_update}. "
        f"Force norm used by gate {replay.accel_norm[_i]:.3f} g, magnetic norm "
        f"{replay.mag_norm[_i]:.3f} times reference.\n\n"
        f"**Raw sensor axes:** gyro {_vec(np.rad2deg(replay.raw_gyro[_i]))} °/s, "
        f"specific force {_vec(replay.raw_force[_i])} m/s². "
        f"EKF bias estimate {_vec(np.rad2deg(_e.bias[_i]))} °/s."
    )
    mo.vstack(
        [
            mo.md(sample_summary),
            mo.ui.plotly(
                charts.pose_figure(replay, _i),
                config={"displaylogo": False, "responsive": True},
            ),
        ]
    )
    return (sample_summary,)


@app.cell(hide_code=True)
def _(mo):
    controller = mo.ui.dictionary(
        {
            "kp": mo.ui.slider(
                0,
                4,
                step=0.05,
                value=0.8,
                label="Torque Kp (N·m/rad)",
                show_value=True,
                debounce=True,
            ),
            "kd": mo.ui.slider(
                0,
                1.5,
                step=0.05,
                value=0.45,
                label="Torque Kd (N·m·s/rad)",
                show_value=True,
                debounce=True,
            ),
            "limit": mo.ui.slider(
                0.05,
                1,
                step=0.05,
                value=0.35,
                label="Per-axis torque limit (N·m)",
                show_value=True,
                debounce=True,
            ),
            "disturbance": mo.ui.slider(
                0,
                0.4,
                step=0.01,
                value=0.08,
                label="Torque disturbance (N·m)",
                show_value=True,
                debounce=True,
            ),
        }
    )
    mo.vstack(
        [
            mo.md(r"""
        ## Adjust the attitude

        Two bodies start from the same conditions. Each controller feeds on its
        own estimate and actuates its own body. The desired roll, pitch and yaw
        step to **12°, -18°, 45°** at 1 s. Both bodies receive a torque pulse at 5 s.

        $$e_b=\operatorname{Log}(\hat R_{wb}^{\mathsf T} R_d),\qquad
        \tau=\operatorname{clip}(K_p e_b - K_d \hat\omega_b)$$

        Lower the torque limit or turn down damping. See whether the true body
        still tracks even when the plotted estimate appears trustworthy.
        """),
            mo.hstack(
                [controller[key] for key in controller.elements],
                justify="start",
                wrap=True,
                gap=0.8,
            ),
        ]
    )
    return (controller,)


@app.cell(hide_code=True)
def _(charts, controller, mo, np, settings, sim):
    _gains = controller.value
    _run = sim.run_control(settings, **_gains)
    _comp, _ekf = _run.complementary, _run.ekf
    control_summary = (
        f"Kp {_gains['kp']:.2f}, Kd {_gains['kd']:.2f}, limit {_gains['limit']:.2f} N·m, "
        f"disturbance {_gains['disturbance']:.2f} N·m. At 12 s: complementary "
        f"**{_comp.error[-1]:.2f}°** tracking error and {_comp.clipped.sum()} clipped samples, "
        f"EKF **{_ekf.error[-1]:.2f}°** and {_ekf.clipped.sum()} clipped samples. "
        f"Over the last second: complementary mean {_comp.error[-50:].mean():.2f}°, "
        f"EKF mean {_ekf.error[-50:].mean():.2f}°. "
        f"Peak torque components: {np.max(abs(_comp.torque)):.2f} and "
        f"{np.max(abs(_ekf.torque)):.2f} N·m."
    )
    mo.vstack(
        [
            mo.md(control_summary),
            mo.ui.plotly(
                charts.control_figure(_run),
                config={"displaylogo": False, "responsive": True},
            ),
        ]
    )
    return (control_summary,)


@app.cell(hide_code=True)
def _(control_summary, equations, sample_summary, tutor_context):
    tutor_context.values = (
        sample_summary.replace("**", "") + "\nControl: " + control_summary.replace("**", "")
    )
    _ordered = (
        "Complementary filters",
        "Error-state Kalman filter",
        "Geometric attitude control",
        "Sources and scope",
    )
    tutor_context.reference = "\n".join(equations.get(section, "") for section in _ordered)
    return


@app.cell(hide_code=True)
def _(asyncio, mo, tutor, tutor_context):
    try:
        _settings = tutor.load_settings()
        _setup = "Tutor off. See the README to connect your preferred model."
    except tutor.TutorUnavailable as _error:
        _settings = None
        _setup = str(_error)

    chat = None
    if _settings is not None:

        async def _answer(messages: list[tutor.Turn], _config: object) -> str:
            try:
                return await asyncio.to_thread(
                    tutor.ask_tutor,
                    _settings,
                    tutor.tutor_messages(tutor_context, messages),
                )
            except tutor.TutorUnavailable as error:
                return f"Tutor unavailable. {error} The experiments are still available."

        chat = mo.ui.chat(
            _answer,
            prompts=[
                "Why was the correction rejected at this sample?",
                "How does my mounting error change the control result?",
            ],
            max_height=360,
        )
        _panel = mo.vstack(
            [
                mo.md(
                    "## Ask the tutor\nOn submit, your configured provider receives the selected "
                    "experiment and recent conversation."
                ),
                chat,
            ]
        )
    else:
        _panel = mo.md(f"## Optional tutor\n{_setup}")
    mo.sidebar(_panel, width="22rem")
    return (chat,)


@app.cell(hide_code=True)
def _(StringIO, mo, np, replay):
    _series = np.column_stack(
        (
            replay.time,
            replay.truth_euler,
            replay.gyro.euler,
            replay.complementary.euler,
            replay.ekf.euler,
            replay.accel_accepted,
            replay.mag_accepted,
        )
    )
    _header = (
        "t_s,"
        + ",".join(
            f"{method}_{axis}_deg"
            for method in ("truth", "gyro", "comp", "ekf")
            for axis in ("roll", "pitch", "yaw")
        )
        + ",accel_used,mag_used"
    )
    _buffer = StringIO()
    np.savetxt(_buffer, _series, delimiter=",", fmt="%.6g", header=_header, comments="")
    mo.download(
        _buffer.getvalue().encode(),
        filename="imu-attitude-replay.csv",
        mimetype="text/csv",
        label="Download sampled replay CSV",
    )
    return


@app.cell(hide_code=True)
def _(chat, mo):
    takeaway = mo.ui.text_area(label="Keep an engineering takeaway", full_width=True, rows=3)
    keep_chat = mo.ui.checkbox(label="Include tutor conversation")
    _options = [keep_chat] if chat is not None else []
    mo.vstack([mo.md("## Save the trial"), takeaway, *_options])
    return keep_chat, takeaway


@app.cell(hide_code=True)
def _(chat, control_summary, keep_chat, mo, sample_summary, takeaway, tutor):
    _saved = tutor.notes_markdown(
        "Sample and control",
        sample_summary + "\n\n" + control_summary,
        takeaway.value.strip(),
        chat.value if chat is not None and keep_chat.value else [],
        title="3D IMU attitude lab",
    )
    mo.download(
        _saved,
        filename="imu-attitude-notes.md",
        mimetype="text/markdown",
        label="Download Markdown notes",
    )
    return


if __name__ == "__main__":
    app.run()
