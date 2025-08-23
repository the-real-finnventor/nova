# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['menu_bar.py'],
    pathex=[],
    # binaries=[('/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/ffmpeg', '.')],
    binaries=None,
    datas=[('settings.yml', '.'), ('.venv/lib/python3.13/site-packages/whisper', 'whisper')],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='Nova',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
app = BUNDLE(
    exe,
    name='Nova.app',
    bundle_identifier="com.everspaugh.nova",
    info_plist= { 
        "NSMicrophoneUsageDescription":"Nova needs to hear your request", 
        "LSUIElement": True,
         "RunAtLoad": True
        },
    icon="atom.icns"
)
