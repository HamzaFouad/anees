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
if sys.platform == "win32" and os.path.exists("vendor/win-x64/ffmpeg.exe"):
    _ffmpeg_bin = [("vendor/win-x64/ffmpeg.exe", ".")]
elif sys.platform == "darwin" and os.path.exists("vendor/macos/ffmpeg"):
    _ffmpeg_bin = [("vendor/macos/ffmpeg", ".")]

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=yt_dlp_binaries + _ffmpeg_bin,
    datas=yt_dlp_datas,
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
    icon=None,              # TODO: add icon.ico / icon.icns
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
        icon=None,
        bundle_identifier="ai.ginni.anees",
        info_plist={
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
        },
    )
