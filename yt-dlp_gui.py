#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, json, shutil, threading, time, re,subprocess
from pathlib import Path
from typing import List, Optional
import random
import textwrap
import tkinter as tk
from tkinter import CENTER, Toplevel, Label, Button
from tkinter import ttk, filedialog, messagebox
import tkinter.simpledialog as simpledialog
import tkinter.messagebox as messagebox
from PIL import Image, ImageTk, ImageSequence   # ✅ for resizing icons
from urllib.parse import urlparse, parse_qs
import pygame
import yt_dlp as ytdlp
from io import BytesIO
import queue
from queue import Queue, Empty

# -----
# NEW: THEME DEFINITIONS
# Central place to control the look of your application.
# -----
dark_theme = {
    "bg": "#2E2E2E",
    "fg": "#FFFFFF",
    "button_bg": "#3C3C3C",
    "button_fg": "#FFFFFF",
    "button_active_bg": "#505050",
    "accent": "#FF8C00",  # Orange accent for progress bar and sliders
    "toolbar_bg": "#1C1C1C",
    "menu_bg": "#2E2E2E",
    "menu_fg": "#FFFFFF",
    "menu_active_bg": "#505050",
    "volume_slider_accent":"#E4821F",
}

light_theme = {
    "bg": "#F0F0F0",
    "fg": "#000000",
    "button_bg": "#E1E1E1",
    "button_fg": "#000000",
    "button_active_bg": "#CACACA",
    "accent": "#0078D7",  # Blue accent for progress bar and sliders
    "toolbar_bg": "#FFFFFF",
    "menu_bg": "#FFFFFF",
    "menu_fg": "#000000",
    "menu_active_bg": "#E1E1E1",
    "volume_slider_accent":"#acacac",
    "Progress_bar_green":"#57d221",
}

# Use the static SVGs for the default button icons.
STATIC_PNG_PATHS = [
    "YouTube MP3 DL 1AV 4A.png",
    "YouTube MP4 DL 1AV 4A.png",
    "YouTube MP3 PL DL 1AV 4A.png",
    "YouTube MP4 PL DL 1AV 4A.png",
]

# Use pre-converted animated GIFs for the downloading state.
ANIMATED_GIF_PATHS = [
    "MP3_animated.gif",
    "MP4_animated.gif",
    "MP3_PL_animated.gif",
    "MP4_PL_animated.gif",
]

UI_ICON_PATHS = [
    "volume sldr Orange.png",                     # tiny knob image (you can use a PNG)
    "volume overlay Play Orange.png",
    "volume overlay Play Default.png",
    "volume overlay Pause Orange.png",
    "volume overlay Pause Default.png",
    "YouTube2Media1AV 2A.ico",
]

# Global playlist trackingFQI
APP_NAME    = "YouTube‑Downloader"
APP_VERSION = "v0.15.4"        # ← change this when you release a new build
active_button: Optional[tk.Button] = None # Will hold the button being animated
is_animating = False
gif_frames: dict[int, list[ImageTk.PhotoImage]] = {}
manual_playlist_index = 1
current_index = 1
current_playlist_count = 1
custom_toolbar = None
custom_toolbar: Optional[tk.Frame] = None
last_download_path: Optional[str] = None
current_is_video = False
current_base_dir = ""
is_audio_enabled = False
button_images_refs: list[ImageTk.PhotoImage] = [] 
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
loaded_loop_track_path: Optional[str] = None
ICON_FOLDER = "yt download err Icons"
loaded_player_volume: float = 0.5 # Default to 50%
_resize_save_job = None # For saving window geometry

# -------------
# Helpers – path handling for a bundled executable
# -------------
def _resource_path(relative_path: str) -> str:
    """
    Get absolute path to a resource that might be inside the PyInstaller bundle.
    """
    try:
        meipass = sys._MEIPASS  # noqa: F841 – used later in the conditional
        if isinstance(meipass, (bytes, bytearray)):
            base_path = Path(meipass.decode('utf-8'))   # <-- decode bytes to str
        else:
            base_path = Path(meipass)                   # already a str
    except AttributeError:  # not frozen → run from source code
        base_path = Path(__file__).parent
    full_path = base_path / relative_path
    return str(full_path)

music_file = _resource_path("playmusic/No Copyright Come With Me (Creative Commons) deep house.mp3")
print(f"--- [DEBUG] Attempting to use music file at this exact path: ---")
print(f"'{music_file}'")
print(f"-----------------------------------------------------------------")

ALERT_SOUND_FILE: str | None = _resource_path("sounds/Coin Win.mp3")
music_muted = False
MUSIC_DIR = os.path.expandvars(r"%USERPROFILE%\Music\0A. Download (C) MP3 Stream\YouTube")
VIDEO_DIR = os.path.expandvars(r"%USERPROFILE%\Videos\0A. Download (C) MP4 Stream\YouTube")
ico_filename = UI_ICON_PATHS[-1]
icon_path = _resource_path(os.path.join(ICON_FOLDER, ico_filename))

def load_config():
    global MUSIC_DIR, VIDEO_DIR, ALERT_SOUND_FILE, max_resolution, loaded_loop_track_path, loaded_player_volume
    if not os.path.exists(CONFIG_FILE):
        return
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f: 
            data = json.load(f)
            MUSIC_DIR = data.get("music_dir", MUSIC_DIR)
            VIDEO_DIR = data.get("video_dir", VIDEO_DIR)
            # If alert_sound_file exists in config and file exists, use it.
            alert_file = data.get("alert_sound_file")
            if alert_file and os.path.isfile(alert_file):
                ALERT_SOUND_FILE = alert_file
            else:
                # fallback to default bundled sound
                ALERT_SOUND_FILE = _resource_path("sounds/Coin Win.mp3")
                
            # --- Load the saved volume level
            saved_volume = data.get("player_volume", loaded_player_volume)
            # Clamp the value between 0.0 and 1.0 to prevent errors
            loaded_player_volume = max(0.0, min(1.0, float(saved_volume)))
            print(f"[DEBUG] Loaded player volume from config: {loaded_player_volume}")
            
            # --- NEW: Load the new music player settings ---
            is_random_playback.set(data.get("is_random_playback", True)) # Default to True
            
            # Load the random music directory path
            saved_random_dir = data.get("random_music_directory")
            if saved_random_dir:
                random_music_directory.set(saved_random_dir)
            
            # Load the specific looping track path into our temporary global variable
            saved_loop_track = data.get("looping_track_path")
            if saved_loop_track and os.path.exists(saved_loop_track):
                loaded_loop_track_path = saved_loop_track
                print(f"[DEBUG] Loaded looping track from config: {loaded_loop_track_path}")
            saved_volume = data.get("player_volume", 0.5)
            loaded_player_volume = max(0.0, min(1.0, float(saved_volume)))
            print(f"[DEBUG] Loaded player volume from config: {loaded_player_volume}")
            dark_mode.set(data.get("dark_mode", False))
            minimal_mode.set(data.get("minimal_mode", False))
            orientation.set(data.get("orientation", "Vertical"))
            root.geometry(data.get("window_geometry", "265x605"))
            max_resolution.set(data.get("max_resolution", "1440"))
            # The window geometry is loaded by a separate function
    except (FileNotFoundError, json.JSONDecodeError, ValueError, KeyError) as e:
        # If the config is missing, corrupt, or has a bad value, fall back to defaults
        print(f"[DEBUG] Could not fully load config ({e}), using defaults for some settings.")
        loaded_player_volume

def save_config():
    """Saves application settings."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {} # Create a new dictionary if the file is missing or corrupt

    data.update({
        "music_dir": MUSIC_DIR,
        "video_dir": VIDEO_DIR,
        "alert_sound_file": ALERT_SOUND_FILE,
        "dark_mode": dark_mode.get(),
        "minimal_mode": minimal_mode.get(),
        "orientation": orientation.get(),
        "window_geometry": root.geometry(),
        "max_resolution": max_resolution.get(),
        "is_random_playback": is_random_playback.get(),
        "random_music_directory": random_music_directory.get(),
    })
    # Safely get the looping track path from the player object if it exists
    if player and player.default_loop_track:
        data["looping_track_path"] = str(player.default_loop_track)
        
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# -------------
# 🔹 Save geometry + layout
# -------------
def save_window_geometry():
    """Saves the current window size, position, and layout to the config file."""
    global _resize_save_job
    _resize_save_job = None

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    # Current geometry string
    geom = root.geometry()
    window_geometry.set(geom)

    # Update globals
    size, _, pos = geom.partition("+")
    if "x" in size:
        w, h = size.split("x")
        last_window_w.set(int(w))
        last_window_h.set(int(h))
    if "+" in geom:
        position_parts = pos.split("+")
        if len(position_parts) == 2:
            x, y = position_parts
            last_window_x.set(int(x))
            last_window_y.set(int(y))

    # Save values
    data.update({
        "window_geometry": geom,
        "orientation": orientation.get(),
        "dark_mode": dark_mode.get(),
        "minimal_mode": minimal_mode.get()
    })

    print(f"[DEBUG] Saving window geometry: {geom}, orient={orientation.get()}, "
          f"dark={dark_mode.get()}, minimal={minimal_mode.get()}")

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# -------------
# 🔹 Schedule save on resize
# -------------
def schedule_geometry_save(event=None):
    """
    Debounced geometry save – called on window resize/move events.
    """
    global _resize_save_job
    if event and event.widget != root:
        return
    if _resize_save_job:
        root.after_cancel(_resize_save_job)
    _resize_save_job = root.after(2000, save_window_geometry)  # save after 2s idle

# -------------
# 🔹 Force save when changing orientation/theme
# -------------
def toggle_mode():
    """Toggle between dark and light modes and refresh UI."""
    apply_theme()   # 👈 Force full UI redraw

def toggle_orientation():
    rebuild_buttons()      # rebuild buttons with new layout
    save_window_geometry() # save current orientation immediately

def toggle_minimal():
    """Toggle minimal mode on/off and refresh buttons/layout."""
    rebuild_buttons()   # Recreate toolbar/buttons with minimal layout
    save_window_geometry()

# --- NEW: Scans the playmusic directory for valid song files ---
def get_music_files(directory_path: str) -> list[Path]:
    """
    Scans a directory for .mp3 and .wav files and returns a list of their paths.
    """
    music_dir = Path(directory_path)
    if not music_dir.is_dir():
        print(f"[DEBUG] Music directory not found: {music_dir}")
        return []
    
    # Find all files with .mp3 or .wav extensions
    song_list = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
    print(f"[DEBUG] Found {len(song_list)} songs in {music_dir}.")
    return song_list

# -------------
# 🔹 Load geometry + layout
# -------------
def load_window_geometry():
    global window_geometry, orientation, dark_mode, minimal_mode
    """Loads and applies the window geometry + layout from the config file at startup."""
    if 'window_geometry' not in globals() or not isinstance(window_geometry, tk.StringVar):
        window_geometry = tk.StringVar()
    if not os.path.exists(CONFIG_FILE):
        return
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            geometry = data.get("window_geometry")
            if geometry:
                print(f"[DEBUG] Loading window geometry: {geometry}")
                root.geometry(geometry)
                window_geometry.set(geometry)

                geometry_parts = geometry.split("+")
                size = geometry_parts[0]           # "1024x600"
                pos_x = int(geometry_parts[1]) if len(geometry_parts) > 1 else 0
                pos_y = int(geometry_parts[2]) if len(geometry_parts) > 2 else 0

                if "x" in size:
                    w, h = size.split("x")
                    last_window_w.set(int(w))
                    last_window_h.set(int(h))

                last_window_x.set(pos_x)
                last_window_y.set(pos_y) 

            # Restore layout state (orientation, dark_mode, minimal_mode)
            orientation.set(data.get("orientation", orientation.get()))
            dark_mode.set(data.get("dark_mode", dark_mode.get()))
            minimal_mode.set(data.get("minimal_mode", minimal_mode.get()))

    except (FileNotFoundError, json.JSONDecodeError, tk.TclError):
        print("[DEBUG] No valid window geometry found. Using default.")
        root.geometry(window_geometry.get())

# --- NEW: Robust Audio Initialization ---
def initialize_audio():
    """
    Initializes the main pygame module and its mixer.
    This should be called only ONCE at the start of the application.
    Returns True on success, False on failure.
    """
    try:
        print("[DEBUG] Initializing Pygame & Mixer...")
        pygame.init()
        print("[DEBUG] Initializing Pygame Mixer...")
        pygame.mixer.init()
        print("[DEBUG] Audio systems initialized successfully.")
        return True
    except Exception as e:
        print(f"!!!!!!!!!!!!!! PYGAME AUDIO FAILED TO INITIALIZE !!!!!!!!!!!!!!")
        print(f"ERROR: {e}")
        return False

# --- NEW: Allows the user to select a specific track to loop ---
def set_track_to_loop():
    """Opens a file dialog for the user to select an MP3 or WAV file to loop."""
    if not player: return

    file_path_str = filedialog.askopenfilename(
        title="Select a Song to Loop",
        filetypes=[("Audio Files", "*.mp3 *.wav")]
    )
    if file_path_str:
        player.set_looping_track(Path(file_path_str))

# --- NEW: Allows the user to select a folder for random playback ---
def set_random_music_folder():
    """Opens a directory dialog for the user to select a folder for random playback."""
    if not player: return

    dir_path_str = filedialog.askdirectory(title="Select Folder for Random Music")
    if dir_path_str:
        random_music_directory.set(dir_path_str) # Store the new path
        player.update_random_playlist(Path(dir_path_str))

def _load_pause_icon(icon_name: str = "media playback pause orange.png",
                     size=(20, 20)) -> ImageTk.PhotoImage:
    """
    Loads an .ico file, resizes it and returns a PhotoImage that Tk can use.
    """
    here = Path(__file__).resolve().parent

    icon_path = here / icon_name

    if not icon_path.exists():
        raise FileNotFoundError(f"Icon not found: {icon_path}")

    img = Image.open(icon_path)          # Pillow opens .ico automatically
    img = img.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)

# -------------
# Icon helper
# -------------
def apply_window_icon(win: tk.Tk | tk.Toplevel):
    try:
        win.iconbitmap(icon_path)
    except Exception:
        try:
            img = tk.PhotoImage(file=icon_path)
            win.tk.call('wm', 'iconphoto', win._w, img)
        except Exception as e:
            print(f"⚠️ Could not set icon: {e}")

# For thread-safe communication between yt-dlp hook and GUI
gui_queue = Queue()

# Cache for loaded GIF frames to prevent reloading
gif_frames_cache = {}

def load_png_icon(path, button_size, theme_color):
    """
    Loads a static PNG, resizes it to a square, and pastes it onto a
    theme-colored background matching the button's final size.
    """
    try:
        full_path = _resource_path(os.path.join(ICON_FOLDER, path))
        source_icon = Image.open(full_path).convert("RGBA")

        # 1. Calculate a target SQUARE size for the icon (e.g., 70% of the smaller dimension)
        min_dimension = min(button_size)
        target_size = int(min_dimension * 0.7)
        if target_size < 1: return None

        # 2. Resize the source icon to the target square size
        resized_icon = source_icon.resize((target_size, target_size), Image.Resampling.LANCZOS)

        # 3. Create a new background canvas with the button's true dimensions and theme color
        background = Image.new("RGBA", button_size, theme_color)
        
        # 4. Calculate coordinates to paste the icon in the center
        paste_x = (button_size[0] - target_size) // 2
        paste_y = (button_size[1] - target_size) // 2

        # 5. Paste the resized icon onto the background
        background.paste(resized_icon, (paste_x, paste_y), resized_icon)

        return ImageTk.PhotoImage(background)
    except Exception as e:
        print(f"Error loading PNG {path}: {e}")
        return ImageTk.PhotoImage(Image.new('RGBA', button_size, (0, 0, 0, 0)))

def load_gif_frames(path, button_size, theme_color):
    """
    Loads all frames from a GIF, resizes each to a square, and pastes it
    onto a theme-colored background for centered, non-distorted animation.
    """
    full_path = _resource_path(os.path.join(ICON_FOLDER, path))
    
    # Use a cache key that includes size and color to avoid incorrect re-use
    cache_key = (full_path, button_size, theme_color)
    if cache_key in gif_frames_cache:
        return gif_frames_cache[cache_key]
        
    try:
        gif = Image.open(full_path)
        
        # 1. Calculate a target SQUARE size for the icon frames
        min_dimension = min(button_size)
        target_size = int(min_dimension * 0.7)
        if target_size < 1: return []

        # 2. Calculate coordinates for centering (this is constant for all frames)
        paste_x = (button_size[0] - target_size) // 2
        paste_y = (button_size[1] - target_size) // 2
        
        final_frames = []
        for frame in ImageSequence.Iterator(gif):
            # 3. Create the background canvas for this frame
            background = Image.new("RGBA", button_size, theme_color)
            
            # 4. Resize the raw GIF frame to the target square size
            resized_frame = frame.convert('RGBA').resize((target_size, target_size), Image.Resampling.LANCZOS)
            
            # 5. Paste the frame onto the canvas
            background.paste(resized_frame, (paste_x, paste_y), resized_frame)
            
            final_frames.append(ImageTk.PhotoImage(background))

        gif_frames_cache[cache_key] = final_frames
        return final_frames
    except Exception as e:
        print(f"Error loading GIF {path}: {e}")
        return []

def animate_button(widget, frames, frame_index=0):
    """Recursively updates the widget's image to play the GIF animation."""
    if minimal_mode.get():
        return
    if not getattr(widget, 'is_animating', False):
        return  # Stop the loop if the animation flag has been turned off

    widget.config(image=frames[frame_index])
    next_index = (frame_index + 1) % len(frames)
    # Schedule the next frame update
    widget.after_id = widget.after(50, animate_button, widget, frames, next_index)

def start_animation_on_button(button_index):
    global active_button
    if minimal_mode.get():
        return
    if button_index >= len(grid_frame.winfo_children()): return
    """Begins the animation for a specific button by its index."""
    print(f"[DEBUG] Called start_animation_on_button for index: {button_index}")
    
    button = grid_frame.winfo_children()[button_index]
    active_button = button # Set the new active butto
    
    theme = dark_theme if dark_mode.get() else light_theme
    
    button.is_animating = True
    icon_size = (button.winfo_width(), button.winfo_height())
    
    #if getattr(button, 'is_animating', False): return # Already animating
    #if hasattr(button, 'is_animating') and button.is_animating:
    #    print("[DEBUG] Button is already animating. Aborting.")
    #    return

    frames = load_gif_frames(ANIMATED_GIF_PATHS[button_index], icon_size, theme["button_bg"])
    print(f"[DEBUG] Button size for animation is: {icon_size}")
    if frames:
        print(f"[DEBUG] Successfully loaded {len(frames)} frames. Starting animation.")
        if not hasattr(button, 'static_icon'):
             button.static_icon = button.cget("image") # Save the static SVG icon
        animate_button(button, frames)
    else:
        # --- DEBUG: This will tell us if the GIF failed to load ---
        print("[DEBUG] FAILED to load GIF frames. Animation cannot start.")

def stop_animation_on_button(button_index):
    """Stops the animation and restores the original static SVG icon."""
    if button_index >= len(grid_frame.winfo_children()): return
    button = grid_frame.winfo_children()[button_index]
    button.is_animating = False
    if hasattr(button, 'after_id'):
        button.after_cancel(button.after_id)
    if hasattr(button, 'static_icon'):
        button.config(image=button.static_icon)

def check_gui_queue():
    """Main GUI loop function to check for messages from the download thread."""
    if not gui_queue.empty():
        try:
            message, button_index = gui_queue.get(block=False)
            print(f"[DEBUG] RECEIVED message from queue: '{message}' for button {button_index}")
            if message == 'start_animation':
                start_animation_on_button(button_index)
            if message == 'stop_animation':
                stop_animation_on_button(button_index)
        except queue.Empty: # <--- This is the error
            pass

    # Always schedule the next check
    root.after(100, check_gui_queue)

# -------------
# Custom Askstring Dialog (The reliable replacement)
# -------------
def custom_askstring(title: str, prompt: str, parent: tk.Tk) -> Optional[str]:
    """A custom, icon-aware replacement for simpledialog.askstring."""

    result = [None] # Use a list for mutable access inside nested functions

    # 1. Create the Toplevel window
    win = Toplevel(parent)
    win.title(title)
    win.resizable(False, False)

    # 2. Apply the icon and parenting (this part was correct)
    win.transient(parent)
    apply_window_icon(win)

    # Theme colors
    theme = dark_theme if dark_mode.get() else light_theme
    win.configure(bg=theme["bg"])

    # --- Create the dialog's widgets ---
    main_frame = tk.Frame(win, padx=10, pady=10, bg=theme["bg"])
    main_frame.pack(fill="both", expand=True)

    # Create widgets
    tk.Label(main_frame, text=prompt, justify=tk.CENTER, font=("Arial", 11),
                bg=theme["bg"], fg=theme["fg"]).pack(padx=10, pady=20)

    entry_frame = tk.Frame(main_frame, bg=theme["bg"])
    entry_frame.pack(pady=(0, 10), padx=20, fill="x")

    entry = ttk.Entry(entry_frame, width=40)
    # The entry widget expands to fill the space left by the button
    entry.pack(side="left", fill="x", expand=True)
    entry.focus_set()

    paste_icon_filename = _resource_path(os.path.join(ICON_FOLDER, "yz_Paste_Icon_Gray_Lght_Thme.png"))
    
    # --- NEW: Create and place the Paste Button ---
    try:
        # Assumes you have a 'paste_icon.png' in your ICON_FOLDER
        #yz_Paste_Icon_Gray_Lght_Thme.png
        #yz_Paste_Icon_Gray_Dark_Thme.png
        if dark_mode.get():
            paste_icon_path = _resource_path(os.path.join(ICON_FOLDER, "yz_Paste_Icon_Gray_Dark_Thme.png"))
        else:
            paste_icon_path = _resource_path(os.path.join(ICON_FOLDER, "yz_Paste_Icon_Gray_Lght_Thme.png"))
            
        paste_img = Image.open(paste_icon_path).resize((18, 18), Image.LANCZOS)
        paste_photo = ImageTk.PhotoImage(paste_img)
        
        def paste_from_clipboard():
            try:
                # Get content from the clipboard
                clipboard_content = root.clipboard_get()
                # Clear the entry widget and insert the content
                entry.delete(0, tk.END)
                entry.insert(0, clipboard_content)
            except tk.TclError:
                # This happens if the clipboard is empty or contains non-text data
                pass 

        paste_button = tk.Button(entry_frame, image=paste_photo, width=24, height=24, 
                                 command=paste_from_clipboard,
                                 bg=theme["button_bg"], activebackground=theme["button_active_bg"],
                                 relief="raised", bd=1, highlightthickness=0)
        paste_button.image = paste_photo # Keep a reference to prevent garbage collection
        # Pack the button to the right, with a little padding
        paste_button.pack(side="right", padx=(5, 0))
    except Exception as e:
        print(f"⚠️ Could not load paste icon: {e}")
        # If the icon fails, the entry box will just be wider, which is a graceful fallback.
    button_frame = tk.Frame(main_frame, bg=theme["bg"])
    button_frame.pack()

    # --- Define button commands ---
    def on_ok(event=None): # Add event=None to handle key bindings
        result[0] = entry.get()
        win.destroy()

    def on_cancel(event=None): # Add event=None to handle key bindings
        result[0] = None # Ensure result is None on cancel
        win.destroy()

    tk.Button(button_frame, text="OK", width=8, command=on_ok,
                bg=theme["button_bg"], fg=theme["button_fg"],
                activebackground=theme["button_active_bg"],
                activeforeground=theme["button_fg"]).pack(side="left", padx=5)
    tk.Button(button_frame, text="Canel", width=8, command=on_cancel,
                bg=theme["button_bg"], fg=theme["button_fg"],
                activebackground=theme["button_active_bg"],
                activeforeground=theme["button_fg"]).pack(side="left", padx=5)

    # --- Bind Enter/Escape keys ---
    win.bind("<Return>", on_ok)
    win.bind("<Escape>", on_cancel)

    # --- START: THE CRITICAL FIX ---
    # 3. Force the window to calculate its size based on its content.
    win.update_idletasks()

    # 4. Calculate the position to center the dialog over the parent window.
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()
    win_width = win.winfo_width()
    win_height = win.winfo_height()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (win.winfo_width() // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (win.winfo_height() // 2)

    # 5. Set the dialog's position.
    win.geometry(f"+{x}+{y}")
    # --- END FIX ---

    # 6. NOW that the window is visible and centered, make it modal.
    win.grab_set()
    parent.wait_window(win)

    return result[0]

# --- ANIMATION AND BUTTON HANDLING ---
def load_gifs():
    """Pre-loads all GIF frames into memory for efficient animation."""
    for idx, gif_name in enumerate(ANIMATED_GIF_PATHS):
        gif_path = _resource_path(os.path.join(ICON_FOLDER, gif_name))
        if os.path.exists(gif_path):
            frames = []
            with Image.open(gif_path) as gif:
                for frame in ImageSequence.Iterator(gif):
                    # Ensure frame has transparency support
                    frames.append(frame.copy().convert("RGBA"))
            gif_frames[idx] = frames

def start_button_animation(button: tk.Button, button_index: int):
    """
    FIX: Replaces button PNG with a resized, animated GIF.
    """
    global active_button, is_animating
    if minimal_mode.get():
        return
    if is_animating or button_index not in gif_frames:
        return

    is_animating = True
    active_button = button
    
    # Store the original static image if it doesn't exist yet
    if not hasattr(button, 'original_img'):
        button.original_img = button.cget("image")
        
    frames = gif_frames[button_index]
    
    def update_frame(idx=0):
        if is_animating and active_button == button:
            frame_image = frames[idx]
            theme = dark_theme if dark_mode.get() else light_theme
            # Continue looping only if the animation flag is set for this specific button
            #if not is_animating or active_button != button:
            #    return # Exit the loop cleanly.
            # Resize the GIF frame to fit the current button size while maintaining aspect ratio
            #frame_image = frames[idx]
            
            # --- Use the exact same resizing logic as thumbnail_for_button ---
            btn_size = min(button.winfo_width(), button.winfo_height())
            if btn_size > 1:
                # Calculate target size
                target_size = max(min(int(btn_size * 0.7), btn_size - ICON_PADDING), 1)
                
                # Resize the current GIF frame
                resized_frame = frame_image.resize((target_size, target_size), Image.LANCZOS)
                
                # Paste it onto a theme-colored background to ensure it's centered
                new_image = Image.new("RGBA", (button.winfo_width(), button.winfo_height()), theme["button_bg"])
                paste_x = (button.winfo_width() - target_size) // 2
                paste_y = (button.winfo_height() - target_size) // 2
                new_image.paste(resized_frame, (paste_x, paste_y), resized_frame)
                
                photo_image = ImageTk.PhotoImage(new_image)
                
                button.config(image=photo_image)
                button.image = photo_image # Keep reference
            
            root.after(50, update_frame, (idx + 1) % len(frames))

    # Give the button a moment to draw before starting animation
    root.after(20, update_frame)

def stop_button_animation():
    """Stops the current GIF animation and restores the original PNG image."""
    global is_animating, active_button
    if not is_animating or not active_button:
        return
        
    is_animating = False
    if hasattr(active_button, 'original_img') and active_button.original_img:
        active_button.config(image=active_button.original_img)
    
    active_button = None

# --- Global flag to track audio status ---
is_audio_enabled = False

# -------------
# Music player – uses pygame.mixer for MP3 looping & mute support
# -------------
class LoopingMusicPlayer:
    def __init__(self, default_loop_track_path: Path, initial_random_folder_path: Path):
        """
        Initializes the player's state but does NOT load any music yet.
        Playback is handled by the start() method.
        """
        self.default_loop_track = default_loop_track_path
        random_music_directory.set(str(initial_random_folder_path))
        self.random_playlist = get_music_files(str(initial_random_folder_path))
        
        # --- Set initial states ---
        self.is_muted = False
        self.is_paused = False
        self.pause_pos = 0  # store position in seconds
        self.volume = 0.5   # default starting volume
        self.is_loaded = False
        self.volume = loaded_player_volume
        self._watcher_id = None # To manage the root.after() job
        
        # --- MODIFIED: Check if audio is enabled before proceeding ---
        if not is_audio_enabled:
            print("[DEBUG] Audio is disabled, LoopingMusicPlayer will not initialize.")
            return
            
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception as e:
                print(f"⚠️ Could not init mixer: {e}")
                return 

    def start(self) -> None:
        """Kicks off the playback logic based on the current mode."""
        if not is_audio_enabled:
            print("[DEBUG] Audio is disabled, player will not start.")
            return
        self.play_next_song()
        
    def play_next_song(self):
        """Loads and plays the next song based on the current playback mode."""
        if self.is_muted: return
        self.stop() # Stop any current music before loading the next

        song_to_play = None
        play_loops = 0

        if is_random_playback.get():
            # --- RANDOM MODE ---
            if not self.random_playlist:
                messagebox.showwarning("Random Playback", "The selected random music folder is empty or contains no valid audio files.")
                return
            song_to_play = random.choice(self.random_playlist)
            play_loops = 0 # Play once, the watcher will handle playing the next song
            print(f"[DEBUG] Playing random song: {song_to_play.name}")
        else:
            # --- LOOPING MODE ---
            song_to_play = self.default_loop_track
            play_loops = -1 # Loop this song forever
            print(f"[DEBUG] Playing looping track: {song_to_play.name}")

        if song_to_play and song_to_play.exists():
            try:
                pygame.mixer.music.load(str(song_to_play))
                self.is_loaded = True
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play(loops=play_loops)
                self.is_paused = False
                # IMPORTANT: Only start the "end of song" checker if in random mode
                if is_random_playback.get():
                    self._check_song_end()
            except Exception as e:
                print(f"⚠️ Could not load/play song '{song_to_play.name}'. ERROR: {e}")
                self.is_loaded = False
        else:
            self.is_loaded = False
            print(f"⚠️ Song not found: {song_to_play}")

    def _check_song_end(self):
        """
        Watcher function that checks if the current song has finished playing.
        If it has, it calls play_next_song() to start a new random track.
        """
        # If we are no longer in random mode, stop checking.
        if not is_random_playback.get() or self.is_paused or self.is_muted:
            if self._watcher_id: root.after_cancel(self._watcher_id)
            return

        # If the music is no longer playing, start the next song.
        if not pygame.mixer.music.get_busy():
            print("[DEBUG] Song finished. Playing next random song.")
            self.play_next_song()
        else:
            # Otherwise, schedule this check again in a couple of seconds.
            self._watcher_id = root.after(2000, self._check_song_end)
            
    def on_playback_mode_change(self, *args):
        """Called by the menu checkbox. Stops current music and starts the new mode."""
        print(f"[DEBUG] Playback mode changed. Random is now: {is_random_playback.get()}")
        self.stop()
        root.after(100, self.start)
            
    # --- NEW: Method to handle setting a new looping track ---
    def set_looping_track(self, new_track_path: Path):
        """
        Updates the default song, turns off random mode, and restarts playback.
        """
        print(f"[DEBUG] New looping track has been set to: {new_track_path.name}")
        
        # 1. Update the default song to the user's new choice
        self.default_loop_track = new_track_path
        
        # 2. CRUCIAL: Automatically turn off random mode.
        # This provides a great user experience.
        is_random_playback.set(False)
        
        # 3. Use our existing mode-change logic to restart the player cleanly.
        self.on_playback_mode_change()

    def update_random_playlist(self, new_folder_path: Path):
        """Scans a new folder for songs, turns on random mode, and restarts playback."""
        print(f"[DEBUG] Updating random playlist from folder: {new_folder_path}")
        self.random_playlist = get_music_files(str(new_folder_path))
        is_random_playback.set(True) # Automatically switch to random mode

    def stop(self) -> None:
        if not self.is_loaded: return
        pygame.mixer.music.stop()
        self.is_paused = False
        # Cancel any pending song-end check
        if self._watcher_id:
            root.after_cancel(self._watcher_id)
            self._watcher_id = None

    def on_playback_mode_change(self):
        """Called by the menu. Stops current music and starts the new mode."""
        print(f"[DEBUG] Playback mode changed. Random is now: {is_random_playback.get()}")
        self.stop()
        # Give a brief moment before starting the new song
        root.after(100, self.start)
        
    def toggle_pause(self) -> None:
        if not self.is_loaded: return
        """Pauses or resumes the music playback correctly."""
        if self.is_paused:
            # If paused, unpause the music
            pygame.mixer.music.unpause()
            print("[DEBUG] Resuming playback.")
        else:
            # If playing, pause the music
            pygame.mixer.music.pause()
            print("[DEBUG] Pausing playback.")

        # Invert the paused state
        self.is_paused = not self.is_paused

    def set_volume(self, vol: float) -> None:
        """`vol` is 0.0 … 1.0."""
        self.volume = vol  # <-- store the volume for later use
        pygame.mixer.music.set_volume(vol)

    def toggle_mute(self) -> None:
        if self.is_muted:
            self.start()          # resume playing
        else:
            self.stop()           # stop playback
        self.is_muted = not self.is_muted

def create_light_toolbar():
    """Create and display a custom, light-themed toolbar with clickable menus."""
    global custom_toolbar
    if custom_toolbar and custom_toolbar.winfo_exists():
        custom_toolbar.destroy()

    theme = light_theme
    custom_toolbar = tk.Frame(root, bg=theme["toolbar_bg"], height=9)
    custom_toolbar.pack(side="top", fill="x", before=main_frame)

    menus_to_add = { "File": file_menu, "Edit": edit_menu, "Help": help_menu }

    for name, menu_object in menus_to_add.items():
        menubutton = tk.Menubutton(
            custom_toolbar, text=name, fg=theme["menu_fg"], bg=theme["toolbar_bg"], relief="flat",
            activebackground=theme["menu_active_bg"], activeforeground=theme["menu_fg"], padx=5
        )
        menubutton.pack(side="left", padx=2, pady=0)
        # --- FIX: Call the correct themed function ---
        light_menu = clone_submenu_themed(menu_object, menubutton, theme='light')
        menubutton.config(menu=light_menu)

def create_dark_toolbar():
    """Create and display a custom, dark-themed toolbar with clickable menus."""
    global custom_toolbar
    if custom_toolbar and custom_toolbar.winfo_exists():
        custom_toolbar.destroy()

    theme = dark_theme
    custom_toolbar = tk.Frame(root, bg=theme["toolbar_bg"], height=9)
    custom_toolbar.pack(side="top", fill="x", before=main_frame)

    menus_to_add = { "File": file_menu, "Edit": edit_menu, "Help": help_menu }

    for name, menu_object in menus_to_add.items():
        menubutton = tk.Menubutton(
            custom_toolbar, text=name, fg=theme["menu_fg"], bg=theme["toolbar_bg"], relief="flat",
            activebackground=theme["menu_active_bg"], activeforeground=theme["menu_fg"], padx=5
        )
        menubutton.pack(side="left", padx=2, pady=0)
        # --- FIX: Call the correct themed function ---
        dark_menu = clone_submenu_themed(menu_object, menubutton, theme='dark')
        menubutton.config(menu=dark_menu)

def set_alert_sound():
    """Let user select an MP3 or WAV file as alert sound."""
    global ALERT_SOUND_FILE
    file_path = filedialog.askopenfilename(
        title="Choose Alert Sound",
        filetypes=[("Audio files", "*.mp3 *.wav")]
    )
    if file_path:
        ALERT_SOUND_FILE = file_path
        save_config()
        messagebox.showinfo("Alert Sound", f"Alert sound set:\n{ALERT_SOUND_FILE}")

def clear_alert_sound():
    """Remove any stored alert sound."""
    global ALERT_SOUND_FILE
    ALERT_SOUND_FILE = None
    save_config()
    messagebox.showinfo("Alert Sound", "Alert sound cleared – no sound will play on completion.")

def play_alert_sound():
    """Play the alert sound if one is set, matching player volume."""
    if not ALERT_SOUND_FILE:
        return
    # --- MODIFIED: Check if audio is enabled ---
    if not is_audio_enabled or not ALERT_SOUND_FILE:
        return
    try:
        # Load with pygame instead of playsound (allows volume control)
        alert = pygame.mixer.Sound(ALERT_SOUND_FILE)

        # Use the current player volume (fallback = 1.0)
        vol = getattr(player, "volume", 1.0)
        alert.set_volume(vol)

        alert.play()
    except Exception as e:
        messagebox.showwarning("Alert Sound Error", f"Could not play alert sound:\n{e}")

def _is_playlist(url: str) -> bool:
    """
    Very small helper that checks if a YouTube URL looks like a playlist.
    We simply look for a ``list`` query‑parameter – the official way YouTube
    encodes playlists in URLs.

    Parameters
    ----------
    url : str
        The raw string entered by the user.

    Returns
    -------
    bool
        True if the URL contains a ``list=…`` parameter, False otherwise.
    """
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        return "list" in qs
    except Exception:
        # If anything goes wrong (e.g. an empty string) we treat it as *not* a playlist
        return False

block_cipher = None

exe_dir = os.path.dirname(sys.argv[0])      # or: os.path.abspath(os.path.join(sys.executable, '..'))

COOKIE_FILE = os.path.join(exe_dir, 'cookies.txt')

cached_images: dict[tuple[int,int], ImageTk.PhotoImage] = {}

# -------------
# Keep references so Tk doesn’t GC the images
# -------------
button_imgs: dict[str, ImageTk.PhotoImage] = {}

def cleanup_empty_playlist_dir(base_dir: str, playlist_title: str):
    """
    Check if the yt-dlp playlist folder exists and is empty.
    If yes, delete it.

    Args:
        base_dir (str): Parent directory where files are saved (VIDEO_DIR / MUSIC_DIR).
        playlist_title (str): Title of the playlist (unsanitized, yt-dlp sanitizes it).
    """
    # yt-dlp replaces unsafe characters, so we sanitize the name
    safe_title = playlist_title
    for c in r'\/:*?"<>|':
        safe_title = safe_title.replace(c, "_")

    playlist_dir = os.path.join(base_dir, safe_title)

    if os.path.isdir(playlist_dir):
        try:
            if not os.listdir(playlist_dir):  # empty directory
                shutil.rmtree(playlist_dir)
                print(f"Removed empty playlist directory: {playlist_dir}")
        except Exception as e:
            print(f"Error cleaning up {playlist_dir}: {e}")

# -------------
# 1️⃣ Make stdout/stderr UTF‑8 on Windows (Python ≥ 3.7)
# -------------
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass  # ignore – we’ll fall back to safe_print

# -------------
# Music player – uses pygame.mixer for MP3 looping & mute support
# -------------
def safe_print(*args, **kwargs):
    """Print without crashing if the console can't encode some characters."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fall back to a plain ASCII message
        msg = "pygame is required for background music (music will be disabled)."
        sys.stdout.write(msg + "\n")

try:
    import pygame
except ImportError:          # <-- this block ends here
    pygame = None            # graceful fallback

# The following is *outside* of the try/except block
if pygame:
    # initialise mixer, play music, etc.
    pass
else:
    print("pygame not available – background music disabled")

# -------------
# YT-DL command helpers
# -------------
YTDLP_PATH = "yt-dlp"

# -------------
# 1️⃣ Common helpers – no UI here, just pure logic
# -------------
def _ensure_dir(path: str) -> None:
    """Create *path* (and any missing parents) if it does not exist."""
    os.makedirs(os.path.expandvars(path), exist_ok=True)

    # Default folders (can be changed via menu)

# --- NEW: A dedicated function to handle the application closing event ---
def on_closing():
    """
    This function is called when the user tries to close the main window.
    It guarantees that the final configuration is saved before exiting.
    """
    print("[DEBUG] Window is closing. Saving final configuration...")
    
    # Save all current settings (including the last-set volume) one last time.
    save_config()
    
    # Properly destroy the Tkinter window and exit the application.
    root.destroy()
    
def _base_cmd(url: str, *, playlist_title: bool = False,
              video: bool = False) -> list[str]:
    """
    Return the base yt‑dlp command list.

    * `playlist_title` – if True, use the %(playlist_title,sanitize)s placeholder
      in the output path.  This is only needed for playlist builders.
    * `video` – if True, we want a video (MP4); otherwise an audio file.
    """


    base_dir = VIDEO_DIR if video else MUSIC_DIR

    if playlist_title:
        # add playlist title subdir
        base_dir = os.path.join(base_dir, "%(playlist_title,sanitize)s")

    _ensure_dir(base_dir)

    # -------------
    # 2️⃣ Output template – always “%(title)s.%(ext)s”
    # -------------
    out_template = os.path.join(base_dir, "%(title)s.%(ext)s")

    # -------------
    # 3️⃣ Assemble the common parts of the command
    # -------------
    cmd: list[str] = [YTDLP_PATH, url, "-o", out_template]

    if video:
        selected_height = max_resolution.get()  # dynamic resolution
        cmd += [
            "-f", f"bestvideo[ext=mp4][height<={selected_height}]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--embed-chapters",
            "--merge-output-format", "mp4",
        ]
    else:
        cmd += [
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
        ]

    # --- Common options ---
    cmd += [
        "-v",
        "--embed-thumbnail",
        "--no-mtime",
        "--sponsorblock-remove", "sponsor",
        "--ignore-errors",
        "--http-header", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "--extractor-args", "youtube:player_client=web",
    ]
    # Handle playlists
    if not playlist_title:
        cmd.append("--no-playlist")

    return cmd
    # Remove any empty strings that slipped in (e.g. when no‑playlist flag is added)
    #return [part for part in cmd if part]


# -------------
# 2️⃣ Public “builder” functions – one line each
# -------------
def build_cmd_single_mp3(url: str) -> List[str]:
    
    """Download a single video as MP3 to the static Music folder."""
    return _base_cmd(url, playlist_title=False, video=False)


def build_cmd_single_mp4(url: str) -> List[str]:
    """Download a single video as MP4 to the static Videos folder."""
    return _base_cmd(url, playlist_title=False, video=True)


def build_cmd_playlist_mp3(url: str) -> List[str]:
    """
    Download all items of a playlist as MP3s.

    If the supplied URL does not look like a playlist we still run yt‑dlp
    but warn the user.
    """
    if not _is_playlist(url):
        messagebox.showwarning(
            "Wrong URL",
            ("The provided link does not look like a playlist.\n"
             "We will still try to download it, but you might get an error.")
        )
    return _base_cmd(url, playlist_title=True, video=False)


def build_cmd_playlist_mp4(url: str) -> List[str]:
    """
    Download all items of a playlist as MP4s.

    Same folder logic as the MP3 version, but keeps both video and audio.
    """
    if not _is_playlist(url):
        messagebox.showwarning(
            "Wrong URL",
            ("The provided link does not look like a playlist.\n"
             "We will still try to download it, but you might get an error.")
        )
    return _base_cmd(url, playlist_title=True, video=True)

# -------------
# Show Messages commands (NEW)
# -------------
def show_success_message(path: Optional[str]):
    """If enabled, shows a success message with the download path, centered on main window."""
    if not show_messages_var.get():
        return

    msg = "✅ Download successful!"
    display_path = None
    display_pathwfilename = None
    if path:
        # If playlist, just show directory
        display_path = os.path.dirname(path)
        wrapped_path = textwrap.fill(display_path, width=66)
        
        msg += f"\n\nSaved to:\n"
   
    if last_download_path:
        directory = os.path.dirname(last_download_path)
        filename = os.path.basename(last_download_path)
        msgfilename = f"File: {filename}"

        if current_playlist_count > 1:
            # Playlist: show both dir and filename
            display_path = f"{directory}\n{filename}"
        else:
            # Single: show full path
            display_pathwfilename = last_download_path
            
    def _popup():
        win = tk.Toplevel(root)
        win.title("Download Finished")
        win.transient(root)  # Parent to main window
        win.resizable(False, False)
        apply_window_icon(win)  # Use your app icon

        # Theme colors
        theme = dark_theme if dark_mode.get() else light_theme
        win.configure(bg=theme["bg"])

        # Create widgets
        tk.Label(win, text=msg, justify=tk.CENTER, font=("Arial", 11),
                 bg=theme["bg"], fg=theme["fg"]).pack(padx=10, pady=20)
        
        # --- Path Display Box ---
        if directory:
            wrapped_path = textwrap.fill(display_path, width=66)

            frame = tk.Frame(win, bg=theme["bg"], highlightbackground=theme["fg"],
                             highlightthickness=1, bd=0)
            frame.pack(padx=15, pady=(0, 15), fill="x")

            path_label = tk.Label(
                frame, text=wrapped_path, justify=tk.CENTER,
                font=("Consolas", 10), bg=theme["bg"], fg=theme["fg"], wraplength=400
            )
            path_label.pack(padx=8, pady=6)

            # Tooltip for "Copy"
            tooltip = tk.Label(
                win, text="Copy", bg="black", fg="white",
                font=("Arial", 9), relief="solid", bd=1
            )
            tooltip.place_forget()

            def on_enter(event):
                tooltip.place(x=event.x_root - win.winfo_rootx() + 10,
                              y=event.y_root - win.winfo_rooty() + 10)

            def on_leave(event):
                tooltip.place_forget()

            def on_click(event):
                win.clipboard_clear()
                win.clipboard_append(directory)
                win.update()  # ensures clipboard persists
                tooltip.config(text="Copied ✔")

            path_label.bind("<Enter>", on_enter)
            path_label.bind("<Leave>", on_leave)
            path_label.bind("<Button-1>", on_click)        

        # Create widgets
        tk.Label(win, text=msgfilename, justify=tk.CENTER, font=("Arial", 11),
                 bg=theme["bg"], fg=theme["fg"]).pack(padx=10, pady=20)

        tk.Button(win, text="OK", width=8, command=win.destroy,
                  bg=theme["button_bg"], fg=theme["button_fg"],
                  activebackground=theme["button_active_bg"],
                  activeforeground=theme["button_fg"]).pack(pady=(0, 10))

        # Force update and center on parent window
        win.update_idletasks()
        px, py = root.winfo_x(), root.winfo_y()
        pw, ph = root.winfo_width(), root.winfo_height()
        ww, wh = win.winfo_width(), win.winfo_height()
        x = px + (pw // 2) - (ww // 2)
        y = py + (ph // 2) - (wh // 2)
        win.geometry(f"+{x}+{y}")
        
        if current_index == current_playlist_count and current_playlist_count > 1:
            cleanup_empty_playlist_dir(current_base_dir, "%(playlist_title,sanitize)s")
        # Play only your custom alert sound
        play_alert_sound()

    root.after(0, _popup)

def show_error_message(error: Exception):
    """If enabled, shows a formatted error message, centered on main window."""
    if not show_messages_var.get():
        return

    err_msg = f"An error occurred:\n\n{str(error)}", stop_button_animation()

    def _popup():
        win = tk.Toplevel(root)
        win.title("Error Message")
        win.transient(root)
        win.resizable(False, False)
        apply_window_icon(win)

        theme = dark_theme if dark_mode.get() else light_theme
        win.configure(bg=theme["bg"])

        tk.Label(win, text=err_msg, justify=tk.CENTER, font=("Arial", 11),
                 bg=theme["bg"], fg=theme["fg"]).pack(padx=10, pady=20)
        tk.Button(win, text="OK", width=8, command=win.destroy,
                  bg=theme["button_bg"], fg=theme["button_fg"],
                  activebackground=theme["button_active_bg"],
                  activeforeground=theme["button_fg"]).pack(pady=(0, 10))

        win.update_idletasks()
        px, py = root.winfo_x(), root.winfo_y()
        pw, ph = root.winfo_width(), root.winfo_height()
        ww, wh = win.winfo_width(), win.winfo_height()
        x = px + (pw // 2) - (ww // 2)
        y = py + (ph // 2) - (wh // 2)
        win.geometry(f"+{x}+{y}")

        play_alert_sound()

    root.after(0, _popup)

# Popup Toplevel Windows location & primary display location -----
def center_window(parent, width, height):
    # Get parent's position and size
    parent.update_idletasks()
    px = parent.winfo_x()
    py = parent.winfo_y()
    pw = parent.winfo_width()
    ph = parent.winfo_height()

    # Calculate x and y coordinates to center child window
    x = px + (pw // 2) - (width // 2)
    y = py + (ph // 2) - (height // 2)
    return f"{width}x{height}+{x}+{y}"

# -------------
# Show Messages commands
# -------------
def run_command(cmd: list[str]) -> None:
    """
    Execute an external command and show a friendly error dialog if it fails.
    On success, display a short “Download finished” message **and** the full path
    where yt‑dlp saved the file.
    """
    try:
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            creationflags=creationflags,
        )

        # -------------
        # Try to grab the final “to <path>” line that yt‑dlp prints.
        # Example:  "[download]   100% of 3.50MiB in 00:01 (4.42MiB/s) → C:\Users\me\Music\song.mp3"
        # -------------
        download_path = None
        for line in result.stdout.splitlines():
            match = re.search(r"→\s*(.+)$", line)
            if match:
                download_path = match.group(1).strip()
                break

        msg = f"✅  {cmd[0]} completed successfully."
        if download_path:
            msg += f"\n\nSaved to:\n{download_path}"

        messagebox.showinfo("Download finished", msg)

    except subprocess.CalledProcessError as exc:
        err = (
            f"Command failed with exit code {exc.returncode}\n\n"
            f"Stdout:\n{exc.stdout.strip()}\n\n"
            f"Stderr:\n{exc.stderr.strip()}"
        )
        messagebox.showerror("Download Failed", err)

# -------------
# GUI setup
# -------------
root = tk.Tk()
root.title("YouTube Downloader")
root.resizable(True, True)

# -------------
# State flags
# -------------
dark_mode = tk.BooleanVar(value=True)  # ✅ start in dark mode
minimal_mode = tk.BooleanVar(value=False)
orientation = tk.StringVar(value="Horizontal")
max_resolution = tk.StringVar(value="1440") # <-- ADD THIS LINE (default to 1080p)
show_messages_var = tk.BooleanVar(value=True)

# Bind the resize/move event handler
root.bind("<Configure>", schedule_geometry_save, add="+")  # track size/move

# Create variable to set if LoopingMusicPlayer is to play track 'next Random'
is_random_playback = tk.BooleanVar(value=True) # Default to random mode
random_music_directory = tk.StringVar(value="")

# -------------
# 🔹 Global geometry state
# -------------
window_geometry = tk.StringVar(value="555x205")   # Default fallback
last_window_x = tk.IntVar(value=100)
last_window_y = tk.IntVar(value=100)
last_window_w = tk.IntVar(value=555)
last_window_h = tk.IntVar(value=205)

# Load persisted app config (like paths)
load_config()

# Load window geometry right after creating the root window
load_window_geometry()

def apply_window_icon(win: tk.Tk | tk.Toplevel):
    """Apply the main app icon to any window (Tk or Toplevel)."""
    try:
        win.iconbitmap(icon_path)  # Windows prefers .ico
    except Exception:
        try:
            # Fallback if iconbitmap fails (Linux/macOS, or non-ICO icons)
            img = tk.PhotoImage(file=icon_path)
            win.iconphoto(True, img)
        except Exception as e:
            print(f"⚠️ Could not set icon: {e}")

# Top-level layout
main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True)

# Container frame for everything
container = tk.Frame(main_frame)
container.pack(fill="both", expand=True)

# Row 0: button grid frame
grid_frame = tk.Frame(container)
grid_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 1))

# -------------
# 1️⃣ Progress bar + centered text label
# -------------
# Create bottom progress frame
progress_frame = tk.Frame(container)
progress_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=9)

# Progress bar inside the frame
progress = ttk.Progressbar(progress_frame,
    orient="horizontal",
    mode="determinate"
)
progress.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=2)

# Optional text label under/above progress bar
progress_text = tk.Label(progress_frame, text="", anchor="center")
progress_text.grid(row=0, column=1, padx=5)
progress_frame.columnconfigure(0, weight=1)  # progress bar stretches

container.rowconfigure(0, weight=0)   # fixed-height for overlay
container.rowconfigure(1, weight=1)   # buttons expand
container.rowconfigure(2, weight=0)   # bottom progress bar fixed
container.columnconfigure(0, weight=1)

# --- NEW: Intercept the window close ("X") button event ---
root.protocol("WM_DELETE_WINDOW", on_closing)

# -------------
# --- Helpers ---
# -------------
def show_progress_text(txt: str) -> None:
    theme = dark_theme if dark_mode.get() else light_theme
    progress_text.config(text=txt, bg=theme["accent"], fg=theme["fg"])
    progress_text.lift()

def set_progress(value: float) -> None:
    global current_index, current_playlist_count
    """Set the progress bar value (0.0 – 1.0) and update overlay text."""
    progress["maximum"] = 100
    progress["value"] = value * 100

    if value < 1.0:
        progress_text.config(text=f"Working {current_index}/{current_playlist_count}")
    else:
        progress_text.config(text=f"Done {current_index}/{current_playlist_count}")
        progress_frame.after(15000, lambda: progress_text.config(text=""))

# -------------
# Progress hook for yt-dlp
# -------------
def on_progress(d):
    global manual_playlist_index, current_index, last_download_path
    thread_obj = threading.current_thread()
    if d['status'] == 'downloading' and not getattr(thread_obj, 'animation_started', False):
        print(f"[DEBUG] theread downloading - Hook received status: {d.get('status')}")
        button_index = getattr(thread_obj, 'button_index', -1)
        if button_index != -1:
            print(f"[DEBUG] SENDING 'start_animation' message for button {button_index}")
            gui_queue.put(('start_animation', button_index))
            thread_obj.animation_started = True # Set flag to prevent sending again
    status = d.get("status")
    if not current_is_video and status in ("postprocess_finished"):
        print(f"[DEBUG] postprocess_finished - Hook received status: {d.get('status')}")
        # This is the final mp3 or muxed mp4
        finished_filename = d.get("info_dict", {}).get("filepath") or d.get("filename", "")
        if finished_filename:
            last_download_path = finished_filename
        if manual_playlist_index < current_playlist_count:
            manual_playlist_index += 1
            
    # --- MP4 logic (works correctly for videos in older version) ---
    elif current_is_video and status == "finished":
        print(f"[DEBUG] finished - Hook received status: {d.get('status')}")
        finished_filename = d.get("info_dict", {}).get("filepath") or d.get("filename", "")

        target_extension = ".mp4"
        # Only increment when the *final muxed file* (not raw streams) is done
        if finished_filename.endswith(target_extension):
            last_download_path = finished_filename
            if manual_playlist_index < current_playlist_count:
                manual_playlist_index += 1
                

    # Always sync current index with yt-dlp’s own playlist_index if provided
    current_index = manual_playlist_index
    if d.get("playlist_index") is not None:
        current_index = d["playlist_index"]

    def update_gui():
        global current_base_dir, current_is_video, current_playlist_count
        current_base_dir = VIDEO_DIR if current_is_video else MUSIC_DIR
        theme = dark_theme if dark_mode.get() else light_theme

        if status == "downloading":
            print(f"[DEBUG] downloading - Hook received status: {d.get('status')}")
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                percent = downloaded / total * 100
                progress["maximum"] = 100
                progress["value"] = percent
                progress_text.config(
                    text=f"Working {current_index}/{current_playlist_count} – {percent:.1f}%",
                    bg=theme["bg"], fg=theme["fg"]
                )
            else:
                progress_text.config(
                    text=f"Working {current_index}/{current_playlist_count}",
                    bg=theme["bg"], fg=theme["fg"]
                )
                print(f"[DEBUG] Working - Hook received status: {d.get('status')}")

        elif status == "postprocess_finished":
            print(f"[DEBUG] GUI postprocess_finished - Hook received status: {d.get('status')}")
            progress["value"] = 100
            progress_text.config(
                text=f"Done {current_index}/{current_playlist_count}",
                bg=theme["bg"], fg=theme["fg"]
            )
            if current_index == current_playlist_count:
                progress_frame.after(7000, lambda: (
                reset_progress_bar,
                cleanup_empty_playlist_dir(current_base_dir, "%(playlist_title,sanitize)s")
            ))

    root.after(0, update_gui)

def reset_progress_bar():
    progress["value"] = 0
    theme = dark_theme if dark_mode.get() else light_theme
    progress_text.config(text="", bg=theme["bg"])

# -------------
# 2️⃣ Geometry configuration for the container
# -------------
def _show_text(txt: str, delay: int = 0) -> None:
    """
    Show *txt* in the centre of the progress bar.
    If *delay* > 0 seconds, hide it again after that many seconds.
    """
    # Make sure we’re on the main thread
    root.after(0, lambda: _set_text(txt))

    if delay > 0:
        # Remove the text after `delay` ms (default 15000 = 15 s)
        root.after(int(delay * 1000), lambda: _hide_text())

def _set_text(txt: str) -> None:
    progress_text.config(text=txt)
    progress_text.lift()   # keep it on top

def _hide_text() -> None:
    progress_text.config(text="")

# -------------
# 3️⃣ Submenu to Clone
# -------------
def clone_submenu_themed(src_menu, parent, theme: str = 'dark'):
    """
    Recursively clones a Tkinter Menu with theme-aware colors.
    `theme` can be 'light' or 'dark'.
    """
    theme_colors = dark_theme if theme == 'dark' else light_theme
    menu_config = {
        "bg": theme_colors["menu_bg"],
        "fg": theme_colors["menu_fg"],
        "activebackground": theme_colors["menu_active_bg"],
        "activeforeground": theme_colors["menu_fg"],
        "bd": 0
    }

    new_menu = tk.Menu(parent, tearoff=0, **menu_config)

    end_index = src_menu.index("end")
    if end_index is None:
        return new_menu

    for j in range(end_index + 1):
        item_type = src_menu.type(j)
        if item_type == "separator":
            new_menu.add_separator()
        elif item_type in ("command", "checkbutton", "radiobutton"):
            # This logic works for all three types
            opts = {
                "label": src_menu.entrycget(j, "label"),
                "command": src_menu.entrycget(j, "command")
            }
            if item_type != "command":
                opts["variable"] = src_menu.entrycget(j, "variable")
            if item_type == "radiobutton":
                opts["value"] = src_menu.entrycget(j, "value")

            if item_type == "command":
                new_menu.add_command(**opts)
            elif item_type == "checkbutton":
                new_menu.add_checkbutton(**opts)
            else: # radiobutton
                new_menu.add_radiobutton(**opts)

        elif item_type == "cascade":
            sub_lbl = src_menu.entrycget(j, "label")
            sub_src = src_menu.nametowidget(src_menu.entrycget(j, "menu"))
            # Recurse, passing the theme down
            sub_new = clone_submenu_themed(sub_src, new_menu, theme=theme)
            new_menu.add_cascade(label=sub_lbl, menu=sub_new)

    return new_menu

# -------------
# Custom Volume Overlay
# -------------
def create_volume_overlay(root, player: LoopingMusicPlayer):
    """Attach pause + volume bar overlay on the right side of the menu bar."""
    theme = dark_theme if dark_mode.get() else light_theme

    overlay = tk.Frame(root, bg=theme["toolbar_bg"])
    overlay.place(relx=1.0, y=1, anchor="ne")

    pause_button = tk.Label(overlay, bg=theme["toolbar_bg"])
    pause_button.pack(side="left", padx=(0, 1))

    def update_pause_icon():
        if not playback_icon_photos:
            pause_button.config(
                text="▶" if player.is_paused else "⏸",
                fg=theme["volume_slider_accent"],
                font=("Arial", 12)
            )
            return

        theme_prefix = "dark" if dark_mode.get() else "light"
        state_suffix = "play" if player.is_paused else "pause"
        icon_key = f"{theme_prefix}_{state_suffix}"
        if icon_key in playback_icon_photos:
            pause_button.config(image=playback_icon_photos[icon_key])

    def toggle_player_and_icon(_=None):
        player.toggle_pause()
        update_pause_icon()

    pause_button.bind("<Button-1>", toggle_player_and_icon)
    update_pause_icon()

    slider_style_name = "Dark.Horizontal.TScale" if dark_mode.get() else "Light.Horizontal.TScale"

    vol_slider = ttk.Scale(
        overlay,
        from_=0.0,
        to=1.0,
        orient="horizontal",
        value=player.volume,
        command=lambda v: player.set_volume(float(v)),
        style=slider_style_name
    )
    vol_slider.pack(side="left", fill="x", expand=True)

    player.set_volume(0.5)

    return overlay,vol_slider

# -------------
# REVISED: Central Theme Application Function
# -------------
def apply_theme() -> None:
    """Applies the selected color theme to all UI elements."""
    global custom_toolbar, volume_overlay, volume_slider
    active_animation_index = None
    if is_animating and active_button and active_button.winfo_exists():
        try:
            # Find the numerical index of the currently animating button.
            active_animation_index = grid_frame.winfo_children().index(active_button)
            print(f"[DEBUG] Preserving animation state for button index: {active_animation_index}")
        except ValueError:
            # This is a safety net in case the button isn't found.
            active_animation_index = None
    theme = dark_theme if dark_mode.get() else light_theme 
    # --- Toolbar and Menubar Management ---
    if 'custom_toolbar' in globals() and custom_toolbar and custom_toolbar.winfo_exists():
        custom_toolbar.destroy()

    # --- Rebuild dynamic UI elements that depend on the theme ---
    if 'volume_overlay' in globals() and volume_overlay and volume_overlay.winfo_exists():
        volume_overlay.destroy()

    is_dark = dark_mode.get()

    # Apply background colors
    root.configure(bg=theme["bg"])
    main_frame.configure(bg=theme["bg"])
    container.configure(bg=theme["bg"])
    grid_frame.configure(bg=theme["bg"])
    progress_frame.configure(bg=theme["bg"])

    # Apply foreground/text colors
    progress_text.configure(bg=theme["bg"], fg=theme["fg"])

    # Hide the default menubar to use our custom one fully
    empty_menu = tk.Menu(root)
    root.config(menu=empty_menu)

    # Re-create toolbar with the correct theme
    if is_dark:
        progress.configure(style="Dark.Horizontal.TProgressbar")
        create_dark_toolbar()
    else:
        progress.configure(style="Light.Horizontal.TProgressbar")
        create_light_toolbar()


    if player: # Only create if player exists
        volume_overlay, volume_slider = create_volume_overlay(root, player)

    # Rebuild the main buttons to apply new colors
    rebuild_buttons()
    
    # After the new buttons have been created, check if we need to restore an animation.
    if active_animation_index is not None:
        print(f"[DEBUG] Restoring animation for new button at index: {active_animation_index}")
        # Call the existing start_animation function on the NEW button at the same index.
        # We add a small delay to ensure the new button is fully drawn and sized.
        root.after(50, lambda: start_animation_on_button(active_animation_index))

# -------------
# CENTRALIZED TTK WIDGET STYLING
# -------------
style = ttk.Style()
try:
    style.theme_use("clam")
except Exception:
    pass

# --- Progress Bar Styles ---
style.configure(
    "Light.Horizontal.TProgressbar",
    troughcolor=light_theme["bg"],
    bordercolor=light_theme["bg"],
    background=light_theme["Progress_bar_green"]
)
style.configure(
    "Dark.Horizontal.TProgressbar",
    troughcolor=dark_theme["bg"],
    bordercolor=dark_theme["bg"],
    background=dark_theme["accent"]
)

# --- Volume Slider (TScale) Styles ---
style.configure(
    "Light.Horizontal.TScale",
    troughcolor=light_theme["button_bg"],
    background=light_theme["volume_slider_accent"] # Slider handle color
)
style.configure(
    "Dark.Horizontal.TScale",
    troughcolor=dark_theme["button_bg"],
    background=dark_theme["volume_slider_accent"] # Slider handle color
)

# -------------
# 3️⃣ (Optional) Reset progress bar when a new download starts
#    – this keeps the bar clean if you click another button.
# -------------
def reset_progress_bar() -> None:
    set_progress(0)
    theme = dark_theme if dark_mode.get() else light_theme
    progress_text.config(text="", bg=theme["bg"])

# -------------
# 2️⃣ Hook into yt-dlp
# -------------
def download(url: str, out_template: str):
    ydl_opts = {
        "v": True,
        "progress_hooks": [on_progress],
        "outtmpl": out_template,   # now defined
        #"cookies": COOKIE_FILE,
        "sponsorblock-remove": "sponsor",
        "no-mtime": True,
        "ignoreerrors": True,
        "embed-thumbnail": True,
        "embed-chapters": True,
        "extractor-args": "youtube:player_client=web",
    }

    with ytdlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except Exception as e:
            messagebox.showerror("Download error", str(e))

if os.name == "nt" and os.path.exists(icon_path):
    try:
        root.iconbitmap(icon_path)
    except Exception as e:
        print(f"⚠️ Could not set icon: {e}")

# -------------
# Menu setup
# -------------
# Keep global references for images to avoid garbage collection
button_images_refs: list[ImageTk.PhotoImage] = []
def resize_orientation() -> None:
    """
    Called when the user changes the window orientation via Edit menu.
    Simply forces a re-layout of buttons in grid_frame according to orientation.
    """
    grid_frame.update_idletasks()

def rebuild_buttons() -> None:
    """Rebuild the button layout based on current orientation, theme, and minimal mode."""
    global button_images_refs
    theme = dark_theme if dark_mode.get() else light_theme
    button_images_refs.clear()

    # Clear old buttons
    for widget in grid_frame.winfo_children():
        widget.destroy()

    # Button definitions in correct order
    button_specs = [
        ("Download as MP3", build_cmd_single_mp3),
        ("Download as MP4", build_cmd_single_mp4),
        ("Download Playlist>MP3", build_cmd_playlist_mp3),
        ("Download Playlist>MP4", build_cmd_playlist_mp4)
    ]

    choice = orientation.get()  # read from radiobutton variable
    theme = dark_theme if dark_mode.get() else light_theme

    # Reset all grid weights
    for i in range(4): # Clear previous weights
        grid_frame.rowconfigure(i, weight=0); grid_frame.columnconfigure(i, weight=0)

    vertical_padding = 1

    for idx, (label, builder) in enumerate(button_specs):
        # 1. Base button kwargs from the theme dictionary
        btn_kwargs = {
            "command": lambda b=builder, i=idx: on_button_click(b, i),
            "bg": theme["button_bg"],
            "fg": theme["button_fg"],
            "activebackground": theme["button_active_bg"],
            "activeforeground": theme["button_fg"],
            "relief": "flat",
            "bd": 1
        }

        # 2. Prepare the kwargs dictionary based on the current mode
        if minimal_mode.get():
            # In minimal mode, we only need to add the 'text' key
            btn_kwargs["text"] = label
        else:
            # In icon mode, create a placeholder image and add 'image' and 'compound' keys
            photo = ImageTk.PhotoImage(Image.new('RGBA', (MIN_BTN_SIZE, MIN_BTN_SIZE)))
            btn_kwargs["image"] = photo
            btn_kwargs["compound"] = "center"

        # 3. NOW, create the button using the fully prepared dictionary
        btn = tk.Button(grid_frame, **btn_kwargs)
        btn.grid_propagate(False)

        # 4. Store the original image reference if it exists
        if "image" in btn_kwargs:
            btn.original_img = btn_kwargs["image"]
        else:
            btn.original_img = None
            
        # Placement based on orientation
        if choice == "Vertical":
            btn.grid(row=idx, column=0, sticky="nsew", padx=3, pady=vertical_padding)
        elif choice == "Horizontal":
            btn.grid(row=0, column=idx, sticky="nsew", padx=3, pady=vertical_padding)
        else:  # Square 2x2
            r, c = divmod(idx, 2)
            btn.grid(row=r, column=c, sticky="nsew", padx=3, pady=vertical_padding)

    # Make rows/columns expand properly
    if choice == "Vertical":
        for i in range(len(button_specs)):
            grid_frame.rowconfigure(i, weight=1)
        grid_frame.columnconfigure(0, weight=1)
    elif choice == "Horizontal":
        for i in range(len(button_specs)):
            grid_frame.columnconfigure(i, weight=1)
        grid_frame.rowconfigure(0, weight=1)
    else:  # Square
        for i in range(2):
            grid_frame.rowconfigure(i, weight=1)
            grid_frame.columnconfigure(i, weight=1)
            
    root.after(50, _resize_buttons)


# -------------
# Locate Path menu
# -------------
def _choose_directory(title: str) -> Optional[str]:
    """Open a directory picker and return the chosen path."""
    path = filedialog.askdirectory(title=title)
    return path if path else None


def set_music_path() -> None:
    global MUSIC_DIR
    new_dir = filedialog.askdirectory(title="Choose Music folder")
    if new_dir:
        MUSIC_DIR = new_dir
        save_config()
        messagebox.showinfo("Music Path", f"MP3 downloads will now save under:\n{MUSIC_DIR}")

def set_video_path() -> None:
    global VIDEO_DIR
    new_dir = filedialog.askdirectory(title="Choose Video folder")
    if new_dir:
        VIDEO_DIR = new_dir
        save_config()
        messagebox.showinfo("Video Path", f"MP4 downloads will now save under:\n{VIDEO_DIR}")

menubar = tk.Menu(root)

# BooleanVar that syncs with the menu checkbutton
is_music_mute = tk.BooleanVar(value=False)

def _on_mute_change(*args):
    """Called whenever the checkbutton is toggled."""
    if not player:
        return

    if is_music_mute.get():
        # Mute ON → stop playback
        print("[DEBUG] Muting music")
        player.stop()
        player.is_muted = True
    else:
        # Mute OFF → resume playback
        print("[DEBUG] Unmuting music")
        player.start()
        player.is_muted = False

    # Update the menu label to reflect new state
    new_label = "Unmute Music" if is_music_mute.get() else "Mute Music"
    file_menu.entryconfig("Mute Music", label=new_label)

# React whenever the BooleanVar changes
is_music_mute.trace_add("write", _on_mute_change)

file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Locate Music Path…", command=set_music_path)
file_menu.add_command(label="Locate Video Path…", command=set_video_path)
file_menu.add_separator()
is_random_playback.trace_add("write", lambda *args: player.on_playback_mode_change() if player else None)
file_menu.add_checkbutton(
    label="Play Random Song",
    variable=is_random_playback,
)
file_menu.add_command(label="Set Track to Loop...", command=set_track_to_loop)
file_menu.add_command(label="Set Random Music Folder...", command=set_random_music_folder)
file_menu.add_separator()
file_menu.add_command(label="Set Alert Sound…", command=set_alert_sound)
file_menu.add_command(label="Clear Alert Sound", command=clear_alert_sound)
file_menu.add_separator()

file_menu.add_command(label="Exit", command=on_closing)
menubar.add_cascade(label="File", menu=file_menu)

edit_menu = tk.Menu(menubar, tearoff=0)
edit_menu.add_checkbutton(label="Dark Mode", variable=dark_mode, command=toggle_mode)
edit_menu.add_checkbutton(label="Minimal Mode", variable=minimal_mode, command=toggle_minimal)
edit_menu.add_separator()
edit_menu.add_radiobutton(label="Horizontal Window", variable=orientation, value="Horizontal", command=toggle_orientation)
edit_menu.add_radiobutton(label="Square Window", variable=orientation, value="Square", command=toggle_orientation)
edit_menu.add_radiobutton(label="Vertical Window", variable=orientation, value="Vertical", command=toggle_orientation)
edit_menu.add_separator()

# --- ADD THIS NEW SECTION for the Resolution Submenu ---
resolution_menu = tk.Menu(edit_menu, tearoff=0)
resolution_menu.add_radiobutton(label="720p (HD)", variable=max_resolution, value="720", command=save_config)
resolution_menu.add_radiobutton(label="1080p (Full HD)", variable=max_resolution, value="1080", command=save_config)
resolution_menu.add_radiobutton(label="1440p (QHD)", variable=max_resolution, value="1440", command=save_config)
resolution_menu.add_radiobutton(label="2160p (4K)", variable=max_resolution, value="2160", command=save_config)
edit_menu.add_cascade(label="Max Resolution", menu=resolution_menu)
menubar.add_cascade(label="Edit", menu=edit_menu)

# -------------
# 4️⃣ Helper: show the “Check for Updates” dialog
# -------------
def _show_update_dialog() -> None:
    """
    A small, centered window that shows the pip command to update yt-dlp.
    """
    # 1. Create the Toplevel window
    win = Toplevel(root)
    win.title("Update Command")
    win.resizable(False, False)

    # 2. Apply the crucial parenting and icon logic
    win.transient(root)
    apply_window_icon(win)

    # 3. Create the simplified widgets for the window
    main_frame = tk.Frame(win, padx=15, pady=10)
    main_frame.pack(fill="both", expand=True)

    info_label = Label(
        main_frame,
        text="To update yt-dlp, run this command in a terminal:",
        justify="center"
    )
    info_label.pack(pady=(0, 10))

    # The pip command to be displayed
    cmd = "pip install --pre -U yt-dlp"

    # Using a read-only Entry widget makes it easy for the user to copy the text
    cmd_entry = ttk.Entry(main_frame, width=40)
    cmd_entry.insert(0, cmd)
    cmd_entry.configure(state="readonly")
    cmd_entry.pack(pady=(0, 10))

    # A simple "Close" button
    close_button = ttk.Button(main_frame, text="Close", command=win.destroy)
    close_button.pack()

    # 4. Apply the centering logic (copied from our other successful fixes)
    win.update_idletasks()

    parent_x = root.winfo_x()
    parent_y = root.winfo_y()
    parent_width = root.winfo_width()
    parent_height = root.winfo_height()

    win_width = win.winfo_width()
    win_height = win.winfo_height()

    x = parent_x + (parent_width // 2) - (win_width // 2)
    y = parent_y + (parent_height // 2) - (win_height // 2)

    win.geometry(f"+{x}+{y}")

# -------------
# 3️⃣ Helper: show a tiny dialog that contains an “About” message
# -------------
def _show_about() -> None:
    """Display the current build version."""
    win = Toplevel(root)
    win.title(f"{APP_NAME} – About")
    win.resizable(False, False)

    # --- THE FIX for Custom Toplevels ---
    # 1. Tell the OS this window belongs to the main 'root' window.
    win.transient(root)
    # 2. Now that it's parented, apply the icon.
    apply_window_icon(win)
    # --- END FIX ---

    # Theme colors
    theme = dark_theme if dark_mode.get() else light_theme
    win.configure(bg=theme["bg"])

    # Create the widgets inside the window
    msg = f"{APP_NAME}\n\nVersion: {APP_VERSION}\n\n© 2024 YouTube‑Downloader"
    # Create widgets
    tk.Label(win, text=msg, justify=tk.CENTER, font=("Arial", 11),
                bg=theme["bg"], fg=theme["fg"]).pack(padx=20, pady=10)
    tk.Button(win, text="OK", width=8, command=win.destroy,
                bg=theme["button_bg"], fg=theme["button_fg"],
                activebackground=theme["button_active_bg"],
                activeforeground=theme["button_fg"]).pack(pady=(0, 10))

    # --- START: CENTERING LOGIC (Copied from custom_askstring) ---
    # 1. Force the window to calculate its final size.
    win.update_idletasks()

    # 2. Get the geometry of the main application window ('root').
    parent_x = root.winfo_x()
    parent_y = root.winfo_y()
    parent_width = root.winfo_width()
    parent_height = root.winfo_height()

    # 3. Get the size of our new "About" window.
    win_width = win.winfo_width()
    win_height = win.winfo_height()

    # 4. Calculate the coordinates to center the window.
    x = parent_x + (parent_width // 2) - (win_width // 2)
    y = parent_y + (parent_height // 2) - (win_height // 2)

    # 5. Set the "About" window's position.
    win.geometry(f"+{x}+{y}")

# -------------
# 2️⃣ Helper: open the nightly releases page in the default browser
# -------------
import webbrowser
def _open_nightly_url() -> None:
    """Open the yt‑dlp nightly releases page."""
    url = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases"
    webbrowser.open_new_tab(url)

# -------------
# About menu – add the command (replace your old line)
# -------------
help_menu = tk.Menu(menubar, tearoff=0)
updates_submenu = tk.Menu(help_menu, tearoff=0)
updates_submenu.add_command(label="Open Nightly Releases Page",
                            command=_open_nightly_url)
updates_submenu.add_separator()
updates_submenu.add_command(label="Show pip command…",
                            command=_show_update_dialog)

help_menu.add_cascade(label="Check for Updates (yt‑dlp)",
                     menu=updates_submenu,
                     underline=0)   # underline the “C” in Check
help_menu.add_separator()
help_menu.add_checkbutton(label="Show Messages", variable=show_messages_var)
help_menu.add_separator()
help_menu.add_command(label="About",
                      command=_show_about,
                      underline=1)     # underline the “A”
menubar.add_cascade(label="Help", menu=help_menu)

# -------------
# Button handling
# -------------
def on_button_click(build_fn: callable, button_index: int):
    global manual_playlist_index, current_index, current_playlist_count, current_base_dir, current_is_video
    last_download_path = None
    url = custom_askstring(
        "YouTube URL",
        "Paste your video or playlist link:",
        parent=root
    )
    if not url:
        return
    # --- Start animation AFTER getting a valid URL ---
    button = grid_frame.winfo_children()[button_index]
    
    #start_button_animation(button, button_index)
    print("[DEBUG] URL received. Starting animation immediately.")
    start_animation_on_button(button_index)
    
    # Reset counters for the new job
    manual_playlist_index, current_index, current_playlist_count = 1, 1, 1

    if not _is_playlist(url) and build_fn.__name__.startswith("build_cmd_playlist"):
        messagebox.showwarning("Wrong URL", "This is not a playlist link.", parent=root)

    reset_progress_bar()
    current_is_video = build_fn.__name__.endswith("_mp4")

    # --- PASS button_index to the new thread ---
    thread = threading.Thread(target=download_thread, args=(url, build_fn, button_index), daemon=True)
    thread.start()

    # --- Start the download in a separate thread ---
    #threading.Thread(target=download_thread, args=(url, build_fn), daemon=True).start()
    
# --- run download in background thread ---
def download_thread(url: str, build_fn: dict, button_index: int):
    """
    FIX: This function now runs in the background, handling the entire
    yt-dlp process from start to finish.
    """
    global last_download_path, current_playlist_count, last_download_path
    #threading.current_thread().button_index = button_index
    cmd_options = build_fn(url.strip())
    outtmpl = cmd_options[cmd_options.index("-o") + 1]
    try:
        ydl_opts = {
            #"cookies": COOKIE_FILE,
            "v": True,
            "outtmpl": outtmpl,
            "ignoreerrors": True,
            "sponsorblock-remove": "sponsor",
            "progress_hooks": [on_progress],
            "embed-thumbnail": True,
            "no-mtime": True,
            "http_headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"},
            "extractor-args": {"youtube": {"player_client": "web"}},
        }
        if current_is_video:
            selected_height = max_resolution.get()
            format_string = (
                f"bestvideo[ext=mp4][height<={selected_height}]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            )
            ydl_opts.update({
                "format": format_string,
                "merge_output_format": "mp4",
                "postprocessors": [{
                    'add_infojson': None,
                    'key': 'FFmpegMetadata',
                    'add_chapters': True,
                    'add_metadata': True, # Also embeds title, artist, etc.
                }],
            })
        else:
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{"key":
                    "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "0",
                }],
            })
        if "_playlist" in build_fn.__name__: ydl_opts['yes_playlist'] = True
        
        # Perform the download
        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ytdlp.utils.DownloadError("Could not retrieve video/playlist information. The URL may be invalid or private.")
            current_playlist_count = len(info.get("entries", [])) or 1
            ydl.download([url])

        # Schedule UI updates on the main thread
        root.after(0, show_success_message, last_download_path)

    except Exception as e:
        root.after(0, show_error_message, e)
    finally:
        # ALWAYS stop the animation and reset the progress bar
        #root.after(0, stop_button_animation)
        gui_queue.put(('stop_animation', button_index))
        root.after(0, reset_progress_bar)

# -------------
# Load icons (resized & centered)
# -------------
def load_icon_original(filename: str) -> Image.Image | None:
    full_relative_path = os.path.join(ICON_FOLDER, filename)
    path = _resource_path(full_relative_path)
    if os.path.exists(path):
        try:
            return Image.open(path).convert("RGBA")   # keep alpha channel
        except Exception as e:
            print(f"⚠️ Could not load {filename}: {e}")
    return None
# Store originals – we’ll use them to generate thumbnails later
ORIGINAL_ICONS: list[Image.Image | None] = [load_icon_original(p) for p in UI_ICON_PATHS]

# The *current* PhotoImages that the buttons actually display
CURRENT_PHOTOS: dict[int, ImageTk.PhotoImage] = {}

# -------------
# Create a dictionary for the playback icons for easy access
# This runs right after the main loading, as you requested.
# -------------
playback_icon_photos = {}
try:
    playback_icon_photos["dark_play"]   = ImageTk.PhotoImage(ORIGINAL_ICONS[1].resize((20, 20), Image.LANCZOS))
    playback_icon_photos["dark_pause"]  = ImageTk.PhotoImage(ORIGINAL_ICONS[3].resize((20, 20), Image.LANCZOS))
    playback_icon_photos["light_play"]  = ImageTk.PhotoImage(ORIGINAL_ICONS[2].resize((20, 20), Image.LANCZOS))
    playback_icon_photos["light_pause"] = ImageTk.PhotoImage(ORIGINAL_ICONS[4].resize((20, 20), Image.LANCZOS))
    print("✅ Playback icons processed successfully from UI_ICON_PATHS.")

except (IndexError, AttributeError) as e:
    # This will fail if the icons couldn't be loaded or the indices are wrong.
    print(f"⚠️ Could not process playback icons from UI_ICON_PATHS: {e}. Check UI_ICON_PATHS.")
    playback_icon_photos = {} # Ensure it's empty on failure, so the UI can fall back to text.
    
# -------------
# Helper - Create a thumbnail that fits a target button width
# -------------
def thumbnail_for_button(idx: int, btn_width_px: int) -> ImageTk.PhotoImage | None:
    """Return a PhotoImage sized to fit inside button with padding."""
    orig = ORIGINAL_ICONS[idx]
    if not orig or btn_width_px <= 0:
        return None

    # target size = button width minus padding, cap at 70% of width
    target_size = max(min(int(btn_width_px * 0.7), btn_width_px - ICON_PADDING), 1)
    thumb = orig.resize((target_size, target_size), Image.LANCZOS)

    photo = ImageTk.PhotoImage(thumb)
    CURRENT_PHOTOS[idx] = photo  # keep reference alive
    return photo

def stop_button_animation(button: tk.Button):
    """Stop gif and restore original button image."""
    global is_animating, active_button
    if not is_animating or not active_button:
        return
    is_animating = False
    if hasattr(active_button, 'original_img') and active_button.original_img:
        active_button.config(image=active_button.original_img)
    
    active_button = None

# -------------
# Resize handler – update all button widths & images (debounced)
# -------------
MIN_BTN_SIZE = 60  # Minimum button width & height in pixels
ICON_PADDING = 1   # padding inside button to keep icon within edges
_resize_job = None  # global variable to store scheduled job

def _resize_buttons():
    fw = grid_frame.winfo_width()
    fh = grid_frame.winfo_height()
    if fw <= 1 or fh <= 1: return
    theme = dark_theme if dark_mode.get() else light_theme
    choice = orientation.get()
    for idx, btn in enumerate(grid_frame.winfo_children()):
        if not isinstance(btn, tk.Button):
            continue

        # Calculate button size
        if choice == "Vertical":
            btn_size = max(MIN_BTN_SIZE, fw - 20)
            btn.configure(width=btn_size, height=btn_size)
        elif choice == "Horizontal":
            btn_size = max(MIN_BTN_SIZE, fh - 20)
            btn.configure(width=btn_size, height=btn_size)
        else:  # Square 2x2
            btn_w = max(MIN_BTN_SIZE, fw // 2 - 10)
            btn_h = max(MIN_BTN_SIZE, fh // 2 - 10)
            btn.configure(width=btn_w, height=btn_h)
            btn_size = min(btn_w, btn_h)

        btn.configure(width=btn_size, height=btn_size)

        # Resize image if present
        if not minimal_mode.get():
            icon_size = (btn.winfo_width(), btn.winfo_height())
            if icon_size[0] > 1: # Check if the button has a valid size
                # Load the static SVG icon using our new helper function
                photo = load_png_icon(STATIC_PNG_PATHS[idx], icon_size, theme["button_bg"])
                if photo:
                    btn.configure(image=photo)
                    btn.static_icon = photo
                    btn.image = photo

def on_root_resize(event=None):
    """Debounce the resize event to avoid choppy redraws."""
    global _resize_job
    if _resize_job:
        root.after_cancel(_resize_job)
    _resize_job = root.after(200, lambda: (_resize_buttons(), save_config()))  # schedule _resize_buttons after 50ms

# Bind to both the root window and the frame
root.bind("<Configure>", on_root_resize, add='+') # Use add='+' to not overwrite the geometry save binding
grid_frame.bind("<Configure>", on_root_resize)

def toggle_minimal():
    """Called when the user checks/unchecks Minimal."""
    rebuild_buttons()

# -------------
# Background music – optional
# -------------
# --- 1. Initialize the audio system FIRST ---
is_audio_enabled = initialize_audio()
# --- 2. NOW create the music player, which depends on the audio system ---
player: Optional[LoopingMusicPlayer] = None
if pygame:
    if is_audio_enabled:
        # 1. Use the loaded looping track if it exists, otherwise use the hardcoded default.
        if loaded_loop_track_path:
            default_track = Path(loaded_loop_track_path)
        else:
            default_track = Path(_resource_path("playmusic/No Copyright Come With Me (Creative Commons) deep house.mp3"))
        # 2. Use the loaded random folder if it exists, otherwise use the hardcoded default.
        if random_music_directory.get():
            default_random_folder = Path(random_music_directory.get())
        else:
            default_random_folder = Path(_resource_path("playmusic"))
            
        #default_track = Path(_resource_path("playmusic/No Copyright Come With Me (Creative Commons) deep house.mp3"))
        #default_random_folder = Path(_resource_path("playmusic"))
        
        player = LoopingMusicPlayer(
            default_loop_track_path=default_track,
            initial_random_folder_path=default_random_folder
        )
        # The startup thread kicks off the new player logic
        threading.Thread(target=lambda: (time.sleep(5), player.start()), daemon=True).start()
    else:
        print("[DEBUG] Cannot start music player because audio system failed to initialize.")

def toggle_pause(self) -> None:
    if self.is_paused:
        pygame.mixer.unpause()
        self.is_paused = False
    else:
        pygame.mixer.pause()
        self.is_paused = True

if player:
    root.bind("m", lambda e: player.toggle_mute())

# -------------
# INITIAL APPLICATION START
# -------------
#load_gifs() 
check_gui_queue()
apply_theme()  # Apply the default theme (dark) at startup
root.mainloop()





