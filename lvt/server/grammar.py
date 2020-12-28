import pymorphy2

morphy = None

class Grammar():
    """Just to export static initialization method uniformly"""
    def initialize( gConfig ):
        #global config
        global morphy
        #config = gConfig
        morphy = pymorphy2.MorphAnalyzer( lang=gConfig.language )
        pass

def changeGender( tags, gender ) :
    try:
        t = set( tags ) if tags != None else {}
        t.discard( 'masc' )
        t.discard( 'femn' )
        t.discard( 'neut' )
        t.add( gender )
    except:
        t = {gender}
    return t

def parseWord( word: str ):
    """Parse word using phmorphy2 library"""
    global morphy
    return morphy.parse( word )

#def inflectWord( word: str, tags ):
#    """Parse word using phmorphy2 library"""
#    global morphy
#    return morphy.parse (word)

def conformToNumber( this, number: int, word: str ) -> str:
    """Согласовать слово с числом"""
    return transcribeNumber( number ) + ' ' + parseWord( word )[0].make_agree_with_number( number ).word

def transcribeNumber999( number: int, tags=None ):
    if tags == None : tags = {'nomn'}

    s1 = {1:'один', 2:'два', 3:'три', 4:'четыре', 5:'пять', 6:'шесть', 7:'семь', 8:'восемь', 9:'девять', 0:''}
    s2 = {2:'двадцать', 3:'тридцать', 4:'сорок', 5:'пятьдесят',6:'шестьдесят', 
          7:'семьдесят', 8:'восемьдесят',9:'девяносто'}
    s3 = {1:'сто', 2:'двести', 3:'триста', 4:'четыреста', 5:'пятьсот', 6:'шестьсот',
          7:'семьсот', 8:'восемьсот', 9:'девятьсот'}
    tsat = {10:'десять', 11:'одиннадцать', 12:'двенадцать', 13:'тринадцать',14:'четырнадцать',
          15:'пятнадцать', 16:'шестнадцать', 17:'семнадцать',18:'восемнадцать', 19:'девятнадцать'}
    s = str( number )
    p = []
    if len( s ) > 1:
        if 9 < int( s[-2:] ) < 20:
            p.append( tsat[int( s[-2:] )] )
        elif int( s[-2:] ) > 19:
            p.append( s1[int( s[-1] )] )
            p.append( s2[int( s[-2] )] )
    else:
        if int( s[-1] ) > 0:
            p.append( s1[int( s[-1] )] )
        else:
            p.append( 'ноль' )
    if len( s ) == 3:
        p.append( s3[int( s[-3] )] )
    for i in range( len( p ) ):
        w = parseWord( p[i] )[0].inflect( tags )
        if w != None : p[i] = w.word

    transcription = ' '.join( p[::-1] )
    return transcription
    
def transcribeNumber( number: int, tags=None, word: str='' ):
    if tags == None : tags = {'nomn'}
    s = ''
    if number < 0 :
        s = 'минус '
        number = -number

    if number > 999999999:
        s += 'больше миллиарда '
        if word != '' : s += parseWord( word )[0].inflect( tags ).word
        return s.strip()

    if number > 999999:
        n = int( number / 1000000 )
        if n > 0 :
            t = changeGender( tags, 'masc' )
            w = parseWord( 'миллионов' )[0].inflect( t ).make_agree_with_number( n ).word
            s += transcribeNumber999( n, t ) + ' ' + w + ' '
        number = number % 1000000

    if number > 999:
        n = int( number / 1000 )
        if n > 0 :
            t = changeGender( tags, 'femn' )

            w = parseWord( 'тысяч' )[0].inflect( t ).make_agree_with_number( n ).word
            s += transcribeNumber999( n, t ) + ' ' + w + ' '
        number = number % 1000

    if s.strip() == '' or number > 0 :
        s = s + transcribeNumber999( number, tags ) + ' '

    if word != '' :
        w = parseWord( word )[0].inflect( tags )
        if w == None : w = parseWord( word )[0]
        s += w.make_agree_with_number( number ).word

    return s.strip()

def transcribeTime( tm, tags=None ):
    return \
        transcribeNumber( tm.hour,{'nomn'},'часов' ) + ' ' + \
        transcribeNumber( tm.minute, {'nomn'}, 'минут' )

def transcribeDate( dt, tags=None ):
    weekdays = {0:'понедельник', 1:'вторник',2:'среда',3:'четверг',4:'пятница',5:'суббота',6:'воскресенье'}
    months = {1:'января', 2:'февраля',3:'марта',4:'апреля',5:'мая',6:'июня',7:'июля', \
                8:'августа',9:'сентября',10:'октября',11:'ноября',12:'декабря' }

    # Пока не смог полностью победить склонение числительных
    n2 = {1:'первое', 2:'второе', 3:'третье', 4:'четвертое', 5:'пятое', 6:'шестое', 7:'седьмое', \
        8:'восьмое', 9:'девятое', 10:'десятое', 11:'одиннадцатое',12:'двенадцатое',\
        13:'тринадцатое',14:'четырнадцатое',15:'пятнадцатое',16:'шестнадцатое',\
        17:'семнадцатое',18:'восемнадцатое',19:'девятнадцатое',20:'двадцатое',30: 'тридцатое'}
    n1 = {2:'двадцать',3:'тридцать'}

    dow = weekdays[dt.weekday()]
    month = months[dt.month]

    if dt.day in n2 :
        d2 = n2[dt.day]
        d1 = ''
    else:
        d2 = n2[dt.day%10]
        d1 = n1[int(dt.day/10)]


    if tags != None : 
        w = parseWord(d2)[0].incline(tags)
        if w != None : d2 = w.word
        w = parseWord(dow)[0].incline(tags)
        if w != None : dow = w.word
        w = parseWord(month)[0].incline(tags)
        if w != None : month = w.word

    #TODO: добавить год, если дата отличается от текущей больше чем на 3 месяца
    day = f'{d1} {d2}'.strip()
    return f'{dow}, {day} {month}'.strip()



def normalizePhrases( phrases ) -> str:
    """Возвращает нормальизованный список (через запятую) нормализованных цепочек слов (через пробел)
    Пример "включи свет,выключи свет,сделай что-то"
    """
    allowed_chars = 'abcdefghijklmnopqrstuvxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя 1234567890-,'
    phrases = phrases.lower()
    cleaned = ''
    for ch in phrases: cleaned += ch if ch in allowed_chars else ' '
    while True: 
        _ = cleaned
        cleaned = cleaned.replace( '  ',' ' ).replace( ' ,',',' ).replace( ', ',',' ).replace( ',,',',' ).strip()
        if cleaned == _ :break

    while cleaned.startswith( ',' ) : cleaned = cleaned[1:]
    while cleaned.endswith( ',' ) : cleaned = cleaned[:-1]
    return cleaned

def normalizeWords( words ) -> str:
    """Returns space-separated list of words properly cleaned up and filtered"""
    return normalizePhrases( words ).replace( ',',' ' )

def oneOfPhrases( phrase, phrases ) -> bool:
    """Возвращает True если искомая фраза phrase присутствует в списке фраз phrases """
    phrase = normalizeWords( phrase )
    phrases = normalizePhrases( phrases )
    if len( phrase ) == 0 or len( phrases ) == 0 : return False
    return bool( ( ',' + phrases + ',' ).find( ',' + phrase + ',' ) >= 0 )

def oneOfWords( word, words ) -> bool:
    """Возвращает True если слово word присутствует в списке слов words """
    word = normalizeWords( word )
    words = normalizeWords( words )
    if len( word ) == 0 or len( words ) == 0 : return False
    return bool( ( ' ' + words + ' ' ).find( ' ' + word + ' ' ) >= 0 )

def prasesToList( phrases ) -> [str]:
    """Преобразует список разделенных через запятую фраз в массив (list()) """
    return phrases.lower().replace( '  ',' ' ).replace( ', ',',' ).strip().split( ',' )

def wordsToList( words ) -> [str]:
    """Возвращает список слов в виде массива слов (list())"""
    return words.lower().replace( ',',' ' ).replace( '  ',' ' ).strip().split( ' ' )

def joinWords( words, words2 ) -> str:
    """Объединяет два набора слов с дедупликацией"""
    words = normalizeWords( words )
    words2 = wordsToList( words2 )
    for w in words2:
        if ( ' ' + words + ' ' ).find( ' ' + w + ' ' ) < 0 :
            words += ' ' + w
    return words.strip()


def wordsToVocabulary( words, tags=None ) :
    """Расширить словарь словами с генерацией словоформ для заданных тегов
    По умолчанию (теги не заданы) в словарь добавляется только переданные словоформы
    Принимает списки слов в виде строк либо массивов строк (рекурсивно)
    """
    vocabulary = set()
    if isinstance( words, list ) :
        for word in words : 
            vocabulary.update( wordsToVocabulary( word ) )
    elif isinstance( words, str ):
        for w in wordsToList( words ) :
            if tags != None : # Ищем первый разбор удовлетворяющий тегам
                parses = parseWord( w )
                parse = [p for p in parses if tags in p.tag]
                parse = parses[0] if len( parse ) <= 0 else parse[0]
                # Получаем множество лексем на базе выбранного разбора слова
                lexemes = set( [l.word for l in parse.lexeme if tags in l.tag] )
                #Добавляем лексемы в словарь
                vocabulary.update( lexemes )
            else: 
                vocabulary.add( w )
    return vocabulary



def wordsToVocabularyAllForms( words, tags=None ) :
    """Расширить словарь словами с генерацией словоформ для заданных тегов.
    По умолчанию (теги не заданы) в словарь добавляется все возможные словоформы
    Принимает списки слов как в виде строк так и в виде массивов (рекурсивно)"""
    vocabulary = set()
    if isinstance( words, list ) :
        for word in words : 
            vocabulary.update( wordsToVocabularyAllForms( word ) )
    elif isinstance( words, str ):
        for w in wordsToList( words ) :
            parses = parseWord( w )
                
            if tags != None : # Ищем первый разбор удовлетворяющий тегам
                parse = [p for p in parses if tags in p.tag]
                parse = parses[0] if len( parse ) <= 0 else parse[0]
            else: # Берем первый разбор
                parse = parses[0]

            # Получаем множество лексем на базе выбранного разбора слова
            lexemes = set( [l.word for l in parse.lexeme if ( tags == None ) or tags in l.tag] )
            #Добавляем лексемы в словарь
            vocabulary.update( lexemes )

    return vocabulary

