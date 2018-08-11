
"""
A GUI interface using jbaiter's pyomxplayer to control omxplayer

INSTALLATION
***
  *  TBOPlayer requires avconv, youtube-dl, and also the python libraries requests, gobject2, gtk2, pexpect and ptyprocess to be installed in order to work.
  *
  *  -------------------------
  *
  *  To install TBOPlayer and all required libraries, you can simply use the following command from tboplayer directory:
  *
  *      chmod +x setup.sh 
  *      ./setup.sh
  *
  *  -------------------------
  *
  *  See README.md file for more details on installation
  *  
  
OPERATION
Menus
====
 Track - Track - add tracks (for selecting multiple tracks, hold ctrl when clicking) or directories or URLs, edit or remove tracks from the current playlist
 Playlist - save the current playlist or open a saved one or load youtube playlist
 OMX - display the track information for the last played track (needs to be enabled in options)
 Options -
    Audio Output - play sound to hdmi or local output, auto does not send an audio option to omxplayer.
    Mode - play the Single selected track, Repeat the single track, rotate around the Playlist starting from the selected track, randomly play a track from the Playlist.
    Initial directory for tracks - where Add Track starts looking.
    Initial directory for playlists - where Open Playlist starts looking
    Enable subtitles
    OMXPlayer location - path to omxplayer binary
    OMXplayer options - add your own (no validation so be careful)
    Download from Youtube - defines whether to download video and audio or audio only from Youtube (other online video services will always be asked for "video and audio")
    Download actual media URL [when] - defines when to extract the actual media from the given URL, either upon adding the URL or when playing it
    Youtube video quality - lets you choose between "small", "medium" and "high" qualities (Youtube only feature)
    youtube-dl location - path to youtube-dl binary
    Start/End track paused - Pauses the track both in the beginning and in the end of the track
    Autoplay on start up - If TBOPlayer has just been opened and has some file in the playlist, automatically satrt playing the first file in the list
    Forbid windowed mode - if enabled will make videos always show in full screen, disabling the video window mode and video progress bar - useful if you're using tboplayer through a remote desktop
    Debug - prints some debug text to the command line

  *  See README.md file for more details on operation in the OPERATION section

TODO (maybe)
--------
sort out black border around some videos
gapless playback, by running two instances of pyomxplayer
read and write m3u and pls playlists


PROBLEMS
---------------
I think I might have fixed this but two tracks may play at the same time if you use the controls quickly, you may need to SSH in form another computer and use top -upi and k to kill the omxplayer.bin

"""

from options import *
from ytdl import *
from omxplayer import *
from playlist import *
from dnd import *
from dbusinterface import *
from htmlparsers import *
from scrolledframe import *
from debugging import *

from threading import Thread
from time import sleep
from pprint import ( pformat, pprint )
from random import randint
from math import log10
from magic import from_file
import gettext
import json
import re
import string
import sys

from Tkinter import *
from ttk import ( Progressbar, Style, Sizegrip )
from gtk.gdk import ( screen_width, screen_height )
import Tkinter as tk
import tkFileDialog
import tkMessageBox
import tkSimpleDialog
import tkFont

options = Options()

try:
    gettext.translation('tboplayer', localedir=sys.path[0] + '/locale', languages=[options.lang]).install()
except:
    _ = lambda x:x


#**************************
# TBOPLAYER CLASS
# *************************

class TBOPlayer:


    # regular expression patterns
    RE_RESOLUTION = re.compile("^([0-9]+)x([0-9]+)$")
    RE_COORDS = re.compile("^([\+-][0-9]+)([\+-][0-9]+)$")

    _SUPPORTED_MIME_TYPES = ('video/x-msvideo', 'video/quicktime', 'video/mp4', 'video/x-flv', 'video/x-matroska', 'audio/x-matroska',
          'video/3gpp', 'audio/x-aac', 'video/h264', 'video/h263', 'video/x-m4v', 'audio/midi', 
          'audio/mid', 'audio/vnd.qcelp', 'audio/mpeg', 'video/mpeg', 'audio/rmf', 'audio/x-rmf',
          'audio/mp4', 'video/mj2', 'audio/x-tta', 'audio/tta', 'application/mp4', 'audio/ogg',
          'video/ogg', 'audio/wav', 'audio/wave' ,'audio/x-pn-aiff', 'audio/x-pn-wav', 'audio/x-wav',
          'audio/flac', 'audio/x-flac', 'video/h261', 'application/adrift', 'video/3gpp2', 'video/x-f4v',
          'application/ogg', 'audio/mpeg3', 'audio/x-mpeg-3', 'audio/x-gsm', 'audio/x-mpeg', 'audio/mod',
          'audio/x-mod', 'video/x-ms-asf', 'audio/x-pn-realaudio', 'audio/x-realaudio' ,'video/vnd.rn-realvideo', 'video/fli',
          'video/x-fli', 'audio/x-ms-wmv', 'video/avi', 'video/msvideo', 'video/m4v', 'audio/x-ms-wma',
          'application/octet-stream', 'application/x-url', 'text/url', 'text/x-url', 'application/vnd.rn-realmedia', 'video/webm',
          'audio/webm', 'audio/vnd.rn-realaudio', 'audio/x-pn-realaudio', 'audio/x-realaudio', 'audio/aiff', 'audio/x-aiff')

    YTDL_MSGS = (_("Problem retreiving content. Do you have up-to-date dependencies?"),
          _("Problem retreiving content. Content may be copyrighted or the link may be invalid."),
          _("Problem retrieving content. Content may have been truncated."))

    YTDL_WAIT_TAG = "[" + _("wait") + "]"

    progress_bar_total_steps = 200
    progress_bar_step_rate = 0
    volume_max = 60
    volume_normal_step = 40
    volume_critical_step = 49


# ***************************************
# # PLAYING STATE MACHINE
# ***************************************

    """self. play_state controls the playing sequence, it has the following values.
         I am not entirely sure the startign and ending states are required.
         - omx_closed - the omx process is not running, omx process can be initiated
         - omx_starting - omx process is running but is not yet able to receive commands
         - omx_playing - playing a track, commands can be sent
         - omx_ending - omx is doing its termination, commands cannot be sent
    """
    
    def init_play_state_machine(self):

        self._OMX_CLOSED = "omx_closed"
        self._OMX_STARTING = "omx_starting"
        self._OMX_PLAYING = "omx_playing"
        self._OMX_ENDING = "omx_ending"

        self._YTDL_CLOSED = "ytdl_closed"
        self._YTDL_STARTING = "ytdl_starting"
        self._YTDL_WORKING = "ytdl_working"
        self._YTDL_ENDING = "ytdl_ending"

        # what to do next signals
        self.break_required_signal=False         # signal to break out of Repeat or Playlist loop
        self.play_previous_track_signal = False
        self.play_next_track_signal = False

         # playing a track signals
        self.stop_required_signal=False
        self.play_state=self._OMX_CLOSED
        self.quit_sent_signal = False          # signal  that q has been sent
        self.paused=False

        # playing a track signals
        self.ytdl_state=self._YTDL_CLOSED
        self.quit_ytdl_sent_signal = False          # signal  that q has been sent

        # whether omxplayer dbus is connected
        self.dbus_connected = False

        self.start_track_index = None

        self.omx = None
        self.autolyrics = None


    # kick off the state machine by playing a track
    def play(self):
            #initialise all the state machine variables
        if  self.play_state==self._OMX_CLOSED and self.playlist.track_is_selected():
            self.iteration = 0                           # for debugging
            self.paused = False
            self.stop_required_signal=False     # signal that user has pressed stop
            self.quit_sent_signal = False          # signal  that q has been sent
            self.playing_location = self.playlist.selected_track_location
            self.play_state=self._OMX_STARTING
            self.dbus_connected = False
            self._cued = False

            #play the selelected track
            index = self.playlist.selected_track_index()
            self.display_selected_track(index)

            self.start_omx(self.playlist.selected_track_location)
            self.play_state_machine()

            self.set_play_button_state(1)


    def play_state_machine(self):
        # self.monitor ("******Iteration: " + str(self.iteration))
        self.iteration +=1
        if self.play_state == self._OMX_CLOSED:
            self.monitor("      State machine: " + self.play_state)
            self.what_next()
            return 
                
        elif self.play_state == self._OMX_STARTING:
            self.monitor("      State machine: " + self.play_state)
        # if omxplayer is playing the track change to play state
            if self.omx and self.omx.start_play_signal==True:
                self.monitor("            <start play signal received from omx")
                self.omx.start_play_signal=False
                self.play_state=self._OMX_PLAYING
                self.monitor("      State machine: omx_playing started")
                self.dbus_connected = self.omx.init_dbus_link()
                self.show_progress_bar()
                self.set_progress_bar()
                if self.media_is_video() and not self.options.forbid_windowed_mode:
                    self.create_vprogress_bar()
                    if self.dbus_connected:
                        self.omx.set_aspect_mode(OMXPlayer.AM_LETTERBOX)
                if self.options.cue_track_mode:
                    self.toggle_pause()
                if self.options.find_lyrics:
                    self.grab_lyrics()
            else:
                if self.ytdl_state == self._YTDL_CLOSED:
                    self.play_state=self._OMX_CLOSED
                    self.monitor("      youtube-dl failed, stopping omx state machine")
                else:
                    self.monitor("      OMXPlayer did not start yet.")
            self.root.after(350, self.play_state_machine)

        elif self.play_state == self._OMX_PLAYING :
            # service any queued stop signals
            if self.stop_required_signal==True :#or (self.omx and (self.omx.end_play_signal or self.omx.failed_play_signal)):
                self.monitor("      Service stop required signal")
                self.stop_omx()
                self.stop_required_signal=False
            else:
                # quit command has been sent or omxplayer reports it is terminating so change to ending state
                if self.quit_sent_signal == True or self.omx.end_play_signal== True or not self.omx.is_running():
                    if self.quit_sent_signal:
                        self.monitor("            quit sent signal received")
                        self.quit_sent_signal = False
                    if self.omx.end_play_signal:
                        self.monitor("            <end play signal received")
                        self.monitor("            <end detected at: " + str(self.omx.position))
                    self.play_state =self._OMX_ENDING
                    self.reset_progress_bar()
                    if self.media_is_video():
                        self.destroy_vprogress_bar()
                self.do_playing()
            self.root.after(350, self.play_state_machine)

        elif self.play_state == self._OMX_ENDING:
            self.monitor("      State machine: " + self.play_state)
            # if spawned process has closed can change to closed state
            self.monitor ("      State machine : is omx process running -  "  + str(self.omx.is_running()))
            if self.omx.is_running() ==False:
            #if self.omx.end_play_signal==True:    #this is not as safe as process has closed.
                self.monitor("            <omx process is dead")
                self.play_state = self._OMX_CLOSED
            self.dbus_connected = False
            self.do_ending()
            if self.autolyrics:
                self.autolyrics.destroy()
                self.autolyrics = None
            self.root.after(350, self.play_state_machine)

    # do things in each state
 
    def do_playing(self):
        # we are playing so just update time display
        # self.monitor("Position: " + str(self.omx.position))
        if self.paused == False:
            time_string = self.time_string(self.omx.position)
            if self.omx.timenf:
                time_string += "\n/ " + self.time_string(self.omx.timenf['duration'])
            self.display_time.set(time_string)
            if abs(self.omx.position - self.progress_bar_var.get()) > self.progress_bar_step_rate:
                self.set_progress_bar_step()
            if self.options.cue_track_mode and not self._cued and self.omx.timenf and self.omx.position >= self.omx.timenf['duration'] - 1:
                self.toggle_pause()
                self._cued = True
        else:
            self.display_time.set(_("Paused"))           

    def do_starting(self):
        self.display_time.set(_("Starting"))
        return

    def do_ending(self):
        # we are ending so just write End to the time display
        self.display_time.set(_("End"))
        self.hide_progress_bar()


    # respond to asynchrous user input and send signals if necessary
    def play_track(self):
        """ respond to user input to play a track, ignore it if already playing
              needs to start playing and not send a signal as it is this that triggers the state machine.
        """
        self.monitor(">play track received") 
        if self.play_state == self._OMX_CLOSED:
            self.start_track_index = self.playlist.selected_track_index()
            self.play()
        elif self.play_state == self._OMX_PLAYING and not (self.stop_required_signal or self.break_required_signal):
            self.toggle_pause()


    def play_track_by_index(self, track_index=0):
        if self.play_state == self._OMX_CLOSED:
             self.playlist.select(track_index)
             self.play_track()
             return
        elif (track_index == self.start_track_index 
                    and self.play_state == self._OMX_PLAYING):
            self.toggle_pause()
            return
        
        self.stop_track()
        def play_after():
            self.playlist.select(track_index)
            self.play_track()
        self.root.after(1200, play_after)


    def skip_to_next_track(self):
        # send signals to stop and then to play the next track
        if self.play_state == self._OMX_PLAYING:
            self.monitor(">skip  to next received") 
            self.monitor(">stop received for next track") 
            self.stop_required_signal=True
            self.play_next_track_signal=True
        

    def skip_to_previous_track(self):
        # send signals to stop and then to play the previous track
        if self.play_state == self._OMX_PLAYING:
            self.monitor(">skip  to previous received")
            self.monitor(">stop received for previous track") 
            self.stop_required_signal=True
            self.play_previous_track_signal=True


    def stop_track(self):
        # send signals to stop and then to break out of any repeat loop
        if self.play_state == self._OMX_PLAYING:
            self.monitor(">stop received")
            self.start_track_index=None
            self.stop_required_signal=True
            self.break_required_signal=True
            self.hide_progress_bar()
            self.set_play_button_state(0)


    def toggle_pause(self):
        """pause clicked Pauses or unpauses the track"""
        if self.play_state == self._OMX_PLAYING:
            self.send_command('p')
            if self.paused == False:
                self.paused=True
                self.set_play_button_state(0)
            else:
                if(self.options.cue_track_mode and self._cued):
                    self.stop_omx()
                self.paused=False
                self.set_play_button_state(1)


    def set_play_button_state(self, state):
        if state == 0:
            self.play_button['text'] = _('Play')
        elif state == 1:
            self.play_button['text'] = _('Pause')


    def volminusplus(self, event):
        if event.x < event.widget.winfo_width()/2:
            self.volminus()
        else:
            self.volplus()

    def volplus(self):
        self.send_command('+')

    def volminus(self):
        self.send_command('-')

    def time_string(self,secs):
        minu = int(secs/60)
        sec = secs-(minu*60)
        return str(minu)+":"+str(int(sec))


    def what_next(self):

        if self.break_required_signal==True:
            self.hide_progress_bar()
            self.monitor("What next, break_required so exit")
            self.set_play_button_state(0)
            def break_required_signal_false():
                self.break_required_signal=False
            self.root.after(650, break_required_signal_false)
            # fall out of the state machine
            return
        elif self.play_next_track_signal ==True:
        # called when state machine is in the omx_closed state in order to decide what to do next.
            self.monitor("What next, skip to next track")
            self.play_next_track_signal=False
            if self.options.mode=='shuffle':
                self.random_next_track()
                self.play()
            else:
                self.select_next_track()
                self.play()
            return
        elif self.play_previous_track_signal ==True:
            self.monitor("What next, skip to previous track")
            self.select_previous_track()
            self.play_previous_track_signal=False
            self.play()
            return
        elif self.options.mode=='single':
            self.monitor("What next, single track so exit")
            self.set_play_button_state(0)
            # fall out of the state machine
            return
        elif self.options.mode=='repeat':
            self.monitor("What next, Starting repeat track")
            self.play()
            return
        elif 'playlist' in self.options.mode:
            if not 'repeat' in self.options.mode and self.start_track_index == self.playlist.length() - 1: 
                self.stop_required_signal=True
                self.set_play_button_state(0)
                self.monitor("What next, reached end of playlist, so exit")
                return
            self.monitor("What next, Starting playlist track")
            self.select_next_track()
            self.play()
            return     
        elif self.options.mode=='shuffle':
            self.monitor("What next, Starting random track")
            self.random_next_track()
            self.play()
            return


# ***************************************
#   YTDL STATE MACHINE
# ***************************************


    def go_ytdl(self, url, playlist=False):
        self.quit_ytdl_sent_signal = False
        if self.ytdl_state in (self._YTDL_CLOSED, self._YTDL_ENDING):
            self.ytdl_state=self._YTDL_STARTING
            self.ytdl.start_signal=True
          
        if not playlist:
            self.ytdl.retrieve_media_url(url, self.options.youtube_media_format)
        else:
            self.ytdl.retrieve_youtube_playlist(url)
        if self.ytdl_state==self._YTDL_STARTING:
            self.ytdl_state_machine()


    def ytdl_state_machine(self):
        if self.ytdl_state == self._YTDL_CLOSED:
            self.monitor("      Ytdl state machine: " + self.ytdl_state)
            return 
                
        elif self.ytdl_state == self._YTDL_STARTING:
            self.monitor("      Ytdl state machine: " + self.ytdl_state)
            if self.ytdl.start_signal==True:
                self.monitor("            <start play signal received from youtube-dl")
                self.ytdl.start_signal=False
                self.ytdl_state=self._YTDL_WORKING
                self.monitor("      Ytdl state machine: "+self.ytdl_state)
            self.root.after(500, self.ytdl_state_machine)

        elif self.ytdl_state == self._YTDL_WORKING:            
            try:
                if len(self.ytdl.finished_processes):
                    for url  in self.ytdl.finished_processes:
                        process = self.ytdl.finished_processes[url]
                        self.treat_ytdl_result(url, process[1])
                    self.ytdl.finished_processes = {}

                if not self.ytdl.is_running():
                    self.ytdl_state = self._YTDL_ENDING
            except Exception:
                log.logException()
                sys.exc_clear()
            self.root.after(500, self.ytdl_state_machine)

        elif self.ytdl_state == self._YTDL_ENDING:
            self.ytdl.reset_processes()
            self.monitor("      Ytdl state machine: " + self.ytdl_state)
            self.monitor("      Ytdl state machine: is process running - "  + str(self.ytdl.is_running()))
            self.ytdl_state = self._YTDL_CLOSED
            self.root.after(500, self.ytdl_state_machine)


    def treat_ytdl_result(self, url, res):
        if res[0] == 1:
            try:
                result = json.loads(res[1])
            except Exception:
                log.logException()
                sys.exc_clear()
                self.remove_waiting_track(url)
                return
            if 'entries' in result:
                self.treat_youtube_playlist_data(result)
            else:
                self.treat_video_data(url, result)
        else:
            self.remove_waiting_track(url)
            if self.play_state==self._OMX_STARTING:
                self.quit_sent_signal = True
            self.display_selected_track_title.set(self.YTDL_MSGS[res[1]])
            self.root.after(3000, lambda: self.display_selected_track())
        return


    def treat_video_data(self, url, data):
        media_url = self._treat_video_data(data, data['extractor'])
        if not media_url and self.options.youtube_video_quality == "small":  
            media_url = self._treat_video_data(data, data['extractor'], "medium")
        if not media_url: 
            media_url = data['url']
        tracks = self.playlist.waiting_tracks()
        if tracks:
            for track in tracks:
                if track[1][0] == url:
                    self.playlist.replace(track[0],[media_url, data['title'],track[1][PlayList.LOCATION_BACKUP]])
                    if self.play_state == self._OMX_STARTING:
                        self.start_omx(media_url,skip_ytdl_check=True)
                    self.refresh_playlist_display()
                    self.playlist.select(track[0])
                    break

    def treat_youtube_playlist_data(self, data):
        for entry in data['entries']:
            media_url = self._treat_video_data(entry, data['extractor'])
            if not media_url and self.options.youtube_video_quality == "small":
                media_url = self._treat_video_data(entry, data['extractor'], "medium")
            if not media_url:
                media_url = entry['url']
            self.playlist.append([media_url,entry['title'],'',''])
        self.playlist.select(self.playlist.length() - len(data['entries']))
        self.refresh_playlist_display()
        self.root.after(3000, lambda: self.display_selected_track())

    def _treat_video_data(self, data, extractor, force_quality=False):
        media_url = None
        media_format = self.options.youtube_media_format
        quality = self.options.youtube_video_quality if not force_quality else force_quality
        if extractor != "youtube" or (media_format == "mp4" and quality == "high"):
            media_url = data['url']
        else:
            preference = -100
            for format in data['formats']:
                if ((media_format == format['ext'] == "m4a" and
                                ((quality == "high" and format['abr'] == 256) or 
                                (quality in ("medium", "small") and format['abr'] == 128))) or 
                                (media_format == format['ext'] == "mp4" and
                                quality == format['format_note'])):
                    if 'preference' in format and format['preference'] > preference:
                        preference = format['preference']
                        media_url = format['url']
                    else:
                        media_url = format['url']
        return media_url


    def ytdl_update_messages_loop(self):
        if not self.ytdl.updating_signal:
            if self.ytdl.updated_signal:
                tkMessageBox.showinfo("",_("youtube-dl has been updated."))
            elif self.ytdl.update_failed_signal:
                tkMessageBox.showinfo("",_("Failed to update youtube-dl."))
        else:
            if self.ytdl.password_requested_signal and not self.ytdl.has_password_signal:
                password = tkSimpleDialog.askstring("", _("youtube-dl needs to be updated.\nPlease inform your password."), parent=self.root, show="*")
                if password: self.ytdl.set_password(password)
                else: return
                    
            self.root.after(500, self.ytdl_update_messages_loop)


# ***************************************
# WRAPPER FOR JBAITER'S PYOMXPLAYER
# ***************************************

    def start_omx(self, track, skip_ytdl_check=False):
        """ Loads and plays the track"""
        if not skip_ytdl_check and self.ytdl.whether_to_use_youtube_dl(track):
            self.go_ytdl(track)
            index = self.playlist.selected_track_index()
            track = self.playlist.selected_track()
            track = (track[0], self.YTDL_WAIT_TAG+track[1])
            self.playlist.replace(index, track)
            self.playlist.select(index)               
            self.refresh_playlist_display()
            return
        track= "'"+ track.replace("'","'\\''") + "'"
        opts= (self.options.omx_user_options + " " + self.options.omx_audio_output + " " +
                                                        self.options.omx_subtitles + " --vol " + str(self.get_mB()))
        if self.media_is_video():
            if not self.options.forbid_windowed_mode and not self.options.full_screen and '--win' not in opts:
                mc = self.RE_COORDS.match(self.options.windowed_mode_coords)
                mg = self.RE_RESOLUTION.match(self.options.windowed_mode_resolution)
                if mc and mg:
                    w, h, x, y = [int(v) for v in mg.groups()+mc.groups()]
                    opts += ' --win %d,%d,%d,%d' % (x, y, x+w, y+h)

            if not '--aspect-mode' in opts:
                opts += ' --aspect-mode letterbox'
            
            if not '--no-osd' in opts:
                opts += ' --no-osd'

        self.monitor('starting omxplayer with args: "%s"' % (opts,))

	self.omx = OMXPlayer(track, args=opts, start_playback=True)

        self.monitor("            >Play: " + track + " with " + opts)


    def stop_omx(self):
        if self.play_state ==  self._OMX_PLAYING:
            self.monitor("            >Send stop to omx") 
            self.omx.stop()
        else:
            self.monitor ("            !>stop not sent to OMX because track not playing")

    
    def send_command(self,command):

        if command in "+=-pz12jkionms" and self.play_state ==  self._OMX_PLAYING:
            self.monitor("            >Send Command: "+command)
            self.omx.send_command(command)
            if self.dbus_connected and command in ('+' , '=', '-'):
                sleep(0.1)
                try:
                    self.set_volume_bar_step(int(self.vol2dB(self.omx.volume())+self.volume_normal_step))
                except Exception:
                    log.logException()
                    sys.exc_clear()
                    self.monitor("Failed to set volume bar step")
            return True
        else:
            if command in "+=":
                self.set_volume_bar_step(self.volume_var.get() + 3)
            elif command == '-':
                self.set_volume_bar_step(self.volume_var.get() - 3)         
            self.monitor ("            !>Send command: illegal control or track not playing")
            return False

        
    def send_special(self,command):
        if self.play_state ==  self._OMX_PLAYING:
            self.monitor("            >Send special") 
            self.omx.send_command(command)
            return True
        else:
            self.monitor ("            !>Send special: track not playing")
            return False



# ***************************************
# INIT
# ***************************************

    def __init__(self, options):

        # initialise options class and do initial reading/creation of options
        self.options=options
        if self.options.debug:
            log.setLogFile(self.options.log_file)
            log.enableLogging()
            self.monitor('started logging to file "%s"' % (self.options.log_file,))
        else:
            log.disableLogging()

        #initialise the play state machine
        self.init_play_state_machine()

        # start and configure ytdl object
        self.ytdl = Ytdl(self.options, 
                         lambda: tkMessageBox.showinfo("",_("youtube-dl binary is not in the path configured in the Options, please check your configuration")))

        #create the internal playlist
        self.playlist = PlayList(self.YTDL_WAIT_TAG)

        #root is the Tkinter root widget
        self.root = tk.Tk()
        self.root.title("GUI for OMXPlayer")

        self.root.configure(background='grey')
        # width, height, xoffset, yoffset
        self.root.geometry(self.options.geometry)
        self.root.resizable(True,True)

        OMXPlayer.set_omx_location(self.options.omx_location)

        # bind some display fields
        self.filename = tk.StringVar()
        self.display_selected_track_title = tk.StringVar()
        self.display_time = tk.StringVar()
        self.volume_var = tk.IntVar()
        self.progress_bar_var = tk.IntVar()

        self.root.bind("<Configure>", self.save_geometry)
        #Keys
        self.root.bind("<Left>", self.key_left)
        self.root.bind("<Right>", self.key_right)
        self.root.bind("<Up>", self.key_up)
        self.root.bind("<Down>", self.key_down)
        self.root.bind("<Shift-Right>", self.key_shiftright)  #forward 600
        self.root.bind("<Shift-Left>", self.key_shiftleft)  #back 600
        self.root.bind("<Control-Right>", self.key_ctrlright)  #next track      
        self.root.bind("<Control-Left>", self.key_ctrlleft)  #previous track
        self.root.bind("<Control-v>", self.add_url)
        self.root.bind("<Escape>", self.key_escape)
        self.root.bind("<F11>", self.toggle_full_screen)
        self.root.bind("<Control_L>", self.vwindow_start_resize)
        self.root.bind("<KeyRelease-Control_L>", self.vwindow_stop_resize)

        self.root.bind("<Key>", self.key_pressed)

        self.style = Style()
        self.style.theme_use("alt")


# define menu
        menubar = Menu(self.root)
        filemenu = Menu(menubar, tearoff=0, background="grey", foreground="black")
        menubar.add_cascade(label=_('Track'), menu = filemenu)
        filemenu.add_command(label=_('Add'), command = self.add_track)
        filemenu.add_command(label=_('Add Dir'), command = self.add_dir)
        filemenu.add_command(label=_('Add Dirs'), command = self.add_dirs)
        filemenu.add_command(label=_('Add URL'), command = self.add_url)
        filemenu.add_command(label=_('Youtube search'), command = self.youtube_search)
        filemenu.add_command(label=_('Remove'), command = self.remove_track)
        filemenu.add_command(label=_('Edit'), command = self.edit_track)
        
        listmenu = Menu(menubar, tearoff=0, background="grey", foreground="black")
        menubar.add_cascade(label=_('Playlists'), menu = listmenu)
        listmenu.add_command(label=_('Open playlist'), command = self.open_list_dialog)
        listmenu.add_command(label=_('Save playlist'), command = self.save_list)
        listmenu.add_command(label=_('Load Youtube playlist'), command = self.load_youtube_playlist)
        listmenu.add_command(label=_('Clear'), command = self.clear_list)

        omxmenu = Menu(menubar, tearoff=0, background="grey", foreground="black")
        menubar.add_cascade(label='OMX', menu = omxmenu)
        omxmenu.add_command(label=_('Track Info'), command = self.show_omx_track_info)

        optionsmenu = Menu(menubar, tearoff=0, background="grey", foreground="black")
        menubar.add_cascade(label=_('Options'), menu = optionsmenu)
        optionsmenu.add_command(label=_('Edit'), command = self.edit_options)

        helpmenu = Menu(menubar, tearoff=0, background="grey", foreground="black")
        menubar.add_cascade(label=_('Help'), menu = helpmenu)
        helpmenu.add_command(label=_('Help'), command = self.show_help)
        helpmenu.add_command(label=_('About'), command = self.about)
         
        self.root.config(menu=menubar)
        
        # define buttons 
        # add track button
        Button(self.root, width = 5, height = 1, text=_('Add'),
                              foreground='black', command = self.add_track, 
                              background="light grey").grid(row=0, column=1, rowspan=2, sticky=N+W+E+S)
        # add dir button        
        Button(self.root, width = 5, height = 1, text=_('Add Dir'),
                              foreground='black', command = self.add_dir, 
                              background="light grey").grid(row=0, column=2, rowspan=2, sticky=N+W+E+S)
        # add url button
        Button(self.root, width = 5, height = 1, text=_('Add URL'),
                              foreground='black', command = self.add_url, 
                              background="light grey").grid(row=0, column=3, rowspan=2, sticky=N+W+E+S)

        # open list button        
        Button(self.root, width = 5, height = 1, text=_('Open List'),
                              foreground='black', command = self.open_list_dialog, 
                              background="light grey").grid(row=0, column=4, rowspan=2, sticky=N+W+E+S)
        # save list button
        Button(self.root, width = 5, height = 1, text =_('Save List'),
                              foreground='black', command = self.save_list, 
                              background='light grey').grid(row=0, column=5, rowspan=2, sticky=N+W+E+S)
        # clear list button;
        Button(self.root, width = 5, height = 1, text =_('Clear List'),
                              foreground='black', command = self.clear_list, 
                              background='light grey').grid(row=0, column=6, rowspan=2, sticky=N+W+E+S)
        # play/pause button
        self.play_button = Button(self.root, width = 5, height = 1, text=_('Play'),
                              foreground='black', command = self.play_track, 
                              background="light grey")
        self.play_button.grid(row=7, column=1, sticky=N+W+E+S)
        # stop track button       
        Button(self.root, width = 5, height = 1, text=_('Stop'),
                              foreground='black', command = self.stop_track, 
                              background="light grey").grid(row=7, column=2, sticky=N+W+E+S)
        # previous track button
        Button(self.root, width = 5, height = 1, text=_('Previous'),
                              foreground='black', command = self.skip_to_previous_track, 
                              background="light grey").grid(row=7, column=3, sticky=N+W+E+S)
        # next track button
        Button(self.root, width = 5, height = 1, text=_('Next'),
                              foreground='black', command = self.skip_to_next_track, 
                              background="light grey").grid(row=7, column=4, sticky=N+W+E+S)

        # vol button
        minusplus_button = Button(self.root, width = 5, height = 1, text = '-  Vol +',
                              foreground='black', background='light grey')
        minusplus_button.grid(row=7, column=5, sticky=N+W+E+S)#, sticky=E)
        minusplus_button.bind("<ButtonRelease-1>", self.volminusplus)

        # define display of file that is selected
        Label(self.root, font=('Comic Sans', 10),
                              fg = 'black', wraplength = 400, height = 2,
                              textvariable=self.display_selected_track_title,
                              background="grey").grid(row=2, column=1, columnspan=6, sticky=N+W+E)

        # define time/status display for selected track
        Label(self.root, font=('Comic Sans', 9),
                              fg = 'black', wraplength = 100,
                              textvariable=self.display_time,
                              background="grey").grid(row=2, column=6, columnspan=1, sticky=N+W+E+S)

# define display of playlist
        self.track_titles_display = Listbox(self.root, background="white", height = 15,
                               foreground="black", takefocus=0)
        self.track_titles_display.grid(row=3, column=1, columnspan=7,rowspan=3, sticky=N+S+E+W)
        self.track_titles_display.bind("<ButtonRelease-1>", self.select_track)
        self.track_titles_display.bind("<Delete>", self.remove_track)
        self.track_titles_display.bind("<Return>", self.key_return)
        self.track_titles_display.bind("<Double-1>", self.select_and_play)

# scrollbar for displaylist
        scrollbar = Scrollbar(self.root, command=self.track_titles_display.yview, orient=tk.VERTICAL)
        scrollbar.grid(row = 3, column=6, rowspan=3, sticky=N+S+E)
        self.track_titles_display.config(yscrollcommand=scrollbar.set)

# progress bar
        self.style.configure("progressbar.Horizontal.TProgressbar", foreground='medium blue', background='medium blue')
        self.progress_bar = Progressbar(orient=HORIZONTAL, length=self.progress_bar_total_steps, mode='determinate', 
                                                                        maximum=self.progress_bar_total_steps, variable=self.progress_bar_var, 
                                                                        style="progressbar.Horizontal.TProgressbar")
        self.progress_bar.grid(row=6, column=1, columnspan=6, sticky=N+W+E+S)
        self.progress_bar.grid_remove()
        self.progress_bar.bind("<ButtonRelease-1>", self.set_track_position)
        self.progress_bar_var.set(0)

# volume bar, volume meter is 0.0 - 16.0, being normal volume 1.0
        self.style.configure("volumebar.Horizontal.TProgressbar", foreground='cornflower blue', background='cornflower blue')
        self.volume_bar = Progressbar(orient=HORIZONTAL, length=self.volume_max, mode='determinate',
                                                                        maximum=self.volume_max, variable=self.volume_var, 
                                                                        style="volumebar.Horizontal.TProgressbar")
        self.volume_bar.grid(row=7, column=6, stick=W+E)
        self.volume_bar.bind("<ButtonRelease-1>", self.set_volume_bar)
        self.volume_var.set(self.volume_normal_step)

# configure grid
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_columnconfigure(3, weight=1)
        self.root.grid_columnconfigure(4, weight=1)
        self.root.grid_columnconfigure(5, weight=1)
        self.root.grid_columnconfigure(6, weight=1)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_rowconfigure(3, weight=1, minsize=40)
        self.root.grid_rowconfigure(4, weight=0)
        self.root.grid_rowconfigure(5, weight=0)
        self.root.grid_rowconfigure(6, weight=0)
        self.root.grid_rowconfigure(7, weight=0)

# if files were passed in the command line, add them to the playlist
        for f in sys.argv[1:]:
            if os.path.isfile(f) and self.is_file_supported(f):
                self.file = f
                self.file_pieces = self.file.split("/")
                self.playlist.append([self.file, self.file_pieces[-1],'',''])
                self.track_titles_display.insert(END, self.file_pieces[-1])
            elif os.path.isfile(f) and  f[f.rfind('.')+1:]=="csv":
                self._open_list(f)
        
        if self.playlist.length() > 0 and self.options.autoplay:
            if self.options.mode=='shuffle':
                self.random_next_track()
            else:
                self.select_track(False)
            self.play_track()

        self.dnd = DnD(self.root)
        self.dnd.bindtarget(self.root, 'text/uri-list', '<Drop>', self.add_drag_drop)    
        
        if self.options.ytdl_update:
            self.ytdl.check_for_update()
            self.ytdl_update_messages_loop()

    def shutdown(self):
        self.root.quit()
        self.ytdl.quit()
        if self.omx is not None:
            self.omx.stop()
            self.omx.kill()


# ***************************************
# MISCELLANEOUS
# ***************************************

    def edit_options(self):
        """edit the options then read them from file"""
        eo = OptionsDialog(self.root, self.options.options_file,_('Edit Options'))
        self.options.read(self.options.options_file)
        self.ytdl.set_options(self.options)
        OMXPlayer.set_omx_location(self.options.omx_location)

    def show_help (self):
        tkMessageBox.showinfo(_("Help"),
          _("To control playing, type a key\np - pause/play\nspacebar - pause/play\nq - quit\n")
        + _("+ - increase volume\n- - decrease volume\nz - tv show info\n1 - reduce speed\no - forward a chapter\n")
        + _("2 - increase speed\nj - previous audio index\nk - next audio index\ni - back a chapter\nn - previous subtitle index\n")
        + _("m - next subtitle index\ns - toggle subtitles\n>cursor - seek forward 30\n<cursor - seek back 30\n")
        + _("SHIFT >cursor - seek forward 600\nSHIFT <cursor - seek back 600\nCTRL >cursor - next track\nCTRL <cursor - previous track\n")
        + _("F11 - toggle full screen/windowed mode\n\nFor more help, consult the 'Operation' section of the README file"))
  

    def about (self):
        tkMessageBox.showinfo(_("About"),_("GUI for omxplayer using jbaiter's pyomxplayer wrapper\n")
                   +((_("Version dated: %s \nAuthor:\n    Ken Thompson  - KenT2\n")) % datestring)
                   +_("Contributors:\n    eysispeisi\n    heniotierra\n    krugg\n    popiazaza"))

    def monitor(self,text):
        if self.options.debug:
            log.debug(text)

# Key Press callbacks

    def key_right(self,event):
        self.send_special('\x1b\x5b\x43')
        self.monitor("Seek forward 30")

    def key_left(self,event):
        self.send_special('\x1b\x5b\x44')
        self.monitor("Seek back 30")

    def key_shiftright(self,event):
        self.send_special('\x1b\x5b\x42')
        self.monitor("Seek forward 600")

    def key_shiftleft(self,event):
        self.send_special('\x1b\x5b\x41')
        self.monitor("Seek back 600")

    def key_ctrlright(self,event):
        self.skip_to_next_track()

    def key_ctrlleft(self,event):
        self.skip_to_previous_track()

    def key_up(self,event):
        self.select_previous_track()
        
    def key_down(self,event):
        self.select_next_track()

    def key_escape(self,event):
        self.stop_track()
        
    def key_return(self,event):
        self.stop_track()
        def play_aux():
            self.start_track_index = self.playlist.selected_track_index()
            self.play()
        self.root.after(1500, play_aux)

    def key_pressed(self,event):
        char = event.char
        if char=='':
            return
        elif char in ('p', ' ', '.'):
            self.play_track()
            return
        elif char=='q':
            self.stop_track()
            return
        else:
            self.send_command(char)
            return

    def grab_lyrics(self):
        track = self.playlist.selected_track()
        track_title = track[1]
        if ('title' in self.omx.misc and 
                    self.omx.misc['title'] and 
                    'artist' in self.omx.misc and 
                    self.omx.misc['artist']):
            track_title = self.omx.misc['artist'] + '-' + self.omx.misc['title']

        self.autolyrics = AutoLyrics(self.root, self.options.autolyrics_coords, self._save_autolyrics_coords, track_title)

    def save_geometry(self, *sec):
        self.options.geometry = self.root.geometry()
        self.options.save_state()

    def _save_autolyrics_coords(self, *event):
        x = self.autolyrics.winfo_x()
        y = self.autolyrics.winfo_y()
        self.options.autolyrics_coords = ("+" if x>=0 else "-")+str(x)+("+" if y>=0 else "-")+str(y)

    def set_option(self, option, value):
        boolean = ["0", "1"]
        allowed_options_values = {
            "omx_user_options": "str",
            "omx_location": "str",
            "ytdl_location": "str",
            "omx_audio_output": ["hdmi","local","auto","alsa"],
            "mode": ["single", "repeat","playlist","repeat playlist", "shuffle"],
            "debug": ["on", "off"],
            "youtube_media_format": ["mp4", "m4a"],
            "download_media_url_upon": ["add","play"],
            "youtube_video_quality": ["small", "medium","high"],
            "windowed_mode_coords": self.RE_COORDS,
            "windowed_mode_resolution": self.RE_RESOLUTION,
            "autolyrics_coords": self.RE_COORDS,
            "forbid_windowed_mode": boolean,
            "cue_track_mode": boolean,
            "autoplay": boolean,
            "find_lyrics": boolean,
            "full_screen": boolean
        }
        try:
            allowed_option_values = allowed_options_values[option]
        except KeyError, er:
            raise KeyError("Option " + option + " is invalid")
        option_type = str(type(allowed_option_values))
        if (allowed_option_values == "str" or 
                            ("list" in option_type and value in allowed_option_values) or
                            ("SRE_Pattern" in option_type and allowed_option_values.match(value) != None)):
            if allowed_option_values == boolean:
                value = int(value)
            setattr(self.options, option, value)
            self.options.save_state()
            self.options.read(self.options.options_file)
            if option == "ytdl_location": 
                self.ytld.set_options(self.options)
            elif option=="omx_location": 
                OMXPlayer.set_omx_location(self.options.omx_location)
        else: raise AttributeError("Option value does not match an expected value or pattern")


# ******************************************
# PROGRESS BAR CALLBACKS
# ******************************************

    def set_progress_bar(self):
        try:
            self.progress_bar_step_rate = self.omx.timenf['duration']/self.progress_bar_total_steps
        except Exception:
            log.logException()
            sys.exc_clear()
            return False
        

    def show_progress_bar(self):
        self.progress_bar.grid()

    def hide_progress_bar(self):
        self.progress_bar.grid_remove()

    def reset_progress_bar(self):
        self.progress_bar_var.set(0)

    def set_track_position(self,event):
        if not self.dbus_connected: return
        new_track_position = self.progress_bar_step_rate * ((event.x * self.progress_bar_total_steps)/event.widget.winfo_width())
        try:
            self.omx.set_position(new_track_position)
        except Exception:
            log.logException()
            sys.exc_clear()
            self.monitor("Failed to set track position")
        self.focus_root()

    def set_progress_bar_step(self):
        try:
            self.progress_bar_var.set(int((self.omx.position * self.progress_bar_total_steps)/self.omx.timenf['duration']))
        except Exception:
            log.logException()
            sys.exc_clear()
            self.monitor('Error trying to set progress bar step')


# ******************************************
# VIDEO WINDOW FUNCTIONS
# ******************************************

    def create_vprogress_bar(self):
        screenres = self.get_screen_res()
        vsize = self.omx.video['dimensions']

        self.vprogress_bar_window = Toplevel(master=self.root)
        self.vprogress_bar_frame = Frame(self.vprogress_bar_window, bg="black")
        self.vprogress_bar_frame.pack(fill=BOTH,side=TOP, expand=True)
        
        #defne response to main window closing
        self.vprogress_bar_window.protocol ("WM_DELETE_WINDOW", self.vprogress_bar_window.destroy) 
        
        self.vprogress_bar_window.video_height = screenres[1]
        self.vprogress_bar_window.video_width = int(vsize[0] * (screenres[1] / float(vsize[1])))
        self.vprogress_bar_window.resizing = 0
        
        if self.vprogress_bar_window.video_width > screenres[0] + 20:
            self.vprogress_bar_window.video_width = screenres[0]
            self.vprogress_bar_window.video_height = int(vsize[1] * (screenres[0] / float(vsize[0])))

        if self.options.full_screen:
            geometry = "%dx%d-0-0" % screenres
        else:
            coords = self.options.windowed_mode_coords
            coords_m = self.RE_COORDS.match(coords)
            if coords_m is None or int(coords_m.group(1))>screenres[0] or int(coords_m.group(2))>screenres[1]:
                coords = "+200+200"
            geometry = self.options.windowed_mode_resolution + coords

        self.vprogress_bar_window.geometry(geometry)
        self.vprogress_bar_window.overrideredirect(1)

        self.vprogress_bar_window.resizable(True,True)
        self.vprogress_bar = Progressbar(self.vprogress_bar_window, orient=HORIZONTAL, length=self.progress_bar_total_steps, mode='determinate', 
                                                                        maximum=self.progress_bar_total_steps, variable=self.progress_bar_var,
                                                                        style="progressbar.Horizontal.TProgressbar")

        self.vprogress_bar.pack(in_=self.vprogress_bar_frame, fill=BOTH,side=BOTTOM)
        self.root.update()

        self.vprogress_bar.bind("<ButtonRelease-1>", self.set_track_position)
        self.vprogress_bar_window.bind("<Configure>", self.move_video)
        self.vprogress_bar_window.bind("<ButtonPress-1>", self.vwindow_start_move)
        self.vprogress_bar_window.bind("<ButtonRelease-1>", self.vwindow_stop_move)
        self.vprogress_bar_window.bind("<B1-Motion>", self.vwindow_motion)
        self.vprogress_bar_window.bind("<Double-Button-1>", self.toggle_full_screen)
        self.vprogress_bar_window.bind("<Motion>", self.vwindow_show_and_hide)
        self.vprogress_bar_window.bind("<Double-1>", self.restore_window)
        
        # Resize widget, placed in the lower right corner over the progress bar, not ideal.
        self.vprogress_grip = Sizegrip(self.vprogress_bar_window)
        self.vprogress_grip.place(relx=1.0, rely=1.0, anchor="se")
        self.vprogress_grip.bind("<ButtonPress-1>", self.vwindow_start_resize)
        self.vprogress_grip.bind("<ButtonRelease-1>", self.vwindow_stop_resize)
        self.vprogress_grip.bind("<B1-Motion>", self.vwindow_motion)

        self.vprogress_bar_window.protocol ("WM_TAKE_FOCUS", self.focus_root)
        self.vwindow_show_and_hide()
        
    def vwindow_start_move(self, event):
        if self.options.full_screen == 1: return
        self.vprogress_bar_window.x = event.x
        self.vprogress_bar_window.y = event.y

    def vwindow_stop_move(self, event):
        if self.options.full_screen == 1: return
        self.vprogress_bar_window.x = None
        self.vprogress_bar_window.y = None
        self.save_video_window_coordinates()

    def vwindow_motion(self, event):
        if self.options.full_screen == 1:
            return
        try:
            deltax = (event.x - self.vprogress_bar_window.x)/2
            deltay = (event.y - self.vprogress_bar_window.y)/2
        except (TypeError, AttributeError):
            log.logException()
            sys.exc_clear()
            return
        if not self.vprogress_bar_window.resizing:
            x = self.vprogress_bar_window.winfo_x() + deltax
            y = self.vprogress_bar_window.winfo_y() + deltay
            self.vprogress_bar_window.geometry("+%s+%s" % (x, y))
        else:
            w = self.vprogress_bar_window.winfo_width() + deltax
            h = self.vprogress_bar_window.winfo_height() + deltay
            try:
                self.vprogress_bar_window.geometry("%sx%s" % (w, h))
            except Exception:
                log.logException()
                sys.exc_clear()
                self.options.full_screen = 1
                self.toggle_full_screen()
        self.vwindow_show_and_hide()

    def vwindow_start_resize(self,event):
        if (not self.media_is_video() or 
          self.options.full_screen == 1 or 
          not self.vprogress_bar_window): 
            return
        self.vprogress_bar_window.resizing = 1

    def vwindow_stop_resize(self,event):
        if (not self.media_is_video() or 
          self.options.full_screen == 1 or 
          not self.vprogress_bar_window): 
            return
        self.vprogress_bar_window.resizing = 0
        self.save_video_window_coordinates()

    def vwindow_show_and_hide(self, *event):
        self.vprogress_bar.lift(self.vprogress_bar_frame)
        if not self.options.full_screen:
            self.vprogress_grip.lift(self.vprogress_bar)
        self.move_video(pbar=True)
        if not hasattr(self, '_vwindow_show_and_hide_flag'):
            self._vwindow_show_and_hide_flag = None
        if self._vwindow_show_and_hide_flag is None:
            self._vwindow_show_and_hide_flag = self.root.after(3000, self.vwindow_hide)
        else:
            # refresh timer
            self.root.after_cancel(self._vwindow_show_and_hide_flag)
            self._vwindow_show_and_hide_flag = self.root.after(3000, self.vwindow_hide)

    def vwindow_hide(self):
        if self.play_state == self._OMX_PLAYING:
            self._vwindow_show_and_hide_flag = None
            self.vprogress_bar.lower(self.vprogress_bar_frame)
            self.vprogress_grip.lower(self.vprogress_bar_frame)
            self.move_video(pbar=False)

    def set_full_screen(self,*event):
        if not self.dbus_connected: return
        screenres = self.get_screen_res()
        try:
            self.omx.set_video_geometry(0, 0, screenres[0], screenres[1])
            self.vprogress_grip.lower(self.vprogress_bar_frame)
        except Exception, e:
            self.monitor('      [!] set_full_screen failed')
            self.monitor(e)

    def toggle_full_screen(self,*event):
        hasvbw = hasattr(self, 'vprogress_bar_window')
        if (not self.dbus_connected
            or self.options.forbid_windowed_mode
            or not self.media_is_video()
            or not hasvbw
            or (hasvbw and not self.vprogress_bar_window)):
            return
        screenres = self.get_screen_res()
        if self.options.full_screen == 1: 
            self.options.full_screen = 0
            width, height = (480, 360)
            vsize_m = self.RE_RESOLUTION.match(self.options.windowed_mode_resolution)
            if vsize_m:
                width, height = [int(i) for i in vsize_m.groups()]
            coords = self.options.windowed_mode_coords
            coords_m = self.RE_COORDS.match(coords)
            if coords_m is None or int(coords_m.group(1))>screenres[0] or int(coords_m.group(2))>screenres[1]:
                coords = "+200+200"
            geometry = "%dx%d%s" % (width, height, coords)
            self.vprogress_bar_window.geometry(geometry)
        else:
            self.options.full_screen = 1
            self.save_video_window_coordinates()
            geometry = "%dx%d+%d+%d" % ( screenres[0], screenres[1], 0, 0)
            self.vprogress_bar_window.geometry(geometry)
            self.set_full_screen()
            self.vprogress_grip.lower(self.vprogress_bar_frame)
        self.vwindow_show_and_hide()
        self.focus_root()

    def move_video(self,event=None, pbar=True):
        if not self.dbus_connected:
            return
        if not self.options.full_screen:
            w = self.vprogress_bar_window.winfo_width()
            h = self.vprogress_bar_window.winfo_height()
            x1 = self.vprogress_bar_window.winfo_x()
            y1 = self.vprogress_bar_window.winfo_y()
        else:
            w, h= self.get_screen_res()
            x1 = y1 = 0
        x2 = w+x1
        y2 = h+y1
            
        if pbar:
            y2 -= self.vprogress_bar.winfo_height()
        try:
            self.omx.set_video_geometry(x1, y1, x2, y2)
        except Exception, e:
                self.monitor('      [!] move_video failed')
                self.monitor(e)
        self.focus_root()

    def destroy_vprogress_bar(self):
        try:
            if self.options.full_screen == 0:
                self.save_video_window_coordinates()
            self.vprogress_bar_window.destroy()
            self.vprogress_bar_window = None
        except Exception:
            log.logException()
            sys.exc_clear()
            self.monitor("Failed trying to destroy video window: video window nonexistent.") 
    
    def get_screen_res(self):
        return (screen_width(), screen_height())

    def media_is_video(self):
        return hasattr(self,"omx") and hasattr(self.omx, "video") and len(self.omx.video) > 0

    def restore_window(self, *event):
        self.root.update()
        self.root.deiconify()
        
    def focus_root(self, *event):
        self.root.focus()

    def save_video_window_coordinates(self):
        x = self.vprogress_bar_window.winfo_x()
        y = self.vprogress_bar_window.winfo_y()
        h = self.vprogress_bar_window.winfo_height()
        w = self.vprogress_bar_window.winfo_width()
        self.options.windowed_mode_coords = ("+" if x>=0 else "-")+str(x)+("+" if y>=0 else "-")+str(y)
        self.options.windowed_mode_resolution = "%dx%d" % (w, h)
        self.monitor('Saving windowed geometry: "%s%s"' % (self.options.windowed_mode_resolution,self.options.windowed_mode_coords))


# ***************************************
# VOLUME BAR CALLBACKS
# ***************************************

    def set_volume_bar(self, event):
        # new volume ranges from 0 - 60
        new_volume = (event.x * self.volume_max)/self.volume_bar.winfo_width()
        self.set_volume_bar_step(new_volume)
        self.set_volume()

    def set_volume_bar_step(self, step):
        if step > self.volume_max: 
            step = self.volume_max
        elif step <= 0: 
            step = 0
        if step > self.volume_critical_step:
            self.style.configure("volumebar.Horizontal.TProgressbar", foreground='red', background='red')
        elif step <= self.volume_critical_step and self.volume_var.get() > self.volume_critical_step:
            self.style.configure("volumebar.Horizontal.TProgressbar", foreground='cornflower blue', background='cornflower blue')
            
        self.volume_var.set(step)

    def set_volume(self):
        if not self.dbus_connected: return
        try:
            self.omx.volume(self.mB2vol(self.get_mB()))
        except Exception:
            log.logException()
            sys.exc_clear()
            return False

    def get_mB(self): 
        return (self.volume_var.get() - self.volume_normal_step) * 100

    def vol2dB(self, volume):
        return (2000.0 * log10(volume)) / 100
        
    def mB2vol(self, mB):
        return pow(10, mB / 2000.0)


# ***************************************
# DISPLAY TRACKS
# ***************************************

    def display_selected_track(self,index=None):
        index = index if index != None else self.start_track_index
        if self.playlist.track_is_selected():
            self.track_titles_display.activate(index)
            self.display_selected_track_title.set(self.playlist.selected_track()[PlayList.TITLE])
        else:
            self.display_selected_track_title.set("")

    def blank_selected_track(self):
            self.display_selected_track_title.set("")

    def refresh_playlist_display(self):
        self.track_titles_display.delete(0,self.track_titles_display.size())
        for index in range(self.playlist.length()):
            self.playlist.select(index)
            self.track_titles_display.insert(END, self.playlist.selected_track()[PlayList.TITLE])


# ***************************************
# TRACKS AND PLAYLISTS  CALLBACKS
# ***************************************

    def is_file_supported(self, f):
        return from_file(f, mime=True) in self._SUPPORTED_MIME_TYPES

    def add_drag_drop(self, action, actions, type, win, X, Y, x, y, data):
        data = self.dnd.tcl_list_to_python_list(data)
        for item in data:
            if item.startswith('http'):
                self._add_url(item)
            elif os.path.isfile(item):
                if item.endswith('.csv'):
                    self._open_list(item)
                else:
                    self._add_files([item,])
            elif os.path.isdir(item):
                self.ajoute(item, False)

    def add_track(self, path=None):
        """
        Opens a dialog box to open files,
        then stores the tracks in the playlist.
        """
        # get the filez
        if path:
            filez = path
        elif self.options.initial_track_dir == '':
            if self.options.last_track_dir != '':
                filez = tkFileDialog.askopenfilenames(initialdir=self.options.last_track_dir,parent=self.root,title=_('Choose the file(s)'))
            else:
                filez = tkFileDialog.askopenfilenames(parent=self.root,title=_('Choose the file(s)'))
            
        else:
            filez = tkFileDialog.askopenfilenames(initialdir=self.options.initial_track_dir,parent=self.root,title=_('Choose the file(s)'))

        filez = self.root.tk.splitlist(filez)

        if filez:
            self.options.last_track_dir = filez[0][:filez[0].rindex('/')]
        else: 
            return

        self._add_files(filez)


    def _add_files(self, filez):
        for f in filez:
            if not os.path.isfile(f) or not self.is_file_supported(f):
                continue
            self.file = f
            self.file_pieces = self.file.split("/")
            self.playlist.append([self.file, self.file_pieces[-1],'',''])
            self.track_titles_display.insert(END, self.file_pieces[-1])

        # and set the selected track
        if len(filez)>1:
            index = self.playlist.length() - len(filez)
        else:
            index = self.playlist.length() - 1
        self.playlist.select(index)


    def get_dir(self):
        if self.options.initial_track_dir:
            d = tkFileDialog.askdirectory(initialdir=self.options.initial_track_dir,title=_("Choose a directory"))
        elif self.options.last_track_dir:
            d = tkFileDialog.askdirectory(initialdir=self.options.last_track_dir,title=_("Choose a directory"))
        else:
            d = tkFileDialog.askdirectory(parent=self.root,title=_("Choose a directory"))
        return d
 

    def ajoute(self,dir,recursive):
        for f in os.listdir(dir):
            try:
                n=os.path.join(dir,f)
                if recursive and os.path.isdir(n):
                    self.ajoute(n,True)
                if os.path.isfile(n) and self.is_file_supported(n):
                    self.filename.set(n)
                    self.file = self.filename.get()
                    self.file_pieces = self.file.split("/")
                    self.playlist.append([self.file, self.file_pieces[-1],'',''])
                    self.track_titles_display.insert(END, self.file_pieces[-1])
            except Exception:
                log.logException()
                sys.exc_clear()
                return


    def add_dir(self):
        dirname = self.get_dir()
        if dirname:
            self.options.last_track_dir = dirname
            self.ajoute(dirname,False)


    def add_dirs(self):
        dirname = self.get_dir()
        if dirname:
            self.options.last_track_dir = dirname
            self.ajoute(dirname,True)


    def add_url(self, *event):
        cb = ""
        try:
             cb = self.root.clipboard_get()
        except: pass
        d = EditTrackDialog(self.root,_("Add URL"),
                                _("Title"), "",
                                _("Location"), "" if cb == "" or not cb.startswith("http") else cb)
        if d.result == None:
            return
        name = d.result[0]
        url = d.result[1]
        self._add_url(url, name)

    def _add_url(self, url, name=''):
        if not url:
            return
        if not name:
            name = url
        if self.ytdl.is_running(url): return
        if self.options.download_media_url_upon == "add" and self.ytdl.whether_to_use_youtube_dl(url):
            self.go_ytdl(url)
            name = self.YTDL_WAIT_TAG + name

        self.playlist.append([url, name, url])
        self.track_titles_display.insert(END, name)
        self.playlist.select(self.playlist.length()-1)

    def youtube_search(self):
        def add_url_from_search(link):
            if self.ytdl.is_running(link): return
            if "list=" in link:
                self.go_ytdl(link,playlist=True)
                self.display_selected_track_title.set(_("Wait. Loading playlist content..."))
                return

            result = [link,'','']
            self.go_ytdl(link)
            result[1] = self.YTDL_WAIT_TAG + result[0]
            self.playlist.append(result)
            self.track_titles_display.insert(END, result[1])
        YoutubeSearchDialog(self.root, add_url_from_search)


    def remove_track(self,*event):
        if  self.playlist.length()>0 and self.playlist.track_is_selected():
            if self.playlist.selected_track()[1][:6] == self.YTDL_WAIT_TAG and self.ytdl_state==self._YTDL_WORKING:
                # tell ytdl_state_machine to stop
                self.quit_ytdl_sent_signal = True
            index= self.playlist.selected_track_index()
            self.track_titles_display.delete(index,index)
            self.playlist.remove(index)
            self.blank_selected_track()
            self.display_time.set("")


    def edit_track(self):
        if self.playlist.track_is_selected():
            index= self.playlist.selected_track_index()
            d = EditTrackDialog(self.root,_("Edit Track"),
                                _("Title"), self.playlist.selected_track_title,
                                _("Location"), self.playlist.selected_track_location)
            do_ytdl = False

            if d.result and d.result[1] != '':            
                if (self.options.download_media_url_upon == "add" and self.playlist.selected_track()[1][:6] != self.YTDL_WAIT_TAG and 
                                                                self.ytdl.whether_to_use_youtube_dl(d.result[1])):
                    do_ytdl = True
                    d.result[0] = self.YTDL_WAIT_TAG + d.result[0]
                d.result = (d.result[1],d.result[0])
                self.playlist.replace(index, d.result)
                self.playlist.select(index)
                self.refresh_playlist_display()
                if do_ytdl:
                    self.go_ytdl(d.result[0])


    def select_track(self, event):
        """
        user clicks on a track in the display list so try and select it
        """
        # needs forgiving int for possible tkinter upgrade
        if self.playlist.length()>0:
            index = 0
            if event:
                sel = event.widget.curselection()
                if sel:
                    index=int(sel[0]) if event else 0
            self.playlist.select(index)


    def select_and_play(self, event=None):
        if not hasattr(self, 'select_and_play_pending'):
            self.select_and_play_pending = False

        if self.play_state == self._OMX_CLOSED:
            self.select_and_play_pending = False
            self.play_track()
            self.track_titles_display.bind("<Double-1>", self.select_and_play)
        elif not self.select_and_play_pending and self.playing_location != self.playlist.selected_track_location:
            self.track_titles_display.unbind("<Double-1>")
            self.select_and_play_pending = True
            self.stop_track()
        if self.select_and_play_pending:
            self.root.after(700, self.select_and_play)


    def select_next_track(self):
        if self.playlist.length()>0:
            if self.start_track_index == None and self.play_state == self._OMX_CLOSED: 
                index = self.start_track_index = self.playlist.selected_track_index()
            elif self.start_track_index == self.playlist.length() - 1:
                index = self.start_track_index = 0
            else:
                index = self.start_track_index = self.start_track_index + 1
            self.playlist.select(index)
            self.display_selected_track(index)


    def random_next_track(self):
        if self.playlist.length()>0:
            index = self.start_track_index = randint(0,self.playlist.length()-1)
            self.playlist.select(index)
            self.display_selected_track(index)


    def select_previous_track(self):
        if self.playlist.length()>0:
            if self.start_track_index == None: 
                index = self.start_track_index = self.playlist.selected_track_index()
            elif self.start_track_index == 0:
                index = self.start_track_index = self.playlist.length() - 1
            else:
                index = self.start_track_index = self.start_track_index - 1
            self.playlist.select(index)               
            self.display_selected_track(index)


    def remove_waiting_track(self, url):
        tracks = self.playlist.waiting_tracks()
        if tracks:
            for track in tracks:
                if track[1][0] == url:
                    self.track_titles_display.delete(track[0],track[0])
                    self.playlist.remove(track[0])
                    self.blank_selected_track() 

      
# ***************************************
# PLAYLISTS
# ***************************************

    def open_list_dialog(self):
        """
        opens a saved playlist
        playlists are stored as textfiles each record being "path","title"
        """
        if self.options.initial_playlist_dir=='':
            self.filename.set(tkFileDialog.askopenfilename(defaultextension = ".csv",
                                                filetypes = [('csv files', '.csv')],
                                                multiple=False))

        else:
            self.filename.set(tkFileDialog.askopenfilename(initialdir=self.options.initial_playlist_dir,
                                                defaultextension = ".csv",
                                                filetypes = [('csv files', '.csv')],
                                                multiple=False))
        filename = self.filename.get()
        if filename=="":
            return
        self._open_list(filename)


    def _open_list(self, filename):
        #self.options.last_playlist_dir = ''
        ifile  = open(filename, 'rb')
        pl=csv.reader(ifile)
        self.playlist.clear()
        self.track_titles_display.delete(0,self.track_titles_display.size())
        for pl_row in pl:
            if len(pl_row) != 0:
                if 'http' in pl_row[0]:
                    self._add_url(pl_row[0],pl_row[1])
                    continue
                self.playlist.append([pl_row[0],pl_row[1],'',''])
                self.track_titles_display.insert(END, pl_row[1])
        ifile.close()
        self.playlist.select(0)
        return


    def clear_list(self):
        if tkMessageBox.askokcancel(_("Clear Playlist"),_("Clear Playlist")):
            self.track_titles_display.delete(0,self.track_titles_display.size())
            self.playlist.clear()
            self.blank_selected_track()
            self.display_time.set("")


    def load_youtube_playlist(self):
        d = LoadYtPlaylistDialog(self.root)
        if not d.result or not "list=" in d.result:
            return
        else:
            self.go_ytdl(d.result,playlist=True)
            self.display_selected_track_title.set(_("Wait. Loading playlist content..."))

     
    def save_list(self):
        """ save a playlist """
        self.filename.set(tkFileDialog.asksaveasfilename(
                defaultextension = ".csv",
                filetypes = [('csv files', '.csv')]))
        filename = self.filename.get()
        if filename=="":
            return
        ofile  = open(filename, "wb")
        for idx in range(self.playlist.length()):
            self.playlist.select(idx)
            item = self.playlist.selected_track()[PlayList.LOCATION]
            ofile.write ('"' + (item if not 'http' in item else self.playlist.selected_track()[PlayList.LOCATION_BACKUP]) + '","' + self.playlist.selected_track()[PlayList.TITLE]+'"\n')
        ofile.close()
        return

    
    def show_omx_track_info(self):
        try:
            tkMessageBox.showinfo(_("Track Information"), self.playlist.selected_track()[PlayList.LOCATION]  +"\n\n"+ 
                                            _("Video: ") + str(self.omx.video) + "\n" +
                                            _("Audio: ") + str(self.omx.audio) + "\n" +
                                            _("Time: ") + str(self.omx.timenf) + "\n" +
                                            _("Misc: ") + str(self.omx.misc))
        except: return


# *************************************
# OPTIONS DIALOG CLASS
# ************************************

class OptionsDialog(tkSimpleDialog.Dialog):

    def __init__(self, parent, options_file, title=None, ):
        # store subclass attributes
        self.options_file=options_file
        # init the super class
        tkSimpleDialog.Dialog.__init__(self, parent, title)


    def body(self, master):
        config=ConfigParser.ConfigParser()
        config.read(self.options_file)

        self._config = config
        self.geometry_var = config.get('config','geometry',0)
        self.full_screen_var = config.get('config','full_screen',0)
        self.windowed_mode_coords_var = config.get('config','windowed_mode_coords',0)
        self.windowed_mode_resolution_var = config.get('config','windowed_mode_resolution',0)
        self.autolyrics_coords_var = config.get('config','autolyrics_coords',0)
        self.ltracks_var = config.get('config','ltracks',0)

        Label(master, text=_("Audio Output:")).grid(row=0, sticky=W)
        self.audio_var=StringVar()
        self.audio_var.set(config.get('config','audio',0))
        rb_hdmi=Radiobutton(master, text=_("HDMI"), variable=self.audio_var, value="hdmi")
        rb_hdmi.grid(row=1,column=0,sticky=W)
        rb_local=Radiobutton(master, text=_("Local"), variable=self.audio_var,value="local")
        rb_local.grid(row=2,column=0,sticky=W)
        rb_auto=Radiobutton(master, text=_("Auto"), variable=self.audio_var,value="auto")
        rb_auto.grid(row=3,column=0,sticky=W)
        rb_auto=Radiobutton(master, text="ALSA", variable=self.audio_var,value="alsa")
        rb_auto.grid(row=4,column=0,sticky=W)

        Label(master, text="").grid(row=9, sticky=W)
        Label(master, text=_("Mode:")).grid(row=10, sticky=W)
        self.mode_var=StringVar()
        self.mode_var.set(config.get('config','mode',0))
        rb_single=Radiobutton(master, text=_("Single"), variable=self.mode_var, value="single")
        rb_single.grid(row=11,column=0,sticky=W)
        rb_repeat=Radiobutton(master, text=_("Repeat"), variable=self.mode_var,value="repeat")
        rb_repeat.grid(row=12,column=0,sticky=W)
        rb_playlist=Radiobutton(master, text=_("Playlist"), variable=self.mode_var,value="playlist")
        rb_playlist.grid(row=13,column=0,sticky=W)
        rb_rplaylist=Radiobutton(master, text=_("Repeat playlist"), variable=self.mode_var,value="repeat playlist")
        rb_rplaylist.grid(row=14,column=0,sticky=W)
        rb_shuffle=Radiobutton(master, text=_("Shuffle"), variable=self.mode_var,value="shuffle")
        rb_shuffle.grid(row=15,column=0,sticky=W)

        Label(master, text="").grid(row=16, sticky=W)
        Label(master, text=_("Download from Youtube:")).grid(row=17, sticky=W)
        self.youtube_media_format_var=StringVar()
        self.youtube_media_format_var.set(config.get('config','youtube_media_format',0))
        rb_video=Radiobutton(master, text=_("Video and audio"), variable=self.youtube_media_format_var, value="mp4")
        rb_video.grid(row=18,column=0,sticky=W)
        rb_audio=Radiobutton(master, text=_("Audio only"), variable=self.youtube_media_format_var, value="m4a")
        rb_audio.grid(row=19,column=0,sticky=W)

        Label(master, text=_("Youtube media quality:")).grid(row=20, sticky=W)
        self.youtube_video_quality_var=StringVar()
        self.youtube_video_quality_var.set(config.get('config','youtube_video_quality',0))
        om_quality = OptionMenu(master, self.youtube_video_quality_var, "high", "medium", "small")
        om_quality.grid(row=21, sticky=W)
        
        Label(master, text=_("Initial directory for tracks:")).grid(row=0, column=2, sticky=W)
        self.e_tracks = Entry(master)
        self.e_tracks.grid(row=1, column=2)
        self.e_tracks.insert(0,config.get('config','tracks',0))
        Label(master, text=_("Inital directory for playlists:")).grid(row=2, column=2, sticky=W)
        self.e_playlists = Entry(master)
        self.e_playlists.grid(row=3, column=2)
        self.e_playlists.insert(0,config.get('config','playlists',0))
    
    
        Label(master, text=_("OMXPlayer location:")).grid(row=10, column=2, sticky=W)
        self.e_omx_location = Entry(master)
        self.e_omx_location.grid(row=11, column=2)
        self.e_omx_location.insert(0,config.get('config','omx_location',0))
        Label(master, text=_("OMXPlayer options:")).grid(row=12, column=2, sticky=W)
        self.e_omx_options = Entry(master)
        self.e_omx_options.grid(row=13, column=2)
        self.e_omx_options.insert(0,config.get('config','omx_options',0))

        self.subtitles_var = StringVar()
        self.cb_subtitles = Checkbutton(master,text=_("Subtitles"),variable=self.subtitles_var, onvalue="on",offvalue="off")
        self.cb_subtitles.grid(row=14, column=2, sticky = W)
        if config.get('config','subtitles',0)=="on":
            self.cb_subtitles.select()
        else:
            self.cb_subtitles.deselect()

        Label(master, text="").grid(row=16, column=2, sticky=W)
        Label(master, text=_("youtube-dl location:")).grid(row=17, column=2, sticky=W)
        self.e_ytdl_location = Entry(master)
        self.e_ytdl_location.grid(row=18, column=2)
        self.e_ytdl_location.insert(0,config.get('config','ytdl_location',0))
        Label(master, text="").grid(row=19, column=2, sticky=W)

        Label(master, text=_("Download actual media URL:")).grid(row=20, column=2, sticky=W)
        self.download_media_url_upon_var=StringVar()
        self.download_media_url_upon_var.set(_("when adding URL") if config.get('config','download_media_url_upon',0) == "add" else _("when playing URL"))
        om_download_media = OptionMenu(master, self.download_media_url_upon_var, _("when adding URL"), _("when playing URL"))
        om_download_media.grid(row=21, column=2, sticky=W)

        
        Label(master, text="").grid(row=22, sticky=W) 
        Label(master, text=_("Interface language:")).grid(row=23, column=0, sticky=W)
        self.lang_var=StringVar()
        self.lang_var.set(config.get('config','lang',0))
        om_lang = OptionMenu(master, self.lang_var, 'en', 'es' , 'fr', 'pt', 'ro')
        om_lang.grid(row=23, column=2, sticky=W)
        

        self.forbid_windowed_mode_var = IntVar()
        self.forbid_windowed_mode_var.set(int(config.get('config','forbid_windowed_mode',0)))
        self.cb_forbid = Checkbutton(master,text=_("Forbid windowed mode"),variable=self.forbid_windowed_mode_var, onvalue=1,offvalue=0)

        Label(master, text="").grid(row=51, sticky=W)
        self.cb_forbid.grid(row=52, column=2, sticky = W)
        if self.forbid_windowed_mode_var.get()==1:
            self.cb_forbid.select()
        else:
            self.cb_forbid.deselect()

        self.cue_track_mode_var = IntVar()
        self.cue_track_mode_var.set(int(config.get('config','cue_track_mode',0)))
        self.cb_cue = Checkbutton(master,text=_("Begin/End track paused"),variable=self.cue_track_mode_var, onvalue=1,offvalue=0)

        Label(master, text="").grid(row=51, sticky=W)
        self.cb_cue.grid(row=52, column=0, sticky = W)
        if self.cue_track_mode_var.get()==1:
            self.cb_cue.select()
        else:
            self.cb_cue.deselect()

        self.autoplay_var = IntVar()
        self.autoplay_var.set(int(config.get('config','autoplay',0)))
        self.cb_autoplay = Checkbutton(master,text=_("Autoplay on start up"), variable=self.autoplay_var, onvalue=1,offvalue=0)
        self.cb_autoplay.grid(row=60,columnspan=2, sticky = W)
        if self.autoplay_var.get()==1:
            self.cb_autoplay.select()
        else:
            self.cb_autoplay.deselect()

        self.ytdl_update_var = IntVar()
        self.ytdl_update_var.set(int(config.get('config','ytdl_update',0)))
        self.cb_ytdl_update = Checkbutton(master, text=_("Keep youtube-dl up-to-date"), variable=self.ytdl_update_var, onvalue=1, offvalue=0)
        self.cb_ytdl_update.grid(row=60,column=2, sticky = W)
        if self.ytdl_update_var.get()==1:
            self.cb_ytdl_update.select()
        else:
            self.cb_ytdl_update.deselect()

        self.find_lyrics_var = IntVar()
        self.cb_find_lyrics = Checkbutton(master,text=_("Find lyrics"),variable=self.find_lyrics_var, onvalue=1,offvalue=0)
        self.cb_find_lyrics.grid(row=61,column=0, sticky = W)
        if int(config.get('config','find_lyrics',0)) == 1:
            self.cb_find_lyrics.select()
        else:
            self.cb_find_lyrics.deselect()	    

        self.debug_var = StringVar()
        self.cb_debug = Checkbutton(master,text=_("Debug"),variable=self.debug_var, onvalue='on',offvalue='off')
        self.cb_debug.grid(row=61,column=2, sticky = W)
        if config.get('config','debug',0)=='on':
            self.cb_debug.select()
        else:
            self.cb_debug.deselect()

        return None    # no initial focus

    def apply(self):
        if self.debug_var.get():
            log.setLevel(logging.DEBUG)
        else:
            log.disableLogging()
        self.save_options()
        return True

    def save_options(self):
        """ save the output of the options edit dialog to file"""
        config=self._config
        
        if (self.lang_var.get() != config.get('config','lang',0)):
            tkMessageBox.showinfo("",_("Restart TBOplayer to change language"))
            
        config.set('config','audio',self.audio_var.get())
        config.set('config','subtitles',self.subtitles_var.get())
        config.set('config','mode',self.mode_var.get())
        config.set('config','playlists',self.e_playlists.get())
        config.set('config','tracks',self.e_tracks.get())
        config.set('config','ltracks',self.ltracks_var)
        config.set('config','omx_options',self.e_omx_options.get())
        config.set('config','debug',self.debug_var.get())
        config.set('config','youtube_media_format',self.youtube_media_format_var.get())
        config.set('config','omx_location',self.e_omx_location.get())
        config.set('config','ytdl_location',self.e_ytdl_location.get())
        config.set('config','download_media_url_upon',"add" if self.download_media_url_upon_var.get() == _("when adding URL") else "play")
        config.set('config','youtube_video_quality',self.youtube_video_quality_var.get())
        config.set('config','geometry',self.geometry_var)
        config.set('config','full_screen',self.full_screen_var)
        config.set('config','windowed_mode_coords',self.windowed_mode_coords_var)
        config.set('config','windowed_mode_resolution',self.windowed_mode_resolution_var)
        config.set('config','forbid_windowed_mode',self.forbid_windowed_mode_var.get())
        config.set('config','cue_track_mode',self.cue_track_mode_var.get())
        config.set('config','autoplay',self.autoplay_var.get())
        config.set('config','find_lyrics',self.find_lyrics_var.get())
        config.set('config','autolyrics_coords',self.autolyrics_coords_var)
        config.set('config','lang',self.lang_var.get())
        config.set('config','ytdl_update',self.ytdl_update_var.get())
        
        
        with open(self.options_file, 'wb') as configfile:
            config.write(configfile)
            configfile.close()


# *************************************
# EDIT TRACK DIALOG CLASS
# ************************************

class EditTrackDialog(tkSimpleDialog.Dialog):

    def __init__(self, parent, title=None, *args):
        #save the extra args to instance variables
        self.label_location=args[0]
        self.default_location=args[1]       
        self.label_title=args[2]
        self.default_title=args[3]
        #and call the base class _init_which uses the args in body
        tkSimpleDialog.Dialog.__init__(self, parent, title)


    def body(self, master):
        Label(master, text=self.label_location).grid(row=0)
        Label(master, text=self.label_title).grid(row=1)

        self.field1 = Entry(master)
        self.field2 = Entry(master)

        self.field1.grid(row=0, column=1)
        self.field2.grid(row=1, column=1)

        self.field1.insert(0,self.default_location)
        self.field2.insert(0,self.default_title)

        return self.field2 # initial focus on title


    def apply(self):
        first = self.field1.get()
        second = self.field2.get()
        self.result = [first, second,'','']
        return self.result



# *************************************
# LOAD YOUTUBE PLAYLIST DIALOG
# ************************************

class LoadYtPlaylistDialog(tkSimpleDialog.Dialog):

    def __init__(self, parent): 
        #save the extra args to instance variables
        self.label_url="URL"
        self.default_url=""
        #and call the base class _init_which uses the args in body
        tkSimpleDialog.Dialog.__init__(self, parent, _("Load Youtube playlist"))


    def body(self, master):
        Label(master, text=self.label_url).grid(row=0)

        self.field1 = Entry(master)

        self.field1.grid(row=0, column=1)

        self.field1.insert(0,self.default_url)

        return self.field1 # initial focus on title


    def apply(self):
        self.result = self.field1.get()

        return self.result


from urllib import quote_plus
import requests

class YoutubeSearchDialog(Toplevel):

    def __init__(self, parent, add_url_function):
        # store subclass attributes
        self.result_cells = []
        self.add_url = add_url_function
        # init the super class
        Toplevel.__init__(self, parent)
        self.transient(parent)
        self.title(_("Youtube search"))
        self.geometry("390x322")
        self.resizable(False,False)
        master = self
        self.field1 = Entry(master)
        self.field1.grid(row=0, column=0)
        self.field1.focus_set()

        Button(master, width = 5, height = 1, text = _('Search!'),
                              foreground='black', command = self.search, 
                              background='light grey').grid(row=0, column=1)
        Button(master, width = 5, height = 1, text = _('Clear'),
                              foreground='black', command = self.clear_search, 
                              background='light grey').grid(row=1, column=1)

        self.page_lbl = _("Page: ")
        self.page_var = tk.StringVar()
        self.page_var.set(self.page_lbl)

        Label(master, font=('Comic Sans', 9),
                              fg = 'black', wraplength = 100,
                              textvariable=self.page_var,
                              background="light grey").grid(row=0, column=2)
        page_btn = Button(master, width = 5, height = 1, text = '1 | 2 | 3',
                              foreground='black',background='light grey')
        page_btn.grid(row=1, column=2)
        page_btn.bind("<ButtonRelease-1>", self.search_page)
        self.frame = VerticalScrolledFrame(master)
        self.frame.grid(row=2,column=0,columnspan=3,rowspan=6)
        self.frame.configure_scrolling()

    def search(self, page = 0):
        fvalue = self.field1.get()
        if fvalue == "": return
        self.clear_search()
        self.page_var.set(self.page_lbl + str(page + 1))
        pages = [ "SAD", "SBT", "SCj" ]
        terms = fvalue.decode('latin1').encode('utf8')
        searchurl = ("https://www.youtube.com/results?search_query=" + quote_plus(terms) + 
                              "&sp=" + pages[page] + "qAwA%253D")
        pagesrc = requests.get(searchurl).text
        parser = YtsearchParser()
        parser.feed(pagesrc)
        self.show_result(parser.result)

    def search_page(self, event):
        wwidth = event.widget.winfo_width()
        if event.x < wwidth/3:
            page = 0
        elif event.x < 2*(wwidth/3):
            page = 1
        else:
            page = 2
        self.search(page)

    def show_result(self, result):
        for r in result:
            if r[0] != "" and r[1] != "":
                self.result_cells.append(YtresultCell(self.frame.interior,self.add_url,r[0],r[1]))
        return

    def clear_search(self):
        for r in self.result_cells:
            r.destroy()
        self.result_cells = []
        self.frame.canvas.yview_moveto(0)
        return

    def apply(self):
        return


class YtresultCell(Frame):

    def __init__(self, parent, add_url_function, link, title):
        Frame.__init__(self, parent)
        self.grid(sticky=W)
        self.video_name = tk.StringVar()
        self.video_link = tk.StringVar()
        self.video_link.set("https://www.youtube.com" + link)
        self.add_url = add_url_function
        try: 
            self.video_name.set(title)
        except: pass

        self.create_widgets()

    def create_widgets(self):
        if "list=" in self.video_link.get():
            self.video_name.set("(playlist) " + self.video_name.get())
        Label(self, font=('Comic Sans', 10),
                              foreground='black', wraplength = 300, height = 2,
                              textvariable=self.video_name,
                              background="grey").grid(row = 0, column=0, columnspan=2, sticky=W)
        Button(self, width = 5, height = 1, text=_('Add'),
                              foreground='black', command = self.add_link, 
                              background="light grey").grid(row = 0, column=2, sticky=W)

    def add_link(self,*event):
        self.add_url(self.video_link.get())


class AutoLyrics(Toplevel):
    _ARTIST_TITLE_REXP = re.compile(r"([\w\d.&\\/'` ]*)[-:|~]([\w\d.&\\/'` ]*)", re.UNICODE)

    def __init__(self, parent, coords, update_coords_func, track_title):
        Toplevel.__init__(self, parent, background="#d9d9d9")
        try:
            self.geometry(coords)
        except: 
            pass
        self.transient(parent)

        self.bind('<Configure>', update_coords_func)

        self.title(_("Lyrics Finder"))
        self.resizable(False,False)

        self.lyrics_var = tk.StringVar()

        self.lyrics_var.set(_("Trying to grab lyrics from the web..."))

        frame = VerticalScrolledFrame(self)
        frame.grid()
        frame.configure_scrolling()

        Label(frame.interior, font=('Comic Sans', 11),
                              foreground = 'black', wraplength = 378,
                              textvariable=self.lyrics_var,
                              background="#d9d9d9").grid(column=0, row=0, columnspan=3, sticky=E+W+N+S)
        
        search_result = self._ARTIST_TITLE_REXP.search(track_title)
        if not search_result:
            self.nope()
            return
        title_data = search_result.groups()

        artist = title_data[0].strip(' ')
        title = title_data[1].strip(' ')

        self.get_lyrics(artist, title)

    def get_lyrics(self, artist, title):
        self._background_thread = Thread(target=self._get_lyrics, args=[artist, title])
        self._background_thread.start()

    def _get_lyrics(self, artist, title):
        try:
            api_url = 'http://lyrics.wikia.com/api.php'
            api_response =  requests.get(api_url, params={
                'fmt': 'realjson',
                'func': 'getSong',
                'artist': artist,
                'title': title,
                'no_pager': True
            }).json()

            if not api_response or not 'page_id' in api_response:
                raise Exception()
            
            pagesrc = requests.get(api_response['url']).text
            parser = LyricWikiParser()
            parser.feed(pagesrc)
            lyrics = (api_response["artist"] + ": " + api_response["song"] +
                            "\n               -- - -- - -- - -- - -- - -- - -- - -- - --               \n\n" +
                            parser.result)
            self.lyrics_var.set(lyrics)
        except:
            self.nope()

    def nope(self):
        self.lyrics_var.set(_("Unable to retrieve lyrics for this track."))
        self.after(3000, lambda: self.destroy())


# ***************************************
# MAIN
# ***************************************

if __name__ == "__main__":
    datestring="11 Ago 2018"

    dbusif_tboplayer = None
    try:
        bus = dbus.SessionBus()
        bus_object = bus.get_object(TBOPLAYER_DBUS_OBJECT, TBOPLAYER_DBUS_PATH, introspect = False)
        dbusif_tboplayer = dbus.Interface(bus_object, TBOPLAYER_DBUS_INTERFACE)
    except: pass

    if dbusif_tboplayer is None:
        tk.CallWrapper = ExceptionCatcher
        bplayer = TBOPlayer(options)
        TBOPlayerDBusInterface(bplayer)
        gobject_loop = gobject.MainLoop()
        def refresh_player():
            try:
                bplayer.root.update()
                gobject.timeout_add(66, refresh_player)
            except: 
                gobject_loop.quit()
                bplayer.shutdown()
        def start_gobject():
            gobject_loop.run()
        gobject.timeout_add(66, refresh_player)
        bplayer.root.after(65, start_gobject)
        bplayer.root.mainloop()
    elif len(sys.argv[1:]) > 0:
        dbusif_tboplayer.openFiles(sys.argv[1:])
    exit()
