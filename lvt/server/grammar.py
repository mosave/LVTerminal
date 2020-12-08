

def normalizePhrases( phrases ) -> str:
    allowed_chars = 'abcdefghijklmnopqrstuvxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя 1234567890,'
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
    return normalizePhrases( words ).replace( ',',' ' )

def oneOfPhrases( phrase, phrases ) -> bool:
    phrase = normalizeWords( phrase )
    phrases = normalizePhrases( phrases )
    if len( phrase ) == 0 or len( phrases ) == 0 : return False
    return bool( ( ',' + phrases + ',' ).find( ',' + phrase + ',' ) >= 0 )

def oneOfWords( word, words ) -> bool:
    word = normalizeWords( word )
    words = normalizeWords( words )
    if len( word ) == 0 or len( words ) == 0 : return False
    return bool( ( ' ' + words + ' ' ).find( ' ' + word + ' ' ) >= 0 )

def prasesToList( phrases ) -> [str]:
    return phrases.lower().replace( '  ',' ' ).replace( ', ',',' ).strip().split( ',' )

def wordsToList( words ) -> [str]:
    return words.lower().replace( ',',' ' ).replace( '  ',' ' ).strip().split( ' ' )

def joinWords( words, words2 ) -> str:
    words = normalizeWords( words )
    words2 = wordsToList( words2 )
    for w in words2:
        if ( ' ' + words + ' ' ).find( ' ' + w + ' ' ) < 0 :
            words += ' ' + w
    return words.strip()



