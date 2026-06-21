import customtkinter as ctk
from tkinter import filedialog
from tkinter import PhotoImage
from tkinter import Tk, PhotoImage
from pygame import mixer
import time
import os
import random
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from PIL import Image, ImageTk
import io
import sys
from pathlib import Path

# --- Robust Resource Loading ---
def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path is None:
        base_path = Path(__file__).parent
    else:
        base_path = Path(base_path)
    return str(base_path / relative_path)

def find_resource(relative_path: str, verbose=True) -> Path | None:
    base = Path(getattr(sys, "_MEIPASS", None)) if getattr(sys, "_MEIPASS", None) else Path(__file__).parent
    requested = Path(relative_path)
    candidate = base / requested
    if candidate.exists():
        return candidate
    target_name = requested.name.lower()
    try:
        for p in base.rglob('*'):
            if p.is_file() and p.name.lower() == target_name:
                return p
    except Exception:
        pass
    def normalize(s: str) -> str:
        import re
        s2 = s.lower()
        s2 = re.sub(r'[\s\-_]+', '', s2)
        s2 = re.sub(r'[^a-z0-9]', '', s2)
        return s2
    target_norm = normalize(requested.name)
    try:
        for p in base.rglob('*'):
            if p.is_file() and normalize(p.name) == target_norm:
                return p
    except Exception:
        pass
    return None

def load_ctk_image(file_path, size=(60, 60)):
    p = find_resource(file_path)
    if p is None:
        raise FileNotFoundError(f"Image file not found: {file_path}")
    return ctk.CTkImage(Image.open(p), size=size)

# --- Image-only button creator ---
def make_image_button(parent, image_path, command=None, size=(50, 50)):
    img = load_ctk_image(image_path, size=size)
    lbl = ctk.CTkLabel(parent, image=img, text="", fg_color="transparent")
    lbl.image = img
    if command:
        lbl.bind("<Button-1>", lambda e: command())
    return lbl

# --- CTkButton for controls ---
def make_image_ctkbutton(parent, image_path, command=None, size=(50,50)):
    img = load_ctk_image(image_path, size=size)
    btn = ctk.CTkButton(
        parent, image=img, text="", fg_color="transparent",
        hover_color="#2b2b2b", width=size[0], height=size[1],
        corner_radius=12,
        command=command
    )
    btn.image = img
    return btn

# --- Initialize mixer ---
try:
    mixer.init()
except Exception as e:
    print("Warning: mixer.init() failed:", e)

# --- Appearance ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# --- Window ---
root = ctk.CTk()
root.geometry("800x650")
root.title("Tonewave")
root.iconbitmap(resource_path('assets/Icon/music-app.ico'))

# --- Globals ---
current_track = ""
track_length = 0
is_playing = False
is_paused = False
track_offset = 0.0
play_start_time = None
playlist = []
current_index = -1
loop_mode = 0
update_after_id = None

# --- Button Sizes ---
small_btn_size = 40
play_btn_size = 65
corner = 12

# --- Utility Functions ---
def format_time(seconds):
    seconds = max(0, int(seconds))
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins:02d}:{secs:02d}"

def extract_album_art(file_path):
    try:
        audio = ID3(file_path)
        for tag in audio.values():
            if isinstance(tag, APIC):
                image_data = tag.data
                image = Image.open(io.BytesIO(image_data))
                return image
    except Exception:
        pass
    return None

def display_album_art():
    album_frame.update_idletasks()
    frame_width = album_frame.winfo_width()
    frame_height = album_frame.winfo_height()
    if current_track:
        album_art = extract_album_art(current_track)
        if album_art:
            img_width, img_height = album_art.size
            ratio = min(frame_width / img_width, frame_height / img_height)
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
            album_art = album_art.resize((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(album_art)
            album_label.configure(image=photo, text="")
            album_label.image = photo
            return
    no_album_image = Image.open(find_resource("Gray/no-album.png"))
    img_width, img_height = no_album_image.size
    ratio = min(frame_width / img_width, frame_height / img_height)
    new_width = int(img_width * ratio)
    new_height = int(img_height * ratio)
    no_album_image = no_album_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(no_album_image)
    album_label.configure(image=photo, text="")
    album_label.image = photo

def shorten_name(name, max_len=36):
    if not isinstance(name, str):
        name = str(name)
    if len(name) <= max_len:
        return name
    base, ext = os.path.splitext(name)
    if ext and len(ext) <= 6 and len(base) > (max_len - 4 - len(ext)):
        keep = max_len - 4 - len(ext)
        return base[:keep] + "..." + ext
    else:
        return name[:max_len - 3] + "..."

# --- Playlist with Labels ---
def update_playlist_display():
    for widget in playlist_container.winfo_children():
        widget.destroy()
    for i, track in enumerate(playlist):
        base = os.path.basename(track)
        base = shorten_name(base, 36)
        prefix = "▶ " if i == current_index else "  "
        text = f"{prefix}{base}"
        lbl = ctk.CTkLabel(playlist_container, text=text, font=("Consolas", 14), fg_color="transparent")
        lbl.pack(fill="x", pady=2, padx=2)
        if i == current_index:
            lbl.configure(fg_color="#2b2b2b", corner_radius=5)
        lbl.bind("<Button-1>", lambda e, idx=i: load_track_by_index(idx) or play_track())
        lbl.bind("<Double-1>", lambda e, idx=i: load_track_by_index(idx) or play_track())

def add_tracks():
    global playlist
    files = filedialog.askopenfilenames(filetypes=[("Audio Files", "*.mp3 *.wav")])
    if files:
        playlist.extend(files)
        update_playlist_display()

def clear_playlist():
    global playlist, current_index
    playlist = []
    current_index = -1
    update_playlist_display()
    stop_track()

def load_track_by_index(index):
    global current_track, track_length, track_offset, current_index, play_start_time, update_after_id
    if 0 <= index < len(playlist):
        current_index = index
        current_track = playlist[index]
        track_label.configure(text=os.path.basename(current_track))
        try:
            mixer.music.load(current_track)
        except Exception as e:
            print("Error loading:", current_track, e)
        track_offset = 0.0
        play_start_time = None
        try:
            audio = MP3(current_track)
            track_length = int(audio.info.length)
        except Exception:
            track_length = 0
        progress_var.set(0)
        progress_bar.configure(to=track_length if track_length > 0 else 1)
        time_label.configure(text=f"00:00 / {format_time(track_length)}")
        update_playlist_display()
        display_album_art()

# --- Playback Functions ---
def play_track():
    global is_playing, is_paused, play_start_time, update_after_id
    if current_track:
        try:
            mixer.music.play(start=track_offset)
        except Exception:
            try:
                mixer.music.play()
            except Exception as e:
                print("Error playing:", e)
        is_playing = True
        is_paused = False
        play_pause_btn.configure(image=pause_img)
        play_start_time = time.time()
        progress_var.set(track_offset)
        update_progress()

def stop_track():
    global is_playing, is_paused, track_offset, play_start_time, update_after_id
    mixer.music.stop()
    is_playing = False
    is_paused = False
    track_offset = 0.0
    play_start_time = None
    progress_var.set(0)
    play_pause_btn.configure(image=play_img)
    time_label.configure(text=f"00:00 / {format_time(track_length)}")
    if update_after_id is not None:
        try:
            root.after_cancel(update_after_id)
        except Exception:
            pass

def toggle_play_pause():
    global is_playing, is_paused, play_start_time, track_offset
    if not current_track:
        if playlist:
            load_track_by_index(0)
            play_track()
        return
    if is_playing and not is_paused:
        mixer.music.pause()
        if play_start_time is not None:
            track_offset += time.time() - play_start_time
            play_start_time = None
        is_paused = True
        play_pause_btn.configure(image=play_img)
    elif is_paused:
        mixer.music.unpause()
        is_paused = False
        play_pause_btn.configure(image=pause_img)
        play_start_time = time.time()
        update_progress()
    else:
        play_track()

def prev_track():
    global current_index
    if current_index > 0:
        load_track_by_index(current_index - 1)
        play_track()

def next_track():
    global current_index
    if current_index < len(playlist) - 1:
        load_track_by_index(current_index + 1)
        play_track()

def shuffle_track():
    global current_index
    if len(playlist) > 1:
        new_index = current_index
        while new_index == current_index:
            new_index = random.randint(0, len(playlist) - 1)
        load_track_by_index(new_index)
        play_track()

def toggle_loop():
    global loop_mode
    loop_mode = (loop_mode + 1) % 3
    loop_imgs = [loop_off_img, loop_all_img, loop_one_img]
    loop_btn.configure(image=loop_imgs[loop_mode])

def seek_track(value):
    global track_offset, play_start_time, is_playing, is_paused
    try:
        value = float(value)
    except Exception:
        return
    track_offset = value
    progress_var.set(value)
    time_label.configure(text=f"{format_time(int(value))} / {format_time(track_length)}")
    if is_playing and not is_paused:
        try:
            mixer.music.play(start=track_offset)
        except Exception:
            mixer.music.stop()
            mixer.music.play()
        play_start_time = time.time()
        update_progress()

def update_progress():
    global update_after_id, is_playing, is_paused, play_start_time, track_offset, current_index, track_length
    if update_after_id is not None:
        try:
            root.after_cancel(update_after_id)
        except Exception:
            pass
        update_after_id = None
    if not is_playing:
        return
    if is_paused:
        progress_var.set(track_offset)
        time_label.configure(text=f"{format_time(int(track_offset))} / {format_time(track_length)}")
        return
    elapsed = time.time() - play_start_time if play_start_time else 0
    current_pos = track_offset + elapsed
    if current_pos < 0:
        current_pos = 0
    if current_pos < track_length - 0.5:
        progress_var.set(current_pos)
        time_label.configure(text=f"{format_time(int(current_pos))} / {format_time(track_length)}")
        update_after_id = root.after(500, update_progress)
        return
    progress_var.set(track_length)
    time_label.configure(text=f"{format_time(int(track_length))} / {format_time(track_length)}")
    if loop_mode == 2:
        load_track_by_index(current_index)
        play_track()
    elif loop_mode == 1:
        if current_index < len(playlist) - 1:
            load_track_by_index(current_index + 1)
        else:
            load_track_by_index(0)
        play_track()
    else:
        if current_index < len(playlist) - 1:
            load_track_by_index(current_index + 1)
            play_track()
        else:
            stop_track()

# --- UI Setup ---
main_frame = ctk.CTkFrame(root, fg_color="transparent")
main_frame.place(x=10, y=10, relwidth=0.975, relheight=0.975)

no_art_img = load_ctk_image("Gray/no-album.png", size=(480, 250))

# Playlist Frame
playlist_frame = ctk.CTkFrame(main_frame, width=250, fg_color="#1a1a1a")
playlist_frame.pack(side="left", fill="both", padx=(0, 10), pady=0)
playlist_label = ctk.CTkLabel(playlist_frame, text="Playlist", font=("Futura", 16, "bold"))
playlist_label.pack(pady=10)

# --- Scrollable Playlist Container ---
scrollable_frame = ctk.CTkScrollableFrame(playlist_frame, fg_color="#1a1a1a")
scrollable_frame.pack(padx=10, pady=(0,10), fill="both", expand=True)
playlist_container = scrollable_frame

playlist_btn_frame = ctk.CTkFrame(playlist_frame, fg_color="transparent")
playlist_btn_frame.pack(pady=5)
add_btn = make_image_button(playlist_btn_frame, "Gray/add-button.png", add_tracks, size=(30, 30))
add_btn.pack(side="left", padx=5)
clear_btn = make_image_button(playlist_btn_frame, "Gray/clear-button.png", clear_playlist, size=(30, 30))
clear_btn.pack(side="left", padx=5)

# --- Player Frame ---
player_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
player_frame.pack(side="right", fill="both", expand=True)

album_frame = ctk.CTkFrame(player_frame, fg_color="#2b2b2b", height=270)
album_frame.pack(fill="x", padx=20, pady=20)
album_frame.pack_propagate(False)

album_label = ctk.CTkLabel(album_frame, image=no_art_img, text="", width=480, height=250)
album_label.pack(expand=True, fill="both")
album_label.image = no_art_img

track_label = ctk.CTkLabel(player_frame, text="No track loaded", font=("Helvetica", 16, "bold"))
track_label.pack(pady=10)
time_label = ctk.CTkLabel(player_frame, text="00:00 / 00:00", font=("Helvetica", 12))
time_label.pack()

progress_var = ctk.DoubleVar()
progress_bar = ctk.CTkSlider(player_frame, from_=0, to=100, variable=progress_var,
                             width=450, command=seek_track)
progress_bar.pack(pady=15)

ctrl_frame = ctk.CTkFrame(player_frame, fg_color="transparent")
ctrl_frame.pack(pady=15)

#-- Control Buttons ---
play_img = load_ctk_image("Gray/play-button.png", size=(play_btn_size, play_btn_size))
pause_img = load_ctk_image("Gray/pause-button.png", size=(play_btn_size, play_btn_size))
next_img = load_ctk_image("Gray/next-button.png", size=(small_btn_size, small_btn_size))
prev_img = load_ctk_image("Gray/previous-button.png", size=(small_btn_size, small_btn_size))
shuffle_img = load_ctk_image("Gray/shuffle-button.png", size=(small_btn_size, small_btn_size))
loop_off_img = load_ctk_image("Gray/loop-off-button.png", size=(small_btn_size, small_btn_size))
loop_all_img = load_ctk_image("Gray/loop-all-button.png", size=(small_btn_size, small_btn_size))
loop_one_img = load_ctk_image("Gray/loop-one-button.png", size=(small_btn_size, small_btn_size))

#-- Control Buttons Creation ---
shuffle_btn = make_image_ctkbutton(ctrl_frame, "Gray/shuffle-button.png", shuffle_track, size=(small_btn_size, small_btn_size))
prev_btn    = make_image_ctkbutton(ctrl_frame, "Gray/previous-button.png", prev_track, size=(small_btn_size, small_btn_size))
play_pause_btn = make_image_ctkbutton(ctrl_frame, "Gray/play-button.png", toggle_play_pause, size=(play_btn_size, play_btn_size))
next_btn    = make_image_ctkbutton(ctrl_frame, "Gray/next-button.png", next_track, size=(small_btn_size, small_btn_size))
loop_btn    = make_image_ctkbutton(ctrl_frame, "Gray/loop-off-button.png", toggle_loop, size=(small_btn_size, small_btn_size)) 

#-- Control Buttons Layout ---
shuffle_btn.grid(row=0, column=0, padx=5)
prev_btn.grid(row=0, column=1, padx=5)
play_pause_btn.grid(row=0, column=2, padx=10)
next_btn.grid(row=0, column=3, padx=5)
loop_btn.grid(row=0, column=4, padx=5)

# --- Volume Control ---
volume_frame = ctk.CTkFrame(player_frame, fg_color="transparent")
volume_frame.pack(pady=10)
speaker_img = load_ctk_image("Gray/speaker-button.png", size=(20,20))
volume_label = make_image_ctkbutton(volume_frame, "Gray/speaker-button.png", None, size=(30,30))
volume_label.pack(side="left", padx=(0,10))

volume_var = ctk.DoubleVar(value=70)
def set_volume(val):
    try:
        mixer.music.set_volume(float(val)/100)
    except Exception:
        pass
volume_slider = ctk.CTkSlider(volume_frame, from_=0, to=100, variable=volume_var,
                              command=set_volume, width=300)
volume_slider.pack(side="left")
set_volume(70)

# --- Start UI ---
root.mainloop()
