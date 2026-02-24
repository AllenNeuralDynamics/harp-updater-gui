import logging
import logging.handlers
import os
from importlib.metadata import PackageNotFoundError, version


DEFAULT_LOGSERVER_URL = "eng-logtools.corp.alleninstitute.org:9000"
LOGGER_NAME = "harp_updater_gui.update_audit"


class LogServerHandler(logging.handlers.SocketHandler):
    """Socket handler that enriches records with metadata for the internal log server."""

    def __init__(
        self,
        project_name: str,
        project_version: str,
        rig_id: str,
        comp_id: str,
        host: str,
        port: int,
    ):
        super().__init__(host=host, port=port)
        self.project_name = project_name
        self.project_version = project_version
        self.rig_id = rig_id
        self.comp_id = comp_id
        self.formatter = logging.Formatter(
            datefmt="%Y-%m-%d %H:%M:%S",
            fmt="%(asctime)s\n%(name)s\n%(levelname)s\n%(funcName)s (%(filename)s:%(lineno)d)\n%(message)s",
        )

        print (f"Initialized LogServerHandler for {project_name} v{project_version} at {host}:{port} with rig_id={rig_id} comp_id={comp_id}")

    def emit(self, record: logging.LogRecord) -> None:
        record.project = self.project_name
        record.version = self.project_version
        record.rig_id = self.rig_id
        record.comp_id = self.comp_id
        record.extra = None
        super().emit(record)


def _resolve_version(distribution_name: str) -> str:
    try:
        return version(distribution_name)
    except PackageNotFoundError:
        return "unknown"


def _parse_host_port(logserver_url: str) -> tuple[str, int]:
    host, port_raw = logserver_url.rsplit(":", maxsplit=1)
    return host.strip(), int(port_raw.strip())


def setup_update_audit_logger(
    app_name: str = "harp_updater_gui",
    app_version: str | None = None,
    logserver_url: str | None = None,
) -> logging.Logger:
    """Create a singleton logger that sends update audit records to the internal log server."""
    logger = logging.getLogger(LOGGER_NAME)

    if getattr(logger, "_audit_configured", False):
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    resolved_version = app_version or _resolve_version(app_name)
    resolved_url = (
        logserver_url
        if logserver_url is not None
        else os.getenv("HARP_UPDATER_LOGSERVER_URL", DEFAULT_LOGSERVER_URL)
    )

    if not resolved_url:
        logger.addHandler(logging.NullHandler())
        logger._audit_configured = True
        return logger

    try:
        host, port = _parse_host_port(resolved_url)
    except (ValueError, TypeError):
        logger.warning(
            "Invalid HARP_UPDATER_LOGSERVER_URL; expected host:port, got '%s'",
            resolved_url,
        )
        logger.addHandler(logging.NullHandler())
        logger._audit_configured = True
        return logger

    handler = LogServerHandler(
        host=host,
        port=port,
        project_name=app_name,
        project_version=resolved_version,
        rig_id=os.getenv("aibs_rig_id", "unknown"),
        comp_id=os.getenv("aibs_comp_id", "unknown"),
    )
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger._audit_configured = True

    return logger


def log_successful_firmware_update(
    logger: logging.Logger,
    device_name: str,
    port_name: str,
    previous_firmware_version: str,
    new_firmware_version: str,
) -> None:
    """Emit a structured success log for internal firmware update auditing."""
    logger.info(
        "firmware_update_success device_name=%s port=%s previous_fw=%s new_fw=%s",
        device_name,
        port_name,
        previous_firmware_version,
        new_firmware_version,
        extra={
            "device_name": device_name,
            "port": port_name,
            "previous_fw": previous_firmware_version,
            "new_fw": new_firmware_version,
        },
    )
