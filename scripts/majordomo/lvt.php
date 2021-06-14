<?php

//*****************************************************************************
//
//             Скрипт интеграции Lite Voice Terminal в MajorDoMo
//
//*****************************************************************************

// Через этот скрипт реализуется взаимодействие между LVT сервером и MajorDoMo.
// Для этого в разделе [MajorDoMo] файла конфигурации LVT сервера  server.cfg
// необходимо указать URL MajorDoMo и включить параметр
// Integration=1
// В случае если параметр Integration=0 или не задан все распознанные но необработанные 
// голосовые команды будут переданы в стандартный срипт MajorDoMo (command.php)
//
// Вызов скрипта:
// lvt.php?cmd=<command>{&param1=<value1>}
//
// Результат возвращается в виде JSON пакета со следующими обязательными полями:
//   'cmd' : Обрабатываемая команда
//   'ok' : 1 (команда выполнена успешно) или 0 (произошла ошибка) 
//   'status' : код возврата / код ошибки
//   'message' : сообщение / сообщение об ошибке
//
// Предопределенные коды ошибок:
//   403 - отказ в доступе
//   404 - неизвестная команда либо параметр cmd= отсутствует.
//   9999 - необработанный exception.
//
//
// Список поддерживаемых команд (параметр cmd):
//
// GetEntities - запрос списока устройств и локаций. В ответ скрипт возвращает 
//    JSON с описанием локаций и устройств, который может использоваться на 
//    стороне LVT сервера.
//
// LVTStatus - обновление состояния LVT сервера. JSON с ннформацией о состоянии 
//    сервера передается в переменной Status. Помимо общей информации о сервере, 
//    элемент "Terminals" содержит список зарегистрированных терминалов 
//    и их текущее состояние в следующем виде: 
//
//    [ "<Terminal Id>"={
//        "Terminal"="<Terminal Id>",
//        "Name"="<Terminal Name>",
//        "Connected"="<true|false>",
//        .....
//       }
//    ]
//
// НЕ РЕАЛИЗОВАНО:
// Voice - Распознанный текст голосовой команды, обращенной к голосовому помошнику и не обработанной LVT.
//    JSON содержит как оригинальное сообщение, так и слова в морфологически разобранном виде.
//    ??? Если к соответствующему терминалу привязан объект, то текст команды будет передан в 
//    <terminalObject>.onText

// Set global exception handler
set_exception_handler('lvtExceptionHandler');

include_once("./config.php");
include_once("./lib/loader.php");
include_once("./modules/application.class.php");
$session = new session("prj");
include_once("./load_settings.php");

//phpInfo();

// Define undefined
if( !defined( 'LVT_RESTRICT' ) ) define('LVT_RESTRICT', false);
if( !defined( 'LVT_SERVER' ) ) define('LVT_SERVER', 'localhost');
if( !defined( 'LVT_PORT' ) ) define('LVT_PORT', 7999);


$cmd = strtolower(gr('cmd').'');

$lvtResult = array();
$lvtResult['cmd'] = $cmd;
$lvtResult['ok'] = 1;
$lvtResult['status'] = 0;
$lvtResult['message'] = '';

// Check LVT server address if required:
if( LVT_RESTRICT && ($_SERVER['REMOTE_ADDR'] != LVT_SERVER) ) {
    lvtError( 403,'Access Denied');
}

// Restrict method to POST only:
if( LVT_RESTRICT && ($_SERVER['REQUEST_METHOD'] != 'POST') ) {
    lvtError( 403, $_SERVER['REQUEST_METHOD'].' not allowed');
}

// Process commands
if( $cmd == 'getentities') {
    $lvtResult['locations'] = lvtGetLocations();
    $lvtResult['patterns'] = lvtGetPatterns();
    $lvtResult['devices'] = lvtGetDevices();
    lvtReturn();
} elseif( $cmd == 'lvtstatus' ) {
    $status = json_decode( gr('status'), true);
    $lvtTerminals = $status['Terminals'];
    $terminals = getAllTerminals();
    //DebMes($status,'lvt');

    // Auto-update LVT terminals
    foreach( $terminals as $terminal ) {
        $lvtTerminal = false;
        foreach($lvtTerminals as $t) {
            if( strtolower($terminal['NAME']) == strtolower($t['Terminal'])) {
                $lvtTerminal = $t;
            }
        }
        if( $lvtTerminal ) {
            //DebMes('found '.$lvtTerminal['Terminal'],'lvt');
            $update = false;
            if( $lvtTerminal['Connected'] ) {
                if( $terminal['HOST'] != $lvtTerminal['Address'] ) {
                    $terminal['HOST'] = $lvtTerminal['Address'];
                }
                $terminal['LATEST_ACTIVITY'] = date('Y-m-d H:i:s');
                $update = true;
            }
            if( $terminal['TITLE'] != $lvtTerminal['Name'] ) {
                $terminal['TITLE'] = $lvtTerminal['Name'];
                $update = true;
            }
            if( $terminal['TTS_TYPE'] != 'lvt' ) {
                $terminal['TTS_TYPE'] = 'lvt';
                $update = true;
            }
            if( $terminal['IS_ONLINE'] != ($lvtTerminal['Connected']?1:0) ) {
                $terminal['IS_ONLINE'] = ($lvtTerminal['Connected']?1:0);
                $update = true;
            }
            if( $update ) {
                SQLUpdate('terminals', $terminal);
                //DebMes('updated '.$lvtTerminal['Terminal'],'lvt');
            }
            unset($lvtTerminals[$lvtTerminal['Terminal']]);
        }
    }
    // Auto-register LVT terminals:
    foreach( $lvtTerminals as $lvtTerminal ) {
        $terminal=array();
        $terminal['NAME']=$lvtTerminal['Terminal'];
        $terminal['TITLE']=$lvtTerminal['Name'];
        $terminal['HOST'] = $lvtTerminal['Address'];
        $terminal['CANTTS']=1;
        $terminal['TTS_TYPE']='lvt';
        $terminal['IS_ONLINE'] = ($lvtTerminal['Connected']?1:0);
        if( $lvtTerminal['Connected'] ) {
            $terminal['LATEST_ACTIVITY'] = date('Y-m-d H:i:s');
        }
        $terminal['ID']=SQLInsert('terminals',$terminal);
        DebMes('New terminal registered: '.$lvtTerminal['Terminal'],'lvt');
    }

    lvtReturn();
//} elseif( $cmd == '' ) {
} else {
    lvtError( 404, 'Unknown command "'.$cmd.'"' );
}


/* Processing command:

    $terminal = gr('terminal');
    $terminals = getTerminalsByName($terminal);
    $terminal_rec = $terminals[0];
    $session->data['TERMINAL'] = $terminal;


    $user_id = 0;
    $username = gr('username');
    if ($username) {
        $user=SQLSelectOne("SELECT * FROM users WHERE USERNAME LIKE '".DBSafe($username)."'");
        $session->data['SITE_USERNAME']=$user['USERNAME'];
        $session->data['SITE_USER_ID']=$user['ID'];
        $user_id = (int)$user['ID'];
    }

    if (isset($params['user_id'])) {
        $user_id = $params['user_id'];
    }

    $qrys = explode(' ' . DEVIDER . ' ', $qry);
    $total = count($qrys);

    $session->save();

    for ($i = 0; $i < $total; $i++) {
        $room_id = 0;

        $say_source = '';
        if ($terminal_rec['ID']) {
            $say_source = 'terminal' . $terminal_rec['ID'];
            $terminal_rec['LATEST_ACTIVITY'] = date('Y-m-d H:i:s');
            $terminal_rec['LATEST_REQUEST_TIME'] = $terminal_rec['LATEST_ACTIVITY'];
            $terminal_rec['LATEST_REQUEST'] = htmlspecialchars($qrys[$i]);
            $terminal_rec['IS_ONLINE'] = 1;
            SQLUpdate('terminals', $terminal_rec);
        }

        if (!$say_source) {
            $say_source = 'command.php';
        }

        say( htmlspecialchars($qrys[$i]), 0, $user_id, $say_source);

    }
    SQLExec('UPDATE terminals SET IS_ONLINE=0 WHERE LATEST_ACTIVITY < (NOW() - INTERVAL 30 MINUTE)');
*/

//*****************************************************************************
//                     GetEntities command implementation
//*****************************************************************************

function lvtGetLocations() {
   $sqlQuery = "SELECT id, Title 
                  FROM locations
                 ORDER BY id";
   return SQLSelect($sqlQuery);
}

function lvtGetPatterns() {
   $sqlQuery = "SELECT id, Title, Pattern
                  FROM patterns
                 ORDER BY id";

   return SQLSelect($sqlQuery);
}

function lvtGetDevices() {
   $sqlQuery = "
        SELECT
            o.Title Id, sd.ID SDeviceId,
            coalesce(plt.VALUE, pot.VALUE) DeviceType,
            coalesce(sd.Title,o.Description) Title, 
            sd.ALT_TITLES AltTitles,
            o.Description, 
            c.id ClassId, c.Title ClassTitle, c.Description ClassDescription,
            l.id LocationId, l.TITLE Location
        FROM 
            objects o 
            left outer join classes c ON c.ID = o.class_id
            left outer join classes cp ON cp.id = c.parent_id
            left outer join devices sd on sd.LINKED_OBJECT=o.TITLE
            left outer join locations l on l.id = COALESCE(sd.LOCATION_ID,o.location_id)
            left outer join pvalues plt on plt.PROPERTY_NAME=concat(o.Title,'.loadType')
            left outer join pvalues pot on pot.PROPERTY_NAME=concat(o.Title,'.openType')
    ";

   $devices  = SQLSelect($sqlQuery);
   $total = count($devices);
   for ($i = 0; $i < $total; $i++) {
      $dt = strtoupper(trim($devices[$i]['DeviceType']));
      if( !empty($dt) ) {
          $s = constant("LANG_DEVICES_LOADTYPE_$dt");
          if( empty($s) ) $s = constant("LANG_DEVICES_OPENTYPE_$dt");
          if( !empty($s) ) $devices[$i]['DeviceType'] = $s;
      }
   }
/*
    'DEVICES_LOADTYPE_VENT' => 'Вентиляция',
    'DEVICES_LOADTYPE_HEATING' => 'Обогрев',
    'DEVICES_LOADTYPE_CURTAINS' => 'Шторы',
    'DEVICES_LOADTYPE_GATES' => 'Ворота',
    'DEVICES_LOADTYPE_LIGHT' => 'Освещение',
    'DEVICES_LOADTYPE_LIGHT_ALT' => 'Свет',
    'DEVICES_LOADTYPE_POWER' => 'Разное',

    'DEVICES_OPENTYPE_CURTAINS' => 'Шторы',
    'DEVICES_OPENTYPE_SHUTTERS' => 'Ставни',
    'DEVICES_OPENTYPE_GATES' => 'Ворота',
    'DEVICES_OPENTYPE_WINDOW' => 'Окно',
    'DEVICES_OPENTYPE_DOOR' => 'Дверь',

*/

   return $devices;
}

//*****************************************************************************
//                              Helper functions
//*****************************************************************************

function lvtReturn( $message='' ){
    global $lvtResult;
    if($message != '') $lvtResult['message'] = $message;
    header("Content-type:application/json; encoding=utf-8;");
    echo json_encode($lvtResult, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    exit(0);
}

function lvtError( $status, $message ){
    global $lvtResult;
    $lvtResult['ok'] = 0;
    $lvtResult['status'] = $status;
    $lvtResult['message'] = $message;

    header("Content-type:application/json; encoding=utf-8;");
    echo json_encode($lvtResult, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    exit(0);
}

// Return error JSON if any exceptions
function lvtExceptionHandler($e) {
    lvtError( 9999, basename($e->getFile()).'#'.$e->getLine().': '.$e->getMessage() );
}

?>
