# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo==0.25.2", "matplotlib==3.10.8", "numpy==2.4.6"]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="IMUs from chip to controller")


@app.cell
def _():
    import asyncio
    import re
    from base64 import b64encode
    from collections.abc import Iterable
    from pathlib import Path

    import marimo as mo
    import numpy as np

    import imu_navigation as nav
    import imu_plots as plots
    import imu_sensor as sensor
    import imu_tutor as tutor
    from imu_cutaway import cutaway

    return (
        Iterable,
        Path,
        asyncio,
        b64encode,
        cutaway,
        mo,
        nav,
        np,
        plots,
        re,
        sensor,
        tutor,
    )


@app.cell(hide_code=True)
def _(Path, re, tutor):
    _file = Path(__file__).with_name("course.md").read_text(encoding="utf-8")
    _sections = re.split(r"^## (.+)$", _file, flags=re.MULTILINE)[1:]
    sections = dict(zip(_sections[::2], _sections[1::2], strict=True))
    active_context = tutor.ExperimentContext()
    return active_context, sections


@app.cell(hide_code=True)
def _(mo, sections):
    _labels = [
        "Sensors",
        "Magnetometer",
        "Attitude",
        "Motion",
        "3D pose",
        "Fusion",
        "Control",
    ]
    chapter = mo.ui.radio(
        dict(zip(_labels, sections, strict=True)),
        value="Sensors",
        inline=True,
        label="Chapter",
    )
    mo.vstack(
        [
            mo.md("""
            # IMUs from chip to controller

            Start with what the chip feels. Follow those signals through attitude,
            reference-point motion, estimation and feedback. An optional tutor lives in the sidebar.

            For the equations and the hands-on complementary, Kalman, RLS and
            control experiments, double-click **Open IMU Math.command** in the repo.
            """),
            chapter,
        ],
        gap=0.4,
    )
    return (chapter,)


@app.cell(hide_code=True)
def _(chapter, mo):
    _slider = mo.ui.slider
    match chapter.value:
        case "Sensors":
            _exercise = (
                "Will the sensor read 1 g or zero in free fall? Tilt it first, "
                "then switch support. "
                "Reverse the gyro rate and watch the sign of the Coriolis term."
            )
            _controls = {
                "tilt": _slider(
                    -90, 90, value=20, step=5, label="Sensor tilt (°)", show_value=True
                ),
                "linear": _slider(
                    -4,
                    4,
                    value=0,
                    step=0.25,
                    label="World +x acceleration (g)",
                    show_value=True,
                ),
                "fall": mo.ui.checkbox(label="Free fall along z"),
                "range": mo.ui.dropdown({"±2 g": 2, "±8 g": 8}, value="±2 g", label="ADC range"),
                "drive": _slider(
                    0,
                    50,
                    value=25,
                    step=5,
                    label="Peak gyro drive (mm/s)",
                    show_value=True,
                ),
                "rate": _slider(
                    -360,
                    360,
                    value=90,
                    step=15,
                    label="Gyroscope rate (°/s)",
                    show_value=True,
                ),
                "stage": mo.ui.dropdown(
                    ["Pattern", "Release", "Package", "Readout"],
                    value="Release",
                    label="Fabrication stage",
                ),
            }
        case "Magnetometer":
            _exercise = (
                "Rotate the board and add bias. Predict which adjustment shifts the center "
                "and which changes the shape. Then compare raw and calibrated heading."
            )
            _controls = {
                "yaw": _slider(
                    0, 360, value=50, step=5, label="Yaw from East (°)", show_value=True
                ),
                "bias": _slider(
                    -30, 30, value=14, label="Hard iron x offset (µT)", show_value=True
                ),
                "scale": _slider(
                    0.45,
                    1.8,
                    value=1.25,
                    step=0.05,
                    label="Soft iron scale",
                    show_value=True,
                ),
                "declination": _slider(
                    -30, 30, value=10, label="East declination (°)", show_value=True
                ),
            }
        case "Attitude":
            _exercise = (
                "Turn the mounting offset with the object held still. Compare the sensor's "
                "axis arrows with the body's. Change yaw alone and watch the gravity reading."
            )
            _controls = {
                "roll": _slider(
                    -180, 180, value=15, step=5, label="Body roll (°)", show_value=True
                ),
                "pitch": _slider(
                    -90, 90, value=25, step=5, label="Body pitch (°)", show_value=True
                ),
                "yaw": _slider(-180, 180, value=35, step=5, label="Body yaw (°)", show_value=True),
                "mount": _slider(
                    -180,
                    180,
                    value=45,
                    step=5,
                    label="Sensor mount about body z (°)",
                    show_value=True,
                ),
            }
        case "Motion & position":
            _exercise = (
                "Move the IMU away from the origin and increase the turn rate. Predict when "
                "the two points see the same acceleration. Then inject bias and turn aiding on."
            )
            _controls = {
                "offset": _slider(
                    0,
                    2,
                    value=0.75,
                    step=0.05,
                    label="Forward sensor offset (m)",
                    show_value=True,
                ),
                "rate": _slider(
                    -120,
                    120,
                    value=45,
                    step=5,
                    label="Initial yaw rate (°/s)",
                    show_value=True,
                ),
                "alpha": _slider(
                    -12,
                    12,
                    value=4,
                    label="Angular acceleration (°/s²)",
                    show_value=True,
                ),
                "bias": _slider(
                    -0.4,
                    0.4,
                    value=0.12,
                    step=0.02,
                    label="Sensor x bias (m/s²)",
                    show_value=True,
                ),
                "aid": mo.ui.dropdown(
                    {"Off": 0, "Every 2 s": 2, "Every 5 s": 5, "Every 10 s": 10},
                    value="Every 5 s",
                    label="Ideal position and velocity aid",
                ),
                "time": _slider(
                    0,
                    20,
                    value=7,
                    step=0.1,
                    label="Inspect at time (s)",
                    show_value=True,
                ),
            }
        case "3D pose reconstruction":
            _exercise = (
                "Position the sensor at any offset in three dimensions. Predict which sensor "
                "readings change while the reference-point state stays the same."
            )
            _controls = {
                "x": _slider(
                    -1,
                    1,
                    value=0.6,
                    step=0.05,
                    label="Body x offset (m)",
                    show_value=True,
                ),
                "y": _slider(
                    -1,
                    1,
                    value=-0.3,
                    step=0.05,
                    label="Body y offset (m)",
                    show_value=True,
                ),
                "z": _slider(
                    -1,
                    1,
                    value=0.5,
                    step=0.05,
                    label="Body z offset (m)",
                    show_value=True,
                ),
                "yaw": _slider(-180, 180, value=45, step=5, label="Body yaw (°)", show_value=True),
                "mount": _slider(
                    -180,
                    180,
                    value=30,
                    step=5,
                    label="Sensor mount yaw (°)",
                    show_value=True,
                ),
                "spin": _slider(
                    -2,
                    2,
                    value=1,
                    step=0.1,
                    label="Angular-rate multiplier",
                    show_value=True,
                ),
            }
        case "Fusion":
            _exercise = (
                "Turn up gyro bias, then add a sideways acceleration pulse. Which error grows "
                "gradually? Which appears suddenly? Try the norm gate and see whether it helps."
            )
            _controls = {
                "bias": _slider(
                    -5, 5, value=1.4, step=0.1, label="Gyro bias (°/s)", show_value=True
                ),
                "pulse": _slider(
                    0,
                    1.5,
                    value=0.7,
                    step=0.05,
                    label="Body x acceleration pulse (g)",
                    show_value=True,
                ),
                "gain": _slider(
                    0,
                    0.15,
                    value=0.04,
                    step=0.005,
                    label="Accelerometer correction per sample",
                    show_value=True,
                ),
                "reject": mo.ui.checkbox(label="Gate updates when measured norm differs from 1 g"),
            }
        case "Control & applications":
            _exercise = (
                "Increase proportional gain with derivative gain at zero. Watch for overshoot "
                "and torque clipping. Add damping and compare response under the same disturbance."
            )
            _controls = {
                "kp": _slider(
                    0,
                    12,
                    value=3,
                    step=0.25,
                    label="Proportional gain (N·m/rad)",
                    show_value=True,
                ),
                "kd": _slider(
                    0,
                    8,
                    value=2,
                    step=0.25,
                    label="Derivative gain (N·m·s/rad)",
                    show_value=True,
                ),
                "disturbance": _slider(
                    0,
                    5,
                    value=0.6,
                    step=0.1,
                    label="Disturbance torque (N·m)",
                    show_value=True,
                ),
            }
    controls = mo.ui.dictionary(_controls)
    mo.vstack(
        [
            mo.md(f"**Predict first.** {_exercise}"),
            mo.hstack(
                [controls[key] for key in controls.elements],
                justify="start",
                align="center",
                wrap=True,
                gap=0.8,
            ),
        ],
        gap=0.25,
    )
    return (controls,)


@app.cell(hide_code=True)
def _(
    Iterable,
    active_context,
    b64encode,
    chapter,
    controls,
    cutaway,
    mo,
    nav,
    np,
    plots,
    sections,
    sensor,
):
    def _vector(value: Iterable[float]) -> str:
        return "(" + ", ".join(f"{axis:+.3f}" for axis in value) + ")"

    _v = controls.value
    _name = chapter.value
    _cutaway_image = None
    match _name:
        case "Sensors":
            _s = sensor.chip_sample(
                _v["tilt"],
                _v["linear"],
                _v["fall"],
                _v["range"],
                _v["drive"],
                _v["rate"],
            )
            _physics = (
                "Free fall cancels vertical gravity in a - g. Any imposed world x "
                "acceleration remains."
                if _v["fall"]
                else "The support prevents downward acceleration, so a - g has +1 g along "
                "world up. Tilt projects this vector onto the sensor axes."
            )
            _summary = (
                f"At tilt {_v['tilt']}°, world x acceleration {_v['linear']} g, "
                f"and {'free fall along z' if _v['fall'] else 'support along z'}, "
                f"ideal sensor specific force (x, y, z) is **{_vector(_s.specific_g)} g**. "
                f"After clipping to ±{_v['range']} g it reads **{_vector(_s.measured_g)} g**. "
                f"{_physics}\n\n"
                f"Proof mass x deflection **{_s.displacement_um:+.3f} µm** "
                "in this toy spring model. "
                f"At peak drive {_v['drive']} mm/s and rate {_v['rate']}°/s, "
                f"instantaneous Coriolis y acceleration is **{_s.coriolis_mm_s2:+.2f} mm/s²**. "
                f"Stage: {_v['stage']}."
            )
            _svg = cutaway(_s.displacement_um, _v["stage"])
            _file = "data:image/svg+xml;base64," + b64encode(_svg.encode()).decode("ascii")
            _cutaway_image = mo.image(
                _file,
                alt=f"Isometric MEMS cutaway, {_v['stage']} stage. "
                f"Proof mass displacement {_s.displacement_um:+.3f} μm.",
                width="100%",
            )
            _chart = plots.plot_chip(_s)
        case "Magnetometer":
            _ideal, _raw, _point, _raw_point = sensor.magnetic_sweep(
                _v["yaw"], _v["bias"], _v["scale"], _v["declination"]
            )
            _mag = sensor.compass_heading_deg(_point)
            _raw_heading = sensor.compass_heading_deg(_raw_point)
            _true = (_mag + _v["declination"]) % 360
            _summary = (
                f"Yaw {_v['yaw']}° from East, hard iron x {_v['bias']} µT, "
                f"soft iron scale {_v['scale']:.2f}, declination {_v['declination']}°. "
                f"Raw horizontal field {_vector(_raw_point)} µT gives **{_raw_heading:.1f}°**. "
                f"Calibrated magnetic heading **{_mag:.1f}°**, true heading **{_true:.1f}°**."
            )
            _chart = plots.plot_magnetic(_ideal, _raw, _point, _raw_point)
        case "Attitude":
            _body = sensor.rotation(_v["roll"], _v["pitch"], _v["yaw"])
            _mount = sensor.rotation(0, 0, _v["mount"])
            _mounted = _body @ _mount
            _f_g = _mounted.T @ [0, 0, 1]
            _field = _mounted.T @ sensor.magnetic_field(10, 45, 48)
            _summary = (
                f"Roll {_v['roll']}°, pitch {_v['pitch']}°, yaw {_v['yaw']}°, "
                f"mount {_v['mount']}°. "
                f"Body forward in world ENU **{_vector(_body[:, 0])}**. "
                f"Sensor forward **{_vector(_mounted[:, 0])}**.\n\n"
                f"At rest, sensor specific force **{_vector(_f_g)} g**. "
                f"Sensor magnetic field **{_vector(_field)} µT**. "
                "Dotted W is world, solid B is body, dashed S is mounted sensor."
            )
            _chart = plots.plot_attitude(_body, _mounted)
        case "Motion & position":
            _case = nav.motion_case(_v["offset"], _v["rate"], _v["alpha"], _v["bias"], _v["aid"])
            _i = int(np.argmin(abs(_case.t - _v["time"])))
            _error = np.linalg.norm(_case.corrected_pos[_i] - _case.truth_pos[_i])
            _summary = (
                f"Offset {_v['offset']:.2f} m, initial rate {_v['rate']}°/s, "
                f"angular acceleration {_v['alpha']}°/s², x bias {_v['bias']:+.2f} m/s², "
                f"aid interval {_v['aid']} s (0 means off). At **{_case.t[_i]:.1f} s**: "
                f"yaw **{_case.theta_deg[_i]:.1f}°**, "
                f"centripetal x **{_case.radial_m_s2[_i]:+.3f} m/s²**, "
                f"tangential y **{_case.tangential_m_s2[_i]:+.3f} m/s²**.\n\n"
                f"Reference truth position {_vector(_case.truth_pos[_i])} m, "
                f"velocity {_vector(_case.truth_vel[_i])} m/s in world East/North. "
                f"Sensor position {_vector(_case.sensor_pos[_i])} m, "
                f"raw sensor horizontal reading {_vector(_case.body_force[_i])} m/s². "
                f"After offset correction, position error **{_error:.3f} m**."
            )
            _chart = plots.plot_motion(_case, _i)
        case "3D pose reconstruction":
            _r = np.array([_v["x"], _v["y"], _v["z"]])
            _ref, _p_s, _v_s, _f_s = sensor.pose_trial(_r, _v["yaw"], _v["mount"], _v["spin"])
            _summary = (
                f"Body offset {_vector(_r)} m, body yaw {_v['yaw']}°, "
                f"mount yaw {_v['mount']}°, rate multiplier {_v['spin']}. "
                f"Sensor position {_vector(_p_s)} m, velocity {_vector(_v_s)} m/s in world ENU. "
                f"Sensor specific force {_vector(_f_s)} m/s² in sensor axes.\n\n"
                f"Recovered reference position **{_vector(_ref.position_m)} m**, "
                f"velocity **{_vector(_ref.velocity_m_s)} m/s**, "
                f"acceleration **{_vector(_ref.acceleration_m_s2)} m/s²**. "
                f"Body-forward direction in world **{_vector(_ref.body_to_world[:, 0])}**."
            )
            _chart = plots.plot_pose(_ref.body_to_world, _ref.offset_world_m)
        case "Fusion":
            _case = nav.fusion_case(_v["bias"], _v["pulse"], _v["gain"], _v["reject"])
            _peak = np.max(abs(_case.fused_deg - _case.truth_deg))
            _gyro_drift = _case.gyro_only_deg[-1] - _case.truth_deg[-1]
            _summary = (
                f"Gyro bias {_v['bias']:+.1f}°/s, acceleration pulse {_v['pulse']} g, "
                f"correction gain {_v['gain']:.3f}, norm gate {'on' if _v['reject'] else 'off'}. "
                f"Gyro-only final error **{_gyro_drift:+.2f}°**. "
                f"Fused peak error **{_peak:.2f}°**. "
                f"**{np.count_nonzero(_case.rejected)}** accelerometer updates gated."
            )
            _chart = plots.plot_fusion(_case)
        case "Control & applications":
            _case = nav.control_case(_v["kp"], _v["kd"], _v["disturbance"])
            _error = _case.target_deg[-1] - _case.closed_deg[-1]
            _summary = (
                f"Kp {_v['kp']:.2f} N·m/rad, Kd {_v['kd']:.2f} N·m·s/rad, "
                f"disturbance {_v['disturbance']:.1f} N·m. "
                f"Final target **{_case.target_deg[-1]:.1f}°**, "
                f"open loop **{_case.open_deg[-1]:.1f}°**, "
                f"feedback **{_case.closed_deg[-1]:.1f}°**. "
                f"Final feedback error **{_error:+.2f}°**, "
                f"peak command **{np.max(abs(_case.torque)):.2f} N·m**."
            )
            _chart = plots.plot_control(_case)
    _image = mo.image(
        plots.png(_chart),
        alt=f"{_name} experiment plot. {_summary.replace('**', '')}",
        width="100%",
    )
    _visuals = [_cutaway_image, _image] if _cutaway_image is not None else [_image]

    active_context.chapter = _name
    snapshot = _summary.replace("**", "")
    active_context.values = snapshot
    active_context.reference = sections[_name]
    mo.vstack(
        [
            mo.md(_summary),
            *_visuals,
            mo.accordion({"Theory, engineering practice and sources": mo.md(sections[_name])}),
        ]
    )
    return (snapshot,)


@app.cell(hide_code=True)
def _(active_context, asyncio, mo, tutor):
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
                    tutor.tutor_messages(active_context, messages),
                )
            except tutor.TutorUnavailable as error:
                return f"Tutor unavailable. {error} The experiments are still available."

        chat = mo.ui.chat(
            _answer,
            prompts=[
                "Explain my current readings.",
                "What would I test on a real board?",
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
    mo.sidebar(_panel, width="23rem")
    return (chat,)


@app.cell(hide_code=True)
def _(chat, mo):
    notes = mo.ui.text_area(label="Keep a takeaway", rows=3, full_width=True)
    include_chat = mo.ui.checkbox(label="Include tutor conversation")
    _options = [include_chat] if chat is not None else []
    mo.vstack([mo.md("## Your notes"), notes, *_options])
    return include_chat, notes


@app.cell(hide_code=True)
def _(chapter, chat, include_chat, mo, notes, snapshot, tutor):
    _text = notes.value.strip()
    _turns = chat.value if chat is not None and include_chat.value else []
    mo.download(
        data=tutor.notes_markdown(chapter.value, snapshot, _text, _turns),
        filename="imu-takeaways.md",
        mimetype="text/markdown",
        label="Download Markdown notes",
        disabled=not (_text or _turns),
    )
    return


if __name__ == "__main__":
    app.run()
