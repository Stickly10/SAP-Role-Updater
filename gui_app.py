#!/usr/bin/env python3
"""Tkinter GUI launcher for SAP-Role-Updater."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os


ACCENT = "#0078D4"
BG = "#282C34"
FG = "#e6e8eb"
ENTRY_BG = "#ffffff"
ENTRY_FG = "#111827"
STATUS_BG = "#1f2329"
ERROR_BG = "#3c1f20"
FONT_FAMILY = "Segoe UI"


def _apply_modern_theme(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        ".",
        background=BG,
        foreground=FG,
        fieldbackground=ENTRY_BG,
        font=(FONT_FAMILY, 10),
    )
    style.configure("Accent.TButton", background=ACCENT, foreground="white", padding=8, font=(FONT_FAMILY, 11, "bold"))
    style.map("Accent.TButton", background=[("active", "#1d8fe3")])
    style.configure("TButton", padding=6, font=(FONT_FAMILY, 10))
    style.configure("TLabel", padding=2, font=(FONT_FAMILY, 10), background=BG, foreground=FG)
    style.configure("TEntry", padding=4, relief="solid", borderwidth=1, foreground=ENTRY_FG, fieldbackground=ENTRY_BG)
    style.configure("Error.TEntry", padding=4, relief="solid", borderwidth=1, foreground=ENTRY_FG, fieldbackground=ERROR_BG)
    style.configure("TCheckbutton", background=BG, foreground=FG, font=(FONT_FAMILY, 10))
    style.configure("Info.TLabel", background=BG, foreground="#cbd5e1", font=(FONT_FAMILY, 9))
    style.configure("Group.TLabelframe", background=BG, foreground=FG, font=(FONT_FAMILY, 10, "bold"))
    style.configure("Group.TLabelframe.Label", background=BG, foreground=FG, font=(FONT_FAMILY, 10, "bold"))
    style.configure("Status.TLabel", background=BG, foreground=FG, font=(FONT_FAMILY, 10, "bold"))
    style.configure("Warn.TLabel", background=BG, foreground="#fbbf24", font=(FONT_FAMILY, 10))
    style.configure("StatusBox.TLabel", background=STATUS_BG, foreground=FG, font=(FONT_FAMILY, 10))
    root.configure(bg=BG)


def _truncate_path(path, max_len=40):
    if not path:
        return ""
    if len(path) <= max_len:
        return path
    head, tail = os.path.split(path)
    if len(tail) > max_len - 5:
        return "..." + tail[-(max_len - 3) :]
    return "..." + os.path.join("", tail)


def launch_gui(run_job_func, version):
    root = tk.Tk()
    root.title(f"SAP Role Updater {version}")
    root.resizable(False, False)
    _apply_modern_theme(root)

    state = {
        "in": tk.StringVar(),
        "rules": tk.StringVar(),
        "outdir": tk.StringVar(),
        "status": tk.StringVar(value="Listo para procesar."),
    }
    full_paths = {"in": "", "rules": "", "outdir": ""}
    last_out = {"outfile": "", "log": "", "warns": []}
    entries = {}

    def set_path(target, path):
        full_paths[target] = path
        state[target].set(_truncate_path(path))
        entries[target].tooltip = path
        if target == "in" and not full_paths["outdir"]:
            full_paths["outdir"] = os.path.dirname(path)
            state["outdir"].set(_truncate_path(full_paths["outdir"]))

    def browse(target, save=False):
        path = filedialog.askdirectory(title="Selecciona carpeta de salida") if save else filedialog.askopenfilename(title="Selecciona archivo")
        if path:
            set_path(target, path)

    def validate():
        valid = True
        for key in ("in", "rules", "outdir"):
            entries[key].configure(style="TEntry")
        if not full_paths["in"] or not os.path.isfile(full_paths["in"]):
            entries["in"].configure(style="Error.TEntry")
            valid = False
        if not full_paths["rules"] or not os.path.isfile(full_paths["rules"]):
            entries["rules"].configure(style="Error.TEntry")
            valid = False
        if not full_paths["outdir"]:
            entries["outdir"].configure(style="Error.TEntry")
            valid = False
        return valid

    progress = ttk.Progressbar(root, mode="indeterminate", length=200)

    def run(preview=False):
        if not validate():
            state["status"].set("Completa los archivos requeridos; revisa resaltados.")
            return
        try:
            progress.grid(row=5, column=1, pady=6)
            progress.start(10)
            root.update_idletasks()
            counters, outfile, log_path, warns = run_job_func(
                full_paths["in"],
                full_paths["rules"],
                full_paths["outdir"],
                preview=preview,
                verbose=False,
            )
            msg = (
                f"{'Previsualización' if preview else 'Proceso completado'}. Adds={counters['adds']} Deletes={counters['deletes']} "
                f"Replaces={counters['replaces']} Warns={counters['warns']}."
            )
            if not preview:
                msg += f"\nSalida: {outfile}\nLog: {log_path}"
            if warns:
                msg += "\nAdvertencias:\n- " + "\n- ".join(warns)
                status_label.configure(style="Warn.TLabel")
            else:
                status_label.configure(style="StatusBox.TLabel")
            state["status"].set(msg)
            if not preview:
                last_out["outfile"], last_out["log"], last_out["warns"] = outfile, log_path, warns
                messagebox.showinfo("Éxito", "Proceso completado correctamente.")
        except Exception as ex:  # noqa: BLE001
            state["status"].set(f"Error: {ex}")
            messagebox.showerror("Error", str(ex))
        finally:
            progress.stop()
            progress.grid_remove()

    pad = {"padx": 12, "pady": 6}
    group = ttk.Labelframe(root, text="Configuración de archivos", style="Group.TLabelframe")
    group.grid(row=0, column=0, columnspan=3, padx=12, pady=10, sticky="ew")

    def add_row(row, label_text, var_key, icon, save=False):
        ttk.Label(group, text=label_text).grid(row=row, column=0, sticky="w", **pad)
        entry = ttk.Entry(group, textvariable=state[var_key], width=55)
        entry.grid(row=row, column=1, **pad)
        entries[var_key] = entry
        btn = ttk.Button(group, text=icon, width=3, command=lambda: browse(var_key, save=save))
        btn.grid(row=row, column=2, **pad)
        entry.tooltip = ""

    add_row(0, "Archivo de Roles Existente (Base)", "in", "📂")
    add_row(1, "Archivo de Actualización/Reglas (.CSV)", "rules", "📂")
    add_row(2, "Carpeta de salida", "outdir", "📂", save=True)

    status_frame = ttk.Frame(root, padding=8)
    status_frame.grid(row=2, column=0, columnspan=3, sticky="ew")
    status_label = ttk.Label(status_frame, textvariable=state["status"], style="StatusBox.TLabel", wraplength=540, anchor="w")
    status_label.grid(row=0, column=0, columnspan=3, sticky="ew")

    def open_path(path):
        if not path:
            messagebox.showwarning("Aviso", "Nada para abrir todavía.")
            return
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                import subprocess, platform

                opener = "open" if platform.system() == "Darwin" else "xdg-open"
                subprocess.Popen([opener, path])
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Error", f"No se pudo abrir: {ex}")

    ttk.Button(status_frame, text="Abrir carpeta salida", command=lambda: open_path(os.path.dirname(last_out.get("outfile","")))).grid(row=1, column=0, sticky="w", pady=(6,0))
    ttk.Button(status_frame, text="Abrir log", command=lambda: open_path(last_out.get("log",""))).grid(row=1, column=1, sticky="w", pady=(6,0))

    ttk.Button(root, text="👁️ Previsualizar", command=lambda: run(preview=True)).grid(row=4, column=0, pady=10)
    ttk.Button(root, text="⚙️ Procesar", style="Accent.TButton", command=lambda: run(preview=False)).grid(
        row=4, column=0, columnspan=3, pady=10
    )

    root.mainloop()
