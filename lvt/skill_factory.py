import os
import sys
import importlib
from lvt.const import *

class SkillFactory:
    """Dynamically scans skill modules and creates Skill instances"""
    def __init__( this, terminal ):
        this.skillDir = os.path.abspath( os.path.join( ROOT_DIR,'lvt/skills/' ) )
        this.terminal = terminal

    def loadAllSkills( this ) -> list():
        """Returns list of skill instances.

          * Scans /lvt/skills directory recursively
          * Loads all module found there
          * Creates instance of every lvt.skill.Skill successor class
        """
        this.skills = list()
        this.loadSkillsFromDir( this.skillDir )
        return this.skills

    def loadSkillsFromDir( this, dir:str ):
        """Recursively Load modules starting from folder specified and place Skill instancess in this.skills
        """
        dirsAndFiles = os.listdir( dir )
        for fileName in dirsAndFiles:
            fullName = os.path.join( dir,fileName )

            if os.path.isdir( fullName ) and not fileName.startswith( '.' ) :
                # recursively scan for subdirectories ignoring those started
                # with "."
                this.loadSkillsFromDir( os.path.join( dir,fileName ) )
            elif os.path.isfile( fullName ) and fileName.lower().endswith( '.py' ):
                try: # Try load module file and search for Skill successors
                    prefix = dir[len( this.skillDir ):].replace( '/','.' ).replace( '\\','.' )
                    moduleName = f'lvt.skills{prefix}.{fileName[:-3]}'
                    module = importlib.import_module( moduleName, fullName )
                    module.ROOT_DIR = ROOT_DIR
                    #Search for Skill successors and place instance in
                    #this.skills
                    this.loadSkillsFromModule( module, moduleName )

                except Exception as e:
                    print( f'Exception loading module {moduleName}: {e}' )
                    pass

    def loadSkillsFromModule( this, module, moduleName ):
        for className in dir( module ):
            try:
                cls = getattr( module, className )
                if this.isSkillClass( cls ) :
                    this.skills.append( cls( this.terminal ) )
            except Exception as e:
                print( f'Exception creating class {moduleName}.{className}: {e}' )

    def isSkillClass( this, cls ):
        if not hasattr( cls, '__name__' ) or not hasattr( cls, '__base__' ) : return False
        base = cls.__base__
        while base != None :
            if str( base.__name__ ) == 'Skill': return True
            base = base.__base__






