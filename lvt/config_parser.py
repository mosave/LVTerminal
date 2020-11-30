import sys
import os
import shlex

class ConfigParser:
    def __init__( this, fileName ):
        with open( fileName, "r", encoding='utf-8' ) as f:
            lines = list( f.readlines() )
        this.sections = set()
        this.values = []
        section = ''
        for i in range( len( lines ) ):
            a = list( shlex.shlex( lines[i], posix=True ) )
            if ( len( a ) == 3 ) and ( a[0] == '[' ) and ( a[2] == ']' ) :
                section = a[1].lower()
            elif ( len( a ) > 1 ) :
                row = [i + 1, section, a[0].lower()]
                p = 2 if a[1] == '=' else 1
                for j in range( p, len( a ) ): row.append( a[j] )

                this.values.append( row )
                this.sections.add( section )
            elif len( a ) > 0:
                print( lines[i] )
                print( len( a ) )
                raise Exception( f'Error parsing "{fileName}", line {(i+1)}' )
        this.sections = list( this.sections )

    def getValue( this, section: str, key: str, default: str ) ->str:
        for v in this.values:
            if( v[1] == section.strip().lower() and v[2] == key.strip().lower() ):
                value = str( v[3] )
                for i in range( 4,len( v ) ): value+=' ' + v[i]
                return value
        return default

    def getIntValue( this, section: str, key: str, default: int ) -> int:
        return int( this.getValue( section, key, str( default ) ) )

    def getValues( this, section: str ) ->dict():
        values = dict()
        for v in this.values:
            if( v[1] == section.strip().lower() ):
                value = str( v[3] )
                for i in range( 4,len( v ) ): value+=' ' + v[i]
                values[v[2]] = value
        return values
