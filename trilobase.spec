# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Trilobase standalone executables

Two executables are produced:
  trilobase.exe     - GUI viewer (console=False, no console blocking)
  trilobase_mcp.exe - MCP stdio server (console=True, for Claude Desktop)

Build with: pyinstaller trilobase.spec
"""

block_cipher = None

# ---------------------------------------------------------------------------
# trilobase.exe  (GUI viewer)
# ---------------------------------------------------------------------------
a = Analysis(
    ['scripts/gui.py'],
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
        'asgiref',
        'asgiref.wsgi',
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
    console=False,  # GUI subsystem: no console window, no blocking from PowerShell/cmd
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# ---------------------------------------------------------------------------
# trilobase_mcp.exe  (MCP stdio server for Claude Desktop)
# ---------------------------------------------------------------------------
mcp_a = Analysis(
    ['mcp_server.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('trilobase.db', '.'),
    ],
    hiddenimports=[
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

mcp_pyz = PYZ(mcp_a.pure, mcp_a.zipped_data, cipher=block_cipher)

mcp_exe = EXE(
    mcp_pyz,
    mcp_a.scripts,
    mcp_a.binaries,
    mcp_a.zipfiles,
    mcp_a.datas,
    [],
    name='trilobase_mcp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Required for stdin/stdout MCP stdio communication
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
