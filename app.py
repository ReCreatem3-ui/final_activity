import os
from tkinter import filedialog

import customtkinter as ctk
from pygame import mixer
from PIL import Image, ImageTk

from utils import resource_path, find_resource, format_time, extract_album_art, shorten_name
from playlist import PlaylistManager
from state import TrackState
from player import TonewavePlayer


# Image Button Helpers
def load_ctk_image(file_path, size=(60, 60)):
    p = find_resource(file_path)
    if p is None:
        raise FileNotFoundError(f"Image file not found: {file_path}")
    return ctk.CTkImage(Image.open(p), size=size)

def make_image_button(parent, image_path, command=None, size=(50, 50)):
    img = load_ctk_image(image_path, size=size)
    lbl = ctk.CTkLabel(parent, image=img, text="", fg_color="transparent")
    lbl.image = img
    if command:
        lbl.bind("<Button-1>", lambda e: command())
    return lbl

def make_image_ctkbutton(parent, image_path, command=None, size=(50, 50)):
    img = load_ctk_image(image_path, size=size)
    btn = ctk.CTkButton(
        parent, image=img, text="", fg_color="transparent",
        hover_color="#2b2b2b", width=size[0], height=size[1],
        corner_radius=12, command=command,
    )
    btn.image = img
    return btn


# UI
class TonewaveUI:

    def __init__(self, root, player):
        self.__root = root
        self.__player = player
        self.__build_ui()

    def __build_ui(self):
        player  = self.__player
        small   = 40
        play_sz = 65

        main_frame = ctk.CTkFrame(self.__root, fg_color="transparent")
        main_frame.place(x=10, y=10, relwidth=0.975, relheight=0.975)

        # Playlist Panel
        playlist_frame = ctk.CTkFrame(main_frame, width=250, fg_color="#1a1a1a")
        playlist_frame.pack(side="left", fill="both", padx=(0, 10), pady=0)
        ctk.CTkLabel(
            playlist_frame, text="Playlist", font=("Futura", 16, "bold")
        ).pack(pady=10)

        scrollable = ctk.CTkScrollableFrame(playlist_frame, fg_color="#1a1a1a")
        scrollable.pack(padx=10, pady=(0, 10), fill="both", expand=True)
        self.__playlist_container = scrollable

        btn_frame = ctk.CTkFrame(playlist_frame, fg_color="transparent")
        btn_frame.pack(pady=5)
        make_image_button(
            btn_frame, "gray/add_button.png", self.__add_tracks, size=(30, 30)
        ).pack(side="left", padx=5)
        make_image_button(
            btn_frame, "gray/clear_button.png", self.__clear_playlist, size=(30, 30)
        ).pack(side="left", padx=5)

        # Player Panel
        player_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        player_frame.pack(side="right", fill="both", expand=True)

        album_frame = ctk.CTkFrame(player_frame, fg_color="#2b2b2b", height=270)
        album_frame.pack(fill="x", padx=20, pady=20)
        album_frame.pack_propagate(False)
        self.__album_frame = album_frame

        no_art = load_ctk_image("gray/no_album.png", size=(480, 250))
        self.__album_label = ctk.CTkLabel(
            album_frame, image=no_art, text="", width=480, height=250
        )
        self.__album_label.pack(expand=True, fill="both")
        self.__album_label.image = no_art

        self.__track_label = ctk.CTkLabel(
            player_frame, text="No track loaded", font=("Helvetica", 16, "bold")
        )
        self.__track_label.pack(pady=10)

        self.__time_label = ctk.CTkLabel(
            player_frame, text="00:00 / 00:00", font=("Helvetica", 12)
        )
        self.__time_label.pack()

        self.__progress_var = ctk.DoubleVar()
        self.__progress_bar = ctk.CTkSlider(
            player_frame, from_=0, to=100,
            variable=self.__progress_var, width=450,
            command=player.seek,
        )
        self.__progress_bar.pack(pady=15)

        # Control Buttons
        ctrl_frame = ctk.CTkFrame(player_frame, fg_color="transparent")
        ctrl_frame.pack(pady=15)

        self.__play_img  = load_ctk_image("gray/play_button.png",  size=(play_sz, play_sz))
        self.__pause_img = load_ctk_image("gray/pause_button.png", size=(play_sz, play_sz))
        self.__loop_imgs = [
            load_ctk_image("gray/loop_off_button.png", size=(small, small)),
            load_ctk_image("gray/loop_all_button.png", size=(small, small)),
            load_ctk_image("gray/loop_one_button.png", size=(small, small)),
        ]

        make_image_ctkbutton(ctrl_frame, "gray/shuffle_button.png",  player.shuffle,           size=(small, small)).grid(row=0, column=0, padx=5)
        make_image_ctkbutton(ctrl_frame, "gray/previous_button.png", player.prev_track,        size=(small, small)).grid(row=0, column=1, padx=5)

        self.__play_pause_btn = make_image_ctkbutton(
            ctrl_frame, "gray/play_button.png", player.toggle_play_pause, size=(play_sz, play_sz)
        )
        self.__play_pause_btn.grid(row=0, column=2, padx=10)

        make_image_ctkbutton(ctrl_frame, "gray/next_button.png", player.next_track, size=(small, small)).grid(row=0, column=3, padx=5)

        self.__loop_btn = make_image_ctkbutton(
            ctrl_frame, "gray/loop_off_button.png", player.toggle_loop, size=(small, small)
        )
        self.__loop_btn.grid(row=0, column=4, padx=5)

        # Volume Control
        vol_frame = ctk.CTkFrame(player_frame, fg_color="transparent")
        vol_frame.pack(pady=10)
        make_image_ctkbutton(vol_frame, "gray/speaker_button.png", None, size=(30, 30)).pack(side="left", padx=(0, 10))

        self.__volume_var = ctk.DoubleVar(value=70)
        ctk.CTkSlider(
            vol_frame, from_=0, to=100,
            variable=self.__volume_var, command=self.__set_volume, width=300,
        ).pack(side="left")
        self.__set_volume(70)

    # Private Helpers
    def __add_tracks(self):
        files = filedialog.askopenfilenames(filetypes=[("Audio Files", "*.mp3 *.wav")])
        if files:
            pl = self.__player.get_playlist()
            pl.add_tracks(files)
            self.update_playlist_display(
                pl.get_playlist(),
                pl.get_current_index(),
                self.__player.load_track_by_index,
                self.__player.play,
            )

    def __clear_playlist(self):
        self.__player.get_playlist().clear()
        self.update_playlist_display([], -1, None, None)
        self.__player.stop()

    def __set_volume(self, val):
        try:
            mixer.music.set_volume(float(val) / 100)
        except Exception:
            pass

    # UI Update Methods
    def set_play_icon(self):
        self.__play_pause_btn.configure(image=self.__play_img)

    def set_pause_icon(self):
        self.__play_pause_btn.configure(image=self.__pause_img)

    def update_loop_icon(self, mode):
        self.__loop_btn.configure(image=self.__loop_imgs[mode])

    def update_track_label(self, text):
        self.__track_label.configure(text=text)

    def update_time_label(self, current, total):
        self.__time_label.configure(text=f"{format_time(current)} / {format_time(total)}")

    def set_progress(self, value):
        self.__progress_var.set(value)

    def set_progress_max(self, value):
        self.__progress_bar.configure(to=value if value > 0 else 1)

    def update_playlist_display(self, playlist, current_index, load_fn, play_fn):
        for widget in self.__playlist_container.winfo_children():
            widget.destroy()
        for i, track in enumerate(playlist):
            base   = shorten_name(os.path.basename(track), 36)
            prefix = "▶ " if i == current_index else "  "
            lbl = ctk.CTkLabel(
                self.__playlist_container,
                text=f"{prefix}{base}",
                font=("Consolas", 14),
                fg_color="transparent",
            )
            lbl.pack(fill="x", pady=2, padx=2)
            if i == current_index:
                lbl.configure(fg_color="#2b2b2b", corner_radius=5)
            if load_fn and play_fn:
                lbl.bind("<Button-1>", lambda e, idx=i: load_fn(idx) or play_fn())
                lbl.bind("<Double-1>", lambda e, idx=i: load_fn(idx) or play_fn())

    def display_album_art(self, current_track):
        self.__album_frame.update_idletasks()
        fw = self.__album_frame.winfo_width()
        fh = self.__album_frame.winfo_height()
        art = extract_album_art(current_track) if current_track else None
        img = art if art else Image.open(find_resource("gray/no_album.png"))
        ratio = min(fw / img.width, fh / img.height)
        img   = img.resize(
            (int(img.width * ratio), int(img.height * ratio)),
            Image.Resampling.LANCZOS,
        )
        photo = ImageTk.PhotoImage(img)
        self.__album_label.configure(image=photo, text="")
        self.__album_label.image = photo


# Entry Point
if __name__ == "__main__":
    try:
        mixer.init()
    except Exception as e:
        print("Warning: mixer.init() failed:", e)

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.geometry("800x650")
    root.title("Tonewave")
    root.iconbitmap(resource_path("assets/icon/music_app.ico"))

    playlist_manager = PlaylistManager()
    track_state      = TrackState()
    player           = TonewavePlayer(root, playlist_manager, track_state)

    ui = TonewaveUI(root, player)
    player.set_ui(ui)

    root.mainloop()
