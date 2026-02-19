# Plan: Single EXE with MCP stdio Mode Support

**Date:** 2026-02-10
**Type:** Plan (P16)
**Goal:** Add `--mcp-stdio` command-line option to trilobase.exe for native MCP stdio support without Node.js dependency

---

## Current Situation

### Current MCP Setup (SSE + mcp-remote)
```
User Environment
├─ trilobase.exe (GUI) → MCP server on http://localhost:8081/sse
├─ Claude Desktop → npx mcp-remote → http://localhost:8081/sse
└─ Dependencies: Python (bundled), Node.js (required for mcp-remote)
```

**Issues:**
- ❌ Requires Node.js installation (similar to requiring Python)
- ❌ GUI must be manually started before Claude Desktop
- ❌ mcp-remote adds extra proxy layer
- ❌ Not simpler than stdio approach

---

## Proposed Solution

### Single EXE with Dual Mode
```bash
# GUI Mode (default)
trilobase.exe
# or
trilobase.exe --gui

# MCP stdio Mode (for Claude Desktop)
trilobase.exe --mcp-stdio
```

### New Architecture
```
User Environment (Option A: MCP stdio)
├─ trilobase.exe --mcp-stdio ← spawned by Claude Desktop
└─ Dependencies: None! (Python bundled in exe)

User Environment (Option B: GUI + MCP SSE)
├─ trilobase.exe (GUI + embedded MCP SSE server)
└─ Dependencies: None (if user wants GUI)
```

**Benefits:**
- ✅ No Node.js required (for stdio mode)
- ✅ No manual GUI startup (for stdio mode)
- ✅ Auto-spawned by Claude Desktop
- ✅ Single exe file (simpler distribution)
- ✅ Users can choose: GUI mode OR stdio mode

---

## Implementation Plan

### Phase 1: Code Changes

#### 1.1 Modify `scripts/gui.py`

**Add argparse for command-line options:**
```python
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Trilobase SCODA Viewer")
    parser.add_argument('--mcp-stdio', action='store_true',
                       help='Run MCP server in stdio mode')
    parser.add_argument('--gui', action='store_true', default=False,
                       help='Run GUI mode (default)')

    args = parser.parse_args()

    if args.mcp_stdio:
        # Run MCP stdio mode
        run_mcp_stdio_mode()
    else:
        # Run GUI mode (default)
        run_gui_mode()
```

**MCP stdio mode handler:**
```python
def run_mcp_stdio_mode():
    """Run MCP server in stdio mode."""
    try:
        import asyncio
        import sys
        import os

        # Add parent directory to sys.path for mcp_server import
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        from mcp_server import run_stdio
        asyncio.run(run_stdio())

    except Exception as e:
        import traceback
        print("MCP stdio Error:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
```

**GUI mode handler (with console hiding on Windows):**
```python
def run_gui_mode():
    """Run GUI mode."""
    try:
        # Hide console window in frozen mode (Windows only)
        if getattr(sys, 'frozen', False) and sys.platform == 'win32':
            import ctypes
            # SW_HIDE = 0
            ctypes.windll.user32.ShowWindow(
                ctypes.windll.kernel32.GetConsoleWindow(), 0
            )

        gui = TrilobaseGUI()
        gui.run()

    except Exception as e:
        import traceback
        print("GUI Error:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
```

#### 1.2 Modify `trilobase.spec`

**Change console mode to True:**
```python
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
    console=True,  # ← Changed from False (stdio needs stdin/stdout)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
```

**Note:** `console=True` means:
- **stdio mode**: Console window visible (required for stdin/stdout)
- **GUI mode**: Console window hidden by code (via `ctypes.windll.user32.ShowWindow`)

---

### Phase 2: Testing

#### 2.1 Test stdio Mode

**Build exe:**
```bash
pyinstaller trilobase.spec
```

**Test manual stdio invocation:**
```bash
# Should wait for stdin (MCP protocol)
dist/trilobase.exe --mcp-stdio

# Test with basic MCP client
python test_mcp_basic.py --executable dist/trilobase.exe
```

#### 2.2 Test Claude Desktop Integration

**Update `claude_desktop_config.json`:**
```json
{
  "mcpServers": {
    "trilobase": {
      "command": "C:\\path\\to\\trilobase.exe",
      "args": ["--mcp-stdio"]
    }
  }
}
```

**Test in Claude Desktop:**
1. Close Claude Desktop
2. Update config file
3. Restart Claude Desktop
4. Check MCP tools are available (should see 14 tools)
5. Test queries: "Show me the taxonomy tree", "Search for Paradoxides"

#### 2.3 Test GUI Mode

**Test default GUI launch:**
```bash
# Should open GUI (no console window)
dist/trilobase.exe
```

**Test explicit GUI flag:**
```bash
# Should open GUI (no console window)
dist/trilobase.exe --gui
```

---

### Phase 3: Documentation Updates

#### 3.1 Update `docs/MCP_GUIDE.md`

**Add new "Method 1" (stdio with single exe):**
```markdown
### Method 1: stdio Mode with Single EXE (Recommended) ⭐

**장점:**
- ✅ Python 설치 불필요
- ✅ Node.js 설치 불필요
- ✅ 자동 실행 (Claude Desktop이 spawn)
- ✅ GUI 불필요
- ✅ 가장 간단한 설정

**설정:**

1. **실행 파일 다운로드**
   - [Releases](https://github.com/yourname/trilobase/releases)에서 다운로드

2. **Claude Desktop 설정**

   파일: `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

   ```json
   {
     "mcpServers": {
       "trilobase": {
         "command": "C:\\path\\to\\trilobase.exe",
         "args": ["--mcp-stdio"]
       }
     }
   }
   ```

3. **Claude Desktop 재시작**

**완료!** 이제 Claude Desktop에서 바로 사용 가능합니다.
```

**Demote existing methods:**
- Method 2: SSE with GUI (GUI 사용자용)
- Method 3: stdio with Python source (개발자용)

#### 3.2 Update `README.md`

**Quick Start 섹션 업데이트:**
```markdown
## Quick Start

### For Claude Desktop Users (MCP)

1. Download `trilobase.exe`
2. Add to Claude Desktop config:
   ```json
   {
     "mcpServers": {
       "trilobase": {
         "command": "C:\\path\\to\\trilobase.exe",
         "args": ["--mcp-stdio"]
       }
     }
   }
   ```
3. Restart Claude Desktop

**No Python, No Node.js required!** ✨

### For GUI Users

Double-click `trilobase.exe` to open the GUI.
```

#### 3.3 Update `HANDOVER.md`

**Add to "Completed Work" section:**
```markdown
### Phase 24 완료: Single EXE MCP stdio Support (2026-02-10)
- `trilobase.exe --mcp-stdio` 옵션 추가
- Node.js 의존성 제거 (stdio 모드 사용 시)
- GUI와 MCP stdio를 단일 exe로 통합
- Claude Desktop 직접 spawn 지원
```

---

### Phase 4: Deployment

#### 4.1 Build Release

```bash
# Clean previous builds
rm -rf build dist

# Build new version
pyinstaller trilobase.spec

# Test
dist/trilobase.exe --mcp-stdio
dist/trilobase.exe --gui
```

#### 4.2 Create GitHub Release

**Tag:** `v1.2.0`
**Title:** "Single EXE with MCP stdio Support"

**Release Notes:**
```markdown
## What's New

### MCP stdio Mode (No Node.js Required!) 🎉

You can now use Trilobase with Claude Desktop without installing Node.js!

**Before (v1.1.0):**
- Required: Python (bundled) + Node.js (for mcp-remote)
- Setup: GUI + mcp-remote proxy

**After (v1.2.0):**
- Required: Nothing! (Python bundled in exe)
- Setup: Just one config line

**Usage:**

```json
{
  "mcpServers": {
    "trilobase": {
      "command": "C:\\path\\to\\trilobase.exe",
      "args": ["--mcp-stdio"]
    }
  }
}
```

### GUI Mode Still Works

Double-click `trilobase.exe` to use the GUI as before.

## Downloads

- Windows: `trilobase.exe`
- Linux: `trilobase` (coming soon)

## Full Changelog

- feat: Add `--mcp-stdio` command-line option
- feat: Single exe supports both GUI and MCP stdio modes
- fix: Console window hidden in GUI mode on Windows
- docs: Update MCP_GUIDE.md with new stdio setup
- docs: Simplify README quick start
```

---

## Risks and Mitigations

### Risk 1: Console Window Visibility

**Issue:** `console=True` in PyInstaller might show console briefly in GUI mode

**Mitigation:**
- Hide console window programmatically via `ctypes` on Windows
- Test on multiple Windows versions (10, 11)
- If unavoidable, document as known limitation

### Risk 2: Backwards Compatibility

**Issue:** Users with existing SSE + mcp-remote setup might be confused

**Mitigation:**
- Keep SSE mode fully functional
- Mark as "Method 2" in docs (not deprecated, just not recommended)
- Clear migration guide in release notes

### Risk 3: stdio Communication Issues

**Issue:** stdio mode might have buffering or encoding issues on Windows

**Mitigation:**
- Test thoroughly with `test_mcp_basic.py`
- Test with actual Claude Desktop on Windows
- Add troubleshooting section in docs

---

## Success Criteria

- [ ] `trilobase.exe --mcp-stdio` runs without errors
- [ ] Claude Desktop successfully spawns and communicates with exe
- [ ] All 14 MCP tools work in stdio mode
- [ ] `trilobase.exe` (GUI) opens without console window
- [ ] No Node.js required for stdio mode
- [ ] Documentation updated (MCP_GUIDE.md, README.md, HANDOVER.md)
- [ ] GitHub release created with clear instructions

---

## Timeline

- **Phase 1 (Code):** 30 minutes
- **Phase 2 (Testing):** 1 hour
- **Phase 3 (Docs):** 30 minutes
- **Phase 4 (Deploy):** 20 minutes

**Total:** ~2.5 hours

---

## Next Steps After Implementation

1. Monitor user feedback on GitHub Issues
2. Consider adding:
   - `--version` flag
   - `--help` with ASCII art logo
   - Configuration file support (`trilobase.yaml`)
3. Linux/macOS builds with same stdio support

---

## Open Questions

1. **Should we deprecate SSE + mcp-remote setup?**
   - **Answer:** No, keep it for users who want GUI integration
   - Mark stdio as "recommended" but don't remove SSE

2. **Should GUI mode also work without hiding console?**
   - **Answer:** Hide console for better UX, but keep it as fallback if hiding fails

3. **Should we add a `--mcp-sse` flag for consistency?**
   - **Answer:** Not necessary, GUI already starts SSE server
   - Keep it simple: stdio = CLI flag, SSE = GUI embedded

---

## Approval Needed

- [ ] User approves this plan
- [ ] Ready to proceed with implementation

---

**End of Plan**
