from demo.fountain import ProductionFountain, ProductionScenario, status_for_alert


def test_fountain_returns_none_when_no_abnormal_event_occurs() -> None:
    fountain = ProductionFountain(event_probability=0.0, seed=1)

    assert fountain.next_alert() is None


def test_fountain_generates_valid_abnormal_alert() -> None:
    fountain = ProductionFountain(event_probability=1.0, seed=1)

    alert = fountain.next_alert()

    assert alert is not None
    assert alert.alert_id.startswith("sim-")
    assert alert.asset_id in {"cnc-01", "assembly-robot-02", "packaging-line-03"}
    assert alert.severity in {"critical", "warning", "info"}
    assert status_for_alert(alert) in {"fault", "warning", "idle", "maintenance"}


def test_robot_fault_creates_dependent_packaging_idle_event() -> None:
    robot_fault = ProductionScenario(
        asset_id="assembly-robot-02",
        alert_type="temperature_high",
        severity="critical",
        value_min=90.0,
        value_max=90.0,
        unit="celsius",
        message_template="Robot fault",
        status="fault",
    )
    fountain = ProductionFountain(event_probability=1.0, seed=1, scenarios=[robot_fault])

    first_alert = fountain.next_alert()
    second_alert = fountain.next_alert()

    assert first_alert is not None
    assert second_alert is not None
    assert first_alert.asset_id == "assembly-robot-02"
    assert second_alert.asset_id == "packaging-line-03"
    assert second_alert.alert_type == "idle_detected"
