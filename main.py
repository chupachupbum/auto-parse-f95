"""F95zone Game Parser — tkinter GUI entry point."""

import threading
import tkinter as tk
from tkinter import ttk

from parser import parse_f95_thread
from sheets import write_game_data


class App:
    """Main application window."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("F95zone → Google Sheet Parser")
        self.root.resizable(False, False)

        # Center the window
        window_width, window_height = 520, 200
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        x = (screen_w - window_width) // 2
        y = (screen_h - window_height) // 2
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        """Build the GUI widgets."""
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)

        # URL input
        ttk.Label(frame, text="Paste f95zone thread link:").pack(anchor="w")

        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(frame, textvariable=self.url_var, width=65)
        self.url_entry.pack(fill="x", pady=(4, 12))
        self.url_entry.focus()

        # Bind Enter key
        self.url_entry.bind("<Return>", lambda e: self._on_parse())

        # Parse button
        self.parse_btn = ttk.Button(frame, text="Parse", command=self._on_parse)
        self.parse_btn.pack()

        # Status label
        self.status_var = tk.StringVar(value="Ready — paste a link and press Enter or click Parse.")
        self.status_label = ttk.Label(
            frame, textvariable=self.status_var, wraplength=480, justify="center"
        )
        self.status_label.pack(pady=(12, 0))

    def _set_status(self, msg: str, error: bool = False):
        """Update the status label (thread-safe)."""
        def update():
            self.status_var.set(msg)
            self.status_label.configure(
                foreground="red" if error else "green"
            )
        self.root.after(0, update)

    def _set_busy(self, busy: bool):
        """Enable/disable the input controls."""
        def update():
            state = "disabled" if busy else "normal"
            self.url_entry.configure(state=state)
            self.parse_btn.configure(state=state)
        self.root.after(0, update)

    def _on_parse(self):
        """Handle the Parse button click / Enter key."""
        url = self.url_var.get().strip()
        if not url:
            self._set_status("Please paste a URL first.", error=True)
            return

        # Run in background thread to keep GUI responsive
        self._set_busy(True)
        self._set_status("Fetching page...")
        thread = threading.Thread(target=self._do_parse, args=(url,), daemon=True)
        thread.start()

    def _do_parse(self, url: str):
        """Background worker: parse the page and write to sheet."""
        try:
            self._set_status("Parsing f95zone page...")
            game = parse_f95_thread(url)

            self._set_status("Writing to Google Sheet...")
            row = write_game_data(game)

            self._set_status(
                f"✓ Done! \"{game.name}\" written to row {row}."
            )
        except ValueError as e:
            self._set_status(f"Error: {e}", error=True)
        except ConnectionError as e:
            self._set_status(f"Connection error: {e}", error=True)
        except Exception as e:
            self._set_status(f"Unexpected error: {e}", error=True)
        finally:
            self._set_busy(False)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
