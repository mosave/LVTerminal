Update all

Install respeaker drivers: 
https://github.com/SeeedDocument/Seeed-WiKi/blob/master/docs/ReSpeaker_4_Mic_Array_for_Raspberry_Pi.md


sudo apt install python3-pip

sudo pip3 install websockets
sudo apt-get install python3-pyaudio
sudo pip3 install webrtcvad
sudo apt install python3-numpy
sudo apt-get install python3-spidev
sudo apt-get install python3-gpiozero

raspi-config, включить spi

pip3 install webrtcvad





1. Install as a service

sudo cp lvt_client /etc/init.d
chmod 755 /etc/init.d/lvt_client

Create symbolic link to start service:
sudo update-rc.d lvt_client defaults


sudo /etc/init.d/lvt_client start
sudo /etc/init.d/lvt_client stop
sudo /etc/init.d/lvt_client status