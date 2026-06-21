import os
import time
from abc import ABC, abstractmethod

from pygame import mixer
from mutagen.mp3 import MP3

from playlist import PlaylistManager
from state import TrackState


# Abstraction
class MediaPlayerBase(ABC):

    @abstractmethod
    def play(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def next_track(self):
        pass

    @abstractmethod
    def prev_track(self):
        pass

    @abstractmethod
    def seek(self, value):
        pass


# Inheritance + Polymorphism
class TonewavePlayer(MediaPlayerBase):

    def __init__(self, root, playlist_manager, track_state):
        self.__root = root
        self.__playlist = playlist_manager
        self.__state = track_state
        self.__update_after_id = None
        self.__ui = None

    def set_ui(self, ui):
        self.__ui = ui

    # Method Overriding
    def play(self):
        track = self.__playlist.get_current_track()
        if track:
            try:
                mixer.music.play(start=self.__state.get_track_offset())
            except Exception:
                try:
                    mixer.music.play()
                except Exception as e:
                    print("Error playing:", e)
            self.__state.set_playing(True)
            self.__state.set_paused(False)
            self.__state.set_play_start_time(time.time())
            if self.__ui:
                self.__ui.set_pause_icon()
            self.__update_progress()

    # Method Overriding
    def stop(self):
        mixer.music.stop()
        self.__state.reset()
        if self.__ui:
            self.__ui.set_play_icon()
            self.__ui.update_time_label(0, self.__state.get_track_length())
            self.__ui.set_progress(0)
        self.__cancel_update()

    # Method Overriding
    def next_track(self):
        if self.__playlist.has_next():
            self.load_track_by_index(self.__playlist.get_current_index() + 1)
            self.play()

    # Method Overriding
    def prev_track(self):
        if self.__playlist.has_prev():
            self.load_track_by_index(self.__playlist.get_current_index() - 1)
            self.play()

    # Method Overriding
    def seek(self, value):
        try:
            value = float(value)
        except Exception:
            return
        self.__state.set_track_offset(value)
        if self.__ui:
            self.__ui.set_progress(value)
            self.__ui.update_time_label(int(value), self.__state.get_track_length())
        if self.__state.get_is_playing() and not self.__state.get_is_paused():
            try:
                mixer.music.play(start=value)
            except Exception:
                mixer.music.stop()
                mixer.music.play()
            self.__state.set_play_start_time(time.time())
            self.__update_progress()

    # Behaviours
    def toggle_play_pause(self):
        track = self.__playlist.get_current_track()
        if not track:
            if self.__playlist.count() > 0:
                self.load_track_by_index(0)
                self.play()
            return
        if self.__state.get_is_playing() and not self.__state.get_is_paused():
            mixer.music.pause()
            start = self.__state.get_play_start_time()
            if start is not None:
                self.__state.set_track_offset(
                    self.__state.get_track_offset() + (time.time() - start)
                )
                self.__state.set_play_start_time(None)
            self.__state.set_paused(True)
            if self.__ui:
                self.__ui.set_play_icon()
        elif self.__state.get_is_paused():
            mixer.music.unpause()
            self.__state.set_paused(False)
            self.__state.set_play_start_time(time.time())
            if self.__ui:
                self.__ui.set_pause_icon()
            self.__update_progress()
        else:
            self.play()

    def shuffle(self):
        self.load_track_by_index(self.__playlist.get_random_index())
        self.play()

    def toggle_loop(self):
        self.__state.cycle_loop_mode()
        if self.__ui:
            self.__ui.update_loop_icon(self.__state.get_loop_mode())

    def load_track_by_index(self, index):
        if self.__playlist.set_index(index):
            track = self.__playlist.get_current_track()
            try:
                mixer.music.load(track)
            except Exception as e:
                print("Error loading:", track, e)
            self.__state.set_track_offset(0.0)
            self.__state.set_play_start_time(None)
            try:
                audio = MP3(track)
                self.__state.set_track_length(int(audio.info.length))
            except Exception:
                self.__state.set_track_length(0)
            if self.__ui:
                self.__ui.update_track_label(os.path.basename(track))
                self.__ui.set_progress(0)
                self.__ui.set_progress_max(self.__state.get_track_length())
                self.__ui.update_time_label(0, self.__state.get_track_length())
                self.__ui.update_playlist_display(
                    self.__playlist.get_playlist(),
                    self.__playlist.get_current_index(),
                    self.load_track_by_index,
                    self.play
                )
                self.__ui.display_album_art(track)

    # Getters
    def get_state(self):
        return self.__state

    def get_playlist(self):
        return self.__playlist

    # Private Helpers
    def __cancel_update(self):
        if self.__update_after_id is not None:
            try:
                self.__root.after_cancel(self.__update_after_id)
            except Exception:
                pass
            self.__update_after_id = None

    def __update_progress(self):
        self.__cancel_update()
        state = self.__state
        if not state.get_is_playing():
            return
        if state.get_is_paused():
            offset = state.get_track_offset()
            if self.__ui:
                self.__ui.set_progress(offset)
                self.__ui.update_time_label(int(offset), state.get_track_length())
            return
        start = state.get_play_start_time()
        elapsed = (time.time() - start) if start else 0
        current_pos = max(0, state.get_track_offset() + elapsed)
        track_length = state.get_track_length()

        if current_pos < track_length - 0.5:
            if self.__ui:
                self.__ui.set_progress(current_pos)
                self.__ui.update_time_label(int(current_pos), track_length)
            self.__update_after_id = self.__root.after(500, self.__update_progress)
            return

        if self.__ui:
            self.__ui.set_progress(track_length)
            self.__ui.update_time_label(track_length, track_length)

        loop = state.get_loop_mode()
        idx  = self.__playlist.get_current_index()
        if loop == 2:
            self.load_track_by_index(idx)
            self.play()
        elif loop == 1:
            self.load_track_by_index((idx + 1) % self.__playlist.count())
            self.play()
        else:
            if self.__playlist.has_next():
                self.load_track_by_index(idx + 1)
                self.play()
            else:
                self.stop()
