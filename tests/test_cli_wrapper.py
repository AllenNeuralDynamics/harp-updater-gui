import subprocess
import sys
from pathlib import Path

import pytest

from harp_updater_gui.services.cli_wrapper import CLIWrapper


REGULATOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "deps/harp_regulator/win-x64/HarpRegulator.exe"
)


@pytest.mark.parametrize(
    "stdout, stderr, expected",
    [
        (
            "Firmware written. Waiting for the device to restart...\n",
            "Firmware was written, but the device did not respond within 20 seconds.\n",
            "Firmware written. Waiting for the device to restart...\n"
            "Firmware was written, but the device did not respond within 20 seconds.",
        ),
        ("Upload aborted", "", "Upload aborted"),
        (None, "Invalid HEX checksum", "Invalid HEX checksum"),
        (None, None, "Firmware upload failed with exit code 1."),
    ],
)
def test_upload_failure_preserves_output(mocker, stdout, stderr, expected):
    cli = CLIWrapper()
    mocker.patch.object(
        cli,
        "_run_command",
        side_effect=subprocess.CalledProcessError(
            1, ["HarpRegulator"], output=stdout, stderr=stderr
        ),
    )

    assert cli.upload_firmware("firmware.hex", "COM4") == (False, expected)


def test_atxmega_validation_command(mocker):
    cli = CLIWrapper()
    command = mocker.patch.object(
        cli,
        "_run_command",
        return_value=subprocess.CompletedProcess([], 0, stdout="Firmware upload skipped"),
    )

    assert cli.upload_firmware(
        "Behavior-fw3.3-harp1.15-hw2.0-ass0.hex",
        "validation-only",
        progress=False,
        no_upload=True,
    ) == (True, "Firmware upload skipped")
    command.assert_called_once_with(
        [
            "HarpRegulator",
            "upload",
            "Behavior-fw3.3-harp1.15-hw2.0-ass0.hex",
            "--target",
            "validation-only",
            "--no-interactive",
            "--no-progress",
            "--no-upload",
        ]
    )


@pytest.mark.skipif(
    sys.platform != "win32" or not REGULATOR_PATH.is_file(),
    reason="Bundled Windows regulator is not available",
)
@pytest.mark.parametrize(
    "filename, contents, force, expected_success",
    [
        ("Behavior-fw3.3-harp1.15-hw2.0-ass0.hex", ":0400000001020304F2\n:00000001FF\n", False, True),
        ("Behavior-fw3.3-harp1.15-hwx.x-assx-preview1.hex", ":00000001FF\n", False, True),
        ("firmware.hex", ":00000001FF\n", True, False),
        ("Behavior-fw3.3-harp1.15-hw2.0-ass0.hex", ":0400000001020304F3\n:00000001FF\n", True, False),
    ],
)
def test_bundled_regulator_validates_without_device_access(
    tmp_path, filename, contents, force, expected_success
):
    firmware = tmp_path / filename
    firmware.write_text(contents)

    success, output = CLIWrapper(str(REGULATOR_PATH)).upload_firmware(
        str(firmware),
        "validation-only",
        force=force,
        progress=False,
        no_upload=True,
    )

    assert success is expected_success, output
    if success:
        assert "No device connection was made" in output
    else:
        assert "Failed to load firmware file" in output