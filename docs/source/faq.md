# FAQs

## Why does firmware file validation fail?

Common causes:

- File does not exist
- Unsupported extension (must be `.uf2` or `.hex`)
- Device/file mismatch:
  - Pico requires `.uf2`
  - ATxmega requires `.hex`
- Invalid ATxmega metadata filename: use
  `<device>-fw<firmware>-harp<core>-hw<hardware>-ass<assembly>.hex`, for example
  `Behavior-fw3.3-harp1.15-hw2.0-ass0.hex`
- Invalid Intel HEX checksums

ATxmega validation uses HarpRegulator `--no-upload` and does not connect to a device.
Force upload cannot bypass invalid filenames or image contents.

## Why are no devices shown after refresh?

- Check USB cable/power
- Reconnect device and retry
- Enable **Connect all** and refresh again
- On Windows, install drivers with:

```bash
HarpRegulator install-drivers
```

## Why does upload fail on a device in use?

Ports can be held by another process. Close tools that may be using the device serial port, then retry.

## When should I use Force upload?

Only when normal upload fails due to compatibility/safety checks and you understand the risk.

For ATxmega devices, Force upload skips device-name and hardware compatibility checks
and can recover a device already in bootloader mode. The GUI suggests force-retry only
for connection or compatibility failures before reset, not after a write or restart failure.

## What does an ATxmega restart timeout mean?

Regulator always restarts ATxmega devices after writing firmware and waits up to
20 seconds for a Harp response. A timeout means firmware was written but the device
did not respond. Check power, the serial port, and the activity log before attempting
recovery. The GUI does not record this result as a successful update.

## Where can I get more help?

- [Issue Reporting](issue-reporting.md)
- GitHub repository: [https://github.com/AllenNeuralDynamics/harp-updater-gui](https://github.com/AllenNeuralDynamics/harp-updater-gui)
