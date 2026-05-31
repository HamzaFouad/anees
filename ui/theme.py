from PySide6.QtWidgets import QApplication

# ── Colors ────────────────────────────────────────────────────────────────────
PRIMARY       = "#0044FF"
PRIMARY_HOVER = "#0039D9"
PRIMARY_TINT  = "rgba(0,68,255,0.10)"

FG            = "#0F1729"
FG_MUTED      = "#5C6F8A"
FG_SUBTLE     = "#344256"

BG            = "#FFFFFF"
BG_MUTED      = "#F8FAFC"
BG_SUBTLE     = "#F1F5F9"
BG_ACCENT     = "#F3F4F7"

BORDER        = "#E5E7EB"

SUCCESS       = "#10B981"
SUCCESS_DARK  = "#065F46"
SUCCESS_BG    = "#D1FAE5"

ERROR         = "#EF4444"
ERROR_DARK    = "#991B1B"
ERROR_BG      = "#FEE2E2"
ERROR_BORDER  = "#FECACA"

WARN_DARK     = "#92400E"
WARN_BG       = "#FEF3C7"

# ── Semantic surface / state roles ────────────────────────────────────────────
ON_PRIMARY      = "#FFFFFF"           # text/icon on solid PRIMARY fill
ROW_DIVIDER     = "#EAECF0"           # 1 px row separators in tables/lists
DISABLED_BG     = "#F3F4F6"           # disabled button / input background
DISABLED_FG     = "#9CA3AF"           # disabled text
SURFACE_ALT     = "#E2E8F0"           # secondary button bg; toggle track-off
INACTIVE        = "#D6D3D1"           # inactive playlist status dot
WIN_CLOSE_HOVER = "#E81123"           # Windows system close-button hover

# ── Tint palette (all rgba(primary/error, …) usages consolidated) ─────────────
PRIMARY_TINT_4  = "rgba(0,68,255,0.04)"
PRIMARY_TINT_8  = "rgba(0,68,255,0.08)"   # PRIMARY_TINT stays as 0.10
PRIMARY_TINT_18 = "rgba(0,68,255,0.18)"
ERROR_TINT_4    = "rgba(239,68,68,0.04)"
ERROR_TINT_10   = "rgba(239,68,68,0.10)"
WARN_TINT_4     = "rgba(245,158,11,0.04)"

# ── Log level surfaces ────────────────────────────────────────────────────────
LOG_BG_INFO  = "#E8ECF2"
LOG_BG_DEBUG = "#F1F5F9"
LOG_BG_DARK  = "#0E142C"              # expandable log-detail background
FG_ON_DARK   = "rgba(255,255,255,0.78)"

# ── Typography ────────────────────────────────────────────────────────────────
FONT_UI   = "'.AppleSystemUIFont','Segoe UI','Helvetica Neue',sans-serif"
FONT_MONO = "'JetBrains Mono','Menlo','Consolas','Courier New',monospace"
TEXT_XS   = 10    # uppercase field labels, badge counts
TEXT_SM   = 11    # timestamps, secondary labels, hints
TEXT_MD   = 12    # body text, table cells, button text
TEXT_BASE = 13    # global default
TEXT_LG   = 14    # dialog titles
TEXT_XL   = 16    # detail panel playlist title
TEXT_2XL  = 18    # history summary values

# ── Spacing scale ─────────────────────────────────────────────────────────────
SPACE_2  = 2;  SPACE_4  = 4;  SPACE_6  = 6;  SPACE_8  = 8
SPACE_10 = 10; SPACE_12 = 12; SPACE_14 = 14; SPACE_16 = 16
SPACE_18 = 18; SPACE_20 = 20; SPACE_24 = 24

# ── Radius scale ─────────────────────────────────────────────────────────────
RADIUS_SM   = 4    # checkboxes, badges, small buttons
RADIUS_MD   = 6    # main buttons, inputs
RADIUS_LG   = 8    # cards
RADIUS_XL   = 12   # large cards
RADIUS_PILL = 99   # fully-rounded pills

# ── Fixed component dimensions ────────────────────────────────────────────────
H_TITLEBAR  = 36;  H_TOOLBAR  = 52;  H_TABBAR    = 36;  H_STATUSBAR = 24
H_BTN_SM    = 28;  H_BTN_MD   = 32;  H_ROW       = 44
W_SIDEBAR   = 280; W_COL_IDX  = 28;  W_COL_DUR   = 50
W_COL_STAGE = 28;  W_COL_STATE = 92

# ── Equalizer icon SVG (app mark) ────────────────────────────────────────────
EQUALIZER_SVG = """<svg width="12" height="12" viewBox="0 0 11 11" xmlns="http://www.w3.org/2000/svg">
  <rect x="1" y="3" width="1.6" height="6" fill="white"/>
  <rect x="4" y="1" width="1.6" height="8" fill="white"/>
  <rect x="7" y="4" width="1.6" height="5" fill="white"/>
</svg>"""

# ── Icon SVG paths (Lucide-style, stroke="currentColor") ─────────────────────
ICONS: dict[str, str] = {
    "plus":     '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    "list":     '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
    "folder":   '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    "settings": '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
    "check":    '<polyline points="20 6 9 17 4 12"/>',
    "x":        '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "pause":    '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>',
    "play":     '<polygon points="5 3 19 12 5 21 5 3"/>',
    "chev_down":'<polyline points="6 9 12 15 18 9"/>',
    "chev_right":'<polyline points="9 18 15 12 9 6"/>',
    "chev_up":  '<polyline points="18 15 12 9 6 15"/>',
    "scissors": '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="20" y1="4" x2="8.12" y2="15.88"/><line x1="14.47" y1="14.48" x2="20" y2="20"/><line x1="8.12" y1="8.12" x2="12" y2="12"/>',
    "gauge":    '<path d="M12 14l4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
    "music":    '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    "merge":    '<path d="m8 6 4-4 4 4"/><path d="M12 2v10.3a4 4 0 0 1-1.172 2.872L4 22"/><path d="m20 22-5-5"/>',
    "refresh":  '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10"/><path d="M20.49 15a9 9 0 0 1-14.85 3.36L1 14"/>',
    "trash":    '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/>',
    "more":     '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
    "link":     '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "clock":    '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "search":   '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "alert":    '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
    "terminal": '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>',
    "send":     '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    "copy":     '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "shield":   '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "arrow_rt": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    "win_min":  "",  # drawn manually
    "win_max":  "",
    "win_close":"",
}

PIPELINE_STAGES = [
    ("download", "Download", "DL",  "download"),
    ("mp3",      "Mono MP3", "MP3", "music"),
    ("split",    "Split",    "/",   "scissors"),
    ("speed",    "Speed up", "×",   "gauge"),
]


def make_icon_svg(key: str, size: int, color: str = FG_MUTED) -> bytes:
    path = ICONS.get(key, "")
    svg = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.75" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'xmlns="http://www.w3.org/2000/svg">{path}</svg>'
    )
    return svg.encode()


def fmt_dur(sec: int) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def fmt_mb(mb: float | None) -> str:
    if mb is None:
        return "—"
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.1f} MB"


def apply_global_stylesheet(app: QApplication) -> None:
    app.setStyleSheet(f"""
        QWidget {{
            font-family: {FONT_UI};
            font-size: 13px;
            color: {FG};
            border: 0;
        }}
        QScrollBar:vertical {{
            width: 6px; background: transparent; margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {BORDER}; border-radius: 3px; min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {FG_MUTED};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            height: 6px; background: transparent; margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {BORDER}; border-radius: 3px; min-width: 20px;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        QToolTip {{
            background: {FG};
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
        }}
    """)
