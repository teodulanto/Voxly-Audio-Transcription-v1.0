"""
Voxly - Stylized Compact HUD (Tkinter)
Optimized for voice-reactive visualizer bars and compact styling.
"""
import tkinter as tk
from tkinter import font as tkfont
import threading
import os
import math
from PIL import Image, ImageTk


class HudWindow:
    # ── Design Tokens ───────────────────────────────────────────────────────
    CHROMA  = "#010203"       # Windows chroma-key transparency
    PILL_BG = "#121212"       # Modern dark grey
    FG      = "#FFFFFF"       # Pure white for status
    FG_HINT = "#9CA3AF"       # Gray-400 for hints
    ACCENT  = "#3B82F6"       # Blue-500 for bars
    RED_DOT = "#EF4444"       # Red-500 for recording

    # ── Compact Geometry ────────────────────────────────────────────────────
    W = 380                   # More compact width
    H = 56                    # More compact height
    R = 28                    # H/2
    PAD = 15                  # Canvas padding

    def __init__(self, icon_path=None):
        self.icon_path = icon_path
        self.root      = None
        self._ready    = threading.Event()
        self._anim_id  = None
        self._tick_cnt = 0
        self._bars     = []
        self._state    = "standby"
        self._current_vol = 0.0 # Reactive volume level

    # ────────────────────────────────────── Build ──────────────────────────
    def _build(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Window Props
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-alpha", 1.0)
        self.root.configure(bg=self.CHROMA)
        self.root.wm_attributes("-transparentcolor", self.CHROMA)
        self._set_icon()

        # Build Canvas
        cw, ch = self.W + self.PAD * 2, self.H + self.PAD * 2
        self.canvas = tk.Canvas(self.root, width=cw, height=ch, 
                                bg=self.CHROMA, highlightthickness=0)
        self.canvas.pack()

        # Draw Base Pill
        x0, y0 = self.PAD, self.PAD
        x1, y1 = self.PAD + self.W, self.PAD + self.H
        self._draw_rounded_pill(x0, y0, x1, y1, self.R)

        # ── Main Layout Container ──────────────────────────────────────────
        self.main_frame = tk.Frame(self.canvas, bg=self.PILL_BG)
        
        # Left Content: Dot + Bars
        self.left_box = tk.Frame(self.main_frame, bg=self.PILL_BG)
        self.left_box.pack(side="left", padx=(18, 0))

        # 1. Red Dot (Smaller)
        self.dot_size = 10
        self.dot_canvas = tk.Canvas(self.left_box, width=self.dot_size, height=self.dot_size,
                                    bg=self.PILL_BG, highlightthickness=0)
        self.dot_canvas.pack(side="left", padx=(0, 10))
        self.dot_obj = self.dot_canvas.create_oval(1, 1, self.dot_size-1, self.dot_size-1,
                                                   fill=self.PILL_BG, outline="")

        # 2. Visualizer Bars (Compact)
        self.bar_w, self.bar_gap, self.n_bars = 4, 4, 5
        self.bars_width = self.n_bars * self.bar_w + (self.n_bars - 1) * self.bar_gap
        self.bars_height = 24
        self.bar_canvas = tk.Canvas(self.left_box, width=self.bars_width, height=self.bars_height,
                                    bg=self.PILL_BG, highlightthickness=0)
        self.bar_canvas.pack(side="left")
        
        b_mid = self.bars_height // 2
        for i in range(self.n_bars):
            bx = i * (self.bar_w + self.bar_gap)
            rect = self.bar_canvas.create_rectangle(bx, b_mid - 2, bx + self.bar_w, b_mid + 2,
                                                    fill=self.ACCENT, outline="", width=0)
            self._bars.append(rect)

        # Right Content: Text Stack
        self.right_box = tk.Frame(self.main_frame, bg=self.PILL_BG)
        self.right_box.pack(side="left", padx=(16, 20))

        # Stylized Typography (Compact)
        self.f_status = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.f_hint   = tkfont.Font(family="Segoe UI", size=9)

        self.lbl_status = tk.Label(self.right_box, text="Standby", font=self.f_status,
                                   fg=self.FG, bg=self.PILL_BG, anchor="w")
        self.lbl_status.pack(anchor="w")

        self.lbl_hint = tk.Label(self.right_box, text="Press Ctrl+Alt+V to dictate", 
                                 font=self.f_hint, fg=self.FG_HINT, bg=self.PILL_BG, anchor="w")
        self.lbl_hint.pack(anchor="w")

        # Position main_frame on canvas
        self.canvas.create_window(cw // 2, ch // 2, window=self.main_frame, anchor="center")

        # Drag support
        for w in [self.canvas, self.main_frame, self.left_box, self.right_box, self.lbl_status, self.lbl_hint]:
            w.bind("<Button-1>", self._on_press)
            w.bind("<B1-Motion>", self._on_motion)

        # Positioning (Top-Center)
        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"+{(sw - cw) // 2}+30")

        self._ready.set()
        self.root.mainloop()

    # ────────────────────────────────────── Logic ────────────────────────────
    def _draw_rounded_pill(self, x0, y0, x1, y1, r):
        # Draw arcs and rectangles to form a pill
        self.canvas.create_arc(x0, y0, x0 + 2*r, y0 + 2*r, start=90, extent=90, style="pieslice", fill=self.PILL_BG, outline=self.PILL_BG)
        self.canvas.create_arc(x1 - 2*r, y0, x1, y0 + 2*r, start=0, extent=90, style="pieslice", fill=self.PILL_BG, outline=self.PILL_BG)
        self.canvas.create_arc(x0, y1 - 2*r, x0 + 2*r, y1, start=180, extent=90, style="pieslice", fill=self.PILL_BG, outline=self.PILL_BG)
        self.canvas.create_arc(x1 - 2*r, y1 - 2*r, x1, y1, start=270, extent=90, style="pieslice", fill=self.PILL_BG, outline=self.PILL_BG)
        self.canvas.create_rectangle(x0 + r, y0, x1 - r, y1, fill=self.PILL_BG, outline=self.PILL_BG)
        self.canvas.create_rectangle(x0, y0 + r, x1, y1 - r, fill=self.PILL_BG, outline=self.PILL_BG)

    def _set_icon(self):
        if not self.icon_path: return
        try:
            ico = self.icon_path.replace('.png', '.ico')
            if os.path.exists(ico): self.root.iconbitmap(ico)
        except Exception: pass

    def _on_press(self, event):
        self._offset_x = event.x_root - self.root.winfo_x()
        self._offset_y = event.y_root - self.root.winfo_y()

    def _on_motion(self, event):
        x = event.x_root - self._offset_x
        y = event.y_root - self._offset_y
        self.root.geometry(f"+{x}+{y}")

    # ────────────────────────────────────── Animation ───────────────────────
    def _animate(self):
        if not self.root: return
        
        if self._state == "recording":
                # Reactive animation based on self._current_vol
                # Reset bars height based on volume with high contrast
                b_mid = self.bars_height // 2
                for i, bar in enumerate(self._bars):
                    # Add unique offset to each bar for organic look
                    offset = (i % 3) * 0.05
                    # Enhance sensitivity: use exponential scaling for drama
                    # raw volume usually ranges 0-0.2, we want to pop at speak levels
                    v = max(0.01, self._current_vol + offset)
                    # Non-linear scaling: small sounds stay small, voice pops
                    h_factor = math.pow(v * 7.0, 1.2) 
                    h = 4 + int(24 * min(1.0, h_factor)) 
                    
                    bx = i * (self.bar_w + self.bar_gap)
                    self.bar_canvas.coords(bar, bx, b_mid - h//2, bx + self.bar_w, b_mid + h//2)
                # Faster decay for snappier response
                self._current_vol *= 0.7 
        elif self._state in ["processing", "loading"]:
            # Standard sinusoidal animation
            b_mid = self.bars_height // 2
            for i, bar in enumerate(self._bars):
                phase = self._tick_cnt * 0.2 + i * 0.8
                h = 4 + int(10 * (0.5 + 0.5 * math.sin(phase)))
                bx = i * (self.bar_w + self.bar_gap)
                self.bar_canvas.coords(bar, bx, b_mid - h//2, bx + self.bar_w, b_mid + h//2)
            self._tick_cnt += 1
        else:
            # Standby: static bars
            self._anim_id = None
            return

        self._anim_id = self.root.after(50, self._animate)

    # ────────────────────────────────────── API ──────────────────────────────
    def set_volume_level(self, level):
        """Update the volume level for reactive bars."""
        # Sensitivity adjustment
        if level > self._current_vol:
            self._current_vol = level
        else:
            self._current_vol = self._current_vol * 0.4 + level * 0.6

    def start(self):
        t = threading.Thread(target=self._build, daemon=True)
        t.start()
        self._ready.wait(timeout=5)

    def show(self):
        if self.root: self.root.after(0, self.root.deiconify)

    def hide(self):
        if self.root: self.root.after(0, self.root.withdraw)

    def update_status(self, state, message, hint=""):
        if not self.root: return
        def _task():
            self._state = state
            self.lbl_status.config(text=message)
            self.lbl_hint.config(text=hint)
            
            # Recording Dot Visibility
            if state == "recording":
                self.dot_canvas.itemconfig(self.dot_obj, fill=self.RED_DOT)
            else:
                self.dot_canvas.itemconfig(self.dot_obj, fill=self.PILL_BG)

            # Start animation
            if state in ["recording", "processing", "loading"]:
                if not self._anim_id:
                    self._animate()
            else:
                # Reset to standby (flat bars)
                b_mid = self.bars_height // 2
                for i, bar in enumerate(self._bars):
                    bx = i * (self.bar_w + self.bar_gap)
                    self.bar_canvas.coords(bar, bx, b_mid - 2, bx + self.bar_w, b_mid + 2)

        self.root.after(0, _task)

    def set_preview(self, text):
        if self.root:
            self.root.after(0, lambda: self.lbl_hint.config(
                text=text if text else "Press Ctrl+Alt+V to dictate",
                fg=self.ACCENT if text else self.FG_HINT
            ))

    def destroy(self):
        if self.root:
            self.root.after(0, self.root.destroy)
            self.root = None
