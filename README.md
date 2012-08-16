A GUI interface using jbaiter's pyomxplayer to control omxplayer

INSTALLATION
*** Instructions for installation on the official Debian Wheezy Raspbian image
  *  requires the latest bug fixed version of omxplayer which you can get by doing apt-get update then apt-get upgrade
  *  install pexpect by following the instructions at www.noah.org/wiki/pexpect
  *  pyomxplayer is currently included inline in the code as I have made some modifications to jbaiter's version, his original can be seen at https://github.com/jbaiter/pyomxplayer
  *  download tboplayer.py into a directory
  *  type python tboplayer.py from a terminal opened in the directory within which tboplayer.py is stored. 
  *  developed on raspbian wheezy with python 2.7
  
OPERATION
Menus
====
 Track - add  edit or remove a track from the current playlist
 Playlist - save the current playlist or open a saved one
 OMX - display the track information for the last played track (needs to be enabled in options)
 Options -
    Audio Output - play sound to hdmi or local output, auto does not send an audio option to omxplayer.
    Mode - play the Single selected track, Repeat the single track or rotate around the Playlist starting from the selected track.
    Initial directory for tracks - where Add Track starts looking.
    Initial directory for playlists - where Open Playlist starts looking
    OMX player options - add your own (no validation so be careful)
    Debug - prints some debug text to the command line
    Generate Track Information - parses the output of omxplayer, disabled by default as it may cause problems with some tracks.

A track is selected using a single click of the mouse, playing is started by pressing the Play button or the . key

During playing of a track a slightly modified set of  omxplayer commands can be used from the keyboard but there must be FOCUS on TBOPlayer.
A list  of comands is provided in the help menu. Note: some of the commands are not implemented by omxplayer.

If you have problems playing a track try it from the command line with omxplayer ohdmi file or omxplayer -olocal file
