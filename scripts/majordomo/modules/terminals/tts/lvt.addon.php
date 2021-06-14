<?php
//include_once("/lib/lvt.class.php");

class lvt extends tts_addon {
    function __construct($terminal) {
        //DebMes("Constricting LVT Addon for ".json_encode($this->terminal, JSON_UNESCAPED_UNICODE),'lvt');
        $this->title="Lite Voice Terminal TTS Addon";
        parent::__construct($terminal);
    }

    function say($phrase, $level = 0) {
        //DebMes("Say \"$phrase\" with level $level to ".json_encode($this->terminal, JSON_UNESCAPED_UNICODE),'lvt');
        return lvtSayTo( $this->terminal['NAME'], $phrase );
    }

    function ask($phrase, $level = 0) {
        //DebMes("Ask \"$phrase\" with level $level to ".json_encode($this->terminal, JSON_UNESCAPED_UNICODE),'lvt');
        return lvtAsk( $this->terminal['NAME'], $phrase, '' );
    }
}