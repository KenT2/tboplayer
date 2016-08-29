#!/bin/bash

TBOPLAYER_PATH=/opt/tboplayer
SCRIPT_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BIN_PATH=$HOME/bin
DESKTOP_PATH=$HOME/Desktop
FAKE_BIN=$BIN_PATH/tboplayer
SUPPORTED_TYPES=('application/ogg' 'video/ogg' 'audio/ogg' 
		'video/mpeg' 'audio/mpeg' 'video/mp4' 'audio/x-aac' 
		'video/3gp' 'video/3gpp2' 'video/quicktime' 'video/x-f4v' 
		'video/flv' 'audio/x-wav' 'video/x-msvideo')
DESKTOP_ENTRIES=($DESKTOP_PATH/tboplayer.desktop 
		/usr/share/applications/tboplayer.desktop)
MIMEAPPS_FILE=$HOME/.config/mimeapps.list
MIMEAPPS_FILE_SECTION='Added Associations'

# uninstall TBOPlayer
if [ "$1" == "uninstall" ]; then
    echo ""
    echo "Do you really wish to uninstall TBOPlayer? [Y/N]" 
    read answer
    if [ "$answer" == "Y" ] || [ "$answer" == "y" ]; then
	echo ""
        echo "* Removing TBOPlayer..."
        sudo rm -Rf $TBOPLAYER_PATH
	rm -f $FAKE_BIN
	rm -f "${DESKTOP_ENTRIES[0]}" 
        sudo rm -f "${DESKTOP_ENTRIES[1]}" 
        for TYPE in "${SUPPORTED_TYPES[@]}"; do
            crudini --del "$MIMEAPPS_FILE" "$MIMEAPPS_FILE_SECTION" $TYPE >/dev/null 2>&1
        done
        echo ""
        echo "Would you like to remove all of TBOPlayer dependencies too? [Y/N]" 
        read answer
        if [ "$answer" == "Y" ] || [ "$answer" == "y" ]; then
            echo ""
            echo "* Removing TBOPlayer dependencies..."
            yes | pip uninstall pexpect ptyprocess >/dev/null 2>&1
            sudo apt-get -y remove python-gobject-2 python-gtk2 python-requests crudini >/dev/null 2>&1
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

mkdir $BIN_PATH >/dev/null 2>&1
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
addToAptInstall "gtk" "python-gtk2" true
addToAptInstall "avconv" "libav-tools" false

echo "* Installing dependencies: "$toaptinstall

addToAptInstall "pip" "python-pip" false
addToAptInstall "crudini" "crudini" false

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
    yes | pip install --user magic >/dev/null 2>&1
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
command -v tboplayer >/dev/null 2>&1
if [ $? -eq 0 ]; then 
	rm $FAKE_BIN
fi

echo "* Creating tboplayer's bash executable..."
echo '#!/bin/bash' >> $FAKE_BIN
echo 'python '$TBOPLAYER_PATH'/tboplayer.py' >> $FAKE_BIN
chmod +x $FAKE_BIN

# install tboplayer 'shortcut' in /home/<user>/Desktop

echo "* Creating shortcuts and configuring links..."
DESKTOP_ENTRY="${DESKTOP_ENTRIES[0]}"
$DESKTOP_ENTRY >/dev/null 2>&1
if [ $? -eq 126 ]; then 
	rm $DESKTOP_ENTRY
fi

echo '[Desktop Entry]' >> $DESKTOP_ENTRY
echo 'Name=TBOPlayer' >> $DESKTOP_ENTRY
echo 'Comment=GUI for omxplayer' >> $DESKTOP_ENTRY
echo 'Exec=python '$TBOPLAYER_PATH'/tboplayer.py %F' >> $DESKTOP_ENTRY
echo 'Icon=/usr/share/pixmaps/python.xpm' >> $DESKTOP_ENTRY
echo 'Terminal=false' >> $DESKTOP_ENTRY
echo 'Type=Application' >> $DESKTOP_ENTRY
echo 'Categories=Application;Multimedia;Audio;AudioVideo' >> $DESKTOP_ENTRY

sudo cp $DESKTOP_ENTRY "${DESKTOP_ENTRIES[1]}"

for TYPE in "${SUPPORTED_TYPES[@]}"; do
    crudini --set "$MIMEAPPS_FILE" "$MIMEAPPS_FILE_SECTION" $TYPE 'tboplayer.desktop'
done

echo ""
echo "Installation finished."
echo ""
echo "If all went as expected, TBOPlayer is now installed in your system." 
echo "TBOPlayer can be found at the "$TBOPLAYER_PATH" directory."
echo "To run it, type 'tboplayer', use the shortcut created on your Desktop, or open a file directly by double clicking on it, or using the right-click menu, when using your file manager."
echo ""
echo "Good bye! ;)"

exit
