import asyncio

import pytest
from nicegui import ui
from nicegui.elements.table import Table

from harp_updater_gui.components import device_table as table_module
from harp_updater_gui.models.device import Device
from harp_updater_gui.services.device_manager import DeviceManager
from harp_updater_gui.services.device_operations import DeviceOperations


@pytest.fixture
def table(tmp_path, mocker):
    manager = DeviceManager(operations=DeviceOperations(tmp_path / "devices.lock"))
    component = table_module.DeviceTable(manager, mocker.Mock(), mocker.AsyncMock())
    component.table = mocker.Mock(spec=Table, selected=[], rows=[])
    component.deploy_button = mocker.Mock()
    component.refresh_button = mocker.Mock()
    component.force_upload_checkbox = mocker.Mock(value=False)
    component.batch_update_checkbox = mocker.Mock(value=False)
    component.firmware_file_path = "firmware.hex"
    mocker.patch.object(table_module, "ui")
    return component


def device(serial="FIRST", port="COM4"):
    return Device(
        Confidence="High", Kind="ATxmega", State="Online",
        SerialNumber=serial, PortName=port,
    )


def test_refresh_rebinds_selection_to_current_object(table):
    table.selected_device = device()
    current = device(port="COM9")
    table.device_manager.devices = [current]

    table.update_table()

    assert table.selected_device is current
    assert table.device_manager.selected_device is current
    assert table.table.selected == [table.table.rows[0]]
    table.deploy_button.set_enabled.assert_called_with(True)


def test_refresh_clears_removed_or_replaced_selection(table):
    table.selected_device = device()
    table.device_manager.devices = [device(serial="REPLACEMENT")]

    table.update_table()

    assert table.selected_device is None
    assert table.device_manager.selected_device is None
    assert table.table.selected == []
    table.deploy_button.set_enabled.assert_called_with(False)


def test_portless_rows_have_distinct_keys_and_ambiguous_selection_is_rejected(table):
    bootloader = Device(Confidence="High", Kind="Pico", State="Bootloader")
    table.device_manager.devices = [bootloader, bootloader.model_copy()]
    table.update_table()

    assert len({row["id"] for row in table.table.rows}) == 2
    table.table.selected = [table.table.rows[0]]
    table.on_row_select(None)

    assert table.selected_device is None
    table.deploy_button.set_enabled.assert_called_with(False)


@pytest.mark.parametrize("flag", ["is_deploying", "is_refreshing", "is_installing_drivers"])
def test_table_update_never_reenables_deploy_during_operation(table, flag):
    table.selected_device = device()
    table.device_manager.devices = [table.selected_device]
    setattr(table, flag, True)

    table.update_table()

    table.deploy_button.set_enabled.assert_called_with(False)
    table.refresh_button.set_enabled.assert_called_with(False)


def test_busy_state_uses_real_nicegui_table_api(table):
    table.table = ui.table(rows=[], columns=[], selection="single", row_key="id")
    try:
        table.is_deploying = True
        table._update_control_state()
        assert table.table.props["selection"] == "none"
        table.is_deploying = False
        table._update_control_state()
        assert table.table.props["selection"] == "single"
    finally:
        table.table.delete()


def test_render_keeps_deploy_outside_the_scrollable_table(table, mocker):
    mocker.patch.object(table_module, "ui", ui)
    mocker.patch.object(ui, "timer")
    table.render()
    container = table.table.parent_slot.parent
    try:
        assert "device-table-scroll" in table.table.classes
        assert table.table.pagination["rowsPerPage"] == 10
        actions = table.deploy_button.parent_slot.parent
        assert "firmware-upload-actions" in actions.classes
        layout = actions.parent_slot.parent
        assert "firmware-upload-layout" in layout.classes
        assert "firmware-upload-file-row" in table.browse_button.parent_slot.parent.classes
        assert table.browse_button.parent_slot.parent.parent_slot.parent is layout
        options = table.batch_update_checkbox.parent_slot.parent
        assert "firmware-upload-options" in options.classes
        assert options.parent_slot.parent is actions
        assert table.force_upload_checkbox.parent_slot.parent is options
        firmware_section = layout.parent_slot.parent
        assert "firmware-upload-card" in firmware_section.classes
        assert firmware_section.parent_slot.parent is container
    finally:
        container.delete()


@pytest.mark.asyncio
async def test_second_deploy_callback_is_rejected_until_first_finishes(table):
    table.selected_device = device()
    table.device_manager.devices = [table.selected_device]
    entered, finish = asyncio.Event(), asyncio.Event()

    async def deploy(*args):
        entered.set()
        await finish.wait()

    table.on_deploy.side_effect = deploy
    task = asyncio.create_task(table.deploy_firmware())
    await entered.wait()
    try:
        table.update_table()
        table.deploy_button.set_enabled.assert_called_with(False)
        await table.deploy_firmware()
        table.on_deploy.assert_awaited_once()
    finally:
        finish.set()
        await task

    assert not table.is_deploying
    table.deploy_button.set_enabled.assert_called_with(True)


@pytest.mark.asyncio
async def test_other_client_operation_blocks_all_handlers(table, mocker):
    table.selected_device = device()
    table.device_manager.devices = [table.selected_device]
    discovery = mocker.patch.object(table.device_manager.cli, "list_devices")
    install = mocker.patch.object(table.device_manager.cli, "install_drivers")
    lease = table.device_manager.operations.begin("Other client deployment")
    try:
        table.update_table()
        await table.refresh_devices()
        await table.install_drivers()
        await table.deploy_firmware()
        table.deploy_button.set_enabled.assert_called_with(False)
        table.on_deploy.assert_not_awaited()
        discovery.assert_not_called()
        install.assert_not_called()
    finally:
        table.device_manager.operations.end(lease)

    table._update_control_state()
    table.deploy_button.set_enabled.assert_called_with(True)