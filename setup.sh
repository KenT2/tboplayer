#!/bin/bash

echo "Installing TBOPlater and its dependencies..."
echo "*"
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

python -c 'import requests' >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    echo "* Installing requests..."
    sudo apt-get install -y python-requests >/dev/null 2>&1
fi

python -c 'import gobject' >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    echo "* Installing gobject..."
    sudo apt-get install -y python-gobject-2 >/dev/null 2>&1
fi

python -c 'import gtk' >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    echo "* Installing gtk..."
    sudo apt-get install -y python-gtk2 >/dev/null 2>&1
fi

# install avconv and ffmpeg if either of them is not installed
command -v avconv >/dev/null 2>&1
AVCONV_INSTALLED=$?
command -v ffmpeg >/dev/null 2>&1
FFMPEG_INSTALLED=$?
if [ $AVCONV_INSTALLED -eq 1 ] || [ $FFMPEG_INSTALLED -eq 1 ]; then
    echo "* Installing avconv and ffmpeg..."
    sudo apt-get -y install libav-tools ffmpeg >/dev/null 2>&1
else
    echo "* Updating avconv and ffmpeg..."
    sudo apt-get -y --only-upgrade install libav-tools ffmpeg >/dev/null 2>&1
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

~/bin >/dev/null 2>&1
if [ $? -eq 127 ]; then
    mkdir ~/bin
fi

# install fake tboplayer executable in /home/<user>/bin
command -v tboplayer >/dev/null 2>&1
if [ $? -eq 1 ]; then 
    echo "* Installing tboplayer..."
    FAKE_BIN=~/bin/tboplayer
    mv ~/KenT2-tboplayer-* ~/tboplayer
    echo '#!/bin/bash' >> $FAKE_BIN
    echo 'python ~/tboplayer/tboplayer.py' >> $FAKE_BIN
    chmod +x $FAKE_BIN
fi

# install tboplayer 'shortcut' in /home/<user>/Desktop
DESKTOP_ENTRY=~/Desktop/tboplayer.desktop
$DESKTOP_ENTRY >/dev/null 2>&1
if [ $? -eq 127 ]; then 
    echo "* Creating shortcut in desktop..."
    echo '[Desktop Entry]' >> $DESKTOP_ENTRY
    echo 'Name=TBOPlayer' >> $DESKTOP_ENTRY
    echo 'Comment=UI for omxplayer' >> $DESKTOP_ENTRY
    echo 'Exec=python '$HOME'/tboplayer/tboplayer.py "%F"' >> $DESKTOP_ENTRY
    echo 'Icon=/usr/share/pixmaps/python.xpm' >> $DESKTOP_ENTRY
    echo 'Terminal=false' >> $DESKTOP_ENTRY
    echo 'Type=Application' >> $DESKTOP_ENTRY
fi

echo "* Installation finished."
echo "*"
echo "* If all went as expected, TBOPlayer is now installed in your system." 
echo "* To run it, type 'tboplayer', or use the shortcut created on your Desktop."
echo "* Oh, just keep the tboplayer folder in your "$HOME" directory, alright?"
echo "*"
echo "Good bye! ;)"

exit;
