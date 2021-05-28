** Установка софта и настройка клиента LVT сервера

Технически LVT сервер можно запустить и на старших моделях Raspberry Pi (4/4B) и он будет "тянуть" 
пару одновременно подключенных терминалов при условии использовании "облегченной" голосовой модели
(размер модели ~85MB).

Однако для использования полной голосовой модели (3.5GB) или при необходимости подключения большего 
количества терминалов рекомендуется разворачивать сервер на более мощном железе. Как показала 
практика, сервер на базе Intel i3 с объемом RAM 16GB обеспечивает нормальную скорость работы при 
параллельном распознавании с 6-7 терминалов, при этом общее количество терминалов может быть 
гораздо больше. 


*** 1. Движок распознавания речи [Kaldi](http://kaldi-asr.org/doc)

Официальная процедура установки kaldi [находится здесь](http://kaldi-asr.org/doc/install.html)

Но поскольку мы будем использовать kaldi в связке с Vosk API, то воспользуемся несколько измененной
процедурой, описанной [на официальном сайте Vosk](https://alphacephei.com/vosk/).
Вот что у меня получилось в результате:

```
cd /opt
git clone -b lookahead-1.8.0 --single-branch https://github.com/alphacep/kaldi
cd /opt/kaldi/tools
git clone -b v0.3.13 --single-branch https://github.com/xianyi/OpenBLAS
git clone -b v3.2.1  --single-branch https://github.com/alphacep/clapack
make -C OpenBLAS ONLY_CBLAS=1 DYNAMIC_ARCH=1 TARGET=NEHALEM USE_LOCKING=1 USE_THREAD=0 all
make -C OpenBLAS PREFIX=$(pwd)/OpenBLAS/install install
mkdir -p clapack/BUILD && cd clapack/BUILD && cmake .. && make -j 10 && find . -name "*.a" | xargs cp -t ../../OpenBLAS/install/lib
cd /opt/kaldi/tools
git clone --single-branch https://github.com/alphacep/openfst openfst
cd openfst
autoreconf -i
CFLAGS="-g -O3" ./configure --prefix=/opt/kaldi/tools/openfst --enable-static --enable-shared --enable-far --enable-ngram-fsts --enable-lookahead-fsts --with-pic --disable-bin
make -j 10 && make install
cd /opt/kaldi/src
./configure --mathlib=OPENBLAS_CLAPACK --shared --use-cuda=no
sed -i 's:-msse -msse2:-msse -msse2:g' kaldi.mk
sed -i 's: -O1 : -O3 :g' kaldi.mk
make -j $(nproc) online2 lm rnnlm
```

Для заинтересованных: скомпилировать Kaldi под Windows у меня тоже получилось. Процедура для Windows 
несколько сложнее, мне для этого потребовалась полная версия Microsoft Visual Studio 2019 (НЕ Visual Studioo Code) 
и подгонка под него файлов проекта. Однако после сборки Kaldi под Windows я не смог заставить работать 
Vosk API. Возможно, я еще вернусь к этой задаче - но позже :)


*** 2. Устанавливаем и настраиваем [Vosk API](https://github.com/alphacep/vosk-api)

Описание процедуры установки [на официальном сайте Vosk](https://alphacephei.com/vosk/]

```
cd /opt/
git clone https://github.com/alphacep/vosk-api
cd vosk-api/src
KALDI_ROOT=/opt/kaldi make
cd ../python
python3 setup.py install
```

*** 3. Скачиваем голосовые модели для kaldi

 * Большая подборка моделей лежит [здесь](https://alphacephei.com/vosk/models)
 * Официальный список моделей [на сервере Kaldi](http://kaldi-asr.org/models.html)

Для информации: Облегченная модель для русского языка (в отличие от полной модели) 
поддерживает возможность ограничения активного словаря. Это позволяет значительно 
повысить надежность распознавания в режиме "со словарем", поэтому LVT поддерживает
динамическое переключение между двумя моделями а режим "со словарем" можно задать
в качестве основного в настройках.

*** 4. Устанавливаем необходимые Python библиотеки

sudo apt install python3-pip python3-websockets python3-psutil python3-pyaudio
sudo pip3 install pymorphy2 hbmqtt numpy rhvoice_wrapper

sudo apt-get install python3-pyaudio
sudo apt install python3-numpy

1. Install as a service

sudo cp lvt_server /etc/init.d
sudo chmod 755 /etc/init.d/lvt_server

Create symbolic link to start service:
sudo update-rc.d lvt_server defaults


sudo /etc/init.d/lvt_server start
sudo /etc/init.d/lvt_server stop
sudo /etc/init.d/lvt_server status





Windows 10, Speech API, голос MS Pavel не доступен для использования в приложениях.
Решение здесь: https://stackoverflow.com/questions/53804721/how-to-get-and-use-full-installed-text-to-speech-languages-list