
# Encapsulation
class TrackState:

    def __init__(self):
        self.__is_playing = False
        self.__is_paused = False
        self.__track_offset = 0.0
        self.__play_start_time = None
        self.__track_length = 0
        self.__loop_mode = 0    # 0 = off | 1 = loop all | 2 = loop one

    # Getters
    def get_is_playing(self):
        return self.__is_playing

    def get_is_paused(self):
        return self.__is_paused

    def get_track_offset(self):
        return self.__track_offset

    def get_play_start_time(self):
        return self.__play_start_time

    def get_track_length(self):
        return self.__track_length

    def get_loop_mode(self):
        return self.__loop_mode

    # Setters
    def set_playing(self, value):
        self.__is_playing = value

    def set_paused(self, value):
        self.__is_paused = value

    def set_track_offset(self, value):
        self.__track_offset = value

    def set_play_start_time(self, value):
        self.__play_start_time = value

    def set_track_length(self, value):
        self.__track_length = value

    def cycle_loop_mode(self):
        self.__loop_mode = (self.__loop_mode + 1) % 3

    def reset(self):
        self.__is_playing = False
        self.__is_paused = False
        self.__track_offset = 0.0
        self.__play_start_time = None
