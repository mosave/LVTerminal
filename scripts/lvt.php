<?php
/*** Lite Voice Terminal MajorDoMo integration script 
*
*  Place it to the root of MajorDoMo site
*
*/

include_once("./config.php");
include_once("./lib/loader.php");
include_once("./load_settings.php");


function getLocations() {
   $sqlQuery = "SELECT id, Title 
                  FROM locations
                 ORDER BY id";

   return SQLSelect($sqlQuery);
}

function getPatterns() {
   $sqlQuery = "SELECT id, Title, Pattern
                  FROM patterns
                 ORDER BY id";

   return SQLSelect($sqlQuery);
}

function getDevices() {
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
   return $devices;
}


function postEntities(){
    $r = array();
    $l = array();

    $r['locations'][] = getLocations();
    $r['patterns'][] = getPatterns();
    $r['devices'][] = getDevices();

    header("Content-type:application/json; encoding=utf-8;");
    echo json_encode($r, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
}


postEntities();


?>