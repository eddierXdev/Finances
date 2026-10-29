# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for the portable Windows desktop build."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

PROJECT_ROOT = Path(SPECPATH).resolve().parent
MIGRATIONS = PROJECT_ROOT / "migrations"
I18N = PROJECT_ROOT / "app" / "presentation" / "desktop" / "i18n"
THEMES = PROJECT_ROOT / "app" / "presentation" / "desktop" / "themes"

hiddenimports = collect_submodules("app") + [
    "alembic",
    "logging.config",
    "sqlalchemy.dialects.sqlite",
]

a = Analysis(
    [str(PROJECT_ROOT / "app" / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(MIGRATIONS), "migrations"),
        (str(I18N), "app/presentation/desktop/i18n"),
        (str(THEMES), "app/presentation/desktop/themes"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ResaleManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ResaleManager",
)
