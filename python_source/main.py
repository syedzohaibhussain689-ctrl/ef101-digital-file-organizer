"""This file is main.py and it runs the main window and screens for our Digital Photo and File Organizer.
It builds the sidebar menu, top bar, summary cards, tables, and buttons using Tkinter.
All the colors, fonts, and sizes are kept at the top of this file so the design stays clean and consistent.
"""
import os
import sys
import time
import queue
import random
import threading
from datetime import datetime

# Tell Windows to draw crisp text on high resolution screens so the window never looks blurry.
# This has to run before we open the main Tkinter window.
if sys.platform == "win32":
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk, filedialog
from tkinter import font as tkfont

import database
import duplicate
import image_metadata
import charts
import organizer
import exporter
from scanner import scan_folder

# Pillow helps us draw sharp icons and small photo previews (thumbnails)
try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Color palette and spacing settings used across every screen in the app
BG = "#F9F9F8"            # Soft off white background for the sidebar and bottom status bar
SURFACE = "#FFFFFF"       # Pure white background for cards and main pages
BORDER = "#E8E8E5"
BORDER_LIGHT = "#F0F0EE"
TEXT = "#171716"
TEXT_SEC = "#5E5E5A"
TEXT_MUTED = "#8F8F8A"
ACCENT = "#171716"
ACCENT_SOFT = "#F2F2F0"
GLOW = "#F7F7F7"          # Light highlight color when the mouse hovers over a table row
GLOW_BG = "#F2F2F1"       # Light highlight color when hovering over a sidebar button
PRIMARY_HOVER = "#333333"
DANGER = "#9B2C2C"
DANGER_SOFT = "#FEF2F2"
SCROLL_THUMB = "#D4D4D2"
SCROLL_THUMB_HOVER = "#B3B3B0"

# Different shades of grey for each file category so charts and badges are easy to tell apart
CAT_COLORS = {
    "Image": "#111111", "Document": "#444444", "Audio": "#666666",
    "Video": "#888888", "Archive": "#AAAAAA", "Other": "#CCCCCC",
}

PAGE_SIZE = 50
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

# The S() helper function scales pixel sizes automatically on bigger or zoomed in screens
SCALE = 1.0


def S(value):
    """Multiplies a pixel size by the screen zoom scale so buttons and text never look tiny."""
    if value == 0:
        return 0
    return max(1, int(round(value * SCALE)))


def init_scale(root):
    global SCALE
    SCALE = max(1.0, root.winfo_fpixels("1i") / 96.0)


def hex_rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def blend(fg, bg, alpha):
    """Mixes two hex colors together to create lighter or faded shades for disabled buttons."""
    a, b = hex_rgb(fg), hex_rgb(bg)
    return "#%02X%02X%02X" % tuple(int(round(a[i] * alpha + b[i] * (1 - alpha))) for i in range(3))


# Load the Plus Jakarta Sans font from fonts_data.py, or fall back to Segoe UI if needed
JAKARTA = "Plus Jakarta Sans"
FONT_OK = False
_font_cache = {}


def load_embedded_fonts():
    try:
        import base64
        import fonts_data
    except ImportError:
        return
    folder = os.path.join(BASE_DIR, "fonts")
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        return
    for weight, data in fonts_data.FONT_DATA.items():
        path = os.path.join(folder, f"PlusJakartaSans-{weight}.ttf")
        try:
            raw = base64.b64decode(data)
            if not os.path.exists(path) or os.path.getsize(path) != len(raw):
                with open(path, "wb") as file:
                    file.write(raw)
            if sys.platform == "win32":
                # 0x10 tells Windows to load this font privately just for our app window
                ctypes.windll.gdi32.AddFontResourceExW(path, 0x10, 0)
        except Exception:
            pass


def init_fonts(root):
    global FONT_OK
    try:
        FONT_OK = JAKARTA in set(tkfont.families(root))
    except tk.TclError:
        FONT_OK = False


def _family(weight):
    """Picks the right font name and bold setting for regular, medium, semibold, or bold text."""
    if FONT_OK:
        return {
            "regular": (JAKARTA, False),
            "medium": (JAKARTA + " Medium", False),
            "semibold": (JAKARTA + " SemiBold", False),
            "bold": (JAKARTA, True),
        }[weight]
    if sys.platform == "win32":
        return {
            "regular": ("Segoe UI", False),
            "medium": ("Segoe UI", False),
            "semibold": ("Segoe UI Semibold", False),
            "bold": ("Segoe UI", True),
        }[weight]
    base = tkfont.nametofont("TkDefaultFont").actual("family")
    return (base, weight in ("semibold", "bold"))


def FN(px, weight="regular"):
    """Creates a simple font setting for any text label or button."""
    family, bold = _family(weight)
    return (family, -S(px), "bold") if bold else (family, -S(px))


def FM(px, weight="regular"):
    """Creates a font object that can measure how wide a word is in pixels."""
    key = (px, weight, SCALE)
    if key not in _font_cache:
        family, bold = _family(weight)
        _font_cache[key] = tkfont.Font(family=family, size=-S(px),
                                       weight="bold" if bold else "normal")
    return _font_cache[key]


def mono(px):
    return ("Consolas" if sys.platform == "win32" else "DejaVu Sans Mono", -S(px))


def sp(text):
    """Adds a tiny bit of breathing room between uppercase letters in small headings."""
    return " ".join(text) if FONT_OK else text


def ellipsize(text, font, max_px):
    """If a file name is too long to fit in its box, this trims the end and adds three dots (...)."""
    if font.measure(text) <= max_px:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.measure(text[:mid] + "…") <= max_px:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + "…"


def ellipsize_middle(text, font, max_px):
    """Trims a long file name in the middle so you can still read both the start and the file ending."""
    if font.measure(text) <= max_px:
        return text
    best = "…"
    lo, hi = 1, len(text)
    while lo < hi:
        keep = (lo + hi + 1) // 2
        tail = max(4, keep // 3)
        head = max(1, keep - tail)
        candidate = text[:head].rstrip() + "…" + text[-tail:].lstrip()
        if font.measure(candidate) <= max_px:
            best = candidate
            lo = keep
        else:
            hi = keep - 1
    return best


def fmt_size(num_bytes):
    """Formats a byte number into easy units like 512 B, 1.5 KB, or 3.2 MB."""
    if not num_bytes:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num_bytes)
    index = 0
    while value >= 1024 and index < len(units) - 1:
        value /= 1024
        index += 1
    text = f"{value:.1f}".rstrip("0").rstrip(".") if index else f"{int(value)}"
    return f"{text} {units[index]}"


# Draw our own icons with Pillow and save them in a dictionary cache so they load fast
_icon_cache = {}


def _draw_icon(name, size, color, stroke):
    k = 8                                   # Draw 8 times bigger first, then shrink it so lines look super smooth
    px = size * k
    u = px / 24.0
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(1, int(round(stroke * u)))
    col = hex_rgb(color) + (255,)

    def P(x, y):
        return (x * u, y * u)

    def dot(x, y):
        cx, cy = P(x, y)
        d.ellipse([cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2], fill=col)

    def line(*pts, closed=False):
        pts = list(pts) + ([pts[0]] if closed else [])
        d.line([P(*p) for p in pts], fill=col, width=w, joint="curve")
        for p in pts:
            dot(*p)

    def rrect(x0, y0, x1, y1, r):
        h = w / 2
        d.rounded_rectangle([x0 * u - h, y0 * u - h, x1 * u + h, y1 * u + h],
                            radius=r * u, outline=col, width=w)

    if name == "grid":
        for (x, y) in ((3, 3), (14, 3), (3, 14), (14, 14)):
            rrect(x, y, x + 7, y + 7, 1)
    elif name == "list":
        for y in (6, 10, 14, 18):
            line((4, y), (20, y))
    elif name == "copy":
        rrect(4, 4, 16, 16, 2)
        h = w / 2
        d.rounded_rectangle([8 * u - h, 8 * u - h, 20 * u + h, 20 * u + h],
                            radius=2 * u, fill=(0, 0, 0, 0))   # Clear the overlapping corner so the two squares look layered
        rrect(8, 8, 20, 20, 2)
    elif name == "chart":
        rrect(3, 11, 9, 21, 2)
        rrect(9, 7, 15, 21, 2)
        rrect(15, 3, 21, 21, 2)
    elif name == "folder":
        line((5, 5), (10, 5), (12, 7), (19, 7), (21, 9), (21, 17), (19, 19),
             (5, 19), (3, 17), (3, 7), closed=True)
    elif name == "file-down":
        line((7, 3), (12.6, 3), (19, 9.4), (19, 19), (17, 21), (7, 21), (5, 19), (5, 5),
             closed=True)
        line((12, 10), (12, 16))
        line((9, 13), (12, 16), (15, 13))
    elif name == "upload":
        line((4, 16), (4, 17), (7, 20), (17, 20), (20, 17), (20, 16))
        line((8, 8), (12, 4), (16, 8))
        line((12, 4), (12, 16))
    elif name == "refresh":
        h = w / 2
        d.arc([4 * u - h, 4 * u - h, 20 * u + h, 20 * u + h], 195, 358, fill=col, width=w)
        d.arc([4 * u - h, 4 * u - h, 20 * u + h, 20 * u + h], 15, 178, fill=col, width=w)
        line((4, 4), (4, 9), (9, 9))
        line((20, 20), (20, 15), (15, 15))
    elif name == "folder-down":
        line((5, 5), (10, 5), (12, 7), (19, 7), (21, 9), (21, 17), (19, 19),
             (5, 19), (3, 17), (3, 7), closed=True)
        line((12, 11), (12, 15))
        line((10, 13), (12, 15), (14, 13))
    elif name == "bolt":
        line((13, 10), (13, 3), (4, 14), (11, 14), (11, 21), (20, 10), closed=True)
    elif name == "eye":
        d.ellipse([2.5 * u, 6.5 * u, 21.5 * u, 17.5 * u], outline=col, width=w)
        cx, cy = P(12, 12)
        r = 3 * u
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=w)
    elif name == "check-circle":
        d.ellipse([3 * u, 3 * u, 21 * u, 21 * u], outline=col, width=w)
        line((9, 12), (11, 14), (15, 10))
    elif name == "sad":
        d.ellipse([3 * u, 3 * u, 21 * u, 21 * u], outline=col, width=w)
        dot(9, 10)
        dot(15, 10)
        line((9.2, 16.2), (12, 15), (14.8, 16.2))

    return img.resize((size, size), Image.LANCZOS)


def icon(name, size, color, stroke=2.0):
    """Returns a ready to use icon image from the cache so we do not redraw it every time."""
    if not PIL_OK:
        return None
    key = (name, size, color, stroke, SCALE)
    if key not in _icon_cache:
        _icon_cache[key] = ImageTk.PhotoImage(_draw_icon(name, S(size), color, stroke))
    return _icon_cache[key]


# Small helper building blocks used to create labels, lines, buttons, and cards across the app
def clear(frame):
    for child in frame.winfo_children():
        child.destroy()


def lbl(parent, text="", px=13, weight="regular", fg=TEXT, bg=None, **kw):
    kw.setdefault("bd", 0)
    kw.setdefault("highlightthickness", 0)
    return tk.Label(parent, text=text, font=FN(px, weight), fg=fg,
                    bg=bg if bg is not None else parent.cget("bg"), **kw)


def hline(parent, color=BORDER, **pack):
    line = tk.Frame(parent, bg=color, height=S(1))
    line.pack(fill="x", **pack)
    return line


def swap_bg(widget, old, new):
    """Changes the background color of a box and everything inside it when the mouse hovers over it."""
    if getattr(widget, "_noswap", False):
        return
    try:
        if str(widget.cget("bg")).lower() == old.lower():
            widget.configure(bg=new)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        swap_bg(child, old, new)


def bind_tree(widget, sequence, handler):
    """Attaches a mouse click or hover action to a box and all the items inside it."""
    if getattr(widget, "_noswap", False):
        return
    widget.bind(sequence, handler, add="+")
    for child in widget.winfo_children():
        bind_tree(child, sequence, handler)


def pointer_inside(widget, event):
    try:
        under = widget.winfo_containing(event.x_root, event.y_root)
    except (KeyError, tk.TclError):
        return False
    while under is not None:
        if under is widget:
            return True
        under = under.master
    return False


class Btn(tk.Frame):
    """Custom button widget with a clean border that changes color when you hover or click on it."""
    KINDS = {
        "default": dict(border=BORDER, hborder=TEXT_MUTED, bg=SURFACE, hbg=SURFACE,
                        fg=TEXT, hover_fg=TEXT),
        "primary": dict(border=ACCENT, hborder=PRIMARY_HOVER, bg=ACCENT, hbg=PRIMARY_HOVER,
                        fg="#FFFFFF", hover_fg="#FFFFFF"),
        "danger": dict(border=DANGER, hborder=DANGER, bg=SURFACE, hbg=DANGER_SOFT,
                       fg=DANGER, hover_fg=DANGER),
    }

    def __init__(self, parent, text, command=None, icon_name=None, kind="default",
                 px=16, py=8, size=13, icon_size=14):
        self.kind = kind
        super().__init__(parent, bg=self.KINDS[kind]["border"], cursor="hand2")
        self._noswap = True
        self.command = command
        self.enabled = True
        self.hovering = False
        self.icon_name = icon_name if PIL_OK else None
        self.icon_size = icon_size

        self.inner = tk.Frame(self, bg=SURFACE)
        self.inner.pack(fill="both", expand=True, padx=S(1), pady=S(1))
        self.content = tk.Frame(self.inner, bg=SURFACE)
        self.content.pack(expand=True)

        self.icon_label = None
        if self.icon_name:
            self.icon_label = tk.Label(self.content, bd=0, highlightthickness=0)
            self.icon_label.pack(side="left", padx=(S(px), S(8)), pady=S(py))
        self.text_label = tk.Label(self.content, text=text, font=FN(size, "medium"),
                                   bd=0, highlightthickness=0)
        self.text_label.pack(side="left", padx=(0 if self.icon_label else S(px), S(px)),
                             pady=S(py))

        self._parts = [self, self.inner, self.content, self.text_label]
        if self.icon_label:
            self._parts.append(self.icon_label)
        for part in self._parts:
            part.bind("<Enter>", self._enter)
            part.bind("<Leave>", self._leave)
            part.bind("<Button-1>", self._click)
        self._apply()

    # Updates the button colors depending on whether it is hovered, active, or disabled
    def _apply(self):
        k = self.KINDS[self.kind]
        bg = k["hbg"] if (self.hovering and self.enabled) else k["bg"]
        border = k["hborder"] if (self.hovering and self.enabled) else k["border"]
        fg = k["fg"]
        if not self.enabled:                       # Fade the colors if the button is currently disabled
            bg_page = SURFACE
            border, bg, fg = blend(border, bg_page, .4), blend(bg, bg_page, .4), blend(fg, bg_page, .4)
        super().configure(bg=border, cursor="hand2" if self.enabled else "arrow")
        self.inner.configure(bg=bg)
        self.content.configure(bg=bg)
        self.text_label.configure(bg=bg, fg=fg)
        if self.icon_label:
            self.icon_label.configure(bg=bg, image=icon(self.icon_name, self.icon_size, fg))

    def set_kind(self, kind):
        if kind != self.kind:
            self.kind = kind
            self._apply()

    def set_enabled(self, enabled):
        self.enabled = enabled
        self._apply()

    def set_text(self, text):
        self.text_label.configure(text=text)

    def _enter(self, event):
        self.hovering = True
        self._apply()

    def _leave(self, event):
        if pointer_inside(self, event):
            return
        self.hovering = False
        self._apply()

    def _click(self, event):
        if self.enabled and self.command:
            self.command()
        return "break"


class NavItem(tk.Frame):
    """One clickable menu row inside the left sidebar with an icon, title, and file count badge."""

    def __init__(self, parent, text, icon_name, command):
        super().__init__(parent, bg=BG, cursor="hand2")
        self.text = text
        self.icon_name = icon_name
        self.command = command
        self.active = False
        self.hovering = False
        self.icon_label = tk.Label(self, bd=0, highlightthickness=0)
        self.icon_label.pack(side="left", padx=(S(12), S(12)), pady=S(10))
        self.text_label = tk.Label(self, text=text, bd=0, highlightthickness=0)
        self.text_label.pack(side="left")
        self.count_label = tk.Label(self, text="", font=FN(11, "medium"), bd=0,
                                    highlightthickness=0)
        self.count_label.pack(side="right", padx=(0, S(12)))
        for part in (self, self.icon_label, self.text_label, self.count_label):
            part.bind("<Enter>", self._enter)
            part.bind("<Leave>", self._leave)
            part.bind("<Button-1>", lambda e: self.command())
        self._apply()

    def _apply(self):
        if self.active:
            bg, fg, icon_color = ACCENT_SOFT, ACCENT, ACCENT
        else:
            bg = GLOW_BG if self.hovering else BG
            fg = TEXT if self.hovering else TEXT_SEC
            icon_color = blend(fg, bg, .8)
        font = FN(13, "semibold" if self.active else "medium")
        self.configure(bg=bg)
        self.icon_label.configure(bg=bg, image=icon(self.icon_name, 16, icon_color))
        self.text_label.configure(bg=bg, fg=fg, font=font)
        self.count_label.configure(bg=bg, fg=TEXT_MUTED)

    def set_active(self, active):
        self.active = active
        self._apply()

    def set_count(self, text):
        self.count_label.configure(text=text)

    def _enter(self, event):
        self.hovering = True
        self._apply()

    def _leave(self, event):
        if pointer_inside(self, event):
            return
        self.hovering = False
        self._apply()


class TextInput(tk.Frame):
    """Text box for searching and filtering with helpful grey hint text (placeholder) inside."""

    def __init__(self, parent, width, placeholder="", command=None):
        super().__init__(parent, bg=SURFACE, width=S(width), height=S(36),
                         highlightthickness=S(1), highlightbackground=BORDER,
                         highlightcolor=BORDER)
        self.pack_propagate(False)
        self.placeholder = placeholder
        self.command = command
        self.showing_placeholder = False
        self.error = False
        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, bd=0, relief="flat",
                              highlightthickness=0, bg=SURFACE, fg=TEXT,
                              insertbackground=ACCENT, font=FN(13),
                              selectbackground="#DCDCD8", selectforeground=TEXT)
        self.entry.pack(fill="both", expand=True, padx=S(12), pady=S(2))
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.bind("<KeyRelease>", self._typed)
        self.entry.bind("<Return>", lambda e: self._notify(True))
        self._show_placeholder()

    def value(self):
        return "" if self.showing_placeholder else self.var.get().strip()

    def set(self, text):
        self.showing_placeholder = False
        self.entry.configure(fg=TEXT)
        self.var.set(text)
        if not text and self.focus_get() is not self.entry:
            self._show_placeholder()

    def set_error(self, error):
        self.error = error
        self._paint()

    def _paint(self, focused=False):
        if focused:
            self.configure(highlightthickness=S(2), highlightbackground=ACCENT)
        else:
            self.configure(highlightthickness=S(1),
                           highlightbackground=DANGER if self.error else BORDER)

    def _show_placeholder(self):
        if not self.var.get() and self.placeholder:
            self.showing_placeholder = True
            self.entry.configure(fg=TEXT_MUTED)
            self.var.set(self.placeholder)

    def _focus_in(self, event):
        if self.showing_placeholder:
            self.showing_placeholder = False
            self.var.set("")
            self.entry.configure(fg=TEXT)
        self._paint(focused=True)

    def _focus_out(self, event):
        self._show_placeholder()
        self._paint()

    def _typed(self, event):
        if event.keysym in ("Tab", "Shift_L", "Shift_R", "Control_L", "Control_R",
                            "Return", "Left", "Right", "Up", "Down", "Escape"):
            return
        self._notify(False)

    def _notify(self, immediate):
        if self.command:
            self.command(immediate)


class Select(ttk.Combobox):
    """Dropdown menu that lets the user pick a category, extension, or sort order."""

    def __init__(self, parent, values, command=None, width=16):
        super().__init__(parent, values=values, state="readonly", style="Web.TCombobox",
                         font=FN(13), width=width, takefocus=0)
        self.command = command
        self.current(0)
        self.bind("<<ComboboxSelected>>", self._chosen)
        self.bind("<MouseWheel>", self._wheel)      # Stop mouse wheel scrolling from accidentally changing the dropdown choice

    def _chosen(self, event):
        self.after(10, lambda: self.selection_clear())
        if self.command:
            self.command()

    def _wheel(self, event):
        if SCROLLER is not None:
            SCROLLER.on_wheel(event)
        return "break"

    def set_values(self, values):
        current = self.get()
        self.configure(values=values)
        self.set(current if current in values else values[0])


SCROLLER = None   # Reference to the main page scroller so the mouse wheel works everywhere


class ScrollFrame(tk.Frame):
    """Scrollable page container that holds all the cards and tables."""

    def __init__(self, parent, bg=SURFACE):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0,
                                yscrollincrement=S(24))
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                  style="Web.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.window = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self._seen = (0, 0, 0)
        self.canvas.bind("<Configure>", lambda e: self._fit())
        self.inner.bind("<Configure>", lambda e: self._fit())
        self._watch()

    def _watch(self):
        # Periodically check if the page content grew taller so the scrollbar stays accurate
        try:
            if (self.canvas.winfo_width(), self.canvas.winfo_height(),
                    self.inner.winfo_reqheight()) != self._seen:
                self._fit()
            self.after(120, self._watch)
        except tk.TclError:
            pass

    def _on_scroll(self, first, last):
        self.vbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.vbar.state(["disabled"])
        else:
            self.vbar.state(["!disabled"])

    def _fit(self):
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        needed = self.inner.winfo_reqheight()
        self._seen = (width, height, needed)
        self.canvas.itemconfigure(self.window, width=width, height=max(needed, height))
        self.canvas.configure(scrollregion=(0, 0, width, max(needed, height)))

    def scroll_to_top(self):
        self.canvas.yview_moveto(0)

    def on_wheel(self, event):
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            return
        if getattr(event, "num", None) == 4:
            step = -1
        elif getattr(event, "num", None) == 5:
            step = 1
        else:
            step = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(step * 4, "units")


class Flow(tk.Frame):
    """Places items side by side from left to right and wraps to a new line when space runs out."""

    def __init__(self, parent, gap_x=12, gap_y=12, bg=SURFACE):
        super().__init__(parent, bg=bg, height=1)
        self.gap_x, self.gap_y = S(gap_x), S(gap_y)
        self.items = []
        self.bind("<Configure>", lambda e: self.relayout())

    def add(self, widget):
        self.items.append(widget)
        self.after_idle(self.relayout)

    def relayout(self):
        width = self.winfo_width()
        if width <= 1 or not self.items:
            return
        self.update_idletasks()
        x = y = row_height = 0
        for widget in self.items:
            w, h = widget.winfo_reqwidth(), widget.winfo_reqheight()
            if x > 0 and x + w > width:
                x = 0
                y += row_height + self.gap_y
                row_height = 0
            widget.place(x=x, y=y)
            x += w + self.gap_x
            row_height = max(row_height, h)
        self.configure(height=y + row_height)


class ResponsiveGrid(tk.Frame):
    """Arranges cards into equal width columns that automatically adjust when you resize the window."""

    def __init__(self, parent, min_width, gap=16, bg=SURFACE):
        super().__init__(parent, bg=bg)
        self.min_width, self.gap = S(min_width), S(gap)
        self.items = []
        self.columns = 0
        self.bind("<Configure>", self._on_configure)

    def set_items(self, items):
        self.items = list(items)
        self.columns = 0
        self._layout(self._count())

    def _count(self):
        return max(1, (self.winfo_width() + self.gap) // (self.min_width + self.gap))

    def _on_configure(self, event):
        count = self._count()
        if count != self.columns:
            self._layout(count)

    def _layout(self, columns):
        self.columns = columns
        for widget in self.items:
            widget.grid_forget()
        for c in range(40):
            self.columnconfigure(c, weight=0, uniform="")
        for c in range(columns):
            self.columnconfigure(c, weight=1, uniform="cell")
        for index, widget in enumerate(self.items):
            row, col = divmod(index, columns)
            widget.grid(row=row, column=col, sticky="nsew",
                        padx=(0, self.gap if col < columns - 1 else 0),
                        pady=(0, self.gap))


class ProgressBar(tk.Canvas):
    """Thin animated progress line shown at the top of the window while scanning or hashing files."""

    def __init__(self, parent, bg=SURFACE):
        super().__init__(parent, height=S(3), bg=BORDER_LIGHT, highlightthickness=0, bd=0)
        self.fraction = None
        self.position = 0.0
        self.running = False

    def start(self):
        self.fraction = None
        if not self.running:
            self.running = True
            self._tick()

    def set(self, fraction):
        self.fraction = fraction
        self._draw()

    def stop(self):
        self.running = False

    def _tick(self):
        if not self.running:
            return
        self.position = (self.position + 0.025) % 1.3
        self._draw()
        self.after(30, self._tick)

    def _draw(self):
        self.delete("all")
        width, height = max(self.winfo_width(), 1), S(3)
        if self.fraction is None:
            x0 = (self.position - 0.3) * width
            self.create_rectangle(max(0, x0), 0, min(width, x0 + 0.3 * width), height,
                                  fill=ACCENT, width=0)
        else:
            self.create_rectangle(0, 0, width * self.fraction, height, fill=ACCENT, width=0)


def make_card(parent, padding=24, bg=SURFACE):
    """Creates a white card box with a thin 1 pixel border around it."""
    outer = tk.Frame(parent, bg=BORDER)
    inner = tk.Frame(outer, bg=bg)
    inner.pack(fill="both", expand=True, padx=S(1), pady=S(1))
    body = tk.Frame(inner, bg=bg)
    body.pack(fill="both", expand=True, padx=S(padding), pady=S(padding))
    return outer, body


def bar(parent, fraction, color, bg=SURFACE):
    """Draws a horizontal percentage bar to visualize storage usage."""
    track = tk.Frame(parent, bg=BORDER_LIGHT, height=S(4))
    fill = tk.Frame(track, bg=color)
    fill.place(x=0, y=0, relheight=1, relwidth=max(0.0, min(1.0, fraction)))
    return track


def setup_styles(root):
    """Styles the Tkinter scrollbars and dropdown menus so they look flat and modern."""
    root.configure(bg=SURFACE)
    style = ttk.Style(root)
    style.theme_use("clam")   # The clam theme lets us customize every color freely

    style.layout("Web.Vertical.TScrollbar", [
        ("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
    style.configure("Web.Vertical.TScrollbar", background=SCROLL_THUMB, troughcolor=SURFACE,
                    bordercolor=SURFACE, lightcolor=SCROLL_THUMB, darkcolor=SCROLL_THUMB,
                    width=S(6), relief="flat", gripcount=0)
    style.map("Web.Vertical.TScrollbar",
              background=[("disabled", SURFACE), ("pressed", SCROLL_THUMB_HOVER),
                          ("active", SCROLL_THUMB_HOVER)],
              lightcolor=[("disabled", SURFACE)], darkcolor=[("disabled", SURFACE)])

    style.configure("Web.TCombobox", fieldbackground=SURFACE, background=SURFACE,
                    foreground=TEXT, arrowcolor=TEXT_MUTED, bordercolor=BORDER,
                    lightcolor=SURFACE, darkcolor=SURFACE, relief="flat",
                    padding=(S(8), S(7)), arrowsize=S(13),
                    selectbackground=SURFACE, selectforeground=TEXT)
    style.map("Web.TCombobox",
              fieldbackground=[("readonly", SURFACE)],
              background=[("readonly", SURFACE), ("active", SURFACE)],
              foreground=[("readonly", TEXT)],
              selectbackground=[("readonly", SURFACE)],
              selectforeground=[("readonly", TEXT)],
              bordercolor=[("focus", ACCENT), ("active", TEXT_MUTED)],
              lightcolor=[("focus", SURFACE)], darkcolor=[("focus", SURFACE)],
              arrowcolor=[("active", TEXT)])

    # Style the popup list that appears when you click a dropdown menu
    root.option_add("*TCombobox*Listbox.background", SURFACE)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_SOFT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
    root.option_add("*TCombobox*Listbox.borderWidth", 0)
    root.option_add("*TCombobox*Listbox.relief", "flat")
    root.option_add("*TCombobox*Listbox.font", FM(13))


# Helpers for creating small square photo previews and file extension tiles in Grid View
def _pil_font(size):
    for name in (os.path.join(BASE_DIR, "fonts", "PlusJakartaSans-SemiBold.ttf"),
                 "segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_thumbnail(path, size):
    """Creates a small square preview image of a photo, or returns None if the photo cannot be opened."""
    try:
        with Image.open(path) as img:
            img.draft("RGB", (size * 2, size * 2))     # Speeds up loading huge camera photos
            img = img.convert("RGB")
            img.thumbnail((size, size), Image.LANCZOS)
            tile = Image.new("RGB", (size, size), hex_rgb(ACCENT_SOFT))
            tile.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
            return tile
    except Exception:
        return None


def make_type_tile(category, extension, size):
    """Creates a neat square tile showing the file extension (like PDF or MP3) for non photo files."""
    tile = Image.new("RGB", (size, size), hex_rgb(ACCENT_SOFT))
    draw = ImageDraw.Draw(tile)
    bar_h = max(3, size // 28)
    draw.rectangle([0, size - bar_h, size, size], fill=hex_rgb(CAT_COLORS.get(category, "#CCCCCC")))
    text = extension.lstrip(".").upper()[:4] or "FILE"
    font = _pil_font(max(10, size // 5))
    box = draw.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.text(((size - w) / 2 - box[0], (size - bar_h - h) / 2 - box[1]),
              text, fill=hex_rgb(TEXT_MUTED), font=font)
    return tile


# Main App controller class and dropdown menu choices
SORT_OPTIONS = [
    ("Name A–Z", "name", False), ("Name Z–A", "name", True),
    ("Largest first", "size", True), ("Smallest first", "size", False),
    ("Newest first", "date", True), ("Oldest first", "date", False),
    ("Extension A–Z", "ext", False), ("Extension Z–A", "ext", True),
]
SORT_DB_NAME = {"name": "Name", "size": "Size", "date": "Date", "ext": "Extension"}

CATEGORY_OPTIONS = [
    ("All categories", "All"), ("Images", "Image"), ("Documents", "Document"),
    ("Audio", "Audio"), ("Video", "Video"), ("Archives", "Archive"), ("Other", "Other"),
]

NAV = [
    ("dashboard", "Dashboard", "grid"),
    ("files", "All Files", "list"),
    ("duplicates", "Duplicates", "copy"),
    ("charts", "Charts", "chart"),
    ("organize", "Organize", "folder"),
    ("export", "Export", "file-down"),
]


class App:
    def __init__(self, root):
        global SCROLLER
        self.root = root
        init_scale(root)
        init_fonts(root)

        root.title("EF101-P19 — Digital Photo & File Organizer")
        width = min(S(1280), root.winfo_screenwidth() - S(60))
        height = min(S(780), root.winfo_screenheight() - S(120))
        x = max(0, (root.winfo_screenwidth() - width) // 2)
        y = max(0, (root.winfo_screenheight() - height) // 2 - S(20))
        root.geometry(f"{width}x{height}+{x}+{y}")
        root.minsize(min(S(980), width), min(S(600), height))
        setup_styles(root)
        database.create_table()

        # Variables that keep track of which page is open and what filters are active
        self.current = "dashboard"
        self.has_files = False
        self.meta = {}
        self.folder = ""
        self.scanning = False
        self.scan_queue = None
        self.photo_cache = {}
        self.view_mode = "list"
        self.page_no = 1
        self.sort_key, self.sort_desc = "name", False
        self.filter_after = None
        self.filters_built = False
        self.more_open = False
        self.hover_row = None
        self.toast_job = None
        self.modal = None
        self.modal_opened_at = 0.0
        self.pages = {}
        self.nav_items = {}

        # Build the main window layout: left sidebar, top bar, center scroll area, and bottom status bar
        shell = tk.Frame(root, bg=BG)
        shell.pack(fill="both", expand=True)
        self.build_sidebar(shell)
        main = tk.Frame(shell, bg=SURFACE)
        main.pack(side="left", fill="both", expand=True)
        self.build_statusbar(main)        # Pack the status bar at the bottom first so it never gets pushed off screen
        self.build_topbar(main)
        self.scroll = ScrollFrame(main)
        self.scroll.pack(fill="both", expand=True)
        SCROLLER = self.scroll
        for name in ("intro", "dashboard", "files", "duplicates", "charts", "organize", "export"):
            self.pages[name] = tk.Frame(self.scroll.inner, bg=SURFACE)

        self.toast_label = tk.Label(root, bg=TEXT, fg=SURFACE, font=FN(13, "medium"),
                                    padx=S(24), pady=S(12), bd=0)
        root.bind_all("<MouseWheel>", self.scroll.on_wheel)
        root.bind_all("<Button-4>", self.scroll.on_wheel)
        root.bind_all("<Button-5>", self.scroll.on_wheel)
        root.bind("<Escape>", lambda e: self.close_modal())
        root.bind("<Button-1>", self.maybe_close_modal, add="+")

        self.reload_state()
        self.show_page("dashboard")

    # Functions that build the left sidebar, top bar, and bottom status bar
    def build_sidebar(self, shell):
        sidebar = tk.Frame(shell, bg=BG, width=S(240))
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Frame(shell, bg=BORDER, width=S(1)).pack(side="left", fill="y")

        logo = tk.Frame(sidebar, bg=BG)
        logo.pack(fill="x", padx=S(20), pady=(S(24), S(20)))
        lbl(logo, "FileOrganizer", 15, "semibold", TEXT, BG).pack(anchor="w")
        lbl(logo, sp("EF101-P19"), 10, "medium", TEXT_MUTED, BG).pack(anchor="w", pady=(S(4), 0))

        nav = tk.Frame(sidebar, bg=BG)
        nav.pack(fill="x", pady=(S(12), 0))
        lbl(nav, sp("MAIN"), 10, "semibold", TEXT_MUTED, BG).pack(anchor="w", padx=S(20),
                                                                   pady=(0, S(8)))
        for key, text, icon_name in NAV:
            item = NavItem(nav, text, icon_name, lambda k=key: self.navigate(k))
            item.pack(fill="x", padx=S(10), pady=(0, S(2)))
            self.nav_items[key] = item

        bottom = tk.Frame(sidebar, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=S(20), pady=S(20))
        Btn(bottom, "Scan Folder", self.choose_and_scan, icon_name="upload",
            kind="primary").pack(fill="x")

    def build_topbar(self, main):
        bar_frame = tk.Frame(main, bg=SURFACE)
        bar_frame.pack(fill="x")
        row = tk.Frame(bar_frame, bg=SURFACE)
        row.pack(fill="x", padx=S(32), pady=S(16))

        self.path_label = lbl(row, "No folder selected", 13, "medium", TEXT_MUTED, SURFACE)
        self.path_label.pack(side="left")

        right = tk.Frame(row, bg=SURFACE)
        right.pack(side="right")
        self.scan_time_label = lbl(right, "", 12, "medium", TEXT_MUTED, SURFACE)
        self.scan_time_label.pack(side="left", padx=(0, S(16)))
        self.rescan_btn = Btn(right, "Rescan", self.rescan, icon_name="refresh")
        self.rescan_btn.pack(side="left")

        # This progress bar stays hidden until a folder scan actually starts
        self.progress_wrap = tk.Frame(row, bg=SURFACE)
        self.scan_status = lbl(self.progress_wrap, "Scanning...", 12, "medium", TEXT_SEC, SURFACE,
                               anchor="w")
        self.scan_status.pack(fill="x")
        self.progress = ProgressBar(self.progress_wrap)
        self.progress.pack(fill="x", pady=S(8))
        hline(main, BORDER_LIGHT)

    def build_statusbar(self, main):
        wrap = tk.Frame(main, bg=BG)
        wrap.pack(side="bottom", fill="x")
        hline(wrap, BORDER)
        row = tk.Frame(wrap, bg=BG)
        row.pack(fill="x", padx=S(32), pady=S(10))

        item = tk.Frame(row, bg=BG)
        item.pack(side="left")
        self.status_dot = tk.Canvas(item, width=S(6), height=S(6), bg=BG,
                                    highlightthickness=0, bd=0)
        self.status_dot_shape = self.status_dot.create_oval(0, 0, S(6), S(6), fill=TEXT_MUTED,
                                                            width=0)
        self.status_dot.pack(side="left", padx=(0, S(6)))
        self.status_text = lbl(item, "No folder scanned", 12, "medium", TEXT_MUTED, BG)
        self.status_text.pack(side="left")

        self.status_folder = tk.Frame(row, bg=BG)
        if PIL_OK:
            self.status_folder_icon = icon("folder", 12, TEXT_MUTED)
            tk.Label(self.status_folder, image=self.status_folder_icon, bg=BG, bd=0).pack(
                side="left", padx=(0, S(6)))
        self.status_folder_name = lbl(self.status_folder, "", 12, "medium", TEXT_MUTED, BG)
        self.status_folder_name.pack(side="left")

    # Helper functions for popup toast messages, switching screens, and refreshing numbers
    def toast(self, message):
        self.toast_label.configure(text=message)
        self.toast_label.place(relx=0.5, rely=1.0, y=-S(40), anchor="s")
        self.toast_label.lift()
        if self.toast_job:
            self.root.after_cancel(self.toast_job)
        self.toast_job = self.root.after(2400, self.toast_label.place_forget)

    def navigate(self, page):
        if not self.has_files and page != "dashboard":
            self.toast("Scan a folder first, or load demo data")
            return
        self.show_page(page)

    def show_page(self, page):
        self.close_modal()
        self.current = page
        for key, item in self.nav_items.items():
            item.set_active(key == page)
        for frame in self.pages.values():
            frame.pack_forget()

        key = "intro" if (page == "dashboard" and not self.has_files) else page
        if key == "intro":
            self.render_intro()
        elif page == "dashboard":
            self.render_dashboard()
        elif page == "files":
            self.render_files_page()
        elif page == "duplicates":
            self.render_duplicates()
        elif page == "charts":
            self.render_charts()
        elif page == "organize":
            self.render_organize()
        elif page == "export":
            self.render_export()
        self.pages[key].pack(fill="both", expand=True, padx=S(40), pady=S(32))
        self.scroll.scroll_to_top()

    def reload_state(self):
        """Reads the latest file counts from the database and updates the sidebar and status bar."""
        count, total = database.get_totals()
        self.has_files = count > 0
        self.meta = database.get_meta()
        groups, extra, waste = database.get_duplicate_stats()

        self.nav_items["files"].set_count(f"{count:,}" if count else "0")
        self.nav_items["duplicates"].set_count(str(extra))

        root_folder = self.meta.get("root_folder", "")
        if root_folder:
            self.folder = root_folder if os.path.isdir(root_folder) else self.folder
        shown = root_folder or ("Inventory from an earlier scan" if self.has_files else "")
        self.path_label.configure(
            text=ellipsize("Root: " + shown if root_folder else shown or "No folder selected",
                           FM(13, "medium"), S(460)))

        scan_date = self.meta.get("scan_date", "")
        self.scan_time_label.configure(text=f"Scanned {scan_date}" if scan_date else "")

        if self.has_files:
            seconds = self.meta.get("scan_seconds")
            self.status_text.configure(
                text=f"{count:,} files scanned in {float(seconds):.1f}s" if seconds
                else f"{count:,} files in the inventory",
                fg=TEXT_MUTED)
            self.status_dot.itemconfigure(self.status_dot_shape, fill=TEXT)
            if root_folder:
                self.status_folder_name.configure(text=os.path.basename(root_folder.rstrip("/\\"))
                                                  or root_folder)
                self.status_folder.pack(side="left", padx=(S(24), 0))
            else:
                self.status_folder.pack_forget()
        else:
            self.status_text.configure(text="No folder scanned")
            self.status_dot.itemconfigure(self.status_dot_shape, fill=TEXT_MUTED)
            self.status_folder.pack_forget()

        self.refresh_filter_options()

    # Folder scanning runs in a background thread so the window never freezes while scanning
    def choose_and_scan(self):
        folder = filedialog.askdirectory(
            title="Select a folder to scan", mustexist=True,
            initialdir=self.folder if self.folder and os.path.isdir(self.folder)
            else os.path.expanduser("~"))
        if folder:
            self.start_scan(folder)

    def rescan(self):
        if self.folder and os.path.isdir(self.folder):
            self.start_scan(self.folder)
        else:
            self.choose_and_scan()

    def start_scan(self, folder):
        if self.scanning:
            self.toast("A scan is already running")
            return
        self.scanning = True
        self.folder = folder
        self.scan_status.configure(text="Reading files…")
        self.progress_wrap.pack(side="left", fill="x", expand=True, padx=S(24))
        self.progress.start()
        self.rescan_btn.set_enabled(False)
        self.path_label.configure(text=ellipsize("Root: " + folder, FM(13, "medium"), S(300)))
        self.scan_queue = queue.Queue()
        threading.Thread(target=self._scan_worker, args=(folder, self.scan_queue),
                         daemon=True).start()
        self.root.after(60, self._poll_scan)

    def _scan_worker(self, folder, q):
        started = time.time()
        try:
            results, errors, folder_count = scan_folder(
                folder, progress=lambda n: q.put(("read", n)))
            database.save_files(results)

            q.put(("hashing", 0, 0))
            hashes, hash_errors = duplicate.hash_candidates(
                results, progress=lambda done, total: q.put(("hash", done, total)))
            database.save_hashes(hashes)

            seconds = time.time() - started
            scan_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            database.set_meta(root_folder=folder,
                              scan_date=scan_now,
                              scan_seconds=f"{seconds:.2f}", folder_count=folder_count,
                              unreadable=len(errors) + len(hash_errors))
            database.save_scan_snapshot(folder, scan_now)
            q.put(("done", len(results), len(errors) + len(hash_errors), seconds))
        except Exception as error:               # Send any unexpected error back to the main window safely
            q.put(("error", str(error)))

    def _poll_scan(self):
        finished = False
        try:
            while True:
                message = self.scan_queue.get_nowait()
                kind = message[0]
                if kind == "read":
                    self.scan_status.configure(text=f"Reading files… {message[1]:,}")
                elif kind == "hashing":
                    self.scan_status.configure(text="Computing SHA-256 fingerprints for duplicates…")
                elif kind == "hash":
                    done, total = message[1], message[2]
                    self.progress.set(done / total if total else 1)
                    self.scan_status.configure(text=f"Computing hashes… {done:,}/{total:,}")
                elif kind == "done":
                    finished = True
                    self._finish_scan(message[1], message[2], message[3])
                elif kind == "error":
                    finished = True
                    self._end_scan_ui()
                    self.toast("Scan failed: " + message[1])
        except queue.Empty:
            pass
        if not finished:
            self.root.after(60, self._poll_scan)

    def _end_scan_ui(self):
        self.scanning = False
        self.progress.stop()
        self.progress_wrap.pack_forget()
        self.rescan_btn.set_enabled(True)

    def _finish_scan(self, count, unreadable, seconds):
        self._end_scan_ui()
        self.photo_cache.clear()
        self.reset_filter_state()
        self.reload_state()
        self.show_page("dashboard")
        extra = f", {unreadable} could not be read" if unreadable else ""
        self.toast(f"Scanned {count:,} files in {seconds:.1f}s{extra}")

    # Creates sample demo files in the database so you can test the app right away
    def load_demo(self):
        names = {
            "Image": ["photo", "portrait", "screenshot", "banner", "icon", "wallpaper", "render", "scan"],
            "Document": ["report", "invoice", "readme", "notes", "contract", "manual", "syllabus", "budget", "thesis"],
            "Audio": ["track", "recording", "podcast", "sample", "beat", "interview", "song"],
            "Video": ["clip", "recording", "tutorial", "vlog", "presentation", "demo", "meeting"],
            "Archive": ["backup", "project", "release", "assets", "export", "source", "media"],
            "Other": ["config", "data", "script", "stylesheet", "build", "output", "log", "temp"],
        }
        exts = {
            "Image": [".jpg", ".png", ".gif", ".webp", ".svg", ".tiff", ".bmp"],
            "Document": [".pdf", ".docx", ".txt", ".xlsx", ".pptx", ".md", ".csv", ".html"],
            "Audio": [".mp3", ".wav", ".flac", ".m4a", ".ogg"],
            "Video": [".mp4", ".mkv", ".avi", ".mov", ".webm"],
            "Archive": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Other": [".json", ".xml", ".log", ".cfg", ".sh", ".css", ".js", ".py"],
        }
        folders = ["Photos/2024", "Photos/2023", "Photos/Travel", "Documents/Work",
                   "Documents/Personal", "Documents/Reports", "Music/Albums", "Music/Podcasts",
                   "Videos/Family", "Videos/Projects", "Archives/Backups", "Archives/Old",
                   "Downloads", "Desktop", "Misc/Other", "Misc/Temp"]
        sizes = [500, 5000, 50000, 500000, 5000000, 50000000]

        rows, used = [], set()

        def add(category, name, ext, size, folder, when, digest=None):
            path = f"DemoFolder/{folder}/{name}{ext}"
            if path in used:
                return
            used.add(path)
            rows.append(dict(name=name + ext, path=path, extension=ext, category=category,
                             size_bytes=size, created=when, modified=when,
                             parent_folder=folder.split("/")[-1], digest=digest))

        categories = list(names)
        while len(rows) < 250:
            category = categories[len(rows) % len(categories)]
            base = random.choice(names[category])
            when = datetime.fromtimestamp(time.time() - random.random() * 5 * 365 * 86400)
            add(category, f"{base}_{random.randint(1, 9999)}", random.choice(exts[category]),
                int(random.choice(sizes) * (0.5 + random.random())),
                random.choice(folders), when.strftime("%Y-%m-%d %H:%M"))

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for group in range(5):                                    # Add 5 duplicate file groups for testing the Duplicates screen
            category = categories[group % len(categories)]
            digest = "%064x" % random.getrandbits(256)
            size = random.randint(100000, 5000000)
            for copy in range(random.randint(2, 3)):
                add(category, f"duplicate_group_{group + 1}_copy{copy + 1}",
                    exts[category][0], size, random.choice(folders), now[:16], digest)

        database.save_files(rows)
        database.save_hashes({r["path"]: r["digest"] for r in rows if r["digest"]})
        database.set_meta(root_folder="DemoFolder", scan_date=now, scan_seconds="1.24",
                          folder_count=len(folders), unreadable=0)
        database.save_scan_snapshot("DemoFolder", now)
        self.photo_cache.clear()
        self.reset_filter_state()
        self.reload_state()
        self.show_page("dashboard")
        self.toast(f"Demo loaded: {len(rows)} files across {len(folders) + 1} folders")

    # Welcome screen shown before any folder has been scanned
    def render_intro(self):
        page = self.pages["intro"]
        clear(page)
        box = tk.Frame(page, bg=SURFACE)
        box.place(relx=0.5, rely=0.5, anchor="center")
        if PIL_OK:
            self.intro_icon = icon("folder-down", 48, TEXT_MUTED, stroke=1.5)
            tk.Label(box, image=self.intro_icon, bg=SURFACE, bd=0).pack(pady=(0, S(12)))
        lbl(box, "Digital File Organizer", 28, "semibold", TEXT, SURFACE).pack()
        lbl(box, "Select a folder to scan. The app will recursively explore all subfolders, "
                 "classify your files, detect duplicates, and build a complete inventory.",
            15, "regular", TEXT_SEC, SURFACE, wraplength=S(420), justify="center").pack(
            pady=(S(12), 0))
        buttons = tk.Frame(box, bg=SURFACE)
        buttons.pack(pady=(S(24), 0))
        Btn(buttons, "Choose Folder", self.choose_and_scan, icon_name="folder",
            kind="primary").pack(side="left", padx=S(6))
        Btn(buttons, "Load Demo Data", self.load_demo, icon_name="bolt").pack(side="left",
                                                                            padx=S(6))

    # Dashboard screen showing the 4 summary cards, category bars, and Top 10 largest files
    def page_header(self, page, title, right_text=""):
        head = tk.Frame(page, bg=SURFACE)
        head.pack(fill="x", pady=(0, S(24)))
        lbl(head, title, 20, "semibold", TEXT, SURFACE).pack(side="left")
        right = lbl(head, right_text, 12, "medium", TEXT_MUTED, SURFACE)
        right.pack(side="right")
        return head, right

    def card_title(self, parent, text):
        lbl(parent, sp(text.upper()), 11, "semibold", TEXT_MUTED, parent.cget("bg")).pack(
            anchor="w", pady=(0, S(12)))

    def render_dashboard(self):
        page = self.pages["dashboard"]
        clear(page)
        count, total = database.get_totals()
        folder_count = int(self.meta.get("folder_count", 0) or 0)
        categories = database.get_category_summary()
        groups, extra, waste = database.get_duplicate_stats()
        scan_date = self.meta.get("scan_date", "")

        self.page_header(page, "Dashboard", f"Scanned {scan_date}" if scan_date else "")

        top = max(categories, key=lambda c: c[2]) if categories else None
        metrics = [
            ("Total Files", f"{count:,}", f"{folder_count:,} folders"),
            ("Total Storage", fmt_size(total),
             f"{fmt_size(total / count)} avg per file" if count else "—"),
            ("Duplicates Found", f"{extra:,}", f"{fmt_size(waste)} recoverable"),
            ("Categories", str(len(categories)),
             f"largest: {top[0]} ({fmt_size(top[2])})" if top else "—"),
        ]
        grid = ResponsiveGrid(page, min_width=180, gap=16)
        grid.pack(fill="x", pady=(0, S(16)))
        cards = []
        for label, value, sub in metrics:
            outer, body = make_card(grid, padding=20)
            lbl(body, sp(label.upper()), 11, "semibold", TEXT_MUTED, SURFACE).pack(
                anchor="w", pady=(0, S(8)))
            lbl(body, value, 28, "semibold", TEXT, SURFACE).pack(anchor="w")
            lbl(body, sub, 12, "regular", TEXT_SEC, SURFACE).pack(anchor="w", pady=(S(6), 0))
            cards.append(outer)
        grid.set_items(cards)

        # Storage bars broken down by file category
        outer, body = make_card(page, padding=24)
        outer.pack(fill="x", pady=(S(16), S(24)))
        self.card_title(body, "By Category")
        for category, number, size in categories:
            row = tk.Frame(body, bg=SURFACE)
            row.pack(fill="x", pady=S(6))
            row.columnconfigure(1, weight=1)
            name = tk.Frame(row, bg=SURFACE, width=S(110))
            name.grid(row=0, column=0, sticky="w")
            tk.Frame(name, bg=CAT_COLORS.get(category, "#CCCCCC"), width=S(8), height=S(8)).pack(
                side="left", padx=(0, S(8)))
            lbl(name, category, 13, "medium", TEXT, SURFACE).pack(side="left")
            name.grid_propagate(False)
            row.columnconfigure(0, minsize=S(118))
            bar(row, size / total if total else 0, CAT_COLORS.get(category, "#CCCCCC")).grid(
                row=0, column=1, sticky="ew", padx=S(12))
            lbl(row, fmt_size(size), 13, "regular", TEXT_SEC, SURFACE, anchor="e").grid(
                row=0, column=2, sticky="e", padx=(0, S(12)))
            row.columnconfigure(2, minsize=S(92))
            lbl(row, f"{number:,} file" + ("" if number == 1 else "s"), 12, "regular", TEXT_MUTED, SURFACE, anchor="e").grid(
                row=0, column=3, sticky="e")
            row.columnconfigure(3, minsize=S(72))

        # Card listing the 10 largest individual files
        outer, body = make_card(page, padding=24)
        outer.pack(fill="x")
        self.card_title(body, "10 Largest Files")
        largest = database.get_largest_files(10)
        biggest = largest[0]["size_bytes"] if largest else 1
        for rank, f in enumerate(largest, start=1):
            row = tk.Frame(body, bg=SURFACE, cursor="hand2")
            row.pack(fill="x", pady=S(6))
            row.columnconfigure(2, weight=1)
            row.columnconfigure(0, minsize=S(28))
            row.columnconfigure(1, minsize=S(280))
            lbl(row, str(rank), 12, "semibold", TEXT_MUTED, SURFACE).grid(row=0, column=0,
                                                                          sticky="w")
            lbl(row, ellipsize(f["name"], FM(13, "medium"), S(270)), 13, "medium", TEXT,
                SURFACE).grid(row=0, column=1, sticky="w")
            bar(row, f["size_bytes"] / biggest if biggest else 0,
                CAT_COLORS.get(f["category"], "#CCCCCC")).grid(row=0, column=2, sticky="ew",
                                                              padx=S(12))
            lbl(row, fmt_size(f["size_bytes"]), 13, "medium", TEXT_SEC, SURFACE, anchor="e").grid(
                row=0, column=3, sticky="e")
            row.columnconfigure(3, minsize=S(72))
            bind_tree(row, "<Button-1>", lambda e, file_id=f["id"]: self.show_details(file_id))

    # All Files screen with search box, dropdown filters, sorting, and List or Grid view
    def reset_filter_state(self):
        self.page_no = 1
        self.sort_key, self.sort_desc = "name", False
        if self.filters_built:
            self.search.set("")
            self.category_select.set(CATEGORY_OPTIONS[0][0])
            self.ext_select.set("All extensions")
            self.folder_select.set("All folders")
            for box in (self.min_input, self.max_input, self.from_input, self.to_input):
                box.set("")
                box.set_error(False)
            self.sync_sort_select()

    def refresh_filter_options(self):
        if not self.filters_built:
            return
        self.ext_select.set_values(["All extensions"] + database.get_extensions())
        self.folder_select.set_values(["All folders"] + database.get_folders())

    def render_files_page(self):
        page = self.pages["files"]
        if not self.filters_built:
            self.build_files_controls(page)
            self.filters_built = True
            self.refresh_filter_options()
        self.render_results()

    def build_files_controls(self, page):
        head = tk.Frame(page, bg=SURFACE)
        head.pack(fill="x", pady=(0, S(24)))
        lbl(head, "All Files", 20, "semibold", TEXT, SURFACE).pack(side="left")
        right = tk.Frame(head, bg=SURFACE)
        right.pack(side="right")
        self.results_label = lbl(right, "", 13, "medium", TEXT_MUTED, SURFACE)
        self.results_label.pack(side="left", padx=(0, S(16)))
        self.list_btn = Btn(right, "List", lambda: self.set_view("list"), px=14, py=6)
        self.grid_btn = Btn(right, "Grid", lambda: self.set_view("grid"), px=14, py=6)
        self.list_btn.pack(side="left")
        self.grid_btn.pack(side="left", padx=(S(-1), 0))
        self.update_view_buttons()

        # First filter row with search box and main dropdowns
        self.flow = Flow(page, gap_x=12, gap_y=12)
        self.flow.pack(fill="x")
        self.search = TextInput(self.flow, 244, "Search name, extension, path...",
                                self.filters_changed)
        self.category_select = Select(self.flow, [c[0] for c in CATEGORY_OPTIONS],
                                      self.filters_changed, width=12)
        self.sort_select = Select(self.flow, [o[0] for o in SORT_OPTIONS],
                                  self.sort_changed, width=11)
        self.ext_select = Select(self.flow, ["All extensions"], self.filters_changed, width=12)
        self.clear_btn = Btn(self.flow, "Clear", self.clear_filters)
        self.more_btn = Btn(self.flow, "More filters", self.toggle_more)
        for widget in (self.search, self.category_select, self.sort_select, self.ext_select,
                       self.clear_btn, self.more_btn):
            self.flow.add(widget)

        # Second filter row that opens when the user clicks More filters
        self.more_flow = Flow(page, gap_x=12, gap_y=12)
        self.folder_select = Select(self.more_flow, ["All folders"], self.filters_changed,
                                    width=20)
        self.min_input = TextInput(self.more_flow, 130, "Min size (MB)", self.filters_changed)
        self.max_input = TextInput(self.more_flow, 130, "Max size (MB)", self.filters_changed)
        self.from_input = TextInput(self.more_flow, 160, "From  YYYY-MM-DD", self.filters_changed)
        self.to_input = TextInput(self.more_flow, 160, "To  YYYY-MM-DD", self.filters_changed)
        for widget in (self.folder_select, self.min_input, self.max_input, self.from_input,
                       self.to_input):
            self.more_flow.add(widget)

        self.results_holder = tk.Frame(page, bg=SURFACE)
        self.results_holder.pack(fill="x", pady=(S(24), 0))
        self.sync_sort_select()

    def toggle_more(self):
        self.more_open = not self.more_open
        if self.more_open:
            self.more_flow.pack(fill="x", pady=(S(12), 0), after=self.flow)
        else:
            self.more_flow.pack_forget()
        self.more_btn.set_text("Fewer filters" if self.more_open else "More filters")

    def update_view_buttons(self):
        self.list_btn.set_kind("primary" if self.view_mode == "list" else "default")
        self.grid_btn.set_kind("primary" if self.view_mode == "grid" else "default")

    def set_view(self, mode):
        if mode == "grid" and not PIL_OK:
            self.toast("Grid view needs Pillow:  pip install pillow")
            return
        if mode != self.view_mode:
            self.view_mode = mode
            self.update_view_buttons()
            self.render_results()

    def clear_filters(self):
        self.page_no = 1
        self.sort_key, self.sort_desc = "name", False
        self.reset_filter_state()
        self.render_results()

    def filters_changed(self, immediate=True):
        """Refreshes the file list when filters change, waiting a tiny moment while typing so it stays smooth."""
        if self.filter_after:
            self.root.after_cancel(self.filter_after)
            self.filter_after = None
        self.page_no = 1
        if immediate:
            self.render_results()
        else:
            self.filter_after = self.root.after(220, self.render_results)

    def sort_changed(self):
        label = self.sort_select.get()
        for text, key, desc in SORT_OPTIONS:
            if text == label:
                self.sort_key, self.sort_desc = key, desc
        self.page_no = 1
        self.render_results()

    def sync_sort_select(self):
        for text, key, desc in SORT_OPTIONS:
            if key == self.sort_key and desc == self.sort_desc:
                self.sort_select.set(text)
                return

    def sort_by_header(self, key):
        if self.sort_key == key:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_key = key
            self.sort_desc = key in ("size", "date")      # Default to biggest or newest first when clicking Size or Date
        self.page_no = 1
        self.sync_sort_select()
        self.render_results()

    def read_filters(self):
        """Reads all filter boxes and checks that any size numbers or dates are typed in the right format."""
        problems = False

        def number(box):
            nonlocal problems
            text = box.value()
            box.set_error(False)
            if not text:
                return None
            try:
                return int(float(text) * 1024 * 1024)
            except ValueError:
                box.set_error(True)
                problems = True
                return None

        def date(box):
            nonlocal problems
            text = box.value()
            box.set_error(False)
            if not text:
                return ""
            try:
                datetime.strptime(text, "%Y-%m-%d")
                return text
            except ValueError:
                box.set_error(True)
                problems = True
                return ""

        category = dict(CATEGORY_OPTIONS).get(self.category_select.get(), "All")
        ext = self.ext_select.get()
        folder = self.folder_select.get()
        args = dict(
            name=self.search.value(),
            category=category,
            extension="All" if ext == "All extensions" else ext,
            folder="All" if folder == "All folders" else folder,
            min_size=number(self.min_input), max_size=number(self.max_input),
            date_from=date(self.from_input), date_to=date(self.to_input),
        )
        return None if problems else args

    def render_results(self):
        self.filter_after = None
        if self.current != "files" or not self.filters_built:
            return
        args = self.read_filters()
        if args is None:
            return                                     # Stop if the user typed an invalid number or date
        holder = self.results_holder
        clear(holder)
        self.hover_row = None

        total_matching, matching_bytes = database.count_matching(**args)
        pages = max(1, -(-total_matching // PAGE_SIZE))
        self.page_no = max(1, min(self.page_no, pages))
        rows = database.search_files(
            **args, sort_by=SORT_DB_NAME[self.sort_key], descending=self.sort_desc,
            limit=PAGE_SIZE, offset=(self.page_no - 1) * PAGE_SIZE)

        self.results_label.configure(text=f"{total_matching:,} results")

        outer, body = make_card(holder, padding=0)
        outer.pack(fill="x")
        if not rows:
            empty = tk.Frame(body, bg=SURFACE)
            empty.pack(fill="x", pady=S(60))
            if PIL_OK:
                self.empty_icon = icon("sad", 32, blend(TEXT_MUTED, SURFACE, .5))
                tk.Label(empty, image=self.empty_icon, bg=SURFACE, bd=0).pack(pady=(0, S(16)))
            lbl(empty, "No files match these filters", 13, "regular", TEXT_MUTED, SURFACE).pack()
        elif self.view_mode == "list":
            self.build_table(body, rows)
        else:
            self.build_grid(body, rows)

        # Previous and Next page buttons at the bottom of the file list
        hline(body, BORDER_LIGHT)
        foot = tk.Frame(body, bg=SURFACE)
        foot.pack(fill="x", padx=S(24), pady=S(16))
        lbl(foot, f"Page {self.page_no} of {pages} ({total_matching:,} files)", 13, "medium",
            TEXT_SEC, SURFACE).pack(side="left")
        nxt = Btn(foot, "Next →", lambda: self.change_page(1))
        nxt.pack(side="right")
        prev = Btn(foot, "← Prev", lambda: self.change_page(-1))
        prev.pack(side="right", padx=(0, S(8)))
        prev.set_enabled(self.page_no > 1)
        nxt.set_enabled(self.page_no < pages)

    def change_page(self, step):
        self.page_no += step
        self.render_results()
        self.scroll.scroll_to_top()

    # Builds the rows and columns for List View
    def build_table(self, parent, rows):
        table = tk.Frame(parent, bg=SURFACE)
        table.pack(fill="x")
        widths = [None, 112, 78, 108, 116, 130, 96]
        # Give any leftover horizontal space to the File Name column
        available = max(self.scroll.canvas.winfo_width() - S(82), S(700))
        name_px = max(S(190), available - sum(S(w) for w in widths[1:]) - S(32))
        self.name_px = name_px
        for col, width in enumerate(widths):
            table.columnconfigure(col, weight=1 if col == 0 else 0,
                                  minsize=S(width) if width else name_px + S(32))

        heads = [("name", "Name"), ("type", "Type"), ("ext", "Ext"), ("size", "Size"),
                 ("date", "Modified"), ("folder", "Folder"), ("act", "Actions")]
        for col, (key, text) in enumerate(heads):
            sortable = key in ("name", "ext", "size", "date")
            arrow = ""
            if sortable:
                arrow = "  " + (("↓" if self.sort_desc else "↑") if self.sort_key == key else "↕")
            head = tk.Label(table, text=sp(text.upper()) + arrow, font=FN(11, "semibold"),
                            fg=ACCENT if (sortable and self.sort_key == key) else TEXT_MUTED,
                            bg=SURFACE, anchor="w", bd=0, highlightthickness=0,
                            cursor="hand2" if sortable else "")
            head.grid(row=0, column=col, sticky="ew", padx=S(16), pady=S(12))
            if sortable:
                head.bind("<Button-1>", lambda e, k=key: self.sort_by_header(k))
                head.bind("<Enter>", lambda e, w=head: w.configure(fg=ACCENT))
                head.bind("<Leave>", lambda e, w=head, k=key: w.configure(
                    fg=ACCENT if self.sort_key == k else TEXT_MUTED))
        tk.Frame(table, bg=BORDER, height=S(1)).grid(row=1, column=0, columnspan=7, sticky="ew")

        cell_pad = dict(padx=S(16), pady=S(12))
        for index, f in enumerate(rows):
            r = 2 + index * 2
            cells = []

            def cell(col):
                frame = tk.Frame(table, bg=SURFACE)
                frame.grid(row=r, column=col, sticky="nsew")
                cells.append(frame)
                return frame

            name = cell(0)
            lbl(name, ellipsize(f["name"], FM(13, "medium"), self.name_px), 13, "medium", TEXT,
                SURFACE, anchor="w").pack(anchor="w", padx=S(16), pady=(S(12), 0))
            lbl(name, ellipsize(f["path"], FM(11), self.name_px), 11, "regular", TEXT_MUTED, SURFACE,
                anchor="w").pack(anchor="w", padx=S(16), pady=(S(2), S(12)))

            kind = cell(1)
            badge = tk.Frame(kind, bg=SURFACE, highlightthickness=S(1), highlightbackground=BORDER)
            badge.pack(anchor="w", padx=S(16), expand=True)
            tk.Frame(badge, bg=CAT_COLORS.get(f["category"], "#CCCCCC"), width=S(7),
                     height=S(7)).pack(side="left", padx=(S(8), 0))
            badge_text = lbl(badge, (f["category"] or "Other").lower(), 11, "semibold", TEXT_SEC,
                             SURFACE)
            badge_text.pack(side="left", padx=(S(5), S(8)), pady=S(3))
            badge.lift()
            badge._noswap_children = True

            ext = cell(2)
            tk.Label(ext, text=f["extension"] or "—", font=mono(12), fg=TEXT_MUTED, bg=SURFACE,
                     bd=0, anchor="w").pack(anchor="w", expand=True, **cell_pad)

            size = cell(3)
            lbl(size, fmt_size(f["size_bytes"]), 13, "medium", TEXT_SEC, SURFACE).pack(
                anchor="w", padx=S(16), pady=(S(12), 0))
            lbl(size, f"{f['size_bytes']:,} B", 11, "regular", TEXT_MUTED, SURFACE).pack(
                anchor="w", padx=S(16), pady=(S(2), S(12)))

            when = cell(4)
            lbl(when, (f["modified_time"] or "—")[:10], 13, "regular", TEXT_SEC, SURFACE).pack(
                anchor="w", expand=True, **cell_pad)

            folder = cell(5)
            lbl(folder, ellipsize(f["parent_folder"] or "", FM(12), S(98)), 12, "regular",
                TEXT_MUTED, SURFACE).pack(anchor="w", expand=True, **cell_pad)

            actions = cell(6)
            details = Btn(actions, "Details", lambda file_id=f["id"]: self.show_details(file_id),
                          px=10, py=4, size=12)
            details.pack(anchor="w", padx=S(16), expand=True)

            tk.Frame(table, bg=BORDER_LIGHT, height=S(1)).grid(
                row=r + 1, column=0, columnspan=7, sticky="ew")

            for frame in cells:
                bind_tree(frame, "<Enter>", lambda e, c=cells: self.highlight_row(c))
                bind_tree(frame, "<Button-1>", lambda e, i=f["id"]: self.show_details(i))
                frame.configure(cursor="hand2")

    def highlight_row(self, cells):
        if self.hover_row is cells:
            return
        if self.hover_row is not None:
            for frame in self.hover_row:
                if frame.winfo_exists():
                    swap_bg(frame, GLOW, SURFACE)
        self.hover_row = cells
        for frame in cells:
            swap_bg(frame, SURFACE, GLOW)

    # Builds the square photo and file cards for Grid View
    def build_grid(self, parent, rows):
        wrap = tk.Frame(parent, bg=SURFACE)
        wrap.pack(fill="x", padx=S(24), pady=S(24))
        grid = ResponsiveGrid(wrap, min_width=170, gap=16)
        grid.pack(fill="x")
        cards = [self.build_file_card(grid, f) for f in rows]
        grid.set_items(cards)

    def thumbnail_for(self, f, size):
        key = (f["path"], size)
        if key in self.photo_cache:
            return self.photo_cache[key]
        tile = None
        if (f["extension"] or "").lower() in IMAGE_EXTENSIONS:
            tile = make_thumbnail(f["path"], S(size))
        if tile is None:
            tile = make_type_tile(f["category"], f["extension"] or "", S(size))
        self.photo_cache[key] = ImageTk.PhotoImage(tile)
        return self.photo_cache[key]

    def build_file_card(self, parent, f):
        outer = tk.Frame(parent, bg=BORDER, cursor="hand2")
        inner = tk.Frame(outer, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=S(1), pady=S(1))
        thumb_area = tk.Frame(inner, bg=ACCENT_SOFT)
        thumb_area.pack(fill="x")
        tk.Label(thumb_area, image=self.thumbnail_for(f, 120), bg=ACCENT_SOFT, bd=0).pack(
            pady=S(10))
        text = tk.Frame(inner, bg=SURFACE)
        text.pack(fill="both", expand=True, padx=S(12), pady=(S(10), S(12)))
        name = ellipsize_middle(f["name"], FM(12, "medium"), S(150) * 1.9)
        lbl(text, name, 12, "medium", TEXT, SURFACE, wraplength=S(150), justify="left",
            anchor="w").pack(anchor="w", fill="x")
        lbl(text, fmt_size(f["size_bytes"]), 11, "regular", TEXT_MUTED, SURFACE).pack(
            anchor="w", pady=(S(4), 0))

        def enter(event):
            outer.configure(bg=TEXT_MUTED)

        def leave(event):
            if not pointer_inside(outer, event):
                outer.configure(bg=BORDER)

        bind_tree(outer, "<Enter>", enter)
        bind_tree(outer, "<Leave>", leave)
        bind_tree(outer, "<Button-1>", lambda e, i=f["id"]: self.show_details(i))
        return outer

    # Opens a popup window with all file info, EXIF camera tags, and hash details when a file is clicked
    def show_details(self, file_id):
        f = database.get_file(file_id)
        if not f:
            return
        self.close_modal()
        rows = [
            ("Full path", f["path"]),
            ("File name", f["name"]),
            ("Extension", f["extension"] or "(none)"),
            ("Category", f["category"]),
            ("Size (bytes)", f"{f['size_bytes']:,} B"),
            ("Size (human)", fmt_size(f["size_bytes"])),
            ("Parent folder", f["parent_folder"]),
            ("Created", f["created_time"] or "Unknown"),
            ("Last modified", f["modified_time"] or "Unknown"),
        ]

        if (f["extension"] or "").lower() in IMAGE_EXTENSIONS and os.path.isfile(f["path"]):
            meta = image_metadata.read_image_metadata(f["path"])
            if meta.get("ok"):
                rows += [
                    ("Image format", f"{meta['format']} ({meta.get('mode', 'RGB')})"),
                    ("Image dimensions", f"{meta['width']} × {meta['height']} px"),
                    ("Megapixels", f"{meta['megapixels']} MP"),
                    ("Aspect ratio", meta["aspect"]),
                ]
                if meta["exif"]:
                    rows.append(("Camera", meta["camera"] or "Not recorded"))
                    if meta.get("lens"):
                        rows.append(("Lens model", meta["lens"]))
                    rows.append(("Captured", meta["captured"] or "Not recorded"))
                    if meta.get("iso"):
                        rows.append(("ISO speed", meta["iso"]))
                    if meta.get("aperture"):
                        rows.append(("Aperture", meta["aperture"]))
                    if meta.get("shutter"):
                        rows.append(("Shutter speed", meta["shutter"]))
                    if meta.get("focal_length"):
                        rows.append(("Focal length", meta["focal_length"]))
                    if meta.get("software"):
                        rows.append(("Software", meta["software"]))
                    rows.append(("GPS", "Present in the file" if meta["gps"] else "Not recorded"))
                else:
                    rows.append(("EXIF", "Unavailable (this image has no EXIF data)"))
            else:
                rows.append(("Image info", "Could not be read"))

        if f["hash"]:
            rows.append(("SHA-256 hash", f["hash"]))
            twins = [g for g in database.get_duplicate_groups() if any(x["id"] == f["id"] for x in g)]
            if twins:
                others = [x["path"] for x in twins[0] if x["id"] != f["id"]]
                rows.append(("Duplicate of", "\n".join(others)))
        elif f["size_bytes"] > 0:
            rows.append(("SHA-256 hash", "Not needed: no other file has this exact size"))

        modal = tk.Frame(self.root, bg=BORDER)
        inner = tk.Frame(modal, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=S(1), pady=S(1))
        body = tk.Frame(inner, bg=SURFACE)
        body.pack(fill="both", expand=True, padx=S(32), pady=S(28))

        head = tk.Frame(body, bg=SURFACE)
        head.pack(fill="x", pady=(0, S(16)))
        close = Btn(head, "×", self.close_modal, px=10, py=2, size=15)
        close.pack(side="right", anchor="n")
        lbl(head, ellipsize(f["name"], FM(18, "semibold"), S(370)), 18, "semibold", TEXT, SURFACE,
            anchor="w").pack(side="left", anchor="n")

        scroller = ScrollFrame(body)
        scroller.pack(fill="both", expand=True)
        for index, (key, value) in enumerate(rows):
            row = tk.Frame(scroller.inner, bg=SURFACE)
            row.pack(fill="x")
            lbl(row, key, 13, "medium", TEXT_MUTED, SURFACE, anchor="nw", justify="left").pack(
                side="left", anchor="n", padx=(0, S(12)), pady=S(10))
            row.winfo_children()[0].configure(width=0)
            lbl(row, value, 13, "regular", TEXT, SURFACE, wraplength=S(300), justify="left",
                anchor="nw").pack(side="left", anchor="n", pady=S(10), fill="x", expand=True)
            hline(scroller.inner, BORDER_LIGHT)
            row.winfo_children()[0].configure(width=16)

        self.root.update_idletasks()
        wanted = scroller.inner.winfo_reqheight()
        limit = int(self.root.winfo_height() * 0.68) - S(90)
        scroller.canvas.configure(height=min(wanted, limit))
        modal.place(relx=0.5, rely=0.5, anchor="center", width=S(560))
        modal.lift()
        self.modal = modal
        self.modal_opened_at = time.time()

    def close_modal(self):
        if self.modal is not None:
            self.modal.destroy()
            self.modal = None

    def maybe_close_modal(self, event):
        """Closes the details popup when the user clicks anywhere outside the popup box."""
        if self.modal is None or time.time() - self.modal_opened_at < 0.25:
            return
        widget = event.widget
        while widget is not None:
            if widget is self.modal:
                return
            widget = getattr(widget, "master", None)
        self.close_modal()

    # Duplicates screen showing all identical twin file groups and their SHA 256 fingerprint
    def render_duplicates(self):
        page = self.pages["duplicates"]
        clear(page)
        groups = database.get_duplicate_groups()
        _, extra, waste = database.get_duplicate_stats()
        summary = (f"{len(groups)} groups · {extra} extra copies · {fmt_size(waste)} recoverable"
                   if groups else "No duplicates found")
        self.page_header(page, "Duplicate Files", summary)

        outer, body = make_card(page, padding=20, bg=BG)
        outer.pack(fill="x", pady=(0, S(24)))
        lbl(body, "How duplicates are detected & reviewed", 13, "semibold", TEXT, BG).pack(anchor="w")
        lbl(body, "Files are first compared by size (fast check). For files with matching sizes, "
                  "a SHA-256 cryptographic hash is computed and compared — this is the fingerprint "
                  "of the file's content. The first copy is marked KEEP, and you can inspect Details "
                  "or safely move extra COPY files into the Quarantine folder without permanent deletion.",
            13, "regular", TEXT_SEC, BG, wraplength=S(800), justify="left", anchor="w").pack(
            anchor="w", fill="x", pady=(S(8), 0))
        body.bind("<Configure>", lambda e: [w.configure(wraplength=max(200, e.width - 4))
                                            for w in body.winfo_children()[1:]])

        if not groups:
            empty = tk.Frame(page, bg=SURFACE)
            empty.pack(fill="x", pady=S(60))
            if PIL_OK:
                self.dup_empty_icon = icon("check-circle", 32, blend(TEXT_MUTED, SURFACE, .5))
                tk.Label(empty, image=self.dup_empty_icon, bg=SURFACE, bd=0).pack(pady=(0, S(16)))
            lbl(empty, "No duplicate files detected.", 13, "regular", TEXT_MUTED, SURFACE).pack()
            return

        shown = groups[:150]
        for group in shown:
            self.build_dup_group(page, group)
        if len(groups) > len(shown):
            lbl(page, f"… and {len(groups) - len(shown)} more groups (the 150 biggest are shown)",
                13, "medium", TEXT_MUTED, SURFACE).pack(anchor="w", pady=S(8))

    def build_dup_group(self, page, group):
        size = group[0]["size_bytes"]
        waste = size * (len(group) - 1)
        outer = tk.Frame(page, bg=BORDER)
        outer.pack(fill="x", pady=(0, S(16)))
        inner = tk.Frame(outer, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=S(1), pady=S(1))

        header = tk.Frame(inner, bg=BG, cursor="hand2")
        header.pack(fill="x")
        row = tk.Frame(header, bg=BG)
        row.pack(fill="x", padx=S(20), pady=S(16))
        if PIL_OK:
            self.dup_icons = getattr(self, "dup_icons", {})
            self.dup_icons["copy"] = icon("copy", 16, TEXT)
            tk.Label(row, image=self.dup_icons["copy"], bg=BG, bd=0).pack(side="left",
                                                                         padx=(0, S(12)))
        lbl(row, f"{len(group)} identical files — {fmt_size(size)} each", 14, "semibold", TEXT,
            BG).pack(side="left")
        arrow = lbl(row, "▼", 10, "regular", TEXT_MUTED, BG)
        arrow.pack(side="right", padx=(S(12), 0))
        lbl(row, f"{fmt_size(waste)} wasted", 12, "medium", TEXT_SEC, BG).pack(side="right")

        holder = tk.Frame(inner, bg=SURFACE)
        state = {"open": False, "built": False}

        def toggle(event=None):
            state["open"] = not state["open"]
            if state["open"]:
                if not state["built"]:
                    self.fill_dup_group(holder, group)
                    state["built"] = True
                holder.pack(fill="x")
                hline_top.pack(fill="x", before=holder)
            else:
                holder.pack_forget()
                hline_top.pack_forget()
            arrow.configure(text="▲" if state["open"] else "▼")

        hline_top = tk.Frame(inner, bg=BORDER, height=S(1))
        for widget in (header, row, *row.winfo_children()):
            widget.bind("<Button-1>", toggle)

    def quarantine_copy(self, file_row):
        """Bonus Feature: Safely moves a duplicate copy into the Quarantine folder and refreshes the screen."""
        dst = organizer.quarantine_duplicate_file(file_row)
        self.reload_state()
        self.render_duplicates()
        self.toast(f"Moved copy to Quarantine: {os.path.basename(dst)}")

    def fill_dup_group(self, holder, group):
        body = tk.Frame(holder, bg=SURFACE)
        body.pack(fill="x", padx=S(20), pady=S(16))
        line = tk.Frame(body, bg=SURFACE)
        line.pack(fill="x", pady=(0, S(12)))
        lbl(line, "SHA-256: ", 12, "regular", TEXT_MUTED, SURFACE).pack(side="left")
        tk.Label(line, text=group[0]["hash"], font=mono(11), fg=TEXT_MUTED, bg=SURFACE,
                 bd=0).pack(side="left")
        for index, f in enumerate(group):
            row = tk.Frame(body, bg=SURFACE)
            row.pack(fill="x")
            lbl(row, "KEEP" if index == 0 else "COPY", 11, "semibold",
                TEXT if index == 0 else TEXT_MUTED, SURFACE, width=6, anchor="w").pack(
                side="left", pady=S(8))
            lbl(row, ellipsize(f["path"], FM(13, "medium"), S(360)), 13, "medium", TEXT,
                SURFACE, anchor="w").pack(side="left", pady=S(8))
            Btn(row, "Details", lambda file_id=f["id"]: self.show_details(file_id), px=10, py=4,
                size=11).pack(side="right", pady=S(4))
            if index > 0:
                Btn(row, "Quarantine Copy", lambda item=f: self.quarantine_copy(item),
                    kind="danger", px=10, py=4, size=11).pack(side="right", padx=(0, S(8)), pady=S(4))
            lbl(row, fmt_size(f["size_bytes"]), 13, "regular", TEXT_SEC, SURFACE).pack(
                side="right", padx=S(12))
            if index < len(group) - 1:
                hline(body, BORDER_LIGHT)
        lbl(body, "Safe Review Workflow: Quarantining moves extra copies into Duplicate_Quarantine without deleting originals.",
            12, "regular", TEXT_MUTED, SURFACE).pack(anchor="w", pady=(S(12), 0))

    # Visual Summaries (Charts) page showing Category Storage, Size Distribution, Top Extensions, and Activity Timeline
    def render_charts(self):
        page = self.pages["charts"]
        clear(page)
        count, total = database.get_totals()
        self.page_header(page, "Visual Summaries", f"{count:,} files · {fmt_size(total)} total")

        # 1. Storage by Category Breakdown
        cat_data = charts.get_storage_by_category()
        outer, body = make_card(page, padding=24)
        outer.pack(fill="x", pady=(0, S(20)))
        self.card_title(body, "Storage Breakdown by Category")
        for item in cat_data:
            row = tk.Frame(body, bg=SURFACE)
            row.pack(fill="x", pady=S(6))
            row.columnconfigure(1, weight=1)
            row.columnconfigure(0, minsize=S(120))
            row.columnconfigure(2, minsize=S(100))
            row.columnconfigure(3, minsize=S(110))

            left = tk.Frame(row, bg=SURFACE)
            left.grid(row=0, column=0, sticky="w")
            tk.Frame(left, bg=CAT_COLORS.get(item["category"], "#CCCCCC"), width=S(8), height=S(8)).pack(
                side="left", padx=(0, S(8)))
            lbl(left, item["category"], 13, "medium", TEXT, SURFACE).pack(side="left")

            bar(row, item["percentage"] / 100.0, CAT_COLORS.get(item["category"], "#CCCCCC")).grid(
                row=0, column=1, sticky="ew", padx=S(12))
            lbl(row, f"{item['size_readable']} ({item['percentage']}%)", 13, "medium", TEXT_SEC,
                SURFACE, anchor="e").grid(row=0, column=2, sticky="e", padx=(0, S(12)))
            lbl(row, f"{item['count']:,} files", 12, "regular", TEXT_MUTED, SURFACE,
                anchor="e").grid(row=0, column=3, sticky="e")

        # 2. File Size Distribution Tiers (Small, Medium, Large, Huge)
        size_data = charts.get_size_distribution()
        outer, body = make_card(page, padding=24)
        outer.pack(fill="x", pady=(0, S(20)))
        self.card_title(body, "File Size Distribution Tiers")
        for tier in size_data:
            row = tk.Frame(body, bg=SURFACE)
            row.pack(fill="x", pady=S(6))
            row.columnconfigure(1, weight=1)
            row.columnconfigure(0, minsize=S(190))
            row.columnconfigure(2, minsize=S(100))
            row.columnconfigure(3, minsize=S(110))

            lbl(row, tier["tier"], 13, "medium", TEXT, SURFACE).grid(row=0, column=0, sticky="w")
            bar(row, tier["percentage"] / 100.0, ACCENT).grid(row=0, column=1, sticky="ew", padx=S(12))
            lbl(row, f"{tier['count']:,} files ({tier['percentage']}%)", 13, "medium", TEXT_SEC,
                SURFACE, anchor="e").grid(row=0, column=2, sticky="e", padx=(0, S(12)))
            lbl(row, tier["size_readable"], 12, "regular", TEXT_MUTED, SURFACE,
                anchor="e").grid(row=0, column=3, sticky="e")

        # 3. Top File Extensions & Monthly Timeline side-by-side cards
        ext_data = charts.get_top_extensions(limit=8)
        outer, body = make_card(page, padding=24)
        outer.pack(fill="x", pady=(0, S(20)))
        self.card_title(body, "Most Common File Extensions")
        max_ext = max((e["count"] for e in ext_data), default=1)
        for item in ext_data:
            row = tk.Frame(body, bg=SURFACE)
            row.pack(fill="x", pady=S(5))
            row.columnconfigure(2, weight=1)
            row.columnconfigure(0, minsize=S(80))
            row.columnconfigure(1, minsize=S(100))
            row.columnconfigure(3, minsize=S(80))
            tk.Label(row, text=item["extension"], font=mono(12), fg=TEXT, bg=SURFACE, bd=0,
                     anchor="w").grid(row=0, column=0, sticky="w")
            lbl(row, item["category"], 12, "regular", TEXT_MUTED, SURFACE).grid(row=0, column=1, sticky="w")
            bar(row, item["count"] / max_ext if max_ext else 0,
                CAT_COLORS.get(item["category"], "#888888")).grid(row=0, column=2, sticky="ew", padx=S(12))
            lbl(row, f"{item['count']:,} files", 12, "medium", TEXT_SEC, SURFACE,
                anchor="e").grid(row=0, column=3, sticky="e")

        timeline = charts.get_timeline_summary()[-12:]
        if timeline:
            outer, body = make_card(page, padding=24)
            outer.pack(fill="x")
            self.card_title(body, "Recent Activity Timeline (By Year-Month)")
            max_month = max((m["count"] for m in timeline), default=1)
            for m in reversed(timeline):
                row = tk.Frame(body, bg=SURFACE)
                row.pack(fill="x", pady=S(5))
                row.columnconfigure(1, weight=1)
                row.columnconfigure(0, minsize=S(100))
                row.columnconfigure(2, minsize=S(90))
                row.columnconfigure(3, minsize=S(90))
                tk.Label(row, text=m["period"], font=mono(12), fg=TEXT, bg=SURFACE, bd=0,
                         anchor="w").grid(row=0, column=0, sticky="w")
                bar(row, m["count"] / max_month if max_month else 0, "#555555").grid(
                    row=0, column=1, sticky="ew", padx=S(12))
                lbl(row, f"{m['count']:,} files", 12, "medium", TEXT_SEC, SURFACE,
                    anchor="e").grid(row=0, column=2, sticky="e", padx=(0, S(12)))
                lbl(row, m["size_readable"], 12, "regular", TEXT_MUTED, SURFACE,
                    anchor="e").grid(row=0, column=3, sticky="e")

    # Organize Files page with Date-Based Photo Organization, Dry-Run Preview, Safe Copy/Move, Undo, and ZIP Backup
    def render_organize(self):
        page = self.pages["organize"]
        clear(page)
        count, total = database.get_totals()
        self.page_header(page, "Organize Files", f"{count:,} files ready to organize")

        strategy_choices = [
            ("By Category (Images, Documents, Audio…)", "category"),
            ("By Year & Month (EXIF Capture / Modified Date)", "date"),
            ("Photos by EXIF Date (Photos/YYYY-MM) + Categories", "photo_date"),
            ("By File Extension (JPG, PDF, MP3…)", "extension"),
        ]
        mode_choices = [
            ("Safe Copy (Keep original files untouched)", True),
            ("Move Files (Relocate into Organized folder)", False),
        ]

        outer, body = make_card(page, padding=24)
        outer.pack(fill="x", pady=(0, S(20)))
        self.card_title(body, "1. Configure Organization Rule & Backup")
        lbl(body, "Choose how you want subfolders arranged. You can preview the exact dry-run plan "
                  "before any files are copied or moved, create a ZIP backup first, and undo the last run.",
            13, "regular", TEXT_SEC, SURFACE, wraplength=S(760), justify="left").pack(
            anchor="w", pady=(0, S(16)))

        controls = Flow(body, gap_x=12, gap_y=12)
        controls.pack(fill="x")

        self.org_strategy_select = Select(controls, [c[0] for c in strategy_choices], width=38)
        self.org_mode_select = Select(controls, [m[0] for m in mode_choices], width=32)
        controls.add(self.org_strategy_select)
        controls.add(self.org_mode_select)

        default_out = os.path.join(self.folder if (self.folder and os.path.isdir(self.folder)) else BASE_DIR, "Organized_Output")
        self.org_output_input = TextInput(body, 520, "Output folder path...")
        self.org_output_input.set(default_out)
        self.org_output_input.pack(anchor="w", pady=(S(12), S(16)))

        btn_row = tk.Frame(body, bg=SURFACE)
        btn_row.pack(fill="x")

        preview_holder = tk.Frame(page, bg=SURFACE)
        preview_holder.pack(fill="x")

        def get_selected_strategy():
            label = self.org_strategy_select.get()
            for text, key in strategy_choices:
                if text == label:
                    return key
            return "category"

        def get_copy_mode():
            label = self.org_mode_select.get()
            for text, is_copy in mode_choices:
                if text == label:
                    return is_copy
            return True

        def show_dry_run():
            clear(preview_holder)
            out_dir = self.org_output_input.value() or default_out
            strat = get_selected_strategy()
            plan = organizer.build_organize_plan(base_output_dir=out_dir, strategy=strat)

            p_outer, p_body = make_card(preview_holder, padding=24)
            p_outer.pack(fill="x")
            self.card_title(p_body, f"2. Dry-Run Preview ({len(plan):,} files — No files moved yet)")

            folder_counts = {}
            for item in plan:
                folder_counts[item["destination_folder"]] = folder_counts.get(item["destination_folder"], 0) + 1

            summary_str = "  ·  ".join(f"{k}: {v} files" for k, v in list(folder_counts.items())[:8])
            lbl(p_body, f"Target Subfolders:  {summary_str}", 12, "medium", TEXT_SEC, SURFACE,
                wraplength=S(760), justify="left").pack(anchor="w", pady=(0, S(14)))
            hline(p_body, BORDER)

            for item in plan[:40]:
                r = tk.Frame(p_body, bg=SURFACE)
                r.pack(fill="x", pady=S(6))
                lbl(r, ellipsize(item["name"], FM(13, "medium"), S(220)), 13, "medium", TEXT,
                    SURFACE, width=24, anchor="w").pack(side="left")
                lbl(r, "→", 13, "semibold", TEXT_MUTED, SURFACE).pack(side="left", padx=S(10))
                tk.Label(r, text=ellipsize(item["proposed_path"], FM(12), S(460)), font=mono(11),
                         fg=TEXT_SEC, bg=SURFACE, bd=0, anchor="w").pack(side="left", fill="x", expand=True)
                hline(p_body, BORDER_LIGHT)

            if len(plan) > 40:
                lbl(p_body, f"… plus {len(plan) - 40:,} more files in this dry-run plan.",
                    12, "regular", TEXT_MUTED, SURFACE).pack(anchor="w", pady=(S(10), 0))

        def run_organize():
            out_dir = self.org_output_input.value() or default_out
            strat = get_selected_strategy()
            copy_only = get_copy_mode()
            plan = organizer.build_organize_plan(base_output_dir=out_dir, strategy=strat)
            completed, errors = organizer.execute_organize_plan(plan, copy_only=copy_only)
            undo_btn.set_enabled(organizer.can_undo())
            action_word = "Copied" if copy_only else "Moved"
            self.toast(f"{action_word} {len(completed):,} files ({len(errors)} errors)")
            show_dry_run()

        def run_undo():
            if not organizer.can_undo():
                self.toast("Nothing to undo yet")
                return
            undone, errors = organizer.undo_last_organize()
            undo_btn.set_enabled(organizer.can_undo())
            self.toast(f"Undid last organization for {undone:,} files")

        def run_zip_backup():
            default_zip = os.path.join(BASE_DIR, f"Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
            path = filedialog.asksaveasfilename(
                title="Save ZIP Backup Archive",
                initialfile=os.path.basename(default_zip),
                defaultextension=".zip",
                filetypes=[("ZIP Archive", "*.zip")])
            if not path:
                return
            total_f, real_f = organizer.create_zip_backup(path, root_folder=self.folder)
            self.toast(f"ZIP Backup saved ({total_f:,} inventory records, {real_f:,} files archived)")

        Btn(btn_row, "Preview Plan (Dry Run)", show_dry_run, icon_name="eye").pack(
            side="left", padx=(0, S(8)))
        Btn(btn_row, "Organize Files Now", run_organize, icon_name="folder",
            kind="primary").pack(side="left", padx=(0, S(8)))
        Btn(btn_row, "Create ZIP Backup First", run_zip_backup, icon_name="file-down").pack(
            side="left", padx=(0, S(8)))
        undo_btn = Btn(btn_row, "Undo Last Run", run_undo, icon_name="refresh")
        undo_btn.pack(side="left")
        undo_btn.set_enabled(organizer.can_undo())

        self.org_strategy_select.command = show_dry_run
        show_dry_run()

    # Export, ZIP Backup, Integrity Verification, and Scan History / Snapshot Comparison page
    def render_export(self):
        page = self.pages["export"]
        clear(page)
        count, total = database.get_totals()
        self.page_header(page, "Export, Backup & Verification", f"{count:,} files in current inventory")

        # 1. Export Reports (CSV / JSON / ZIP Backup)
        outer, body = make_card(page, padding=24)
        outer.pack(fill="x", pady=(0, S(20)))
        self.card_title(body, "1. Export Inventory Reports & ZIP Backup")
        lbl(body, "Save your complete file inventory as a CSV spreadsheet (for Excel/Google Sheets), "
                  "a structured JSON file, or create a compressed ZIP backup archive.",
            13, "regular", TEXT_SEC, SURFACE, wraplength=S(760), justify="left").pack(
            anchor="w", pady=(0, S(16)))

        btn_row = tk.Frame(body, bg=SURFACE)
        btn_row.pack(fill="x")

        def export_file(fmt):
            ext = ".csv" if fmt == "csv" else ".json"
            default_name = f"file_inventory_{datetime.now().strftime('%Y%m%d_%H%M')}{ext}"
            path = filedialog.asksaveasfilename(
                title=f"Export {fmt.upper()} Report",
                initialfile=default_name,
                defaultextension=ext,
                filetypes=[(f"{fmt.upper()} file", f"*{ext}")])
            if path:
                exporter.save_export_file(path, fmt=fmt)
                self.toast(f"Saved {fmt.upper()} report to {os.path.basename(path)}")

        def create_backup_zip():
            default_zip = f"folder_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            path = filedialog.asksaveasfilename(
                title="Save Full ZIP Backup",
                initialfile=default_zip,
                defaultextension=".zip",
                filetypes=[("ZIP Archive", "*.zip")])
            if path:
                total_f, real_f = organizer.create_zip_backup(path, root_folder=self.folder)
                self.toast(f"Created ZIP backup: {os.path.basename(path)} ({total_f:,} items)")

        Btn(btn_row, "Export CSV Report", lambda: export_file("csv"), icon_name="file-down",
            kind="primary").pack(side="left", padx=(0, S(8)))
        Btn(btn_row, "Export JSON Report", lambda: export_file("json"), icon_name="file-down").pack(
            side="left", padx=(0, S(8)))
        Btn(btn_row, "Create Full ZIP Backup", create_backup_zip, icon_name="folder").pack(side="left")

        # 2. Bonus Feature: SHA-256 File Integrity Verification
        i_outer, i_body = make_card(page, padding=24)
        i_outer.pack(fill="x", pady=(0, S(20)))
        self.card_title(i_body, "2. File Integrity Verification (SHA-256 Check)")
        lbl(i_body, "Verify that scanned files on disk have not been corrupted, altered, or deleted "
                    "by re-computing and checking their SHA-256 cryptographic hashes.",
            13, "regular", TEXT_SEC, SURFACE, wraplength=S(760), justify="left").pack(
            anchor="w", pady=(0, S(14)))

        integrity_result_box = tk.Frame(i_body, bg=SURFACE)

        def run_integrity_check():
            clear(integrity_result_box)
            files = database.get_all_files()
            report = duplicate.verify_inventory_integrity(files)
            if report["new_hashes"]:
                database.save_hashes(report["new_hashes"])

            intact_n = len(report["intact"])
            mod_n = len(report["modified"])
            miss_n = len(report["missing"])

            hline(integrity_result_box, BORDER_LIGHT, pady=(S(12), S(12)))
            summary_txt = (f"Verification Complete:  {intact_n:,} Intact (OK)   ·   "
                           f"{mod_n:,} Modified   ·   {miss_n:,} Missing")
            lbl(integrity_result_box, summary_txt, 13, "semibold",
                DANGER if (mod_n or miss_n) else TEXT, SURFACE).pack(anchor="w", pady=(0, S(8)))

            sample_items = (report["modified"] + report["missing"] + report["intact"])[:8]
            for item in sample_items:
                r = tk.Frame(integrity_result_box, bg=SURFACE)
                r.pack(fill="x", pady=S(3))
                lbl(r, ellipsize(item["name"], FM(12, "medium"), S(220)), 12, "medium", TEXT,
                    SURFACE, width=24, anchor="w").pack(side="left")
                lbl(r, item["status"], 12, "regular", TEXT_SEC, SURFACE, width=32, anchor="w").pack(
                    side="left", padx=S(8))
                tk.Label(r, text=(item["hash"] or "")[:24] + ("…" if len(item["hash"] or "") > 24 else ""),
                         font=mono(11), fg=TEXT_MUTED, bg=SURFACE, bd=0).pack(side="left")

            self.toast(f"Integrity verified: {intact_n:,} intact, {mod_n:,} modified, {miss_n:,} missing")

        Btn(i_body, "Verify File Integrity Now", run_integrity_check, icon_name="check-circle",
            kind="primary").pack(anchor="w")
        integrity_result_box.pack(fill="x")

        # 3. Bonus Feature: Saved Scan History & Comparison of Two Folder Snapshots
        h_outer, h_body = make_card(page, padding=24)
        h_outer.pack(fill="x")
        self.card_title(h_body, "3. Saved Scan History & Folder Snapshot Comparison")
        lbl(h_body, "Every scan automatically saves a timestamped snapshot in SQLite. You can also save "
                    "a manual snapshot at any time and compare any two snapshots to see Added, Removed, "
                    "and Modified files.",
            13, "regular", TEXT_SEC, SURFACE, wraplength=S(760), justify="left").pack(
            anchor="w", pady=(0, S(14)))

        history = database.get_scan_history(limit=20)
        if not history and self.has_files:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            database.save_scan_snapshot(self.meta.get("root_folder", "Current"), now_str)
            history = database.get_scan_history(limit=20)

        snap_labels = [
            f"#{h['id']} — {h['scan_date']} — {os.path.basename(h['root_folder']) or h['root_folder']} ({h['total_files']} files, {fmt_size(h['total_bytes'])})"
            for h in history
        ] or ["No snapshots yet"]

        snap_bar = Flow(h_body, gap_x=12, gap_y=12)
        snap_bar.pack(fill="x", pady=(0, S(12)))
        older_select = Select(snap_bar, snap_labels, width=36)
        newer_select = Select(snap_bar, snap_labels, width=36)
        if len(snap_labels) >= 2:
            older_select.current(1)
            newer_select.current(0)

        snap_bar.add(older_select)
        snap_bar.add(newer_select)

        diff_box = tk.Frame(h_body, bg=SURFACE)

        def parse_snap_id(text):
            if text.startswith("#"):
                try:
                    return int(text.split("—")[0].lstrip("#").strip())
                except ValueError:
                    return None
            return None

        def run_snapshot_compare():
            clear(diff_box)
            old_id = parse_snap_id(older_select.get())
            new_id = parse_snap_id(newer_select.get())
            if not old_id or not new_id:
                self.toast("Save at least one scan snapshot first")
                return
            diff = database.compare_snapshots(old_id, new_id)
            if not diff:
                return

            hline(diff_box, BORDER_LIGHT, pady=(S(12), S(12)))
            head_txt = (f"Comparison (#{old_id} → #{new_id}):   "
                        f"+{len(diff['added'])} Added   ·   "
                        f"-{len(diff['removed'])} Removed   ·   "
                        f"~{len(diff['modified'])} Modified   ·   "
                        f"{diff['unchanged_count']} Unchanged")
            lbl(diff_box, head_txt, 13, "semibold", TEXT, SURFACE).pack(anchor="w", pady=(0, S(8)))

            changes = (
                [("ADDED", f["name"], f["path"], fmt_size(f.get("size_bytes", 0))) for f in diff["added"][:10]] +
                [("REMOVED", f["name"], f["path"], fmt_size(f.get("size_bytes", 0))) for f in diff["removed"][:10]] +
                [("MODIFIED", f["name"], f["path"], f"{fmt_size(f['old_size'])} → {fmt_size(f['new_size'])}") for f in diff["modified"][:10]]
            )
            if not changes:
                lbl(diff_box, "Both snapshots have the exact same files, sizes, and hashes.",
                    12, "regular", TEXT_MUTED, SURFACE).pack(anchor="w")
            else:
                for badge_txt, name, path, detail in changes[:15]:
                    r = tk.Frame(diff_box, bg=SURFACE)
                    r.pack(fill="x", pady=S(3))
                    lbl(r, badge_txt, 11, "semibold", DANGER if badge_txt == "REMOVED" else TEXT,
                        SURFACE, width=10, anchor="w").pack(side="left")
                    lbl(r, ellipsize(name, FM(12, "medium"), S(220)), 12, "medium", TEXT,
                        SURFACE, width=24, anchor="w").pack(side="left")
                    lbl(r, detail, 12, "regular", TEXT_SEC, SURFACE).pack(side="right")

        def save_manual_snapshot():
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            database.save_scan_snapshot(self.meta.get("root_folder", "Snapshot"), now_str)
            self.render_export()
            self.toast("Saved current inventory as a new scan snapshot")

        action_row = tk.Frame(h_body, bg=SURFACE)
        action_row.pack(fill="x")
        Btn(action_row, "Compare Two Snapshots", run_snapshot_compare, icon_name="copy",
            kind="primary").pack(side="left", padx=(0, S(8)))
        Btn(action_row, "Save Current Snapshot", save_manual_snapshot, icon_name="upload").pack(
            side="left")
        diff_box.pack(fill="x")


def main():
    load_embedded_fonts()
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()