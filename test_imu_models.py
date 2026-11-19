"""Physics anchors for the interactive IMU course."""

from dataclasses import dataclass
from xml.etree import ElementTree

import numpy as np

import imu_tutor
from imu_cutaway import cutaway
from imu_navigation import control_case, fusion_case, motion_case
from imu_sensor import chip_sample, compass_heading_deg, magnetic_sweep, pose_trial, rotation
from imu_tutor import ExperimentContext, tutor_messages


def test_supported_free_fall_and_gyro_sign() -> None:
    bench = chip_sample(0, 0, False, 2, 10, 90)
    dropped = chip_sample(37, 0, True, 2, 10, -90)
    clipped = chip_sample(0, 4, False, 2, 10, 0)
    np.testing.assert_allclose(bench.specific_g, [0, 0, 1])
    np.testing.assert_allclose(dropped.measured_g, [0, 0, 0])
    np.testing.assert_allclose(clipped.measured_g, [2, 0, 1])
    assert dropped.coriolis_mm_s2 == -bench.coriolis_mm_s2 > 0


def test_frame_and_heading_conventions() -> None:
    body = rotation(0, 0, 90)
    np.testing.assert_allclose(body @ [1, 0, 0], [0, 1, 0], atol=1e-12)
    np.testing.assert_allclose(body.T @ [0, 0, 1], [0, 0, 1])
    ideal, raw, point, selected_raw = magnetic_sweep(0, 0, 1, 10)
    np.testing.assert_allclose(raw, ideal)
    np.testing.assert_allclose(selected_raw, point)
    assert abs((compass_heading_deg(point) + 10) % 360 - 90) < 1e-9


def test_arbitrary_mount_and_offset_recover_reference_state() -> None:
    offset = np.array([0.5, -0.37, 0.8])
    ref, p_sensor, v_sensor, f_sensor = pose_trial(offset, 39, -22, 1.7)
    at_origin, _, _, _ = pose_trial(np.zeros(3), 39, 115, -1.1)
    np.testing.assert_allclose(ref.body_to_world, rotation(20, -30, 39), atol=1e-12)
    np.testing.assert_allclose(ref.body_to_world, at_origin.body_to_world, atol=1e-12)
    np.testing.assert_allclose(ref.offset_world_m, ref.body_to_world @ offset, atol=1e-12)
    np.testing.assert_allclose(ref.position_m, [2, -1, 1.5])
    np.testing.assert_allclose(ref.velocity_m_s, [0.8, 0.3, 0.4])
    np.testing.assert_allclose(ref.acceleration_m_s2, [0.1, 0.4, -0.2])
    assert not np.allclose(ref.position_m, p_sensor)
    assert not np.allclose(ref.velocity_m_s, v_sensor)
    assert np.linalg.norm(f_sensor) > 8


def test_rotating_mount_and_aiding_anchor() -> None:
    ideal = motion_case(0.75, 90, 4, 0, 5)
    assert abs(ideal.radial_m_s2[0] + (np.pi / 2) ** 2 * 0.75) < 1e-12
    assert abs(ideal.tangential_m_s2[0] - np.deg2rad(4) * 0.75) < 1e-12
    np.testing.assert_allclose(ideal.corrected_pos, ideal.truth_pos, atol=1e-4)
    biased = motion_case(0.75, 0, 0, 0.1, 5)
    last = -1
    drift = biased.corrected_pos[last, 0] - biased.truth_pos[last, 0]
    assert abs(drift - 0.5 * 0.1 * 20**2) < 1e-4
    np.testing.assert_allclose(biased.aided_pos[last], biased.truth_pos[last])
    np.testing.assert_allclose(biased.aided_vel[last], biased.truth_vel[last])


def test_fusion_and_feedback_have_distinct_baselines() -> None:
    ideal = fusion_case(0, 0, 0.03, False)
    np.testing.assert_allclose(ideal.accel_deg, ideal.truth_deg, atol=1e-9)
    disturbed = fusion_case(1.4, 1.5, 0.04, False)
    gated = fusion_case(1.4, 1.5, 0.04, True)
    assert gated.rejected.any()
    assert np.max(abs(gated.fused_deg - gated.truth_deg)) < np.max(
        abs(disturbed.fused_deg - disturbed.truth_deg)
    )
    control = control_case(3, 2, 0.6)
    assert abs(control.target_deg[-1] - control.closed_deg[-1]) < 1
    assert abs(control.target_deg[-1] - control.open_deg[-1]) > 10
    assert np.max(abs(control.torque)) <= 4


def test_cutaway_stages_include_svg_and_live_motion() -> None:
    for stage in ("Pattern", "Release", "Package", "Readout"):
        svg = cutaway(0, stage)
        assert ElementTree.fromstring(svg).tag.endswith("svg")
        assert stage in svg
    assert cutaway(0, "Release") != cutaway(0.8, "Release")


@dataclass(frozen=True)
class Message:
    """Minimal analogue of the notebook chat widget turn."""

    role: str
    content: str


def test_tutor_uses_latest_chapter_but_keeps_conversation() -> None:
    context = ExperimentContext("Sensors", "supported", "source")
    turns = [Message("user", "What happened?"), Message("assistant", "Let's change a control.")]
    previous = tutor_messages(context, turns)
    context.chapter = "Fusion"
    context.values = "gate enabled"
    current = tutor_messages(context, turns)
    assert "supported" not in current[0]["content"]
    assert "Active chapter: Fusion" in current[0]["content"]
    assert "gate enabled" in current[0]["content"]
    assert current[1:] == previous[1:]


def test_notes_include_trials_and_only_explicit_conversation() -> None:
    turns = [Message("user", "What changed?"), Message("assistant", "The sensors rotated.")]
    without = imu_tutor.notes_markdown("Attitude", "Pitch 25°", "Mount offset matters.", [])
    with_dialog = imu_tutor.notes_markdown("Attitude", "Pitch 25°", "", turns)
    assert "Pitch 25°" in without.decode()
    assert "Mount offset matters." in without.decode()
    assert "What changed?" not in without.decode()
    assert "## Tutor conversation" in with_dialog.decode()
    assert "What changed?" in with_dialog.decode()
    assert "The sensors rotated." in with_dialog.decode()
