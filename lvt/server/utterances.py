from typing import Final
from lvt.const import *
from lvt.logger import *
from lvt.server.grammar import *
import lvt.server.entities as entities

UF_ANY_WORD : Final = "?"
UF_ANY_WORDS : Final = "*"
UF_WORDS : Final = "Words"
UF_INTEGER : Final = "Integer"
UF_NUMBER : Final = "Number"
UF_TIME : Final = "Time"

LATIN_CHARS : Final = 'abcdefghijklmnopqrstuvxyzABCDEFGHIJKLMNOPQRSTUVXYZ'
RUSSIAN_CHARS : Final = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
SPECIAL_CHARS : Final = '[]<>,*?='
ALLOWED_CHARS : Final = LATIN_CHARS + RUSSIAN_CHARS + SPECIAL_CHARS + ' -0123456789._'

class ParseException(Exception):
     pass

class UFragmentMatch:
    """Результат проверки соответствия фрагмента шаблона ключевой фразы
    value - значение переменной (слота) либо None если соответствия не обнаружено
    text  - цепочка слов, удовлетворяющая фрагменту шаблона
    weight - вес соответствия (количество слов, удовлетворяющих ключевой фразе)
    """
    def __init__(self, value: str, text: str, len: int, weight: int):
        self.value = value
        self.text = text
        self.len = len
        self.weight = weight

class UWords:
    """Определение значения в словаре. 
    text : исходный текст фразы
    parses : список разобранных слов
    value : значение, возвращаемое если разбираемый текст соответствует фразе
    """
    def __init__(self, value: str, words: list[str], parses = None ):
        self.value = value
        self.words = normalizeWords(words)
        if parses is not None :
            self.parses = parses
        else:
            self.parses = parseText( self.words )

    def __lt__(self, other):
        return len(self.parses) > len(other.parses)

class UFragment:
    """Определение фрагмента шаблона текста 
        type: тип фрагмента, см. константы UF_***
        variable: имя возвращаемой переменной (слота)
        words: список возможных фраз (при type==UF_WORDS)
    """
    def __init__(self, type=UF_WORDS, variable=None):
        self.type = type
        self.variable = variable
        self.words : list[UWords] = []
        
    def addWords( self, words: UWords ):
        self.words.append(words)

    def match(self, parses)->list[UFragmentMatch]:
        """Возвращает list[match] вариантов соответствий распарсенной фразы фрагменту шаблона.
        
        Каждый элемент списка содержит, в зависимости от типа фрагмента (self.type):
        * UF_WORDS: value соответствующей фразы из словаря
        * UF_ANY_*: возвращаемое значение конструируется из исходных форм в parses
        * UF_INTEGER, UF_NUMBER: int либо float соответственно
        * UF_TIME: "YYYY-MM-DD HH-MM-SS" (?)

        Список отсортирован по убыванию веса соответствия
        """
        matches = []
        if self.type==UF_ANY_WORD:
            if len(parses)>0:
                matches.append(UFragmentMatch( parses[0][0].word, parses[0][0].word, 1, 0))
        elif self.type==UF_ANY_WORDS:
            p = len(parses)
            while p>=0:
                value = (' '.join([p[0].word for p in parses[:p]])) if p>0 else None
                text = ' '.join([p[0].word for p in parses[:p]])
                matches.append(UFragmentMatch(value, text, p, 0 ))
                p -= 1
        elif self.type==UF_WORDS:
            for words in self.words:
                l = len(words.parses)
                if l<= len(parses):
                    f = True
                    for i in range(l):
                        if words.parses[i][0].normal_form != parses[i][0].normal_form:
                            f = False
                            break
                    if f: 
                        text = ' '.join([p[0].word for p in parses[:l]])
                        matches.append(UFragmentMatch( words.value, text, l, l ))
        elif self.type==UF_INTEGER:
            pass
        elif self.type==UF_NUMBER:
            pass
        elif self.type==UF_TIME:
            pass
        return matches

class Utterance:
    """Шаблон ключевой фразы"""

    def __init__( self, utterance: str, terminal ):
        """Разобрать ключевую фразу и отстроить список фрагментов
        utterance - текст шаблона ключевой фразы.
        terminal - LVT терминал (контекст)
        """

        self.fragments : list[UFragment] = []
        self.utterance = utterance
        self.terminal = terminal
        #region подготовка массива слов words
        cleaned = ''
        for ch in utterance: 
            if ch not in ALLOWED_CHARS:
                raise ParseException(f'Недопустимый символ: {ch}')
            cleaned += ' '+ch+' ' if ch in SPECIAL_CHARS else ch

        while '  ' in cleaned: 
            cleaned = cleaned.replace( '  ',' ' ).strip()
        words = cleaned.split(' ')

        if len(words) < 1:
            raise ParseException("Ошибка описания шаблона фразы")
        #endregion
        p = 0
        while p < len(words):
            #region Вычленение имени переменной (разбор конструкции "<var_name>="). Результат - в переменной variable
            if (p+1<len(words)) and (words[p+1]=='=') :
                if isId( words[p] ):
                    variable = words[p]
                    p += 2
                    if p>=len(words):
                        raise ParseException(f'Отсутствует определение переменной {variable}=... ')
                else:
                    raise ParseException(f'Недопустимое имя переменной \"{words[p]}\"')
            else:
                variable = ""
            #endregion

            if words[p] == '[': # Parse list
                fragment = UFragment( UF_WORDS, variable )
                defA = p = p + 1
                valA = valB = 0

                while True:
                    if p >= len(words):
                        raise ParseException("Ошибка при определении списка: пропущена закрывающая скобка")
                    elif words[p] == '=':
                        valA = defA
                        valB = p
                        defA = p = p + 1
                    elif (words[p]==',') or (words[p]==']'):
                        if valA==0:
                            valA = defA
                            valB = p
                        if defA>=p:
                            raise ParseException("Ошибка при определении списка: пропущена строка")
                        if valA>=valB:
                            raise ParseException(f'Ошибка при определении списка: неверный ID строки')
                        for w in words[valA:valB]:
                            if not isValue(w):
                                raise ParseException(f'Ошибка при определении списка: неверный ID строки {" ".join(words[valA:valB])}')
                        for w in words[defA:p]:
                            if not isWord(w):
                                raise ParseException(f'Ошибка при определении списка: нераспознаваемое слово { w }')
                        
                        fragment.addWords( UWords( ' '.join(words[valA:valB]), words[defA:p] ) )
                        if words[p]==']':
                            break
                        defA = p = p+1
                        valA = valB = 0
                    else:
                        p += 1

                self.fragments.append( fragment )
                p += 1
            elif words[p] == '<': # Parse dictionary
                if p+2<len(words) and isId(words[p+1]) and words[p+2]==">":
                    if( words[p+1].lower()=='integer' ) : 
                        fragment = UFragment( UF_INTEGER, variable )
                    elif( words[p+1].lower()=='number' ) : 
                        fragment = UFragment( UF_NUMBER, variable )
                    if( words[p+1].lower()=='time' ) : 
                        fragment = UFragment( UF_TIME, variable )
                    else:
                        fragment = UFragment( UF_WORDS, variable )
                        entity = entities.get( words[p+1], self.terminal.id )
                        for e in entity.definitions:
                            fragment.addWords(UWords(e.id, e.definition, e.parses))

                        # create LIST from dictionary

                    self.fragments.append( fragment )
                    p += 3
                    continue
                else:
                    raise ParseException("Неверное определение справочника")
            elif words[p] == '?':
                self.fragments.append( UFragment( UF_ANY_WORD, variable ) )
                p += 1
            elif words[p] == '*':
                self.fragments.append( UFragment( UF_ANY_WORDS, variable ) )
                p += 1
            elif isWord(words[p]):
                defA = p
                p += 1
                while (p<len(words)) and isWord(words[p]) and ( (p+1>=len(words)) or (words[p+1]!='=') ):
                    p += 1
                
                fragment = UFragment( UF_WORDS, variable )
                fragment.addWords( UWords( ' '.join(words[defA:p]), words[defA:p] ) )
                self.fragments.append( fragment )
            else:
                raise ParseException("Ошибка при разборе ключевой фразы.")
        for f in self.fragments:
            f.words.sort()

    def __lt__(self, other):
        return len(self.fragments) > len(other.fragments)

    def __match(self, index: int, parses: list, values:dict, weight: int ) -> tuple[int, dict] : 
        """Рекурсивный поиск соответствия шаблона ключевой фразы списку Parses.
        Возвращает Tuple(weight, values) если соответсвие обнаружено либо 
        (-1, None) если parses не соответствуют шаблону
        """
        if len(parses)<0:
            return (-1,None)
        matches = self.fragments[index].match(parses)
        for m in matches:
            v = values
            if self.fragments[index].variable :
                v[self.fragments[index].variable] = m.value
            if index+1 == len(self.fragments):
                if m.len==len(parses):
                    return (weight + m.weight, v)
            else:
                ( rw, rv) = self.__match(index+1, parses[m.len:], v, weight + m.weight )
                if rw>=0:
                    return ( rw, rv)
        return (-1, None )



    def match(self, parses):
        """Проверяет список parses на соответствие шаблону.
        Возвращает Tuple(weight: int, values:dict ), где
            weight:int - вес результата (количиство сопоставленных слов) либо -1 если соответствия не обнаружено
            values:dict - значения переменных
        """
        (weight, values) = self.__match( 0, parses,  {}, 0 )
        if( weight>=0 ):
            if ("speaker" not in values) or (values["speaker"] is None):
                values["speaker"] = self.terminal.id
            if ("location" not in values) or (values["location"] is None):
                values["location"] = self.terminal.location
            if ("person" not in values) or (values["location"] is None):
                values["person"] = self.terminal.speaker
        return (weight, values)

    def matchText(self, text: str):
        """Проверяет строку на соответствие шаблону.
        Возвращает Tuple(weight: int, values:dict ), где
            weight:int - вес результата (количиство сопоставленных слов) либо -1 если соответствия не обнаружено
            values:dict - значения переменных
        """
        return self.match( parseText(text) )

class UtteranceMatch:
    """Описание найденного соответствия фрагмента шаблона ключевой фразе
    id - utteranceId
    weight - вес соответствия
    values - справочник значений переменных
    utterance - шаблон ключевой фразы
    """
    def __init__(self, id, weight: int, values, utterance: str):
        self.id = id
        self.weight = weight
        self.values = values
        self.utterance = utterance

    def __lt__(self, other):
        return self.weight > other.weight

class Utterances:
    """Список шаблонов ключевых фраз
    При использовании списка 
    """

    def __init__(self, terminal):
        self.utterances : list(Utterance) = []
        self.terminal = terminal

    def add(self, uId: str, utterance: str ):
        """Добавление шаблона ключевой фразы в список
        uId - идентификатор ключевой фразы. Не обязательно уникальный.
        utterance - текст шаблона ключевой фразы
        """
        u = Utterance( utterance, self.terminal )
        u.id = uId
        self.utterances.append(u)
        self.utterances.sort()

    def remove(self, uId):
        """Удалить шаблоны с идентификатором uId """
        toRemove = [u for u in self.utterances if u.id==uId]
        for u in toRemove:
            self.utterances.remove(u)

    def clear(self):
        """Очистить список шаблонов ключевых фраз"""
        self.utterances.clear()
    

    def match(self, parses):
        """Проверяет массив parses на соответствие шаблонам.
        Возвращает dict[uId], содержащий наилучшее из найденных соответствие для данного uId
            (uId, dict значений переменных если parses соответсвуют шаблону
            None если соответствия не обнаружено
        """
        matches = {}
        for u in self.utterances:
            (w, v) = u.match(parses)
            f = (w>matches[u.id].weight) if u.id in matches else (w>=0)
            if f: matches[u.id] = UtteranceMatch( u.id, w, v, u.utterance )

        matches = [ m for _, m in matches.items() ]
        matches.sort()
        return matches

    def matchText(self, text: str):
        """Проверяет строку на соответствие шаблону.
        Возвращает:
            dict значений переменных если parses соответсвуют шаблону
            None если соответствия не обнаружено
        """
        return self.match( parseText(text) )




#region isWord / isId / isValue / isInteger / isNumber
def isWord( lexeme: str)->bool:
    """Распознаваемое слово"""
    for ch in lexeme:
        if ch not in RUSSIAN_CHARS + LATIN_CHARS:
            return False
    return True

def isId( lexeme: str)->bool:
    """Идентификатор """
    if (len(lexeme)<1) or (lexeme[0] not in LATIN_CHARS) :
        return False

    for ch in lexeme[1:]:
        if ch not in LATIN_CHARS + "1234567890_":
            return False
    
    return True

def isValue( lexeme: str)->bool:
    """Идентификатор """
    if len(lexeme)<1:
        return False

    for ch in lexeme:
        if ch not in LATIN_CHARS + RUSSIAN_CHARS + "1234567890_":
            return False
    
    return True

def parseNumber( lexeme: str)->bool:
    """parse word and returns (isValid, integerPart, decimalPart, isNegative) """
    integerPart = ''
    decimalPart = ''
    isNegative = False
    decimalPoint = False
    for ch in lexeme:
        if ch=='-':
            if isNegative or (integerPart!=''):
                return (False, integerPart, decimalPart, isNegative)
        elif ch=='.':
            if (integerPart=='') or decimalPoint:
                return (False, integerPart, decimalPart, isNegative)
            decimalPoint = True
        elif ch in "0123456789":
            if not decimalPoint:
                integerPart = integerPart + ch
            else:
                decimalPart = decimalPart + ch
        else:
            return (False, integerPart, decimalPart, isNegative)

    return ( (integerPart!=''), integerPart, decimalPart, isNegative)

def isInteger( lexeme: str)->bool:
    """Целое число"""
    (valid, i,d,n) = parseNumber(lexeme)
    return valid and (d=='')

def isNumber( lexeme: str)->bool:
    """Целое число или десятичная дробь """
    (valid, i,d,n) = parseNumber(lexeme)
    return valid
#endregion

