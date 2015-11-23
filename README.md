A GUI interface using jbaiter's pyomxplayer wrapper to control omxplayer

INSTALLATION
============

Instructions for installation on the official Raspbian image:

You can use the installer that comes with TBOPlayer, or install it manually.

To use the installer, from a terminal window open in your home directory, type:

        # skip this first line if you have already downloaded and extracted the tarball
        wget https://github.com/KenT2/tboplayer/tarball/master -O - | tar xz
        cd KenT2-tboplayer-* && chmod +x setup.sh && ./setup.sh
	
After that, TBOPlayer will have been installed on your system. To run it, just type 'tboplayer', or use the shortcut created in your Desktop.

If you prefer to install it manually, do as follows:
	
Update omxplayer
---------------

Ensure you have the latest version of omxplayer by typing the following in a terminal window open in the home directory:

        sudo apt-get -y update
        sudo apt-get install --only-upgrade -y omxplayer

Install pexpect
-----------------------------

From a terminal window, type to install pip if you don't have it yet

        sudo apt-get install -y python-pip
	
Then to install pexpect, in the terminal window, type 

        sudo pip install pexpect ptyprocess

Install gobject
-----------------------------

From a terminal window, type 

        sudo apt-get install -y python-gobject-2

Download and Install TBOPlayer
------------------------------

From a terminal window open in your home directory, type:

        wget https://github.com/KenT2/tboplayer/tarball/master -O - | tar xz

There should now be a directory 'KenT2-tboplayer-xxxx' in your home directory. Rename the directory to tboplayer.

Open a terminal window and type:

        python /path/to/tboplayer.py

TBOPlayer is developed on Raspbian Wheezy with python 2.7

**Note**: If you want to be able to watch videos from online services like Youtube, then you must have up-to-date **youtube-dl** installed on your system, as well as either **avconv 9.14**+ or **ffmpeg 0.8.17**+.

See this link for a list of services supported by youtube-dl: https://rg3.github.io/youtube-dl/supportedsites.html (not all of them were tested with TBOPlayer/OMXplayer)

Download and Install youtube-dl
-----------------------------

This is specified here https://github.com/rg3/youtube-dl/#installation and copied below:

From a terminal window open in your home directory, type:

        sudo wget https://yt-dl.org/downloads/latest/youtube-dl -O /usr/local/bin/youtube-dl
        sudo chmod a+rx /usr/local/bin/youtube-dl
	
Or update it with:

        sudo youtube-dl -U
	
OPERATION
=========

Buttons
-------

* `ADD` - duplicates the Track>Add menu item

* `ADD DIR` - duplicates the Track>Add Dir menu item

* `EDIT` - duplicates the Track>Edit menu item

* `OPEN/SAVE/CLEAR LIST` - duplicates the Playlist>Open,Save,Clear menu item

* `PLAY/PAUSE` - Play the selected track or pause if playing

* `STOP` - Stop playing, operational only during playing

* `PREVIOUS` - Play previous track, operational only after played some track

* `NEXT` - Play next track, up to mode that you set

* `- VOL +` - Minus/plus volume control

Menus
-----
* `Track` - add tracks (for selecting multiple tracks, hold ctrl when clicking) or directories, edit or remove tracks (or URLs) from the current playlist
 
* `Playlist` - save the current playlist or open a saved one or load youtube playlist
 
* `OMX` - display the track information for the last played track (needs to be enabled in options)
 
* `Options` -

    * Audio Output - play sound to hdmi or local output, auto does not send an audio option to omxplayer.
	
    * Mode - play the Single selected track, Repeat the single track, rotate around the Playlist starting from the selected track, randomly play a track from the Playlist.
	
    * Initial directory for tracks - where Add Track starts looking.
	
    * Initial directory for playlists - where Open Playlist starts looking
	
    * Enable subtitles

    * OMXPlayer location - path to omxplayer binary

    * OMXplayer options - add your own (no validation so be careful)
    
    * Download from Youtube - defines whether to download video and audio or audio only from Youtube (other online video services will always be asked for "video and audio")
     
    * Download actual media URL [when] - defines when to extract the actual media from the given URL, either upon adding the URL or when playing it
    
    * Youtube video quality - lets you choose between "small", "medium" and "high" qualities (Youtube only feature)
    
    * youtube-dl location - path to youtube-dl binary
    
    * youtube-dl transcoder - prefer to use either avconv or ffmpeg when using youtube-dl for extracting data from online supported services
	
    * Debug - prints some debug text to the command line
	
    * Generate Track Information - parses the output of omxplayer, disabled by default as it may cause problems with some tracks.


A track is selected using a single click of the mouse or up-down arrow key, playing is started by pressing the Play/Pause button, the . key or the Return key.

Removing the selected track can be done by pressing the Delete key.

During playing of a track, a clickable progress bar will appear below the playlist, which lets you seek a position, and if playing a video it's possible to see the progress bar if you move your mouse to the lowest side of the video.

Again during playing of a track, a slightly modified set of omxplayer commands can be used from the keyboard but there must be FOCUS on TBOPlayer. A list of commands is provided in the help menu. Note: some of the commands are not implemented by omxplayer. 

TROUBLESHOOTING
=========

If you have problems playing a track try it from the command line with omxplayer -o hdmi file or omxplayer -o local file to make sure it's not a problem with omxplayer.

If the progress bar or volume bar don't work for you, it may be that you have another instance of omxplayer running in the background. In that case, you can try to close that instance, and then play the track again. You can force omxplayer to terminate by typing in a terminal:

        sudo pkill -9 omxplayer

Contributors:
-------------

KenT2 - Original idea and implementation

popiazaza - GUI enhancements

heniotierra - GUI enhancements and youtube-dl integration

krugg - GUI enhancements
