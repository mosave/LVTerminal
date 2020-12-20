import sys
import os
import time
from lvt.const import *

config = None
shared = None

class Updater:
    def initialize( gConfig, gShared ):
        global config
        global shared
        config = gConfig
        shared = gShared

    def __init__( this ):
        pass

    def update(this, package ):
        targetDir = ROOT_DIR
        #targetDir = 'C:\\Buffer\\3'
        try:
            print()
            print('Updating LVT Client files')
            for file in package:
                print(f'    {file[0]}')
                with open( os.path.join( targetDir, file[0]), "w", encoding='utf-8' ) as f:
                    f.writelines(file[1])
            print()
            print('Files updated. Shutting down client...')
            shared.isTerminated = True
            time.sleep(5);
            print('Restarting...')
            os.execl(sys.executable, f'"{format(sys.executable)}"', *sys.argv)
        except Exception as e:
            print(f'Error updating client files: {e}')

