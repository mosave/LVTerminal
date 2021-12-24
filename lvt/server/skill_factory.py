import sys
import importlib
from lvt.const import *
from lvt.logger import *
from lvt.server.grammar import *
import lvt.server.config as config
from lvt.server.skill import Skill

class SkillFactory():
    def __init__( self, terminal ):
        self.terminal = terminal
        pass
    def loadSkills( self ) -> list():
        """Returns list of skill instances.
          * Scans lvt/skills directory recursively
          * Loads all module found there
          * Creates instance of every lvt.skill.Skill successor class
        """
        self.skills = list()
        self.skillCount = 0
        self.skillErrors = 0
        self.loadSkillsFromDir(
            os.path.join( ROOT_DIR,'lvt','server','skills' ), 
            "lvt.server.skills"
        )
        self.skills.sort( key = lambda s:s.priority, reverse=True)
        return self.skills

    def loadSkillsFromDir( self, directory:str, prefix:str ):
        """Recursively Load modules starting from folder specified and place Skill instancess in self.skills
        """
        dirsAndFiles = os.listdir( directory )
        for fileName in dirsAndFiles:
            filePath = os.path.join( directory,fileName )
            moduleName, ext = os.path.splitext(fileName)
            moduleName = prefix + '.' + moduleName

            if os.path.isdir( filePath ) and not fileName.startswith( '.' ) :
                # recursively scan for subdirectories ignoring those started
                # with "."
                self.loadSkillsFromDir( filePath, moduleName )
            elif os.path.isfile( filePath ) and ext == '.py':
                try: # Try load module file and search for Skill successors
                    module = importlib.import_module( moduleName, filePath )
                    #Search for Skill successors and place instance in
                    for className in dir( module ):
                        try:
                            cls = getattr( module, className )
                            if self.isSkillClass( cls ) :
                                sn = className.lower()
                                cfg = config.skills[sn] if sn in config.skills else {'enable':True}
                                if cfg['enable'] :
                                    self.skills.append( cls( self.terminal, filePath, className, cfg ) )
                                    self.skillCount += 1
                                else:
                                    self.terminal.logDebug(f'Skill "{className}" disabled in configuration')
                        except Exception as e:
                            self.skillErrors += 1
                            self.terminal.logError( f'Exception creating class {moduleName}.{className}: {e}' )
                except Exception as e:
                    self.skillErrors += 1
                    self.terminal.logError( f'Exception loading module {moduleName}: {e}' )

    def isSkillClass( self, cls ):
        if not hasattr( cls, '__name__' ) or not hasattr( cls, '__base__' ) : return False
        base = cls.__base__
        while base != None :
            if str( base.__name__ ) == 'Skill': return True
            base = base.__base__

