import sys
import os
import shlex
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

        with open( os.path.join( ROOT_DIR, fileName), "r", encoding='utf-8' ) as f:
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

    def getValue( this, section: str, key: str, default: str=None ) -> str:
        """Retrieve single (first appearing) value as string, using default if not specified
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
        
        for v in this.values:
            thisSection = (v[iSection] == section) if searchWithId else (v[iSection].startswith( section ))

            if( thisSection and v[iVarName] == key.strip().lower() ):
                value = str( v[iValue] )
                for i in range( iValue2, len( v ) ): value+=' ' + v[i]
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

    def getValues( this, section: str ) -> dict():
        """Retrieve all values for specific section(s) as dictionary
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
        values['section']=(section+'|0').split('|')[0]
        values['sectionId']=(section+'|0').split('|')[1]

        for v in this.values:
            thisSection = (v[iSection] == section) if searchWithId else (v[iSection].startswith( section ))

            if thisSection:
                value = str( v[iValue] )
                for i in range( iValue2, len( v ) ): value+=' ' + v[i]
                values[v[iVarName]] = value
        return values
