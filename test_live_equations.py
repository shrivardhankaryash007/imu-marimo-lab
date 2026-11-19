from dataclasses import replace

import numpy as np

from attitude_sim import BODY_INERTIA, Settings, run_control, run_replay
from gyro_rls import RecursiveLeastSquares, calibrate_gyro
from live_equations import complementary, control, kalman, prediction, rls_update


def test_filter_inspector_reads_the_replay_update_and_gate():
    settings = Settings()
    replay = run_replay(settings)
    pair = replay.updates[60]["accelerometer"]
    step = pair.complementary
    np.testing.assert_allclose(step.error, np.cross(step.observed, step.predicted))
    update = pair.kalman
    assert update.accepted
    np.testing.assert_allclose(update.correction, update.gain @ update.residual)

    assert "initializes attitude" in prediction(replay, 0, 2)
    assert prediction(replay, 60, 2) != prediction(replay, 61, 2)
    assert complementary(replay, settings, 60, 0, "accelerometer") != complementary(
        replay, settings, 60, 2, "accelerometer"
    )
    assert "Kalman gain" in kalman(replay, settings, 60, 2, "accelerometer")
    rejected_index, reference = next(
        (index, name)
        for index, row in enumerate(replay.updates)
        for name, update_pair in row.items()
        if not update_pair.kalman.accepted
    )
    assert "NIS gate rejected" in kalman(replay, settings, rejected_index, 2, reference)
    without_heading = replace(settings, heading_aid=False)
    assert "Heading aid is off" in kalman(
        run_replay(without_heading), without_heading, 60, 2, "magnetometer"
    )


def test_rls_inspector_reads_the_sequential_parameter_fit():
    forgetting = 0.98
    run = calibrate_gyro(forgetting, 2.0, "Varied rate")
    prior = RecursiveLeastSquares(forgetting).estimate
    np.testing.assert_allclose(run.estimates[0], prior + run.gain[0] * run.residual[0])
    np.testing.assert_allclose(
        run.estimates[1:], run.estimates[:-1] + run.gain[1:] * run.residual[1:, None]
    )
    assert rls_update(run, forgetting, 0) != rls_update(run, forgetting, 60)


def test_control_inspector_reads_the_torque_and_actual_plant_update():
    kp, kd, limit = 0.80, 0.45, 0.35
    run = run_control(Settings(), kp, kd, limit, 0.15)
    for trace in (run.complementary, run.ekf):
        requested = kp * trace.error_vector - kd * trace.estimated_rate
        np.testing.assert_allclose(trace.torque, np.clip(requested, -limit, limit))
        np.testing.assert_allclose(
            trace.angular_acceleration,
            (trace.torque + trace.disturbance_torque - trace.gyroscopic_torque) / BODY_INERTIA,
        )
        index, axis = np.argwhere(abs(requested) > limit)[0]
        assert "at the actuator limit" in control(trace, index, axis, kp, kd, limit)
