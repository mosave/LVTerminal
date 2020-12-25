# Lite Voice Terminal

Lite Voice Terminal is free open source client-server platform for powering up DIY offline "lite" smart speaker for Russian language.
�Lite� means lite speaker is built on hardware with limited computational power like RaspberryPi Zero / Zero W
"Offline" means voice recognition services are provided by on-premise ASR server.

Lite Voice Terminal ��� ������-��������� ��������� � �������� ����� ��� �������� "������" ����� �������, 
�� ��������� ������������� ������-�������� ��� ������������� ������.

��� ������ "������" ���������� ����������� ���������� � ������ ����� �������, 
������� ����� ���� ����������� �� Raspberry Zero/ZeroW ��� �������� ����������� ���������� � ������������ ���������� 
�������������� ���������� � ������������ ������ �����

������������� ������ ��� ���� ��������� ������������� �������� ������. ��������������, ��� ������
�� ���� Intel Core i3 / 16Gb ���������� ��� ��������� �� 10-20 ����������.

### ����������� (������������� � ����������� � ����������)
* �� ������� ������������� ������� ������ ��������
* ����� ����� ���������� � ��������� ������ ����������� �� ��������� websock � ���������� SSL
* ������������� ���������� �� ������
* ����������� ���������� ������� ���������� �� ���� ��������� ����� ������� 
* �������������� � ������������ �� MQTT ��������� (?)
* ���������� � MajorDoMo (?)

### ��� ���������� LVT ������������ ��������� ���������� � ������:

* [kaldi](https://github.com/alphacep/kaldi): ������-������������� ����
* [vosk API](https://github.com/alphacep/vosk-ap): ����������� ��������� ��� kaldi
* [pymorphy2](https://github.com/kmike/pymorphy2): ��������������� ���������� ��� �������� � ����������� ������
* [RHVoice](https://github.com/Olga-Yakovleva/RHVoice):  ������ ������ ��� �������� �����
* [APA102](https://pypi.org/project/apa102): ���������� ������������ ������
* [WebRTC VAD](https://github.com/wiseman/py-webrtcvad): ����������� ������� ������ �� ������� ������
* [ReSpeaker components](https://github.com/respeaker): �������������� � ���������� � ������ ��������� ������
* [mdmTerminale](https://github.com/Aculeasis/mdmTerminal2): ����� ���� � ���� �������������� �� ���������� ���������� ��������� MajorDoMo

## License

LVT is distributed under [LGPL v2.1](https://www.gnu.org/licenses/lgpl-2.1.html) or later.
Components and API used may be a subject of other licenses.

