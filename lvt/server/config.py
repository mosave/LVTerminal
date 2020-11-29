import sys
import time
import os
import psutil
from lvt.config_parser import ConfigParser

class Config:
    def __init__(this, fileName):
        p = ConfigParser ( fileName )
        section=""
        this.serverAddress = p.getValue(section, "ServerAddress","0.0.0.0")
        this.serverPort = p.getIntValue(section, "ServerPort",2700)
        this.sslCertFile = p.getValue(section, "SSLCertFile","")
        this.sslKeyFile = p.getValue(section, "SSLKeyFile","")
        this.model = p.getValue(section, "Model","model")
        this.fullModel = p.getValue(section, "Model",this.model)
        this.spkModel = p.getValue(section, "SpkModel","")
        this.sampleRate = p.getIntValue(section, "SampleRate",8000)
        this.recognitionThreads = p.getIntValue(section, "RecognitionThreads",os.cpu_count())
        if( this.recognitionThreads < 1  ): this.recognitionThreads = 1

        this.assistantName = p.getValue(section, "AssistantName","") \
            .replace(',',' ').replace('  ',' ').strip().replace(' ',', ')

        if( len(this.assistantName.strip()) == 0): 
            raise Exception('AssistantName should be specified')

        this.confirmationPhrases = p.getValue(section, "ConfirmationPhrases","да, хорошо, согласен, да будет так") \
            .lower().replace('  ',' ').replace(', ',',')

        this.cancellationPhrases = p.getValue(section, "CancellationPhrases","нет, отмена, стоп, стой") \
            .lower().replace('  ',' ').replace(', ',',')

        tts = p.getValue(section, "VoiceEngine","RHVoice")
        if( tts.lower().strip() == "rhvoice"):
            this.ttsEngine = 0
        else:
            raise Exception("Invalid voice engine specified")


    def getJson( this, terminals=None ):
        # '1.20MB', '1.17GB'...
        def formatSize(bytes, suffix="B"):
            factor = 1024
            for unit in ["", "K", "M", "G", "T", "P"]:
                if bytes < factor:
                    return f"{bytes:.2f}{unit}{suffix}"
                bytes /= factor

        cpufreq = psutil.cpu_freq()
        svmem = psutil.virtual_memory()

        js = '{'
        js += f'"Model":"{this.model}",'
        js += f'"FullModel":"{this.fullModel}",'
        js += f'"SpkModel":"{this.spkModel}",'
        js += f'"SampleRate":"{this.sampleRate}",'
        js += f'"RecognitionThreads":"{this.recognitionThreads}",'
        js += f'"AssistantName":"{this.assistantName}",'
        js += f'"VoiceEngine":"{this.ttsEngine}",'
        if terminals != None :
            activeClients = 0
            for t in terminals: activeClients+= 1 if t.isActive else 0
            js += f'"TotalClients":"{len(terminals)}",'
            js += f'"ActiveClients":"{activeClients}",'
        js += f'"CpuCores":"{os.cpu_count()}",'
        js += f'"CpuFreq":"{cpufreq.current:.2f}Mhz",'
        js += f'"CpuLoad":"{psutil.cpu_percent()}%",'
        js += f'"MemTotal":"{formatSize(svmem.total)}",'
        js += f'"MemAvail":"{formatSize(svmem.available)}",'
        js += f'"MemUsed":"{formatSize(svmem.used)}",'
        js += f'"MemLoad":"{svmem.percent}%"'+'}'
        return js
       

