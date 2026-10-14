# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the wowfish single-file executable.

Build with: uv run pyinstaller --clean --noconfirm packaging/wowfish.spec
"""

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas, binaries, hiddenimports = [], [], []
# importlib.metadata.version("wowfish") needs the dist-info inside the bundle.
datas += copy_metadata("wowfish")
datas += collect_data_files("soundcard")  # it reads bundled *.py.h headers at import
datas += [("../src/wowfish/assets", "wowfish/assets")]

a = Analysis(
    ["../src/wowfish/__main__.py"],
    pathex=["../src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PIL", "torch", "torchvision"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="wowfish",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)
