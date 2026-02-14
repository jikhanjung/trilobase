#!/usr/bin/env python3
"""
Build standalone executable for SCODA Desktop using PyInstaller

Usage:
    python scripts/build.py [--clean] [--no-scoda]

Options:
    --clean      Remove previous build artifacts before building
    --no-scoda   Skip .scoda package creation after build
"""

import subprocess
import sys
import shutil
import os
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent


def check_pyinstaller():
    """Check if PyInstaller is installed, install if not."""
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__} found")
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✓ PyInstaller installed")
            return True
        except subprocess.CalledProcessError:
            print("✗ Failed to install PyInstaller", file=sys.stderr)
            return False


def clean_build():
    """Remove previous build artifacts."""
    print("\nCleaning previous builds...")
    for path in ['build', 'dist']:
        if os.path.exists(path):
            print(f"  Removing {path}/")
            shutil.rmtree(path)
    print("✓ Clean complete")


def build_executable():
    """Run PyInstaller to build the executable."""
    print("\nBuilding SCODA Desktop standalone executable...")
    print("-" * 60)

    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'ScodaDesktop.spec'
    ]

    print(f"Running: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed with exit code {e.returncode}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("\n✗ PyInstaller not found in PATH", file=sys.stderr)
        return False


def create_scoda_packages():
    """Create .scoda packages in dist/ by calling the dedicated scripts."""
    print("\nCreating .scoda packages...")

    for script, db_name in [
        ('create_scoda.py', 'trilobase.db'),
        ('create_paleocore_scoda.py', 'paleocore.db'),
    ]:
        if not Path(db_name).exists():
            scoda_name = db_name.replace('.db', '.scoda')
            print(f"  Skipping {scoda_name} ({db_name} not found)")
            continue

        scoda_output = str(Path('dist') / db_name.replace('.db', '.scoda'))
        script_path = str(SCRIPTS_DIR / script)
        cmd = [sys.executable, script_path, '--output', scoda_output]

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"✗ {script} failed with exit code {e.returncode}", file=sys.stderr)


def print_results(skip_scoda):
    """Print build results and next steps."""
    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)

    exe_name = 'ScodaDesktop.exe' if sys.platform == 'win32' else 'ScodaDesktop'
    exe_path = Path('dist') / exe_name

    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n✓ Executable created: {exe_path}")
        print(f"  Size: {size_mb:.1f} MB")

        if not skip_scoda:
            create_scoda_packages()

        print("\nNext steps:")
        print(f"  1. Test: ./{exe_path}")
        print(f"  2. Distribute: Copy dist/{exe_name} + dist/trilobase.scoda + dist/paleocore.scoda to users")
    else:
        print(f"\n✗ Expected executable not found: {exe_path}", file=sys.stderr)
        return False

    return True


def main():
    print("=" * 60)
    print("SCODA Desktop Standalone Executable Builder")
    print("=" * 60)

    # Check command line arguments
    if '--clean' in sys.argv:
        clean_build()

    skip_scoda = '--no-scoda' in sys.argv

    # Check PyInstaller
    if not check_pyinstaller():
        sys.exit(1)

    # Check spec file exists
    if not os.path.exists('ScodaDesktop.spec'):
        print("\n✗ ScodaDesktop.spec not found", file=sys.stderr)
        print("Run this script from the project root directory", file=sys.stderr)
        sys.exit(1)

    # Build
    if not build_executable():
        sys.exit(1)

    # Print results
    if not print_results(skip_scoda):
        sys.exit(1)

    print("\n" + "=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user")
        sys.exit(1)
