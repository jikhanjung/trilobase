#!/usr/bin/env python3
"""
SCODA Desktop — GUI Control Panel

Provides a simple graphical interface to control the Flask server.
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
import webbrowser
import os
import sys
import time
import subprocess

# Ensure parent directory is in path for scoda_package import
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
import scoda_package


class LogRedirector:
    """Redirect stdout/stderr to GUI log viewer."""
    def __init__(self, callback):
        self.callback = callback

    def write(self, text):
        if text.strip():
            self.callback(text.strip())

    def flush(self):
        pass

    def isatty(self):
        """Return False to indicate this is not a TTY (required by uvicorn logger)."""
        return False

    def fileno(self):
        """Return a dummy file descriptor (required by some logging handlers)."""
        return -1


class TrilobaseGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SCODA Desktop")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        self.root.minsize(600, 400)

        # Flask server state
        self.server_process = None  # For subprocess mode
        self.server_thread = None   # For threaded mode (frozen)
        self.flask_app = None       # For threaded mode
        self.original_stdout = None # For restoring stdout after redirect
        self.original_stderr = None # For restoring stderr after redirect
        self.log_reader_thread = None
        self.server_running = False
        self.port = 8080

        # MCP server state
        self.mcp_process = None     # MCP subprocess
        self.mcp_thread = None      # MCP thread (frozen mode)
        self.mcp_log_reader_thread = None
        self.mcp_running = False
        self.mcp_port = 8081

        # Determine base path
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        os.chdir(self.base_path)

        # Use scoda_package for DB path resolution
        self.scoda_info = scoda_package.get_scoda_info()
        self.canonical_db_path = self.scoda_info['canonical_path']
        self.overlay_db_path = self.scoda_info['overlay_path']
        self.db_exists = self.scoda_info['canonical_exists']

        self._create_widgets()
        self._update_status()

        # Initial log messages
        self._append_log("SCODA Desktop initialized")
        if self.scoda_info['source_type'] == 'scoda':
            self._append_log(f"Loaded: {os.path.basename(self.scoda_info['scoda_path'])} (v{self.scoda_info.get('version', '?')})")
        else:
            self._append_log(f"Loaded: {os.path.basename(self.canonical_db_path)}")
        # Log paleocore dependency
        if self.scoda_info.get('paleocore_exists'):
            if self.scoda_info.get('paleocore_source_type') == 'scoda':
                pc_name = os.path.basename(self.scoda_info.get('paleocore_scoda_path', 'paleocore.scoda'))
                pc_ver = self.scoda_info.get('paleocore_version', '?')
                self._append_log(f"  \u2514 dependency: {pc_name} (v{pc_ver})")
            else:
                self._append_log(f"  \u2514 dependency: paleocore.db")
        self._append_log(f"Overlay: {os.path.basename(self.overlay_db_path)}")
        if not self.db_exists:
            self._append_log("WARNING: Data source not found!", "WARNING")

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

    def _create_widgets(self):
        """Create all GUI widgets."""
        # Header
        header_frame = tk.Frame(self.root, bg="#2196F3", height=50)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        header = tk.Label(header_frame, text="SCODA Desktop",
                         font=("Arial", 14, "bold"), bg="#2196F3", fg="white")
        header.pack(pady=12)

        # Top section (Info + Controls side by side)
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=10)

        # Left: Info section
        info_frame = tk.LabelFrame(top_frame, text="Information", padx=10, pady=10)
        info_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # Data source (Package or DB)
        db_row = tk.Frame(info_frame)
        db_row.pack(fill="x", pady=3)
        if self.scoda_info['source_type'] == 'scoda':
            tk.Label(db_row, text="Packages:", width=10, anchor="w").pack(side="left")
            scoda_name = os.path.basename(self.scoda_info['scoda_path'])
            db_text = f"{scoda_name} (v{self.scoda_info.get('version', '?')})"
            db_color = "blue" if self.db_exists else "red"
        else:
            tk.Label(db_row, text="Canonical:", width=10, anchor="w").pack(side="left")
            db_name = os.path.basename(self.canonical_db_path)
            db_color = "blue" if self.db_exists else "red"
            db_text = db_name if self.db_exists else f"{db_name} (not found)"
        self.db_label = tk.Label(db_row, text=db_text, anchor="w", fg=db_color)
        self.db_label.pack(side="left", fill="x", expand=True)

        # PaleoCore dependency row (if loaded)
        if self.scoda_info.get('paleocore_exists'):
            dep_row = tk.Frame(info_frame)
            dep_row.pack(fill="x", pady=0)
            tk.Label(dep_row, text="", width=10, anchor="w").pack(side="left")
            if self.scoda_info.get('paleocore_source_type') == 'scoda':
                pc_name = os.path.basename(self.scoda_info.get('paleocore_scoda_path', 'paleocore.scoda'))
                pc_ver = self.scoda_info.get('paleocore_version', '?')
                dep_text = f"\u2514 {pc_name} (v{pc_ver}, dependency)"
            else:
                dep_text = "\u2514 paleocore.db (dependency)"
            tk.Label(dep_row, text=dep_text, anchor="w", fg="gray").pack(side="left", fill="x", expand=True)

        # Overlay Database
        overlay_row = tk.Frame(info_frame)
        overlay_row.pack(fill="x", pady=3)
        tk.Label(overlay_row, text="Overlay:", width=10, anchor="w").pack(side="left")
        overlay_name = os.path.basename(self.overlay_db_path)
        overlay_exists = os.path.exists(self.overlay_db_path)
        overlay_text = overlay_name if overlay_exists else f"{overlay_name} (auto-created)"
        overlay_color = "green" if overlay_exists else "gray"
        self.overlay_label = tk.Label(overlay_row, text=overlay_text, anchor="w", fg=overlay_color)
        self.overlay_label.pack(side="left", fill="x", expand=True)

        # Flask Status
        flask_status_row = tk.Frame(info_frame)
        flask_status_row.pack(fill="x", pady=3)
        tk.Label(flask_status_row, text="Flask:", width=10, anchor="w").pack(side="left")
        self.status_label = tk.Label(flask_status_row, text="● Stopped", anchor="w", fg="red")
        self.status_label.pack(side="left", fill="x", expand=True)

        # Flask URL
        url_row = tk.Frame(info_frame)
        url_row.pack(fill="x", pady=3)
        tk.Label(url_row, text="Flask URL:", width=10, anchor="w").pack(side="left")
        self.url_label = tk.Label(url_row, text=f"http://localhost:{self.port}",
                                  anchor="w", fg="gray", cursor="hand2")
        self.url_label.pack(side="left", fill="x", expand=True)
        self.url_label.bind("<Button-1>", lambda e: self.open_browser())

        # Right: Control section
        control_frame = tk.LabelFrame(top_frame, text="Controls", padx=10, pady=10)
        control_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # Flask Start/Stop row
        server_row = tk.Frame(control_frame)
        server_row.pack(pady=3)

        self.start_btn = tk.Button(server_row, text="▶ Start Flask", width=12,
                                   command=self.start_server, bg="#4CAF50", fg="white",
                                   relief="raised", bd=2)
        self.start_btn.pack(side="left", padx=2)

        self.stop_btn = tk.Button(server_row, text="■ Stop Flask", width=12,
                                  command=self.stop_server, state="disabled",
                                  bg="#f44336", fg="white", relief="raised", bd=2)
        self.stop_btn.pack(side="left", padx=2)

        # Open browser button
        self.browser_btn = tk.Button(control_frame, text="🌐 Open Browser", width=26,
                                     command=self.open_browser, state="disabled",
                                     relief="raised", bd=2)
        self.browser_btn.pack(pady=3)

        # Clear log button
        self.clear_log_btn = tk.Button(control_frame, text="📄 Clear Log", width=26,
                                       command=self.clear_log,
                                       relief="raised", bd=2)
        self.clear_log_btn.pack(pady=3)

        # Quit button
        quit_btn = tk.Button(control_frame, text="Exit", width=26,
                            command=self.quit_app, bg="#9E9E9E", fg="white",
                            relief="raised", bd=2)
        quit_btn.pack(pady=3)

        # Bottom: Log Viewer
        log_frame = tk.LabelFrame(self.root, text="Server Log", padx=5, pady=5)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Scrollbar
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        # Text widget (read-only)
        self.log_text = tk.Text(
            log_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            state="disabled",
            height=20,
            font=("Courier", 9),
            bg="#f5f5f5",
            fg="#333333"
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Color tags for log levels
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("INFO", foreground="blue")
        self.log_text.tag_config("SUCCESS", foreground="green")

    def start_server(self):
        """Start Flask server."""
        if self.server_running:
            return

        if not self.db_exists:
            self._append_log("ERROR: Canonical database not found!", "ERROR")
            messagebox.showerror("Database Error",
                               f"Database file not found:\n{self.canonical_db_path}\n\n"
                               "Please ensure trilobase.db is available.")
            return

        try:
            # In frozen mode (PyInstaller), run Flask in thread with stdout redirect
            # In dev mode, run as subprocess for better log capture
            if getattr(sys, 'frozen', False):
                self._start_server_threaded()
            else:
                self._start_server_subprocess()

            self.server_running = True
            self._update_status()

            # Auto-open browser after 1.5 seconds
            self.root.after(1500, self.open_browser)

        except Exception as e:
            self._append_log(f"ERROR: Failed to start server: {e}", "ERROR")
            messagebox.showerror("Server Error", f"Could not start server:\n{e}")
            return

    def _start_server_threaded(self):
        """Start Flask server in thread (for frozen/PyInstaller mode)."""
        self._append_log("Starting Flask server (threaded mode)...", "INFO")

        # Import Flask app
        try:
            from app import app
            self.flask_app = app
        except ImportError as e:
            raise Exception(f"Could not import Flask app: {e}")

        # Redirect stdout/stderr to GUI
        # Both stdout and stderr use auto-detection (tag=None) for proper color coding
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = LogRedirector(lambda msg: self.root.after(0, self._append_log, msg))
        sys.stderr = LogRedirector(lambda msg: self.root.after(0, self._append_log, msg))

        # Start Flask in thread
        self.server_thread = threading.Thread(target=self._run_flask_app, daemon=True)
        self.server_thread.start()

        self._append_log("Flask server started in thread", "INFO")

    def _start_server_subprocess(self):
        """Start Flask server as subprocess (for development mode)."""
        python_exe = sys.executable
        app_py = os.path.join(self.base_path, 'app.py')

        if not os.path.exists(app_py):
            raise FileNotFoundError(f"app.py not found at {app_py}")

        self._append_log(f"Starting Flask server (subprocess mode): {python_exe}", "INFO")

        # Start Flask as subprocess
        self.server_process = subprocess.Popen(
            [python_exe, app_py],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            cwd=self.base_path
        )

        # Start log reader thread
        self.log_reader_thread = threading.Thread(
            target=self._read_server_logs,
            daemon=True
        )
        self.log_reader_thread.start()

    def _start_mcp_server(self):
        """Start MCP server (SSE mode)."""
        # Always use subprocess in development mode for better stability
        # Only use threading in frozen (PyInstaller) mode
        if getattr(sys, 'frozen', False):
            self._start_mcp_threaded()
        else:
            self._start_mcp_subprocess()

    def _start_mcp_threaded(self):
        """Start MCP server in thread (for frozen/PyInstaller mode)."""
        self._append_log("Starting MCP server (threaded mode)...", "INFO")

        # Add base path to sys.path for imports
        if self.base_path not in sys.path:
            sys.path.insert(0, self.base_path)

        # Import mcp_server module
        try:
            import mcp_server
        except ImportError as e:
            raise Exception(f"Could not import MCP server: {e}")

        # Start MCP in thread
        def run_mcp():
            try:
                mcp_server.run_sse(host='localhost', port=self.mcp_port)
            except Exception as e:
                self.root.after(0, self._append_log, f"MCP ERROR: {e}", "ERROR")
                self.mcp_running = False
                self.root.after(0, self._update_status)

        self.mcp_thread = threading.Thread(target=run_mcp, daemon=True)
        self.mcp_thread.start()

        self._append_log(f"MCP server started on port {self.mcp_port}", "INFO")

    def _start_mcp_subprocess(self):
        """Start MCP server as subprocess (for development mode)."""
        python_exe = sys.executable
        mcp_py = os.path.join(self.base_path, 'mcp_server.py')

        if not os.path.exists(mcp_py):
            raise FileNotFoundError(f"mcp_server.py not found at {mcp_py}")

        self._append_log(f"Starting MCP server (subprocess mode, port {self.mcp_port})...", "INFO")

        # Start MCP as subprocess
        self.mcp_process = subprocess.Popen(
            [python_exe, mcp_py, '--mode', 'sse', '--port', str(self.mcp_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            cwd=self.base_path
        )

        # Start MCP log reader thread
        self.mcp_log_reader_thread = threading.Thread(
            target=self._read_mcp_logs,
            daemon=True
        )
        self.mcp_log_reader_thread.start()

    def _read_mcp_logs(self):
        """Read MCP server logs from subprocess and display in GUI."""
        while self.mcp_running and self.mcp_process:
            try:
                line = self.mcp_process.stdout.readline()
                if line:
                    # Add MCP prefix and update GUI from main thread
                    prefixed_line = f"[MCP] {line.strip()}"
                    self.root.after(0, self._append_log, prefixed_line, "INFO")
                else:
                    # EOF or process terminated
                    break
            except Exception as e:
                self._append_log(f"MCP log reader error: {e}", "ERROR")
                break

        # Check if process ended with error
        if self.mcp_process:
            returncode = self.mcp_process.poll()
            if returncode is not None and returncode != 0:
                self.root.after(0, self._append_log,
                              f"MCP server process exited with code {returncode}", "ERROR")

    def _run_flask_app(self):
        """Run Flask app with uvicorn (called in thread for frozen mode)."""
        try:
            from asgiref.wsgi import WsgiToAsgi
            import uvicorn

            # Convert Flask WSGI app to ASGI
            asgi_app = WsgiToAsgi(self.flask_app)

            # Run with uvicorn (production-ready, no dev server warning)
            uvicorn.run(
                asgi_app,
                host='127.0.0.1',
                port=self.port,
                log_level='info'
            )
        except OSError as e:
            if "Address already in use" in str(e):
                self.root.after(0, self._append_log, f"ERROR: Port {self.port} already in use", "ERROR")
                self.root.after(0, lambda: messagebox.showerror(
                    "Port Error",
                    f"Port {self.port} is already in use.\nPlease close other applications."
                ))
            else:
                self.root.after(0, self._append_log, f"ERROR: {e}", "ERROR")
            self.server_running = False
            self.root.after(0, self._update_status)
        except Exception as e:
            import traceback
            self.root.after(0, self._append_log, f"ERROR: {e}", "ERROR")
            self.root.after(0, self._append_log, traceback.format_exc(), "ERROR")
            self.server_running = False
            self.root.after(0, self._update_status)

    def stop_mcp(self):
        """Stop MCP SSE server."""
        if not self.mcp_running:
            return

        self._append_log("Stopping MCP server...", "INFO")
        self.mcp_running = False

        if self.mcp_process:
            try:
                self.mcp_process.terminate()
                self.mcp_process.wait(timeout=3)
                self._append_log("MCP server stopped successfully", "INFO")
            except subprocess.TimeoutExpired:
                self._append_log("MCP server did not stop gracefully, forcing...", "WARNING")
                self.mcp_process.kill()
                self.mcp_process.wait()
            except Exception as e:
                self._append_log(f"WARNING: Error stopping MCP server: {e}", "WARNING")
            finally:
                self.mcp_process = None

        self._update_status()

    def start_mcp(self):
        """Start MCP SSE server (optional, independent of Flask)."""
        if self.mcp_running:
            return

        try:
            self._start_mcp_server()
            self.mcp_running = True
            self._update_status()
        except Exception as e:
            self._append_log(f"ERROR: Failed to start MCP server: {e}", "ERROR")

    def stop_server(self):
        """Stop Flask server (independent of MCP)."""
        if not self.server_running:
            return

        self._append_log("Stopping Flask server...", "INFO")
        self.server_running = False

        # Terminate server process (subprocess mode)
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=3)
                self._append_log("Server stopped successfully", "INFO")
            except subprocess.TimeoutExpired:
                self._append_log("Server did not stop gracefully, forcing...", "WARNING")
                self.server_process.kill()
                self.server_process.wait()
                self._append_log("Server forcefully stopped", "WARNING")
            except Exception as e:
                self._append_log(f"WARNING: Error stopping server: {e}", "WARNING")
            finally:
                self.server_process = None

        # Thread mode (frozen) - cannot cleanly stop Flask in thread
        elif self.server_thread:
            # Restore stdout/stderr
            if hasattr(self, 'original_stdout'):
                sys.stdout = self.original_stdout
                sys.stderr = self.original_stderr
            self._append_log("Server marked as stopped (thread mode)", "WARNING")
            self._append_log("Note: Flask thread may still be active. Restart app to fully stop.", "WARNING")

        self._update_status()

    def _read_server_logs(self):
        """Read server logs from subprocess and display in GUI."""
        while self.server_running and self.server_process:
            try:
                line = self.server_process.stdout.readline()
                if line:
                    # Update GUI from main thread
                    self.root.after(0, self._append_log, line.strip())
                else:
                    # EOF or process terminated
                    break
            except Exception as e:
                self._append_log(f"Log reader error: {e}", "ERROR")
                break

        # Check if process ended with error
        if self.server_process:
            returncode = self.server_process.poll()
            if returncode is not None and returncode != 0:
                self.root.after(0, self._append_log,
                              f"Server process exited with code {returncode}", "ERROR")

    def _append_log(self, line, tag=None):
        """Append log line to text widget (called from main thread)."""
        # Ensure line is string (not bytes)
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='replace')

        self.log_text.config(state="normal")

        # Auto-detect log level if not specified
        if tag is None:
            if "ERROR" in line or "error" in line.lower() or "Exception" in line or "Traceback" in line:
                tag = "ERROR"
            elif "WARNING" in line or "warning" in line.lower():
                tag = "WARNING"
            elif "INFO" in line or "Running on" in line or "Serving Flask" in line:
                tag = "INFO"
            elif "200 GET" in line or "200 POST" in line or "GET /" in line:
                tag = "SUCCESS"
            elif "Address already in use" in line:
                tag = "ERROR"
                self.root.after(0, lambda: messagebox.showerror(
                    "Port Error",
                    f"Port {self.port} is already in use.\n"
                    "Please close other applications using this port."
                ))

        # Add timestamp
        timestamp = time.strftime("[%H:%M:%S] ")

        # Insert log with tag
        if tag:
            self.log_text.insert("end", timestamp + line + "\n", tag)
        else:
            self.log_text.insert("end", timestamp + line + "\n")

        # Auto-scroll to bottom
        self.log_text.see("end")

        self.log_text.config(state="disabled")

        # Limit log size (keep last 1000 lines)
        line_count = int(self.log_text.index('end-1c').split('.')[0])
        if line_count > 1000:
            self.log_text.config(state="normal")
            self.log_text.delete('1.0', '500.0')
            self.log_text.config(state="disabled")

    def clear_log(self):
        """Clear log viewer."""
        self.log_text.config(state="normal")
        self.log_text.delete('1.0', 'end')
        self.log_text.config(state="disabled")
        self._append_log("Log cleared")

    def open_browser(self):
        """Open default browser."""
        if not self.server_running:
            return

        try:
            webbrowser.open(f'http://localhost:{self.port}')
        except Exception as e:
            messagebox.showerror("Browser Error",
                               f"Could not open browser:\n{e}")

    def quit_app(self):
        """Quit application."""
        if self.server_running or self.mcp_running:
            result = messagebox.askyesno("Quit",
                                        "Servers are still running.\n\n"
                                        "Are you sure you want to quit?")
            if not result:
                return

            # Mark as stopped (don't call stop_server to avoid delays)
            self.server_running = False
            self.mcp_running = False

        # Clean up MCP server process
        if self.mcp_process:
            try:
                self.mcp_process.terminate()
                self.mcp_process.wait(timeout=2)
            except:
                try:
                    self.mcp_process.kill()
                except:
                    pass

        # Clean up Flask server process
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=2)
            except:
                try:
                    self.server_process.kill()
                except:
                    pass

        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def _update_status(self):
        """Update UI based on server status."""
        # Update Flask status
        if self.server_running:
            self.status_label.config(text="● Running", fg="green")
            self.url_label.config(fg="blue")
            self.browser_btn.config(state="normal")
        else:
            self.status_label.config(text="● Stopped", fg="red")
            self.url_label.config(fg="gray")
            self.browser_btn.config(state="disabled")

        # Update Flask buttons
        if self.server_running:
            self.start_btn.config(state="disabled", relief="sunken")
            self.stop_btn.config(state="normal", relief="raised")
        else:
            self.start_btn.config(state="normal" if self.db_exists else "disabled",
                                 relief="raised")
            self.stop_btn.config(state="disabled", relief="sunken")

    def run(self):
        """Start GUI main loop."""
        self.root.mainloop()


def main():
    """Main entry point."""
    try:
        gui = TrilobaseGUI()
        gui.run()
    except Exception as e:
        import traceback
        print("GUI Error:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
