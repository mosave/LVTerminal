#instll win32com:
#pip3 install pywin32

import win32com.client
speaker = win32com.client.Dispatch("SAPI.SpVoice")
stream = win32com.client.Dispatch("SAPI.SpFileStream")
voices = speaker.GetVoices();
print(voices)
print(voices.Item(0).GetAttribute("Name"))
for v in voices:
    print(v.GetAttribute("Name"))

speaker.Voice = voices.Item(0)
speaker.Rate = 0
speaker.Volume = 100

# Create
stream.Open( 'C:\\Buffer\\1\\asdf2.wav', 3 )
speaker.AudioOutputStream = stream
speaker.Speak("Jump! Jump now!!! Прыгай же давай скорее!")


