# -*- mode: python ; coding: utf-8 -*-
import nicegui
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Function to get the nicegui base path dynamically
def get_nicegui_path():
    # Get the directory containing the nicegui module
    nicegui_dir = os.path.dirname(nicegui.__file__)
    return nicegui_dir

a = Analysis(
    ['src\\harp_updater_gui\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (get_nicegui_path(), 'nicegui'),
        ('src/harp_updater_gui/static', 'static'),
        ('deps/harp_regulator', 'harp_regulator'),
        *collect_data_files('webview', include_py_files=True),
    ],
    hiddenimports=[
        *collect_submodules('webview.platforms'),
        *collect_submodules('pythonnet'),
        *collect_submodules('clr_loader'),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='harp_updater_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['src\\harp_updater_gui\\static\\app_icon_color.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='harp_updater_gui',
)
