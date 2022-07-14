from argparse import ArgumentError
import math
import pymorphy2

from lvt.logger import logError
# PyMorphy2: 
# https://pymorphy2.readthedocs.io/en/stable/user/guide.html
#
morphy = pymorphy2.MorphAnalyzer( lang='ru' )

#region PyMorphy parse*, transcribe*, normalFormOf, inflect*, conform ######################
def parseWord( word: str ):
    """Parse word using phmorphy2 library"""
    word_chars = 'abcdefghijklmnopqrstuvxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    number_chars = '+-.1234567890'
    global morphy

    wrd = str(word).strip().lower()
    w = ""
    f = ""
    for ch in wrd: 
        if ch in word_chars: w += ch
        if ch in number_chars: f += ch
    
    p = morphy.parse( w if len(w)>0 else f )
    p[0].originalWord = str(word).strip()
    return p

def parseText( text ):
    """Convert text to array of parsed words"""
    global morphy
    allowed_chars = ' abcdefghijklmnopqrstuvxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя1234567890-+.\u0301'
    words = ""
    for ch in text: words += ch if ch.lower() in allowed_chars else ' '
    text = words.replace( ',',' ' ).replace( '  ',' ' ).strip().split( ' ' )
    parsedText = list()
    for w in text:
        if bool(w):
            parses = parseWord( w )
            #Проигнорировать предикативы, наречия, междометия и частицы
            #if {'PRED'} not in parses[0].tag and {'ADVB'} not in parses[0].tag
            #and {'INTJ'} not in parses[0].tag and {'PRCL'} not in
            #parses[0].tag :

            #Проигнорировать междометия
            if {'INTJ'} not in parses[0].tag :
                parsedText.append( parses )

    return parsedText

def transcribeAndParseText( text: str ):
    parses = parseText(text)
    result = list()
    for p in parses:
        if 'NUMB' in p[0].tag:
            parses2 = parseText(transcribeNumber( int(p[0].word) if 'intg' in p[0].tag else float(p[0].word) ))
            for p2 in parses2:
                p2[0].originalWord = p2[0].word
                result.append(p2)
        else:
            result.append(p)

    return result

def transcribeText( text: str ):
    parses = transcribeAndParseText(text)
    text = ''
    for p in parses: text += p[0].originalWord+' '
    return text.strip()

def normalFormOf( word: str, tags=None ) -> str:
    """Возвращает нормальную форму слова с учетом морфологических признаков"""
    parses = parseWord( word )
    for p in parses:
        if ( tags is None ) or tags in p.tag: 
            return p.normal_form#.replace( 'ё', 'e' )
    return ''

def inflectText( text: str, tags) -> str:
    """Склоняет переданных текст в соответствии с тегами"""
    words = parseText( text )
    text = ""
    for p in words:
        w = p[0].inflect(tags)
        text += (w.word if w is not None else p[0].originalWord) +' '
    return text.strip()

def conformToNumber( number: float, text: str ) -> str:
    """Согласовать слово с числом"""
    (nDec, nInt) = math.modf( round(number, 3) )
    if round(nDec * 1000) != 0:
        text = inflectText(text, {'sing', 'gent'} )
    else:
        parses = parseText(text)
        text = ''
        for p in parses:
            p2 = p[0].make_agree_with_number( int(nInt) )
            text += (p2.word if p2 is not None else p[0].originalWord) + ' '

    return text.strip()

    #return transcribeInt( round(float(number)) ) + ' ' + parseWord( word )[0].make_agree_with_number( round(float(number)) ).word
    #return parseWord( word )[0].make_agree_with_number( round(float(number)) ).word
#endregion

#region tag() ##############################################################################
def extractTags( tags: str): 
    tgs = tags.replace(',',' ').split(' ')
    result = set()
    for t in tgs:
        if bool(t.strip()):
            try:
                tag = morphy.TagClass(t.strip())
                if bool(tag): result.add(t.strip())
            except ValueError as ve:
                try:
                    s = morphy.cyr2lat(t.strip())
                    tag = morphy.TagClass(s)
                    if bool(tag): result.add(s)
                except ValueError as ve:
                    logError(f'pymorphy2: неизвестный тег "{t}"')
                    pass
    return result
#endregion

#region Integer transcription ##############################################################
def transcribeInt999( number: int, tags=None ):
    """Перевод целого числа в диапазоне 0..999 в фразу на русском языке с учетом заданных тегов"""
    if tags is None : tags = {'nomn'}
    if (number<0) or (number>999):
        raise ArgumentError("Число должно находиться в диапазоне 0..999")

    s1 = {0:'', 1:'один', 2:'два', 3:'три', 4:'четыре', 5:'пять', 6:'шесть', 7:'семь', 8:'восемь', 9:'девять' }
    s2 = {0:'', 2:'двадцать', 3:'тридцать', 4:'сорок', 5:'пятьдесят',6:'шестьдесят', 
          7:'семьдесят', 8:'восемьдесят',9:'девяносто'}
    s3 = {0:'', 1:'сто', 2:'двести', 3:'триста', 4:'четыреста', 5:'пятьсот', 6:'шестьсот',
          7:'семьсот', 8:'восемьсот', 9:'девятьсот'}
    tsat = {0:'', 10:'десять', 11:'одиннадцать', 12:'двенадцать', 13:'тринадцать',14:'четырнадцать',
          15:'пятнадцать', 16:'шестнадцать', 17:'семнадцать',18:'восемнадцать', 19:'девятнадцать'}
    s = str( number )
    
    p = []
    if len( s ) >= 3:
        p.append( s3[int( s[-3] )] )

    if len( s ) >=2 :
        if 9 < int( s[-2:] ) < 20:
            p.append( tsat[int( s[-2:] )] )
        else:
            if int( s[-2] )>0:
                p.append( s2[int( s[-2] )] )
            if int( s[-1] )>0:
                p.append( s1[int( s[-1] )] )

    elif (len( s ) >=1) and (int( s[-1] ) > 0):
        p.append( s1[int( s[-1] )] )
    else:
        p.append( 'ноль' )

    for i in range( len( p ) ):
        w = parseWord( p[i] )[0].inflect( tags )
        if w is not None: p[i] = w.word

    return ' '.join( p )
    
def transcribeInt( number: int, tags=None, word: str='' ):
    """Перевод целого числа до миллиарда в фразу на русском языке с учетом заданных тегов"""
    if tags is None : tags = {'nomn'}
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
            w = parseWord( 'миллионов' )[0].inflect( {'masc'} ).make_agree_with_number( n ).word
            s += transcribeInt999( n, {'masc'} ) + ' ' + w + ' '
        number = number % 1000000

    if number > 999:
        n = int( number / 1000 )
        if n > 0 :
            w = parseWord( 'тысяч' )[0].inflect( {'femn'} ).make_agree_with_number( n ).word
            s += transcribeInt999( n, {'femn'} ) + ' ' + w + ' '
        number = number % 1000

    if s.strip() == '' or number > 0 :
        s = s + transcribeInt999( number, tags ) + ' '

    if word != '' :
        w = parseWord( word )[0].inflect( tags )
        if w is None : w = parseWord( word )[0]
        s += w.make_agree_with_number( number ).word

    return s.strip()
#endregion

#region Number transcription ###############################################################
def transcribeNumber( number: float, tags=None):
    (nDec, nInt) = math.modf( round(number, 3) )
    nInt = round(nInt)
    text = transcribeInt( round(nInt) )

    if round(nDec*1000) != 0:
        text = transcribeInt( nInt )
        if nInt % 10 == 1:
            text = inflectText( text, {'femn'} ) + ' целая '
        else:
            text += ' целых '

        s = str(round(abs(nDec*1000)))
        if s[-2:] == '00':
            n = round(int(s)/100)
            if n == 1:
                text += 'одна десятая'
            else:
                text += transcribeInt999(n, {'femn'}) + ' ' + "десятых"
        elif s[-1:] == '0':
            n = round(int(s)/10)
            if s[-2:-1] == '1' and s[-3:-1] != '11':
                text += transcribeInt999( n, {'femn'} ) + ' сотая'
            else:
                text += transcribeInt999( n, {'femn'} ) + ' сотых'

#                text += transcribeInt999( n ) + ' ' + conformToNumber( int(s)/10, "сотая")
        # else:
        #     text += transcribeInt999(int(s)) + ' ' + conformToNumber( int(s), "тысячная")
        elif s[-1:] == '1' and s[-2:] != '11':
            text += transcribeInt999( int(s), {'femn'} ) + ' тысячная'
        else:
            text += transcribeInt999( int(s), {'femn'} ) + ' тысячных'
    else:
        text = transcribeInt( round(nInt) )

    return text
#endregion

#region Date/Time transcription ############################################################
def transcribeTime( tm, tags=None ):
    """Перевод времени в фразу на русском с учетом тегов"""
    return \
        transcribeInt( tm.hour,{'nomn','masc'},'часов' ) + ' ' + \
        transcribeInt( tm.minute, {'nomn','femn'}, 'минут' )

def transcribeDate( dt, tags=None ):
    """Перевод даты в фразуна русском вида "пятница, 13 февраля" с учетом тегов """
    weekdays = {0:'понедельник', 1:'вторник',2:'среда',3:'четверг',4:'пятница',5:'суббота',6:'воскресенье'}
    months = {1:'января', 2:'февраля',3:'марта',4:'апреля',5:'мая',6:'июня',7:'июля', \
                8:'августа',9:'сентября',10:'октября',11:'ноября',12:'декабря' }

    # Пока не смог полностью победить склонение числительных
    n2 = {1:'первое', 2:'второе', 3:'третье', 4:'четвёртое', 5:'пятое', 6:'шестое', 7:'седьмое', \
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


    if tags is not None : 
        w = parseWord(d2)[0].incline(tags)
        if w is not None : d2 = w.word
        w = parseWord(dow)[0].incline(tags)
        if w is not None : dow = w.word
        w = parseWord(month)[0].incline(tags)
        if w is not None : month = w.word

    #TODO: добавить год, если дата отличается от текущей больше чем на 3 месяца
    day = f'{d1} {d2}'.strip()
    return f'{dow}, {day} {month}'.strip()
#endregion

#region Манипуляция цепочками слов (чере пробел) и фразами (через запятую) #################
def normalizePhrases( phrases ) -> str:
    """Возвращает нормализованный список (через запятую) нормализованных цепочек слов (через пробел)
    Пример "включи свет,выключи свет,сделай что-то"
    """
    if phrases is None : return ''
    allowed_chars = 'abcdefghijklmnopqrstuvxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя 1234567890-,'
    phrases = str(phrases).lower()
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

def phrasesToList( phrases ) -> list:
    """Преобразует список разделенных через запятую фраз в массив (list()) """
    return phrases.lower().replace( '  ',' ' ).replace( ', ',',' ).strip().split( ',' )

def wordsToList( words ) -> list:
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
#endregion

#region wordsToVocabulary() / wordsToVocabularyAllForms() ##################################
def wordsToVocabulary( words ) :
    """Расширить словарь, словами в исходной и нормальной форме
    Принимает списки слов в виде строк либо массивов строк (рекурсивно)
    """
    if isinstance( words, list ) :
        parses = parseText( ' '.join(words) )
    else:
        parses = parseText( str(words) )

    vocabulary = set()
    for p in parses:
        if p is not None:
            vocabulary.add( p[0].normal_form )
            vocabulary.add( p[0].word )
    return vocabulary

def wordsToVocabularyAllForms( words ) :
    """Расширить словарь словами с генерацией словоформ для заданных тегов.
    По умолчанию (теги не заданы) в словарь добавляется все возможные словоформы
    Принимает списки слов как в виде строк так и в виде массивов (рекурсивно)"""
    if isinstance( words, list ) :
        parses = parseText( ' '.join(words) )
    else:
        parses = parseText( str(words) )

    vocabulary = set()
    for parse in parses:
        if parse is not None:
            vocabulary.add( parse[0].normal_form )
            for lexeme in parse[0].lexeme:
                vocabulary.add( lexeme.word )

    return vocabulary
#endregion
