A GUI interface using jbaiter's pyomxplayer wrapper to control omxplayer

INSTALLATION
============

Instructions for installation on the official Raspbian image

Update omxplayer
---------------

Ensure you have the latest version of omxplayer by typing the following in a terminal window open in the home directory:

        sudo apt-get update
        sudo apt-get upgrade
	

Download and Install pexpect
-----------------------------

This is specified here http://www.noah.org/wiki/pexpect#Download_and_Installation and copied below:

From a terminal window open in your home directory type:

        wget http://pexpect.sourceforge.net/pexpect-2.3.tar.gz
        tar xzf pexpect-2.3.tar.gz
        cd pexpect-2.3
        sudo python ./setup.py install


Download and Install TBOPlayer
------------------------------

From a terminal window open in your home directory type:

         wget https://github.com/KenT2/tboplayer/tarball/master -O - | tar xz

There should now be a directory 'KenT2-tboplayer-xxxx' in your home directory. Rename the directory to tboplayer

Open the tboplayer directory and from a terminal opened in THIS directory:

		python tboplayer.py

TBOPlayer is developed on Raspbian Wheezy with python 2.7


Oh, and if you want to be able to watch videos from youtube, then
Download and Install youtube-dl
-----------------------------

This is specified here https://github.com/rg3/youtube-dl/#installation:

From a terminal window open in your home directory type:

        sudo wget https://yt-dl.org/downloads/latest/youtube-dl -O /usr/local/bin/youtube-dl
        sudo chmod a+rx /usr/local/bin/youtube-dl
	
Or update it with

        sudo youtube-dl -U
	
OPERATION
=========

Buttons
-------

* ADD - duplicates the Track>Add menu item

* ADD DIR - duplicates the Track>Add Dir menu item

* EDIT - duplicates the Track>Edit menu item

* OPEN/SAVE/CLEAR LIST - duplicates the Playlist>Open,Save,Clear menu item

* PLAY/PAUSE - Play the selected track or pause if playing

* STOP - Stop playing, operational only during playing

* PREVIOUS - Play previous track, operational only after played some track

* NEXT - Play next track, up to mode that you set

* VOL +- - Volume control, operational only during playing

Menus
-----
* Track - add tracks (for selecting multiple tracks, hold ctrl when clicking) or directories, edit or remove tracks (or URLs) from the current playlist
 
* Playlist - save the current playlist or open a saved one or load youtube playlist
 
* OMX - display the track information for the last played track (needs to be enabled in options)
 
* Options -

    * Audio Output - play sound to hdmi or local output, auto does not send an audio option to omxplayer.
	
    * Mode - play the Single selected track, Repeat the single track, rotate around the Playlist starting from the selected track, randomly play a track from the Playlist.
    
    * Download from Youtube - defines whether to download video and audio or audio only from Youtube videos.
	
    * Initial directory for tracks - where Add Track starts looking.
	
    * Initial directory for playlists - where Open Playlist starts looking
	
	* Enable subtitles
	
    * OMX player options - add your own (no validation so be careful)
	
    * Debug - prints some debug text to the command line
	
    * Generate Track Information - parses the output of omxplayer, disabled by default as it may cause problems with some tracks.

A track is selected using a single click of the mouse or up-down arrow key, playing is started by pressing the Play/Pause button, the . key or the Return key.

Removing the selected track can be done by pressing the Delete key.

During playing of a track a slightly modified set of omxplayer commands can be used from the keyboard but there must be FOCUS on TBOPlayer. A list  of commands is provided in the help menu. Note: some of the commands are not implemented by omxplayer.

If you have problems playing a track try it from the command line with omxplayer -ohdmi file or omxplayer -o local file
