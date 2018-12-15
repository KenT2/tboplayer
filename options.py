import csv
import os
import ConfigParser

# ***************************************
# OPTIONS CLASS
# ***************************************

class Options:


# store associated with the object is the tins file. Variables used by the player
# is just a cached interface.
# options dialog class is a second class that reads and saves the otions from the options file

    def __init__(self):

        # define options for interface with player
        self.omx_audio_output = "" # omx audio option
        self.omx_subtitles = "" # omx subtitle option
        self.mode = ""
        self.initial_track_dir =""   # initial directory for add track.
        self.last_track_dir =""   # last directory for add track.
        self.initial_playlist_dir =""   # initial directory for open playlist      
        self.omx_user_options = ""  # omx options suppplied by user, audio overidden by audio option (HDMI or local)
        self.youtube_media_format = "" # what type of file must be downloded from youtube
        self.debug = False  # print debug information to terminal
        self.generate_track_info = False  # generate track information from omxplayer output
        self.lang = ""
        self.subtitles_lang = ""

        # create an options file if necessary
        confdir = os.path.expanduser("~") + '/.tboplayer'
        self.options_file = confdir + '/tboplayer.cfg'
        self.log_file = confdir + '/tboplayer.log'
        self.lang_file = confdir + '/lang'

        if os.path.exists(self.options_file):
            self.read(self.options_file)
        else:
            if not os.path.isdir(confdir):
                os.mkdir(confdir)
            self.create(self.options_file)
            self.read(self.options_file)

    
    def read(self,filename):
        """reads options from options file to interface"""
        config=ConfigParser.ConfigParser()
        config.read(filename)
        try:
            self.omx_audio_output = "-o " + config.get('config','audio',0)
            self.mode = config.get('config','mode',0)
            self.initial_track_dir = config.get('config','tracks',0)
            self.last_track_dir = config.get('config','ltracks',0)
            self.initial_playlist_dir = config.get('config','playlists',0)    
            self.omx_user_options = config.get('config','omx_options',0)
            self.youtube_media_format = config.get('config','youtube_media_format',0)
            self.omx_location = config.get('config','omx_location',0)
            self.ytdl_location = config.get('config','ytdl_location',0)
            self.download_media_url_upon = config.get('config','download_media_url_upon',0)
            self.youtube_video_quality = config.get('config','youtube_video_quality',0)
            self.geometry = config.get('config','geometry',0)
            self.full_screen = int(config.get('config','full_screen',0))
            self.windowed_mode_coords = config.get('config','windowed_mode_coords',0)
            self.windowed_mode_resolution = config.get('config','windowed_mode_resolution',0)
            self.forbid_windowed_mode = int(config.get('config','forbid_windowed_mode',0))
            self.cue_track_mode = int(config.get('config','cue_track_mode',0))
            self.autoplay = int(config.get('config','autoplay',0))
            self.find_lyrics = int(config.get('config','find_lyrics',0))
            self.autolyrics_coords = config.get('config','autolyrics_coords',0)
            self.lang = config.get('config','lang',0)
            self.subtitles_lang = config.get('config','subtitles_lang',0)
            self.ytdl_update = int(config.get('config','ytdl_update',0))

            if config.get('config','debug',0) == 'on':
                self.debug = True
            else:
                self.debug = False

            if config.get('config','subtitles',0) == 'on':
                self.omx_subtitles = "-t on"
            else:
                self.omx_subtitles = ""
        except Exception:
            self.create(self.options_file)
            self.read(self.options_file)
         

    def create(self,filename):
        config=ConfigParser.ConfigParser()
        config.add_section('config')
        config.set('config','audio','hdmi')
        config.set('config','subtitles','off')       
        config.set('config','mode','single')
        config.set('config','playlists','')
        config.set('config','tracks','')
        config.set('config','ltracks','')
        config.set('config','omx_options','')
        config.set('config','debug','off')
        config.set('config','youtube_media_format','mp4')
        config.set('config','omx_location','/usr/bin/omxplayer')
        config.set('config','ytdl_location','/usr/local/bin/youtube-dl')
        config.set('config','download_media_url_upon','add')
        config.set('config','youtube_video_quality','medium')
        config.set('config','geometry','662x380+350+250')
        config.set('config','full_screen','0')
        config.set('config','windowed_mode_coords','+200+200')
        config.set('config','windowed_mode_resolution','480x360')
        config.set('config','forbid_windowed_mode','0')
        config.set('config','cue_track_mode','0')
        config.set('config','autoplay','1')
        config.set('config','find_lyrics','0')
        config.set('config','autolyrics_coords','+350+350')
        config.set('config','lang','en')
        config.set('config','subtitles_lang','en')
        config.set('config','ytdl_update','1')
        with open(filename, 'wb') as configfile:
            config.write(configfile)
            configfile.close()

    def save_state(self):
        config=ConfigParser.ConfigParser()
        config.add_section('config')
        config.set('config','audio',self.omx_audio_output.replace("-o ",""))
        config.set('config','subtitles',"on" if "on" in self.omx_subtitles else "off")       
        config.set('config','mode',self.mode)
        config.set('config','playlists',self.initial_playlist_dir)
        config.set('config','tracks',self.initial_track_dir)
        config.set('config','ltracks',self.last_track_dir)
        config.set('config','omx_options',self.omx_user_options)
        config.set('config','debug',"on" if self.debug else "off")
        config.set('config','youtube_media_format',self.youtube_media_format)
        config.set('config','omx_location',self.omx_location)
        config.set('config','ytdl_location',self.ytdl_location)
        config.set('config','download_media_url_upon',self.download_media_url_upon)
        config.set('config','youtube_video_quality',self.youtube_video_quality)
        config.set('config','geometry',self.geometry)
        config.set('config','full_screen',self.full_screen)
        config.set('config','windowed_mode_coords',self.windowed_mode_coords)
        config.set('config','windowed_mode_resolution',self.windowed_mode_resolution)
        config.set('config','forbid_windowed_mode',self.forbid_windowed_mode)
        config.set('config','cue_track_mode',self.cue_track_mode)
        config.set('config','autoplay',self.autoplay)
        config.set('config','find_lyrics',self.find_lyrics)
        config.set('config','autolyrics_coords',self.autolyrics_coords)
        config.set('config','lang',self.lang)
        config.set('config','subtitles_lang',self.subtitles_lang)
        config.set('config','ytdl_update',self.ytdl_update)
        with open(self.options_file, 'wb') as configfile:
            config.write(configfile)
            configfile.close()

