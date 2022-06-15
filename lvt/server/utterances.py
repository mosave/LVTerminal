from datetime import datetime, date, time, timezone, timedelta
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

LATIN_CHARS : Final = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
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
    INTEGER_WORDS : Final = \
        "миллиадрд миллиардов миллион миллионов тысяча тысяч сотня сотен сто двести триста четыреста пятьсот шестьсот семьсот восемьсот девятьсот десять одиннадцать двенадцать " + \
        "тринадцать четырнадцать пятнадцать шестнадцать семнадцать восемнадцать девятнадцать двадцать тридцать сорок пятьдесят шестьдесят " + \
        "семьдесят восемьдесят девяносто ноль один два три четыре пять шесть семь восемь девять "
    NUMBER_WORDS : Final = \
        "целых десятых сотых тысячных десятитысячных полтора с половиной четвертью точка"

    TIME_WORDS : Final = \
        "в через дней часов минут секунд полчаса пару понедельник вторник среда четверг пятницу субботу воскресенье " + \
        "завтра послезавтра послепослезавтра сегодня вечером утром "

    def __init__(self, type=UF_WORDS, variable=None):
        self.type = type
        self.variable = variable
        self.words : list[UWords] = []
        
    def addWords( self, words: UWords ):
        self.words.append(words)

    def getVocabulary(self):
        vocabulary = set()
        if self.type==UF_ANY_WORD:
            pass
        elif self.type==UF_ANY_WORDS:
            pass
        elif self.type==UF_WORDS:
            for words in self.words:
                for parse in words.parses:
                    vocabulary.update( {parse[0].normal_form, parse[0].word} )
        elif self.type==UF_INTEGER:
            vocabulary.update( wordsToVocabulary( UFragment.INTEGER_WORDS ) )
        elif self.type==UF_NUMBER:
            vocabulary.update( wordsToVocabulary( UFragment.INTEGER_WORDS + " " +UFragment.NUMBER_WORDS ) )
        elif self.type==UF_TIME:
            vocabulary.update( wordsToVocabulary( UFragment.INTEGER_WORDS + " " +UFragment.TIME_WORDS ) )
            pass
        return vocabulary

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
                value = (' '.join([parse[0].word for parse in parses[:p]])) if p>0 else None
                text = ' '.join([parse[0].word for parse in parses[:p]])
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
        elif (self.type==UF_INTEGER) or (self.type==UF_NUMBER):
            (t, v, l) = self.matchNumber(parses)
            if (l>0) and ( (self.type==UF_NUMBER) or (t==UF_INTEGER)):
                text = ' '.join([parse[0].word for parse in parses[:l]])
                matches.append(UFragmentMatch( str(v), text, l, l))
        elif self.type==UF_TIME:
            (t, l) = self.matchTime(parses)
            if (l>0) :
                text = ' '.join([parse[0].word for parse in parses[:l]])
                matches.append(UFragmentMatch( str(v), text, l, l))
        return matches

#region Matching integer
    def matchInteger(self, parses ):
        """Возвращает Tuple( value: int, len: int) если parses начинается с целого числа (до 999 миллиардов)
        Либо (0,0) если это не так
        """
        v = 0
        l = 0
        pwr = 3

        while l<len(parses):
            if (parses[l][0].normal_form == "пара") :
                return (2,1)

            (v999, l999) = self.match999( parses[l:] )
            
            if l999<=0 :
                return (v,l)

            l += l999

            if l<len(parses) and (pwr>=3) and (parses[l][0].normal_form == "миллиадрд") :
                v += v999 * 1000000000
                l += 1
                pwr = 2
            elif l<len(parses) and (pwr>=2) and (parses[l][0].normal_form == "миллион") :
                v += v999 * 1000000
                l += 1
                pwr = 1
            elif l<len(parses) and (pwr>=1) and (parses[l][0].normal_form == "тысяча") :
                v += v999 * 1000
                l += 1
                pwr = 1
            elif l<len(parses) and (pwr>=1) and (parses[l][0].normal_form == "сотня") :
                v += v999 * 100
                l += 1
                pwr = 1
            else:
                v += v999
                break

        return (v,l)
    def match999(self, parses ):
        """Возвращает Tuple( value : int, len: int) если parses начинается с числа в диапазоне 0..999
        Либо (0,0) если это не так
        """
        p = 0
        v = 0
        ones = True

        if p<len(parses):
            if parses[p][0].normal_form == "сто":
                v += 100
                p += 1
            elif parses[p][0].normal_form == "двести":
                v += 200
                p += 1
            elif parses[p][0].normal_form == "триста":
                v += 300
                p += 1
            elif parses[p][0].normal_form == "четыреста":
                v += 400
                p += 1
            elif parses[p][0].normal_form == "пятьсот":
                v += 500
                p += 1
            elif parses[p][0].normal_form == "шестьсот":
                v += 600
                p += 1
            elif parses[p][0].normal_form == "семьсот":
                v += 700
                p += 1
            elif parses[p][0].normal_form == "восемьсот":
                v += 800
                p += 1
            elif parses[p][0].normal_form == "девятьсот":
                v += 900
                p += 1
        
        if p<len(parses):
            if parses[p][0].normal_form == "десять":
                v += 10
                p += 1
            elif parses[p][0].normal_form == "одиннадцать":
                v += 11
                p += 1
                ones = False
            elif parses[p][0].normal_form == "двенадцать":
                v += 12
                p += 1
                ones = False
            elif parses[p][0].normal_form == "тринадцать":
                v += 13
                p += 1
                ones = False
            elif parses[p][0].normal_form == "четырнадцать":
                v += 14
                p += 1
                ones = False
            elif parses[p][0].normal_form == "пятнадцать":
                v += 15
                p += 1
                ones = False
            elif parses[p][0].normal_form == "шестнадцать":
                v += 16
                p += 1
                ones = False
            elif parses[p][0].normal_form == "семнадцать":
                v += 17
                p += 1
                ones = False
            elif parses[p][0].normal_form == "восемнадцать":
                v += 18
                p += 1
                ones = False
            elif parses[p][0].normal_form == "девятнадцать":
                v += 19
                p += 1
                ones = False
            elif parses[p][0].normal_form == "двадцать":
                v += 20
                p += 1
            elif parses[p][0].normal_form == "тридцать":
                v += 30
                p += 1
            elif parses[p][0].normal_form == "сорок":
                v += 40
                p += 1
            elif parses[p][0].normal_form == "пятьдесят":
                v += 50
                p += 1
            elif parses[p][0].normal_form == "шестьдесят":
                v += 60
                p += 1
            elif parses[p][0].normal_form == "семьдесят":
                v += 70
                p += 1
            elif parses[p][0].normal_form == "восемьдесят":
                v += 80
                p += 1
            elif parses[p][0].normal_form == "девяносто":
                v += 90
                p += 1

        if p<len(parses) and ones:
            if parses[p][0].normal_form == "ноль":
                p += 1
            elif parses[p][0].normal_form == "один":
                v += 1
                p += 1
            elif parses[p][0].normal_form == "два":
                v += 2
                p += 1
            elif parses[p][0].normal_form == "три":
                v += 3
                p += 1
            elif parses[p][0].normal_form == "четыре":
                v += 4
                p += 1
            elif parses[p][0].normal_form == "пять":
                v += 5
                p += 1
            elif parses[p][0].normal_form == "шесть":
                v += 6
                p += 1
            elif parses[p][0].normal_form == "семь":
                v += 7
                p += 1
            elif parses[p][0].normal_form == "восемь":
                v += 8
                p += 1
            elif parses[p][0].normal_form == "девять":
                v += 9
                p += 1
        return ( v,p )
#endregion

#region Matching Number
    def matchNumber(self, parses ):
        """Возвращает 
            - Tuple( UF_INTEGER, value: int, len: int) если parses начинается с названия целого числа (до 999 миллиардов)
            - Tuple( UF_NUMBER, value: float, len: int) если parses начинается с названия дробного числа
            - Tuple( None, 0, 0) если parses не содержит определения числа
        """
        l = 0
        if l>=len(parses):
            return(None,0,0)

        if (parses[l][0].normal_form == "пара") :
            return (UF_INTEGER,2,1)

        if (parses[l][0].normal_form == "полтора") :
            return (UF_NUMBER,1.5,1)

        (vInt, lInt) = self.matchInteger( parses )

        if( lInt>0 ) and lInt+1<len(parses) and (parses[lInt][0].normal_form=='с') and (parses[lInt+1][0].normal_form=='половина'):
            return (UF_NUMBER,vInt + 0.5, lInt+2 )

        if( lInt>0 ) and lInt+1<len(parses) and (parses[lInt][0].normal_form=='с') and (parses[lInt+1][0].normal_form=='четверть'):
            return (UF_NUMBER,vInt + 0.25, lInt+2 )

        if( lInt>0 ) and lInt<len(parses) and ((parses[lInt][0].normal_form=='целый') or (parses[lInt][0].normal_form=='точка')):
            l = lInt+1
            (vDec, lDec) = self.matchInteger( parses[l:])
            l += lDec
            if (lDec>0) and l<len(parses):
                if (parses[l][0].word=='десятых') and (vDec<=10):
                    return (UF_NUMBER,vInt + vDec/10.0, l+1 )

                if (parses[l][0].word=='сотых') and (vDec<=100):
                    return (UF_NUMBER,vInt + vDec/100.0, l+1 )
                    
                if (parses[l][0].word=='тысячных') and (vDec<=1000):
                    return (UF_NUMBER,vInt + vDec/1000.0, l+1 )

                if (parses[l][0].word=='десятитысячных') and (vDec<=10000):
                    return (UF_NUMBER,vInt + vDec/10000.0, l+1 )
            return (None, 0, 0 )
            
        return (UF_INTEGER, vInt, lInt)

#endregion

#region Matching Time
    def matchTime(self, parses ):
        """Возвращает Tuple( value: struct_time, len: int) если parses начинается с определения времени
        Либо (localtime,0) если это не так
        Значения, воспримнимаемые в качестве времени:
        "через <number> [минут часов]"
        "в <int> часов <int> минут"
        "[завтра, послезавтра, в понедельник..воскресенье] в <int> часов <int> минут "
        "<int> [декабря,.., января], в <int> часов <int> минут"

        """
        dt = datetime.now()
        l = 0
        # if l<len(parses) and parses[l][0].normal_form == 'через':
        #     l += 1
        #     (nt, n, nl) = self.matchNumber(parses[1:])
        #     l += nl
        #     if (nl<=0) or (l>=len(parses)) :
        #         return (dt, 0)
        #     if parses[l][0].normal_form == 'часов':
        #         dt = dt + timedelta( seconds = n*3600 )
        #         (nt2, n2, nl2) = self.matchNumber(parses[l+1:])
        #         if ( nl2>0 ) and (parses[l+nl2+2][0].normal_form==''):
        #             pass

        #     if parses[i][0].normal_form == 'минут':
        #         dt = dt + timedelta( seconds = n*60 )


        return (dt, 0)
#endregion

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
        self.vocabulary = set()
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
                    elif( words[p+1].lower()=='time' ) : 
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
            self.vocabulary.update(f.getVocabulary())

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
        self.vocabulary = set()

    def add(self, uId: str, utterance: str ):
        """Добавление шаблона ключевой фразы в список
        uId - идентификатор ключевой фразы. Не обязательно уникальный.
        utterance - текст шаблона ключевой фразы
        """
        u = Utterance( utterance, self.terminal )
        u.id = uId
        self.utterances.append(u)
        self.utterances.sort()
        self.updateVocabulary()

    def remove(self, uId):
        """Удалить шаблоны с идентификатором uId """
        toRemove = [u for u in self.utterances if u.id==uId]
        for u in toRemove:
            self.utterances.remove(u)

        self.updateVocabulary()

    def clear(self):
        """Очистить список шаблонов ключевых фраз"""
        self.utterances.clear()
        self.updateVocabulary()
    

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

    def updateVocabulary(self):
        self.vocabulary = set()
        for u in self.utterances:
            self.vocabulary.update(u.vocabulary)


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

