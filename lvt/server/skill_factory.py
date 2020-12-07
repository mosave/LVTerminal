import sys
import importlib
from lvt.const import *
from lvt.server.grammar import *
from lvt.server.skill import Skill

class SkillFactory():
    def __init__( this, terminal ):
        this.terminal = terminal
        pass
    def loadSkills( this ) -> list():
        """Returns list of skill instances.
          * Scans lvt/skills directory recursively
          * Loads all module found there
          * Creates instance of every lvt.skill.Skill successor class
        """
        this.skills = list()
        this.skillCount = 0
        this.skillErrors = 0
        this.loadSkillsFromDir(
            os.path.join( ROOT_DIR,'lvt','server','skills' ), 
            "lvt.server.skills"
        )
        this.skills.sort( key = lambda s:s.priority, reverse=True)
        return this.skills

    def loadSkillsFromDir( this, directory:str, prefix:str ):
        """Recursively Load modules starting from folder specified and place Skill instancess in this.skills
        """
        dirsAndFiles = os.listdir( directory )
        for fileName in dirsAndFiles:
            filePath = os.path.join( directory,fileName )
            moduleName, ext = os.path.splitext(fileName)
            moduleName = prefix + '.' + moduleName

            if os.path.isdir( filePath ) and not fileName.startswith( '.' ) :
                # recursively scan for subdirectories ignoring those started
                # with "."
                this.loadSkillsFromDir( filePath, moduleName )
            elif os.path.isfile( filePath ) and ext == '.py':
                try: # Try load module file and search for Skill successors
                    module = importlib.import_module( moduleName, filePath )
                    #Search for Skill successors and place instance in
                    for className in dir( module ):
                        try:
                            cls = getattr( module, className )
                            if this.isSkillClass( cls ) :
                                this.skills.append( cls( this.terminal, filePath, className ) )
                            this.skillCount += 1
                        except Exception as e:
                            this.skillErrors += 1
                            this.terminal.logError( f'Exception creating class {moduleName}.{className}: {e}' )
                except Exception as e:
                    this.skillErrors += 1
                    this.terminal.logError( f'Exception loading module {moduleName}: {e}' )

    def isSkillClass( this, cls ):
        if not hasattr( cls, '__name__' ) or not hasattr( cls, '__base__' ) : return False
        base = cls.__base__
        while base != None :
            if str( base.__name__ ) == 'Skill': return True
            base = base.__base__

