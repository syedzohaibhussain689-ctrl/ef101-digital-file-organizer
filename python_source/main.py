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
SPOT = "#4F46E5"          # Indigo spotlight ring that shows first-time users what to click next
SPOT_SOFT = "#A5B4FC"     # Lighter pulse shade of the spotlight ring
SPOT_BG = "#EEF2FF"       # Soft indigo tint behind the current demo mission
SUCCESS = "#15803D"       # Green check marks for completed demo missions
SUCCESS_SOFT = "#F0FDF4"

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
        self._fit_pending = False
        self.canvas.bind("<Configure>", lambda e: self.schedule_fit())
        self.inner.bind("<Configure>", lambda e: self.schedule_fit())

    def schedule_fit(self):
        # Coalesce rapid resize/content changes into a single layout pass without timer polling
        if not self._fit_pending:
            self._fit_pending = True
            self.after_idle(self._fit)

    def _on_scroll(self, first, last):
        self.vbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.vbar.state(["disabled"])
        else:
            self.vbar.state(["!disabled"])

    def _fit(self):
        self._fit_pending = False
        try:
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
            needed = self.inner.winfo_reqheight()
            if (width, height, needed) == self._seen:
                return
            self._seen = (width, height, needed)
            self.canvas.itemconfigure(self.window, width=width, height=max(needed, height))
            self.canvas.configure(scrollregion=(0, 0, width, max(needed, height)))
        except tk.TclError:
            pass

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
        self._relayout_pending = False
        self._last_width = -1
        self.bind("<Configure>", lambda e: self._schedule_relayout())

    def add(self, widget):
        self.items.append(widget)
        self._last_width = -1
        self._schedule_relayout()

    def _schedule_relayout(self):
        if not self._relayout_pending:
            self._relayout_pending = True
            self.after_idle(self.relayout)

    def relayout(self):
        self._relayout_pending = False
        try:
            width = self.winfo_width()
        except tk.TclError:
            return
        if width <= 1 or not self.items or width == self._last_width:
            return
        self._last_width = width
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
        prev = self.columns
        self.columns = 0
        self._layout(self._count(), prev_cols=prev)

    def _count(self):
        return max(1, (self.winfo_width() + self.gap) // (self.min_width + self.gap))

    def _on_configure(self, event):
        count = self._count()
        if count != self.columns:
            self._layout(count, prev_cols=self.columns)

    def _layout(self, columns, prev_cols=0):
        old_max = max(prev_cols, self.columns, columns)
        self.columns = columns
        for widget in self.items:
            widget.grid_forget()
        for c in range(columns, old_max):
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
    """Styles the Tkinter scrollbars, dropdown menus, and tables so they look flat and modern."""
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

    # Flat, high-performance native Treeview table style matching the monochrome design
    style.layout("Web.Treeview", [("Web.Treeview.treearea", {"sticky": "nswe"})])
    style.configure("Web.Treeview", background=SURFACE, fieldbackground=SURFACE,
                    foreground=TEXT, borderwidth=0, relief="flat",
                    font=FN(12, "regular"), rowheight=S(38))
    style.map("Web.Treeview",
              background=[("selected", ACCENT_SOFT)],
              foreground=[("selected", TEXT)])
    style.configure("Web.Treeview.Heading", background=BG, foreground=TEXT_MUTED,
                    relief="flat", borderwidth=0, font=FN(11, "semibold"),
                    padding=(S(12), S(10)))
    style.map("Web.Treeview.Heading",
              background=[("active", ACCENT_SOFT)],
              foreground=[("active", TEXT)])

    # Style the popup list that appears when you click a dropdown menu
    root.option_add("*TCombobox*Listbox.background", SURFACE)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_SOFT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
    root.option_add("*TCombobox*Listbox.borderWidth", 0)
    root.option_add("*TCombobox*Listbox.relief", "flat")
    root.option_add("*TCombobox*Listbox.font", FM(13))


_PIL_FONT_CACHE = {}
_TYPE_TILE_IMG_CACHE = {}


# Helpers for creating small square photo previews and file extension tiles in Grid View
def _pil_font(size):
    cached = _PIL_FONT_CACHE.get(size)
    if cached is not None:
        return cached
    for name in (os.path.join(BASE_DIR, "fonts", "PlusJakartaSans-SemiBold.ttf"),
                 "segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(name, size)
            _PIL_FONT_CACHE[size] = font
            return font
        except OSError:
            continue
    font = ImageFont.load_default()
    _PIL_FONT_CACHE[size] = font
    return font


def make_thumbnail(path, size):
    """Creates a small square preview image of a photo, or returns None if the photo cannot be opened."""
    if not path or not os.path.isfile(path):
        return None
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
    """Creates (and caches) a neat square tile showing the file extension for non-photo files."""
    key = (category or "Other", (extension or "").lower(), size)
    cached = _TYPE_TILE_IMG_CACHE.get(key)
    if cached is not None:
        return cached
    tile = Image.new("RGB", (size, size), hex_rgb(ACCENT_SOFT))
    draw = ImageDraw.Draw(tile)
    bar_h = max(3, size // 28)
    draw.rectangle([0, size - bar_h, size, size], fill=hex_rgb(CAT_COLORS.get(category, "#CCCCCC")))
    text = (extension or "").lstrip(".").upper()[:4] or "FILE"
    font = _pil_font(max(10, size // 5))
    box = draw.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.text(((size - w) / 2 - box[0], (size - bar_h - h) / 2 - box[1]),
              text, fill=hex_rgb(TEXT_MUTED), font=font)
    _TYPE_TILE_IMG_CACHE[key] = tile
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

# Hands-on Guided Demo: each step is a short mission where the user clicks the REAL controls.
# "event" is fired by the real UI handler, "target" is the widget the spotlight ring points at,
# "after" means the mission only counts once another mission is done, and "prep" is the target
# the "Show me" button opens first when the mission's own target is not on screen yet.
DEMO_STEPS = [
    {
        "page": "dashboard",
        "title": "Your Storage Dashboard",
        "description": "Total files, storage used, recoverable duplicate space and your biggest files, all at a glance.",
        "tasks": [
            {"event": "details:dashboard", "target": "dash_largest",
             "label": "Click any file in the “10 Largest Files” list",
             "pill": "Click a file to inspect it",
             "done": "Nice! That popup shows the full path, size, dates and SHA-256 fingerprint."},
            {"event": "modal_closed", "target": "modal_close", "after": "details:dashboard",
             "label": "Close the popup with × (or press Esc)",
             "pill": "Close the popup",
             "done": "Popup closed. You can open details like this from any file list."},
        ],
    },
    {
        "page": "files",
        "title": "Search, Filter & Browse All Files",
        "description": "Narrow hundreds of files down instantly. Tip: you can also type in the search box or click a column header to sort.",
        "tasks": [
            {"event": "files_category", "target": "files_category",
             "label": "Pick a category (e.g. Images) from the category dropdown",
             "pill": "Pick a category here",
             "done": "Filtered! Only files from that category are listed now."},
            {"event": "files_grid", "target": "files_grid",
             "label": "Click the Grid button to switch to thumbnail view",
             "pill": "Switch to Grid view",
             "done": "Grid view on: every file gets a thumbnail or type tile."},
            {"event": "details:files", "target": "files_card",
             "label": "Click any file to open its details",
             "pill": "Click any file",
             "done": "That is how you inspect any file while browsing."},
        ],
    },
    {
        "page": "duplicates",
        "title": "Find & Clean Up Duplicate Files",
        "description": "Files are grouped by exact size first, then confirmed with SHA-256 hashes, so renamed copies are caught too.",
        "tasks": [
            {"event": "dup_expand", "target": "dup_group",
             "label": "Click a duplicate group to expand it",
             "pill": "Click to expand this group",
             "done": "Expanded! KEEP is the original, every COPY is wasted space."},
            {"event": "dup_quarantine", "target": "dup_quarantine", "prep": "dup_group",
             "label": "Click “Quarantine Copy” to safely set one extra copy aside",
             "pill": "Quarantine this copy",
             "done": "Copy quarantined. It is moved aside, not deleted, so nothing is lost."},
        ],
    },
    {
        "page": "charts",
        "title": "Explore Interactive Storage Charts",
        "description": "Category bars are clickable. Drill into one to see which files take up the most space.",
        "tasks": [
            {"event": "charts_category", "target": "charts_cat",
             "label": "Click a category bar in “Storage Breakdown by Category”",
             "pill": "Click a category bar",
             "done": "Drill-down open: these are the biggest files in that category."},
            {"event": "details:charts", "target": "charts_file", "prep": "charts_cat",
             "label": "Click one of the files in the drill-down",
             "pill": "Click a file",
             "done": "You can jump from a chart straight to any file's details."},
        ],
    },
    {
        "page": "organize",
        "title": "Organize Folders Safely",
        "description": "Pick a rule, check the dry-run preview, then organize. Demo files are only simulated, so nothing on disk changes.",
        "tasks": [
            {"event": "org_strategy", "target": "org_strategy",
             "label": "Choose a different rule in the strategy dropdown",
             "pill": "Pick an organization rule",
             "done": "The dry-run preview below updated live for the new rule."},
            {"event": "org_run", "target": "org_run",
             "label": "Click “Organize Files Now” (Safe Copy mode)",
             "pill": "Run it",
             "done": "Organized! Safe Copy keeps the original files untouched."},
            {"event": "org_undo", "target": "org_undo", "after": "org_run",
             "label": "Click “Undo Last Run” to reverse it",
             "pill": "Undo it",
             "done": "Undone. Every organize run can be reversed with one click."},
        ],
    },
    {
        "page": "export",
        "title": "Export, Verify & Track Changes",
        "description": "Export reports, verify files with SHA-256 and compare snapshots to see what changed between scans.",
        "tasks": [
            {"event": "export_verify", "target": "export_verify",
             "label": "Click “Verify File Integrity Now”",
             "pill": "Run the SHA-256 check",
             "done": "Verified! Every file's hash was checked for corruption or changes."},
            {"event": "export_snapshot", "target": "export_snapshot",
             "label": "Click “Save Current Snapshot”",
             "pill": "Save a snapshot",
             "done": "Snapshot saved. It records the inventory exactly as it is right now."},
            {"event": "export_compare", "target": "export_compare",
             "label": "Click “Compare Two Snapshots” to see what changed",
             "pill": "Compare snapshots",
             "done": "There is the diff: added, removed and modified files between two scans."},
        ],
    },
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
        self.type_tile_cache = {}
        self._data_version = 0
        self._page_version = {}
        self._files_rendered_version = -1
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

        # State for the hands-on 6-step Guided Demo (the user clicks the real controls)
        self.demo_active = False
        self.demo_step_index = 0
        self.demo_completed = set()        # Steps whose missions are all done
        self.demo_done_tasks = {}          # step index -> set of completed mission events
        self.demo_last_note = None
        self.demo_targets = {}             # target key -> (widget, action) for the spotlight
        self.modal_kind = None
        self._spot_job = None
        self._spot_phase = 0
        self._spot_ident = None
        self._spot_geom = None
        self._spot_pill_mode = "target"
        self._org_show_dry_run = None
        self._export_run_integrity = None

        # Build the main window layout: left sidebar, top bar, center scroll area, and bottom status bar
        shell = tk.Frame(root, bg=BG)
        shell.pack(fill="both", expand=True)
        self.build_sidebar(shell)
        main = tk.Frame(shell, bg=SURFACE)
        main.pack(side="left", fill="both", expand=True)
        self.build_statusbar(main)        # Pack the status bar at the bottom first so it never gets pushed off screen
        self.demo_bar_slot = tk.Frame(main, bg=BG)
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
        # Pulsing indigo spotlight ring + hint pill used by the hands-on Guided Demo
        self._spot_edges = [tk.Frame(root, bg=SPOT, bd=0, highlightthickness=0) for _ in range(4)]
        self._spot_pill = tk.Label(root, bg=SPOT, fg="#FFFFFF", font=FN(12, "semibold"),
                                   padx=S(10), pady=S(4), bd=0, cursor="hand2")
        self._spot_pill.bind("<Button-1>", self._demo_pill_clicked)
        root.bind("<Escape>", lambda e: self.close_modal(user=True))
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
            self.demo_target("nav:" + key, item, lambda k=key: self.navigate(k))

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
        self.rescan_btn.pack(side="left", padx=(0, S(8)))
        self.demo_btn = Btn(right, "Demo", self.toggle_demo_walkthrough, icon_name="bolt")
        self.demo_btn.pack(side="left")

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
        self.statusbar_wrap = wrap
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
        y_offset = -S(40)
        if self.demo_active:
            bar_h = self.demo_bar_slot.winfo_height()
            status_h = self.statusbar_wrap.winfo_height()
            y_offset = -(bar_h + status_h + S(14)) if bar_h > 1 else -S(245)
        self.toast_label.place(relx=0.5, rely=1.0, y=y_offset, anchor="s")
        self.toast_label.lift()
        if self.toast_job:
            self.root.after_cancel(self.toast_job)
        self.toast_job = self.root.after(2400, self.toast_label.place_forget)

    def navigate(self, page):
        if not self.has_files and page != "dashboard":
            self.toast("Scan a folder first, or click Demo")
            return
        if self.demo_active:
            for idx, step in enumerate(DEMO_STEPS):
                if step["page"] == page:
                    if idx != self.demo_step_index:
                        self.go_to_demo_step(idx)       # Clicking a sidebar tab moves the tour too
                        return
                    break
        self.show_page(page)
        if self.demo_active:
            self.render_demo_bar()

    def show_page(self, page, force=False):
        self.close_modal()
        self.current = page
        for key, item in self.nav_items.items():
            item.set_active(key == page)
        for frame in self.pages.values():
            frame.pack_forget()

        key = "intro" if (page == "dashboard" and not self.has_files) else page
        needs_render = force or (self._page_version.get(key) != self._data_version)
        if key == "files":
            self.render_files_page(force=force)
        elif needs_render:
            if key == "intro":
                self.render_intro()
            elif page == "dashboard":
                self.render_dashboard()
            elif page == "duplicates":
                self.render_duplicates()
            elif page == "charts":
                self.render_charts()
            elif page == "organize":
                self.render_organize()
            elif page == "export":
                self.render_export()
            self._page_version[key] = self._data_version
        self.pages[key].pack(fill="both", expand=True, padx=S(40), pady=S(32))
        self.scroll.scroll_to_top()
        self.scroll.schedule_fit()

    def reload_state(self):
        """Reads the latest file counts from the database and updates the sidebar and status bar."""
        self._data_version += 1
        self._page_version.clear()
        self._files_rendered_version = -1
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
        if self.demo_active:
            self.exit_demo_walkthrough(restore_clean=False, silent=True)
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
    def load_demo(self, show_toast=True):
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
        if show_toast:
            self.toast(f"Demo loaded: {len(rows)} files across {len(folders) + 1} folders")

    # Hands-on Guided Demo: a pulsing spotlight shows what to click and the real UI handlers
    # report back through demo_event() so each mission is ticked off as the user does it.
    def toggle_demo_walkthrough(self):
        if self.demo_active:
            self.exit_demo_walkthrough(restore_clean=False)
        else:
            self.start_demo_walkthrough()

    def start_demo_walkthrough(self):
        self.view_mode = "list"
        if self.filters_built:
            self.update_view_buttons()
        self.load_demo(show_toast=False)
        self.demo_active = True
        self.demo_step_index = 0
        self.demo_completed = set()
        self.demo_done_tasks = {}
        self.demo_last_note = None
        self.demo_btn.set_text("Exit Demo")
        self.demo_btn.set_kind("primary")
        self.demo_bar_slot.pack(side="bottom", fill="x", before=self.scroll)
        self.show_page(DEMO_STEPS[0]["page"])
        self.render_demo_bar()
        self._demo_start_spotlight()
        self.show_demo_welcome()

    def exit_demo_walkthrough(self, restore_clean=False, silent=False):
        self._demo_stop_spotlight()
        self.close_modal()
        self.demo_active = False
        self.demo_step_index = 0
        self.demo_completed = set()
        self.demo_done_tasks = {}
        self.demo_last_note = None
        self.demo_bar_slot.pack_forget()
        clear(self.demo_bar_slot)
        self.demo_btn.set_text("Demo")
        self.demo_btn.set_kind("default")
        if restore_clean:
            self.view_mode = "list"
            if self.filters_built:
                self.update_view_buttons()
            self.load_demo(show_toast=False)
        if not silent:
            self.toast("Guided Demo finished, clean sample dataset restored."
                       if restore_clean else "Exited Guided Demo.")

    def finish_demo_walkthrough(self):
        total = sum(len(s["tasks"]) for s in DEMO_STEPS)
        done = sum(len(v) for v in self.demo_done_tasks.values())
        steps_done = set(self.demo_completed)
        self.exit_demo_walkthrough(restore_clean=True, silent=True)
        self.show_demo_finish(done, total, steps_done)

    def go_to_demo_step(self, idx):
        clamped = max(0, min(len(DEMO_STEPS) - 1, idx))
        self.close_modal()
        self.demo_step_index = clamped
        self.demo_last_note = None
        page = DEMO_STEPS[clamped]["page"]
        if page == "files" and clamped not in self.demo_completed:
            self.view_mode = "list"               # Start the All Files mission from a clean list
            self.reset_filter_state()
            if self.filters_built:
                self.update_view_buttons()
        self.show_page(page)
        self.render_demo_bar()
        self._demo_spot_now()

    def next_demo_step(self):
        if not self.demo_active:
            return
        if self.demo_step_index >= len(DEMO_STEPS) - 1:
            self.finish_demo_walkthrough()
        else:
            self.go_to_demo_step(self.demo_step_index + 1)

    def prev_demo_step(self):
        if self.demo_active and self.demo_step_index > 0:
            self.go_to_demo_step(self.demo_step_index - 1)

    def demo_target(self, key, widget, action=None):
        """Registers a real widget the spotlight can point at, plus what "Show me" should do."""
        self.demo_targets[key] = (widget, action)

    def _demo_done(self, idx=None):
        idx = self.demo_step_index if idx is None else idx
        return self.demo_done_tasks.setdefault(idx, set())

    def _demo_current_task(self):
        if not self.demo_active:
            return None
        done = self._demo_done()
        for task in DEMO_STEPS[self.demo_step_index]["tasks"]:
            if task["event"] not in done:
                return task
        return None

    def demo_event(self, event, force=False):
        """Called by the real UI handlers so the tour can tick off missions the user performs."""
        if not self.demo_active:
            return
        idx = self.demo_step_index
        done = self._demo_done(idx)
        tasks = DEMO_STEPS[idx]["tasks"]
        for task in tasks:
            if task["event"] != event or event in done:
                continue
            if not force and task.get("after") and task["after"] not in done:
                return
            done.add(event)
            self.demo_last_note = task["done"]
            if all(t["event"] in done for t in tasks):
                self.demo_completed.add(idx)
            self.render_demo_bar()
            self._demo_spot_now()
            return

    def _demo_entry(self, key):
        entry = self.demo_targets.get(key) if key else None
        if not entry:
            return None
        try:
            if not entry[0].winfo_exists() or not entry[0].winfo_viewable():
                return None
        except tk.TclError:
            return None
        return entry

    def demo_show_me(self):
        """Fallback for anyone who gets stuck: performs the highlighted action for them."""
        if not self.demo_active:
            return
        task = self._demo_current_task()
        if task is None:
            self.next_demo_step()
            return
        if self.modal is not None and task["target"] != "modal_close":
            self.close_modal()
        entry = self._demo_entry(task["target"])
        if entry is None and task.get("prep"):
            prep = self._demo_entry(task["prep"])
            if prep and prep[1]:
                prep[1]()
                self.root.update_idletasks()
                entry = self._demo_entry(task["target"])
        if entry and entry[1]:
            entry[1]()
        if self.demo_active and task["event"] not in self._demo_done():
            self.demo_event(task["event"], force=True)     # Never leave the user stuck

    def _demo_spot_target(self):
        """Returns (target key, hint text, pill side) for whatever the user should click next."""
        task = self._demo_current_task()
        if task is not None:
            return task["target"], task["pill"], "auto"
        if self.modal is not None and self.modal_kind == "details":
            return "modal_close", "Close to continue", "auto"
        if self.demo_step_index >= len(DEMO_STEPS) - 1:
            return "demo_next", "Finish the tour", "auto"
        nxt = DEMO_STEPS[self.demo_step_index + 1]["page"]
        label = next(text for key, text, _ in NAV if key == nxt)
        return "nav:" + nxt, f"Next: click {label}", "right"

    @staticmethod
    def _is_inside(widget, ancestor):
        while widget is not None:
            if widget is ancestor:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _demo_start_spotlight(self):
        self._demo_stop_spotlight()
        self._spot_job = self.root.after(120, self._demo_spot_tick)

    def _demo_stop_spotlight(self):
        if self._spot_job:
            try:
                self.root.after_cancel(self._spot_job)
            except Exception:
                pass
            self._spot_job = None
        self._demo_hide_spot()
        self._spot_ident = None

    def _demo_hide_spot(self):
        for edge in self._spot_edges:
            edge.place_forget()
        self._spot_pill.place_forget()
        self._spot_geom = None

    def _demo_spot_tick(self):
        self._spot_job = None
        if not self.demo_active:
            self._demo_hide_spot()
            return
        self._spot_phase = (self._spot_phase + 1) % 14
        self._demo_place_spot()
        self._spot_job = self.root.after(90, self._demo_spot_tick)

    def _demo_spot_now(self):
        self._spot_geom = None
        self._spot_ident = None            # Treat as a new target so it scrolls into view
        self.root.after_idle(self._demo_place_spot)

    def _demo_scroll_into_view(self, widget):
        try:
            self.root.update_idletasks()
            self.scroll._fit()             # Ensure scrollregion includes newly expanded cards
            self.root.update_idletasks()
            inner, canvas = self.scroll.inner, self.scroll.canvas
            y = widget.winfo_rooty() - inner.winfo_rooty()
            total = max(1, inner.winfo_height())
            view = canvas.winfo_height()
            if total <= view:
                return
            top = max(0, min(y - int(view * 0.42), total - view))
            canvas.yview_moveto(top / float(total))
            self.root.update_idletasks()
        except tk.TclError:
            pass

    def _demo_lift_spot(self):
        for edge in self._spot_edges:
            edge.lift()
        self._spot_pill.lift()

    def _demo_place_spot(self):
        """Draws the pulsing ring around the real widget the user should click next."""
        if not self.demo_active:
            self._demo_hide_spot()
            return
        key, text, side = self._demo_spot_target()
        entry = self._demo_entry(key)
        if entry is None or (self.modal is not None and not self._is_inside(entry[0], self.modal)):
            self._demo_hide_spot()
            return
        widget, root = entry[0], self.root
        try:
            ox, oy = root.winfo_rootx(), root.winfo_rooty()
            x0, y0 = widget.winfo_rootx() - ox, widget.winfo_rooty() - oy
            ww, wh = widget.winfo_width(), widget.winfo_height()
        except tk.TclError:
            self._demo_hide_spot()
            return
        if ww <= 1 or wh <= 1:
            self._demo_hide_spot()
            return
        ident = (key, str(widget))
        new_target = ident != self._spot_ident
        self._spot_ident = ident

        pad, t = S(4), S(3)
        x0, y0 = x0 - pad, y0 - pad
        x1, y1 = x0 + ww + 2 * pad, y0 + wh + 2 * pad
        top_limit = 0
        if self._is_inside(widget, self.scroll.inner):
            c = self.scroll.canvas
            cx0, cy0 = c.winfo_rootx() - ox, c.winfo_rooty() - oy
            cx1, cy1 = cx0 + c.winfo_width(), cy0 + c.winfo_height()
            if new_target and (y0 < cy0 or y1 > cy1):
                self._demo_scroll_into_view(widget)
                self._spot_geom = None
                return                                  # The next tick draws it at its new spot
            if y1 <= cy0 + S(6) or y0 >= cy1 - S(6):
                self._demo_show_scroll_hint(y1 <= cy0 + S(6), cx0, cy0, cx1, cy1)
                return
            x0, y0, x1, y1 = max(x0, cx0), max(y0, cy0), min(x1, cx1), min(y1, cy1)
            top_limit = cy0

        color = SPOT if self._spot_phase < 7 else SPOT_SOFT
        geom = (x0, y0, x1, y1, color, text)
        if geom == self._spot_geom:
            self._demo_lift_spot()
            return
        self._spot_geom = geom
        bw, bh = x1 - x0, y1 - y0
        boxes = ((x0, y0, bw, t), (x0, y1 - t, bw, t), (x0, y0, t, bh), (x1 - t, y0, t, bh))
        for edge, (fx, fy, fw, fh) in zip(self._spot_edges, boxes):
            edge.configure(bg=color)
            edge.place(x=fx, y=fy, width=max(1, fw), height=max(1, fh))

        self._spot_pill_mode = "target"
        ph = self._spot_pill.winfo_reqheight()
        if side == "right":
            self._spot_pill.configure(text=f"◀  {text}")
            px, py = x1 + S(8), y0 + (bh - ph) // 2
        elif y0 - ph - S(6) >= top_limit:
            self._spot_pill.configure(text=f"▼  {text}")
            px, py = x0, y0 - ph - S(6)
        else:
            self._spot_pill.configure(text=f"▲  {text}")
            px, py = x0, y1 + S(6)
        pw = self._spot_pill.winfo_reqwidth()
        if side != "right" and px + pw > root.winfo_width() - S(12):
            px = x1 - pw
        px = max(S(4), min(px, root.winfo_width() - pw - S(8)))
        py = max(S(4), min(py, root.winfo_height() - ph - S(4)))
        self._spot_pill.place(x=px, y=py)
        self._demo_lift_spot()

    def _demo_show_scroll_hint(self, above, cx0, cy0, cx1, cy1):
        for edge in self._spot_edges:
            edge.place_forget()
        self._spot_geom = None
        self._spot_pill_mode = "scroll"
        self._spot_pill.configure(text="▲  Scroll up to the highlighted item" if above
                                  else "▼  Scroll down to the highlighted item")
        pw, ph = self._spot_pill.winfo_reqwidth(), self._spot_pill.winfo_reqheight()
        px = cx0 + (cx1 - cx0 - pw) // 2
        py = cy0 + S(10) if above else cy1 - ph - S(10)
        self._spot_pill.place(x=px, y=py)
        self._spot_pill.lift()

    def _demo_pill_clicked(self, event=None):
        if self._spot_pill_mode == "scroll":
            entry = self._demo_entry(self._demo_spot_target()[0])
            if entry:
                self._demo_scroll_into_view(entry[0])
                self._spot_geom = None
        else:
            self.demo_show_me()
        return "break"

    # Welcome and finish cards shown at the start and end of the hands-on tour
    def _show_info_modal(self, kind, title, subtitle, items, buttons, width=540):
        self.close_modal()
        self.toast_label.place_forget()
        modal = tk.Frame(self.root, bg=SPOT)
        inner = tk.Frame(modal, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=S(2), pady=S(2))
        body = tk.Frame(inner, bg=SURFACE)
        body.pack(fill="both", expand=True, padx=S(32), pady=S(28))
        lbl(body, title, 22, "semibold", TEXT, SURFACE).pack(anchor="w")
        lbl(body, subtitle, 13, "regular", TEXT_SEC, SURFACE, wraplength=S(width - 72),
            justify="left").pack(anchor="w", pady=(S(8), S(16)))
        for mark, text, color in items:
            row = tk.Frame(body, bg=SURFACE)
            row.pack(fill="x", pady=S(3))
            lbl(row, mark, 12, "semibold", color, SURFACE, width=3, anchor="w").pack(side="left")
            lbl(row, text, 13, "medium", TEXT, SURFACE, anchor="w").pack(side="left")
        btns = tk.Frame(body, bg=SURFACE)
        btns.pack(fill="x", pady=(S(22), 0))
        for text, command, kind_btn in reversed(buttons):
            Btn(btns, text, command, kind=kind_btn, px=16, py=8, size=13).pack(
                side="right", padx=(S(8), 0))
        modal.place(relx=0.5, rely=0.45, anchor="center", width=S(width))
        modal.lift()
        self.modal = modal
        self.modal_kind = kind
        self.modal_opened_at = time.time()

    def show_demo_welcome(self):
        count, _ = database.get_totals()
        items = [(str(i + 1), s["title"], SPOT) for i, s in enumerate(DEMO_STEPS)]
        self._show_info_modal(
            "welcome", "Welcome! Let's take a hands-on tour",
            f"We loaded {count:,} sample files so you can practise safely: nothing on your "
            "computer is touched. You will click the real buttons yourself, just follow the "
            "pulsing blue outline. Stuck? Press “Show me” and the app does that step for you.",
            items,
            [("Skip tour", lambda: self.exit_demo_walkthrough(restore_clean=False), "default"),
             ("Start the tour →", self.close_modal, "primary")])

    def show_demo_finish(self, done, total, steps_done):
        items = [("✓" if i in steps_done else "○", s["title"],
                  SUCCESS if i in steps_done else TEXT_MUTED) for i, s in enumerate(DEMO_STEPS)]
        if done >= total:
            title = "You're all set!"
            subtitle = (f"You completed all {total} hands-on missions across the 6 screens. "
                        "Ready to organize your own files?")
        else:
            title = "Tour complete"
            subtitle = (f"You completed {done} of {total} hands-on missions. You can replay the "
                        "tour any time with the Demo button at the top.")

        def scan_own():
            self.close_modal()
            self.choose_and_scan()

        self._show_info_modal(
            "finish", title, subtitle, items,
            [("Replay tour", self.start_demo_walkthrough, "default"),
             ("Keep exploring", self.close_modal, "default"),
             ("Scan my own folder", scan_own, "primary")])

    def render_demo_bar(self):
        saved_y = self.scroll.canvas.yview()[0]
        old_children = list(self.demo_bar_slot.winfo_children())
        if not self.demo_active:
            for child in old_children:
                child.destroy()
            return

        idx = self.demo_step_index
        step = DEMO_STEPS[idx]
        total = len(DEMO_STEPS)
        is_last = idx == total - 1
        is_done = idx in self.demo_completed
        done = self._demo_done(idx)
        current = self._demo_current_task()

        wrap = tk.Frame(self.demo_bar_slot, bg=BG)
        hline(wrap, BORDER)
        pad = tk.Frame(wrap, bg=BG)
        pad.pack(fill="x", padx=S(32), pady=S(10))
        card_outer = tk.Frame(pad, bg=SPOT)
        card_outer.pack(fill="x")
        card = tk.Frame(card_outer, bg=SURFACE)
        card.pack(fill="x", padx=S(1), pady=S(1))

        # Progress strip showing how many missions of the whole tour are done
        all_tasks = sum(len(s["tasks"]) for s in DEMO_STEPS)
        all_done = sum(len(v) for v in self.demo_done_tasks.values())
        prog_track = tk.Frame(card, bg=BORDER_LIGHT, height=S(3))
        prog_track.pack(fill="x")
        prog_track.pack_propagate(False)
        if all_done:
            tk.Frame(prog_track, bg=SUCCESS).place(relx=0, rely=0, relheight=1.0,
                                                   relwidth=all_done / float(all_tasks))

        body = tk.Frame(card, bg=SURFACE)
        body.pack(fill="x", padx=S(18), pady=S(10))
        body.columnconfigure(0, weight=1)
        left = tk.Frame(body, bg=SURFACE)
        left.grid(row=0, column=0, sticky="nsew")
        right = tk.Frame(body, bg=SURFACE)
        right.grid(row=0, column=1, sticky="ne", padx=(S(16), 0))

        # Left side: step badge + title, description, mission checklist, feedback
        head = tk.Frame(left, bg=SURFACE)
        head.pack(fill="x")
        tk.Label(head, text=f"STEP {idx + 1} OF {total}", bg=SPOT, fg="#FFFFFF",
                 font=FN(10, "semibold"), padx=S(8), pady=S(3), bd=0).pack(side="left")
        lbl(head, step["title"], 14, "semibold", TEXT, SURFACE).pack(side="left", padx=(S(10), 0))
        lbl(left, step["description"], 12, "regular", TEXT_SEC, SURFACE, wraplength=S(720),
            justify="left").pack(anchor="w", pady=(S(4), S(6)))

        for task in step["tasks"]:
            finished = task["event"] in done
            active = current is task
            row_bg = SPOT_BG if active else SURFACE
            row = tk.Frame(left, bg=row_bg)
            row.pack(fill="x", pady=S(1))
            mark = "✓" if finished else ("●" if active else "○")
            color = SUCCESS if finished else (SPOT if active else TEXT_MUTED)
            lbl(row, mark, 12, "semibold", color, row_bg, width=2).pack(side="left", padx=(S(6), 0),
                                                                       pady=S(3))
            lbl(row, task["label"], 12, "semibold" if active else "medium",
                TEXT_MUTED if finished else TEXT, row_bg).pack(side="left", pady=S(3))
            if active:
                lbl(row, "← do this now", 11, "semibold", SPOT, row_bg).pack(
                    side="left", padx=(S(10), 0))

        note = self.demo_last_note
        if is_done:
            if is_last:
                tail = "All missions done! Click Finish to wrap up."
            else:
                nxt = DEMO_STEPS[idx + 1]["page"]
                label = next(text for key, text, _ in NAV if key == nxt)
                tail = f"Step complete! Click “{label}” in the sidebar or press Next →"
            note = f"{note}  {tail}" if note else tail
        if note:
            note_box = tk.Frame(left, bg=SUCCESS_SOFT)
            note_box.pack(fill="x", pady=(S(6), 0))
            lbl(note_box, f"✓  {note}", 11, "medium", SUCCESS, SUCCESS_SOFT, padx=S(10),
                pady=S(5), wraplength=S(720), justify="left").pack(anchor="w")

        # Right side: clickable step dots + exit, then Show me / Back / Next
        top = tk.Frame(right, bg=SURFACE)
        top.pack(anchor="e")
        dots = tk.Frame(top, bg=SURFACE)
        dots.pack(side="left")
        for i in range(total):
            is_cur = i == idx
            dot_col = SPOT if is_cur else (SUCCESS if i in self.demo_completed else BORDER)
            dot = tk.Frame(dots, bg=dot_col, width=S(22) if is_cur else S(8), height=S(7),
                           cursor="hand2")
            dot.pack(side="left", padx=S(3))
            dot.pack_propagate(False)
            dot.bind("<Button-1>", lambda e, target=i: self.go_to_demo_step(target))
        close_btn = tk.Label(top, text="✕", bg=SURFACE, fg=TEXT_MUTED, font=FN(13, "semibold"),
                             padx=S(6), pady=S(2), cursor="hand2")
        close_btn.pack(side="left", padx=(S(8), 0))
        close_btn.bind("<Button-1>", lambda e: self.exit_demo_walkthrough(restore_clean=False))

        show_btn = Btn(right, "Show me", self.demo_show_me, icon_name="eye", px=12, py=6, size=12)
        show_btn.pack(anchor="e", pady=(S(12), S(8)), fill="x")
        show_btn.set_enabled(current is not None)

        nav_btns = tk.Frame(right, bg=SURFACE)
        nav_btns.pack(anchor="e")
        back_btn = Btn(nav_btns, "← Back", self.prev_demo_step, px=12, py=6, size=12)
        back_btn.pack(side="left", padx=(0, S(8)))
        back_btn.set_enabled(idx > 0)
        if is_last:
            next_text = "Finish ✓" if is_done else "Finish tour"
        else:
            next_text = "Next →" if is_done else "Skip →"
        next_btn = Btn(nav_btns, next_text, self.next_demo_step,
                       kind="primary" if is_done else "default", px=14, py=6, size=12)
        next_btn.pack(side="left")
        self.demo_target("demo_next", next_btn, self.next_demo_step)
        wrap.pack(fill="x")
        for child in old_children:
            child.destroy()
        if saved_y > 0:
            self.root.update_idletasks()
            self.scroll.canvas.yview_moveto(saved_y)

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
        Btn(buttons, "Start Guided Demo", self.start_demo_walkthrough, icon_name="bolt").pack(
            side="left", padx=S(6))

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
            bind_tree(row, "<Button-1>",
                      lambda e, file_id=f["id"]: self.show_details(file_id, "dashboard"))
            if rank == 1:
                self.demo_target("dash_largest", row,
                                 lambda file_id=f["id"]: self.show_details(file_id, "dashboard"))

    # All Files screen with search box, dropdown filters, sorting, and List or Grid view
    def reset_filter_state(self):
        self.page_no = 1
        self.sort_key, self.sort_desc = "name", False
        self._files_rendered_version = -1
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

    def render_files_page(self, force=False):
        page = self.pages["files"]
        if not self.filters_built:
            self.build_files_controls(page)
            self.filters_built = True
            self.refresh_filter_options()
            force = True
        if force or self._files_rendered_version != self._data_version:
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

        def demo_pick_images():
            self.category_select.set("Images")
            self.filters_changed()

        self.demo_target("files_category", self.category_select, demo_pick_images)
        self.demo_target("files_grid", self.grid_btn, lambda: self.set_view("grid"))

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
        if mode == "grid":
            self.demo_event("files_grid")

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
        if self.demo_active and self.category_select.get() != CATEGORY_OPTIONS[0][0]:
            self.demo_event("files_category")

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
        self._files_rendered_version = self._data_version
        self.scroll.schedule_fit()

    def change_page(self, step):
        self.page_no += step
        self.render_results()
        self.scroll.scroll_to_top()

    # Builds the rows and columns for List View using a single native ttk.Treeview (C-backed)
    def build_table(self, parent, rows):
        cols = ("name", "type", "ext", "size", "date", "folder")
        tree = ttk.Treeview(
            parent,
            columns=cols,
            show="headings",
            style="Web.Treeview",
            selectmode="browse",
            height=max(1, len(rows)),
        )
        tree.pack(fill="x", expand=True)

        available = max(self.scroll.canvas.winfo_width() - S(84), S(700))
        fixed = {"type": S(104), "ext": S(82), "size": S(112), "date": S(112), "folder": S(150)}
        name_w = max(S(240), available - sum(fixed.values()))

        heads = [
            ("name", "Name", name_w, "w", True),
            ("type", "Type", fixed["type"], "w", False),
            ("ext", "Ext", fixed["ext"], "w", True),
            ("size", "Size", fixed["size"], "e", True),
            ("date", "Modified", fixed["date"], "w", True),
            ("folder", "Folder", fixed["folder"], "w", False),
        ]
        for key, text, width, anchor, sortable in heads:
            arrow = ""
            if sortable:
                arrow = "  " + (("↓" if self.sort_desc else "↑") if self.sort_key == key else "↕")
            label = sp(text.upper()) + arrow
            if sortable:
                tree.heading(key, text=label, anchor=anchor,
                             command=lambda k=key: self.sort_by_header(k))
            else:
                tree.heading(key, text=label, anchor=anchor)
            tree.column(key, width=width, minwidth=min(width, S(64)),
                        anchor=anchor, stretch=(key == "name"))

        tree.tag_configure("odd", background=SURFACE)
        tree.tag_configure("even", background=BG)
        tree.tag_configure("hover", background=GLOW)

        iid_to_file = {}
        iid_base_tag = {}
        for idx, f in enumerate(rows):
            iid = str(f["id"])
            base_tag = "even" if idx % 2 else "odd"
            iid_to_file[iid] = f["id"]
            iid_base_tag[iid] = base_tag
            tree.insert(
                "", "end", iid=iid, tags=(base_tag,),
                values=(
                    f["name"],
                    (f["category"] or "Other").lower(),
                    f["extension"] or "—",
                    fmt_size(f["size_bytes"]),
                    (f["modified_time"] or "—")[:10],
                    f["parent_folder"] or "—",
                ),
            )

        hovered = {"iid": None}

        def on_motion(event):
            row_id = tree.identify_row(event.y)
            if row_id == hovered["iid"]:
                return
            prev = hovered["iid"]
            if prev and prev in iid_base_tag and tree.exists(prev):
                tree.item(prev, tags=(iid_base_tag[prev],))
            hovered["iid"] = row_id or None
            if row_id and tree.exists(row_id):
                tree.item(row_id, tags=("hover",))
                tree.configure(cursor="hand2")
            else:
                tree.configure(cursor="")

        def on_leave(event):
            prev = hovered["iid"]
            if prev and prev in iid_base_tag and tree.exists(prev):
                tree.item(prev, tags=(iid_base_tag[prev],))
            hovered["iid"] = None
            tree.configure(cursor="")

        def on_click(event):
            if tree.identify_region(event.x, event.y) != "cell":
                return
            row_id = tree.identify_row(event.y)
            if row_id in iid_to_file:
                self.show_details(iid_to_file[row_id], "files")

        def on_activate(event):
            sel = tree.selection()
            if sel and sel[0] in iid_to_file:
                self.show_details(iid_to_file[sel[0]], "files")

        tree.bind("<Motion>", on_motion)
        tree.bind("<Leave>", on_leave)
        tree.bind("<ButtonRelease-1>", on_click)
        tree.bind("<Return>", on_activate)
        if rows:
            self.demo_target("files_card", tree,
                             lambda file_id=rows[0]["id"]: self.show_details(file_id, "files"))

    # Builds the square photo and file cards for Grid View
    def build_grid(self, parent, rows):
        wrap = tk.Frame(parent, bg=SURFACE)
        wrap.pack(fill="x", padx=S(24), pady=S(24))
        grid = ResponsiveGrid(wrap, min_width=170, gap=16)
        grid.pack(fill="x")
        cards = [self.build_file_card(grid, f) for f in rows]
        grid.set_items(cards)
        if cards:
            self.demo_target("files_card", cards[0],
                             lambda file_id=rows[0]["id"]: self.show_details(file_id, "files"))

    def thumbnail_for(self, f, size):
        ext = (f["extension"] or "").lower()
        path = f["path"]
        if ext in IMAGE_EXTENSIONS and path and os.path.isfile(path):
            key = (path, size)
            cached = self.photo_cache.get(key)
            if cached is not None:
                return cached
            tile = make_thumbnail(path, S(size))
            if tile is not None:
                photo = ImageTk.PhotoImage(tile)
                self.photo_cache[key] = photo
                return photo

        # Share one cached PhotoImage per (category, extension, size) for instant Grid rendering
        tkey = (f["category"] or "Other", ext, size)
        cached_tile = self.type_tile_cache.get(tkey)
        if cached_tile is not None:
            return cached_tile
        photo = ImageTk.PhotoImage(make_type_tile(f["category"], ext, S(size)))
        self.type_tile_cache[tkey] = photo
        return photo

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
        bind_tree(outer, "<Button-1>", lambda e, i=f["id"]: self.show_details(i, "files"))
        return outer

    # Opens a popup window with all file info, EXIF camera tags, and hash details when a file is clicked
    def show_details(self, file_id, source=None):
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
        close = Btn(head, "×", lambda: self.close_modal(user=True), px=10, py=2, size=15)
        self.demo_target("modal_close", close, lambda: self.close_modal(user=True))
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
        ratio = 0.50 if self.demo_active else 0.68
        limit = max(S(180), int(self.root.winfo_height() * ratio) - S(90))
        scroller.canvas.configure(height=min(wanted, limit))
        modal.place(relx=0.5, rely=0.38 if self.demo_active else 0.5,
                    anchor="center", width=S(560))
        modal.lift()
        self.modal = modal
        self.modal_kind = "details"
        self.modal_opened_at = time.time()
        if source:
            self.demo_event("details:" + source)

    def close_modal(self, user=False):
        """Closes any popup. user=True means the user closed it (× button, Esc, or outside click)."""
        if self.modal is not None:
            kind = self.modal_kind
            self.modal.destroy()
            self.modal = None
            self.modal_kind = None
            if user and kind == "details":
                self.demo_event("modal_closed")
            if self.demo_active:
                self._demo_spot_now()

    def maybe_close_modal(self, event):
        """Closes the details popup when the user clicks anywhere outside the popup box."""
        if self.modal is None or time.time() - self.modal_opened_at < 0.25:
            return
        widget = event.widget
        while widget is not None:
            if widget is self.modal:
                return
            widget = getattr(widget, "master", None)
        self.close_modal(user=True)

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
        for index, group in enumerate(shown):
            self.build_dup_group(page, group, first=(index == 0))
        if len(groups) > len(shown):
            lbl(page, f"… and {len(groups) - len(shown)} more groups (the 150 biggest are shown)",
                13, "medium", TEXT_MUTED, SURFACE).pack(anchor="w", pady=S(8))

    def build_dup_group(self, page, group, first=False):
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
        state = {"open": False, "built": False, "quarantine": None}

        def toggle(event=None):
            state["open"] = not state["open"]
            if state["open"]:
                if not state["built"]:
                    state["quarantine"] = self.fill_dup_group(holder, group)
                    state["built"] = True
                holder.pack(fill="x")
                hline_top.pack(fill="x", before=holder)
                if state["quarantine"] is not None:
                    self.demo_target("dup_quarantine", *state["quarantine"])
            else:
                holder.pack_forget()
                hline_top.pack_forget()
            arrow.configure(text="▲" if state["open"] else "▼")
            self.scroll.schedule_fit()
            if state["open"]:
                self.demo_event("dup_expand")

        hline_top = tk.Frame(inner, bg=BORDER, height=S(1))
        for widget in (header, row, *row.winfo_children()):
            widget.bind("<Button-1>", toggle)
        if first:
            self.demo_target("dup_group", outer, lambda: None if state["open"] else toggle())

    def quarantine_copy(self, file_row):
        """Bonus Feature: Safely moves a duplicate copy into the Quarantine folder and refreshes the screen."""
        dst = organizer.quarantine_duplicate_file(file_row)
        self.reload_state()
        self.render_duplicates()
        self._page_version["duplicates"] = self._data_version
        self.scroll.schedule_fit()
        self.toast(f"Moved copy to Quarantine: {os.path.basename(dst)}")
        self.demo_event("dup_quarantine")

    def fill_dup_group(self, holder, group):
        body = tk.Frame(holder, bg=SURFACE)
        body.pack(fill="x", padx=S(20), pady=S(16))
        line = tk.Frame(body, bg=SURFACE)
        line.pack(fill="x", pady=(0, S(12)))
        lbl(line, "SHA-256: ", 12, "regular", TEXT_MUTED, SURFACE).pack(side="left")
        tk.Label(line, text=group[0]["hash"], font=mono(11), fg=TEXT_MUTED, bg=SURFACE,
                 bd=0).pack(side="left")
        first_quarantine = None
        for index, f in enumerate(group):
            row = tk.Frame(body, bg=SURFACE)
            row.pack(fill="x")
            lbl(row, "KEEP" if index == 0 else "COPY", 11, "semibold",
                TEXT if index == 0 else TEXT_MUTED, SURFACE, width=6, anchor="w").pack(
                side="left", pady=S(8))
            lbl(row, ellipsize(f["path"], FM(13, "medium"), S(360)), 13, "medium", TEXT,
                SURFACE, anchor="w").pack(side="left", pady=S(8))
            Btn(row, "Details", lambda file_id=f["id"]: self.show_details(file_id, "duplicates"),
                px=10, py=4, size=11).pack(side="right", pady=S(4))
            if index > 0:
                q_btn = Btn(row, "Quarantine Copy", lambda item=f: self.quarantine_copy(item),
                            kind="danger", px=10, py=4, size=11)
                q_btn.pack(side="right", padx=(0, S(8)), pady=S(4))
                if first_quarantine is None:
                    first_quarantine = (q_btn, lambda item=f: self.quarantine_copy(item))
            lbl(row, fmt_size(f["size_bytes"]), 13, "regular", TEXT_SEC, SURFACE).pack(
                side="right", padx=S(12))
            if index < len(group) - 1:
                hline(body, BORDER_LIGHT)
        lbl(body, "Safe Review Workflow: Quarantining moves extra copies into Duplicate_Quarantine without deleting originals.",
            12, "regular", TEXT_MUTED, SURFACE).pack(anchor="w", pady=(S(12), 0))
        return first_quarantine

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
        lbl(body, "Click a category to see its largest files.", 12, "regular", TEXT_MUTED,
            SURFACE).pack(anchor="w", pady=(0, S(8)))
        for cat_index, item in enumerate(cat_data):
            wrap = tk.Frame(body, bg=SURFACE)
            wrap.pack(fill="x")
            row = tk.Frame(wrap, bg=SURFACE, cursor="hand2")
            row.pack(fill="x", pady=S(6))
            row.columnconfigure(1, weight=1)
            row.columnconfigure(0, minsize=S(120))
            row.columnconfigure(2, minsize=S(100))
            row.columnconfigure(3, minsize=S(110))
            row.columnconfigure(4, minsize=S(24))

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
            arrow = lbl(row, "▼", 10, "regular", TEXT_MUTED, SURFACE, anchor="e")
            arrow.grid(row=0, column=4, sticky="e")
            drill = tk.Frame(wrap, bg=BG)
            self.bind_chart_drill(row, drill, arrow, item["category"], first=(cat_index == 0))

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

    def bind_chart_drill(self, row, drill, arrow, category, first=False):
        """Makes a chart category row clickable: it expands to list that category's largest files."""
        state = {"open": False, "built": False, "first_file": None}

        def toggle(event=None):
            state["open"] = not state["open"]
            if state["open"]:
                if not state["built"]:
                    state["first_file"] = self.fill_chart_drill(drill, category)
                    state["built"] = True
                drill.pack(fill="x", pady=(0, S(8)))
                if state["first_file"] is not None:
                    self.demo_target("charts_file", *state["first_file"])
            else:
                drill.pack_forget()
            arrow.configure(text="▲" if state["open"] else "▼")
            self.scroll.schedule_fit()
            if state["open"]:
                self.demo_event("charts_category")

        def enter(event):
            swap_bg(row, SURFACE, GLOW_BG)

        def leave(event):
            if not pointer_inside(row, event):
                swap_bg(row, GLOW_BG, SURFACE)

        bind_tree(row, "<Button-1>", toggle)
        bind_tree(row, "<Enter>", enter)
        bind_tree(row, "<Leave>", leave)
        if first:
            self.demo_target("charts_cat", row, lambda: None if state["open"] else toggle())

    def fill_chart_drill(self, holder, category):
        files = database.search_files(category=category, sort_by="Size", descending=True, limit=5)
        inner = tk.Frame(holder, bg=BG)
        inner.pack(fill="x", padx=S(16), pady=S(10))
        lbl(inner, sp(f"LARGEST {category.upper()} FILES"), 10, "semibold", TEXT_MUTED, BG).pack(
            anchor="w", pady=(0, S(6)))
        first = None
        for f in files:
            r = tk.Frame(inner, bg=BG, cursor="hand2")
            r.pack(fill="x", pady=S(1))
            lbl(r, ellipsize(f["name"], FM(12, "medium"), S(320)), 12, "medium", TEXT, BG).pack(
                side="left", pady=S(4), padx=(S(6), 0))
            lbl(r, fmt_size(f["size_bytes"]), 12, "regular", TEXT_SEC, BG).pack(
                side="right", padx=(0, S(6)))
            lbl(r, f["parent_folder"] or "", 11, "regular", TEXT_MUTED, BG).pack(
                side="right", padx=S(16))

            def open_file(file_id=f["id"]):
                self.show_details(file_id, "charts")

            def enter(event, r=r):
                swap_bg(r, BG, BORDER_LIGHT)

            def leave(event, r=r):
                if not pointer_inside(r, event):
                    swap_bg(r, BORDER_LIGHT, BG)

            bind_tree(r, "<Button-1>", lambda e, action=open_file: action())
            bind_tree(r, "<Enter>", enter)
            bind_tree(r, "<Leave>", leave)
            if first is None:
                first = (r, open_file)
        if not files:
            lbl(inner, "No files in this category.", 12, "regular", TEXT_MUTED, BG).pack(anchor="w")
        return first

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

            preview_rows = plan[:60]
            tree = ttk.Treeview(
                p_body,
                columns=("file", "dest", "path"),
                show="headings",
                style="Web.Treeview",
                selectmode="none",
                height=min(max(1, len(preview_rows)), 14),
            )
            tree.heading("file", text=sp("FILE NAME"), anchor="w")
            tree.heading("dest", text=sp("TARGET SUBFOLDER"), anchor="w")
            tree.heading("path", text=sp("PROPOSED PATH"), anchor="w")
            tree.column("file", width=S(220), minwidth=S(140), anchor="w", stretch=False)
            tree.column("dest", width=S(150), minwidth=S(100), anchor="w", stretch=False)
            tree.column("path", width=S(420), minwidth=S(200), anchor="w", stretch=True)
            tree.tag_configure("odd", background=SURFACE)
            tree.tag_configure("even", background=BG)

            for idx, item in enumerate(preview_rows):
                tree.insert(
                    "", "end",
                    tags=("even" if idx % 2 else "odd",),
                    values=(item["name"], item["destination_folder"], item["proposed_path"]),
                )
            tree.pack(fill="x", pady=(S(6), 0))

            if len(plan) > len(preview_rows):
                lbl(p_body, f"… plus {len(plan) - len(preview_rows):,} more files in this dry-run plan.",
                    12, "regular", TEXT_MUTED, SURFACE).pack(anchor="w", pady=(S(10), 0))
            self.scroll.schedule_fit()

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
            self.demo_event("org_run")

        def run_undo():
            if not organizer.can_undo():
                self.toast("Nothing to undo yet")
                return
            undone, errors = organizer.undo_last_organize()
            undo_btn.set_enabled(organizer.can_undo())
            self.toast(f"Undid last organization for {undone:,} files")
            self.demo_event("org_undo")

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
        organize_btn = Btn(btn_row, "Organize Files Now", run_organize, icon_name="folder",
                           kind="primary")
        organize_btn.pack(side="left", padx=(0, S(8)))
        Btn(btn_row, "Create ZIP Backup First", run_zip_backup, icon_name="file-down").pack(
            side="left", padx=(0, S(8)))
        undo_btn = Btn(btn_row, "Undo Last Run", run_undo, icon_name="refresh")
        undo_btn.pack(side="left")
        undo_btn.set_enabled(organizer.can_undo())

        def on_strategy_chosen():
            show_dry_run()
            self.demo_event("org_strategy")

        def demo_pick_strategy():
            labels = [c[0] for c in strategy_choices]
            current = self.org_strategy_select.get()
            self.org_strategy_select.set(labels[1] if current != labels[1] else labels[0])
            on_strategy_chosen()

        self._org_show_dry_run = show_dry_run
        self.org_strategy_select.command = on_strategy_chosen
        self.demo_target("org_strategy", self.org_strategy_select, demo_pick_strategy)
        self.demo_target("org_run", organize_btn, run_organize)
        self.demo_target("org_undo", undo_btn, run_undo)
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
            self.scroll.schedule_fit()
            self.demo_event("export_verify")

        self._export_run_integrity = run_integrity_check
        verify_btn = Btn(i_body, "Verify File Integrity Now", run_integrity_check,
                         icon_name="check-circle", kind="primary")
        verify_btn.pack(anchor="w")
        self.demo_target("export_verify", verify_btn, run_integrity_check)
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

        def snap_label(h):
            return (f"#{h['id']} — {h['scan_date']} — {os.path.basename(h['root_folder']) or h['root_folder']}"
                    f" ({h['total_files']} files, {fmt_size(h['total_bytes'])})")

        snap_labels = [snap_label(h) for h in history] or ["No snapshots yet"]

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
            self.scroll.schedule_fit()
            self.demo_event("export_compare")

        def save_manual_snapshot():
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            database.save_scan_snapshot(self.meta.get("root_folder", "Snapshot"), now_str)
            # Refresh the two snapshot dropdowns in place so integrity results stay on screen
            labels = [snap_label(h) for h in database.get_scan_history(limit=20)] or ["No snapshots yet"]
            for box in (older_select, newer_select):
                box.configure(values=labels)
            older_select.current(1 if len(labels) >= 2 else 0)
            newer_select.current(0)
            clear(diff_box)
            self.toast("Saved current inventory as a new scan snapshot")
            self.demo_event("export_snapshot")

        action_row = tk.Frame(h_body, bg=SURFACE)
        action_row.pack(fill="x")
        compare_btn = Btn(action_row, "Compare Two Snapshots", run_snapshot_compare,
                          icon_name="copy", kind="primary")
        compare_btn.pack(side="left", padx=(0, S(8)))
        snapshot_btn = Btn(action_row, "Save Current Snapshot", save_manual_snapshot,
                           icon_name="upload")
        snapshot_btn.pack(side="left")
        self.demo_target("export_compare", compare_btn, run_snapshot_compare)
        self.demo_target("export_snapshot", snapshot_btn, save_manual_snapshot)
        diff_box.pack(fill="x")


def main():
    load_embedded_fonts()
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()