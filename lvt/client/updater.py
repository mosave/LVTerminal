import sys
import os
import time
from lvt.const import *
import lvt.client.config as config


def updateClient( package ):
    targetDir = ROOT_DIR
    #targetDir = 'C:\\Buffer\\3'
    try:
        print()
        print('Updating LVT Client files')
        for file in package:
            print(f'    {file[0]}')
            dir = os.path.abspath( os.path.join( targetDir, file[0]) )
            if dir.startswith( targetDir ) :
                with open( dir, "w", encoding='utf-8' ) as f:
                    f.writelines(file[1])
            else:
                print(f'Hack attempt detected!!!')
        print()
        print('All files updated successfuly')
        return True
    except Exception as e:
        print(f'Error updating files: {e}')
        return False
