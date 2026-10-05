# CSS Styling Guide

## Overview

Styling is centralized in:

`src/harp_updater_gui/static/styles.css`

The stylesheet is injected at startup in `main.py` using `ui.add_head_html(...)`.

## Theme Model

The app combines two sources of styling variables:

1. **NiceGUI/Quasar theme tokens** set in `ui.colors(...)`
	 - `--q-primary`, `--q-secondary`, `--q-accent`, `--q-positive`, `--q-negative`, `--q-info`, `--q-warning`
2. **Local semantic tokens** in `:root` and `body.body--dark`
	 - `--bg-*`, `--text-*`, `--border-*`, `--shadow-*`

Dark mode is controlled by NiceGUI (`ui.dark_mode()`), and CSS reacts through `body.body--dark`.

## Implemented CSS Sections

### Global Layout

- The desktop layout fills the viewport using Quasar's measured header/footer spacing, without fixed pixel compensation.
- `.nicegui-content` and `.app-container` pass the available height to the splitter panels.
- `.device-table-scroll` fits short device lists and shrinks to the available height for longer lists; its header stays sticky and pagination stays outside the scrolling body.
- Firmware controls do not shrink into the table. Browse and filename occupy the first row; Batch and Force sit below on the left, with Deploy on the right. Small screens stack the second row.
- At widths of 960 CSS pixels or less, panels stack and the document scrolls. Short desktop windows use compact spacing.

### Header/Footer

- `.header-container`, `.header-title`, `.header-subtitle`
- `.footer-container`, `.footer-link`

### Device Table Area

- `.device-table-container`
- Quasar table overrides for `.q-table`, `.q-table th`, `.q-table td`, hover and selected states
- `.firmware-upload-card`

### Workflow Log Area

- `.workflow-container`, `.workflow-title`, `.activity-log`
- Log-level classes:
	- `.log-info`
	- `.log-success`
	- `.log-warning`
	- `.log-error`
	- `.log-debug`

### Reusable Utilities

- Buttons: `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-success`, `.btn-full`
- Form controls: `.input-field`, `.select-field`
- Utility helpers: `.hidden`, `.text-*`, `.font-*`, `.mt-*`, `.mb-*`, `.p-*`, `.gap-*`, `.items-center`

### Scrollbar Styling

- Custom `::-webkit-scrollbar*` rules aligned with theme tokens

## Component-Class Mapping (Current)

- `components/header.py`
	- `.header-container`, `.header-title`, `.header-subtitle`
- `components/device_table.py`
	- `.device-table-container`, `.firmware-upload-card`, `.btn`, `.btn-primary`, `.btn-secondary`
- `components/update_workflow.py`
	- `.workflow-container`, `.workflow-title`, `.activity-log`, `.log-*`

## Working with Styles

1. Prefer existing utility and component classes before adding new ones.
2. Use Quasar theme tokens (`--q-*`) or existing semantic tokens (`--bg-*`, `--text-*`) instead of introducing arbitrary colors.
3. Keep dark-mode compatibility by validating both default and `body.body--dark` states.
4. Since `reload=False` is used in `ui.run(...)`, restart the app after CSS edits.

## Notes

- Some classes in `styles.css` are generic helpers and may not currently be used in every component.
- The refresh and upload loading indicators are rendered with NiceGUI dialogs and use shared utility classes such as `.items-center` and spacing helpers.

## Layout Verification

Check empty and single-device lists for unnecessary table whitespace, and use at least
12 devices to exercise both table-body scrolling and pagination.
Check long firmware filenames, row selection on the second page, and light/dark mode.
Pagination and Deploy must stay within the desktop panel, above the fixed footer.
On narrow windows, scrolling must expose every firmware control without horizontal page overflow.

Test logical viewports of 1366x768, 1280x720, 1024x600, 800x600, and 390x844.
For a 1366x768 display, 125% and 150% scaling correspond approximately to
1093x614 and 911x512 logical viewports. Browser viewport checks cover the layout
at these sizes; verify native WebView resizing and actual Windows DPI transitions
on the release machine as well.
