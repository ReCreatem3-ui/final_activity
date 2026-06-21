import random


# Encapsulation
class PlaylistManager:

    def __init__(self):
        self.__playlist = []
        self.__current_index = -1

    # Getters
    def get_playlist(self):
        return self.__playlist

    def get_current_index(self):
        return self.__current_index

    def get_current_track(self):
        if 0 <= self.__current_index < len(self.__playlist):
            return self.__playlist[self.__current_index]
        return None

    # Setters
    def add_tracks(self, files):
        self.__playlist.extend(files)

    def clear(self):
        self.__playlist = []
        self.__current_index = -1

    def set_index(self, index):
        if 0 <= index < len(self.__playlist):
            self.__current_index = index
            return True
        return False

    # Behaviours
    def has_next(self):
        return self.__current_index < len(self.__playlist) - 1

    def has_prev(self):
        return self.__current_index > 0

    def count(self):
        return len(self.__playlist)

    def get_random_index(self):
        if len(self.__playlist) > 1:
            new_index = self.__current_index
            while new_index == self.__current_index:
                new_index = random.randint(0, len(self.__playlist) - 1)
            return new_index
        return self.__current_index
