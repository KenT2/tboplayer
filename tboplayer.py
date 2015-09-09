#!/usr/bin/env python

"""
A GUI interface using jbaiter's pyomxplayer to control omxplayer


INSTALLATION
*** Instructions for installation on the official Debian Wheezy Raspbian image
  *  requires the latest bug fixed version of omxplayer which you can get by doing apt-get update then apt-get upgrade or compile from https://github.com/popcornmix/omxplayer/
  *  install pexpect by following the instructions at www.noah.org/wiki/pexpect
  *  pyomxplayer is currently included inline in the code as I have made some modifications to jbaiter's version, his original can be seen at https://github.com/jbaiter/pyomxplayer
  *  download tboplayer.py into a directory
  *  type python tboplayer.py from a terminal opened in the directory within which tboplayer.py is stored
  *  If you want to be able to watch videos from online services like Youtube, then you must have up-to-date youtube-dl installed on your system, as well as avconv 10 or later
  *  developed on raspbian wheezy with python 2.7
  *  2015 version developed on ubuntu mate 15.04 and mint 17.2
  *  
  *  see README.md for better instructions
  *  
  
OPERATION
Menus
====
 Track - Track - add tracks (for selecting multiple tracks, hold ctrl when clicking) or directories or URLs, edit or remove tracks from the current playlist
 Playlist - save the current playlist or open a saved one or load youtube playlist
 OMX - display the track information for the last played track (needs to be enabled in options)
 Options -
    Audio Output - play sound to hdmi or local output, auto does not send an audio option to omxplayer.
    Mode - play the Single selected track, Repeat the single track, rotate around the Playlist starting from the selected track, or play at Random.
    Download from Youtube - defines whether to download video and audio or audio only from Youtube (other online video services will always be asked for mp4)
    OMXPlayer location - path to omxplayer binary
    OMXplayer options - add your own (no validation so be careful)
    Download from Youtube - defines whether to download video and audio or audio only from Youtube (other online video services will always be asked for "video and audio")
    Download actual media URL [when] - defines when to extract the actual media from the given URL, either upon adding the URL or when playing it
    youtube-dl location - path to youtube-dl binary
    youtube-dl transcoder - prefer to use either avconv or ffmpeg when using youtube-dl for extracting data from online supported services
    Debug - prints some debug text to the command line
    Generate Track Information - parses the output of omxplayer, disabled by default as it may cause problems with some tracks.

A track is selected using a single click of the mouse, playing is started by pressing the Play button or the . key

During playing of a track a slightly modified set of omxplayer commands can be used from the keyboard but there must be FOCUS on TBOPlayer.
A list  of comands is provided in the help menu. Note: some of the commands are not implemented by omxplayer.

If you have problems playing a track try it from the command line with omxplayer -o hdmi file or omxplayer -o local file

TODO (maybe)
--------
Scroll display list with up/down cursor key and select with Return
sort out black border around some videos
gapless playback, by running two instances of pyomxplayer
read and write m3u and pls playlists
Fit to every screen size (also resizeable)



PROBLEMS
---------------
I think I might have fixed this but two tracks may play at the same time if you use the controls quickly, you may need to SSH in form another computer and use top -upi and k to kill the omxplayer.bin

"""

# pyomxplayer from https://github.com/jbaiter/pyomxplayer
# modified by KenT

# ********************************
# PYOMXPLAYER
# ********************************

import pexpect
import re
import string

from threading import Thread
from time import sleep


class OMXPlayer(object):

    _FILEPROP_REXP = re.compile(r".*audio streams (\d+) video streams (\d+) chapters (\d+) subtitles (\d+).*")
    _VIDEOPROP_REXP = re.compile(r".*Video codec ([\w-]+) width (\d+) height (\d+) profile (\d+) fps ([\d.]+).*")
    _AUDIOPROP_REXP = re.compile(r"Audio codec (\w+) channels (\d+) samplerate (\d+) bitspersample (\d+).*")
    _STATUS_REXP = re.compile(r"M:\s*([\d.]+).*")
    _DONE_REXP = re.compile(r"have a nice day.*")
    
    _LAUNCH_CMD = ''
    _LAUNCH_ARGS_FORMAT = ' -s %s %s'
    _PAUSE_CMD = 'p'
    _TOGGLE_SUB_CMD = 's'
    _QUIT_CMD = 'q'
    
    paused = False
    playing_location = ''
    # KRT turn subtitles off as a command option is used
    subtitles_visible = False

    #****** KenT added argument to control dictionary generation
    def __init__(self, mediafile, args=None, start_playback=False, do_dict=False):
        if not args:
            args = ""
        #******* KenT signals to tell the gui playing has started and ended
        self.start_play_signal = False
        self.end_play_signal = False

        cmd = self._LAUNCH_CMD % (mediafile, args)
        self._process = pexpect.spawn(cmd)
        print "        cmd: " + cmd
        # fout= file('logfile.txt','w')
        # self._process.logfile_send = sys.stdout
        
        # ******* KenT dictionary generation moved to a function so it can be omitted.
        if do_dict:
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
        
        while True:
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
                    self.position = float(self._process.match.group(1)) / 1000000
            except Exception:
                break
            sleep(0.05)


    def make_dict(self):
        self.video = dict()
        self.audio = dict()

        #******* KenT add exception handling to make code resilient.
        
        # Get file properties
        try:
            file_props = self._FILEPROP_REXP.match(self._process.readline()).groups()
        except AttributeError:
            return False        
        (self.audio['streams'], self.video['streams'],
        self.chapters, self.subtitles) = [int(x) for x in file_props]
        
        # Get video properties        
        try:
            video_props = self._VIDEOPROP_REXP.match(self._process.readline()).groups()
        except AttributeError:
            return False
        self.video['decoder'] = video_props[0]
        self.video['dimensions'] = tuple(int(x) for x in video_props[1:3])
        self.video['profile'] = int(video_props[3])
        self.video['fps'] = float(video_props[4])
                        
        # Get audio properties
        try:
            audio_props = self._AUDIOPROP_REXP.match(self._process.readline()).groups()
        except AttributeError:
            return False       
        self.audio['decoder'] = audio_props[0]
        (self.audio['channels'], self.audio['rate'],
         self.audio['bps']) = [int(x) for x in audio_props[1:]]

        if self.audio['streams'] > 0:
            self.current_audio_stream = 1
            self.current_volume = 0.0



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

    def set_volume(self, volume):
        raise NotImplementedError

    def seek(self, minutes):
        raise NotImplementedError

    @staticmethod
    def set_omx_location(location):
        OMXPlayer._LAUNCH_CMD = location + OMXPlayer._LAUNCH_ARGS_FORMAT



# ***************************************
# YTDL CLASS
# ***************************************

class Ytdl:

    _YTLAUNCH_CMD = ''
    _YTLAUNCH_ARGS_FORMAT = ' --prefer-%s -g -f %s "%s"'
    _YTLAUNCH_PLST_CMD = ''
    _YTLAUNCH_PLST_ARGS_FORMAT = ' --prefer-%s -J -f mp4 "%s"'
    _PREFERED_TRANSCODER = ''
    _YOUTUBE_MEDIA_TYPE = ''
    _SUPPORTED_SERVICES = []
    
    _STATUS_REXP = re.compile("\n")
    _WRN_REXP = re.compile("WARNING:")
    _ERR_REXP = re.compile("ERROR:")
    _LINK_REXP = re.compile("(http[s]?://[a-zA-Z0-9.,?&/_\-=+]+)")
    
    MSGS = ("Problem retreiving content. Do you have up-to-date dependencies?", 
                                     "Problem retreiving content. Content may be copyrighted or the link invalid.",
                                     "Problem retrieving content. Content may have been truncated.")
    WAIT_TAG = "[wait]"
    start_signal = False
    end_signal = False
    
    def __init__(self, options, supported_services):
        self.set_options(options)
        self._SUPPORTED_SERVICES=supported_services

    def _response(self):
        data = self._process.before
        if self._WRN_REXP.search(data):
            # warning message
            r = (0, self.MSGS[0])
        elif self._ERR_REXP.search(data):
            # error message
            r = (-1, self.MSGS[1])
        else: 
            r = (1, data)
        self.result = r

    def _get_link_media_format(self, url):
        return "m4a" if (self._YOUTUBE_MEDIA_TYPE == "m4a" and "youtube." in url) else "mp4"

    def _background_process(self):
        while True:
            try:
                index = self._process.expect([self._STATUS_REXP,
                                                pexpect.TIMEOUT,
                                                pexpect.EOF,
                                                self._STATUS_REXP])
                if index == 1: continue
                elif index in (2, 3):
                    self.end_signal = True
                    break
                else:
                    self._response()
                    self.end_signal = True
            except Exception:
                break
            sleep(0.05)

    def _spawn_thread(self):
        self.end_signal = False
        self._position_thread = Thread(target=self._background_process)
        self._position_thread.start()

    def retrieve_media_url(self, url):
        ytcmd = self._YTLAUNCH_CMD % (self._PREFERED_TRANSCODER, self._get_link_media_format(url), url)
        self._process = pexpect.spawn(ytcmd)
        self._spawn_thread()

    def retrieve_youtube_playlist(self, playlist_url):
        ytcmd = self._YTLAUNCH_PLST_CMD % (self._PREFERED_TRANSCODER, playlist_url)
        self._process = pexpect.spawn(ytcmd, timeout=180, maxread=50000, searchwindowsize=50000)
        self._spawn_thread()
 
    def whether_to_use_youtube_dl(self,url):
        return url[:4] == "http" and any(re.match("(http(?:s){0,1}://(?:\w\w\w\.){0,1}" + s + "\.)", url) for s in self._SUPPORTED_SERVICES)

    def is_running(self):
        return self._process.isalive()

    def set_options(self, options):
        self._YTLAUNCH_CMD=options.ytdl_location + self._YTLAUNCH_ARGS_FORMAT
        self._YTLAUNCH_PLST_CMD=options.ytdl_location + self._YTLAUNCH_PLST_ARGS_FORMAT
        self._PREFERED_TRANSCODER=options.ytdl_prefered_transcoder
        self._YOUTUBE_MEDIA_TYPE=options.youtube_media_format



#from pyomxplayer import OMXPlayer
from pprint import pformat
from pprint import pprint
from random import randint
from json import loads
from Tkinter import *
import Tkinter as tk
import tkFileDialog
import tkMessageBox
import tkSimpleDialog
import tkFont
import csv
import os
import ConfigParser



#**************************
# TBOPLAYER CLASS
# *************************

class TBOPlayer:



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


    # kick off the state machine by playing a track
    def play(self):
        if  self.play_state==self._OMX_CLOSED:
            if self.playlist.track_is_selected():
                #initialise all the state machine variables
                self.iteration = 0                           # for debugging
                self.paused = False
                self.stop_required_signal=False     # signal that user has pressed stop
                self.quit_sent_signal = False          # signal  that q has been sent
                self.root.title(self.playlist.selected_track_title[:30] + (self.playlist.selected_track_title[30:] and '..') + " - OMXPlayer")
                self.playing_location = self.playlist.selected_track_location
                self.play_state=self._OMX_STARTING
                
                #play the selelected track
                self.start_omx(self.playlist.selected_track_location)
                self.root.after(500, self.play_state_machine)
 

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
            try:
                if self.omx.start_play_signal==True:
                    self.monitor("            <start play signal received from omx")
                    self.omx.start_play_signal=False
                    self.play_state=self._OMX_PLAYING
                    self.monitor("      State machine: omx_playing started")
                    #if self.debug:
                       # pprint(self.omx.__dict__)
            except:
                self.monitor("      OMXPlayer not started yet.")
            self.root.after(500, self.play_state_machine)

        elif self.play_state == self._OMX_PLAYING:
            # self.monitor("      State machine: " + self.play_state)
            # service any queued stop signals
            if self.stop_required_signal==True:
                self.monitor("      Service stop required signal")
                self.stop_omx()
                self.stop_required_signal=False
            else:
                # quit command has been sent or omxplayer reports it is terminating so change to ending state
                if self.quit_sent_signal == True or self.omx.end_play_signal== True:
                    if self.quit_sent_signal:
                        self.monitor("            quit sent signal received")
                        self.quit_sent_signal = False
                    if self.omx.end_play_signal:                    
                        self.monitor("            <end play signal received")
                        self.monitor("            <end detected at: " + str(self.omx.position))
                    self.play_state =self. _OMX_ENDING
                self.do_playing()
            self.root.after(500, self.play_state_machine)

        elif self.play_state == self._OMX_ENDING:
            self.monitor("      State machine: " + self.play_state)
            # if spawned process has closed can change to closed state
            self.monitor ("      State machine : is omx process running -  "  + str(self.omx.is_running()))
            if self.omx.is_running() ==False:
            #if self.omx.end_play_signal==True:    #this is not as safe as process has closed.
                self.monitor("            <omx process is dead")
                self.play_state = self._OMX_CLOSED
            self.do_ending()
            self.root.after(500, self.play_state_machine)

    # do things in each state
 
    def do_playing(self):
        # we are playing so just update time display
        # self.monitor("Position: " + str(self.omx.position))
        if self.paused == False:
            self.display_time.set(self.time_string(self.omx.position))
        else:
            self.display_time.set("Paused")           

    def do_starting(self):
        self.display_time.set("Starting")
        return

    def do_ending(self):
        # we are ending so just write End to the time display
        self.display_time.set("End")


    # respond to asynchrous user input and send signals if necessary
    def play_track(self):
        """ respond to user input to play a track, ignore it if already playing
              needs to start playing and not send a signal as it is this that triggers the state machine.
        """
        self.monitor(">play track received") 
        if self.play_state == self._OMX_CLOSED:
            self.play()
        elif self.playing_location==self.playlist.selected_track_location:
            self.toggle_pause()
        else:
            self.stop_track()
            self.root.after(1000, self.play_track)


    def skip_to_next_track(self):
        # send signals to stop and then to play the next track
        self.monitor(">skip  to next received") 
        self.monitor(">stop received for next track") 
        self.stop_required_signal=True
        self.play_next_track_signal=True
        

    def skip_to_previous_track(self):
        # send signals to stop and then to play the previous track
        self.monitor(">skip  to previous received")
        self.monitor(">stop received for previous track") 
        self.stop_required_signal=True
        self.play_previous_track_signal=True


    def stop_track(self):
        # send signals to stop and then to break out of any repeat loop
        self.monitor(">stop received")
        self.stop_required_signal=True
        self.break_required_signal=True


    def toggle_pause(self):
        """pause clicked Pauses or unpauses the track"""
        self.send_command('p')
        if self.paused == False:
            self.paused=True
        else:
            self.paused=False

    def volplus(self):
        self.send_command('+')
        
    def volminus(self):
        self.send_command('-')

    def time_string(self,secs):
        minu = int(secs/60)
        sec = secs-(minu*60)
        return str(minu)+":"+str(int(sec))


    def what_next(self):
        # called when state machine is in the omx_closed state in order to decide what to do next.
        if self.play_next_track_signal ==True:
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
        elif self.break_required_signal==True:
            self.monitor("What next, break_required so exit")
            self.break_required_signal=False
            # fall out of the state machine
            return
        elif self.options.mode=='single':
            self.monitor("What next, single track so exit")
            # fall out of the state machine
            return
        elif self.options.mode=='repeat':
            self.monitor("What next, Starting repeat track")
            self.play()
            return
        elif self.options.mode=='playlist':
            self.monitor("What next, Starting playlist track")
            self.select_next_track()
            self.play()
            return     
        elif self.options.mode=='shuffle':
            self.monitor("What next, Starting random track")
            self.random_next_track()
            self.play()
            return


    def go_ytdl(self,url,playlist=False):
        if self.ytdl_state==self._YTDL_CLOSED:
            #initialise all the state machine variables
            self.quit_ytdl_sent_signal = False
            self.ytdl_state=self._YTDL_STARTING
            self.ytdl.start_signal=True
          
            if not playlist:
                self.ytdl.retrieve_media_url(url)
            else:
                self.ytdl.retrieve_youtube_playlist(url)
            self.ytdl_state_machine()
            self.root.after(500, self.ytdl_state_machine)


    def ytdl_state_machine(self):
        if self.ytdl_state == self._YTDL_CLOSED:
            self.monitor("      Ytdl state machine: " + self.ytdl_state)
            return 
                
        elif self.ytdl_state == self._YTDL_STARTING:
            self.monitor("      Ytdl state machine: " + self.ytdl_state)
            # if omxplayer is playing the track change to play state
            if self.ytdl.start_signal==True:
                self.monitor("            <start play signal received from youtube-dl")
                self.ytdl.start_signal=False
                self.ytdl_state=self._YTDL_WORKING
                self.monitor("      Ytdl state machine: "+self.ytdl_state)
            self.root.after(500, self.ytdl_state_machine)

        elif self.ytdl_state == self._YTDL_WORKING:
            # youtube-dl reports it is terminating or user has removed a waiting track so change to ending state
            if self.ytdl.end_signal == True or self.quit_ytdl_sent_signal == True:
                if self.ytdl.end_signal == True:
                    self.treat_ytdl_result()
                self.monitor("            <end play signal received from youtube-dl")
                self.ytdl_state =self._YTDL_ENDING
            self.root.after(500, self.ytdl_state_machine)

        elif self.ytdl_state == self._YTDL_ENDING:
            self.monitor("      Ytdl state machine: " + self.ytdl_state)
            # if spawned process has closed can change to closed state
            self.monitor("      Ytdl state machine: is process running - "  + str(self.ytdl.is_running()))
            if self.ytdl.is_running() or self.quit_ytdl_sent_signal == True:
                self.monitor("            <youtube-dl process is dead")
                self.ytdl_state = self._YTDL_CLOSED
            self.root.after(500, self.ytdl_state_machine)


    def treat_ytdl_result(self):
        if self.ytdl.result[0] == 1:
            if self.ytdl._LINK_REXP.match(self.ytdl.result[1]):
                try:
                    track = self.playlist.waiting_track()
                    result = (self.ytdl.result[1], track[1][1].replace(self.ytdl.WAIT_TAG,""))
                    self.playlist.replace(track[0], result)
                    self.playlist.select(track[0])               
                    self.display_selected_track(track[0])
                    self.refresh_playlist_display()
                    if self.play_state==self._OMX_STARTING:
                        self.start_omx(result[0],skip_ytdl_check=True)
                except:
                    # no need to treat this
                    return
            else:
                try:
                    self.treat_youtube_playlist(loads(self.ytdl.result[1]))
                except:
                    self.display_selected_track_title.set(self.ytdl.MSGS[2])
        else:
            if self.ytdl.result[0] == -1:
                index = self.playlist.waiting_track()[0]
                self.track_titles_display.delete(index,index)
                self.playlist.remove(index)
                self.blank_selected_track()
            self.display_selected_track_title.set(self.ytdl.result[1])
            return


    def treat_youtube_playlist(self,ytplst):
        for entry in ytplst['entries']:
            if self.options.youtube_media_format == 'mp4':
                media_url = entry['url']
            else:
                preference = -100
                for format in entry['formats']:
                    if format['ext'] == 'm4a':
                        if format['preference'] and format['preference'] > preference:
                            preference = format['preference']
                            media_url = format['url']
                        elif not format['preference']:
                            media_url = format['url']
            self.playlist.append([media_url,entry['title'],'',''])
            # add title to playlist display
            self.track_titles_display.insert(END, entry['title']) 
            # and set it as the selected track
        self.playlist.select(self.playlist.length() - len(ytplst['entries']))
        self.display_selected_track(self.playlist.selected_track_index())

 

# ***************************************
# WRAPPER FOR JBAITER'S PYOMXPLAYER
# ***************************************

    def start_omx(self, track, skip_ytdl_check=False):
        """ Loads and plays the track"""
        if not skip_ytdl_check and self.ytdl.whether_to_use_youtube_dl(track):
            self.go_ytdl(track)
            index = self.playlist.selected_track_index()
            track = self.playlist.selected_track()
            track = (track[0], self.ytdl.WAIT_TAG+track[1])
            self.playlist.replace(index, track)
            self.playlist.select(index)               
            self.display_selected_track(index)
            self.refresh_playlist_display()
            return

        ttrack= "'"+ track.replace("'","'\\''") + "'"
        opts= self.options.omx_user_options + " "+ self.options.omx_audio_option + " " + self.options.omx_subtitles_option + " "
        self.omx = OMXPlayer(ttrack, args=opts, start_playback=True, do_dict = self.options.generate_track_info)

        self.monitor("            >Play: " + ttrack + " with " + opts)


    def stop_omx(self):
        if self.play_state ==  self._OMX_PLAYING:
            self.monitor("            >Send stop to omx") 
            self.omx.stop()
        else:
            self.monitor ("            !>stop not sent to OMX because track not playing")


    def send_command(self,command):
        if (command in '+-pz12jkionms') and self.play_state ==  self._OMX_PLAYING:
            self.monitor("            >Send Command: "+command) 
            self.omx.send_command(command)
            return True
        else:
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

    def __init__(self):

        # initialise options class and do initial reading/creation of options
        self.options=Options()

        #initialise the play state machine
        self.init_play_state_machine()

        #create the internal playlist
        self.playlist = PlayList()

        #root is the Tkinter root widget
        self.root = tk.Tk()
        self.root.title("GUI for OMXPlayer")

        self.root.configure(background='grey')
        # width, height, xoffset, yoffset
        self.root.geometry('408x340+350+250')
        self.root.resizable(False,False)

        #defne response to main window closing
        self.root.protocol ("WM_DELETE_WINDOW", self.app_exit)

        OMXPlayer.set_omx_location(self.options.omx_location)

        # start and configure ytdl object
        f = open(os.path.dirname(os.path.realpath(sys.argv[0])) + "/yt-dl_supported_sites", "r")
        self.ytdl = Ytdl(self.options, loads(f.read()))
        f.close()

        self._SUPPORTED_MEDIA_FORMATS = (".m4a",".mp2",".mp3",".ogg",".aac",".3gp",".wav",".avi",".mp4",".mkv",".ogv")

        # bind some display fields
        self.filename = tk.StringVar()
        self.display_selected_track_title = tk.StringVar()
        self.display_time = tk.StringVar()

        #Keys
        self.root.bind("<Left>", self.key_left)
        self.root.bind("<Right>", self.key_right)
        self.root.bind("<Up>", self.key_up)
        self.root.bind("<Down>", self.key_down)
        self.root.bind("<Shift-Right>", self.key_shiftright)  #forward 600
        self.root.bind("<Shift-Left>", self.key_shiftleft)  #back 600
        self.root.bind("<Control-Right>", self.key_ctrlright)  #next track      
        self.root.bind("<Control-Left>", self.key_ctrlleft)  #previous track
        self.root.bind("<Control-v>", self.key_paste)
        self.root.bind("<Escape>", self.key_escape)

        self.root.bind("<Key>", self.key_pressed)


# define menu
        menubar = Menu(self.root)
        filemenu = Menu(menubar, tearoff=0, bg="grey", fg="black")
        menubar.add_cascade(label='Track', menu = filemenu)
        filemenu.add_command(label='Add', command = self.add_track)
        filemenu.add_command(label='Add Dir', command = self.add_dir)
        filemenu.add_command(label='Add Dirs', command = self.add_dirs)
        filemenu.add_command(label='Add URL', command = self.add_url)
        filemenu.add_command(label='Remove', command = self.remove_track)
        filemenu.add_command(label='Edit', command = self.edit_track)
        
        listmenu = Menu(menubar, tearoff=0, bg="grey", fg="black")
        menubar.add_cascade(label='Playlists', menu = listmenu)
        listmenu.add_command(label='Open playlist', command = self.open_list)
        listmenu.add_command(label='Save playlist', command = self.save_list)
        listmenu.add_command(label='Load Youtube playlist', command = self.load_yt_playlist)
        listmenu.add_command(label='Clear', command = self.clear_list)

        omxmenu = Menu(menubar, tearoff=0, bg="grey", fg="black")
        menubar.add_cascade(label='OMX', menu = omxmenu)
        omxmenu.add_command(label='Track Info', command = self.show_omx_track_info)

        optionsmenu = Menu(menubar, tearoff=0, bg="grey", fg="black")
        menubar.add_cascade(label='Options', menu = optionsmenu)
        optionsmenu.add_command(label='Edit', command = self.edit_options)

        helpmenu = Menu(menubar, tearoff=0, bg="grey", fg="black")
        menubar.add_cascade(label='Help', menu = helpmenu)
        helpmenu.add_command(label='Help', command = self.show_help)
        helpmenu.add_command(label='About', command = self.about)
         
        self.root.config(menu=menubar)


# define buttons 
        # add track button
        Button(self.root, width = 5, height = 1, text='Add',
                              fg='black', command = self.add_track, 
                              bg="light grey").grid(row=0, column=1)
        # add url button
        Button(self.root, width = 5, height = 1, text='Add URL',
                              fg='black', command = self.add_url, 
                              bg="light grey").grid(row=0, column=2)
        # add dir button        
        Button(self.root, width = 5, height = 1, text='Add Dir',
                              fg='black', command = self.add_dir, 
                              bg="light grey").grid(row=0, column=3)
        # open list button        
        Button(self.root, width = 5, height = 1, text='Open List',
                              fg='black', command = self.open_list, 
                              bg="light grey").grid(row=0, column=4)
        # save list button
        Button(self.root, width = 5, height = 1, text = 'Save List',
                              fg='black', command = self.save_list, 
                              bg='light grey').grid(row=0, column=5)
        # clear list button
        Button(self.root, width = 5, height = 1, text = 'Clear List',
                              fg='black', command = self.clear_list, 
                              bg='light grey').grid(row=0, column=6)

        # play/pause button
        Button(self.root, width = 5, height = 1, text='Play/Pause',
                              fg='black', command = self.play_track, 
                              bg="light grey").grid(row=6, column=1)
        # stop track button       
        Button(self.root, width = 5, height = 1, text='Stop',
                              fg='black', command = self.stop_track, 
                              bg="light grey").grid(row=6, column=2)
        # previous track button
        Button(self.root, width = 5, height = 1, text='Previous',
                              fg='black', command = self.skip_to_previous_track, 
                              bg="light grey").grid(row=6, column=3)
        # next track button
        Button(self.root, width = 5, height = 1, text='Next',
                              fg='black', command = self.skip_to_next_track, 
                              bg="light grey").grid(row=6, column=4)
        # vol plus button
        Button(self.root, width = 5, height = 1, text = 'Vol +',
                              fg='black', command = self.volplus, 
                              bg='light grey').grid(row=6, column=5)
        # vol minus button
        Button(self.root, width = 5, height = 1, text = 'Vol -',
                              fg='black', command = self.volminus, 
                              bg='light grey').grid(row=6, column=6)

# define display of file that is selected
        Label(self.root, font=('Comic Sans', 10),
                              fg = 'black', wraplength = 300, height = 2,
                              textvariable=self.display_selected_track_title, 
                              bg="grey").grid(row=3, column=0, columnspan=6)

# define time/status display for selected track
        Label(self.root, font=('Comic Sans', 11),
                              fg = 'black', wraplength = 300,
                              textvariable=self.display_time, 
                              bg="grey").grid(row=3, column=6, columnspan=1)


# define display of playlist
        self.track_titles_display = Listbox(self.root, selectmode=SINGLE, height=15,
                               width = 40, bg="white",
                               fg="black")
        self.track_titles_display.grid(row=4, column=0, columnspan=7)
        self.track_titles_display.bind("<ButtonRelease-1>", self.select_track)
        self.track_titles_display.bind("<Delete>", self.remove_track)

        self.track_titles_display.bind("<Return>", self.key_return)
# scrollbar for displaylist
        scrollbar = Scrollbar(self.root, command=self.track_titles_display.yview, orient=tk.VERTICAL)
        scrollbar.grid(row = 4, column=6,sticky='ns')
        self.track_titles_display.config(yscrollcommand=scrollbar.set)

        for file in sys.argv[1:]:
            if (os.path.isfile(file) and self.is_file_supported(file)):
                self.file = file
                self.file_pieces = self.file.split("/")
                self.playlist.append([self.file, self.file_pieces[-1],'',''])
                self.track_titles_display.insert(END, self.file_pieces[-1])

#and display them going with Tkinter event loop
        self.root.mainloop()


#exit
    def app_exit(self):
        try:
            self.omx
        except AttributeError:
            exit()
        else:
            self.omx.stop()
            exit()





# ***************************************
# MISCELLANEOUS
# ***************************************


    def edit_options(self):
        """edit the options then read them from file"""
        eo = OptionsDialog(self.root, self.options.options_file,'Edit Options')
        self.options.read(self.options.options_file)
        self.ytdl.set_options(self.options)
        OMXPlayer.set_omx_location(self.options.omx_location)


    def show_help (self):
        tkMessageBox.showinfo("Help",
          " To control playing type a character\n p - pause/play\n spacebar - pause/play\n q - quit\n"
        + "+ - increase volume\n - - decrease volume\n z - tv show info\n 1 - reduce speed\n"
        + "2 - increase speed\n j - previous audio index\n k - next audio index\n i - back a chapter\n"
        + "o - forward a chapter\n n - previous subtitle index\n m - next subtitle index\n"
        + "s - toggle subtitles\n >cursor - seek forward 30\n <cursor - seek back 30\n"
        + "SHIFT >cursor - seek forward 600\n SHIFT <cursor - seek back 600\n"
        + "CTRL >cursor - next track\n CTRL <cursor - previous track")
  

    def about (self):
        tkMessageBox.showinfo("About","GUI for omxplayer using jbaiter's pyomxplayer wrapper\n"
                   +"Version dated: " + datestring + "\nAuthor: Ken Thompson  - KenT")

    def monitor(self,text):
        if self.options.debug: print text

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

    def key_paste(self,event):
        d = EditTrackDialog(self.root,"Add URL",
                                "Title", "",
                                "Location", self.root.clipboard_get())
        if d.result == None:
            return
        if d.result[0] == '':
            d.result = (d.result[1],d.result[1])
        else:
            d.result = (d.result[1],d.result[0])
        if d.result[1] != '':
            # append it to the playlist
            self.playlist.append(d.result)
            # add title to playlist display
            self.track_titles_display.insert(END, d.result[1])  
            # and set it as the selected track
            self.playlist.select(self.playlist.length()-1)
            self.display_selected_track(self.playlist.selected_track_index())

    def key_up(self,event):
        self.select_previous_track()
        
    def key_down(self,event):
        self.select_next_track()

    def key_escape(self,event):
        self.stop_track()
        
    def key_return(self,event):
    	  self.play_track()

    def key_pressed(self,event):
        char = event.char
        if char=='':
            return
        elif char=='.':
            self.play_track()
        elif char=='p':
            self.toggle_pause()
            return
        elif char==' ':
            self.toggle_pause()
            return
        elif char=='q':
            self.stop_track()
            return
        else:
            self.send_command(char)
            return


# ***************************************
# DISPLAY TRACKS
# ***************************************

    def display_selected_track(self,index):
        if self.playlist.track_is_selected:
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

    def is_file_supported(self, file):
        return file[-4:] in self._SUPPORTED_MEDIA_FORMATS

    def add_track(self):                                
        """
        Opens a dialog box to open files,
        then stores the tracks in the playlist.
        """
        # get the filez
        if self.options.initial_track_dir=='':
            filez = tkFileDialog.askopenfilenames(parent=self.root,title='Choose the file(s)')
        else:
            filez = tkFileDialog.askopenfilenames(initialdir=self.options.initial_track_dir,parent=self.root,title='Choose the file(s)')

        filez = self.root.tk.splitlist(filez)

        if filez:
            self.options.initial_track_dir = filez[0][:filez[0].rindex('/')]
        else: 
            return

        for file in filez:
            if not os.path.isfile(file) or not self.is_file_supported(file):
                break
            self.file = file

            # split it to use leaf as the initial title
            self.file_pieces = self.file.split("/")
            
            # append it to the playlist
            self.playlist.append([self.file, self.file_pieces[-1],'',''])
            # add title to playlist display
            self.track_titles_display.insert(END, self.file_pieces[-1])

	# and set the selected track
	if len(filez)>1:
	    index = self.playlist.length() - len(filez)
	else:
	    index = self.playlist.length() - 1
	self.playlist.select(index)
	self.display_selected_track(self.playlist.selected_track_index())
	

    def get_dir(self):
        if self.options.initial_track_dir:
            d = tkFileDialog.askdirectory(initialdir=self.options.initial_track_dir,title="Choose a directory")
        else:
            d = tkFileDialog.askdirectory(parent=self.root,title="Choose a directory")
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
                    # split it to use leaf as the initial title
                    self.file_pieces = self.file.split("/")

                    # append it to the playlist
                    self.playlist.append([self.file, self.file_pieces[-1],'',''])
                    # add title to playlist display
                    self.track_titles_display.insert(END, self.file_pieces[-1])
            except Exception:
                return

    
    def add_dir(self):
        dirname = self.get_dir()
        if dirname:
            self.options.initial_track_dir = dirname
            self.ajoute(dirname,False)


    def add_dirs(self):
        dirname = self.get_dir()
        if dirname:
            self.options.initial_track_dir = dirname
            self.ajoute(dirname,True)


    def add_url(self):
        d = EditTrackDialog(self.root,"Add URL",
                                "Title", "",
                                "Location", "")
        if d.result == None:
            return
        if d.result[0] == '':
            d.result = [d.result[1],d.result[1]]
        else:
            d.result = [d.result[1],d.result[0]]
        if d.result[0] != '':
            if self.options.download_media_url_upon == "add" and self.ytdl.whether_to_use_youtube_dl(d.result[0]):
                if self.ytdl_state != self._YTDL_CLOSED:
                    return
                self.go_ytdl(d.result[0])
                d.result[1] = self.ytdl.WAIT_TAG + d.result[1]

            # append it to the playlist
            self.playlist.append(d.result)
            # add title to playlist display
            self.track_titles_display.insert(END, d.result[1])  
            # and set it as the selected track
            self.playlist.select(self.playlist.length()-1)
            self.display_selected_track(self.playlist.selected_track_index())

   
    def remove_track(self,*event):
        if  self.playlist.length()>0 and self.playlist.track_is_selected():
            index= self.playlist.selected_track_index()
            waiting_track = self.playlist.waiting_track()
            if waiting_track and waiting_track[0] == index and self.ytdl_state==self._YTDL_WORKING:
                # tell ytdl_state_machine to stop
                self.quit_ytdl_sent_signal = True  
            self.track_titles_display.delete(index,index)
            self.playlist.remove(index)
            self.blank_selected_track()
            self.display_time.set("")
                


    def edit_track(self):
        if self.playlist.track_is_selected():
            index= self.playlist.selected_track_index()
            d = EditTrackDialog(self.root,"Edit Track",
                                "Title", self.playlist.selected_track_title,
                                "Location", self.playlist.selected_track_location)
            if d.result[1] != '':
                if self.selected_track()[1][:6] != self.ytdl.WAIT_TAG and self.ytdl.whether_to_use_youtube_dl(d.result[1]):
                    self.go_ytdl(d.result[1])
                    d.result[0] = self.ytdl.WAIT_TAG + d.result[0]
                d.result = (d.result[1],d.result[0])
                self.playlist.replace(index, d.result)
                self.playlist.select(index)               
                self.display_selected_track(index)
                self.refresh_playlist_display()
             
        


    def select_track(self, event):
        """
        user clicks on a track in the display list so try and select it
        """
        # needs forgiving int for possible tkinter upgrade
        if self.playlist.length()>0:
            index=int(event.widget.curselection()[0])
            self.playlist.select(index)
            self.display_selected_track(index)

    	
    def select_next_track(self):
        if self.playlist.length()>0:
            if self.playlist.selected_track_index()== self.playlist.length()-1:
                index=0
            else:
                index= self.playlist.selected_track_index()+1
            self.playlist.select(index)
            self.display_selected_track(index)

    	
    def random_next_track(self):
        if self.playlist.length()>0:
            index= randint(0,self.playlist.length()-1)
            self.playlist.select(index)
            self.display_selected_track(index)

    	
    def select_previous_track(self):
        if self.playlist.length()>0:
            if self.playlist.selected_track_index()== 0:
                index=self.playlist.length()-1
            else:
               index = self.playlist.selected_track_index()- 1
            self.playlist.select(index)               
            self.display_selected_track(index)

      
# ***************************************
# PLAYLISTS
# ***************************************

    def open_list(self):
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
        self.options.initial_playlist_dir = ''
        ifile  = open(filename, 'rb')
        pl=csv.reader(ifile)
        self.playlist.clear()
        self.track_titles_display.delete(0,self.track_titles_display.size())
        for pl_row in pl:
            if len(pl_row) != 0:
                self.playlist.append([pl_row[0],pl_row[1],'',''])
                self.track_titles_display.insert(END, pl_row[1])
        ifile.close()
        self.playlist.select(0)
        self.display_selected_track(0)
        return


    def clear_list(self):
        if tkMessageBox.askokcancel("Clear Playlist","Clear Playlist"):
            self.track_titles_display.delete(0,self.track_titles_display.size())
            self.playlist.clear()
            self.blank_selected_track()
            self.display_time.set("")


    def load_yt_playlist(self):
        d = LoadYtPlaylistDialog(self.root)
        if not d.result or not "list=" in d.result:
            return
        else:
            self.go_ytdl(d.result,playlist=True)
            self.display_selected_track_title.set("Wait. Loading playlist content...")

     
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
                ofile.write ('"' + self.playlist.selected_track()[PlayList.LOCATION] + '","' + self.playlist.selected_track()[PlayList.TITLE]+'"\n')
        ofile.close()
        return

    
    def show_omx_track_info(self):

        if self.options.generate_track_info:
            tkMessageBox.showinfo("Track Information", self.playlist.selected_track()[PlayList.LOCATION]  +"\n"+ pformat(self.omx.__dict__))
        else:
            tkMessageBox.showinfo("Track Information","Not Enabled")



# ***************************************
# OPTIONS CLASS
# ***************************************

class Options:


# store associated with the object is the tins file. Variables used by the player
# is just a cached interface.
# options dialog class is a second class that reads and saves the otions from the options file

    def __init__(self):

        # define options for interface with player
        self.omx_audio_option = "" # omx audio option
        self.omx_subtitles_option = "" # omx subtitle option
        self.mode = ""
        self.initial_track_dir =""   # initial directory for add track.
        self.initial_playlist_dir =""   # initial directory for open playlist      
        self.omx_user_options = ""  # omx options suppplied by user, audio overidden by audio option (HDMI or local)
        self.youtube_media_format = "" # what type of file must be downloded from youtube
        self.debug = False  # print debug information to terminal
        self.generate_track_info = False  # generate track information from omxplayer output

        # create an options file if necessary
        confdir = os.path.expanduser("~") + '/.tboplayer'
        self.options_file = confdir + '/tboplayer.cfg'
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
        
        if  config.get('config','audio',0) == 'auto':
            self.omx_audio_option = ""
        else:
            self.omx_audio_option = "-o "+config.get('config','audio',0)
            
        self.mode = config.get('config','mode',0)
        self.initial_track_dir = config.get('config','tracks',0)
        self.initial_playlist_dir = config.get('config','playlists',0)    
        self.omx_user_options = config.get('config','omx_options',0)
        self.youtube_media_format = config.get('config','youtube_media_format',0)
        self.omx_location = config.get('config','omx_location',0)
        self.ytdl_location = config.get('config','ytdl_location',0)
        self.ytdl_prefered_transcoder = config.get('config','ytdl_prefered_transcoder',0)
        self.download_media_url_upon = config.get('config','download_media_url_upon',0)

        if config.get('config','debug',0) == 'on':
            self.debug = True
        else:
            self.debug = False

        if config.get('config','subtitles',0) == 'on':
            self.omx_subtitles_option = "-t on"
        else:
            self.omx_subtitles_option = ""

        if config.get('config','track_info',0) == 'on':
            self.generate_track_info = True
        else:
            self.generate_track_info = False
         

    def create(self,filename):
        config=ConfigParser.ConfigParser()
        config.add_section('config')
        config.set('config','audio','hdmi')
        config.set('config','subtitles','off')       
        config.set('config','mode','single')
        config.set('config','playlists','')
        config.set('config','tracks','')
        config.set('config','omx_options','')
        config.set('config','debug','off')
        config.set('config','track_info','off')
        config.set('config','youtube_media_format','mp4')
        config.set('config','omx_location','/usr/bin/omxplayer')
        config.set('config','ytdl_location','/usr/local/bin/youtube-dl')
        config.set('config','ytdl_prefered_transcoder','avconv')
        config.set('config','download_media_url_upon','add')
        with open(filename, 'wb') as configfile:
            config.write(configfile)




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

        Label(master, text="Audio Output:").grid(row=0, sticky=W)
        self.audio_var=StringVar()
        self.audio_var.set(config.get('config','audio',0))
        rb_hdmi=Radiobutton(master, text="HDMI", variable=self.audio_var, value="hdmi")
        rb_hdmi.grid(row=1,column=0,sticky=W)
        rb_local=Radiobutton(master, text="Local", variable=self.audio_var,value="local")
        rb_local.grid(row=2,column=0,sticky=W)
        rb_auto=Radiobutton(master, text="Auto", variable=self.audio_var,value="auto")
        rb_auto.grid(row=3,column=0,sticky=W)

        Label(master, text="Mode:").grid(row=10, sticky=W)
        self.mode_var=StringVar()
        self.mode_var.set(config.get('config','mode',0))
        rb_single=Radiobutton(master, text="Single", variable=self.mode_var, value="single")
        rb_single.grid(row=11,column=0,sticky=W)
        rb_repeat=Radiobutton(master, text="Repeat", variable=self.mode_var,value="repeat")
        rb_repeat.grid(row=12,column=0,sticky=W)
        rb_playlist=Radiobutton(master, text="Playlist", variable=self.mode_var,value="playlist")
        rb_playlist.grid(row=13,column=0,sticky=W)
        rb_shuffle=Radiobutton(master, text="Shuffle", variable=self.mode_var,value="shuffle")
        rb_shuffle.grid(row=14,column=0,sticky=W)

        Label(master, text="").grid(row=16, sticky=W)
        Label(master, text="Download from Youtube:").grid(row=17, sticky=W)
        self.youtube_media_format_var=StringVar()
        self.youtube_media_format_var.set(config.get('config','youtube_media_format',0))
        rb_video=Radiobutton(master, text="Video and audio", variable=self.youtube_media_format_var, value="mp4")
        rb_video.grid(row=18,column=0,sticky=W)
        rb_audio=Radiobutton(master, text="Audio only", variable=self.youtube_media_format_var, value="m4a")
        rb_audio.grid(row=19,column=0,sticky=W)
        Label(master, text="Download actual media URL:").grid(row=20, sticky=W)
        self.download_media_url_upon_var=StringVar()
        self.download_media_url_upon_var.set(config.get('config','download_media_url_upon',0))
        rb_adding=Radiobutton(master, text="when adding URL", variable=self.download_media_url_upon_var, value="add")
        rb_adding.grid(row=21,column=0,sticky=W)
        rb_playing=Radiobutton(master, text="when playing URL", variable=self.download_media_url_upon_var, value="play")
        rb_playing.grid(row=22,column=0,sticky=W)

        Label(master, text="Initial directory for tracks:").grid(row=0, column=2, sticky=W)
        self.e_tracks = Entry(master)
        self.e_tracks.grid(row=1, column=2)
        self.e_tracks.insert(0,config.get('config','tracks',0))
        Label(master, text="Inital directory for playlists:").grid(row=2, column=2, sticky=W)
        self.e_playlists = Entry(master)
        self.e_playlists.grid(row=3, column=2)
        self.e_playlists.insert(0,config.get('config','playlists',0))
    
        Label(master, text="").grid(row=10, column=2, sticky=W)
        Label(master, text="OMXPlayer location:").grid(row=11, column=2, sticky=W)
        self.e_omx_location = Entry(master)
        self.e_omx_location.grid(row=12, column=2)
        self.e_omx_location.insert(0,config.get('config','omx_location',0))
        Label(master, text="OMXPlayer options:").grid(row=13, column=2, sticky=W)
        self.e_omx_options = Entry(master)
        self.e_omx_options.grid(row=14, column=2)
        self.e_omx_options.insert(0,config.get('config','omx_options',0))

        self.subtitles_var = StringVar()
        self.cb_subtitles = Checkbutton(master,text="Subtitles",variable=self.subtitles_var, onvalue="on",offvalue="off")
        self.cb_subtitles.grid(row=15, column=2, columnspan=2, sticky = W)
        if config.get('config','subtitles',0)=="on":
            self.cb_subtitles.select()
        else:
            self.cb_subtitles.deselect()

        Label(master, text="").grid(row=16, column=2, sticky=W)
        Label(master, text="youtube-dl location:").grid(row=17, column=2, sticky=W)
        self.e_ytdl_location = Entry(master)
        self.e_ytdl_location.grid(row=18, column=2)
        self.e_ytdl_location.insert(0,config.get('config','ytdl_location',0))
        Label(master, text="").grid(row=19, column=2, sticky=W)
        Label(master, text="youtube-dl transcoder:").grid(row=20, column=2, sticky=W)
        self.ytdl_prefered_transcoder_var=StringVar()
        self.ytdl_prefered_transcoder_var.set(config.get('config','ytdl_prefered_transcoder',0))
        rb_avconv=Radiobutton(master, text="avconv", variable=self.ytdl_prefered_transcoder_var, value="avconv")
        rb_avconv.grid(row=21,column=2,sticky=W)
        rb_ffmpeg=Radiobutton(master, text="ffmpeg", variable=self.ytdl_prefered_transcoder_var, value="ffmpeg")
        rb_ffmpeg.grid(row=22,column=2,sticky=W)

        Label(master, text="").grid(row=51, sticky=W)
        self.debug_var = StringVar()
        self.cb_debug = Checkbutton(master,text="Debug",variable=self.debug_var, onvalue="on",offvalue="off")
        self.cb_debug.grid(row=52,columnspan=2, sticky = W)
        if config.get('config','debug',0)=="on":
            self.cb_debug.select()
        else:
            self.cb_debug.deselect()

        self.track_info_var = StringVar()
        self.cb_track_info = Checkbutton(master,text="Generate Track Information", variable= self.track_info_var, onvalue="on",offvalue="off")
        self.cb_track_info.grid(row=60,columnspan=2, sticky = W)
        if config.get('config','track_info',0)=="on":
            self.cb_track_info.select()
        else:
            self.cb_track_info.deselect()

        return None    # no initial focus

    def apply(self):
        self.save_options()
        return True

    def save_options(self):
        """ save the output of the options edit dialog to file"""
        config=ConfigParser.ConfigParser()
        config.add_section('config')
        config.set('config','audio',self.audio_var.get())
        config.set('config','subtitles',self.subtitles_var.get())
        config.set('config','mode',self.mode_var.get())
        config.set('config','playlists',self.e_playlists.get())
        config.set('config','tracks',self.e_tracks.get())
        config.set('config','omx_options',self.e_omx_options.get())
        config.set('config','debug',self.debug_var.get())
        config.set('config','track_info',self.track_info_var.get())
        config.set('config','youtube_media_format',self.youtube_media_format_var.get())
        config.set('config','omx_location',self.e_omx_location.get())
        config.set('config','ytdl_location',self.e_ytdl_location.get())
        config.set('config','ytdl_prefered_transcoder',self.ytdl_prefered_transcoder_var.get())
        config.set('config','download_media_url_upon',self.download_media_url_upon_var.get())
        with open(self.options_file, 'wb') as optionsfile:
            config.write(optionsfile)
    


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
        tkSimpleDialog.Dialog.__init__(self, parent, "Load Youtube playlist")


    def body(self, master):
        Label(master, text=self.label_url).grid(row=0)

        self.field1 = Entry(master)

        self.field1.grid(row=0, column=1)

        self.field1.insert(0,self.default_url)

        return self.field1 # initial focus on title


    def apply(self):
        self.result = self.field1.get()

        return self.result

# *************************************
# PLAYLIST CLASS
# ************************************

class PlayList():
    """
    manages a playlist of tracks and the track selected from the playlist
    """

    #field definition constants
    LOCATION=0
    TITLE=1
    DURATION=2
    ARTIST=3
    # template for a new track
    _new_track=['','','','']
    

    def __init__(self):
        self._num_tracks=0
        self._tracks = []      # list of track titles
        self._selected_track = PlayList._new_track
        self._selected_track_index =  -1 # index of currently selected track

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

    def waiting_track(self):
        for i in range(len(self._tracks)):
            if self._tracks[i][1][:6] == Ytdl.WAIT_TAG:
                return (i, self._tracks[i])
        return False



# ***************************************
# MAIN
# ***************************************


if __name__ == "__main__":
    datestring=" 4 Septemper 2015"
    bplayer = TBOPlayer()


