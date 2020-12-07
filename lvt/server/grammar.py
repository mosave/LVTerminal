
def normalizeWords( words )->str:
    return words.lower().replace(',',' ').replace('  ',' ').strip()

def normalizePhrases(phrases)->str:
    return phrases.lower().replace('  ',' ').replace(', ',',').strip()

def oneOfPhrases( phrase, phrases )->bool:
    phrase = normalizeWords(phrase)
    phrases = normalizePhrases(phrases)
    if len(phrase)==0 or len(phrases)==0 : return False
    return bool((','+phrases+',').find(','+prase+',')>=0)

def oneOfWords( word, phrases )->bool:
    word = normalizeWords(word)
    words = normalizeWords(phrases)
    if len(word)==0 or len(phrases)==0 : return False
    return bool((' '+words+' ').find(' '+word+' ')>=0)

def prasesToList( phrases )->[str]:
    return phrases.lower().replace('  ',' ').replace(', ',',').strip().split(',')

def wordsToList( words )->[str]:
    return words.lower().replace(',',' ').replace('  ',' ').strip().split(' ')

def joinWords( words, words2 )->str:
    words = normalizeWords( words )
    words2 = wordsToList( words2 )
    for w in words2:
        if (' '+words+' ').find(' '+w+' ')<0 :
            words += ' '+w
    return words.strip()



