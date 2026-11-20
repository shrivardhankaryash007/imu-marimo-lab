# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo==0.25.2", "numpy==2.4.6", "plotly==6.5.2"]
# ///

"""A predict-then-reveal introduction to inertial measurement units."""

# Long lesson copy and Greek symbols are kept intact for the rendered equations.
# B018: a bare name on a cell's last line is how marimo displays that cell.
# ruff: noqa: E501, RUF001, B018

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="IMU foundations: from one chip to a fused attitude")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import plotly.graph_objects as go

    import imu_basics
    import imu_sensor

    def layout_chart(fig, y_title):
        fig.update_layout(
            template="plotly_white",
            height=340,
            margin={"t": 55, "b": 45},
            legend={"orientation": "h", "y": 1.15},
            yaxis_title=y_title,
        )
        return fig

    def lesson_view(
        number,
        title,
        intuition,
        equation,
        definitions,
        try_content,
        question,
        form,
        truth,
        why,
        hardware,
        rel_tol=0.0,
        abs_tol=0.0,
        extras=None,
    ):
        if form.value is None:
            reveal = mo.md("Submit a prediction to see the answer.")
        else:
            raw_guess = form.value
            guess = float(raw_guess.get("value", 0.0) if isinstance(raw_guess, dict) else raw_guess)
            verdict = imu_basics.grade_numeric(
                guess, float(truth), rel_tol=rel_tol, abs_tol=abs_tol
            )
            reveal = mo.vstack(
                [
                    mo.callout(verdict.message, kind="success" if verdict.correct else "warn"),
                    mo.md(why),
                ]
            )
        pieces = [
            mo.md(f"## {number} · {title}"),
            mo.md(intuition),
            mo.md("**The equation**\n\n" + equation + "\n\n" + definitions),
            mo.md("**Try it**"),
            try_content,
            mo.md("**Predict**\n\n" + question),
            form,
            mo.md("**Reveal**"),
            reveal,
            mo.md("**On real hardware**\n\n" + hardware),
        ]
        if extras is not None:
            pieces.insert(-1, extras)
        return mo.vstack(pieces)

    return layout_chart, lesson_view, go, imu_basics, imu_sensor, mo, np


@app.cell
def _(mo):
    intro = mo.md("""
    # IMU foundations: from one chip to a fused attitude

    Predict a number, submit it, then compare it with a live model. An IMU joins
    motion sensors; this course builds from their readings to attitude estimates.
    """)
    return (intro,)


@app.cell
def _(intro, mo):
    lesson_00 = mo.vstack(
        [
            mo.md("## 0 · Start here"),
            intro,
            mo.md("Use this map to see where each idea fits."),
            mo.md("**The equation**\n\nNo equation yet.\n\nNo symbols are needed for the map."),
            mo.md("**Try it**"),
            mo.ui.table(
                {
                    "NN": [
                        "01",
                        "02",
                        "03",
                        "04",
                        "05",
                        "06",
                        "07",
                        "08",
                        "09",
                        "10",
                        "11",
                        "12",
                        "13",
                        "14",
                    ],
                    "Title": [
                        "What an IMU measures",
                        "Counts, resolution and clipping",
                        "Axes and signs",
                        "Tilt from gravity, and what breaks it",
                        "Gyro drift",
                        "Reading gyro noise",
                        "Sampling and aliasing",
                        "Calibration",
                        "Heading",
                        "Complementary filter",
                        "Gimbal lock and quaternions",
                        "Why position drifts",
                        "Your own data",
                        "Where next",
                    ],
                    "You will learn": [
                        "Read specific force",
                        "Connect volts to counts",
                        "Track signs and axes",
                        "See acceleration fool tilt",
                        "Watch bias build",
                        "Measure noise over time",
                        "See sampling hide motion",
                        "Remove sensor errors",
                        "Use a compass when tilted",
                        "Blend gyro and gravity",
                        "Understand an angle singularity",
                        "See why position wanders",
                        "Inspect a log",
                        "Choose a next experiment",
                    ],
                }
            ),
            mo.md(
                "**On real hardware**\n\nKeep the board still for the first readings, then move one axis at a time."
            ),
        ]
    )
    lesson_00
    return (lesson_00,)


@app.cell
def _(mo):
    w01_roll = mo.ui.slider(-180, 180, value=30, label="Roll (°)")
    w01_pitch = mo.ui.slider(-89, 89, value=0, label="Pitch (°)")
    mo.vstack([w01_roll, w01_pitch])
    q01 = mo.ui.form(mo.ui.number(label="Prediction (g)"), submit_button_label="Reveal")
    return w01_pitch, w01_roll, q01


@app.cell
def _(w01_pitch, w01_roll, layout_chart, lesson_view, go, imu_basics, mo, np, q01):
    f01 = imu_basics.gravity_reading_g(w01_roll.value, w01_pitch.value)
    fig01 = layout_chart(
        go.Figure([go.Bar(x=["x", "y", "z"], y=f01, name="specific force")]), "Specific force (g)"
    )
    answer01 = float(f01[2])
    chart01 = mo.vstack(
        [mo.ui.plotly(fig01), mo.md("In free fall the ideal reading is 0 g on every axis.")]
    )
    lesson_01 = lesson_view(
        1,
        "What an IMU measures",
        "At rest, support pushes up on the sensor. The accelerometer reports this specific force, not motion through space. In free fall, support disappears and the ideal reading is zero.",
        r"$f_b = R^T g$",
        "Here $f_b$ is body-frame specific force in g, $R$ is the body-to-world rotation, and $g$ is the upward support reading at rest in g.",
        mo.vstack([w01_roll, w01_pitch, chart01]),
        f"Board rolled {w01_roll.value}°, at rest. What does the z accelerometer read, in g?",
        q01,
        float(f01[2]),
        "The z bar is the vertical component of the gravity-supported specific force.",
        "A board at rest reports the force that holds it up. A drop test briefly removes that support.",
        abs_tol=0.03,
    )
    lesson_01
    return lesson_01, q01, answer01


@app.cell
def _(mo):
    w02_fs = mo.ui.dropdown(
        {"±2 g": 2.0, "±4 g": 4.0, "±8 g": 8.0, "±16 g": 16.0}, value="±4 g", label="Full scale"
    )
    w02_value = mo.ui.slider(-20, 20, value=1.0, label="True value (g)")
    mo.vstack([w02_fs, w02_value])
    q02 = mo.ui.form(mo.ui.number(label="Prediction (mg)"), submit_button_label="Reveal")
    return w02_fs, w02_value, q02


@app.cell
def _(w02_fs, w02_value, layout_chart, lesson_view, go, imu_basics, mo, np, q02):
    d02 = imu_basics.digitize(w02_value.value, w02_fs.value)
    lsb02 = imu_basics.lsb_size(w02_fs.value)
    ramp02 = np.linspace(-20, 20, 401)
    digitized02 = imu_basics.digitize(ramp02, w02_fs.value)
    fig02 = layout_chart(
        go.Figure(
            [
                go.Scatter(x=ramp02, y=ramp02, name="true"),
                go.Scatter(x=ramp02, y=digitized02.units, name="digitised", mode="lines"),
            ]
        ),
        "Value (g)",
    )
    panel02 = mo.vstack(
        [
            mo.md(
                f"LSB: {lsb02 * 1000:.3f} mg · counts: {int(d02.counts)} · back-converted: {float(d02.units):.4f} g · clipped: {bool(d02.clipped)}"
            ),
            mo.ui.plotly(fig02),
        ]
    )
    answer02 = float(lsb02 * 1000)
    lesson_02 = lesson_view(
        2,
        "Counts, resolution and clipping",
        "The chip stores whole-number counts. One count is one small step in acceleration. Values beyond the chosen range clip at the largest code.",
        r"$\mathrm{LSB} = F / 2^{B-1}$",
        "$F$ is the positive full-scale range in g; $B$ is the number of bits; LSB is one count in g.",
        mo.vstack([w02_fs, w02_value, panel02]),
        f"At ±{w02_fs.value:g} g with 16 bits, how big is one count, in mg?",
        q02,
        float(lsb02 * 1000),
        "The step is the selected positive range divided by the signed count range.",
        "Change the range on a board and watch both the smallest step and the clipping point move.",
        rel_tol=0.05,
    )
    lesson_02
    return lesson_02, q02, answer02


@app.cell
def _(mo):
    w03_pitch = mo.ui.slider(-89, 89, value=30, label="Pitch (°)")
    w03_roll = mo.ui.slider(-180, 180, value=0, label="Roll (°)")
    mo.vstack([w03_pitch, w03_roll])
    q03 = mo.ui.form(mo.ui.number(label="Prediction (g)"), submit_button_label="Reveal")
    return w03_pitch, w03_roll, q03


@app.cell
def _(w03_pitch, w03_roll, layout_chart, lesson_view, go, imu_basics, mo, q03):
    f03 = imu_basics.gravity_reading_g(w03_roll.value, w03_pitch.value)
    fig03 = layout_chart(
        go.Figure([go.Bar(x=["x forward", "y left", "z up"], y=f03)]), "Specific force (g)"
    )
    answer03 = float(f03[0])
    lesson_03 = lesson_view(
        3,
        "Axes and signs",
        "The board axes point forward, left, and up. Nose-up pitch is positive. Gravity's support force moves between these axes as the board tilts.",
        r"$f_b = R^T g$",
        "$f_b$ is specific force on the three body axes in g; $R$ rotates body axes into world axes; $g$ is the at-rest upward reading in g.",
        mo.vstack(
            [
                w03_pitch,
                w03_roll,
                mo.ui.plotly(fig03),
                mo.md("Axis convention: x forward, y left, z up; nose-up pitch is positive."),
            ]
        ),
        f"Nose up {w03_pitch.value}°, at rest. What does the x accelerometer read, in g? (mind the sign)",
        q03,
        float(f03[0]),
        "The x reading is the projection of the upward support force onto the forward axis.",
        "Rotate the physical board nose-up and compare the x sign with this convention.",
        abs_tol=0.03,
    )
    lesson_03
    return lesson_03, q03, answer03


@app.cell
def _(mo):
    w04_roll = mo.ui.slider(-180, 180, value=0, label="Roll (°)")
    w04_pitch = mo.ui.slider(-89, 89, value=0, label="Pitch (°)")
    w04_yaw = mo.ui.slider(-180, 180, value=0, label="Yaw (°)")
    w04_accel = mo.ui.slider(0, 0.5, step=0.01, value=0.2, label="Forward acceleration (g)")
    mo.vstack([w04_roll, w04_pitch, w04_yaw, w04_accel])
    q04 = mo.ui.form(mo.ui.number(label="Prediction (°)"), submit_button_label="Reveal")
    return w04_accel, w04_pitch, w04_roll, w04_yaw, q04


@app.cell
def _(
    w04_roll, w04_pitch, w04_yaw, w04_accel, lesson_view, imu_basics, mo, np, go, layout_chart, q04
):
    g04 = imu_basics.gravity_reading_g(w04_roll.value, w04_pitch.value, w04_yaw.value)
    measured04 = g04 + np.array([w04_accel.value, 0.0, 0.0])
    estimated04 = imu_basics.accel_tilt_deg(measured04)
    true04 = (w04_roll.value, w04_pitch.value)
    fig04 = layout_chart(
        go.Figure(
            [
                go.Bar(
                    x=["true roll", "estimated roll", "true pitch", "estimated pitch"],
                    y=[true04[0], estimated04[0], true04[1], estimated04[1]],
                )
            ]
        ),
        "Angle (°)",
    )
    truth04 = float(estimated04[1])
    lesson_04 = lesson_view(
        4,
        "Tilt from gravity, and what breaks it",
        "Gravity can show tilt when the board is still. Forward acceleration adds another force to the same reading. The accelerometer cannot tell which part came from tilt.",
        r"$\hat\theta = \operatorname{accel\_tilt}(f_b)$",
        "$\\hat\\theta$ is estimated pitch in degrees; $f_b$ is measured specific force in g.",
        mo.vstack(
            [
                w04_roll,
                w04_pitch,
                w04_yaw,
                w04_accel,
                mo.ui.plotly(fig04),
                mo.md("Changing yaw does not change this gravity-only tilt estimate."),
            ]
        ),
        f"Level, but accelerating forward at {w04_accel.value} g. What pitch does the accelerometer report, in degrees?",
        q04,
        truth04,
        "Forward force tilts the apparent direction of the measured specific force.",
        "A car accelerometer mixes gravity with acceleration during a launch or brake.",
        abs_tol=1.0,
    )
    lesson_04
    return lesson_04, q04, truth04


@app.cell
def _(mo):
    w05_bias = mo.ui.slider(0, 2, step=0.01, value=0.5, label="Bias (°/s)")
    w05_noise = mo.ui.slider(0, 0.1, step=0.001, value=0.02, label="Noise density (°/s/√Hz)")
    w05_time = mo.ui.slider(10, 300, value=60, label="Duration (s)")
    mo.vstack([w05_bias, w05_noise, w05_time])
    q05 = mo.ui.form(mo.ui.number(label="Prediction (°)"), submit_button_label="Reveal")
    return w05_bias, w05_noise, w05_time, q05


@app.cell
def _(w05_bias, w05_noise, w05_time, layout_chart, lesson_view, go, imu_basics, mo, np, q05):
    t05 = np.linspace(0.0, w05_time.value, 301)
    runs05 = imu_basics.gyro_drift_runs(w05_time.value, 20.0, w05_bias.value, w05_noise.value, 20)
    mean05, sigma05 = imu_basics.gyro_drift_bounds(t05, w05_bias.value, w05_noise.value)
    fig05 = go.Figure()
    for row05 in runs05[1]:
        fig05.add_trace(
            go.Scatter(x=runs05[0], y=row05, mode="lines", opacity=0.25, showlegend=False)
        )
    fig05.add_trace(go.Scatter(x=t05, y=mean05, name="mean"))
    fig05.add_trace(go.Scatter(x=t05, y=mean05 + sigma05, name="+1σ", line={"dash": "dash"}))
    fig05.add_trace(go.Scatter(x=t05, y=mean05 - sigma05, name="−1σ", line={"dash": "dash"}))
    fig05 = layout_chart(fig05, "Heading error (°)")
    answer05 = float(mean05[-1])
    lesson_05 = lesson_view(
        5,
        "Gyro drift: bias × time, noise × √time",
        "A gyro reports turning speed. A small steady offset adds up in proportion to time. Random noise grows more slowly, like the square root of time.",
        r"$\mu(t)=bt,\quad \sigma(t)=N\sqrt{t}$",
        r"$b$ is bias in °/s, $N$ is noise density in °/s/√Hz, $t$ is seconds; $\mu$ and $\sigma$ are degrees.",
        mo.vstack([w05_bias, w05_noise, w05_time, mo.ui.plotly(fig05)]),
        f"Bias {w05_bias.value} °/s, held still for {w05_time.value} s. Mean heading error at the end, in degrees?",
        q05,
        float(mean05[-1]),
        "The mean drift is the steady bias multiplied by elapsed time.",
        "A still board log reveals a fixed gyro offset that can be estimated before motion.",
        rel_tol=0.1,
    )
    lesson_05
    return lesson_05, q05, answer05


@app.cell
def _(mo):
    w06_noise = mo.ui.slider(0.002, 0.05, step=0.001, value=0.01, label="Noise density (°/s/√Hz)")
    w06_walk = mo.ui.slider(0, 0.005, step=0.0001, value=0.0, label="Rate random walk")
    mo.vstack([w06_noise, w06_walk])
    q06 = mo.ui.form(mo.ui.number(label="Prediction (°/s)"), submit_button_label="Reveal")
    return w06_noise, w06_walk, q06


@app.cell
def _(w06_noise, w06_walk, layout_chart, lesson_view, go, imu_basics, mo, np, q06):
    rate06 = imu_basics.simulate_rest_gyro(300.0, 100.0, 0.0, w06_noise.value, w06_walk.value)
    taus06, adev06 = imu_basics.allan_deviation(rate06, 0.01)
    truth06 = float(adev06[int(np.argmin(np.abs(taus06 - 1.0)))])
    fig06 = layout_chart(
        go.Figure(
            [
                go.Scatter(x=taus06, y=adev06, name="ADEV"),
                go.Scatter(x=taus06, y=w06_noise.value / np.sqrt(taus06), name="N/√τ"),
            ]
        ),
        "Allan deviation (°/s)",
    )
    fig06.update_xaxes(type="log", title="Averaging time τ (s)")
    fig06.update_yaxes(type="log")
    lesson_06 = lesson_view(
        6,
        "Reading gyro noise: Allan deviation",
        "A gyro's noise changes with the time window used to average it. Allan deviation shows that change on a log scale. White rate noise falls as the averaging time grows.",
        r"$\sigma_A(\tau) \approx N/\sqrt{\tau}$",
        "$\\sigma_A$ is Allan deviation in °/s; $N$ is noise density in °/s/√Hz; $\\tau$ is seconds.",
        mo.vstack([w06_noise, w06_walk, mo.ui.plotly(fig06)]),
        f"Noise density {w06_noise.value} °/s/√Hz. What is the Allan deviation at τ = 1 s, in °/s?",
        q06,
        truth06,
        "The value is taken from the simulated Allan deviation at the sampled time nearest one second.",
        "A long still recording lets you see which noise behavior dominates at each averaging time.",
        rel_tol=0.15,
    )
    lesson_06
    return lesson_06, q06, truth06


@app.cell
def _(mo):
    w07_freq = mo.ui.slider(1, 400, value=180, label="Tone (Hz)")
    w07_odr = mo.ui.slider(50, 1000, value=200, label="Output data rate (Hz)")
    w07_cut = mo.ui.slider(5, 200, value=20, label="DLPF cutoff (Hz)")
    w07_filter = mo.ui.checkbox(value=False, label="Filter on")
    mo.vstack([w07_freq, w07_odr, w07_cut, w07_filter])
    q07 = mo.ui.form(mo.ui.number(label="Prediction (Hz)"), submit_button_label="Reveal")
    return w07_cut, w07_filter, w07_freq, w07_odr, q07


@app.cell
def _(
    w07_freq, w07_odr, w07_cut, w07_filter, layout_chart, lesson_view, go, imu_basics, mo, np, q07
):
    alias07 = imu_basics.alias_frequency_hz(w07_freq.value, w07_odr.value)
    filter_gain07 = imu_basics.first_order_gain(w07_freq.value, w07_cut.value)
    tone07 = imu_basics.sample_tone(
        w07_freq.value, 1.0, w07_odr.value, 0.2, w07_cut.value if w07_filter.value else None
    )
    mask07 = tone07[0] <= 0.2
    fig07 = layout_chart(
        go.Figure(
            [
                go.Scatter(x=tone07[0][mask07], y=tone07[1][mask07], name="true tone"),
                go.Scatter(x=tone07[2], y=tone07[3], name="samples", mode="markers+lines"),
            ]
        ),
        "Signal (g)",
    )
    panel07 = mo.vstack(
        [
            mo.md(f"Alias: {alias07:.2f} Hz · filter gain at tone: {filter_gain07:.3f}"),
            mo.ui.plotly(fig07),
        ]
    )
    answer07 = float(alias07)
    lesson_07 = lesson_view(
        7,
        "Sampling, aliasing and the low-pass filter",
        "A sensor samples motion at separate moments. A fast vibration can look slower after sampling. A low-pass filter reduces faster motion before it is reported.",
        r"$f_a = |f - k f_s|$",
        "$f_a$ is the apparent alias frequency in Hz; $f$ is the tone frequency; $f_s$ is the sample rate; $k$ is the nearest whole multiple chosen by the model.",
        mo.vstack([w07_freq, w07_odr, w07_cut, w07_filter, panel07]),
        f"A {w07_freq.value} Hz vibration sampled at {w07_odr.value} Hz shows up at what frequency, in Hz?",
        q07,
        float(alias07),
        "Sampling maps the tone to its nearest frequency inside the observable band.",
        "Vibration above a board's useful sample band can appear as a false slower motion.",
        abs_tol=0.5,
    )
    lesson_07
    return lesson_07, q07, answer07


@app.cell
def _(mo):
    w08_gyro = mo.ui.slider(-5, 5, step=0.1, value=0.5, label="Rest gyro x bias (°/s)")
    w08_plus = mo.ui.slider(0.9, 1.1, step=0.001, value=1.03, label="+1 g reading")
    w08_minus = mo.ui.slider(-1.1, -0.9, step=0.001, value=-0.97, label="−1 g reading")
    w08_hard = mo.ui.slider(-80, 80, value=12, label="Hard-iron x (µT)")
    w08_soft = mo.ui.slider(1.0, 1.6, step=0.01, value=1.3, label="Soft-iron scale")
    w08_tab = mo.ui.tabs(
        {
            "Gyro bias": w08_gyro,
            "Six-position accel": mo.vstack([w08_plus, w08_minus]),
            "Magnetometer": mo.vstack([w08_hard, w08_soft]),
        }
    )
    mo.vstack([w08_tab])
    q08 = mo.ui.form(mo.ui.number(label="Prediction (g)"), submit_button_label="Reveal")
    return w08_tab, w08_gyro, w08_plus, w08_minus, w08_hard, w08_soft, q08


@app.cell
def _(
    w08_tab,
    w08_gyro,
    w08_plus,
    w08_minus,
    w08_hard,
    w08_soft,
    layout_chart,
    lesson_view,
    go,
    imu_basics,
    imu_sensor,
    mo,
    np,
    q08,
):
    off08 = imu_basics.axis_scale_offset(w08_plus.value, w08_minus.value)[1]
    gyro_samples08 = np.column_stack(
        [imu_basics.simulate_rest_gyro(10.0, 100.0, w08_gyro.value, 0.0) for _ in range(3)]
    )
    gyro_bias08 = imu_basics.gyro_bias_from_rest(gyro_samples08)
    ideal08, raw08, _, _ = imu_sensor.magnetic_sweep(0.0, w08_hard.value, w08_soft.value, 0.0)
    fit08 = imu_basics.fit_ellipse_2d(raw08)
    corrected08 = imu_basics.apply_mag_fit(raw08, fit08)
    mag_heading08 = imu_sensor.compass_heading_deg(corrected08[0])
    residual08 = imu_basics.angle_diff_deg(
        mag_heading08, imu_sensor.compass_heading_deg(ideal08[0])
    )
    fig08 = layout_chart(
        go.Figure(
            [
                go.Scatter(x=raw08[:, 0], y=raw08[:, 1], name="raw"),
                go.Scatter(x=corrected08[:, 0], y=corrected08[:, 1], name="fitted"),
                go.Scatter(x=ideal08[:, 0], y=ideal08[:, 1], name="ideal"),
            ]
        ),
        "Magnetic y (µT)",
    )
    answer_offset08 = float(off08)
    answer_center08 = float(fit08.center[0])
    panel08 = mo.vstack(
        [
            mo.md(
                f"Rest gyro bias: {gyro_bias08} °/s · fit centre: ({fit08.center[0]:.2f}, {fit08.center[1]:.2f}) µT · residual rotation: {residual08:.2f}°"
            ),
            mo.ui.plotly(fig08),
        ]
    )
    lesson_08 = lesson_view(
        8,
        "Calibration: bias, scale, hard and soft iron",
        "A sensor can have a steady offset and a gain error. Turning it through known poses helps estimate both. Nearby magnetic material can shift and stretch the compass trace.",
        r"$o=(x_+ + x_-)/2$",
        "$o$ is the accelerometer offset in g; $x_+$ and $x_-$ are readings with the axis pointed up and down.",
        mo.vstack([w08_tab, panel08]),
        f"Six-position test reads {w08_plus.value} g up and {w08_minus.value} g down. What is the offset, in g?",
        q08,
        float(off08),
        "The offset is the midpoint between the up and down readings.",
        "Use a flat six-face calibration routine with the board secured in each pose.",
        abs_tol=0.005,
        extras=mo.md(f"The fitted hard-iron x centre is {fit08.center[0]:.2f} µT."),
    )
    lesson_08
    return lesson_08, answer_offset08, answer_center08


@app.cell
def _(mo):
    w09_roll = mo.ui.slider(-45, 45, value=0, label="Roll (°)")
    w09_pitch = mo.ui.slider(-45, 45, value=20, label="Pitch (°)")
    w09_yaw = mo.ui.slider(0, 359, value=100, label="Yaw (°)")
    w09_decl = mo.ui.slider(-20, 20, value=0, label="Declination (°)")
    mo.vstack([w09_roll, w09_pitch, w09_yaw, w09_decl])
    q09 = mo.ui.form(mo.ui.number(label="Prediction (°)"), submit_button_label="Reveal")
    return w09_decl, w09_pitch, w09_roll, w09_yaw, q09


@app.cell
def _(
    w09_roll,
    w09_pitch,
    w09_yaw,
    w09_decl,
    layout_chart,
    lesson_view,
    go,
    imu_basics,
    imu_sensor,
    mo,
    np,
    q09,
):
    field09 = imu_sensor.rotation(
        w09_roll.value, w09_pitch.value, w09_yaw.value
    ).T @ imu_sensor.magnetic_field(w09_decl.value, 60, 48)
    naive09 = imu_basics.naive_heading_deg(field09)
    comp09 = imu_basics.tilt_compensated_heading_deg(field09, w09_roll.value, w09_pitch.value)
    true09 = imu_basics.true_heading_deg(comp09, w09_decl.value)
    err09 = abs(imu_basics.angle_diff_deg(naive09, comp09))
    fig09 = layout_chart(
        go.Figure([go.Bar(x=["naive", "tilt-compensated", "true"], y=[naive09, comp09, true09])]),
        "Heading (°)",
    )
    answer09 = float(err09)
    lesson_09 = lesson_view(
        9,
        "Heading: tilt compensation and declination",
        "A compass reads the magnetic field around it. Tilting changes how that field falls across the sensor axes. Use roll and pitch to level the field before finding heading.",
        r"$\psi=\operatorname{heading}(R m)$",
        r"$\psi$ is heading in degrees; $R$ levels the measured body field $m$; declination converts magnetic north to true north.",
        mo.vstack([w09_roll, w09_pitch, w09_yaw, w09_decl, mo.ui.plotly(fig09)]),
        f"Pitched {w09_pitch.value}°: how far off is the naive (untilted) compass heading, in degrees?",
        q09,
        float(err09),
        "The naive compass ignores the vertical component created by tilt.",
        "A board compass needs a good tilt estimate and a site-specific declination value.",
        abs_tol=2.0,
    )
    lesson_09
    return lesson_09, q09, answer09


@app.cell
def _(mo):
    w10_alpha = mo.ui.slider(0.90, 0.999, step=0.001, value=0.98, label="α")
    w10_bias = mo.ui.slider(0, 2, step=0.1, value=1.0, label="Gyro bias (°/s)")
    w10_noise = mo.ui.slider(0, 2, step=0.1, value=0.5, label="Accel noise (°)")
    mo.vstack([w10_alpha, w10_bias, w10_noise])
    q10 = mo.ui.form(mo.ui.number(label="Prediction (°)"), submit_button_label="Reveal")
    return w10_alpha, w10_bias, w10_noise, q10


@app.cell
def _(w10_alpha, w10_bias, w10_noise, layout_chart, lesson_view, go, imu_basics, mo, np, q10):
    dt10 = 0.01
    t10 = np.arange(0.0, 20.0 + dt10, dt10)
    true10 = np.full(t10.shape, 20.0)
    gyro10 = np.full(t10.shape, w10_bias.value)
    accel10 = true10 + w10_noise.value * np.sin(t10)
    fused10 = imu_basics.complementary_1d(gyro10, true10, dt10, w10_alpha.value, float(true10[0]))
    gyro_only10 = true10[0] + w10_bias.value * t10
    tau10 = imu_basics.complementary_tau(w10_alpha.value, dt10)
    bias_error10 = float(fused10[-1] - true10[-1])
    fig10 = layout_chart(
        go.Figure(
            [
                go.Scatter(x=t10, y=true10, name="truth"),
                go.Scatter(x=t10, y=gyro_only10, name="gyro only"),
                go.Scatter(x=t10, y=accel10, name="accel only"),
                go.Scatter(x=t10, y=fused10, name="fused"),
            ]
        ),
        "Pitch (°)",
    )
    answer10 = bias_error10
    panel10 = mo.vstack(
        [
            mo.md(
                f"Time constant τ: {tau10:.2f} s · steady error for the noise-free model: {tau10 * w10_bias.value:.2f}°"
            ),
            mo.ui.plotly(fig10),
        ]
    )
    lesson_10 = lesson_view(
        10,
        "Complementary filter: trust the gyro short, gravity long",
        "A gyro follows quick turns but its bias builds over time. Gravity gives a slower tilt reference when motion is calm. A complementary filter blends both signals.",
        r"$\tau=\frac{\alpha\,dt}{1-\alpha},\quad e_\infty=\tau b$",
        "$\\alpha$ is the gyro weight per step; $dt$ is seconds; $\\tau$ is seconds; $b$ is gyro bias in °/s; $e_\\infty$ is steady angle error in degrees.",
        mo.vstack([w10_alpha, w10_bias, w10_noise, panel10]),
        f"α = {w10_alpha.value}, dt = 0.01 s, gyro bias {w10_bias.value} °/s. Steady-state angle error, in degrees?",
        q10,
        bias_error10,
        "The run uses a fixed true angle and bias-only gyro, so its final error approaches the filter's bias error.",
        "A real filter uses the accelerometer as the slow correction while the board is not accelerating strongly.",
        rel_tol=0.1,
    )
    lesson_10
    return lesson_10, q10, answer10, tau10


@app.cell
def _(mo):
    w11_pitch = mo.ui.slider(0, 90, value=80, label="Pitch (°)")
    mo.vstack([w11_pitch])
    q11 = mo.ui.form(mo.ui.number(label="Prediction (×)"), submit_button_label="Reveal")
    return w11_pitch, q11


@app.cell
def _(w11_pitch, layout_chart, lesson_view, go, imu_basics, mo, np, q11):
    pitches11 = np.arange(0.0, 90.0, 1.0)
    gains11 = np.array(
        [np.max(np.abs(imu_basics.euler_rate_matrix(0.0, float(p)))) for p in pitches11]
    )
    try:
        matrix11 = imu_basics.euler_rate_matrix(0.0, w11_pitch.value)
        gain11 = float(np.max(np.abs(matrix11)))
        status11 = mo.md(f"Euler-rate gain: {gain11:.3f}×")
        truth11 = gain11
    except ValueError as exc:
        status11 = mo.callout(str(exc), kind="danger")
        truth11 = float("nan")
    quat11 = imu_basics.quat_from_euler(0.0, min(w11_pitch.value, 89.0), 0.0)
    advanced11 = imu_basics.quat_integrate(quat11, np.array([0.0, 1.0, 0.0]), 0.01)
    rotation11 = imu_basics.quat_to_rotation(advanced11)
    fig11 = layout_chart(
        go.Figure([go.Scatter(x=pitches11, y=gains11, name="max Euler-rate gain")]), "Gain"
    )
    if np.isfinite(truth11):
        lesson_11 = lesson_view(
            11,
            "Gimbal lock and quaternions",
            "Euler angles describe rotation with three ordered turns. Near a straight-up pitch, a small body turn can demand a very large yaw-angle rate. Quaternions store rotation without that particular singularity.",
            r"$\dot{\eta}=T(\phi,\theta)\,\omega$",
            "$\\dot{\\eta}$ are Euler-angle rates in rad/s; $T$ maps body rate $\\omega$ in rad/s using roll $\\phi$ and pitch $\\theta$.",
            mo.vstack(
                [
                    w11_pitch,
                    status11,
                    mo.md(f"Quaternion-integrated rotation element: {rotation11[0, 0]:.3f}"),
                    mo.ui.plotly(fig11),
                ]
            ),
            f"At pitch {w11_pitch.value}°, how many times larger than the body rate can the yaw-rate term get?",
            q11,
            truth11,
            "The largest matrix entry gives the maximum Euler-rate gain for unit body rate.",
            "At near-vertical orientations, use an attitude representation that avoids Euler-rate singularities.",
            rel_tol=0.05,
        )
    else:
        lesson_11 = lesson_view(
            11,
            "Gimbal lock and quaternions",
            "Euler angles describe rotation with three ordered turns. Near a straight-up pitch, a small body turn can demand a very large yaw-angle rate. Quaternions store rotation without that particular singularity.",
            r"$\dot{\eta}=T(\phi,\theta)\,\omega$",
            "$\\dot{\\eta}$ are Euler-angle rates in rad/s; $T$ maps body rate $\\omega$ in rad/s using roll $\\phi$ and pitch $\\theta$.",
            mo.vstack([w11_pitch, status11, mo.ui.plotly(fig11)]),
            f"At pitch {w11_pitch.value}°, how many times larger than the body rate can the yaw-rate term get?",
            q11,
            truth11,
            "The matrix is singular at 90 degrees, so no finite gain exists there.",
            "At near-vertical orientations, use an attitude representation that avoids Euler-rate singularities.",
            rel_tol=0.05,
        )
    lesson_11
    return lesson_11, q11, truth11


@app.cell
def _(mo):
    w12_bias = mo.ui.slider(0, 0.5, step=0.01, value=0.1, label="Accel bias (m/s²)")
    w12_tilt = mo.ui.slider(0, 5, step=0.1, value=1, label="Tilt error (°)")
    w12_time = mo.ui.slider(1, 60, value=10, label="Time (s)")
    mo.vstack([w12_bias, w12_tilt, w12_time])
    q12 = mo.ui.form(mo.ui.number(label="Prediction (m)"), submit_button_label="Reveal")
    return w12_bias, w12_tilt, w12_time, q12


@app.cell
def _(w12_bias, w12_tilt, w12_time, layout_chart, lesson_view, go, imu_basics, mo, np, q12):
    t12 = np.linspace(0.0, w12_time.value, 121)
    tilt_accel12 = imu_basics.tilt_leak_m_s2(w12_tilt.value)
    bias_accel12 = np.full(t12.shape, w12_bias.value)
    tilt_accel_trace12 = np.full(t12.shape, tilt_accel12)
    _, bias_pos12 = imu_basics.double_integrate(bias_accel12, float(t12[1] - t12[0]))
    _, tilt_pos12 = imu_basics.double_integrate(tilt_accel_trace12, float(t12[1] - t12[0]))
    truth12 = float(imu_basics.position_error_m(tilt_accel12, w12_time.value))
    fig12 = layout_chart(
        go.Figure(
            [
                go.Scatter(x=t12, y=bias_pos12, name="bias"),
                go.Scatter(x=t12, y=tilt_pos12, name="tilt leak"),
            ]
        ),
        "Position error (m)",
    )
    answer12 = truth12
    lesson_12 = lesson_view(
        12,
        "Why IMUs cannot hold position alone",
        "A tiny acceleration error keeps pushing the velocity estimate. Position then drifts even faster. A small tilt error also leaks part of gravity into the horizontal direction.",
        r"$e_p=\frac{1}{2}at^2$",
        "$e_p$ is position error in metres; $a$ is a constant acceleration error in m/s²; $t$ is time in seconds.",
        mo.vstack([w12_bias, w12_tilt, w12_time, mo.ui.plotly(fig12)]),
        f"A {w12_tilt.value}° tilt error left uncorrected for {w12_time.value} s. Position error, in metres?",
        q12,
        truth12,
        "Tilt error leaks horizontal acceleration, which is integrated twice into position.",
        "In practice, use outside references such as GNSS, wheel motion, vision, or known stationary periods.",
        rel_tol=0.1,
    )
    lesson_12
    return lesson_12, q12, answer12


@app.cell
def _(mo):
    w13_file = mo.ui.file(filetypes=[".csv"], label="Upload IMU CSV")
    w13_unit = mo.ui.dropdown(
        {"deg/s": "deg/s", "rad/s": "rad/s"}, value="deg/s", label="Gyro unit"
    )
    w13_rest = mo.ui.slider(0.5, 10, value=4, label="Rest window (s)")
    mo.vstack([w13_file, w13_unit, w13_rest])
    q13 = mo.ui.form(mo.ui.number(label="Prediction (Hz)"), submit_button_label="Reveal")
    return w13_file, w13_rest, w13_unit, q13


@app.cell
def _(w13_file, w13_unit, w13_rest, layout_chart, lesson_view, go, imu_basics, mo, np, q13):
    try:
        if w13_file.value:
            data13 = w13_file.value[0].contents().decode("utf-8")
            log13 = imu_basics.load_imu_csv(data13, w13_unit.value)
            source13 = "Uploaded CSV"
            can_predict13 = False
        else:
            data13 = imu_basics.example_imu_csv()
            log13 = imu_basics.load_imu_csv(data13, w13_unit.value)
            source13 = "Using example_imu_csv() because no file was uploaded."
            can_predict13 = True
        summary13 = imu_basics.summarize_log(log13, w13_rest.value)
        tplot13 = log13.t[: min(500, log13.t.size)]
        fig13 = layout_chart(
            go.Figure(
                [
                    go.Scatter(x=tplot13, y=summary13.roll_deg[: tplot13.size], name="roll"),
                    go.Scatter(x=tplot13, y=summary13.pitch_deg[: tplot13.size], name="pitch"),
                ]
            ),
            "Angle (°)",
        )
        rate13 = float(summary13.rate_hz)
        result13 = mo.vstack(
            [
                mo.md(
                    f"{source13}\n\nRate: {summary13.rate_hz:.2f} Hz · timing jitter: {summary13.dt_jitter_ms:.3f} ms · gyro bias: {summary13.gyro_bias_deg_s} °/s · mean accel norm: {summary13.accel_norm_mean_g:.3f} g"
                ),
                mo.ui.plotly(fig13),
                mo.md(
                    "Accepted columns: t, time, time_s, timestamp, t_ms or time_ms; ax, ay, az, gx, gy, gz; optional mx, my, mz."
                ),
            ]
        )
    except imu_basics.ImuCsvError as exc:
        result13 = mo.callout(str(exc), kind="danger")
        rate13 = float("nan")
        can_predict13 = False
    if can_predict13:
        lesson_13 = lesson_view(
            13,
            "Your own data",
            "A log is a sequence of readings with timestamps. First check its sample rate, timing, bias, and gravity size. Then compare the estimated roll and pitch over time.",
            r"$f_s=1/\operatorname{median}(\Delta t)$",
            r"$f_s$ is sample rate in Hz; $\Delta t$ is the spacing between timestamps in seconds.",
            mo.vstack([w13_file, w13_unit, w13_rest, result13]),
            "The example log is sampled at what rate, in Hz?",
            q13,
            float(rate13),
            "The example timestamps are parsed by the same CSV reader used for uploaded data.",
            "Export a short still log first, then check column names and units before interpreting motion.",
            rel_tol=0.02,
        )
    else:
        lesson_13 = mo.vstack(
            [
                mo.md("## 13 · Your own data"),
                mo.md(
                    "A log is a sequence of readings with timestamps. First check its sample rate, timing, bias, and gravity size. Then compare the estimated roll and pitch over time."
                ),
                mo.md(
                    "**The equation**\n\n$f_s=1/\\operatorname{median}(\\Delta t)$\n\n$f_s$ is sample rate in Hz; $\\Delta t$ is seconds."
                ),
                mo.md("**Try it**"),
                mo.vstack([w13_file, w13_unit, w13_rest, result13]),
                mo.md("**Predict**\n\nThe example log is sampled at what rate, in Hz?"),
                q13,
                mo.md("**Reveal**"),
                mo.callout(
                    "Upload a CSV to inspect it; the example prediction applies only when no file is uploaded.",
                    kind="warn",
                ),
                mo.md(
                    "**On real hardware**\n\nExport a short still log first, then check column names and units before interpreting motion."
                ),
            ]
        )
    lesson_13
    return lesson_13, q13, rate13


@app.cell
def _(
    q01,
    q02,
    q03,
    q04,
    q05,
    q06,
    q07,
    q08,
    q09,
    q10,
    q11,
    q12,
    q13,
    w01_roll,
    w01_pitch,
    w02_fs,
    w03_roll,
    w03_pitch,
    w04_roll,
    w04_pitch,
    w04_yaw,
    w04_accel,
    w05_bias,
    w05_noise,
    w05_time,
    w06_noise,
    w06_walk,
    w07_freq,
    w07_odr,
    w08_plus,
    w08_minus,
    w08_hard,
    w08_soft,
    w09_roll,
    w09_pitch,
    w09_yaw,
    w09_decl,
    w10_alpha,
    w10_bias,
    w11_pitch,
    w12_tilt,
    w12_time,
    imu_sensor,
    mo,
    np,
    imu_basics,
):
    field09_answers = imu_sensor.rotation(
        w09_roll.value, w09_pitch.value, w09_yaw.value
    ).T @ imu_sensor.magnetic_field(w09_decl.value, 60, 48)
    magfit_answers = imu_basics.fit_ellipse_2d(
        imu_sensor.magnetic_sweep(0.0, w08_hard.value, w08_soft.value, 0.0)[1]
    )
    adev_taus_answers, adev_values_answers = imu_basics.allan_deviation(
        imu_basics.simulate_rest_gyro(300.0, 100.0, 0.0, w06_noise.value, w06_walk.value), 0.01
    )
    comp_tau_answers = imu_basics.complementary_tau(w10_alpha.value, 0.01)
    comp_times_answers = np.arange(0.0, 20.0 + 0.01, 0.01)
    comp_truth_answers = np.full(comp_times_answers.shape, 20.0)
    comp_rate_answers = np.full(comp_times_answers.shape, w10_bias.value)
    comp_trace_answers = imu_basics.complementary_1d(
        comp_rate_answers, comp_truth_answers, 0.01, w10_alpha.value, float(comp_truth_answers[0])
    )
    try:
        euler_gain_answers = float(
            np.max(np.abs(imu_basics.euler_rate_matrix(0.0, w11_pitch.value)))
        )
    except ValueError:
        euler_gain_answers = float("nan")
    example_rate_answers = imu_basics.summarize_log(
        imu_basics.load_imu_csv(imu_basics.example_imu_csv())
    ).rate_hz
    answers: dict[str, float] = {
        "lesson01_z_g": float(imu_basics.gravity_reading_g(w01_roll.value, w01_pitch.value)[2]),
        "lsb_mg": float(imu_basics.lsb_size(w02_fs.value) * 1000),
        "pitch_x_g": float(imu_basics.gravity_reading_g(w03_roll.value, w03_pitch.value)[0]),
        "accel_pitch_error_deg": float(
            imu_basics.accel_tilt_deg(
                imu_basics.gravity_reading_g(w04_roll.value, w04_pitch.value, w04_yaw.value)
                + np.array([w04_accel.value, 0.0, 0.0])
            )[1]
        ),
        "drift_deg": float(
            imu_basics.gyro_drift_bounds(
                np.array([0.0, w05_time.value]), w05_bias.value, w05_noise.value
            )[0][-1]
        ),
        "adev_at_1s": float(adev_values_answers[int(np.argmin(np.abs(adev_taus_answers - 1.0)))]),
        "alias_hz": float(imu_basics.alias_frequency_hz(w07_freq.value, w07_odr.value)),
        "accel_offset_g": float(imu_basics.axis_scale_offset(w08_plus.value, w08_minus.value)[1]),
        "mag_center_x_ut": float(magfit_answers.center[0]),
        "naive_heading_error_deg": float(
            abs(
                imu_basics.angle_diff_deg(
                    imu_basics.naive_heading_deg(field09_answers),
                    imu_basics.tilt_compensated_heading_deg(
                        field09_answers, w09_roll.value, w09_pitch.value
                    ),
                )
            )
        ),
        "comp_tau_s": float(comp_tau_answers),
        "comp_bias_error_deg": float(comp_trace_answers[-1] - comp_truth_answers[-1]),
        "euler_gain_at_pitch": float(euler_gain_answers),
        "tilt_position_error_m": float(
            imu_basics.position_error_m(imu_basics.tilt_leak_m_s2(w12_tilt.value), w12_time.value)
        ),
        "example_rate_hz": float(example_rate_answers),
    }
    forms = [q01, q02, q03, q04, q05, q06, q07, q08, q09, q10, q11, q12, q13]
    truths = [
        answers[key]
        for key in [
            "lesson01_z_g",
            "lsb_mg",
            "pitch_x_g",
            "accel_pitch_error_deg",
            "drift_deg",
            "adev_at_1s",
            "alias_hz",
            "accel_offset_g",
            "naive_heading_error_deg",
            "comp_bias_error_deg",
            "euler_gain_at_pitch",
            "tilt_position_error_m",
            "example_rate_hz",
        ]
    ]
    tolerances = [
        (0, 0.03),
        (0.05, 0),
        (0, 0.03),
        (0, 1.0),
        (0.1, 0),
        (0.15, 0),
        (0, 0.5),
        (0, 0.005),
        (0, 2.0),
        (0.1, 0),
        (0.05, 0),
        (0.1, 0),
        (0.02, 0),
    ]
    submitted = [form.value is not None for form in forms]
    predictions = [
        form.value.get("value") if isinstance(form.value, dict) else form.value for form in forms
    ]
    results = [
        "not submitted"
        if not done
        else (
            "correct"
            if imu_basics.grade_numeric(
                float(guess), float(truth), rel_tol=tol[0], abs_tol=tol[1]
            ).correct
            else "not correct"
        )
        for done, guess, truth, tol in zip(submitted, predictions, truths, tolerances, strict=True)
    ]
    scorecard = mo.ui.table(
        {
            "Lesson": [f"{n:02d}" for n in range(1, 14)],
            "Prediction": ["submitted" if done else "not submitted" for done in submitted],
            "Result": results,
        }
    )
    scorecard_note = mo.md(
        "Scores are computed from submitted form values and reset with this notebook session."
    )
    return answers, scorecard, scorecard_note


@app.cell
def _(answers, scorecard, scorecard_note, mo):
    lesson_14 = mo.vstack(
        [
            mo.md("## 14 · Where next, and your scorecard"),
            mo.md(
                "You now have a path from raw readings to a basic attitude estimate. Keep predictions small, then check them against measured data."
            ),
            mo.md("**The equation**\n\nNo new equation.\n\nNo symbols are needed for this review."),
            mo.md("**Try it**"),
            scorecard,
            scorecard_note,
            mo.md(
                "Suggested experiments: calibrate all six accelerometer faces; log the still gyro for one hour and inspect Allan deviation; rotate the board in a figure eight for a magnetometer sweep."
            ),
            mo.md(
                "**On real hardware**\n\n[imu.py](imu.py) · [attitude_lab.py](attitude_lab.py) · [course.md](course.md) · [equations.md](equations.md) · [hardware-sources.md](hardware-sources.md)"
            ),
            mo.md(
                f"Computed answers are available in the notebook variable `answers` ({len(answers)} truths)."
            ),
        ]
    )
    lesson_14
    return (lesson_14,)


if __name__ == "__main__":
    app.run()
