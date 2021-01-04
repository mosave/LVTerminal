Update all

Install respeaker drivers: 
https://github.com/SeeedDocument/Seeed-WiKi/blob/master/docs/ReSpeaker_4_Mic_Array_for_Raspberry_Pi.md


sudo apt install python3-pip

sudo pip3 install websockets
sudo apt-get install python3-pyaudio
sudo apt install python3-numpy

1. Install as a service

sudo cp lvt_server /etc/init.d
chmod 755 /etc/init.d/lvt_server

Create symbolic link to start service:
sudo update-rc.d lvt_server defaults


sudo /etc/init.d/lvt_server start
sudo /etc/init.d/lvt_server stop
sudo /etc/init.d/lvt_server status