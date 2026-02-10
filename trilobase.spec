# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Trilobase standalone executable

Build with: pyinstaller trilobase.spec
"""

block_cipher = None

a = Analysis(
    ['scripts/gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app.py', '.'),
        ('mcp_server.py', '.'),
        ('templates', 'templates'),
        ('static', 'static'),
        ('trilobase.db', '.'),
    ],
    hiddenimports=[
        'flask',
        'asgiref',
        'asgiref.wsgi',
        'mcp',
        'mcp.server',
        'mcp.server.stdio',
        'mcp.server.sse',
        'starlette',
        'starlette.applications',
        'starlette.routing',
        'starlette.responses',
        'uvicorn',
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
    console=True,   # Required for --mcp-stdio mode (stdin/stdout). GUI mode hides console via ctypes.
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if available
)
