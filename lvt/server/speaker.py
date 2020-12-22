import json
import numpy
from lvt.const import *
from lvt.logger import *
from lvt.config_parser import ConfigParser

config = None
speakers = list()

class Speaker():
    def __init__( this, speakerId: str, configParser: ConfigParser ):
        this.id = speakerId
        signature = configParser.getValue( '','Signature','' ).strip()
        if signature=='' : raise Exception('Speaker signature is empty!')
        this.signature = json.loads(signature)

        this.name = configParser.getValue( '','Name',this.id )
        this.isAdmin = configParser.getIntValue( '', 'isAdmin', 0 ) == 1
        this.email = configParser.getValue( '','email', '' )


    #AE:
    #"[-0.800343, -0.079754, 0.907916, -0.911662, -0.01827, -0.168988, -1.310563, 0.217542, 1.001637, -0.22366, 0.760771, -0.179475, -1.05431, -1.039141, 0.192834, 2.277963, -0.594372, -0.916277, 0.67152, -0.769247, -0.70349, 1.338736, 1.204222, -0.568933, 0.603721, -0.434536, 0.190351, -0.019267, 0.62543, 1.357455, 0.516207, 0.712414, -0.381085, 0.427275, 0.267805, -0.484057, 0.747862, 0.410925, -1.289279, 1.676354, 0.535761, 2.015226, 0.057726, -0.492759, -0.992763, 1.355041, -0.904212, -0.606851, 1.077859, 0.01794, 0.904881, -1.251879, -1.442968, -0.018171, -1.258005, -0.58755, 0.504154, -1.667491, 0.815391, -1.765759, 0.729279, 1.036985, 0.467473, -0.931371, 0.238916, -2.312919, -1.305942, -0.612098, 0.206966, 1.832786, 0.679575, -0.247768, 0.567782, 0.464405, 0.685292, 1.079421, -1.54797, -1.018179, 0.198541, -0.939351, -0.718197, -1.957607, 0.286658, -1.268528, 0.323914, 1.565329, -0.084974, 0.018533, 2.313831, -0.204035, -1.53383, -1.648837, -0.457461, -0.439878, 2.081445, 0.687917, 0.30277, -1.25863, -1.339996, 0.684349, -0.034564, 0.571533, -0.452907, -1.309047, -0.086544, -0.343441, 1.597392, 0.794652, -0.035544, -0.160157, -0.271667, -1.26356, 1.064623, 0.052934, 1.850854, -0.987842, -1.642487, 0.236515, 0.483037, -0.373637, -0.285813, 0.39387, 2.170987, -0.300359, -1.94123, 1.014977, 0.581055, 1.082886]"

    def initialize( gConfig ):
        """"""
        global config
        global speakers
        config = gConfig
        Speaker.loadDatabase()

    def dispose():
        pass

    def getSimilarity( x, y):
        nx = numpy.array(x)
        ny = numpy.array(y)
        return numpy.dot(nx, ny) / numpy.linalg.norm(nx) / numpy.linalg.norm(ny)

    def loadDatabase():
        """Кеширует список сигнатур в память для ускорения идентификации говорящих"""
        global config
        global speakers
        global diffAccuracy
        dir = os.path.join( 'lvt','speakers' )
        speakers = list()
        files = os.listdir( os.path.join( ROOT_DIR, dir ) )
        for file in files:
            path = os.path.join( dir, file )
            if os.path.isfile( path ) and file.lower().endswith( '.cfg' ):
                try: 
                    speakerId = os.path.splitext( file )[0].lower()
                    configParser = ConfigParser( path )
                    if configParser.getValue('','Enable','1') == '1':
                        speakers.append( Speaker( speakerId, configParser ) )
                    configParser = None
                except Exception as e:
                    printError( f'Exception loading  "{file}" : {e}' )
        for i in range(0,len(speakers)-1):
            for j in range(i+1,len(speakers)):
                d = Speaker.getSimilarity(speakers[i].signature, speakers[j].signature)
                if d > config.voiceSimilarity:
                    printDebug( f'{speakers[i].name} and {speakers[j].name} have similar voices: {d:.2f}. You may have identification issues')


    def identify( signature ):
        """Идентифицирует говорящего по сигнатуре. Возвращает None если говорящий не идентифицирован"""

        #printDebug(signature)

        if len(speakers)<1 : return None

        diff = list()
        for speaker in speakers:
            diff.append( [ Speaker.getSimilarity(speaker.signature, signature ), speaker ] )

        diff.sort( key=lambda s:s[0], reverse=True)
        #for d in diff: printDebug(f'{d[1].name}: diff={d[0]}')

        # Идентифицирован?
        # Проверка на минимально допустимый уровень похожести
        if diff[0][0] < config.voiceSimilarity : return None

        # Проверка на селективность оценки
        if len(diff)>1 and diff[0][0]-diff[1][0] < config.voiceSelectivity: return None
        printDebug(f'Говорит {diff[0][1].name}')
        return diff[0][1]
