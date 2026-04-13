# studyquest.spec
# Build command:
#   Windows:  pyinstaller studyquest.spec
#   Linux:    pyinstaller studyquest.spec

import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Force-collect everything from Pillow and matplotlib
pil_datas, pil_binaries, pil_hiddenimports = collect_all('PIL')
mpl_datas, mpl_binaries, mpl_hiddenimports = collect_all('matplotlib')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[*pil_binaries, *mpl_binaries],
    datas=[
        ('icon_256.png', '.'),
        ('icon_48.png',  '.'),
        *pil_datas,
        *mpl_datas,
    ],
    hiddenimports=[
        'customtkinter',
        'matplotlib',
        'matplotlib.backends.backend_agg',
        'pandas',
        'PIL',
        'PIL.Image',
        'PIL._tkinter_finder',
        'PIL._imaging',
        'numpy',
        'tkinter',
        'tkinter.messagebox',
        '_tkinter',
        *pil_hiddenimports,
        *mpl_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook_pil.py'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='StudyQuest',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon_256.png',
)
