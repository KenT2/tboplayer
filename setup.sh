#!/bin/bash

TBOPLAYER_PATH=$HOME/tboplayer
SCRIPT_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BIN_PATH=$HOME/bin
DESKTOP_PATH=$HOME/Desktop
SUPPORTED_TYPES=('application/ogg' 'video/ogg' 'audio/ogg' 
		'video/mpeg' 'audio/mpeg' 'video/mp4' 'audio/x-aac' 
		'video/3gp' 'video/3gpp2' 'video/quicktime' 'video/x-f4v' 
		'video/flv' 'audio/x-wav' 'video/x-msvideo')
DESKTOP_ENTRIES=($HOME/Desktop/tboplayer.desktop 
		usr/share/applications/tboplayer.desktop)
MIMEAPPS_FILE=/home/$USER/.config/mimeapps.list
MIMEAPPS_FILE_SECTION='Added Associations'

# install TBOPlayer
$TBOPLAYER_PATH >/dev/null 2>&1
if [ $? -eq 126 ] && [ "$TBOPLAYER_PATH" != "$SCRIPT_PATH" ]; then
    rm -Rf $TBOPLAYER_PATH
fi

echo ""
echo "Installing TBOPlayer and its dependencies..."
echo ""

mv $SCRIPT_PATH $TBOPLAYER_PATH
if [ $? -eq 1 ] && [ "$TBOPLAYER_PATH" != "$SCRIPT_PATH" ]; then 
    echo ""
    echo "Installation failed. :("
    echo "Please, move this folder to "$HOME" and then run this setup script (setup.sh) again."
    exit
fi

$BIN_PATH >/dev/null 2>&1
if [ $? -eq 127 ]; then
    mkdir $BIN_PATH
fi

$DESKTOP_PATH >/dev/null 2>&1
if [ $? -eq 127 ]; then
    mkdir $DESKTOP_PATH
fi

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

command -v pip >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    sudo apt-get install -y python-pip >/dev/null 2>&1
fi

python -c 'import pexpect' >/dev/null 2>&1
PEXPECT_INSTALLED=$?
python -c 'import ptyprocess' >/dev/null 2>&1
PTYPROCESS_INSTALLED=$?
if [ $PEXPECT_INSTALLED -eq 1 ]; then 
    echo "* Installing pexpect..."
    [[ $PTYPROCESS_INSTALLED -eq 1 ]] && ptyprocess='ptyprocess' || ptyprocess=''
    yes | pip install --user pexpect $ptyprocess >/dev/null 2>&1
fi

tosudoinstall=""

python -c 'import requests' >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    tosudoinstall+="python-requests "
fi

python -c 'import gobject' >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    tosudoinstall+="python-gobject-2 "
fi

python -c 'import gtk' >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    tosudoinstall+="python-gtk2 "
fi

# install avconv and ffmpeg if either of them is not installed
command -v avconv >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    tosudoinstall+="libav-tools "
fi

command -v ffmpeg >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    tosudoinstall+="ffmpeg "
fi

echo "* Installing dependencies: "$tosudoinstall

command -v crudini >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    tosudoinstall+="crudini"
fi

sudo apt-get -y install $tosudoinstall

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
command -v tboplayer >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    echo "* Creating tboplayer's bash executable..."
    FAKE_BIN=$HOME/bin/tboplayer
    echo '#!/bin/bash' >> $FAKE_BIN
    echo 'python $HOME/tboplayer/tboplayer.py' >> $FAKE_BIN
    chmod +x $FAKE_BIN
fi

# install tboplayer 'shortcut' in /home/<user>/Desktop

echo "* Creating shortcuts and configuring links..."
for DESKTOP_ENTRY in "${DESKTOP_ENTRIES[@]}"; do 
    $DESKTOP_ENTRY >/dev/null 2>&1
    if [ $? -eq 127 ]; then 
        sudo echo '[Desktop Entry]' >> $DESKTOP_ENTRY
        sudo echo 'Name=TBOPlayer' >> $DESKTOP_ENTRY
        sudo echo 'Comment=GUI for omxplayer' >> $DESKTOP_ENTRY
        sudo echo 'Exec=python '$HOME'/tboplayer/tboplayer.py %F' >> $DESKTOP_ENTRY
        sudo echo 'Icon=/usr/share/pixmaps/python.xpm' >> $DESKTOP_ENTRY
        sudo echo 'Terminal=false' >> $DESKTOP_ENTRY
        sudo echo 'Type=Application' >> $DESKTOP_ENTRY
        sudo echo 'Categories=Application;Multimedia;Audio;AudioVideo' >> $DESKTOP_ENTRY
    fi
done

for TYPE in "${SUPPORTED_TYPES[@]}"; do
	crudini --set $MIMEAPPS_FILE $MIMEAPPS_FILE_SECTION $TYPE 'tboplayer.desktop'
done

echo ""
echo "Installation finished."
echo ""
echo "If all went as expected, TBOPlayer is now installed in your system." 
echo "To run it, type 'tboplayer', use the shortcut created on your Desktop, or right-click on files."
echo "Oh, just keep the tboplayer folder in your "$HOME" directory, alright?"
echo ""
echo "Good bye! ;)"

exit
