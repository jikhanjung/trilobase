# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SCODA Desktop standalone executables

Two executables are produced:
  ScodaDesktop.exe     - GUI viewer (console=False, no console blocking)
  ScodaDesktop_mcp.exe - MCP stdio server (console=True, for Claude Desktop)

Build with: pyinstaller ScodaDesktop.spec
"""

block_cipher = None

# ---------------------------------------------------------------------------
# ScodaDesktop.exe  (GUI viewer)
# ---------------------------------------------------------------------------
a = Analysis(
    ['scripts/gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app.py', '.'),
        ('scoda_package.py', '.'),
        ('templates', 'templates'),
        ('static', 'static'),
        ('spa', 'spa'),
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
    name='ScodaDesktop',
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
# ScodaDesktop_mcp.exe  (MCP stdio server for Claude Desktop)
# ---------------------------------------------------------------------------
mcp_a = Analysis(
    ['mcp_server.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('scoda_package.py', '.'),
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
    name='ScodaDesktop_mcp',
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
