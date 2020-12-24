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

def parseWord( word: str ):
    """Parse word using phmorphy2 library"""
    global morphy
    return morphy.parse(word)

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

    while cleaned.startswith(',') : cleaned = cleaned[1:]
    while cleaned.endswith(',') : cleaned = cleaned[:-1]
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


def wordsToVocabulary( words, tags = None ) :
    """Расширить словарь словами с генерацией словоформ для заданных тегов
    По умолчанию (теги не заданы) в словарь добавляется только переданные словоформы
    Принимает списки слов в виде строк либо массивов строк (рекурсивно)
    """
    vocabulary = set()
    if isinstance( words, list) :
        for word in words : 
            vocabulary.update(wordsToVocabulary( word ))
    elif isinstance( words, str ):
        for w in wordsToList(words) :
            if tags != None : # Ищем первый разбор удовлетворяющий тегам
                parses = parseWord( w )
                parse = [p for p in parses if tags in p.tag]
                parse = parses[0] if len(parse)<=0 else parse[0]
                # Получаем множество лексем на базе выбранного разбора слова
                lexemes = set( [l.word for l in parse.lexeme if tags in l.tag]  )
                #Добавляем лексемы в словарь
                vocabulary.update( lexemes );
            else: 
                vocabulary.add( w );
    return vocabulary



def wordsToVocabularyAllForms( words, tags = None ) :
    """Расширить словарь словами с генерацией словоформ для заданных тегов.
    По умолчанию (теги не заданы) в словарь добавляется все возможные словоформы
    Принимает списки слов как в виде строк так и в виде массивов (рекурсивно)"""
    vocabulary = set()
    if isinstance( words, list) :
        for word in words : 
            vocabulary.update(wordsToVocabularyAllForms( word ))
    elif isinstance( words, str ):
        for w in wordsToList(words) :
            parses = parseWord( w )
                
            if tags != None : # Ищем первый разбор удовлетворяющий тегам
                parse = [p for p in parses if tags in p.tag]
                parse = parses[0] if len(parse)<=0 else parse[0]
            else: # Берем первый разбор
                parse = parses[0]

            # Получаем множество лексем на базе выбранного разбора слова
            lexemes = set( [l.word for l in parse.lexeme if (tags==None) or tags in l.tag]  )
            #Добавляем лексемы в словарь
            vocabulary.update( lexemes );

    return vocabulary

