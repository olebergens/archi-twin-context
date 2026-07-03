from archi_twin_context.impact import calculate_risk_level


def test_critical_high_results_in_critical() -> None:
    assert calculate_risk_level("critical", "high") == "critical"


def test_warning_high_results_in_high() -> None:
    assert calculate_risk_level("warning", "high") == "high"


def test_unknown_combination_falls_back_to_low() -> None:
    assert calculate_risk_level("unknown", "low") == "low"
