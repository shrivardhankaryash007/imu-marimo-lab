from attitude_charts import control_figure, diagnostic_figure, estimate_figure, pose_figure
from attitude_sim import Settings, run_control, run_replay


def test_attitude_charts_reserve_distinct_title_and_legend_regions():
    settings = Settings()
    replay = run_replay(settings)
    controller = run_control(settings, 0.8, 0.45, 0.35, 0.15)
    control = control_figure(controller, axis=0)
    pose = pose_figure(replay, index=60)
    for figure in (control, pose, estimate_figure(replay), diagnostic_figure(replay)):
        layout = figure.layout
        assert (layout.title.yref, layout.title.yanchor) == ("container", "top")
        assert (layout.legend.yref, layout.legend.yanchor) == ("container", "bottom")
        assert layout.margin.b > layout.legend.maxheight

    assert [trace.name for trace in control.data if trace.showlegend] == [
        "Complementary",
        "Error-state EKF",
        "Target",
    ]
    assert control.layout.annotations[1].text == "Roll response"
    assert [trace.name for trace in pose.data if trace.showlegend] == [
        "True body",
        "EKF body",
        "True IMU",
        "EKF IMU",
        "True IMU position",
    ]
