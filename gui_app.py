#!/usr/bin/env python3
"""Tkinter GUI launcher for SAP-Role-Updater."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def _apply_modern_theme(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    bg = "#0f172a"
    fg = "#e2e8f0"
    accent = "#38bdf8"
    entry_bg = "#1e293b"
    style.configure(".", background=bg, foreground=fg, fieldbackground=entry_bg, relief="flat")
    style.configure("TButton", background=accent, foreground="#0b1220", padding=6)
    style.map("TButton", background=[("active", "#67e8f9")])
    style.configure("TLabel", background=bg, foreground=fg, padding=2)
    style.configure("TEntry", fieldbackground=entry_bg, padding=4, relief="solid", borderwidth=1)
    style.configure("TCheckbutton", background=bg, foreground=fg)
    root.configure(bg=bg)


def launch_gui(run_job_func, version):
    root = tk.Tk()
    root.title(f"SAP Role Updater {version}")
    root.resizable(False, False)
    _apply_modern_theme(root)

    state = {"in": tk.StringVar(), "rules": tk.StringVar(), "out": tk.StringVar(), "dry": tk.BooleanVar(value=False)}

    def browse(target, save=False):
        path = (
            filedialog.asksaveasfilename(title="Selecciona archivo de salida", initialfile="EXPORT_mod.txt")
            if save
            else filedialog.askopenfilename(title="Selecciona archivo")
        )
        if path:
            state[target].set(path)
            if target == "in" and not state["out"].get():
                state["out"].set(path + "_MOD")

    def run():
        infile = state["in"].get()
        rules_path = state["rules"].get()
        outfile = state["out"].get()
        if not (infile and rules_path and outfile):
            messagebox.showerror("Error", "Selecciona archivo base, reglas y salida.")
            return
        try:
            counters, log_path = run_job_func(infile, rules_path, outfile, dry_run=state["dry"].get(), verbose=False)
            msg = (
                f"Listo.\nAdds={counters['adds']} Deletes={counters['deletes']} "
                f"Replaces={counters['replaces']} Warns={counters['warns']}\nLog: {log_path}"
            )
            messagebox.showinfo("Éxito", msg)
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Error", str(ex))

    pad = {"padx": 12, "pady": 6}

    ttk.Label(root, text="Archivo base").grid(row=0, column=0, sticky="w", **pad)
    ttk.Entry(root, textvariable=state["in"], width=60).grid(row=0, column=1, **pad)
    ttk.Button(root, text="Buscar", command=lambda: browse("in")).grid(row=0, column=2, **pad)

    ttk.Label(root, text="Archivo reglas").grid(row=1, column=0, sticky="w", **pad)
    ttk.Entry(root, textvariable=state["rules"], width=60).grid(row=1, column=1, **pad)
    ttk.Button(root, text="Buscar", command=lambda: browse("rules")).grid(row=1, column=2, **pad)

    ttk.Label(root, text="Archivo salida").grid(row=2, column=0, sticky="w", **pad)
    ttk.Entry(root, textvariable=state["out"], width=60).grid(row=2, column=1, **pad)
    ttk.Button(root, text="Guardar como", command=lambda: browse("out", save=True)).grid(row=2, column=2, **pad)

    ttk.Checkbutton(root, text="Dry-run (no escribe archivo)", variable=state["dry"]).grid(
        row=3, column=1, sticky="w", **pad
    )

    ttk.Button(root, text="Procesar", command=run).grid(row=4, column=1, pady=12)

    root.mainloop()
