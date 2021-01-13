# Lite Voice Terminal

### Disclaimer: "����� ���������������" ������ � �������� ����������

Lite Voice Terminal is free open source client-server platform for powering up DIY offline "lite" smart speaker for Russian language.
�Lite� means lite speaker is built on hardware with limited computational power like RaspberryPi Zero / Zero W
"Offline" means voice recognition services are provided by on-premise ASR server.

Lite Voice Terminal ��� ������-��������� ��������� � �������� ����� ��� �������� "������" ����� �������, 
�� ��������� ������������� ������-�������� ��� ������������� ������.

��� ������ "������" ���������� ����������� ���������� � ������ "�����" �������, 
������� ����� ���� ����������� �� Raspberry ZeroW ��� �������� ����������� ���������� � ���������� 
�������������� ���������� � ������������ ������ �����

������������� ������ ��� ���� ��������� ������������� �������� ������. ��������������, ��� ������
�� ���� Intel Core i3 / 16Gb ���������� ��� ��������� �� 10-20 ����������.

### ����������� (������������� � ����������� � ����������)

- [x] ������ LVT ����� �������� ��� ��� unix (RaspberryPi � ����������) ��� � �� windows ���������
- [ ] ���������� LVT ������� �� HTML/JScript 
- [x] �� ������� ������������� ������� ������ ��������
- [x] ����� ����� ���������� � ��������� ������ ����������� �� ��������� websock � ���������� SSL
- [x] �� ������� ����������� ��������� ��������� ��������� (��� snowboy), ��� (��������� ����) ���������� 
������ ����������� � ����� ���������. � ����� �� ������������� � ����� ���������� (�������/�������)
- [ ] ������������� ���������� �� ������ (�������� ������ �� ���������� ������� ������, �� ������� ������ ���������)
- [x] ����������� ���������� ������� ���������� �� ���� ��������� ����� ������� 
- [x] ������������� � �������������� ���� ��� ������������� ������� � ������������ ������������� ����� �������� �� ����. � ���� �� ����� ������������, ����� �� ������� �������� �����...
- [x] �������������� � ������������ �� ��������� **MQTT**: �� ������� ������ �������� ������ �������� ���������
- [x] ���������� � ������� **MajorDoMo**: ����������� ��������� ������ ��������� ����� �������������� php ������, ����� ���� ������������ ����� ��������� ��������������� � LVT ���� ������ ���������� ������������ ����� ��� ��������� � ������� ��)
- [ ] ������������ ��������� ������� **MdmTerminal2**
- [x] ������ ������� LVT �� Unix
- [ ] ������ ������� LVT �� Windows
- [x] RHVoice TTS
- [ ] Windows TTS


### ��� ���������� LVT ������������ ��������� ���������� � ������:

* [kaldi](https://github.com/alphacep/kaldi): ������-������������� ����
* [vosk API](https://github.com/alphacep/vosk-ap): ����������� ��������� ��� kaldi
* [pymorphy2](https://github.com/kmike/pymorphy2): ��������������� ���������� ��� �������� � ����������� ������
* [RHVoice](https://github.com/Olga-Yakovleva/RHVoice):  ������ ������ ��� �������� �����
* [APA102](https://pypi.org/project/apa102): ���������� ������������ ������
* [WebRTC VAD](https://github.com/wiseman/py-webrtcvad): ����������� ������� ������ �� ������� ������
* [ReSpeaker components](https://github.com/respeaker): �������������� � ���������� � ������ ��������� ������
* [mdmTerminal2](https://github.com/Aculeasis/mdmTerminal2): ����� ���� � ���� �������������� �� ���������� ���������� ��������� MajorDoMo

### ������������
 * [��������� � ��������� ������� LVT](https://github.com/mosave/LVTerminal/blob/master/docs/Configuration%20-%20Server.md)
 * [��������� � ��������� ��������� LVT](https://github.com/mosave/LVTerminal/blob/master/docs/Configuration%20-%20Terminal.md)
 * ������� ���������� ����������
    * [Raspberry Pi3 A+ � Respeaker 4 MIC](https://github.com/mosave/LVTerminal/tree/master/hardware/RPi%203A%2B%20with%20Respeaker4/readme.md)
    * [Raspberry Pi ZeroW � Respeaker 4 MIC Linear Array](https://github.com/mosave/LVTerminal/tree/master/hardware/RPi%20Zero%20with%20Respeaker4%20Linear%20Array/readme.md)
    * [Raspberry Pi ZeroW � Respeaker 2 MIC](https://github.com/mosave/LVTerminal/tree/master/hardware/RPi%20Zero%20with%20Respeaker2/readme.md)
 * [�������� ��������� LVT](https://github.com/mosave/LVTerminal/blob/master/docs/LVT%20-%20Protocol.md)
 * [���������� ������� (skill, �����)](https://github.com/mosave/LVTerminal/blob/master/docs/Skill%20-%20Development.md)
 * []()

## License

LVT is distributed under [LGPL v2.1](https://www.gnu.org/licenses/lgpl-2.1.html) or later.
Components and API used may be a subject of other licenses.

