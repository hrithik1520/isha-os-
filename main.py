import tkinter as tk
from tkinter import simpledialog, messagebox
from dataclasses import dataclass, field
from collections import deque
import time

# ---------------- Cooperative scheduler (apps must yield) ----------------
class CoopScheduler:
    def __init__(self, root, tick_ms=25):
        self.root = root
        self.tick_ms = tick_ms
        self.tasks = deque()  # each task is a generator

    def add(self, gen):
        self.tasks.append(gen)

    def run(self):
        if self.tasks:
            gen = self.tasks.popleft()
            try:
                next(gen)   # run until yield
                self.tasks.append(gen)
            except StopIteration:
                pass
        self.root.after(self.tick_ms, self.run)


# ---------------- Document model ----------------
@dataclass
class Document:
    doc_type: str
    name: str
    content: str = ""
    created_at: float = field(default_factory=time.time)


class Desktop:
    def __init__(self, root):
        self.root = root
        self.root.title("Lisa-ish Desktop")
        self.root.geometry("980x640")

        self.clipboard = ""
        self.documents = []
        self.wastebasket = []  # holds deleted docs so they can be restored (Lisa-style) [concept]
        self.scheduler = CoopScheduler(root)

        # Stationery pads (document-centric creation) [Lisa concept]
        self.stationery = [
            ("Write pad", "write"),
            ("Calc pad", "calc"),
            ("Draw pad", "draw"),
        ]

        # Menu bar (Lisa-like top menus) [menu bar is a major Lisa UI element]
        menubar = tk.Menu(root)

        self.file_menu = tk.Menu(menubar, tearoff=0)
        self.file_menu.add_command(label="New from Stationery…", command=self.new_from_stationery_prompt)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=root.quit)
        menubar.add_cascade(label="File", menu=self.file_menu)

        self.edit_menu = tk.Menu(menubar, tearoff=0)
        self.edit_menu.add_command(label="Show Clipboard", command=self.show_clipboard)
        self.edit_menu.add_command(label="Clear Clipboard", command=self.clear_clipboard)
        menubar.add_cascade(label="Edit", menu=self.edit_menu)

        self.desk_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Desk", menu=self.desk_menu)

        root.config(menu=menubar)

        # Desktop canvas
        self.canvas = tk.Canvas(root, bg="#d9d9d9", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.icon_widgets = []
        self.render_desktop()

        # Scheduler loop
        self.scheduler.run()
        # Subtle "system clock" task (doesn't block)
        self.scheduler.add(self.clock_task())

    # ---------------- Desktop rendering ----------------
    def clear_desktop_widgets(self):
        for w in self.icon_widgets:
            try:
                w.destroy()
            except Exception:
                pass
        self.icon_widgets.clear()

    def render_desktop(self):
        self.clear_desktop_widgets()

        # Title labels (simple; Lisa look is mostly icons + windows)
        tk.Label(self.canvas, text="Desktop", bg="#d9d9d9", font=("Arial", 12, "bold")).place(x=18, y=10)

        # Left column: "job-handling" icons (wastebasket, clipboard, preferences) [Lisa concept]
        x = 20
        y = 40
        self._icon_button("Wastebasket", x, y, self.open_wastebasket_window)
        y += 120
        self._icon_button("Clipboard", x, y, self.open_clipboard_window)
        y += 120
        self._icon_button("Preferences", x, y, self.open_preferences)

        # Stationery pads (tear-off model) [Lisa concept]
        x2 = 220
        y2 = 40
        tk.Label(self.canvas, text="Stationery pads", bg="#d9d9d9", font=("Arial", 11, "bold")).place(x=x2, y=y2 - 26)

        for label, dtype in self.stationery:
            self._icon_button(
                label,
                x2, y2,
                on_open=lambda dt=dtype: self.new_doc_from_stationery(dt),
                subtitle="(double-click)"
            )
            y2 += 120

        # Documents area
        x3 = 520
        y3 = 40
        tk.Label(self.canvas, text="Documents", bg="#d9d9d9", font=("Arial", 11, "bold")).place(x=x3, y=y3 - 26)

        shown = self.documents[-12:]
        if not shown:
            tk.Label(self.canvas, text="(No documents yet)", bg="#d9d9d9").place(x=x3, y=y3)
        else:
            for doc in shown:
                self._icon_button(
                    doc.name,
                    x3, y3,
                    on_open=lambda d=doc: self.open_document_window(d),
                    subtitle=f"({doc.doc_type})"
                )
                y3 += 120

        self.refresh_desk_menu()

    def _icon_button(self, label, x, y, on_open, subtitle=None):
        """
        A simple icon-with-label that opens on double-click.
        """
        f = tk.Frame(self.canvas, bg="#d9d9d9")
        f.place(x=x, y=y)
        self.icon_widgets.append(f)

        box = tk.Label(
            f,
            text=" ",
            bg="white",
            width=10,
            height=4,
            relief="ridge",
            bd=2
        )
        box.pack()

        t = tk.Label(f, text=label, bg="#d9d9d9")
        t.pack()

        if subtitle:
            s = tk.Label(f, text=subtitle, bg="#d9d9d9", fg="#555555", font=("Arial", 8))
            s.pack()

        def open_evt(_=None):
            on_open()

        # Double-click opens (Lisa-style icon open)
        box.bind("<Double-Button-1>", open_evt)
        t.bind("<Double-Button-1>", open_evt)

        # Single-click “select” flash
        def select_evt(_=None):
            box.config(bg="#f2f2f2")
            self.root.after(140, lambda: box.config(bg="white"))

        box.bind("<Button-1>", select_evt)
        t.bind("<Button-1>", select_evt)

    # ---------------- Menus ----------------
    def refresh_desk_menu(self):
        self.desk_menu.delete(0, "end")

        wins = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)]
        if wins:
            for w in wins:
                title = w.title() or "(window)"
                self.desk_menu.add_command(label=title, command=w.lift)
            self.desk_menu.add_separator()

        for doc in self.documents[-20:]:
            self.desk_menu.add_command(label=f"Open: {doc.name}", command=lambda d=doc: self.open_document_window(d))

        self.desk_menu.add_separator()
        self.desk_menu.add_command(label="About", command=self.about)

    def about(self):
        messagebox.showinfo(
            "About",
            "Lisa-ish desktop prototype.\n"
            "Ideas: stationery pads, wastebasket restore, clipboard object."
        )

    # ---------------- Stationery / document creation ----------------
    def new_from_stationery_prompt(self):
        choice = simpledialog.askstring("Stationery", "Type: write / calc / draw")
        if not choice:
            return
        self.new_doc_from_stationery(choice.strip().lower())

    def default_doc_name(self, doc_type):
        stamp = time.strftime("%Y-%m-%d %H%M")
        return f"{doc_type}-{stamp}"

    def new_doc_from_stationery(self, doc_type):
        name = simpledialog.askstring("New Document", "Name your document:", initialvalue=self.default_doc_name(doc_type))
        if not name:
            return
        doc = Document(doc_type=doc_type, name=name, content="")
        self.documents.append(doc)
        self.render_desktop()
        self.open_document_window(doc)

    # ---------------- Clipboard ----------------
    def show_clipboard(self):
        messagebox.showinfo("Clipboard", self.clipboard if self.clipboard else "(empty)")

    def clear_clipboard(self):
        self.clipboard = ""

    def open_clipboard_window(self):
        w = tk.Toplevel(self.root)
        w.title("Clipboard")

        tk.Label(w, text="Clipboard contents", font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 0))

        text = tk.Text(w, height=10, wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.insert("1.0", self.clipboard)

        def update_clip():
            self.clipboard = text.get("1.0", "end-1c")
        tk.Button(w, text="Update clipboard", command=update_clip).pack(pady=(0, 10))

        self.refresh_desk_menu()

    # ---------------- Wastebasket ----------------
    def throw_away_document(self, doc: Document):
        # Remove from documents and place in wastebasket so it can be restored (Lisa-like behavior)
        try:
            self.documents.remove(doc)
        except ValueError:
            pass
        self.wastebasket.append(doc)
        self.render_desktop()

    def restore_document(self, doc: Document):
        try:
            self.wastebasket.remove(doc)
        except ValueError:
            pass
        self.documents.append(doc)
        self.render_desktop()

    def open_wastebasket_window(self):
        w = tk.Toplevel(self.root)
        w.title("Wastebasket")

        tk.Label(w, text="Wastebasket (restore last thrown away)", font=("Arial", 11, "bold")).pack(
            anchor="w", padx=10, pady=(10, 5)
        )

        lb = tk.Listbox(w, height=10, width=50)
        lb.pack(fill="both", expand=True, padx=10, pady=10)

        def refresh_list():
            lb.delete(0, "end")
            if not self.wastebasket:
                lb.insert("end", "(empty)")
                lb.config(state="disabled")
            else:
                lb.config(state="normal")
                for d in reversed(self.wastebasket[-50:]):
                    lb.insert("end", f"{d.name} ({d.doc_type})")

        def restore_selected():
            if not self.wastebasket:
                return
            sel = lb.curselection()
            if not sel:
                # restore last
                d = self.wastebasket[-1]
                self.restore_document(d)
                refresh_list()
                return

            idx = sel[0]
            # list is reversed view
            d = list(reversed(self.wastebasket[-50:]))[idx]
            self.restore_document(d)
            refresh_list()

        tk.Button(w, text="Restore selected (or last)", command=restore_selected).pack(pady=(0, 10))

        refresh_list()
        self.refresh_desk_menu()

    # ---------------- Preferences ----------------
    def open_preferences(self):
        w = tk.Toplevel(self.root)
        w.title("Preferences")

        tk.Label(w, text="Preferences", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 5))

        tk.Label(w, text="Prototype settings:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10)
        tk.Label(w, text="- Desktop color", anchor="w").pack(fill="x", padx=10, pady=(4, 0))

        col = tk.StringVar(value="#d9d9d9")

        def apply_color():
            c = col.get().strip()
            self.canvas.config(bg=c)
            self.render_desktop()

        tk.Entry(w, textvariable=col).pack(fill="x", padx=10, pady=4)
        tk.Button(w, text="Apply", command=apply_color).pack(padx=10, pady=(0, 10))

        self.refresh_desk_menu()

    # ---------------- Document window (tool) ----------------
    def open_document_window(self, doc: Document):
        w = tk.Toplevel(self.root)
        w.title(doc.name)

        status = tk.StringVar(value="Ready")

        top = tk.Frame(w)
        top.pack(fill="x")

        tk.Label(top, textvariable=status, anchor="w").pack(side="left", fill="x", expand=True, padx=8, pady=6)

        # Lisa-like "Put Away" idea: close to desktop icon
        def put_away():
            save()
            w.destroy()
            self.render_desktop()

        tk.Button(top, text="Put away", command=put_away).pack(side="right", padx=8, pady=6)

        text = tk.Text(w, wrap="word")
        text.insert("1.0", doc.content)
        text.pack(fill="both", expand=True)

        btns = tk.Frame(w)
        btns.pack(fill="x", pady=(4, 8))

        def copy_sel():
            try:
                sel = text.get("sel.first", "sel.last")
            except tk.TclError:
                sel = ""
            self.clipboard = sel
            status.set("Copied to clipboard")

        def paste_clip():
            text.insert("insert", self.clipboard)
            status.set("Pasted clipboard")

        def save():
            doc.content = text.get("1.0", "end-1c")
            status.set("Saved")
            self.render_desktop()

        def throw_away():
            if messagebox.askyesno("Throw away", f"Throw away '{doc.name}' to Wastebasket?"):
                self.throw_away_document(doc)
                w.destroy()

        tk.Button(btns, text="Copy", command=copy_sel).pack(side="left", padx=6)
        tk.Button(btns, text="Paste", command=paste_clip).pack(side="left", padx=6)
        tk.Button(btns, text="Save", command=save).pack(side="left", padx=6)
        tk.Button(btns, text="Throw away", command=throw_away).pack(side="right", padx=6)

        # Cooperative status blink (non-blocking)
        self.scheduler.add(self.blink_task(status))

        def on_close():
            doc.content = text.get("1.0", "end-1c")
            w.destroy()
            self.render_desktop()

        w.protocol("WM_DELETE_WINDOW", on_close)
        self.refresh_desk_menu()

    # ---------------- Cooperative tasks ----------------
    def blink_task(self, status_var):
        while True:
            cur = status_var.get()
            if cur == "Ready":
                status_var.set("Ready")  # keep subtle; you can change to "Autosave idle…"
            # yield control
            for _ in range(25):
                yield

    def clock_task(self):
        while True:
            self.root.title(f"Lisa-ish Desktop  |  {time.strftime('%H:%M:%S')}")
            for _ in range(40):
                yield


if __name__ == "__main__":
    root = tk.Tk()
    Desktop(root)
    root.mainloop()
