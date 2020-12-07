import json
import sys
import time
import datetime
import rhvoice_wrapper # https://pypi.org/project/rhvoice-wrapper/
from lvt.const import *
from lvt.server.grammar import *
from lvt.config_parser import ConfigParser

config = None

########################################################################################
class Entities():
    """Terminal class
    Properties
      * id: Unique terminal Id, used for client identification
      * password: Password for client identification
      * name: terminal name, speech-friendly Id
      * speaker: Speaker object containing last speaking person details if available
    """
    def __init__( this ):
        this.acronyms = []
        this.assistant_names = []
        this.devices = []
        this.locations = []
        this.actions = this.loadEntity( "actions" )
        this.loadAll()

    def loadAll( this ):
        this.acronyms = this.loadEntity( "acronyms" )
        this.assistanm_names = this.loadEntity( "assistant_names" )
        #this.devices = this.loadEntity( "devices" )
        #this.locations = this.loadEntity( "locations" )
        #this.actions = this.loadEntity( "actions" )

    def load( this, entityFileName ):
        entities = list()
        p = ConfigParser( os.path.join( 'lvt','server','entities', entityFileName ) )
        for v in p.values:
            entity = list()
            for i in range( 2,len( v ) ):
                entity.append( v[i] )
            entities.append( entity )
        return entities


    def joinEntity( this, entity ):
        pass

#region
    def initialize( gConfig ):
        """Initialize module' config variable for easier access """
        global config
        config = gConfig

#endregion
