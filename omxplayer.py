
# pyomxplayer from https://github.com/jbaiter/pyomxplayer
# modified by KenT, heniotierra

# ********************************
# PYOMXPLAYER
# ********************************
import pexpect
import re
import string
import dbus
import gobject
import sys

from threading import Thread
from time import sleep
from dbus import glib
from getpass import getuser


class OMXPlayer(object):

    _PROPS_REXP = re.compile(r"([\w|\W]+)Subtitle count:.*", re.M)
    _TIMEPROP_REXP = re.compile(r".*Duration: (\d{2}:\d{2}:\d{2}.\d{2}), start: (\d.\d+), bitrate: (\d+).*")
    _FILEPROP_REXP = re.compile(r".*audio streams (\d+) video streams (\d+) chapters (\d+) subtitles (\d+).*")
    _VIDEOPROP_REXP = re.compile(r".*Video codec ([\w-]+) width (\d+) height (\d+) profile ([-]{0,1}\d+) fps ([\d.]+).*")
    _TITLEPROP_REXP = re.compile(r"(?:title|TITLE)\s*:\s([\w\d.&\\/'` ]+){0,1}.*", re.UNICODE)
    _ARTISTPROP_REXP = re.compile(r"(?:artist|ARTIST)\s*:\s([\w\d.&\\/'` ]+){0,1}.*", re.UNICODE)
    _AUDIOPROP_REXP = re.compile(r".*Audio codec (\w+) channels (\d+) samplerate (\d+) bitspersample (\d+).*")
    _STATUS_REXP = re.compile(r"M:\s*([\d.]+).*")
    _DONE_REXP = re.compile(r"have a nice day.*")
    
    _LAUNCH_CMD = ''
    _LAUNCH_ARGS_FORMAT = ' -I -s %s %s'
    _PAUSE_CMD = 'p'
    _TOGGLE_SUB_CMD = 's'
    _QUIT_CMD = 'q'
    
    AM_LETTERBOX = 'letterbox'
    AM_FILL = 'fill'
    AM_STRETCH = 'stretch'
    
    paused = False
    playing_location = ''
    # KRT turn subtitles off as a command option is used
    subtitles_visible = False

    #****** KenT added argument to control dictionary generation
    def __init__(self, mediafile, args=None, start_playback=False):
        if not args:
            args = ""
        #******* KenT signals to tell the gui playing has started and ended
        self.start_play_signal = False
        self.end_play_signal = False
        self.failed_play_signal = False
        
        cmd = self._LAUNCH_CMD % (mediafile, args)
        #print "        cmd: " + cmd
        self._process = pexpect.spawn(cmd)
        # fout= file('logfile.txt','w')
        # self._process.logfile_send = sys.stdout
        
        # ******* KenT dictionary generation moved to a function so it can be omitted.
        sleep(0.2)
        self.make_dict()
            
        self._position_thread = Thread(target=self._get_position)
        self._position_thread.start()
        if not start_playback:
            self.toggle_pause()
        # don't use toggle as it seems to have a delay
        # self.toggle_subtitles()

    def _get_position(self):
    
        # ***** KenT added signals to allow polling for end by a gui event loop and also to check if a track is playing before
        # sending a command to omxplayer
        self.start_play_signal = True  

        # **** KenT Added self.position=0. Required if dictionary creation is commented out. Possibly best to leave it in even if not
        self.position=-60.0
        #         commented out in case gui reads position before it is first written.
        
        while self.is_running():
            try:
                index = self._process.expect([self._STATUS_REXP,
                                                pexpect.TIMEOUT,
                                                pexpect.EOF,
                                                self._DONE_REXP])
                if index == 1: continue
                elif index in (2, 3):
                    # ******* KenT added
                    self.end_play_signal=True
                    self.position=0.0
                    break
                else:
                    self.position = float(self._process.match.group(1))/1000000
            except Exception:
                break
            sleep(0.05)

    def make_dict(self):
        self.timenf = dict()
        self.video = dict()
        self.audio = dict()
        self.misc = dict()
        index = -1

        try:
            index = self._process.expect([self._PROPS_REXP, self._DONE_REXP, pexpect.TIMEOUT])
        except Exception:
            if self.is_running(): self.stop()
            self.failed_play_signal = True
        finally:
            if index != 0: self.failed_play_signal = True
        if self.failed_play_signal: return False
        else:
            # Get file properties
            output = self._process.match.group()

            # Get time properties
            time_props = self._TIMEPROP_REXP.search(output)
            if time_props:
                time_props = time_props.groups()
                duration = time_props[0].split(':')
                self.timenf['duration'] = int(duration[0]) * 3600 + int(duration[1]) * 60 + float(duration[2])
                self.timenf['start'] = time_props[1]
                self.timenf['bitrate'] = time_props[2]
            else:
                self.timenf['duration'] = -1
                self.timenf['start'] = -1
                self.timenf['bitrate'] = -1

            # Get file properties
            file_props = self._FILEPROP_REXP.search(output)
            if file_props:
                file_props = file_props.groups()
                (self.audio['streams'], self.video['streams'],
                self.chapters, self.subtitles) = [int(x) for x in file_props]

            # Get video properties        
            video_props = self._VIDEOPROP_REXP.search(output)
            if video_props: 
                video_props = video_props.groups()
                self.video['decoder'] = video_props[0]
                self.video['dimensions'] = tuple(int(x) for x in video_props[1:3])
                self.video['profile'] = int(video_props[3])
                self.video['fps'] = float(video_props[4])
                        
            # Get audio properties
            audio_props = self._AUDIOPROP_REXP.search(output)
            if audio_props:
                audio_props = audio_props.groups()
                self.audio['decoder'] = audio_props[0]
                (self.audio['channels'], self.audio['rate'],
                self.audio['bps']) = [int(x) for x in audio_props[1:]]

            if 'streams' in self.audio and self.audio['streams'] > 0:
                self.current_audio_stream = 1
                self.current_volume = 0.0

            title_prop = self._TITLEPROP_REXP.search(output)
            if title_prop:
                title_prop = title_prop.groups()
                self.misc['title'] = title_prop[0]
            artist_prop = self._ARTISTPROP_REXP.search(output)
            if artist_prop:
                artist_prop = artist_prop.groups()
                self.misc['artist'] = artist_prop[0]


    def init_dbus_link(self):
        try:
            gobject.threads_init()
            glib.init_threads()
            dbus_path = "/tmp/omxplayerdbus." + getuser()
            bus = dbus.bus.BusConnection(open(dbus_path).readlines()[0].rstrip())
            remote_object = bus.get_object("org.mpris.MediaPlayer2.omxplayer", "/org/mpris/MediaPlayer2", introspect=False)
            self.dbusif_player = dbus.Interface(remote_object, 'org.mpris.MediaPlayer2.Player')
            self.dbusif_props = dbus.Interface(remote_object, 'org.freedesktop.DBus.Properties')
        except Exception:
            return False
        return True

    def kill(self):
        self._process.kill(1)

# ******* KenT added basic command sending function
    def send_command(self,command):
        self._process.send(command)
        return True

# ******* KenT added test of whether _process is running (not certain this is necessary)
    def is_running(self):
        return self._process.isalive()

    def toggle_pause(self):
        if self._process.send(self._PAUSE_CMD):
            self.paused = not self.paused

    def toggle_subtitles(self):
        if self._process.send(self._TOGGLE_SUB_CMD):
            self.subtitles_visible = not self.subtitles_visible
            
    def stop(self):
        self._process.send(self._QUIT_CMD)
        self._process.terminate(force=True)

    def set_speed(self):
        raise NotImplementedError

    def set_audiochannel(self, channel_idx):
        raise NotImplementedError

    def set_subtitles(self, sub_idx):
        raise NotImplementedError

    def set_chapter(self, chapter_idx):
        raise NotImplementedError

    def volume(self, volume=False):
        if not volume:
            return self.dbusif_props.Volume()
        else:
            return self.dbusif_props.Volume(float(volume))

    def set_position(self, secs):
        return self.dbusif_player.SetPosition(dbus.ObjectPath('/not/used'), long(secs*1000000))

    def set_video_geometry(self, x1, y1, x2, y2):
        self.dbusif_player.VideoPos(dbus.ObjectPath('/not/used'), str(x1) + ' ' + str(y1) + ' ' + str(x2)+ ' ' + str(y2))
        
    def set_aspect_mode(self, mode):
        '''Use any of the OMXPlayer.AM_??? constants as <mode>'''
        self.dbusif_player.SetAspectMode(dbus.ObjectPath('/not/used'), mode)

    @staticmethod
    def set_omx_location(location):
        OMXPlayer._LAUNCH_CMD = location + OMXPlayer._LAUNCH_ARGS_FORMAT



