#!/bin/bash

TBOPLAYER_PATH=/opt/tboplayer
SCRIPT_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BIN_PATH=/usr/local/bin
DESKTOP_PATH=$HOME/Desktop
FAKE_BIN=$BIN_PATH/tboplayer
YTDL_EXPECTED_PATH=$BIN_PATH/youtube-dl
DESKTOP_ENTRIES=($DESKTOP_PATH/tboplayer.desktop
		/usr/share/applications/tboplayer.desktop)
SUPPORTED_TYPES=('video/x-msvideo' 'video/quicktime' 'video/mp4' 'video/x-flv' 'video/x-matroska' 'audio/x-matroska'
              'video/3gpp' 'audio/x-aac' 'video/h264' 'video/h263' 'video/x-m4v' 'audio/midi'
              'audio/mid' 'audio/vnd.qcelp' 'audio/mpeg' 'video/mpeg' 'audio/rmf' 'audio/x-rmf'
	      'audio/mp4' 'video/mj2' 'audio/x-tta' 'audio/tta' 'application/mp4' 'audio/ogg'
              'video/ogg' 'audio/wav' 'audio/wave' 'audio/x-pn-aiff' 'audio/x-pn-wav' 'audio/x-wav'
              'audio/flac' 'audio/x-flac' 'video/h261' 'application/adrift' 'video/3gpp2' 'video/x-f4v'
              'application/ogg' 'audio/mpeg3' 'audio/x-mpeg-3' 'audio/x-gsm' 'audio/x-mpeg' 'audio/mod'
              'audio/x-mod' 'video/x-ms-asf' 'audio/x-pn-realaudio' 'audio/x-realaudio' 'video/vnd.rn-realvideo' 'video/fli'
              'video/x-fli' 'audio/x-ms-wmv' 'video/avi' 'video/msvideo' 'video/m4v' 'audio/x-ms-wma'
              'application/octet-stream' 'application/x-url' 'text/url' 'text/x-url' 'application/vnd.rn-realmedia'
              'audio/vnd.rn-realaudio' 'audio/x-pn-realaudio' 'audio/x-realaudio' 'audio/aiff' 'audio/x-aiff')

function echoGreen {
    tput setaf 2
    echo $1
    tput sgr0
}

# uninstall TBOPlayer
if [ "$1" == "uninstall" ]; then
    echo ""
    echo "Do you really wish to uninstall TBOPlayer? [Y/N]"
    read answer
    if [ "$answer" == "Y" ] || [ "$answer" == "y" ]; then
	echo ""
        echo "* Removing TBOPlayer..."
        sudo rm -Rf $TBOPLAYER_PATH
        sudo rm $FAKE_BIN
	rm "${DESKTOP_ENTRIES[0]}"
        sudo rm "${DESKTOP_ENTRIES[1]}"
        sudo update-desktop-database
        echo ""
	echoGreen "ATENTION"
        echo "Would you like to remove all of TBOPlayer dependencies too?"
	echo "These may also be used by other programs and removing them can make these programs to stop working. [Y/N]"
        read answer
        if [ "$answer" == "Y" ] || [ "$answer" == "y" ]; then
            echo ""
            echo "* Removing TBOPlayer dependencies..."
            sudo apt-get -y remove python-gobject-2 python-dbus python-tk python-gtk2 python-requests python-magic python-pexpect tkdnd >/dev/null 2>&1
            sudo rm -f /usr/local/bin/youtube-dl >/dev/null 2>&1
        fi
        echo ""
        echo "TBOPlayer has been uninstalled."
    fi
    exit
fi

# install TBOPlayer
$TBOPLAYER_PATH >/dev/null 2>&1
if [ $? -eq 126 ] && [ "$TBOPLAYER_PATH" != "$SCRIPT_PATH" ]; then
    sudo rm -Rf $TBOPLAYER_PATH
fi

echo ""
echo "Installing TBOPlayer and its dependencies..."
echo ""

sudo mv $SCRIPT_PATH $TBOPLAYER_PATH >/dev/null 2>&1
if [ $? -eq 1 ] && [ "$TBOPLAYER_PATH" != "$SCRIPT_PATH" ]; then
    echo ""
    echo "Installation failed. :("
    echo "Please, move this folder to "$HOME" and then run this setup script (setup.sh) again."
    exit
fi

mkdir $DESKTOP_PATH >/dev/null 2>&1

echo "* Updating distro packages database... This may take some seconds."
sudo apt-get update >/dev/null 2>&1

command -v omxplayer >/dev/null 2>&1
if [ $? -eq 1 ]; then
    echo "* Installing omxplayer..."
    sudo apt-get install -y omxplayer >/dev/null 2>&1
else
    echo "* Updating omxplayer..."
    sudo apt-get -y --only-upgrade install omxplayer >/dev/null 2>&1
fi

aptinstall=""

function addToAptInstall {
    dpkg -l $1 >/dev/null 2>&1
    if [ $? -eq 1 ]; then
        aptinstall+=$1" "
    fi
}

addToAptInstall "python-requests"
addToAptInstall "python-gobject-2"
addToAptInstall "python-dbus"
addToAptInstall "python-tk"
addToAptInstall "python-gtk2"
addToAptInstall "python-pexpect"
addToAptInstall "python-pip"
addToAptInstall "libav-tools"
#addToAptInstall "tkdnd"
#addToAptInstall "python-setuptools"

if [ "$aptinstall" != "" ]; then
    echo "* Installing dependencies: "$aptinstall"..."
    sudo apt-get -y install $aptinstall >/dev/null
    sudo apt-get -y install tkdnd --no-install-recommends >/dev/null
fi

python -c 'import magic' >/dev/null 2>&1
if [ $? -eq 1 ]; then
    echo "* Installing magic..."
    yes | pip install --user python-magic >/dev/null 2>&1
fi
function installYoutubedl {
    echo "* Installing youtube-dl..."
    sudo wget https://yt-dl.org/downloads/latest/youtube-dl -O $YTDL_EXPECTED_PATH >/dev/null 2>&1
    sudo chmod a+rx $YTDL_EXPECTED_PATH
}

dpkg -l tkdnd >/dev/null 2>&1
if [ $? -eq 1 ] ; then
    echo "* Compiling tkdnd..."
    sudo apt-get install -y build-essential tcl-dev tk-dev >/dev/null
    wget https://github.com/petasis/tkdnd/tarball/master -O - | tar xz >/dev/null 2>&1
    cd petasis-tkdnd-*
    ./configure >/dev/null 2>&1
    make >/dev/null 2>&1
    sudo make install >/dev/null 2>&1
    cd ..
fi

# install youtube-dl it's if not installed
YTDL_PATH="$( command -v youtube-dl )"
if [ $? -eq 1 ]; then
    echo "* Installing youtube-dl..."
    installYoutubedl
else
    if [ "$YTDL_PATH" != "$YTDL_EXPECTED_PATH" ]; then
        echo ""
	echoGreen "ATENTION"
        echo "You have youtube-dl installed in a location different than expected."
	echo "Do you want this setup to install youtube-dl in the expected path? [Y/N]"
	echo ""
	read answer
	if [ "$answer" == "Y" ] || [ "$answer" == "y" ]; then
	    sudo rm $YTDL_PATH
	    installYoutubedl
	fi
    else
        echo "* Updating youtube-dl..."
        sudo youtube-dl -U >/dev/null 2>&1
    fi
fi

# install fake tboplayer executable in /home/<user>/bin
command -v $FAKE_BIN >/dev/null 2>&1
if [ $? -eq 0 ]; then
    sudo rm $FAKE_BIN
fi

TMP_BIN=$HOME/tmp.tboplayer

echo "* Creating tboplayer's bash executable..."
echo '#!/bin/bash' >> $TMP_BIN
echo 'python '$TBOPLAYER_PATH'/tboplayer.py' >> $TMP_BIN
chmod +x $TMP_BIN
sudo mv $TMP_BIN $FAKE_BIN

# install tboplayer 'shortcut' in /home/<user>/Desktop

echo "* Creating shortcuts and file associations..."
DESKTOP_ENTRY="${DESKTOP_ENTRIES[0]}"
$DESKTOP_ENTRY >/dev/null 2>&1
if [ $? -eq 126 ]; then
    rm $DESKTOP_ENTRY
fi

MIMETS=''
for TYPE in "${SUPPORTED_TYPES[@]}"; do
    MIMETS=$TYPE";"$MIMETS
done

echo '[Desktop Entry]' >> $DESKTOP_ENTRY
echo 'Name=TBOPlayer' >> $DESKTOP_ENTRY
echo 'Comment=GUI for omxplayer' >> $DESKTOP_ENTRY
echo 'Exec=python '$TBOPLAYER_PATH'/tboplayer.py %F' >> $DESKTOP_ENTRY
echo 'Icon=/usr/share/pixmaps/python.xpm' >> $DESKTOP_ENTRY
echo 'Terminal=false' >> $DESKTOP_ENTRY
echo 'Type=Application' >> $DESKTOP_ENTRY
echo 'Categories=Application;Multimedia;Audio;AudioVideo;' >> $DESKTOP_ENTRY
echo 'MimeType='$MIMETS >> $DESKTOP_ENTRY

sudo cp $DESKTOP_ENTRY "${DESKTOP_ENTRIES[1]}"
sudo update-desktop-database

echo ""
echoGreen "Installation finished."
echo ""
echo "If all went as expected, TBOPlayer is now installed in your system."
echo "TBOPlayer can be found at the "$TBOPLAYER_PATH" directory."
echo "To run it, you can type 'tboplayer' in a new terminal,"
echo "or use the shortcut created on your Desktop and apps menu,"
echo "or open a file directly by double clicking on it,"
echo "or use the right-click menu, when using your file manager."
echo ""
echo "If none of the options above work for you,"
echo "try running 'python "$TBOPLAYER_PATH"/tboplayer.py'."
echo ""
echo "If you find a problem or need help, please contact the maintainers"
echo "at github.com/KenT2/tboplayer/issues"
echo ""
echo "Good bye! ;)"

exit
