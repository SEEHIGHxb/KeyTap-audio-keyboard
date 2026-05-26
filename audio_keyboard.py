#!/usr/bin/env python3
"""
KeyTap - The Chaos Sound Keyboard
---------------------------------
A premium, themed system-wide keyboard utility. 
Plays low-latency sound effects on keypresses using custom user sound packs.

Features:
- Global system-wide key interception using a pynput daemon thread.
- Hardware-accelerated low-latency polyphonic playback using pygame.mixer.
- Dynamic theme selector with persistent memory settings.
- Highly optimized widget-sized dashboard with interactive vector art canvas.

Author: Antigravity Coding Assistant (DeepMind)
"""

import os
import sys
import time
import math
import wave
import struct
import random
import queue
import json
import threading
from datetime import datetime

# ==========================================
# BOOTSTRAP / ENVIRONMENT VERIFICATION
# ==========================================
def verify_imports():
    """Verify that required external dependencies are installed."""
    missing = []
    for pkg in ["customtkinter", "pygame", "pynput"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[BOOT] Missing dependencies: {missing}")
        print("[BOOT] Please ensure these packages are installed before running this application.")
        print("[BOOT] Run: pip install customtkinter pygame pynput")

verify_imports()

try:
    import customtkinter as ctk
    import pygame
    from pynput import keyboard
except ImportError:
    pass

# ==========================================
# CONSTANTS & STYLING TOKENS
# ==========================================
WINDOW_TITLE = "KeyTap"
WINDOW_SIZE = "650x450"
COLOR_BG = "#F8F9FA"          # Default starting theme light BG
COLOR_CARD = "#FFFFFF"        # Default card BG
COLOR_ACCENT = "#1A73E8"      # Default Accent
COLOR_ACCENT_ALT = "#5F6368"
COLOR_TEXT_PRIMARY = "#202124"
COLOR_TEXT_MUTED = "#5F6368"
COLOR_LED_ACTIVE = "#1A73E8"
COLOR_LED_MUTED = "#757575"

# ==========================================
# MAIN APPLICATION ENGINE & GUI
# ==========================================
class AudioKeyboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Properties
        self.running = True
        self.sound_enabled = True
        self.keystroke_count = 0
        self.current_volume = 0.8
        self.active_pack_name = "None"
        self.loaded_sounds = {}
        self.sound_packs_root = ""
        self.keyboard_listener = None
        self.start_time = time.time()
        self.ui_update_queue = queue.Queue()

        # Canvas Animation Variables
        self.wave_amplitude = 5.0
        self.wave_amplitude_target = 5.0
        self.wave_phase = 0.0
        self.active_ripples = []
        self.particles = []

        # Initialize Pygame audio mixer
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(32)  # High polyphony overlap
            self.post_ui_log("AUDIO", "Pygame mixer initialized (44.1kHz, stereo, 512 buffer, 32 channels).")
        except Exception as e:
            self.post_ui_log("AUDIO", f"Failed to initialize pygame.mixer: {e}", is_error=True)
        
        # 6 Custom visual themes
        self.themes = {
            "Zoo Theme": {
                "bg": "#141C12", "card": "#212B1E", "accent": "#82C982", "accent_alt": "#CBB393",
                "text": "#ECF9EB", "muted": "#96AF93", "led_active": "#82C982", "led_muted": "#8B6B5C", 
                "mode": "dark"
            },
            "Love Theme": {
                "bg": "#23141F", "card": "#331E2E", "accent": "#FF6BA3", "accent_alt": "#FFB8D2",
                "text": "#FFEAF2", "muted": "#C293AC", "led_active": "#FF6BA3", "led_muted": "#B55A8A", 
                "mode": "dark"
            },
            "Lo-Fi Cafe Theme": {
                "bg": "#1C1713", "card": "#2C231E", "accent": "#D19B68", "accent_alt": "#EAD7A1",
                "text": "#FAEDCE", "muted": "#AFB896", "led_active": "#D19B68", "led_muted": "#8A5935", 
                "mode": "dark"
            },
            "8-Bit Theme": {
                "bg": "#030308", "card": "#0D0D1A", "accent": "#2BFF2B", "accent_alt": "#00FFFF",
                "text": "#FFFFFF", "muted": "#7A7A9E", "led_active": "#2BFF2B", "led_muted": "#E01844", 
                "mode": "dark"
            },
            "Beach Theme": {
                "bg": "#DDF5F2", "card": "#FFFFFF", "accent": "#008573", "accent_alt": "#EFA200",
                "text": "#00473E", "muted": "#007565", "led_active": "#008573", "led_muted": "#E26969", 
                "mode": "light"
            },
            "Plain Theme": {
                "bg": "#F8F9FA", "card": "#FFFFFF", "accent": "#1A73E8", "accent_alt": "#5F6368",
                "text": "#202124", "muted": "#5F6368", "led_active": "#1A73E8", "led_muted": "#757575", 
                "mode": "light"
            }
        }

        # Initialize folders & graphical panels
        self.setup_sound_directories()
        self.build_ui()
        self.process_ui_queue()

        # Handle persistent visual theme loader
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config.json")
        loaded_theme = "Plain Theme"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as cf:
                    conf = json.load(cf)
                    if "theme" in conf and conf["theme"] in self.themes:
                        loaded_theme = conf["theme"]
            except Exception:
                pass
        
        self.combobox_themes.set(loaded_theme)
        self.apply_theme(loaded_theme)

        # Startup audio loading, system hooks & animations
        self.load_default_pack_at_start()
        self.start_keyboard_hook()
        self.pulse_status_led()
        self.animate_canvas()

        # Clean shutdown protocol
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    # ==========================================
    # FILE & DIRECTORY CONTROLLERS
    # ==========================================
    def setup_sound_directories(self):
        """Locates sound packs root directory on host next to script or exe."""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self.sound_packs_root = os.path.join(base_dir, "sound_packs")
        os.makedirs(self.sound_packs_root, exist_ok=True)

    def refresh_sound_packs(self):
        """Scans the sound packs folder and updates the combo box list."""
        packs = []
        if os.path.exists(self.sound_packs_root):
            try:
                for entry in os.listdir(self.sound_packs_root):
                    full_path = os.path.join(self.sound_packs_root, entry)
                    if os.path.isdir(full_path):
                        packs.append(entry)
            except Exception as e:
                self.post_ui_log("SYSTEM", f"Failed to list packages: {e}", is_error=True)
        
        if not packs:
            packs = ["None"]
        
        self.combobox_packs.configure(values=packs)
        return packs

    def load_default_pack_at_start(self):
        """Auto loads first pack during constructor."""
        packs = self.refresh_sound_packs()
        if packs and packs[0] != "None":
            default_pack = packs[0]
            for p in ["Typewriter", "Cat", "Cooking"]:
                if p in packs:
                    default_pack = p
                    break
            self.combobox_packs.set(default_pack)
            self.load_sound_pack(default_pack)
        else:
            self.active_pack_name = "None"
            self.lbl_stat_pack.configure(text="None")

    def load_sound_pack(self, pack_name):
        """Loads a sound pack into memory, initializing pygame.mixer.Sound objects."""
        pygame.mixer.stop()
        self.loaded_sounds = {}
        self.active_pack_name = pack_name
        self.lbl_stat_pack.configure(text=pack_name)
        
        if pack_name == "None":
            self.post_ui_log("SYSTEM", "Unloaded sound packs.")
            return

        pack_dir = os.path.join(self.sound_packs_root, pack_name)
        if not os.path.exists(pack_dir):
            self.post_ui_log("SYSTEM", f"Pack directory {pack_dir} not found.", is_error=True)
            return

        try:
            files = sorted([f for f in os.listdir(pack_dir) if f.lower().endswith('.wav')])
            if not files:
                self.post_ui_log("SYSTEM", f"No .wav files in pack '{pack_name}'", is_error=True)
                return

            loaded_count = 0
            for f in files:
                f_path = os.path.join(pack_dir, f)
                try:
                    sound_obj = pygame.mixer.Sound(f_path)
                    sound_obj.set_volume(self.current_volume)
                    self.loaded_sounds[f.lower()] = sound_obj
                    loaded_count += 1
                except Exception as ex:
                    self.post_ui_log("SYSTEM", f"Failed to load sound file {f}: {ex}", is_error=True)

            self.post_ui_log("SYSTEM", f"Loaded {loaded_count} sound(s) from pack '{pack_name}' in memory.")
        except Exception as e:
            self.post_ui_log("SYSTEM", f"Failed to load pack '{pack_name}': {e}", is_error=True)

    # ==========================================
    # UI COMPONENT HANDLERS
    # ==========================================
    def on_pack_selected(self, pack_name):
        """Dropdown handler for sound pack changes."""
        self.load_sound_pack(pack_name)

    def on_click_refresh_btn(self):
        """User button event for directory scan."""
        self.setup_sound_directories()
        packs = self.refresh_sound_packs()
        self.post_ui_log("SYSTEM", "Rescanned 'sound_packs/' folder successfully.")
        if self.active_pack_name not in packs:
            self.load_default_pack_at_start()

    def on_toggle_switch(self):
        """Handles ON/OFF Master Toggle switch."""
        self.sound_enabled = self.switch_toggle.get() == 1
        t = self.themes.get(self.current_theme, self.themes["Plain Theme"])
        
        if self.sound_enabled:
            self.status_pill.configure(fg_color=t["led_active"])
            self.status_text.configure(text_color=t["led_active"], text="ACTIVE")
            self.post_ui_log("SYSTEM", "Master sound feedback ENABLED.")
        else:
            self.status_pill.configure(fg_color=t["led_muted"])
            self.status_text.configure(text_color=t["led_muted"], text="MUTED")
            self.post_ui_log("SYSTEM", "Master sound feedback MUTED.")

    def on_volume_adjusted(self, value):
        """Handles volume slider movements."""
        self.current_volume = float(value)
        self.lbl_vol_percentage.configure(text=f"{int(self.current_volume * 100)}%")
        
        for sound in self.loaded_sounds.values():
            try:
                sound.set_volume(self.current_volume)
            except Exception:
                pass

    # ==========================================
    # KEYBOARD LISTENER ENGINE
    # ==========================================
    def start_keyboard_hook(self):
        """Launches the global non-blocking keyboard hook."""
        try:
            self.keyboard_listener = keyboard.Listener(
                on_press=self.on_key_press
            )
            self.keyboard_listener.daemon = True
            self.keyboard_listener.start()
            self.post_ui_log("SYSTEM", "Global system-wide key listener launched successfully.")
        except Exception as e:
            self.post_ui_log("SYSTEM", f"Failed to start key listener: {e}", is_error=True)

    def on_key_press(self, key):
        """Processes keystroke hooks and triggers polyphonic playback threads."""
        if not self.running or not self.sound_enabled:
            return

        self.keystroke_count += 1
        self.ui_update_queue.put(lambda: self.lbl_stat_keys.configure(text=str(self.keystroke_count)))

        # Trigger dynamic visual pulse ripples thread-safely on the vector art canvas
        self.wave_amplitude_target = 38.0
        w = self.art_canvas.winfo_width()
        h = self.art_canvas.winfo_height()
        if w <= 1 or h <= 1:
            w, h = 610, 140
        self.ui_update_queue.put(lambda: self.active_ripples.append({
            "x": random.randint(50, w - 50),
            "y": random.randint(25, h - 25),
            "radius": 1.0,
            "opacity": 1.0
        }))

        if not self.loaded_sounds:
            return

        try:
            if hasattr(key, 'char') and key.char is not None:
                key_name = key.char
            else:
                k_str = str(key)
                if k_str.startswith("Key."):
                    key_name = k_str.replace("Key.", "").capitalize()
                else:
                    key_name = k_str
        except Exception:
            key_name = "Key"

        # Trigger overlapping playback on a separate thread to maintain absolute latency freedom
        threading.Thread(target=self.play_sound, args=(key_name,), daemon=True).start()

    def play_sound(self, key_name):
        """Matches a keypress to a loaded sound file and plays it."""
        if not self.loaded_sounds:
            return

        sound_keys = list(self.loaded_sounds.keys())
        sound_to_play = None
        target_sub = key_name.lower()
        
        # Context-Aware Acoustic Mapping:
        matched_keys = [k for k in sound_keys if target_sub in k]
        if matched_keys:
            sound_to_play = random.choice(matched_keys)
        else:
            if key_name == "Space":
                space_candidates = [k for k in sound_keys if "space" in k or "thock" in k]
                if space_candidates:
                    sound_to_play = random.choice(space_candidates)
            elif key_name == "Enter":
                enter_candidates = [k for k in sound_keys if "enter" in k or "bell" in k or "return" in k]
                if enter_candidates:
                    sound_to_play = random.choice(enter_candidates)
            elif key_name == "Backspace":
                back_candidates = [k for k in sound_keys if "backspace" in k or "delete" in k or "hit" in k or "remove" in k]
                if back_candidates:
                    sound_to_play = random.choice(back_candidates)

        if not sound_to_play:
            general_clips = [k for k in sound_keys if "space" not in k and "enter" not in k and "backspace" not in k]
            if not general_clips:
                general_clips = sound_keys
            sound_to_play = general_clips[self.keystroke_count % len(general_clips)]

        if sound_to_play:
            try:
                sound_obj = self.loaded_sounds[sound_to_play]
                sound_obj.play()
                self.log_keypress(key_name, sound_to_play)
            except Exception as e:
                self.post_ui_log("PLAY", f"Failed to play sound: {e}", is_error=True)

    # ==========================================
    # UI CREATION & LAYOUT
    # ==========================================
    def build_ui(self):
        """Creates the full responsive grid layout."""
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.resizable(False, False)

        # Configure window icon
        try:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_dir, "keytap_logo.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=0) # Stats
        self.grid_rowconfigure(2, weight=0) # Controls
        self.grid_rowconfigure(3, weight=1) # Theme Art Canvas (centered)

        # ------------------------------------------
        # 1. HEADER PANEL
        # ------------------------------------------
        self.header_frame = ctk.CTkFrame(self, height=85, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="nsew")
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=0)

        # Title Block
        self.title_block = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.title_block.grid(row=0, column=0, sticky="w")
        
        self.lbl_title = ctk.CTkLabel(
            self.title_block, 
            text="KEYTAP", 
            font=("Segoe UI", 24, "bold"), 
            text_color=COLOR_ACCENT
        )
        self.lbl_title.pack(anchor="w", pady=(0, 2))
        
        self.lbl_subtitle = ctk.CTkLabel(
            self.title_block, 
            text="The Chaos Sound Keyboard", 
            font=("Segoe UI", 12, "italic"), 
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_subtitle.pack(anchor="w")

        # Balanced Right Header Container (aligned side-by-side)
        self.right_header = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.right_header.grid(row=0, column=1, sticky="e", pady=8)

        # Master Toggle Switch
        self.switch_toggle = ctk.CTkSwitch(
            self.right_header, 
            text="ON/OFF", 
            command=self.on_toggle_switch,
            font=("Segoe UI", 11, "bold"),
            progress_color=COLOR_ACCENT
        )
        self.switch_toggle.select()
        self.switch_toggle.pack(side="left", padx=(0, 15))

        # Status Indicator Box
        self.status_box = ctk.CTkFrame(self.right_header, fg_color=COLOR_CARD, corner_radius=20, height=36)
        self.status_box.pack(side="left")
        self.status_box.grid_rowconfigure(0, weight=1)
        
        self.status_pill = ctk.CTkFrame(
            self.status_box, 
            width=10, 
            height=10, 
            corner_radius=5, 
            fg_color=COLOR_LED_ACTIVE
        )
        self.status_pill.grid(row=0, column=0, padx=(12, 6), pady=13)
        
        self.status_text = ctk.CTkLabel(
            self.status_box, 
            text="ACTIVE", 
            font=("Segoe UI", 11, "bold"), 
            text_color=COLOR_LED_ACTIVE
        )
        self.status_text.grid(row=0, column=1, padx=(0, 12), pady=6)

        # ------------------------------------------
        # 2. QUICK STATS PANEL (Row 1)
        # ------------------------------------------
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.stats_frame.grid_columnconfigure((0, 1), weight=1)

        # Card 1: Key Count
        self.card1 = ctk.CTkFrame(self.stats_frame, fg_color=COLOR_CARD, corner_radius=12, border_color="#2A3542", border_width=1)
        self.card1.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        self.lbl_stat1_title = ctk.CTkLabel(self.card1, text="KEYSTROKES", font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT_MUTED)
        self.lbl_stat1_title.pack(pady=(12, 0))
        self.lbl_stat_keys = ctk.CTkLabel(self.card1, text="0", font=("Segoe UI", 26, "bold"), text_color=COLOR_ACCENT)
        self.lbl_stat_keys.pack(pady=(2, 12))

        # Card 2: Active Sound Name
        self.card2 = ctk.CTkFrame(self.stats_frame, fg_color=COLOR_CARD, corner_radius=12, border_color="#2A3542", border_width=1)
        self.card2.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        self.lbl_stat2_title = ctk.CTkLabel(self.card2, text="ACTIVE SOUND", font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT_MUTED)
        self.lbl_stat2_title.pack(pady=(12, 0))
        self.lbl_stat_pack = ctk.CTkLabel(self.card2, text="None", font=("Segoe UI", 20, "bold"), text_color="#E0E0E0")
        self.lbl_stat_pack.pack(pady=(8, 12))

        # ------------------------------------------
        # 3. CONTROL PANEL (Row 2 - Three Columns)
        # ------------------------------------------
        self.controls_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=14, border_color="#2A3542", border_width=1)
        self.controls_frame.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")
        
        self.controls_frame.grid_columnconfigure(0, weight=1)
        self.controls_frame.grid_columnconfigure(1, weight=1)
        self.controls_frame.grid_columnconfigure(2, weight=1)

        # COLUMN 0: SELECT SOUND PACK
        pack_container = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        pack_container.grid(row=0, column=0, padx=10, pady=15, sticky="nsew")
        
        self.lbl_pack_title = ctk.CTkLabel(pack_container, text="SELECT SOUND PACK", font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT_MUTED)
        self.lbl_pack_title.pack(anchor="w", pady=(0, 6))

        pack_row = ctk.CTkFrame(pack_container, fg_color="transparent")
        pack_row.pack(fill="x", anchor="w")

        self.combobox_packs = ctk.CTkComboBox(
            pack_row, 
            width=110, 
            command=self.on_pack_selected,
            values=["None"]
        )
        self.combobox_packs.pack(side="left", padx=(0, 4))

        self.btn_refresh = ctk.CTkButton(
            pack_row, 
            text="Scan Sound", 
            width=80, 
            font=("Segoe UI", 10, "bold"),
            command=self.on_click_refresh_btn
        )
        self.btn_refresh.pack(side="left")

        # COLUMN 1: VOLUME CONTROL
        volume_container = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        volume_container.grid(row=0, column=1, padx=10, pady=15, sticky="nsew")

        self.lbl_volume_title = ctk.CTkLabel(volume_container, text="VOLUME", font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT_MUTED)
        self.lbl_volume_title.pack(anchor="w", pady=(0, 6))

        vol_row = ctk.CTkFrame(volume_container, fg_color="transparent")
        vol_row.pack(fill="x", anchor="w")

        self.slider_volume = ctk.CTkSlider(
            vol_row, 
            from_=0.0, 
            to=1.0, 
            width=115,
            command=self.on_volume_adjusted,
            progress_color=COLOR_ACCENT
        )
        self.slider_volume.set(self.current_volume)
        self.slider_volume.pack(side="left", padx=(0, 4))

        self.lbl_vol_percentage = ctk.CTkLabel(
            vol_row, 
            text="80%", 
            font=("Segoe UI", 11, "bold"), 
            text_color=COLOR_ACCENT,
            width=30
        )
        self.lbl_vol_percentage.pack(side="left")

        # COLUMN 2: CHANGE THEME
        theme_container = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        theme_container.grid(row=0, column=2, padx=10, pady=15, sticky="nsew")

        self.lbl_theme_title = ctk.CTkLabel(theme_container, text="CHANGE THEME", font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT_MUTED)
        self.lbl_theme_title.pack(anchor="w", pady=(0, 6))

        theme_row = ctk.CTkFrame(theme_container, fg_color="transparent")
        theme_row.pack(fill="x", anchor="w")

        theme_list = [
            "Zoo Theme", 
            "Love Theme", 
            "Lo-Fi Cafe Theme", 
            "8-Bit Theme", 
            "Beach Theme", 
            "Plain Theme"
        ]
        self.combobox_themes = ctk.CTkComboBox(
            theme_row, 
            width=180, 
            command=self.apply_theme,
            values=theme_list
        )
        self.combobox_themes.set("Plain Theme")
        self.combobox_themes.pack(side="left")

        # ------------------------------------------
        # 4. INTERACTIVE VECTOR CANVAS (Upgraded!)
        # ------------------------------------------
        self.art_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.art_frame.grid(row=3, column=0, padx=20, pady=(5, 10), sticky="nsew")
        self.art_frame.grid_columnconfigure(0, weight=1)
        self.art_frame.grid_rowconfigure(0, weight=1)

        self.art_canvas = ctk.CTkCanvas(
            self.art_frame, 
            bg="#0B0C10", 
            highlightthickness=1, 
            highlightbackground="#2A3542"
        )
        self.art_canvas.grid(row=0, column=0, sticky="nsew")

    # ==========================================
    # VISUALS & VECTOR ANIMATIONS
    # ==========================================
    def apply_theme(self, theme_name):
        """Applies one of the 6 dynamic visual styles and saves to config.json."""
        self.current_theme = theme_name
        t = self.themes.get(theme_name, self.themes["Plain Theme"])
        
        # Configure overall window theme mode and background
        ctk.set_appearance_mode(t["mode"])
        self.configure(fg_color=t["bg"])
        
        # Configure frames and canvas backgrounds
        self.status_box.configure(fg_color=t["card"])
        self.controls_frame.configure(fg_color=t["card"], border_color=t["accent"])
        self.card1.configure(fg_color=t["card"], border_color=t["accent"])
        self.card2.configure(fg_color=t["card"], border_color=t["accent"])
        self.art_canvas.configure(bg=t["bg"], highlightbackground=t["accent"])
        self.art_frame.configure(fg_color="transparent")
        
        # Configure text elements
        self.lbl_title.configure(text_color=t["accent"])
        self.lbl_subtitle.configure(text_color=t["muted"])
        
        self.lbl_stat1_title.configure(text_color=t["muted"])
        self.lbl_stat_keys.configure(text_color=t["accent"])
        
        self.lbl_stat2_title.configure(text_color=t["muted"])
        self.lbl_stat_pack.configure(text_color=t["text"])
        
        self.lbl_pack_title.configure(text_color=t["muted"])
        self.lbl_theme_title.configure(text_color=t["muted"])
        self.lbl_volume_title.configure(text_color=t["muted"])
        
        # Configure sliders, buttons, and switches
        self.slider_volume.configure(progress_color=t["accent"])
        self.switch_toggle.configure(progress_color=t["accent"])
        
        self.combobox_packs.configure(button_color=t["accent"], border_color=t["accent"])
        self.combobox_themes.configure(button_color=t["accent"], border_color=t["accent"])
        
        # Button styling according to mode
        btn_text_color = t["bg"] if t["mode"] == "light" else t["text"]
        self.btn_refresh.configure(fg_color=t["accent"], hover_color=t["accent_alt"], text_color=btn_text_color)
        
        # Force redraw status LED color immediately
        if self.sound_enabled:
            self.status_pill.configure(fg_color=t["led_active"])
            self.status_text.configure(text_color=t["led_active"])
        else:
            self.status_pill.configure(fg_color=t["led_muted"])
            self.status_text.configure(text_color=t["led_muted"])

        # Reset thematic animated particles in canvas
        self.particles = []
        if theme_name == "Zoo Theme":
            # Initial leaf nodes
            for _ in range(6):
                self.particles.append({
                    "x": random.randint(20, 590),
                    "y": random.randint(-15, 120),
                    "speed": random.uniform(0.8, 1.8),
                    "offset": random.uniform(0, 3)
                })
        elif theme_name == "Love Theme":
            # Floating retro pixel heart nodes
            for _ in range(8):
                self.particles.append({
                    "x": random.randint(20, 590),
                    "y": random.randint(10, 130),
                    "speed": random.uniform(0.5, 1.3),
                    "size": random.randint(8, 13)
                })
        elif theme_name == "8-Bit Theme":
            # Stepping square stars
            for _ in range(12):
                self.particles.append({
                    "x": random.randint(10, 600),
                    "y": random.randint(10, 130),
                    "speed": random.uniform(1.2, 3.2)
                })
            
        self.post_ui_log("SYSTEM", f"Applied color profile: {theme_name}")

        # Save persistent theme choice
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as cf:
                json.dump({"theme": theme_name}, cf)
        except Exception as e:
            self.post_ui_log("SYSTEM", f"Failed to save theme config: {e}", is_error=True)

    def pulse_status_led(self):
        """Micro-animation pulsing effect for active glowing status pill."""
        if not self.running:
            return
            
        try:
            t = self.themes[self.current_theme]
            curr = self.status_pill.cget("fg_color")
            if self.sound_enabled:
                nxt = t["accent_alt"] if curr == t["led_active"] else t["led_active"]
            else:
                nxt = t["muted"] if curr == t["led_muted"] else t["led_muted"]
            self.status_pill.configure(fg_color=nxt)
        except Exception:
            pass
            
        self.after(900, self.pulse_status_led)

    def animate_canvas(self):
        """Dynamic vector drawing renderer loop (~30 FPS)."""
        if not self.running:
            return

        try:
            canvas = self.art_canvas
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w <= 1 or h <= 1:
                w, h = 610, 140

            # Delete dynamic vector items from last frame
            canvas.delete("anim")

            t = self.themes.get(self.current_theme, self.themes["Plain Theme"])
            accent = t["accent"]
            accent_alt = t["accent_alt"]
            
            # Oscillating phase offsets & wave amplitude decay mechanics
            self.wave_amplitude += (self.wave_amplitude_target - self.wave_amplitude) * 0.15
            self.wave_amplitude_target += (6.0 - self.wave_amplitude_target) * 0.08  # Decays back to 6px ambient
            self.wave_phase += 0.09

            if self.current_theme == "Zoo Theme":
                # Subtle jungle grid
                for x in range(0, w, 50):
                    canvas.create_line(x, 0, x, h, fill="#192217", width=1, tags="anim")
                # Rolling double green hills vector curves
                pts1, pts2 = [], []
                for x in range(0, w + 10, 20):
                    y1 = h - 35 + 14 * math.sin(0.008 * x + self.wave_phase)
                    y2 = h - 20 + 9 * math.cos(0.012 * x - self.wave_phase)
                    pts1.extend([x, y1])
                    pts2.extend([x, y2])
                pts1.extend([w, h, 0, h])
                pts2.extend([w, h, 0, h])
                canvas.create_polygon(pts1, fill="#1C2819", tags="anim")
                canvas.create_polygon(pts2, fill="#263A23", tags="anim")
                # Falling leaves animation
                for leaf in self.particles:
                    leaf["y"] += leaf["speed"]
                    leaf["x"] += math.sin(self.wave_phase + leaf["offset"]) * 0.4
                    if leaf["y"] > h + 10:
                        leaf["y"] = -15
                        leaf["x"] = random.randint(10, w - 10)
                    canvas.create_text(leaf["x"], leaf["y"], text="🍃", font=("Segoe UI", 11), tags="anim")

            elif self.current_theme == "Love Theme":
                # Soft vertical grid
                for y in range(0, h, 25):
                    canvas.create_line(0, y, w, y, fill="#2C1A27", width=1, tags="anim")
                # Floating romantic heart nodes
                for heart in self.particles:
                    heart["y"] -= heart["speed"]
                    if heart["y"] < -15:
                        heart["y"] = h + 10
                        heart["x"] = random.randint(10, w - 10)
                    canvas.create_text(heart["x"], heart["y"], text="❤️", font=("Segoe UI", heart["size"]), tags="anim")
                # Symmetric glowing love-pulse oscilloscope
                pts = []
                for x in range(0, w + 5, 5):
                    offset = self.wave_amplitude * math.sin(0.02 * x + self.wave_phase) * math.cos(0.006 * x)
                    pts.append((x, h/2 + offset))
                if len(pts) > 1:
                    canvas.create_line(pts, fill=accent, width=3, smooth=True, tags="anim")

            elif self.current_theme == "Lo-Fi Cafe Theme":
                # Aesthetic warm shadow slits
                for i in range(-50, w + h, 40):
                    canvas.create_line(i, 0, i - 40, h, fill="#241B17", width=2, tags="anim")
                # Rising vertical warm steam vectors
                for offset_x in [-75, 0, 75]:
                    pts = []
                    center_x = w / 2 + offset_x
                    for y in range(12, h - 20, 6):
                        wave_x = center_x + 9 * math.sin(0.07 * y - self.wave_phase * 1.8) * (1.1 - y/h)
                        pts.append((wave_x, y))
                    if len(pts) > 1:
                        canvas.create_line(pts, fill=accent, width=2.5, smooth=True, tags="anim")
                # Central stylized coffee/tea cup vector outline
                cx, cy = w/2, h - 20
                canvas.create_arc(cx - 30, cy - 15, cx + 30, cy + 15, start=180, extent=180, outline=accent_alt, width=3, tags="anim")
                canvas.create_line(cx - 30, cy, cx - 30, cy - 25, fill=accent_alt, width=3, tags="anim")
                canvas.create_line(cx + 30, cy, cx + 30, cy - 25, fill=accent_alt, width=3, tags="anim")
                canvas.create_line(cx - 30, cy - 25, cx + 30, cy - 25, fill=accent_alt, width=3, tags="anim")
                canvas.create_arc(cx + 25, cy - 23, cx + 43, cy - 5, start=270, extent=180, outline=accent_alt, width=3, tags="anim")

            elif self.current_theme == "8-Bit Theme":
                # Digital matrix grid
                for x in range(0, w, 35):
                    canvas.create_line(x, 0, x, h, fill="#080816", width=1, tags="anim")
                for y in range(0, h, 20):
                    canvas.create_line(0, y, w, y, fill="#080816", width=1, tags="anim")
                # Step-quantized retro pixel wave curve
                pts = []
                step_w = 16
                for x in range(0, w + step_w, step_w):
                    angle = 0.02 * x + self.wave_phase
                    sq_sine = 1.0 if math.sin(angle) >= 0 else -1.0
                    y = h/2 + sq_sine * self.wave_amplitude * 0.75
                    pts.extend([x, y, x + step_w, y])
                if len(pts) > 1:
                    canvas.create_line(pts, fill=accent, width=2.5, tags="anim")
                # Drifting star-field pixels
                for star in self.particles:
                    star["x"] += star["speed"]
                    if star["x"] > w:
                        star["x"] = -5
                        star["y"] = random.randint(10, h - 10)
                    canvas.create_rectangle(star["x"], star["y"], star["x"]+4, star["y"]+4, fill=accent_alt, outline="", tags="anim")

            elif self.current_theme == "Beach Theme":
                # Beautiful ocean crest vectors
                pts1, pts2 = [], []
                for x in range(0, w + 10, 15):
                    y1 = h - 45 + 13 * math.sin(0.015 * x + self.wave_phase * 1.3)
                    y2 = h - 25 + 9 * math.cos(0.01 * x - self.wave_phase * 1.1)
                    pts1.extend([x, y1])
                    pts2.extend([x, y2])
                pts1.extend([w, h, 0, h])
                pts2.extend([w, h, 0, h])
                canvas.create_polygon(pts1, fill="#AFE3DE", tags="anim")
                canvas.create_polygon(pts2, fill="#3FAB9B", tags="anim")
                # Sunny beach orb
                canvas.create_oval(w - 75, 12, w - 40, 47, fill=accent_alt, outline="", tags="anim")

            else:
                # Plain Theme: Double anti-aliased clean vector oscilloscope line
                canvas.create_line(0, h/2, w, h/2, fill="#E6E8EA", width=1, tags="anim")
                pts = []
                for x in range(0, w + 5, 5):
                    y = h/2 + self.wave_amplitude * math.sin(0.025 * x + self.wave_phase)
                    pts.append((x, y))
                if len(pts) > 1:
                    canvas.create_line(pts, fill=accent, width=2.5, smooth=True, tags="anim")

            # Update concentric keypress ripple waves
            still_active = []
            for rip in self.active_ripples:
                rip["radius"] += 5.0
                rip["opacity"] -= 0.05
                if rip["opacity"] > 0:
                    still_active.append(rip)
                    lw = max(1, int(rip["opacity"] * 5))
                    canvas.create_oval(
                        rip["x"] - rip["radius"], rip["y"] - rip["radius"],
                        rip["x"] + rip["radius"], rip["y"] + rip["radius"],
                        outline=accent, width=lw, tags="anim"
                    )
            self.active_ripples = still_active

        except Exception:
            pass

        self.after(30, self.animate_canvas)

    def process_ui_queue(self):
        """Processes pending thread-safe callbacks scheduled by background listener thread."""
        if not self.running:
            return
            
        try:
            while True:
                task = self.ui_update_queue.get_nowait()
                task()
        except queue.Empty:
            pass
            
        self.after(40, self.process_ui_queue)

    # ==========================================
    # LOGGER UTILITIES
    # ==========================================
    def post_ui_log(self, tag, message, is_error=False):
        """Safely prints colored time-stamped text outputs to standard output."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{tag.upper()}] {message}")

    def log_keypress(self, key_name, sound_file):
        """GUI logging helper for played keys."""
        self.post_ui_log("KEY", f"'{key_name}' pressed -> triggered {sound_file}")

    def log_error_msg(self, error_text):
        """GUI logging helper for errors."""
        self.post_ui_log("ERROR", error_text, is_error=True)

    # ==========================================
    # EXIT HANDLER
    # ==========================================
    def on_exit(self):
        """Ensures complete resource liberation and thread termination on close."""
        print("[SYSTEM] Shutting down Audio Keyboard App...")
        self.running = False
        
        # Stop background keyboard listener thread
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
            except Exception:
                pass
                
        # Close pygame audio devices
        try:
            pygame.mixer.stop()
            pygame.mixer.quit()
        except Exception:
            pass
            
        # Standard Tkinter destruction
        self.destroy()
        sys.exit(0)


if __name__ == "__main__":
    # Launch main window loops
    try:
        app = AudioKeyboardApp()
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)
