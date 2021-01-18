***
Update all

Мой выбор - raspbian.
1. Записываем флешку с помощью Raspberry Pi Imager
2. На FAT раздел копируем два файла:
  * wpa_supplicant.conf. Конфигурация WiFi.
    Необходимо поправить значение параметров (кавычки обязательны):
    ssid="Имя WiFi сети"
    psk="Пароль к WIFI сети"

  * пустой файл с именем ssh - включение SSH доступа
3. Вставляем флешку в RaspberryPi и включаем ее. На роутере смотрим, какой адрес получила RPi 
   и подключаемся к нему с помощью любого ssh клиента (I love PuTTY). 
   Пользователь "pi", пароль по умолчанию "raspberry"
4. Меняем пароль для пользователя pi и root:
   passwd
   sudo passwd
5. raspi-config:
 * set host name
 * time zone
 * locale: en_GB.UTF8 + ru_RU.CP1251 + ru_RU.UTF-8 + ....
 * keyboard
 * enable SPI
 * enable I2C
 * expand file system
6. sudo apt-get update
   sudo apt-get upgrade
   sudo apt-get autoremove
   sudo apt-get autoclean

7. Устанавливаем драйвера Respeaker: 
   https://github.com/SeeedDocument/Seeed-WiKi/blob/master/docs/ReSpeaker_4_Mic_Array_for_Raspberry_Pi.md
 * git clone https://github.com/respeaker/seeed-voicecard.git
 * cd seeed-voicecard
 * sudo ./install.sh
 * sudo reboot
  
8. Устанавливаем Python3 и необходимые библиотеки для запуска терминального клиента:

 * sudo apt-get install python3-pip
 * sudo pip3 install websockets
 * sudo apt-get install python3-pyaudio
 * sudo pip3 install webrtcvad
 * sudo apt-get install python3-numpy
 * sudo apt-get install python3-spidev
 * sudo apt-get install python3-gpiozero

9. Копируем LVTerminal на RPi. Для работы клиента необходимы следующие файлы:
 * client.py
 * lvt/*
 * lvt/client/*
 * config/client.cfg  (в качестве шаблона можно использовать config.default/client.cfg)
 * logs/

10. Добиваемся чтобы клиент запускался, подключался к серверу и "слышал" звук
 * ./client.py --help    # подсказка по параметрам командной строки
 * ./client.py --devices # получить список аудиоустройств, которые при необходимости можно задавать 
   в параметрах AudioInputDevice и AudioOutputDevice

9. Проверяем и настраиваем уровень звука с микрофонов:
 * Для объективного контроля можно в server.cfg выставить параметр StoreAudio = 1
   Это приведет к тому, что в каталоге logs будут сохраняться все звуковые фрагменты, полученные от клиентов.
 * В одной терминальной сессии запускаем client, в другой alsamixer и подбираем уровень микрофона "оптимальным" образом,
   то есть уровень звука (SNR) при нормальной громкости речи находится в диапазоне от 500-2000 а сохраняемый 
   при этом звук при прослушивании хорошо слышен и не имеет искажений
 * Если в client.cfg параметр 
 * Сохранить текущие настройки громкости и загрузить их:
   sudo alsactl --file=/home/pi/asound.state store
   sudo alsactl --file=/home/pi/asound.state restore

10. Запуск терминального клиента как сервиса

sudo cp ./scripts/lvt_client /etc/init.d
chmod 755 /etc/init.d/lvt_client

Create symbolic link to start service:
sudo update-rc.d lvt_client defaults


sudo /etc/init.d/lvt_client start
sudo /etc/init.d/lvt_client stop
sudo /etc/init.d/lvt_client status
