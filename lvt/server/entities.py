from lvt.const import *
from lvt.logger import *
from lvt.protocol import *
import lvt.server.config as config
from lvt.config_parser import CONFIG_DIR, ConfigParser
from lvt.server.grammar import *


#region
class EntityDefinition():
    def __init__( self, id: str, terminalId: str, definition: str ):
        self.id = str(id).lower()
        self.terminalId = str(terminalId).lower() if terminalId else ''
        self.definition = definition
        self.parses = parseText(definition)
        self.key=''

        self.len = len(self.parses)
        for w in self.parses: self.key += w[0].lexeme[0].word

    def __lt__(self, other):
        return self.len > other.len


class Entity():
    def __init__( self ):
        self.definitions : list[EntityDefinition] = list()

    def add( self, id: str, terminalId: str, definitions):
        if isinstance(definitions, list):
            for definition in definitions:
                self.definitions.append( EntityDefinition(id, terminalId, str(definition)) )
        else:
            self.definitions.append( EntityDefinition(id, terminalId, str(definitions)) )

    def sort(self):
        self.definitions = sorted( self.definitions, key=lambda e: (e.terminalId if e.terminalId!=None else '' ), reverse=True )
        self.definitions = sorted( self.definitions, key=lambda e: e.len, reverse=True )

    def getVocabulary( self, tags = None ) -> set[str]:
        voc =  set()
        for d in self.definitions:
            voc.update( wordsToVocabulary( d.definition, tags) )

        return voc


#endregion


__entities = dict()

def init( ):
    """Initialize module'  """
    global __entities

    files = [f for f in os.listdir( CONFIG_DIR ) if os.path.isfile( os.path.join( CONFIG_DIR, f))  ]

    for fileName in files :
        entityName, ext = os.path.splitext(fileName)
        entityName = str(entityName).lower()
        if ext.lower() == '.entity':
            __entities[entityName] = __loadEntity(fileName)

    #acronyms = Entities.load( 'acronyms' )
    #locations = Entities.load( 'locations' )
    #vocabulary = Entities.load( 'vocabulary' )
        
def get( entityName : str, terminalId: str = '' ) -> Entity:
    global __entities
    entityName = str(entityName).lower()
    terminalId = str(terminalId).lower() if terminalId else ''
    tEntity = Entity()

    if entityName in __entities: 
        entity = __entities[entityName]
        for d in entity.definitions: 
            if d.terminalId=='' or d.terminalId==terminalId :
                isNew = bool(len([e for e in tEntity.definitions if e.key == d.key ])==0)
                if isNew : 
                    tEntity.definitions.append(d)
    return tEntity


def __loadEntity( fileName: str ) -> Entity:
    entity = Entity()
    p = ConfigParser( fileName )

    for section in p.sections:
        defs = p.getRawValues(section)
        prefix = fileName
        terminalId = section.split('|')[0]
        if terminalId:
            prefix = f'{prefix}#{terminalId}'
            terminalId = terminalId.lower()
            if terminalId in config.terminals :
                for eId in defs:
                    if len(str(eId))==0 or str(eId)=='=' :
                        fatalError(f"{prefix}: Неверный ID \"{eId}\"")
                    if defs[eId] == None :
                        fatalError(f"{prefix}: Отсутствует название сущности")
                    entity.add( eId, terminalId, defs[eId])
            else:
                logError(f'{prefix}: неверный ID терминала ("{terminalId}"), секция пропущена')

    entity.sort()
    return entity
