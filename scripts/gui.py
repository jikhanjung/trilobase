#!/usr/bin/env python3
"""
Trilobase GUI Control Panel

Provides a simple graphical interface to control the Flask server.
"""

import tkinter as tk
from tkinter import messagebox
import threading
import webbrowser
import os
import sys
import time


class TrilobaseGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Trilobase SCODA Viewer")
        self.root.geometry("420x320")
        self.root.resizable(False, False)

        # Server state
        self.server_thread = None
        self.server_running = False
        self.flask_app = None
        self.port = 8080

        # Determine DB path
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller bundle
            self.base_path = sys._MEIPASS
        else:
            # Running as normal Python script
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        os.chdir(self.base_path)

        # Check if DB exists
        self.db_path = os.path.join(self.base_path, 'trilobase.db')
        self.db_exists = os.path.exists(self.db_path)

        self._create_widgets()
        self._update_status()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

    def _create_widgets(self):
        """Create all GUI widgets."""
        # Header
        header_frame = tk.Frame(self.root, bg="#2196F3", height=50)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        header = tk.Label(header_frame, text="Trilobase SCODA Viewer",
                         font=("Arial", 14, "bold"), bg="#2196F3", fg="white")
        header.pack(pady=12)

        # Main content frame
        content = tk.Frame(self.root)
        content.pack(pady=20, padx=20, fill="both", expand=True)

        # Info section
        info_frame = tk.LabelFrame(content, text="Information", padx=10, pady=10)
        info_frame.pack(fill="x", pady=(0, 15))

        # Database
        db_row = tk.Frame(info_frame)
        db_row.pack(fill="x", pady=3)
        tk.Label(db_row, text="Database:", width=12, anchor="w").pack(side="left")
        db_name = os.path.basename(self.db_path)
        db_color = "blue" if self.db_exists else "red"
        db_text = db_name if self.db_exists else f"{db_name} (not found)"
        self.db_label = tk.Label(db_row, text=db_text, anchor="w", fg=db_color)
        self.db_label.pack(side="left", fill="x", expand=True)

        # Status
        status_row = tk.Frame(info_frame)
        status_row.pack(fill="x", pady=3)
        tk.Label(status_row, text="Status:", width=12, anchor="w").pack(side="left")
        self.status_label = tk.Label(status_row, text="● Stopped", anchor="w", fg="red")
        self.status_label.pack(side="left", fill="x", expand=True)

        # URL
        url_row = tk.Frame(info_frame)
        url_row.pack(fill="x", pady=3)
        tk.Label(url_row, text="URL:", width=12, anchor="w").pack(side="left")
        self.url_label = tk.Label(url_row, text=f"http://localhost:{self.port}",
                                  anchor="w", fg="gray", cursor="hand2")
        self.url_label.pack(side="left", fill="x", expand=True)
        self.url_label.bind("<Button-1>", lambda e: self.open_browser())

        # Control buttons
        control_frame = tk.LabelFrame(content, text="Controls", padx=10, pady=10)
        control_frame.pack(fill="both", expand=True)

        # Start/Stop row
        server_row = tk.Frame(control_frame)
        server_row.pack(pady=5)

        self.start_btn = tk.Button(server_row, text="▶ Start Server", width=15,
                                   command=self.start_server, bg="#4CAF50", fg="white",
                                   relief="raised", bd=2)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = tk.Button(server_row, text="■ Stop Server", width=15,
                                  command=self.stop_server, state="disabled",
                                  bg="#f44336", fg="white", relief="raised", bd=2)
        self.stop_btn.pack(side="left", padx=5)

        # Open browser button
        self.browser_btn = tk.Button(control_frame, text="🌐 Open in Browser", width=32,
                                     command=self.open_browser, state="disabled",
                                     relief="raised", bd=2)
        self.browser_btn.pack(pady=5)

        # Quit button
        quit_btn = tk.Button(control_frame, text="Exit", width=32,
                            command=self.quit_app, bg="#9E9E9E", fg="white",
                            relief="raised", bd=2)
        quit_btn.pack(pady=5)

    def start_server(self):
        """Start Flask server in background thread."""
        if self.server_running:
            return

        if not self.db_exists:
            messagebox.showerror("Database Error",
                               f"Database file not found:\n{self.db_path}\n\n"
                               "Please ensure trilobase.db is in the same directory as the executable.")
            return

        try:
            # Import Flask app
            from app import app
            self.flask_app = app
        except ImportError as e:
            messagebox.showerror("Import Error",
                               f"Could not import Flask app:\n{e}\n\n"
                               "Please ensure app.py is available.")
            return

        self.server_running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        # Auto-open browser after 1.5 seconds
        self.root.after(1500, self.open_browser)

        self._update_status()

    def stop_server(self):
        """Stop Flask server."""
        if not self.server_running:
            return

        # Note: Flask in thread cannot be cleanly stopped
        # We mark it as stopped and suggest restart
        self.server_running = False
        self._update_status()

        messagebox.showinfo("Server Stopped",
                          "Server marked as stopped.\n\n"
                          "Note: The server thread may still be active.\n"
                          "Please restart the application to fully stop the server.")

    def _run_server(self):
        """Run Flask server (called in thread)."""
        try:
            self.flask_app.run(debug=False, host='127.0.0.1', port=self.port, use_reloader=False)
        except OSError as e:
            self.server_running = False
            self.root.after(0, lambda: messagebox.showerror("Server Error",
                                                           f"Could not start server:\n{e}\n\n"
                                                           f"Port {self.port} may already be in use."))
            self.root.after(0, self._update_status)
        except Exception as e:
            self.server_running = False
            self.root.after(0, lambda: messagebox.showerror("Server Error",
                                                           f"Server error:\n{e}"))
            self.root.after(0, self._update_status)

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
        if self.server_running:
            result = messagebox.askyesno("Quit",
                                        "Server is still running.\n\n"
                                        "Are you sure you want to quit?")
            if not result:
                return

        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def _update_status(self):
        """Update UI based on server status."""
        if self.server_running:
            self.status_label.config(text="● Running", fg="green")
            self.start_btn.config(state="disabled", relief="sunken")
            self.stop_btn.config(state="normal", relief="raised")
            self.browser_btn.config(state="normal")
            self.url_label.config(fg="blue")
        else:
            self.status_label.config(text="● Stopped", fg="red")
            self.start_btn.config(state="normal" if self.db_exists else "disabled",
                                 relief="raised")
            self.stop_btn.config(state="disabled", relief="sunken")
            self.browser_btn.config(state="disabled")
            self.url_label.config(fg="gray")

    def run(self):
        """Start GUI main loop."""
        self.root.mainloop()


def main():
    """Main entry point."""
    try:
        gui = TrilobaseGUI()
        gui.run()
    except Exception as e:
        # Fallback error display if GUI fails
        import traceback
        print("GUI Error:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
