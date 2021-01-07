# Lite Voice Terminal
## ���������� �������

### ����� ���������
 * ������ ������ ������������ ������������� ��� ������������� �������� �������
 * ��������� ������ ��������� ��� ������� ���������-������� � ������ �������������. ��� ���������� ������� �� ������ �� �����������.
 * ����� ������ ������ ������������� �� �������� ������ Skill, ��� ������ ��� �� ����� ����������� ������������� �� Skill
 * ����� ����� ����� ���� ������������, ������� �������� � ����� ����� ������������ � �������, ����������� � ��������� ������.
   ������ ����� ����� ������ � ����� ������������ ����� this.config (��� dict()).
 * ����� ������������� ����� ���������� ����� ����������� ����� ������������� ����������, ������������� ���
   ������������������ "�������": ��������� �������, ����������� ��������� �������: ����������� ��������� � ����������,
   �������������� ���������, ���������� �������� ������� ��� ���������, ����� �� ������������ ������ � ��
 * ��� ���������� ����������� ������� ������� ������������ "�����" - �������� �������������� �����������. 
   ������ ����� ����� ����������� �� ������������ ����� �������.


### �������:

 * onLoad(): ���������� ����� �������� ���������� ������. ����� ����������� ��� ����������� ��������� � ������������� ������
 * onText(): ���������� ����� ���������� ������������� ��������� �����. �������� �����, ����������� ������ ������
 * onPartialText() - ���������� � �������� ������������� �����. ������� ���������, ��� �������� ������������ �����
   ���������� � �������� � ����� ������ ���������� �� ��������� ������.
   ����������� onPartialText() ������������� ������ � ������ �������������, ��������� ��� �������� � �������� �������� �������.
 * onTimer() - ���������� �� ���� �����������, �������� ��� � �������. ������������ � �������������, �������� ����������.
 * onTopicChange( newTopic, params ): ���������� ��� ��������� ������ (�������� �������������� �����������)
   ���������� ������ ���� ����� �������� �� ����� (newTopic) ���� ������� (this.terminal.topic) ������
 

### �������� �������� ������ Skill:
 * terminal
 * moduleFileName
 * name
 * config
 * cfg
 * subscriptions = set()
 * vocabulary = set()
 * priority - ��� ���� �������� ����������, ��� ����� � ������ � �������
    ������������� �������� ����
 * isAppealed
 * appeal
 * appealPos
 * location
 * parsedLocations
 * entities
 * words
 * text
 * originalText
 * topic

### ������ �������� ������ Skill:
 * animate( this, animation:str )
 * say( this, text )
 * play( this, waveFileName )
 * log( this, msg:str )
 * logError( this, msg:str )
 * logDebug( this, msg:str )

 * getNormalFormOf( this, word: str, tags=None ) -> str:
 * getNormalForm( this, index: int, tags=None ) -> str:
 * conformToAppeal( this, word: str ) -> str:
 * isWord( this, index, word: str, tags=None ) -> bool:
 * isInTag( this, index, tags ) -> bool:
 * findWord( this, word: str, tags=None ) -> int:
 * findWordChain( this, chain: str, startIndex: int=0 ) :
 * findWordChainB( this, chain: str, startIndex: int=0 ) -> bool:
 * deleteWord( this, index: int, wordsToDelete:int=1 ):
 * insertWords( this, index:int, words: str ):
 * replaceWordChain( this, chain: str, replaceWithChain: str ) -> bool:
 * subscribe( this, *topics ):
 * unsubscribe( this, *topics ):
 * isSubscribed( this, topic ):
 * extendVocabulary( this, words, tags=None ):
 * changeTopic( this, newTopic, *params, **kwparams ):
 * stopParsing( this, animation: str=None ):
 * restartParsing( this ):

### �������� ��������� (this.terminal)
### ������ ��������� (this.terminal)

