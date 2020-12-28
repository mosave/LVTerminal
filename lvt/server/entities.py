import sys
import time
import datetime
import json
from lvt.const import *
from lvt.logger import *
from lvt.protocol import *
from lvt.config_parser import ConfigParser
from lvt.server.grammar import *
from lvt.server.skill import Skill
from lvt.server.skill_factory import SkillFactory

config = None
vocabulary = None
acronyms = None
locations = None
devices = None

class Entities():
    """Entities class. Single-instance in-memory world facts
    """
### Entities initialization ############################################################
#region
    def __init__( this ):
        pass
#endregion
### Properties #########################################################################
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

    @property
    def devices( this ) -> list:
        """Список локаций"""
        global devices
        return devices
### Static methods #####################################################################
#region
    def initialize( gConfig ):
        """Initialize module' config variable for easier access """
        global config
        global vocabulary
        global acronyms
        global locations
        global devices

        vocabulary = Entities.load( 'vocabulary' )
        acronyms = Entities.load( 'acronyms' )
        locations = Entities.load( 'locations' )
        devices = Entities.load( 'devices' )
        
        config = gConfig

    def dispose():
        pass

    def load( entityFileName ):
        entities = list()
        p = ConfigParser( os.path.join( 'lvt','entities', entityFileName ) )
        for v in p.values:
            entity = list()
            for i in range( 2,len( v ) ):
                entity.append( v[i] )
            entities.append( entity )
        return entities
#endregion
