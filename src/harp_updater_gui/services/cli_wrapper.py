import json
import os
import subprocess
from typing import List, Dict, Any, Optional


class CLIWrapper:
    """Wrapper for HarpRegulator CLI commands"""

    def __init__(self, cli_path: str = "HarpRegulator"):
        """
        Initialize CLI wrapper

        Args:
            cli_path: Path to HarpRegulator executable (default: "HarpRegulator" in PATH)
        """
        self.cli_path = cli_path
        self._subprocess_kwargs: Dict[str, Any] = {}

        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            self._subprocess_kwargs = {
                "startupinfo": startupinfo,
                "creationflags": subprocess.CREATE_NO_WINDOW,
            }

    def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess[str]:
        """Run CLI command without flashing a console window on Windows."""
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            **self._subprocess_kwargs,
        )

    def _run_elevated_windows(self, args: List[str]) -> tuple[bool, str]:
        """Run a command elevated via UAC on Windows and wait for completion."""
        escaped_path = self.cli_path.replace("'", "''")
        escaped_args = [arg.replace("'", "''") for arg in args]
        quoted_args = ", ".join(f"'{arg}'" for arg in escaped_args)
        script = (
            f"$p = Start-Process -FilePath '{escaped_path}' "
            f"-ArgumentList @({quoted_args}) -Verb RunAs -Wait -PassThru; "
            "exit $p.ExitCode"
        )

        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                **self._subprocess_kwargs,
            )
        except Exception as e:
            return False, f"Failed to request administrator privileges: {e}"

        if result.returncode == 0:
            return True, "Driver installation completed successfully."

        if result.returncode == 1223:
            return False, "Driver installation was canceled at the UAC prompt."

        error_output = (result.stderr or result.stdout or "").strip()
        if error_output:
            return False, error_output

        return (
            False,
            f"Driver installation failed with exit code {result.returncode}.",
        )

    def list_devices(
        self, all_devices: bool = True, allow_connect: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List all connected Harp devices

        Args:
            all_devices: Include all devices, even ones that are not definitively Harp devices
            allow_connect: Allow connecting to devices to enumerate missing metadata

        Returns:
            List of device dictionaries with device information
        """
        cmd = [self.cli_path, "list", "--json"]

        if all_devices:
            cmd.append("--all")

        if allow_connect:
            cmd.append("--allow-connect")

        try:
            result = self._run_command(cmd)

            if result.stdout.strip():
                devices = json.loads(result.stdout)
                return devices if isinstance(devices, list) else []
            return []

        except subprocess.CalledProcessError as e:
            print(f"Error listing devices: {e.stderr}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing device list: {e}")
            return []

    def inspect_firmware(self, firmware_path: str) -> Optional[Dict[str, Any]]:
        """
        Inspect a firmware file

        Args:
            firmware_path: Path to firmware file (.uf2 or .hex)

        Returns:
            Dictionary with firmware information or None on error
        """
        cmd = [self.cli_path, "inspect", firmware_path, "--json"]

        try:
            result = self._run_command(cmd)

            if result.stdout.strip():
                return json.loads(result.stdout)
            return None

        except subprocess.CalledProcessError as e:
            print(f"Error inspecting firmware: {e.stderr}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing firmware info: {e}")
            return None

    def upload_firmware(
        self,
        firmware_path: str,
        target: str,
        force: bool = False,
        no_interactive: bool = True,
        progress: bool = True,
        no_reboot: bool = False,
        verbose: bool = False,
    ) -> tuple[bool, str]:
        """
        Upload firmware to a Harp device

        Args:
            firmware_path: Path to firmware file
            target: Target device (COM port, serial number, or "PICOBOOT")
            force: Force upload even if checks fail
            no_interactive: Run without user prompts
            progress: Show progress bars
            no_reboot: Don't reboot after upload
            verbose: Show verbose output
        Returns:
            Tuple of (success: bool, output: str)
        """
        cmd = [self.cli_path, "upload", firmware_path, "--target", target]

        if force:
            cmd.append("--force")

        if no_interactive:
            cmd.append("--no-interactive")

        if progress:
            cmd.append("--progress")
        else:
            cmd.append("--no-progress")

        if no_reboot:
            cmd.append("--no-reboot")

        if verbose:
            cmd.append("--verbose")

        try:
            result = self._run_command(cmd)
            return True, result.stdout

        except subprocess.CalledProcessError as e:
            return False, e.stderr

    def install_drivers(self) -> tuple[bool, str]:
        """
        Install required USB drivers (Windows only)

        Returns:
            Tuple of (success: bool, output: str)
        """
        if os.name != "nt":
            return True, "Driver installation is only required on Windows; skipped."

        if os.name == "nt":
            return self._run_elevated_windows(["install-drivers"])

        cmd = [self.cli_path, "install-drivers"]

        try:
            result = self._run_command(cmd)
            return True, result.stdout

        except subprocess.CalledProcessError as e:
            return False, e.stderr
