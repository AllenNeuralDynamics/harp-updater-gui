# Quick Start Guide

Get the current app running in a few minutes.

## Option A: Use pre-built binaries (Windows)

1. Open: https://github.com/AllenNeuralDynamics/harp-updater-gui/releases
2. Download either:
	- Installer: `harp_updater_gui-installer-<tag>.exe` (recommended)
	- Portable zip: `harp_updater_gui-<tag>.zip`
3. If using the installer, run it. The installer auto-checks for .NET 8 Desktop Runtime and downloads/installs it if needed.
4. If using zip, **unblock** the zip before extraction (see warning below), then run `harp_updater_gui.exe`.

> [!IMPORTANT]
> For the **portable zip** package, right-click the zip file → **Properties** → **Unblock** before extracting.
> This prevents Windows security metadata from blocking the extracted executable/dependencies.

## Prerequisites

1. Python `>=3.11,<4.0` (3.12 recommended)
2. HarpRegulator CLI installed
3. `uv` package manager

## 1) Install uv

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 2) Install dependencies

```bash
cd harp-updater-gui
uv sync
```

## 3) Configure HarpRegulator path

Open `src/harp_updater_gui/main.py` and verify the executable path passed to:
- `DeviceManager(...)`
- `FirmwareService(...)`

The repository currently contains a machine-specific Windows path by default.

## 4) Start app

```bash
uv run harp-updater-gui
```

Alternative:

```bash
uv run python run.py
```

## First Run Workflow

1. Connect one or more Harp devices.
2. Click **Refresh** in the device table.
3. Select a device row.
4. Click **Browse** and pick a firmware file (`.uf2`/`.hex`).
5. Optional: enable batch update by name.
6. Click **Deploy Firmware**.
7. Watch progress in dialogs and the activity log.

## Useful Commands

```bash
uv run harp-updater-gui
uv run pytest
uv run pytest -v
uv run ruff check .
uv run ruff format .
```

## Troubleshooting

### HarpRegulator not found
```bash
HarpRegulator --help
```
If this fails, install HarpRegulator or fix the path in `main.py`.

### No devices detected
1. Reconnect USB device/cable
2. On Windows: `HarpRegulator install-drivers`
3. Refresh with **Connect all** enabled

### Firmware rejected
- Pico requires `.uf2`
- ATxmega requires `.hex`
- Ensure the selected file exists

## Runtime Notes

- App runs with `native=True` and `reload=False`
- Port is configured to `4277`
- Refresh and deploy operations show modal loading dialogs
