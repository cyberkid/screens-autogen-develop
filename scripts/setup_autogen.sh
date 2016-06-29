#!/bin/bash

echo "This script will install and set up what you need for autogen screens"

echo "You must have the file: autogen.tar.gz in your Downloads folder"
read -p "Hit <enter> or <return> to continue"

echo "easy installing pip"

sudo easy_install pip

echo "Now installing virtualenv"
sudo pip install virtualenv

echo "Ensuring directory ~/screens"
mkdir -p ~/screens

echo "cd to ~/screens/"

cd ~/screens/

echo "Checking for autogen.tar.gz"
if [ -e $HOME//Downloads/autogen.tar.gz ];
then
    echo "File autogen.tar.gz exists in ~/Downloads/"
else
    echo "Missing!"
    read -p "Missing required file: 'autogen.tar.gz' in Downloads directory"
    cd -
    return
fi

echo "Extracting code from tarball autogen.tar.gz"
/usr/bin/tar -zxvf ~/Downloads/autogen.tar.gz

echo "Done - look for errors"
cd -
