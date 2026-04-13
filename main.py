"""
StudyQuest — Daily Study Heatmap Tracker
A gamified study tracker with GitHub-style heatmap, streaks, XP, and levels.
Cross-platform: Windows 11 + Linux (GNOME/Fedora/Ubuntu)
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Pure renderer — no PIL.ImageTk, no TkAgg
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import FancyBboxPatch
import numpy as np
from datetime import datetime, date, timedelta
import csv
import os
import json
import sys
import math

# ─── Resource path (works for source + PyInstaller bundle) ────────────────────
def resource_path(filename):
    """Return absolute path to a bundled resource, works with PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller extracts assets to a temp folder (_MEIPASS)
        return os.path.join(sys._MEIPASS, filename)
    # Running from source — look next to main.py
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

# ─── Config ────────────────────────────────────────────────────────────────────
APP_NAME = "StudyQuest"
VERSION = "1.0.0"

def get_data_dir():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.expanduser("~/.local/share")
    path = os.path.join(base, "StudyQuest")
    os.makedirs(path, exist_ok=True)
    return path

DATA_DIR = get_data_dir()
CSV_PATH = os.path.join(DATA_DIR, "study_log.csv")
META_PATH = os.path.join(DATA_DIR, "meta.json")

# ─── Colors ────────────────────────────────────────────────────────────────────
DARK_BG     = "#0d0d1a"
CARD_BG     = "#12122a"
ACCENT      = "#52b788"
ACCENT2     = "#74c69d"
TEXT_MAIN   = "#e0e0ff"
TEXT_DIM    = "#6060a0"
BORDER      = "#2a2a50"
RED         = "#ff6b6b"
GOLD        = "#ffd700"
ORANGE      = "#ff9f43"
PURPLE      = "#a29bfe"

# Heatmap color scale (0–5 levels)
HEAT_COLORS = ["#1a1a2e", "#1b4332", "#2d6a4f", "#40916c", "#52b788", "#74c69d"]

# XP per hour, level thresholds
XP_PER_HOUR = 50
LEVELS = [
    (0,    "📚 Beginner",     "#888"),
    (500,  "⚡ Learner",      "#52b788"),
    (1500, "🔥 Scholar",      "#ffd700"),
    (3000, "🌟 Expert",       "#a29bfe"),
    (6000, "💎 Master",       "#ff6b6b"),
    (10000,"👑 Legend",       "#ff9f43"),
]

BADGES = [
    {"id": "first_day",    "name": "First Step",    "icon": "🌱", "desc": "Log your first session",      "check": lambda s: s["total_days"] >= 1},
    {"id": "streak_3",     "name": "3-Day Streak",  "icon": "🔥", "desc": "Study 3 days in a row",       "check": lambda s: s["streak"] >= 3},
    {"id": "streak_7",     "name": "Week Warrior",  "icon": "⚔️",  "desc": "Study 7 days in a row",       "check": lambda s: s["streak"] >= 7},
    {"id": "streak_30",    "name": "Month Master",  "icon": "🏆", "desc": "Study 30 days in a row",      "check": lambda s: s["streak"] >= 30},
    {"id": "hours_10",     "name": "10 Hours",      "icon": "⏱️",  "desc": "Log 10 total hours",          "check": lambda s: s["total_hours"] >= 10},
    {"id": "hours_100",    "name": "100 Hours",     "icon": "💯", "desc": "Log 100 total hours",         "check": lambda s: s["total_hours"] >= 100},
    {"id": "perfect_week", "name": "Perfect Week",  "icon": "✨", "desc": "Study all 7 days in a week",  "check": lambda s: s["perfect_weeks"] >= 1},
    {"id": "early_bird",   "name": "Early Bird",    "icon": "🌅", "desc": "Log a session before 7 AM",   "check": lambda s: s["early_sessions"] >= 1},
]

# ─── Data Layer ────────────────────────────────────────────────────────────────
def load_csv():
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame(columns=["date","hours","subject","note","logged_at"])
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["hours"] = pd.to_numeric(df["hours"], errors="coerce").fillna(0)
    return df

def save_row(date_val, hours, subject, note):
    exists = os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["date","hours","subject","note","logged_at"])
        w.writerow([date_val, hours, subject, note, datetime.now().isoformat()])

def update_or_add(date_val, hours, subject, note):
    df = load_csv()
    df = df[df["date"] != date_val]  # remove existing entry for that date
    new_row = pd.DataFrame([{"date": date_val, "hours": hours,
                              "subject": subject, "note": note,
                              "logged_at": datetime.now().isoformat()}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(CSV_PATH, index=False)

def load_meta():
    if not os.path.exists(META_PATH):
        return {"earned_badges": [], "early_sessions": 0, "perfect_weeks": 0}
    with open(META_PATH) as f:
        return json.load(f)

def save_meta(meta):
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

def compute_stats(df):
    today = date.today()
    total_days = len(df[df["hours"] > 0]["date"].unique())
    total_hours = float(df["hours"].sum())
    xp = int(total_hours * XP_PER_HOUR)

    # streak
    streak = 0
    d = today
    dates_set = set(df[df["hours"] > 0]["date"].tolist())
    while d in dates_set:
        streak += 1
        d -= timedelta(days=1)

    # level
    level_idx = 0
    for i, (thresh, _, _) in enumerate(LEVELS):
        if xp >= thresh:
            level_idx = i
    level_name = LEVELS[level_idx][1]
    level_color = LEVELS[level_idx][2]
    next_thresh = LEVELS[min(level_idx + 1, len(LEVELS)-1)][0]
    prev_thresh = LEVELS[level_idx][0]
    xp_progress = (xp - prev_thresh) / max(next_thresh - prev_thresh, 1) if level_idx < len(LEVELS)-1 else 1.0

    # perfect weeks (any 7-day Mon–Sun block with 7 entries)
    meta = load_meta()
    perfect_weeks = meta.get("perfect_weeks", 0)
    early_sessions = meta.get("early_sessions", 0)

    return {
        "total_days": total_days,
        "total_hours": round(total_hours, 1),
        "xp": xp,
        "streak": streak,
        "level_name": level_name,
        "level_color": level_color,
        "level_idx": level_idx,
        "xp_progress": xp_progress,
        "perfect_weeks": perfect_weeks,
        "early_sessions": early_sessions,
    }

# ─── Heatmap Builder ───────────────────────────────────────────────────────────
def build_heatmap(df, year=None):
    if year is None:
        year = date.today().year
    today = date.today()

    # Aggregate hours per date
    daily = df.groupby("date")["hours"].sum().to_dict()

    # Build week grid
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    first_dow = start.weekday()  # Mon=0, so offset for Sun-start
    # We'll use Monday-start (ISO week)

    fig, ax = plt.subplots(figsize=(14, 2.8), facecolor=DARK_BG)
    ax.set_facecolor(DARK_BG)

    weeks = []
    cur = start - timedelta(days=start.weekday())  # back to Monday
    while cur <= end + timedelta(days=6):
        week = []
        for i in range(7):
            week.append(cur + timedelta(days=i))
        weeks.append(week)
        cur += timedelta(days=7)

    cell_size = 0.85
    gap = 0.15
    step = cell_size + gap

    DAYS_LABEL = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    MONTHS_LABEL = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    month_positions = {}

    for wi, week in enumerate(weeks):
        for di, day in enumerate(week):
            if day.year != year:
                continue
            hrs = daily.get(day, 0)
            lvl = 0
            if hrs > 0: lvl = min(int(hrs), 5)
            color = HEAT_COLORS[lvl]

            x = wi * step
            y = (6 - di) * step

            rect = FancyBboxPatch((x, y), cell_size, cell_size,
                                  boxstyle="round,pad=0.05",
                                  facecolor=color, edgecolor="none", linewidth=0)
            ax.add_patch(rect)

            if day == today:
                border = FancyBboxPatch((x - 0.05, y - 0.05), cell_size + 0.1, cell_size + 0.1,
                                        boxstyle="round,pad=0.05",
                                        facecolor="none", edgecolor=ACCENT, linewidth=1.5)
                ax.add_patch(border)

            # month label at first occurrence
            if day.day == 1 or (wi == 0 and di == 0):
                month_positions[day.month] = x

    # Month labels
    for month, x in month_positions.items():
        ax.text(x + cell_size/2, 7 * step + 0.1, MONTHS_LABEL[month - 1],
                color=TEXT_DIM, fontsize=7, ha="center", va="bottom",
                fontfamily="monospace")

    # Day labels
    for di, label in enumerate(DAYS_LABEL):
        if di % 2 == 0:
            y = (6 - di) * step + cell_size / 2
            ax.text(-0.6, y, label[0], color=TEXT_DIM, fontsize=7,
                    ha="right", va="center", fontfamily="monospace")

    ax.set_xlim(-1, len(weeks) * step + 0.5)
    ax.set_ylim(-0.5, 8 * step)
    ax.axis("off")
    fig.tight_layout(pad=0.3)
    return fig

def embed_figure(fig, parent):
    """Render matplotlib Figure into a tkinter widget using Agg + base64 PNG."""
    import io, base64
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), dpi=96)
    buf.seek(0)
    photo = tk.PhotoImage(data=base64.b64encode(buf.read()).decode())
    lbl = tk.Label(parent, image=photo, bg=DARK_BG, bd=0)
    lbl.image = photo  # prevent garbage collection
    lbl.pack(fill="x", pady=4)
    plt.close(fig)

# ─── UI ────────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class StudyQuestApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("1100x780")
        self.minsize(900, 650)
        self.configure(fg_color=DARK_BG)
        self.selected_date = date.today()
        self.heatmap_year = date.today().year
        self._set_icon()
        self._build_ui()
        self.refresh()

    def _set_icon(self):
        """Set window + taskbar icon using tkinter only — no PIL.ImageTk needed."""
        try:
            icon_path = resource_path("icon_256.png")
            if os.path.exists(icon_path):
                self._icon_img = tk.PhotoImage(file=icon_path)
                self.wm_iconphoto(True, self._icon_img)
        except Exception:
            pass  # Non-fatal: app runs fine without icon

    def _build_ui(self):
        # ── Sidebar ──
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=CARD_BG, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(self.sidebar, text="StudyQuest", font=("Courier New", 20, "bold"),
                     text_color=ACCENT).pack(pady=(28, 2))
        ctk.CTkLabel(self.sidebar, text="Daily Learning Tracker", font=("Courier New", 10),
                     text_color=TEXT_DIM).pack(pady=(0, 20))

        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [("📊  Dashboard", "dashboard"), ("➕  Log Session", "log"),
                     ("🏆  Achievements", "achievements"), ("📈  Analytics", "analytics")]
        for label, key in nav_items:
            btn = ctk.CTkButton(self.sidebar, text=label, anchor="w",
                                font=("Courier New", 13),
                                fg_color="transparent", hover_color="#1e1e40",
                                text_color=TEXT_MAIN, corner_radius=8,
                                command=lambda k=key: self.show_page(k))
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = btn

        # Stats mini-panel in sidebar
        self.sidebar_stats = ctk.CTkFrame(self.sidebar, fg_color="#0d0d1a", corner_radius=10)
        self.sidebar_stats.pack(fill="x", padx=12, pady=(20, 0))
        self.lbl_streak = ctk.CTkLabel(self.sidebar_stats, text="🔥 0 day streak",
                                       font=("Courier New", 12, "bold"), text_color=GOLD)
        self.lbl_streak.pack(pady=(10, 2))
        self.lbl_level = ctk.CTkLabel(self.sidebar_stats, text="📚 Beginner",
                                      font=("Courier New", 11), text_color=ACCENT)
        self.lbl_level.pack(pady=(0, 4))
        self.xp_bar = ctk.CTkProgressBar(self.sidebar_stats, width=160, progress_color=ACCENT,
                                          fg_color="#1a1a3a")
        self.xp_bar.pack(pady=(0, 4))
        self.xp_bar.set(0)
        self.lbl_xp = ctk.CTkLabel(self.sidebar_stats, text="0 XP", font=("Courier New", 10),
                                   text_color=TEXT_DIM)
        self.lbl_xp.pack(pady=(0, 10))

        # Version
        ctk.CTkLabel(self.sidebar, text=f"v{VERSION}", font=("Courier New", 9),
                     text_color="#333360").pack(side="bottom", pady=10)

        # ── Main content area ──
        self.main_area = ctk.CTkFrame(self, fg_color=DARK_BG, corner_radius=0)
        self.main_area.pack(side="right", fill="both", expand=True)

        # Pages dict
        self.pages = {}
        self._build_dashboard()
        self._build_log_page()
        self._build_achievements_page()
        self._build_analytics_page()
        self.show_page("dashboard")

    # ── Page: Dashboard ──
    def _build_dashboard(self):
        page = ctk.CTkScrollableFrame(self.main_area, fg_color=DARK_BG, corner_radius=0)
        self.pages["dashboard"] = page

        ctk.CTkLabel(page, text="Dashboard", font=("Courier New", 24, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=24, pady=(24, 4))
        ctk.CTkLabel(page, text="Your study activity this year",
                     font=("Courier New", 11), text_color=TEXT_DIM).pack(anchor="w", padx=24)

        # Stat cards row
        self.stat_cards_frame = ctk.CTkFrame(page, fg_color="transparent")
        self.stat_cards_frame.pack(fill="x", padx=24, pady=16)

        self.stat_labels = {}
        stats_def = [("🔥", "Streak", "streak", "days"),
                     ("📅", "Days Studied", "total_days", "days"),
                     ("⏱️",  "Total Hours", "total_hours", "hrs"),
                     ("⚡", "XP Earned", "xp", "XP")]
        for icon, title, key, unit in stats_def:
            card = ctk.CTkFrame(self.stat_cards_frame, fg_color=CARD_BG,
                                corner_radius=12, border_width=1, border_color=BORDER)
            card.pack(side="left", fill="x", expand=True, padx=5)
            ctk.CTkLabel(card, text=icon, font=("", 22)).pack(pady=(14, 0))
            lbl = ctk.CTkLabel(card, text="0", font=("Courier New", 26, "bold"),
                               text_color=ACCENT)
            lbl.pack()
            ctk.CTkLabel(card, text=title, font=("Courier New", 10),
                         text_color=TEXT_DIM).pack(pady=(0, 14))
            self.stat_labels[key] = lbl

        # Heatmap card
        hm_card = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=12,
                               border_width=1, border_color=BORDER)
        hm_card.pack(fill="x", padx=24, pady=(0, 16))

        hm_top = ctk.CTkFrame(hm_card, fg_color="transparent")
        hm_top.pack(fill="x", padx=16, pady=(14, 0))
        ctk.CTkLabel(hm_top, text="Activity Heatmap", font=("Courier New", 14, "bold"),
                     text_color=TEXT_MAIN).pack(side="left")

        yr_frame = ctk.CTkFrame(hm_top, fg_color="transparent")
        yr_frame.pack(side="right")
        cur_yr = date.today().year
        for y in [cur_yr - 1, cur_yr]:
            ctk.CTkButton(yr_frame, text=str(y), width=60, height=28,
                          font=("Courier New", 11),
                          fg_color=ACCENT if y == cur_yr else "#1a1a3a",
                          hover_color="#2d6a4f",
                          command=lambda yr=y: self.switch_year(yr)).pack(side="left", padx=3)

        self.heatmap_frame = ctk.CTkFrame(hm_card, fg_color=DARK_BG, corner_radius=8)
        self.heatmap_frame.pack(fill="x", padx=16, pady=12)

        # Legend
        leg = ctk.CTkFrame(hm_card, fg_color="transparent")
        leg.pack(padx=16, pady=(0, 14))
        ctk.CTkLabel(leg, text="Less", font=("Courier New", 10), text_color=TEXT_DIM).pack(side="left", padx=(0, 4))
        for c in HEAT_COLORS:
            box = tk.Label(leg, bg=c, width=2, height=1, relief="flat")
            box.pack(side="left", padx=1)
        ctk.CTkLabel(leg, text="More", font=("Courier New", 10), text_color=TEXT_DIM).pack(side="left", padx=(4, 0))

        # Today's entry quick view
        self.today_card = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=12,
                                       border_width=1, border_color=BORDER)
        self.today_card.pack(fill="x", padx=24, pady=(0, 24))
        ctk.CTkLabel(self.today_card, text=f"Today — {date.today().strftime('%A, %B %d %Y')}",
                     font=("Courier New", 13, "bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=16, pady=(14, 2))
        self.today_info = ctk.CTkLabel(self.today_card, text="No session logged yet.",
                                       font=("Courier New", 11), text_color=TEXT_DIM)
        self.today_info.pack(anchor="w", padx=16, pady=(0, 14))
        ctk.CTkButton(self.today_card, text="➕  Log Today's Session",
                      font=("Courier New", 12, "bold"),
                      fg_color=ACCENT, hover_color="#2d6a4f", text_color=DARK_BG,
                      command=lambda: self.show_page("log")).pack(padx=16, pady=(0, 14))

    # ── Page: Log Session ──
    def _build_log_page(self):
        page = ctk.CTkScrollableFrame(self.main_area, fg_color=DARK_BG, corner_radius=0)
        self.pages["log"] = page

        ctk.CTkLabel(page, text="Log Session", font=("Courier New", 24, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=24, pady=(24, 4))
        ctk.CTkLabel(page, text="Record what you studied today",
                     font=("Courier New", 11), text_color=TEXT_DIM).pack(anchor="w", padx=24)

        form = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=12,
                            border_width=1, border_color=BORDER)
        form.pack(fill="x", padx=24, pady=20)

        # Date picker (simple entry)
        ctk.CTkLabel(form, text="Date", font=("Courier New", 12, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(20, 4))
        self.date_entry = ctk.CTkEntry(form, placeholder_text="YYYY-MM-DD",
                                       font=("Courier New", 13), height=40,
                                       fg_color="#1a1a3a", border_color=BORDER,
                                       text_color=TEXT_MAIN)
        self.date_entry.pack(fill="x", padx=20, pady=(0, 4))
        self.date_entry.insert(0, str(date.today()))

        # Hours slider
        ctk.CTkLabel(form, text="Hours Studied", font=("Courier New", 12, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(12, 4))
        self.hours_val_lbl = ctk.CTkLabel(form, text="1.0 hours",
                                          font=("Courier New", 20, "bold"), text_color=ACCENT)
        self.hours_val_lbl.pack()
        self.hours_slider = ctk.CTkSlider(form, from_=0.5, to=8, number_of_steps=15,
                                          progress_color=ACCENT, button_color=ACCENT2,
                                          command=self._on_slider)
        self.hours_slider.set(1)
        self.hours_slider.pack(fill="x", padx=20, pady=(0, 4))

        hrs_labels = ctk.CTkFrame(form, fg_color="transparent")
        hrs_labels.pack(fill="x", padx=20)
        for t in ["0.5h", "2h", "4h", "6h", "8h"]:
            ctk.CTkLabel(hrs_labels, text=t, font=("Courier New", 9),
                         text_color=TEXT_DIM).pack(side="left", expand=True)

        # Subject
        ctk.CTkLabel(form, text="Subject / Topic", font=("Courier New", 12, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(16, 4))
        self.subject_entry = ctk.CTkEntry(form, placeholder_text="e.g. Data Structures, Math, Physics...",
                                          font=("Courier New", 13), height=40,
                                          fg_color="#1a1a3a", border_color=BORDER,
                                          text_color=TEXT_MAIN)
        self.subject_entry.pack(fill="x", padx=20)

        # Subjects quick-select
        subjects_frame = ctk.CTkFrame(form, fg_color="transparent")
        subjects_frame.pack(fill="x", padx=20, pady=6)
        for subj in ["Math", "Physics", "CS", "Chemistry", "History", "Language"]:
            ctk.CTkButton(subjects_frame, text=subj, width=80, height=26,
                          font=("Courier New", 10), fg_color="#1a1a3a",
                          hover_color="#2d6a4f", text_color=TEXT_DIM,
                          command=lambda s=subj: self._quick_subject(s)).pack(side="left", padx=3)

        # Note
        ctk.CTkLabel(form, text="Notes (optional)", font=("Courier New", 12, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=20, pady=(12, 4))
        self.note_entry = ctk.CTkTextbox(form, height=80, font=("Courier New", 12),
                                         fg_color="#1a1a3a", border_color=BORDER,
                                         text_color=TEXT_MAIN)
        self.note_entry.pack(fill="x", padx=20)
        self.note_entry.insert("1.0", "What did you study? Key takeaways...")

        # XP preview
        self.xp_preview = ctk.CTkLabel(form, text="⚡ +50 XP",
                                       font=("Courier New", 14, "bold"), text_color=GOLD)
        self.xp_preview.pack(pady=(12, 0))

        # Submit
        ctk.CTkButton(form, text="✅  Save Session", height=48,
                      font=("Courier New", 14, "bold"),
                      fg_color=ACCENT, hover_color="#2d6a4f", text_color=DARK_BG,
                      command=self._save_session).pack(fill="x", padx=20, pady=(12, 20))

        # Recent logs
        ctk.CTkLabel(page, text="Recent Sessions", font=("Courier New", 14, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=24, pady=(0, 8))
        self.recent_frame = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=12,
                                         border_width=1, border_color=BORDER)
        self.recent_frame.pack(fill="x", padx=24, pady=(0, 24))

    def _on_slider(self, val):
        h = round(float(val) * 2) / 2
        self.hours_val_lbl.configure(text=f"{h} hours")
        self.xp_preview.configure(text=f"⚡ +{int(h * XP_PER_HOUR)} XP")

    def _quick_subject(self, s):
        self.subject_entry.delete(0, "end")
        self.subject_entry.insert(0, s)

    def _save_session(self):
        try:
            d = date.fromisoformat(self.date_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
            return
        hours = round(float(self.hours_slider.get()) * 2) / 2
        subject = self.subject_entry.get().strip() or "General"
        note_text = self.note_entry.get("1.0", "end").strip()
        if note_text == "What did you study? Key takeaways...":
            note_text = ""
        update_or_add(d, hours, subject, note_text)

        # Check early bird
        if datetime.now().hour < 7:
            meta = load_meta()
            meta["early_sessions"] = meta.get("early_sessions", 0) + 1
            save_meta(meta)

        self.refresh()
        self._show_save_popup(hours, subject)

    def _show_save_popup(self, hours, subject):
        popup = ctk.CTkToplevel(self)
        popup.title("Session Saved!")
        popup.geometry("360x220")
        popup.configure(fg_color=CARD_BG)
        popup.grab_set()
        ctk.CTkLabel(popup, text="✅ Session Saved!", font=("Courier New", 18, "bold"),
                     text_color=ACCENT).pack(pady=(30, 6))
        ctk.CTkLabel(popup, text=f"{hours}h of {subject}", font=("Courier New", 13),
                     text_color=TEXT_MAIN).pack()
        ctk.CTkLabel(popup, text=f"⚡ +{int(hours * XP_PER_HOUR)} XP earned!",
                     font=("Courier New", 13, "bold"), text_color=GOLD).pack(pady=6)
        ctk.CTkButton(popup, text="Keep Going! 🚀", fg_color=ACCENT, text_color=DARK_BG,
                      font=("Courier New", 12, "bold"),
                      command=popup.destroy).pack(pady=16)

    # ── Page: Achievements ──
    def _build_achievements_page(self):
        page = ctk.CTkScrollableFrame(self.main_area, fg_color=DARK_BG, corner_radius=0)
        self.pages["achievements"] = page

        ctk.CTkLabel(page, text="Achievements", font=("Courier New", 24, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=24, pady=(24, 4))
        ctk.CTkLabel(page, text="Unlock badges by hitting milestones",
                     font=("Courier New", 11), text_color=TEXT_DIM).pack(anchor="w", padx=24)

        self.badges_frame = ctk.CTkFrame(page, fg_color="transparent")
        self.badges_frame.pack(fill="x", padx=24, pady=16)

        ctk.CTkLabel(page, text="Level Progression", font=("Courier New", 14, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=24)
        self.levels_frame = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=12,
                                         border_width=1, border_color=BORDER)
        self.levels_frame.pack(fill="x", padx=24, pady=12)
        for thresh, name, color in LEVELS:
            row = ctk.CTkFrame(self.levels_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(row, text=name, font=("Courier New", 12, "bold"),
                         text_color=color, width=160).pack(side="left")
            ctk.CTkLabel(row, text=f"{thresh} XP", font=("Courier New", 11),
                         text_color=TEXT_DIM).pack(side="left", padx=8)

    def _refresh_badges(self, stats):
        for w in self.badges_frame.winfo_children():
            w.destroy()
        meta = load_meta()
        earned = set(meta.get("earned_badges", []))
        new_earned = []
        for badge in BADGES:
            if badge["check"](stats) and badge["id"] not in earned:
                earned.add(badge["id"])
                new_earned.append(badge["name"])
        if new_earned:
            meta["earned_badges"] = list(earned)
            save_meta(meta)
            for name in new_earned:
                self._show_badge_popup(name)

        cols = 3
        for i, badge in enumerate(BADGES):
            unlocked = badge["id"] in earned
            card = ctk.CTkFrame(self.badges_frame, fg_color=CARD_BG if unlocked else "#0d0d1a",
                                corner_radius=12, border_width=1,
                                border_color=ACCENT if unlocked else BORDER)
            row_f = i // cols
            col_f = i % cols
            card.grid(row=row_f, column=col_f, padx=6, pady=6, sticky="ew")
            self.badges_frame.columnconfigure(col_f, weight=1)

            ctk.CTkLabel(card, text=badge["icon"], font=("", 28)).pack(pady=(16, 4))
            ctk.CTkLabel(card, text=badge["name"], font=("Courier New", 12, "bold"),
                         text_color=TEXT_MAIN if unlocked else TEXT_DIM).pack()
            ctk.CTkLabel(card, text=badge["desc"], font=("Courier New", 9),
                         text_color=TEXT_DIM, wraplength=140).pack(pady=(2, 14))
            if not unlocked:
                ctk.CTkLabel(card, text="🔒 Locked", font=("Courier New", 9),
                             text_color="#333360").pack(pady=(0, 10))

    def _show_badge_popup(self, badge_name):
        popup = ctk.CTkToplevel(self)
        popup.title("Badge Unlocked!")
        popup.geometry("340x180")
        popup.configure(fg_color=CARD_BG)
        popup.grab_set()
        ctk.CTkLabel(popup, text="🏆 Badge Unlocked!", font=("Courier New", 17, "bold"),
                     text_color=GOLD).pack(pady=(28, 6))
        ctk.CTkLabel(popup, text=badge_name, font=("Courier New", 14),
                     text_color=TEXT_MAIN).pack()
        ctk.CTkButton(popup, text="Awesome! 🎉", fg_color=ACCENT, text_color=DARK_BG,
                      font=("Courier New", 12, "bold"),
                      command=popup.destroy).pack(pady=20)

    # ── Page: Analytics ──
    def _build_analytics_page(self):
        page = ctk.CTkScrollableFrame(self.main_area, fg_color=DARK_BG, corner_radius=0)
        self.pages["analytics"] = page

        ctk.CTkLabel(page, text="Analytics", font=("Courier New", 24, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=24, pady=(24, 4))
        ctk.CTkLabel(page, text="Study patterns & subject breakdown",
                     font=("Courier New", 11), text_color=TEXT_DIM).pack(anchor="w", padx=24)

        self.analytics_chart_frame = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=12,
                                                   border_width=1, border_color=BORDER)
        self.analytics_chart_frame.pack(fill="x", padx=24, pady=16)

        self.analytics_subject_frame = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=12,
                                                     border_width=1, border_color=BORDER)
        self.analytics_subject_frame.pack(fill="x", padx=24, pady=(0, 24))

    def _refresh_analytics(self, df):
        # Weekly bar chart (last 8 weeks)
        for w in self.analytics_chart_frame.winfo_children():
            w.destroy()
        for w in self.analytics_subject_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.analytics_chart_frame, text="Weekly Hours (last 8 weeks)",
                     font=("Courier New", 13, "bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=16, pady=(14, 8))

        fig2, ax2 = plt.subplots(figsize=(9, 2.6), facecolor=DARK_BG)
        ax2.set_facecolor(DARK_BG)
        today = date.today()
        weeks_data = []
        for w in range(7, -1, -1):
            week_start = today - timedelta(days=today.weekday() + 7 * w)
            week_end = week_start + timedelta(days=6)
            mask = [(d >= week_start and d <= week_end) for d in df["date"]]
            hours = df[mask]["hours"].sum() if any(mask) else 0
            weeks_data.append((week_start.strftime("%b %d"), float(hours)))

        labels, vals = zip(*weeks_data) if weeks_data else ([], [])
        colors = [ACCENT if v > 0 else "#1a1a3a" for v in vals]
        bars = ax2.bar(range(len(vals)), vals, color=colors, width=0.6, edgecolor="none")
        ax2.set_xticks(range(len(labels)))
        ax2.set_xticklabels(labels, color=TEXT_DIM, fontsize=8, rotation=20)
        ax2.tick_params(colors=TEXT_DIM, labelsize=8)
        ax2.spines[:].set_visible(False)
        ax2.set_facecolor(DARK_BG)
        ax2.yaxis.label.set_color(TEXT_DIM)
        ax2.tick_params(axis="y", colors=TEXT_DIM)
        ax2.set_ylabel("Hours", color=TEXT_DIM, fontsize=8)
        fig2.tight_layout(pad=0.5)
        embed_figure(fig2, self.analytics_chart_frame)

        # Subject breakdown
        ctk.CTkLabel(self.analytics_subject_frame, text="Hours by Subject",
                     font=("Courier New", 13, "bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=16, pady=(14, 8))
        if len(df) > 0 and "subject" in df.columns:
            subj_hours = df.groupby("subject")["hours"].sum().sort_values(ascending=False)
            total = subj_hours.sum() or 1
            palette = [ACCENT, ACCENT2, GOLD, ORANGE, PURPLE, RED, "#74c69d", "#a8edea"]
            for i, (subj, hrs) in enumerate(subj_hours.items()):
                row = ctk.CTkFrame(self.analytics_subject_frame, fg_color="transparent")
                row.pack(fill="x", padx=16, pady=3)
                ctk.CTkLabel(row, text=subj, font=("Courier New", 11),
                             text_color=TEXT_MAIN, width=120, anchor="w").pack(side="left")
                bar_frame = ctk.CTkFrame(row, fg_color="#1a1a3a", corner_radius=4, height=14)
                bar_frame.pack(side="left", fill="x", expand=True, padx=8)
                bar_fill = ctk.CTkFrame(bar_frame, fg_color=palette[i % len(palette)],
                                        corner_radius=4, height=14,
                                        width=int(180 * hrs / total))
                bar_fill.place(x=0, y=0)
                ctk.CTkLabel(row, text=f"{hrs:.1f}h", font=("Courier New", 10),
                             text_color=TEXT_DIM, width=50).pack(side="left")
        else:
            ctk.CTkLabel(self.analytics_subject_frame, text="No data yet. Start logging sessions!",
                         font=("Courier New", 11), text_color=TEXT_DIM).pack(pady=20)

        ctk.CTkFrame(self.analytics_subject_frame, fg_color="transparent", height=14).pack()

    # ── Navigation ──
    def show_page(self, key):
        for k, p in self.pages.items():
            p.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        for k, b in self.nav_buttons.items():
            b.configure(fg_color=ACCENT if k == key else "transparent",
                        text_color=DARK_BG if k == key else TEXT_MAIN)

    def switch_year(self, yr):
        self.heatmap_year = yr
        self._refresh_heatmap(load_csv())

    def _refresh_heatmap(self, df):
        for w in self.heatmap_frame.winfo_children():
            w.destroy()
        fig = build_heatmap(df, self.heatmap_year)
        embed_figure(fig, self.heatmap_frame)

    def _refresh_recent(self, df):
        for w in self.recent_frame.winfo_children():
            w.destroy()
        recent = df.sort_values("date", ascending=False).head(7)
        if len(recent) == 0:
            ctk.CTkLabel(self.recent_frame, text="No sessions yet. Log your first one! 🚀",
                         font=("Courier New", 11), text_color=TEXT_DIM).pack(pady=20)
            return
        for _, row in recent.iterrows():
            r = ctk.CTkFrame(self.recent_frame, fg_color="#0d0d1a", corner_radius=8)
            r.pack(fill="x", padx=10, pady=4)
            ctk.CTkLabel(r, text=str(row["date"]), font=("Courier New", 11, "bold"),
                         text_color=ACCENT, width=110).pack(side="left", padx=(12, 4), pady=10)
            ctk.CTkLabel(r, text=f"{row['hours']}h", font=("Courier New", 13, "bold"),
                         text_color=GOLD).pack(side="left", padx=4)
            ctk.CTkLabel(r, text=str(row.get("subject", "")), font=("Courier New", 11),
                         text_color=TEXT_MAIN).pack(side="left", padx=8)
            if row.get("note"):
                ctk.CTkLabel(r, text=str(row["note"])[:40], font=("Courier New", 10),
                             text_color=TEXT_DIM).pack(side="left", padx=4)

    def refresh(self):
        df = load_csv()
        stats = compute_stats(df)

        # Sidebar
        self.lbl_streak.configure(text=f"🔥 {stats['streak']} day streak")
        self.lbl_level.configure(text=stats["level_name"], text_color=stats["level_color"])
        self.xp_bar.set(stats["xp_progress"])
        self.lbl_xp.configure(text=f"{stats['xp']} XP")

        # Dashboard stat cards
        for key in ["streak", "total_days", "total_hours", "xp"]:
            self.stat_labels[key].configure(text=str(stats[key]))

        # Today info
        today = date.today()
        today_rows = df[df["date"] == today]
        if len(today_rows) > 0:
            r = today_rows.iloc[-1]
            self.today_info.configure(
                text=f"✅  {r['hours']}h logged — {r.get('subject', '')} {('· ' + str(r['note'])[:30]) if r.get('note') else ''}",
                text_color=ACCENT)
        else:
            self.today_info.configure(text="No session logged yet.", text_color=TEXT_DIM)

        self._refresh_heatmap(df)
        self._refresh_recent(df)
        self._refresh_badges(stats)
        self._refresh_analytics(df)

# ─── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = StudyQuestApp()
    app.mainloop()
