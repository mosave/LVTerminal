import sys
import time
import datetime
import json
from lvt.const import *
from lvt.logger import *
from lvt.protocol import *
from lvt.config_parser import ConfigParser
from lvt.server.grammar import *

config = None
vocabulary = None
acronyms = None
locations = None

### class Location() ###################################################################
#region
class Location():
    def __init__( this, id: str, names ):
        this.id = id
        this.names= names if isinstance(names, list) else [names]
    @property
    def name(this):
        return names[0]

#endregion
    


class Entities():
    """Entities class. Single-instance in-memory world facts
    """
### Entities initialization ############################################################
#region
    def __init__( this ):
        pass
#endregion
### Properties & Methods ###############################################################
#region
    @property
    def vocabulary( this ) -> list:
        """Базовый словарь"""
        global vocabulary
        return vocabulary
    @property
    def acronyms( this ) -> list:
        """Список акронимов"""
        global acronyms
        return acronyms

    @property
    def locations( this ) -> list:
        """Список локаций"""
        global locations
        return locations

    def findLocation( this, location: str ) -> str:
        location = normalizeWords( location )
        for l in this.locations:
            if location in l: return(l[0])
        return None

### Static methods #####################################################################
#region
    def initialize( gConfig ):
        """Initialize module' config variable for easier access """
        global config
        global vocabulary
        global acronyms
        global locations

        acronyms = Entities.load( 'acronyms' )
        locations = Entities.load( 'locations' )
        vocabulary = Entities.load( 'vocabulary' )
        
        config = gConfig

    def dispose():
        pass

    def load( entityFileName ):
        entities = list()
        p = ConfigParser( entityFileName )
        for v in p.values:
            entity = list()
            for i in range( 2,len( v ) ):
                entity.append( v[i] )
            entities.append( entity )
        return entities
#endregion
