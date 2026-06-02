# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Anees.

macOS:  pyinstaller anees.spec   → dist/Anees.app
Windows: pyinstaller anees.spec  → dist/Anees/Anees.exe

Requires ffmpeg in PATH (or bundle it in vendor/ and set ffmpeg_location
in YtdlpClient before packaging for a fully self-contained build).
"""

import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

# yt-dlp ships many dynamic extractors — collect everything
yt_dlp_datas, yt_dlp_binaries, yt_dlp_hiddenimports = collect_all("yt_dlp")

# Bundle the platform-specific ffmpeg binary so users don't need to install it
_ffmpeg_bin = []
if sys.platform == "win32":
    for name in ("ffmpeg.exe", "ffprobe.exe"):
        src = f"vendor/win-x64/{name}"
        if os.path.exists(src):
            _ffmpeg_bin.append((src, "."))
elif sys.platform == "darwin":
    for name in ("ffmpeg", "ffprobe"):
        src = f"vendor/macos/{name}"
        if os.path.exists(src):
            _ffmpeg_bin.append((src, "."))

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=yt_dlp_binaries + _ffmpeg_bin,
    datas=yt_dlp_datas + [("ui/images/anees.ico", "images")],
    hiddenimports=yt_dlp_hiddenimports + [
        "PySide6.QtSvg",
        "PySide6.QtXml",
        "PySide6.QtNetwork",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "PIL"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Anees",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="ui/images/anees.ico" if sys.platform == "win32" else "ui/images/anees.icns",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Anees",
)

# macOS .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Anees.app",
        icon="ui/images/anees.icns",
        bundle_identifier="ai.ginni.anees",
        info_plist={
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
        },
    )
