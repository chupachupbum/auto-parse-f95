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
        window_width, window_height = 520, 260
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
        self.url_entry.pack(fill="x", pady=(4, 8))
        self.url_entry.focus()

        # Note input
        ttk.Label(frame, text="Note (optional):").pack(anchor="w")

        self.note_var = tk.StringVar()
        self.note_entry = ttk.Entry(frame, textvariable=self.note_var, width=65)
        self.note_entry.pack(fill="x", pady=(4, 12))

        # Bind Enter and Numpad Enter keys on both entries
        self.url_entry.bind("<Return>", lambda e: self._on_parse())
        self.url_entry.bind("<KP_Enter>", lambda e: self._on_parse())
        self.note_entry.bind("<Return>", lambda e: self._on_parse())
        self.note_entry.bind("<KP_Enter>", lambda e: self._on_parse())

        # Bind Ctrl+A to select all
        def select_all(event):
            event.widget.select_range(0, 'end')
            event.widget.icursor('end')
            return 'break'
        self.url_entry.bind("<Control-a>", select_all)
        self.url_entry.bind("<Control-A>", select_all)
        self.note_entry.bind("<Control-a>", select_all)
        self.note_entry.bind("<Control-A>", select_all)

        # Buttons frame
        btn_frame = ttk.Frame(frame)
        btn_frame.pack()

        # Parse button
        self.parse_btn = ttk.Button(btn_frame, text="Parse", command=self._on_parse)
        self.parse_btn.pack(side="left", padx=5)

        # Clear button
        self.clear_btn = ttk.Button(btn_frame, text="Clear", command=self._on_clear)
        self.clear_btn.pack(side="left", padx=5)

        # Status label
        self.status_var = tk.StringVar(value="Ready — paste a link and press Enter or click Parse.")
        self.status_label = ttk.Label(
            frame, textvariable=self.status_var, wraplength=480, justify="center"
        )
        self.status_label.pack(pady=(12, 0))

    def _on_clear(self):
        """Clear the URL and Note input fields."""
        self.url_var.set("")
        self.note_var.set("")
        self.url_entry.focus()

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
            self.note_entry.configure(state=state)
            self.parse_btn.configure(state=state)
            self.clear_btn.configure(state=state)
        self.root.after(0, update)

    def _on_parse(self):
        """Handle the Parse button click / Enter key."""
        url = self.url_var.get().strip()
        if not url:
            self._set_status("Please paste a URL first.", error=True)
            return

        # Run in background thread to keep GUI responsive
        note = self.note_var.get().strip()
        self._set_busy(True)
        self._set_status("Fetching page...")
        thread = threading.Thread(target=self._do_parse, args=(url, note), daemon=True)
        thread.start()

    def _do_parse(self, url: str, note: str):
        """Background worker: parse the page and write to sheet."""
        try:
            self._set_status("Parsing f95zone page...")
            game = parse_f95_thread(url)

            self._set_status("Writing to Google Sheet...")
            row, replaced, changes = write_game_data(game, note=note)
            
            if replaced:
                change_str = ", ".join(changes) if changes else "No changes"
                self._set_status(
                    f"✓ Done! \"{game.name}\" replaced at row {row}.\nChanges: {change_str}"
                )
            else:
                self._set_status(
                    f"✓ Done! \"{game.name}\" written to new row {row}."
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
