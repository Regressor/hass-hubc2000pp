//==============================================================================
// Скрипт сервиса HUB-C2000PP для работы с интеграцией hubc2000pp home assistant
//==============================================================================

// Адрес сервиса HUB-C2000PP (желательно на той же машине)
var host = "127.0.0.1";
var port = 22000;
const DLM = "__DLM__";

var adc_list = {};

// Заполняется вручную по реальным данным. Цифра - номер зоны
// Типы счетчиков - https://developers.home-assistant.io/docs/core/entity/sensor/#available-state-classes
var sensor_types = {
	1: "doorSensor",
	2: "motionSensor",
	3: "temperatureSensor",
	4: "humiditySensor",
	5: "smokeSensor",
	6: "smokeSensor",
	7: "smokeSensor",
	8: "smokeSensor",
	9: "statusSensor",
	10: "ripOutputSensor",
	11: "ripCurrentSensor",
	12: "ripBatteryVoltageSensor",
	13: "ripBatteryLevelSensor",
	14: "ripInputVoltageSensor",
	15: "statusSensor",
	16: "statusSensor",
	17: "soundSensor",
	18: "carbonMonoxideSensor",
	19: "counterSensor",
	20: "counterTotalSensor",
	21: "counterTotalIncSensor",
	22: "genericAdcSensor",
}

hub.signalUpdateSh.connect(updateSh); // Связать сигнал с функцией.
function updateSh(sh, state) {
        let sh_id = Number(sh);
        let shNum = hub.getShNum(sh_id);
        let shPart = hub.getShPart(sh_id);
        let shType = hub.getShType(sh_id);
        let uid = "" + sh_id + "." + shNum + "." + shPart + "." + shType;

	udp.writeDatagram("zone:" + uid + ":" + state, host, port + 1);
	udp.writeDatagram("zone:" + uid + ":" + state, host, port + 1);
}

hub.signalUpdatePart.connect(updatePart); // Связать сигнал с функцией.
function updatePart(part, state) {
	udp.writeDatagram("part:" + part + ":" + state, host, port + 1);
	udp.writeDatagram("part:" + part + ":" + state, host, port + 1);
}

hub.signalUpdateRelay.connect(updateRelay); // Связать сигнал с функцией.
function updateRelay(rl, state) {
	udp.writeDatagram("relay:" + rl + ":" + state, host, port + 1);
	udp.writeDatagram("relay:" + rl + ":" + state, host, port + 1);
}

hub.signalUpdateADC.connect(updateADC); // Связать сигнал с функцией.
function updateADC(sh, adc) {
	// Накапливаем значения ADC в словаре, чтобы отдавать их по запросу
        adc_list[sh] = adc;
}

hub.signalUpdateCounter.connect(updateCounter); // Связать сигнал с функцией.
function updateCounter(sh, counter) {
	// Накапливаем значения Counter в словаре ADC, чтобы отдавать их по запросу
        adc_list[sh] = counter;
}

function getZoneList() {
    // Возвращает список зон с их конфигурацией, данными и описаниями
    let zoneConfig = "";
    const shList = hub.getShList();
    hub.writeLog("sh list:" + shList.toString());
    for (var sh in shList) {
       sh_id = Number(shList[sh]);
       let shState = hub.getShState(sh_id);
       let shAlarm = hub.isAlarmState(shState);
       let shType = hub.getShType(sh_id);
       let shNum = hub.getShNum(sh_id);
       let shPart = hub.getShPart(sh_id);
       let shDev = hub.getShDev(sh_id);
       let shDesc = hub.getShDescription(sh_id);

       let sensorType = "unknownSensor"
       if (sh_id in sensor_types) {
          sensorType = sensor_types[sh_id];
       }

       let shAdc = '-';
       if (sh_id in adc_list) {
          shAdc = adc_list[sh_id];
       }

       let shConf = "zone:" + sh_id + ":" + shNum + ":" + shPart + ":" + shType + ":" + shState + ":" + shAdc + ":" + sensorType + ":" + shDev + ":" + shDesc;
       if (zoneConfig != "") {
           zoneConfig += DLM;
       }
       zoneConfig += shConf;
    }

    hub.writeLog(zoneConfig);
    return zoneConfig;
}


function getPartList() {
    // Возвращает список разделов с их описаниями и состояниями
    let partConfig = "";
    const partList = hub.getPartList();
    hub.writeLog("part list: " + partList.toString());
    for (var part in partList) {
       part_id = Number(partList[part]);
       let partState = hub.getPartState(part_id);
       let partDesc = hub.getPartDescription(part_id);
       let partConf = "part:" + part_id + ":" + partState + ":" + partDesc;
       if (partConfig != "") {
           partConfig += DLM;
       }
       partConfig += partConf;
    }

    hub.writeLog(partConfig);
    return partConfig;
}


function getRelayList() {
    // Возвращает список реле с описаниями и состояниями
    let relayConfig = ""
    const relayList = hub.getRlList();
    hub.writeLog("relay list:" + relayList.toString());
    for (var relay in relayList) {
       relay_id = Number(relayList[relay]);
       let relayState = hub.getRelayState(relay_id);
       let relayDesc = hub.getRelayDescription(relay_id);
       let relayConf = "relay:" + relay_id + ":" + relayState + ":" + relayDesc;
       if (relayConfig != "") {
           relayConfig += DLM;
       }
       relayConfig += relayConf;
    }

    hub.writeLog(relayConfig);
    return relayConfig;
}



// Прием данных по протоколу UDP и отправка ответов
udp.readDatagram.connect(readDatagram);
udp.bind(port);
function readDatagram(rData, rHost, rPort)
{
    var request = rData.split(":");
    parnum = request.length;

    if (parnum > 0) {
       if (request[0] == "PING" && parnum == 1) {
          // Используется для первоначальной проверки наличия 
          // сервиса при добавлении интеграции в home assistant
          hub.writeLog("PING from " + rHost);
          udp.writeDatagram("PONG", rHost, rPort);
          return;
       }

       if (request[0] == "getZones" && parnum == 1) {
          // Ответ на запрос данных всех подключенных зон
          udp.writeDatagram(getZoneList(), rHost, rPort);
          return;
       }

       if (request[0] == "getParts" && parnum == 1) {
          // Ответ на запрос данных всех подключенных разделов
          udp.writeDatagram(getPartList(), rHost, rPort);
          return;
       }

       if (request[0] == "getRelays" && parnum == 1) {
          // Ответ на запрос данных всех подключенных реле
          udp.writeDatagram(getRelayList(), rHost, rPort);
          return;
       }

       if (request[0] == "arm" && parnum == 2) {
          hub.writeLog("ARM partition: " + rHost + ":" + rPort + ": " + request[1]);
          hub.controlPartArm(Number(request[1]));
          udp.writeDatagram("ARM_OK", rHost, rPort);
          return;
       }

       if (request[0] == "disarm" && parnum == 2) {
          hub.writeLog("DISARM partition: " + rHost + ":" + rPort + ": " + request[1]);
          hub.controlPartDisArm(Number(request[1]));
          udp.writeDatagram("DISARM_OK", rHost, rPort);
          return;
       }

       if (request[0] == "relay_on" && parnum == 2) {
          hub.writeLog("Switch ON relay: " + rHost + ":" + rPort + ": " + request[1]);
          hub.controlRelayOn(Number(request[1]));
          udp.writeDatagram("RELAY_OK", rHost, rPort);
          return;
       }

       if (request[0] == "relay_off" && parnum == 2) {
          hub.writeLog("Switch OFF relay: " + rHost + ":" + rPort + ": " + request[1]);
          hub.controlRelayOff(Number(request[1]));
          udp.writeDatagram("RELAY_OK", rHost, rPort);
          return;
       }

       // Если добрались сюда, то команда в запросе была неверной
       hub.writeLog("UDP readDatagram (" + rHost + ":" + rPort + "): " + rData + ", " + parnum);
       udp.writeDatagram("BAD_CMD", rHost, rPort);
    } else {
       // Формат команды неверный!
       hub.writeLog("UDP readDatagram (" + rHost + ":" + rPort + "): " + rData + ", " + parnum);
       udp.writeDatagram("BAD_CMD", rHost, rPort);
    }
}
