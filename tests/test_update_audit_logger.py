import logging

from harp_updater_gui.utils import update_audit_logger


def _reset_audit_logger_state():
    logger = logging.getLogger(update_audit_logger.LOGGER_NAME)
    logger.handlers.clear()
    if hasattr(logger, "_audit_configured"):
        delattr(logger, "_audit_configured")


def test_parse_host_port():
    host, port = update_audit_logger._parse_host_port("example.internal:9000")
    assert host == "example.internal"
    assert port == 9000


def test_setup_logger_with_empty_url_uses_null_handler(monkeypatch):
    _reset_audit_logger_state()
    monkeypatch.setenv("HARP_UPDATER_LOGSERVER_URL", "")

    logger = update_audit_logger.setup_update_audit_logger()

    assert any(isinstance(h, logging.NullHandler) for h in logger.handlers)


def test_log_successful_firmware_update_emits_expected_message(mocker):
    logger = mocker.Mock()

    update_audit_logger.log_successful_firmware_update(
        logger=logger,
        device_name="EnvironmentSensor",
        port_name="COM7",
        previous_firmware_version="0.2.0",
        new_firmware_version="0.3.0",
    )

    logger.info.assert_called_once()
    call_args = logger.info.call_args
    assert "firmware_update_success" in call_args.args[0]
    assert call_args.args[1:] == (
        "EnvironmentSensor",
        "COM7",
        "0.2.0",
        "0.3.0",
    )
