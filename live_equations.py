"""Render annotated substitutions from the exact selected simulation samples."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from attitude_sim import BODY_INERTIA, DT
from gyro_rls import RecursiveLeastSquares

if TYPE_CHECKING:
    from attitude_sim import ControlTrace, Replay, Settings
    from gyro_rls import CalibrationReplay


def _value(value: float) -> str:
    """Keep substitutions legible while retaining small values and their sign."""
    mantissa, separator, exponent = f"{value:.5g}".partition("e")
    return rf"{mantissa}\times 10^{{{int(exponent)}}}" if separator else mantissa


def _vector(entries: Sequence[float], *, row: bool = False) -> str:
    separator = " & " if row else r" \\ "
    return r"\begin{bmatrix}" + separator.join(_value(v) for v in entries) + r"\end{bmatrix}"


def _display(tex: str) -> str:
    return "\n\n$$\n" + tex + "\n$$\n\n"


def prediction(replay: Replay, index: int, axis: int) -> str:
    """Show the gyro increment entering the EKF at this sample."""
    if index == 0:
        return (
            "### Gyro prediction\n\nThis sample initializes attitude. "
            "Advance the sample slider to inspect the first gyro integration."
        )
    name = "xyz"[axis]
    gyro = replay.raw_gyro[index - 1, axis]
    bias = replay.ekf.bias[index - 1, axis]
    delta = (gyro - bias) * DT
    return (
        "### Gyro prediction\n\n"
        "Bias-corrected angular rate produces a small rotation over one sample interval. "
        "This increment feeds the attitude used to predict the reference directions."
        + _display(r"\hat R^-_{ws,k}=\hat R^+_{ws,k-1}\operatorname{Exp}(\Delta\theta_s)")
        + _display(
            rf"\begin{{aligned}}\Delta\theta_{{s,{name}}}&="
            rf"(y_{{g,{name}}}-\hat b_{{{name}}})\Delta t"
            rf"\\&\simeq ({_value(gyro)}-({_value(bias)}))({_value(DT)})"
            rf"={_value(delta)}\ \mathrm{{rad}}\end{{aligned}}"
        )
        + r"$y_g$ is the previous gyro reading in rad/s. $\hat b$ is the previous EKF "
        r"bias estimate in rad/s. $\Delta t$ is the time between replay samples in seconds. "
        r"$\operatorname{Exp}$ turns the three increments into a 3D rotation."
    )


def _skipped(replay: Replay, settings: Settings, index: int, observation: str, title: str) -> str:
    if observation == "magnetometer" and not settings.heading_aid:
        return f"### {title}\n\nHeading aid is off. No magnetometer update ran at this sample."
    if observation == "magnetometer":
        magnitude = f"{replay.mag_norm[index]:.3f} times the reference field"
    else:
        magnitude = f"{replay.accel_norm[index]:.3f} g"
    return (
        f"### {title}\n\nThe {observation} did not enter the direction update. "
        f"Its magnitude was **{magnitude}**. An invalid or gated measurement has no correction "
        "at this sample. Scrub to another sample or change the rejection setting."
    )


def complementary(
    replay: Replay, settings: Settings, index: int, axis: int, observation: str
) -> str:
    """Show the same direction residual and corrections applied by the filter."""
    pair = replay.updates[index].get(observation)
    if pair is None:
        return _skipped(replay, settings, index, observation, "Complementary correction")
    step = pair.complementary
    names = "xyz"
    name = names[axis]
    j, k = (axis + 1) % 3, (axis + 2) % 3
    z_j, z_k, h_j, h_k = map(
        _value, (step.observed[j], step.observed[k], step.predicted[j], step.predicted[k])
    )
    error = _value(step.error[axis])
    return (
        "### Complementary correction\n\n"
        f"The **{observation}** direction is compared with the complementary filter's prediction."
        + _display(
            rf"\begin{{aligned}}e_{{{name}}}&=z_{{{names[j]}}}h_{{{names[k]}}}"
            rf"-z_{{{names[k]}}}h_{{{names[j]}}}\\"
            rf"&\simeq ({z_j})({h_k})-({z_k})({h_j})={error}\end{{aligned}}"
        )
        + _display(
            rf"\begin{{aligned}}\Delta\theta_{{{name}}}&=k_p w\Delta t\,e_{{{name}}}\\"
            rf"&\simeq ({_value(settings.complementary_kp)})({_value(step.weight)})"
            rf"({_value(DT)})({error})={_value(step.rotation_delta[axis])}\ \mathrm{{rad}}"
            r"\end{aligned}"
        )
        + _display(
            rf"\Delta\hat b_{{{name}}}=-k_i w\Delta t\,e_{{{name}}}"
            rf"\simeq -({_value(settings.complementary_ki)})({_value(step.weight)})"
            rf"({_value(DT)})({error})={_value(step.bias_delta[axis])}\ \mathrm{{rad/s}}"
        )
        + r"$z$ is the measured unit direction. $h$ is the predicted unit direction. "
        r"Their cross product gives $e$. $w$ weights the reference; $k_p$ sets the "
        r"rotation correction and $k_i$ sets the bias correction. "
        r"[Change filter gains](#sensor-fusion-replay)."
    )


def kalman(replay: Replay, settings: Settings, index: int, axis: int, observation: str) -> str:
    """Show a prior, innovation, gate and gain from the actual EKF update."""
    pair = replay.updates[index].get(observation)
    if pair is None:
        return _skipped(replay, settings, index, observation, "Kalman correction")
    step = pair.kalman
    name = "xyz"[axis]
    noise_variance = step.sigma**2
    innovation = step.innovation[axis, axis]
    gate = "The NIS threshold is **9.21**." if settings.reject_disturbance else "NIS gating is off."
    text = (
        "### Kalman correction\n\n"
        f"The **{observation}** measurement reached the EKF. {gate}"
        + _display(
            rf"r_{{{name}}}=z_{{{name}}}-h_{{{name}}}"
            rf"\simeq {_value(step.observed[axis])}-({_value(step.predicted[axis])})"
            rf"={_value(step.residual[axis])}"
        )
        + _display(
            rf"S_{{{name}{name}}}=[HP^-H^T]_{{{name}{name}}}+\sigma^2"
            rf"\simeq {_value(innovation - noise_variance)}+{_value(noise_variance)}"
            rf"={_value(innovation)}"
        )
        + _display(rf"\operatorname{{NIS}}=r^TS^{{-1}}r\simeq {_value(step.nis)}")
        + rf"The selected prior attitude variance is $P^-_{{\theta_{name},\theta_{name}}}"
        rf"\simeq {_value(step.prior_covariance[axis, axis])}\,\mathrm{{rad}}^2$. "
        r"$r$ is the measured minus predicted direction. $P^-$ is the prior state "
        r"covariance, $H$ maps it into direction space and $\sigma^2$ adds sensor noise. "
        r"NIS measures the residual relative to its expected uncertainty. "
        r"[Change noise and rejection settings](#sensor-fusion-replay)."
    )
    if not step.accepted or step.gain is None or step.correction is None:
        return text + "\n\nThe NIS gate rejected this update. No rotation correction was applied."
    gain_row = _vector(step.gain[axis].tolist(), row=True)
    residual = _vector(step.residual.tolist())
    return (
        text
        + _display(
            rf"\begin{{aligned}}K&=P^-H^TS^{{-1}}\\"
            rf"\Delta\theta_{{{name}}}&=(Kr)_{{{name}}}\\"
            rf"&\simeq {gain_row}{residual}={_value(step.correction[axis])}\ \mathrm{{rad}}"
            r"\end{aligned}"
        )
        + "The first bracket is the selected row of the Kalman gain. The second is "
        "the residual vector. Their dot product is the applied local rotation increment."
    )


def rls_update(run: CalibrationReplay, forgetting: float, index: int) -> str:
    """Show an RLS prediction error and its exact two-parameter update."""
    before = run.estimates[index - 1] if index else RecursiveLeastSquares(forgetting).estimate
    prior = _vector(before.tolist())
    gain = _vector(run.gain[index].tolist())
    after = _vector(run.estimates[index].tolist())
    residual = _value(run.residual[index])
    return (
        "### Recursive least squares update\n\n"
        f"Forgetting factor **{forgetting:.3f}** sets how quickly the fit responds to new data."
        + _display(
            rf"\begin{{aligned}}\phi &= [\omega_{{\mathrm{{ref}}}},\ 1]^T"
            rf"\simeq [{_value(run.reference[index])},\ 1]^T\\"
            rf"r &= y-\phi^T\theta^- \simeq {_value(run.measurement[index])}"
            rf"-({_value(run.prediction[index])})={residual}\ \mathrm{{deg/s}}\end{{aligned}}"
        )
        + _display(rf"\theta^+=\theta^-+Kr\simeq {prior}+{gain}({residual})={after}")
        + r"$y$ is the raw gyro rate. $\phi^T\theta^-$ is the prediction from the "
        r"reference speed and previous parameters. $K$ is the two-entry gain. The "
        r"first row of $\theta$ is the dimensionless scale; the second is bias in deg/s. "
        r"These estimates can correct a gyro reading before it enters attitude prediction. "
        r"[Change the forgetting factor or reference motion](#rls-experiment)."
    )


def control(trace: ControlTrace, index: int, axis: int, kp: float, kd: float, limit: float) -> str:
    """Show the selected plant's applied torque and resulting angular acceleration."""
    name = "xyz"[axis]
    error, rate = trace.error_vector[index, axis], trace.estimated_rate[index, axis]
    requested = kp * error - kd * rate
    applied = trace.torque[index, axis]
    clipped = abs(requested) > limit
    return (
        "### Closed-loop control update\n\n"
        f"The selected body axis **{name.upper()}** is {'at' if clipped else 'within'} "
        f"the actuator limit. Requested and applied torque use N·m."
        + _display(
            rf"\begin{{aligned}}\tau^*_{{{name}}}&=K_p e_{{b,{name}}}-K_d\hat\omega_{{b,{name}}}"
            rf"\\&\simeq ({_value(kp)})({_value(error)})-({_value(kd)})({_value(rate)})"
            rf"={_value(requested)}\end{{aligned}}"
        )
        + _display(
            rf"\tau_{{{name}}}=\operatorname{{clip}}(\tau^*_{{{name}}},"
            rf"-{_value(limit)},+{_value(limit)})\simeq {_value(applied)}"
        )
        + _display(
            rf"\dot\omega_{{{name}}}"
            rf"\simeq \frac{{{_value(applied)}+({_value(trace.disturbance_torque[index, axis])})"
            rf"-({_value(trace.gyroscopic_torque[index, axis])})}}{{{_value(BODY_INERTIA[axis])}}}"
            rf"={_value(trace.angular_acceleration[index, axis])}\ \mathrm{{rad/s^2}}"
        )
        + r"$e_b$ is the attitude error in radians. $\hat\omega_b$ is the estimated rate "
        r"in rad/s. $K_p$ sets the restoring torque and $K_d$ sets damping. The plant "
        r"adds disturbance torque, subtracts the gyroscopic term, and divides by the axis "
        r"inertia $J_i$ in kg·m². [Change gains and the torque limit](#adjust-the-attitude)."
    )
