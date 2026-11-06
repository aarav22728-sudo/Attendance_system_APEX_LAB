"""Manage Records: review and delete attendance entries, and deactivate people.
Opened only after the admin PIN is accepted."""

import datetime as dt
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from ui.themes import glassmorphism as theme


class RecordsDialog(ctk.CTkToplevel):
    def __init__(self, master, db, recognizer, audit, on_changed):
        super().__init__(master)
        self._db = db
        self._recognizer = recognizer
        self._audit = audit
        self._on_changed = on_changed
        self._day = dt.date.today()
        self._checks = {}  # entry id -> (BooleanVar, snapshot path)

        self.title("APEX LAB — MANAGE RECORDS")
        self.geometry("780x640")
        self.configure(fg_color=theme.COLOR_BG_ROOT)
        self.transient(master)
        self.grab_set()

        self._tabs = ctk.CTkTabview(self, fg_color=theme.COLOR_BG_PANEL)
        self._tabs.pack(fill="both", expand=True, padx=16, pady=16)
        self._tabs.add("Attendance")
        self._tabs.add("People")
        self._build_attendance(self._tabs.tab("Attendance"))
        self._build_people(self._tabs.tab("People"))

        self._load_entries()
        self._load_people()

    # ── Attendance tab ────────────────────────────────────────────────────
    def _build_attendance(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(top, text="< Previous", width=110,
                      command=lambda: self._shift_day(-1)).pack(side="left", padx=4)
        self._date_lbl = ctk.CTkLabel(top, text="", font=theme.get_font(13, "bold"),
                                      text_color=theme.COLOR_TEXT_PRIMARY)
        self._date_lbl.pack(side="left", padx=12)
        ctk.CTkButton(top, text="Next >", width=110,
                      command=lambda: self._shift_day(1)).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Delete selected", width=140,
                      fg_color=theme.COLOR_ACCENT_DANGER, hover_color="#B91C1C",
                      command=self._delete_selected).pack(side="right", padx=4)

        self._list = ctk.CTkScrollableFrame(parent, fg_color=theme.COLOR_BG_CARD)
        self._list.pack(fill="both", expand=True, padx=8, pady=8)

    def _shift_day(self, delta: int):
        self._day = self._day + dt.timedelta(days=delta)
        self._load_entries()

    def _load_entries(self):
        for w in self._list.winfo_children():
            w.destroy()
        self._checks.clear()
        self._date_lbl.configure(text=self._day.strftime("%A, %d %B %Y"))

        rows = self._db.list_entries_for_day(self._day.isoformat())
        if not rows:
            ctk.CTkLabel(self._list, text="No entries for this day.",
                         text_color=theme.COLOR_TEXT_MUTED).pack(pady=20)
            return

        for eid, ts, status, name, vname, purpose, snap in rows:
            if status == "visitor":
                who = f"{vname} (visitor)"
            elif status == "unknown":
                who = "Unknown person"
            else:
                who = name or "Unknown"
            text = f"{ts[11:19]}   {status:<9}   {who}"
            if purpose:
                text += f"   Purpose: {purpose}"
            var = tk.BooleanVar(value=False)
            ctk.CTkCheckBox(self._list, text=text, variable=var,
                            font=theme.get_font(12)).pack(anchor="w", padx=8, pady=3)
            self._checks[eid] = (var, snap)

    def _delete_selected(self):
        chosen = [eid for eid, (var, _) in self._checks.items() if var.get()]
        if not chosen:
            messagebox.showinfo("Manage Records", "Tick the entries you want to delete.", parent=self)
            return
        word = "entry" if len(chosen) == 1 else "entries"
        if not messagebox.askyesno("Confirm delete",
                                   f"Delete {len(chosen)} {word}? This cannot be undone.",
                                   parent=self):
            return

        snapshots = [self._checks[eid][1] for eid in chosen]
        self._db.delete_entries(chosen)
        removed_files = 0
        for path in snapshots:
            if path:
                try:
                    Path(path).unlink(missing_ok=True)
                    removed_files += 1
                except Exception:
                    pass

        self._audit.record("entries_deleted",
                           details=f"{len(chosen)} {word}, {removed_files} snapshot file(s)",
                           actor="admin")
        self._on_changed()
        self._load_entries()

    # ── People tab ────────────────────────────────────────────────────────
    def _build_people(self, parent):
        ctk.CTkLabel(
            parent,
            text=("Deactivating a person removes their face data and photo, so they are no "
                  "longer recognised. Their past attendance stays in the reports."),
            font=theme.get_font(11), text_color=theme.COLOR_TEXT_SECONDARY, wraplength=680,
        ).pack(pady=8)
        self._people_list = ctk.CTkScrollableFrame(parent, fg_color=theme.COLOR_BG_CARD)
        self._people_list.pack(fill="both", expand=True, padx=8, pady=8)

    def _load_people(self):
        for w in self._people_list.winfo_children():
            w.destroy()
        people = self._db.get_all_persons(active_only=True)
        if not people:
            ctk.CTkLabel(self._people_list, text="No enrolled people.",
                         text_color=theme.COLOR_TEXT_MUTED).pack(pady=20)
            return
        for p in people:
            row = ctk.CTkFrame(self._people_list, fg_color="transparent")
            row.pack(fill="x", pady=2, padx=4)
            ctk.CTkLabel(row, text=f"{p.name}  ({p.role})",
                         font=theme.get_font(12)).pack(side="left", padx=8)
            ctk.CTkButton(
                row, text="Deactivate", width=110, height=26,
                fg_color=theme.COLOR_ACCENT_DANGER, hover_color="#B91C1C",
                command=lambda pid=p.id, name=p.name: self._deactivate(pid, name),
            ).pack(side="right", padx=4)

    def _deactivate(self, pid: int, name: str):
        if not messagebox.askyesno("Confirm",
                                   f"Deactivate {name}? Their face data will be removed.",
                                   parent=self):
            return
        person = self._db.get_person(pid)
        self._db.deactivate_person(pid)
        photo = getattr(person, "photo_path", None) if person else None
        if photo:
            try:
                Path(photo).unlink(missing_ok=True)
            except Exception:
                pass
        self._recognizer.reload()
        self._audit.record("person_deactivated", details=name, actor="admin")
        self._on_changed()
        self._load_people()
