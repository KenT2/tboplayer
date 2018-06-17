
# *************************************
# PLAYLIST CLASS
# ************************************

class PlayList():
    """https://en.wikipedia.org/wiki/Media_type
    manages a playlist of tracks and the track selected from the playlist
    """

    #field definition constants
    LOCATION=0
    TITLE=1
    LOCATION_BACKUP=2

    # template for a new track
    _new_track=['','','']
    

    def __init__(self, YTDL_WAIT_TAG):
        self.YTDL_WAIT_TAG = YTDL_WAIT_TAG
        self._num_tracks=0
        self._tracks = []                   # list of track titles
        self._selected_track = PlayList._new_track
        self._selected_track_index = -1     # index of currently selected track

    def length(self):
        return self._num_tracks

    def track_is_selected(self):
            if self._selected_track_index>=0:
                return True
            else:
                return False
            
    def selected_track_index(self):
        return self._selected_track_index

    def selected_track(self):
        return self._selected_track

    def append(self, track):
        """appends a track to the end of the playlist store"""
        self._tracks.append(track)
        self._num_tracks+=1


    def remove(self,index):
        self._tracks.pop(index)
        self._num_tracks-=1
        # is the deleted track always the selcted one?
        self._selected_track_index=-1


    def clear(self):
        self._tracks = []
        self._num_tracks=0
        self._track_locations = []
        self._selected_track_index=-1
        self.selected_track_title=""
        self.selected_track_location=""


    def replace(self,index,replacement):
        self._tracks[index]= replacement
            

    def select(self,index):
        """does housekeeping necessary when a track is selected"""
        if self._num_tracks>0 and index<= self._num_tracks:
        # save location and title to currently selected variables
            self._selected_track_index=index
            self._selected_track = self._tracks[index]
            self.selected_track_location = self._selected_track[PlayList.LOCATION]
            self.selected_track_title = self._selected_track[PlayList.TITLE]

    def waiting_tracks(self):
        waiting = []
        l = len(self.YTDL_WAIT_TAG)
        for i in range(len(self._tracks)):
            if self._tracks[i][1][:l] == self.YTDL_WAIT_TAG:
                waiting += [(i, self._tracks[i])]
        return waiting if len(waiting) else False

