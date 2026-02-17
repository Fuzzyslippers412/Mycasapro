def test_fleet_manager_includes_mail_agent():
    from core.fleet_manager import get_fleet_manager

    fleet = get_fleet_manager()
    status = fleet.get_fleet_status()

    assert "mail-skill" in status["agents"]
    assert status["agents"]["mail-skill"]["enabled"] is True
