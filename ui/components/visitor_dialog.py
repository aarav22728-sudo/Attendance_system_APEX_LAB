"""Form for logging a temporary visitor: their name and purpose of visit."""

import customtkinter as ctk

from ui.themes import glassmorphism as theme


class VisitorDialog(ctk.CTkToplevel):
    def __init__(self, master, on_save):
        super().__init__(master)
        self._on_save = on_save

        self.title("APEX LAB — TEMPORARY VISITOR")
        self.geometry("420x360")
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
            frame, text="Temporary visitor",
            font=theme.get_font(16, "bold"), text_color=theme.COLOR_TEXT_PRIMARY,
        ).pack(pady=(16, 12))

        ctk.CTkLabel(
            frame, text="Visitor name",
            font=theme.get_font(11, "bold"), text_color=theme.COLOR_TEXT_SECONDARY,
        ).pack(anchor="w", padx=28)
        self._name = ctk.CTkEntry(frame, width=320, placeholder_text="e.g. Ravi Kumar")
        self._name.pack(pady=(2, 10))

        ctk.CTkLabel(
            frame, text="Purpose of coming to the lab",
            font=theme.get_font(11, "bold"), text_color=theme.COLOR_TEXT_SECONDARY,
        ).pack(anchor="w", padx=28)
        self._purpose = ctk.CTkEntry(frame, width=320, placeholder_text="e.g. Collecting samples")
        self._purpose.pack(pady=(2, 8))
        self._name.focus()

        self._msg = ctk.CTkLabel(frame, text="", font=theme.get_font(11), text_color=theme.COLOR_ACCENT_DANGER)
        self._msg.pack(pady=4)

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(fill="x", padx=24, pady=(8, 12))
        ctk.CTkButton(
            btns, text="Cancel", fg_color=theme.COLOR_BG_CARD,
            hover_color=theme.COLOR_BG_CARD_HOVER, command=self._cancel,
        ).pack(side="left", expand=True, fill="x", padx=4)
        ctk.CTkButton(
            btns, text="Save Visitor", fg_color=theme.COLOR_ACCENT_PRIMARY,
            hover_color="#2563EB", command=self._save,
        ).pack(side="left", expand=True, fill="x", padx=4)

    def _cancel(self):
        self.grab_release()
        self.destroy()

    def _save(self):
        name = self._name.get().strip()
        purpose = self._purpose.get().strip()
        if not name or not purpose:
            self._msg.configure(text="Please enter both the name and the purpose.")
            return
        self.grab_release()
        self.destroy()
        self._on_save(name, purpose)
