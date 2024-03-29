### Установка софта и настройка клиента LVT терминала

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
```passwd
sudo passwd
```
5. raspi-config:
  * set host name
  * time zone
  * locale: en_GB.UTF8 + ru_RU.CP1251 + ru_RU.UTF-8 + ....
  * keyboard
  * enable SPI
  * enable I2C
  * expand file system
6.
```
sudo apt-get update
sudo apt-get upgrade
sudo apt-get autoremove
sudo apt-get autoclean
```

7. sudo apt-get install htop mc p7zip git


8. Устанавливаем драйвера Respeaker2:
    описание здесь:  https://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT_Raspberry/
```
    sudo apt-get update
    git clone https://github.com/HinTak/seeed-voicecard
    cd seeed-voicecard
    sudo ./install.sh
    sudo reboot now
```
9. Копируем LVTerminal на RPi. Для работы клиента необходимы следующие файлы:
  * lvt_client.py
  * lvt/*
  * lvt/client/*
  * config/client.cfg  (в качестве шаблона можно использовать config.default/client.cfg)
  * logs/
  

10. Устанавливаем Python3 и необходимые библиотеки для запуска терминального клиента:
    '''
    sudo apt-get install python3 python3-venv python3-pyaudio python3-alsaaudio python3-numpy libatlas-base-dev 

    '''

    Скрипт **lvt_client.sh** сам создает virtual environment и устанавливает необходимые зависимости.
    '''
    cd LVTerminal
    ./lvt_client.sh
    '''

    Однако если по какой-то причине вы решите сделать это самостоятильно либо не использовать virtual_env - клиентская часть LVT зависит от следующих модулей:

    * pyaudio
    * pyalsaaudio (только для управления громкостью)
    * aiohttp
    * webrtcvad
    * rhvoice_wrapper 
    * numpy
    * spidev

11. Добиваемся чтобы клиент запускался, подключался к серверу и "слышал" звук
  * ./lvt_client.py --help    # подсказка по параметрам командной строки
  * ./lvt_client.py --devices # получить список аудиоустройств, которые при необходимости можно задавать 
       в параметрах AudioInputDevice и AudioOutputDevice

12. Проверяем и настраиваем уровень звука с микрофонов:
  * Для объективного контроля можно в server.cfg выставить параметр VoiceLogLevel = 3
     Это приведет к тому, что в каталоге logs будут сохраняться все звуковые фрагменты, полученные от клиентов.
  * В одной терминальной сессии запускаем client, в другой alsamixer и подбираем уровень микрофона "оптимальным" образом,
     то есть уровень звука (SNR) при нормальной громкости речи находится в диапазоне от 500-2000 а сохраняемый 
     при этом звук при прослушивании хорошо слышен и не имеет искажений
  * При наличии нескольких микрофонов можно включить алгоритм выбора канала с наиболее близким к оптимальному
     уровнем звука (параметр **MicSelection="RMS"** в файле конфигурации клиента).
     В этом случае имеет смысл выставить на каналах разные уровни чувствительности микрофона
  * Сохранить текущие настройки громкости и загрузить их:
  ```
     sudo alsactl --file=/home/pi/asound.state store
     sudo alsactl --file=/home/pi/asound.state restore
  ```
     Восстановление настроек можно добавить в /etc/rc.local

13. Запуск терминального клиента как сервис

   В файле scripts/lvt_client поправить путь установки LVTerminal (переменная **DIR**) и имя пользователя, под которым будет запускаться сервис:
   DIR=**/home/pi/LVTerminal**
   DAEMON_USER=**pi**
```
   sudo cp ./scripts/lvt_client /etc/init.d
   sudo chmod 755 /etc/init.d/lvt_client
   sudo update-rc.d lvt_client defaults
```
Управление сервисом:
```
   sudo systemctl start lvt_client
   sudo systemctl stop lvt_client
   sudo systemctl status lvt_client
```



