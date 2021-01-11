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
    def __init__( this, fileName:str, allowKeysOnly=False ):
        this.fileName = fileName

        with open( os.path.join( CONFIG_DIR, fileName), "r", encoding='utf-8' ) as f:
            lines = list( f.readlines() )
        this.sections = set()
        this.values = []
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

                this.values.append( row )
                this.sections.add( section )

        this.sections = list( this.sections )

    def getRawValue( this, section: str, key: str ):
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
        for v in this.values:
            thisSection = (v[iSection] == section) if searchWithId else (v[iSection].startswith( section ))
            if( thisSection and v[iVarName] == key.strip().lower() ):
                if( len(v)>iValue2 ) :
                    value = v[iValue:]
                elif( len(v)>iValue ) :
                    value = str( v[iValue] )
                break
        return value

    def getValue( this, section: str, key: str, default: str=None ) -> str:
        """Retrieve single (first appearing) value as string, using default if not specified
          * section: could be both "SectionName" or "SectionName|SectionId", case-insensitive
          * key: parameter name, case-insensitive
          * default: string value to return if parameter not found
        """
        value = this.getRawValue( section, key )
        if( isinstance(value, list)) :
            return ' '.join(value)
        elif value != None:
            return value
        return default

    def getIntValue( this, section: str, key: str, default: int ) -> int:
        """Retrieve single (first appearing) value as integer, using default value if not specified
          * section: could be both "SectionName" or "SectionName|SectionId", case-insensitive
          * key: parameter name, case-insensitive
          * default: string value to return if parameter not found
        """
        return int( this.getValue( section, key, default ) )

    def getFloatValue( this, section: str, key: str, default: int ) -> int:
        """Retrieve single (first appearing) value as integer, using default value if not specified
          * section: could be both "SectionName" or "SectionName|SectionId", case-insensitive
          * key: parameter name, case-insensitive
          * default: string value to return if parameter not found
        """
        return float( this.getValue( section, key, default ) )

    def getRawValues( this, section: str ) -> dict():
        """Retrieve all RAW values (str or list(str)) for specific section(s) as dictionary
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

        values = dict()
        #values['section']=(section+'|0').split('|')[0]
        #values['sectionId']=(section+'|0').split('|')[1]

        for v in this.values:
            thisSection = (v[iSection] == section) if searchWithId else (v[iSection].startswith( section ))

            if thisSection:
                if len(v)>iValue2 :
                    value = v[iValue:]
                elif len(v)>iValue :
                    value = str( v[iValue] )
                else:
                    value = None
                values[v[iVarName]] = value
        return values

    def getValues( this, section: str ) -> dict():
        """Retrieve all values for specific section(s) as dictionary
          * section: could be both "SectionName" or "SectionName|SectionId", case-insensitive
          * key: parameter name, case-insensitive
          * default: string value to return if parameter not found
        """
        values = this.getRawValues(section)
        for name in values:
            if isinstance(values[name], list):
                values[name] = ' '.join(values[name])
        return values

    def checkConfigFiles( files: list() ) :
        defaultConfigDir = os.path.join( ROOT_DIR ,'config.default' )
        for fn in files :
            if not os.path.exists( os.path.join( CONFIG_DIR, fn ) ) :
                print(f'Файл ./config/{fn} не найден. Копирую ./config.default/{fn}')
                copyfile(os.path.join( defaultConfigDir,fn ), os.path.join( CONFIG_DIR,fn ))
       


