#!/bin/bash

TBOPLAYER_PATH=/opt/tboplayer
SCRIPT_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BIN_PATH=/usr/local/bin
DESKTOP_PATH=$HOME/Desktop
FAKE_BIN=$BIN_PATH/tboplayer
SUPPORTED_TYPES=('video/x-msvideo' 'video/quicktime' 'video/mp4'
                'video/x-flv' 'video/x-matroska' 'video/3gpp' 'audio/x-aac' 
                'video/h264' 'video/h263' 'video/h261' 'video/x-m4v' 'audio/midi'
                'video/mj2' 'audio/mpeg' 'video/mpeg' 'audio/mp4' 'application/mp4'
                'audio/ogg' 'video/ogg' 'audio/x-wav' 'video/flv'
                'audio/flac' 'video/3gpp2' 'video/x-f4v' 'application/ogg' 
                'audio/mpeg3' 'audio/x-mpeg-3' 'audio/x-mpeg' 'audio/mod' 
                'audio/x-mod' 'video/x-ms-asf' 'audio/x-pn-realaudio' 
                'audio/x-realaudio' 'video/vnd.rn-realvideo' 'video/fli' 
                'video/x-fli' 'audio/x-ms-wmv' 'video/avi' 'video/msvideo' 
                'audio/x-wav' 'video/m4v' 'audio/x-ms-wma' 'video/x-f4v')
DESKTOP_ENTRIES=($DESKTOP_PATH/tboplayer.desktop 
		/usr/share/applications/tboplayer.desktop)

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
        echo "Would you like to remove all of TBOPlayer dependencies too? [Y/N]" 
        read answer
        if [ "$answer" == "Y" ] || [ "$answer" == "y" ]; then
            echo ""
            echo "* Removing TBOPlayer dependencies..."
            yes | pip uninstall pexpect ptyprocess python-magic >/dev/null 2>&1
            sudo apt-get -y remove python-gobject-2 python-dbus python-gtk2 python-requests >/dev/null 2>&1
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

toaptinstall=""

function addToAptInstall {
    local cmd=$1
    local package=$2
    local pythn=$3
    if [ $pythn ]; then
        python -c "import "$cmd >/dev/null 2>&1
	local cmdres=$? 
    else
        command -v $cmd >/dev/null 2>&1
	local cmdres=$? 
    fi
    if [ $cmdres -eq 1 ]; then 
        toaptinstall+=$package" "
    fi
}

addToAptInstall "requests" "python-requests" true
addToAptInstall "gobject" "python-gobject-2" true
addToAptInstall "dbus" "python-dbus" true
addToAptInstall "gtk" "python-gtk2" true
addToAptInstall "avconv" "libav-tools" false

echo "* Installing dependencies: "$toaptinstall"..."

addToAptInstall "pip" "python-pip" false

sudo apt-get -y install $toaptinstall 2>&1 >/dev/null

python -c 'import pexpect' >/dev/null 2>&1
PEXPECT_INSTALLED=$?
python -c 'import ptyprocess' >/dev/null 2>&1
PTYPROCESS_INSTALLED=$?
if [ $PEXPECT_INSTALLED -eq 1 ]; then 
    echo "* Installing pexpect..."
    [[ $PTYPROCESS_INSTALLED -eq 1 ]] && ptyprocess='ptyprocess' || ptyprocess=''
    yes | pip install --user pexpect $ptyprocess >/dev/null 2>&1
fi

python -c 'import magic' >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    echo "* Installing magic..."
    yes | pip install --user python-magic >/dev/null 2>&1
fi

# install youtube-dl it's if not installed
command -v youtube-dl >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    echo "* Installing youtube-dl..."
    sudo wget https://yt-dl.org/downloads/latest/youtube-dl -O /usr/local/bin/youtube-dl >/dev/null 2>&1
    sudo chmod a+rx /usr/local/bin/youtube-dl
else 
    echo "* Updating youtube-dl..."
    sudo youtube-dl -U >/dev/null 2>&1
fi

# install fake tboplayer executable in /home/<user>/bin
command -v $FAKE_BIN >/dev/null 2>&1
if [ $? -eq 0 ]; then 
	sudo rm $FAKE_BIN
fi

TMP_BIN=$HOME/tmp.tboplayer

echo "* Creating tboplayer's bash executable..."
echo '#!/bin/bash' >> ~/tmp.tboplayer $TMP_BIN
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
echo "Installation finished."
echo ""
echo "If all went as expected, TBOPlayer is now installed in your system." 
echo "TBOPlayer can be found at the "$TBOPLAYER_PATH" directory."
echo "To run it, you can either type 'tboplayer',"
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
