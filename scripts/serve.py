#!/usr/bin/env python3
"""
Trilobase SCODA Viewer Launcher

Starts the Flask web server and automatically opens the default browser.
"""

import webbrowser
from threading import Timer
import sys
import os


def open_browser():
    """Open default browser after a short delay."""
    webbrowser.open('http://localhost:8080')


def main():
    print("=" * 60)
    print("Trilobase SCODA Viewer")
    print("=" * 60)
    print("Server running at: http://localhost:8080")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    # Open browser after 1.5 seconds
    Timer(1.5, open_browser).start()

    # Import and run Flask app
    # Use relative import to work when frozen by PyInstaller
    try:
        # Change to script directory to find app.py
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller bundle
            base_path = sys._MEIPASS
        else:
            # Running as normal Python script
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        os.chdir(base_path)

        from app import app
        app.run(debug=False, host='127.0.0.1', port=8080, use_reloader=False)
    except ImportError as e:
        print(f"Error: Could not import Flask app: {e}", file=sys.stderr)
        print("Make sure app.py is in the same directory.", file=sys.stderr)
        input("\nPress Enter to exit...")
        sys.exit(1)
    except OSError as e:
        print(f"Error: Could not start server: {e}", file=sys.stderr)
        print("Port 8080 might already be in use.", file=sys.stderr)
        input("\nPress Enter to exit...")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nShutting down Trilobase...")
        sys.exit(0)
