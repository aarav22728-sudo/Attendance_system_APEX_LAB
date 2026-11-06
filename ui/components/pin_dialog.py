"""Modal PIN prompt that guards face registration."""

import time

import customtkinter as ctk

from ui.themes import glassmorphism as theme
from core import pin as pin_auth

MAX_ATTEMPTS = 3
LOCKOUT_SECONDS = 60


class PinDialog(ctk.CTkToplevel):
    def __init__(self, master, on_success):
        super().__init__(master)
        self._on_success = on_success
        self._attempts = 0
        self._locked_until = 0.0

        self.title("APEX LAB — ADMIN ACCESS")
        self.geometry("380x280")
        self.resizable(False, False)
        self.configure(fg_color=theme.COLOR_BG_ROOT)
        self.transient(master)
        self.grab_set()

        frame = ctk.CTkFrame(
            self,
            fg_color=theme.COLOR_BG_PANEL,
            corner_radius=16,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            frame, text="Enter admin PIN",
            font=theme.get_font(16, "bold"), text_color=theme.COLOR_TEXT_PRIMARY,
        ).pack(pady=(18, 4))
        ctk.CTkLabel(
            frame, text="Required to register a new face.",
            font=theme.get_font(11), text_color=theme.COLOR_TEXT_SECONDARY,
        ).pack(pady=(0, 10))

        self._entry = ctk.CTkEntry(frame, show="•", width=200, justify="center", font=theme.get_font(16))
        self._entry.pack(pady=4)
        self._entry.bind("<Return>", lambda e: self._submit())
        self._entry.focus()

        self._msg = ctk.CTkLabel(frame, text="", font=theme.get_font(11), text_color=theme.COLOR_ACCENT_DANGER)
        self._msg.pack(pady=4)

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(fill="x", padx=24, pady=(8, 12))
        ctk.CTkButton(
            btns, text="Cancel", fg_color=theme.COLOR_BG_CARD,
            hover_color=theme.COLOR_BG_CARD_HOVER, command=self._cancel,
        ).pack(side="left", expand=True, fill="x", padx=4)
        ctk.CTkButton(
            btns, text="Unlock", fg_color=theme.COLOR_ACCENT_PRIMARY,
            hover_color="#2563EB", command=self._submit,
        ).pack(side="left", expand=True, fill="x", padx=4)

    def _cancel(self):
        self.grab_release()
        self.destroy()

    def _submit(self):
        remaining = self._locked_until - time.time()
        if remaining > 0:
            self._msg.configure(text=f"Locked. Try again in {int(remaining)}s.")
            return

        if pin_auth.verify_pin(self._entry.get().strip()):
            self.grab_release()
            self.destroy()
            self._on_success()
            return

        self._attempts += 1
        self._entry.delete(0, "end")
        if self._attempts >= MAX_ATTEMPTS:
            self._attempts = 0
            self._locked_until = time.time() + LOCKOUT_SECONDS
            self._msg.configure(text=f"Too many attempts. Locked for {LOCKOUT_SECONDS}s.")
        else:
            left = MAX_ATTEMPTS - self._attempts
            self._msg.configure(text=f"Incorrect PIN ({left} attempt{'s' if left != 1 else ''} left).")
