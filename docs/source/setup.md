# Setup Instructions

This page walks through setup from scratch.

## Option A: Use pre-built binaries (Windows)

This is the fastest path if you only need to run the app.

1. Go to the app's GitHub [releases](https://github.com/AllenNeuralDynamics/harp-updater-gui/releases) page
2. Download either:
	- Installer: `harp_updater_gui-installer-<tag>.exe` (recommended)
	- Portable zip: `harp_updater_gui-<tag>.zip`
3. If using the installer, run it. The installer automatically checks for .NET 8 Desktop Runtime and downloads/installs it if needed.
4. If using zip, right-click the zip file → Properties → Unblock before extracting.
5. Launch `harp_updater_gui.exe`.

```{important}
For the portable zip distribution, always **Unblock** the zip file before extraction (see step 4 above).
Otherwise Windows may propagate download security metadata and block the extracted app or dependencies.
```

Notes:

- Keep the extracted folder structure intact (`harp_updater_gui.exe` + `_internal`)
- If using the installer, .NET 8 Desktop Runtime is checked automatically and installed when missing.
- If using zip, install [Microsoft .NET 8.0 Desktop Runtime (x64)](https://dotnet.microsoft.com/en-us/download/dotnet/8.0/runtime/desktop)
- If SmartScreen appears, verify source and allow execution
- If a browser opens on `localhost` but no native window appears, install WebView2 Runtime and .NET Desktop Runtime (x64)

## Option B: Run from source

Use this option if you are developing or testing changes.

## 1) Prerequisites

- Python `>=3.11,<4.0` (3.12 recommended)
- HarpRegulator CLI installed
- USB access to your Harp devices
- `uv` package manager

## 2) Install uv

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### macOS / Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 3) Install project dependencies

```bash
cd harp-updater-gui
uv sync
```

## 4) Configure HarpRegulator executable path

Open `src/harp_updater_gui/main.py` and verify the executable path passed to:

- `DeviceManager(...)`
- `FirmwareService(...)`

The repository currently includes a machine-specific Windows path by default.

## 5) Start the application

```bash
uv run harp-updater-gui
```

Alternative launcher:

```bash
uv run python run.py
```

## 6) Confirm startup

You should see:

- Header with app title
- Device table panel
- Activity log panel
- Footer links

If startup fails, check [Issue Reporting](issue-reporting.md) and [FAQs](faq.md).
