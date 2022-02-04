import sys
import os
import shlex
from shutil import copyfile
from lvt.const import *

iLine = 0
iSection = 1
iVarName = 2
iValue = 3
iValue2 = 4

class ConfigParser:
    """Parse config-like files
    Properties:
      * sections: set of unique section names in "SectionName|SectionId"  format
                    SectionId technically is line number where section starts
      * values: list of values parsed. Each record have following format:
                [ Line number, Section Name, Variable Name, Value, Value 2, .....  ]
    """
    def __init__( self, fileName:str, allowKeysOnly=False ):
        global CONFIG_DIR
        if not os.path.isabs(fileName):
            fileDir, fileName =  os.path.split(fileName)
            if not fileDir: fileDir = CONFIG_DIR
            self.fileName = os.path.join( fileDir, fileName )
        else:
            self.fileName = fileName

        with open( self.fileName, "r", encoding='utf-8' ) as f:
            lines = list( f.readlines() )
        self.sections = set()
        self.values = []
        section = '|1'
        for line in range( len( lines ) ):
            lex = shlex.shlex( lines[line], posix=True )
            lex.wordchars += 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя'
            a = list( lex )
            # New section name detected
            if ( len( a ) == 3 ) and ( a[0] == '[' ) and ( a[-1] == ']' ) :
                section = a[1]
                i = 2
                while i < len( a ) - 1:
                   section += a[i]
                   i += 1
                section = section.replace( '|','' ) + '|' + str( line )
            elif ( len( a ) > 0 ) :
                row = [line + 1, section.lower(), a[0].lower()]
                for i in range(1,len(a)):
                    if i>1 or a[i]!='=': row.append( a[i] )

                self.values.append( row )
                self.sections.add( section )

        self.sections = list( self.sections )

    def getRawValue( self, section: str, key: str ):
        """Retrieve single (first appearing) raw value (string or list of strings) returning None if not found
          * section: could be both "SectionName" or "SectionName|SectionId", case-insensitive
          * key: parameter name, case-insensitive
          * default: string value to return if parameter not found
        """
        section = section.strip().replace( ' ','' ).lower()
        if section.find( '|' ) < 0 :
            section += '|'
            searchWithId = False
        else:
            searchWithId = True
        
        value = None
        for v in self.values:
            selfSection = (v[iSection] == section) if searchWithId else (v[iSection].startswith( section ))
            if( selfSection and v[iVarName] == key.strip().lower() ):
                if( len(v)>iValue2 ) :
                    value = v[iValue:]
                elif( len(v)>iValue ) :
                    value = str( v[iValue] )
                break
        return value

    def getValue( self, section: str, key: str, default: str=None ) -> str:
        """Retrieve single (first appearing) value as string, using default if not specified
          * section: could be both "SectionName" or "SectionName|SectionId", case-insensitive
          * key: parameter name, case-insensitive
          * default: string value to return if parameter not found
        """
        value = self.getRawValue( section, key )
        if( isinstance(value, list)) :
            return ' '.join(value)
        elif value != None:
            return value
        return default

    def getIntValue( self, section: str, key: str, default: int ) -> int:
        """Retrieve single (first appearing) value as integer, using default value if not specified
          * section: could be both "SectionName" or "SectionName|SectionId", case-insensitive
          * key: parameter name, case-insensitive
          * default: string value to return if parameter not found
        """
        return int( self.getValue( section, key, str(default) ) )

    def getFloatValue( self, section: str, key: str, default: float ) -> int:
        """Retrieve single (first appearing) value as integer, using default value if not specified
          * section: could be both "SectionName" or "SectionName|SectionId", case-insensitive
          * key: parameter name, case-insensitive
          * default: string value to return if parameter not found
        """
        return float( self.getValue( section, key, default ) )

    def getRawValues( self, section: str ) -> dict:
        """Retrieve all RAW values (str or list(str)) for specific section(s) as dictionary
          * section: could be both "SectionName" or "SectionName|SectionId", case-insensitive
          * key: parameter name, case-insensitive
        """
        section = section.strip().replace( ' ','' ).lower()
        if section.find( '|' ) < 0 :
            section += '|'
            searchWithId = False
        else:
            searchWithId = True

        values = dict()
        #values['section']=(section+'|0').split('|')[0]
        #values['sectionId']=(section+'|0').split('|')[1]

        for v in self.values:
            selfSection = (v[iSection] == section) if searchWithId else (v[iSection].startswith( section ))

            if selfSection:
                if len(v)>iValue2 :
                    value = v[iValue:]
                elif len(v)>iValue :
                    value = str( v[iValue] )
                else:
                    value = None
                values[v[iVarName]] = value
        return values

    def getValues( self, section: str ) -> dict:
        """Retrieve all values for specific section(s) as dictionary
          * section: could be both "SectionName" or "SectionName|SectionId", case-insensitive
          * key: parameter name, case-insensitive
          * default: string value to return if parameter not found
        """
        values = self.getRawValues(section)
        for name in values:
            if isinstance(values[name], list):
                values[name] = ' '.join(values[name])
        return values

    def setConfigDir( gConfigDir ):
        global CONFIG_DIR
        CONFIG_DIR = gConfigDir


    def checkConfigFiles( files: list() ) :
        defaultConfigDir = os.path.join( ROOT_DIR ,'config.default' )
        if defaultConfigDir == CONFIG_DIR : return
        for fn in files :
            if not os.path.exists( os.path.join( CONFIG_DIR, fn ) ) :
                print(f'Файл ./config/{fn} не найден. Копирую ./config.default/{fn}')
                copyfile(os.path.join( defaultConfigDir,fn ), os.path.join( CONFIG_DIR,fn ))



