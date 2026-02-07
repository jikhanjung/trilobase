# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Trilobase standalone executable

Build with: pyinstaller trilobase.spec
"""

block_cipher = None

a = Analysis(
    ['scripts/serve.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app.py', '.'),
        ('templates', 'templates'),
        ('static', 'static'),
        ('trilobase.db', '.'),
    ],
    hiddenimports=[
        'flask',
        'sqlite3',
        'json',
        'webbrowser',
        'threading',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    name='trilobase',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console for server logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if available
)
