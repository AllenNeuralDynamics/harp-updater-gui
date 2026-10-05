import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

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


@pytest.mark.parametrize("returncode", [0, 1])
def test_streaming_output_arrives_before_process_exit(mocker, returncode):
    cli = CLIWrapper()
    original_popen = subprocess.Popen
    processes = []
    first_update = Event()
    messages = []
    code = (
        "import sys; "
        "sys.stdout.buffer.write(b'10% Write\\r'); sys.stdout.flush(); "
        "sys.stdin.readline(); "
        "sys.stdout.buffer.write(b'Firmware written\\r\\n'); sys.stdout.flush(); "
        "sys.stderr.write('Readiness result'); sys.stderr.flush(); "
        f"sys.exit({returncode})"
    )

    def start_process(*args, **kwargs):
        process = original_popen(*args, stdin=subprocess.PIPE, **kwargs)
        processes.append(process)
        return process

    def on_output(message):
        messages.append(message)
        if message == "10% Write":
            first_update.set()

    mocker.patch.object(subprocess, "Popen", side_effect=start_process)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            cli._run_streaming_command, [sys.executable, "-u", "-c", code], on_output
        )
        try:
            assert first_update.wait(timeout=5)
            assert processes[0].poll() is None
            assert messages == ["10% Write"]
        finally:
            if processes:
                processes[0].stdin.write(b"continue\n")
                processes[0].stdin.flush()
        if returncode:
            with pytest.raises(subprocess.CalledProcessError) as error:
                future.result(timeout=5)
            output = error.value.stdout
        else:
            output = future.result(timeout=5).stdout

    assert messages == ["10% Write", "Firmware written", "Readiness result"]
    assert output == "10% Write\rFirmware written\r\nReadiness result"


def test_upload_callback_selects_streaming_runner(mocker):
    cli = CLIWrapper()
    callback = mocker.Mock()
    streaming = mocker.patch.object(
        cli, "_run_streaming_command",
        return_value=subprocess.CompletedProcess([], 0, stdout="Uploaded"),
    )
    buffered = mocker.patch.object(cli, "_run_command")

    assert cli.upload_firmware("firmware.hex", "COM4", on_output=callback) == (True, "Uploaded")
    assert streaming.call_args.args[1] is callback
    buffered.assert_not_called()


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