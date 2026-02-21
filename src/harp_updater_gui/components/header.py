from nicegui import ui
import platform
import importlib.metadata



class Header:
    """Application header component"""

    def __init__(self, dark_mode_toggle=None):
        self.connection_status = "Connected"
        self.host_name = platform.node()
        self.dark_mode_toggle = dark_mode_toggle
        self.render()

    def render(self):
        """Render the header component"""
        with ui.header().classes("header-container"):
            with ui.row().classes("w-full justify-between items-center"):
                with ui.row().classes("items-center"):
                    ui.image("/static/app_icon.png").classes("w-16")
                    ui.label("Harp Updater GUI").classes("header-title")
                    ui.label(f"v{importlib.metadata.version('harp_updater_gui')}").classes("text-xs self-end pb-4")
                with ui.row().classes("items-center gap-4"):
                    ui.label(f"Connected to {self.host_name}").classes(
                        "header-subtitle"
                    )
                    # Dark mode toggle button
                    if self.dark_mode_toggle:

                        def toggle_theme(button):
                            self.dark_mode_toggle.toggle()
                            # Update icon based on current mode
                            button.props(
                                f"icon={'light_mode' if self.dark_mode_toggle.value else 'dark_mode'}"
                            )

                        dark_button = (
                            ui.button(
                                icon="dark_mode",
                                on_click=lambda: toggle_theme(dark_button),
                            )
                            .props("flat round")
                            .classes("text-white")
                        )

                        dark_button.tooltip("Toggle theme")

    def update_status(self, connected: bool, host: str = None):
        """
        Update connection status

        Args:
            connected: Whether connected
            host: Host name or identifier
        """
        self.connection_status = "Connected" if connected else "Disconnected"
        if host:
            self.host_name = host
