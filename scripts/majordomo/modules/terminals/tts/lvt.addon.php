<?php

class lvt extends tts_addon {

    function __construct($terminal) {
        //DebMes("Constricting LVT Addon for ".json_encode($this->terminal, JSON_UNESCAPED_UNICODE),'lvt');
        $this->title="Lite Voice Terminal API Addon";
        parent::__construct($terminal);

	$this->server = defined('LVT_SERVER') ? LVT_SERVER : '127.0.0.1';
	$this->port = defined('LVT_PORT') ? LVT_PORT : 7999;

    }

    function say($phrase, $level = 0) {
        //DebMes("Say \"$phrase\" with level $level to ".json_encode($this->terminal, JSON_UNESCAPED_UNICODE),'lvt');
        return $this->lvtCommand( 'Say', $phrase);
    }

    function ask($phrase, $level = 0) {
        //DebMes("Ask \"$phrase\" with level $level to ".json_encode($this->terminal, JSON_UNESCAPED_UNICODE),'lvt');
        return $this->lvtCommand( 'Ask', $phrase);
    }

    function lvtCommand( $cmd, $params ) {
        if ($this->terminal['HOST']) {
            $message =  $cmd.' '.$this->terminal['NAME'].' '.$params;
            DebMes('LVT Command for '.$this->server.':'.$this->port.': '.$message,'lvt');


            if (!preg_match('/^\d/', $this->server)) return 0;
            $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
            if ($socket === false) {
                return 0;
            }
            $result = socket_connect($socket, $this->server, $this->port);
            if ($result === false) {
                return 0;
            }
            $result = socket_write($socket, $message, strlen($message));
            socket_close($socket);
            DebMes('LVT Command result: '.$result,'lvt');
            return $result;
        }
    }

}