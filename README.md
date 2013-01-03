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
 
 
OPERATION
=========

Buttons
-------

* ADD - duplicates the Track>Add menu item

* PLAY - Play the selected track

* PAUSE - Pause playing, operational only during playing

* STOP - Stop playing, operational only during playing

* VOL +- - Volume control, operational only during playing

Menus
-----
* Track - add  edit or remove a track from the current playlist
 
* Playlist - save the current playlist or open a saved one
 
* OMX - display the track information for the last played track (needs to be enabled in options)
 
* Options -

    * Audio Output - play sound to hdmi or local output, auto does not send an audio option to omxplayer.
	
    * Mode - play the Single selected track, Repeat the single track or rotate around the Playlist starting from the selected track.
	
    * Initial directory for tracks - where Add Track starts looking.
	
    * Initial directory for playlists - where Open Playlist starts looking
	
	* Enable subtitles
	
    * OMX player options - add your own (no validation so be careful)
	
    * Debug - prints some debug text to the command line
	
    * Generate Track Information - parses the output of omxplayer, disabled by default as it may cause problems with some tracks.

A track is selected using a single click of the mouse, playing is started by pressing the Play button or the . key

During playing of a track a slightly modified set of omxplayer commands can be used from the keyboard but there must be FOCUS on TBOPlayer. A list  of commands is provided in the help menu. Note: some of the commands are not implemented by omxplayer.

If you have problems playing a track try it from the command line with omxplayer -ohdmi file or omxplayer -olocal file
