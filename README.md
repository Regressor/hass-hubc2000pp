[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![hassfest](https://github.com/Regressor/hass-hubc2000pp/actions/workflows/main.yml/badge.svg)
![hacs](https://github.com/Regressor/hass-hubc2000pp/actions/workflows/hacs.yml/badge.svg)

# Интеграция оборудования Bolid в home assistant

Данный репозиторий представляет собой интеграцию для Home Assistant. Интеграция предназначена 
для добавления возможности управления оборудованием компании Болид (https://bolid.ru/). Подключение 
к оборудованию выполняется с помощью устройства С2000-ПП и программы HUB-C2000PP (ссылка форум сайта [bolid.ru](https://partners.bolid.ru/forum/forum_23451.html#answer25769))

Для подключения вашей системы безопасности, построенной на оборудовании Болид необходимо выполнить следующие действия:

- Приобрести блок С2000-ПП и настроить в нем зоны, разделы и реле согласно документации на этот блок
- Скачать, скомпилировать и установить сервис HUB-C2000PP старше версии 2.0.2 (программа, опрашивающая оборудование и предоставляющее ряд методов для управления им)
- В конфигураторе программы HUB-C2000PP во вкладке "Сценарии" добавить содержимое файла script.js из данного репозитория и исправить в начале этого скрипта ip адрес home assistant (по умолчанию 127.0.0.1). Из соображений безопасности желательно держать и home assistant и HUB-C2000PP на одном сервере 
- Также в сценарии необходимо назначить соответствие зон типам сенсоров (возможные варианты типов сенсоров: )
- Добавить папку hubc2000pp в каталог config/custom_components вашего экземпляра home assistant
- **Если у вас home assistant запущен в виде docker контейнера необходимо добавить перенаправление порта 22001/udp и пересоздать контейнер (только если контейнер home assistant не запущен в режиме host)**
- Перезапустить контейнер
- Добавить интеграцию в веб-интерфейсе home assistant (при необходимости поменять ip адрес и порт сервиса hub-c2000pp)
- Все настроенные в блоке С2000-ПП устройства добавятся автоматически

# Схема работы интеграции

- При старте работы интеграции производится отправка команды PING на порт 22000 указанного адреса. Если в ответ получено PONG то считаем, что сервис HUB-C2000PP со скриптом доступен и работает.
- Интеграция Home assistant раз в минуту запрашивает из сервиса HUB-C2000PP данные обо всех зонах, реле и разделах
- Интеграция Home assistant слушает udp порт 22001 (т.е. указанный в настройках номер порта + 1), на который сервис HUB-C2000PP отправляет push уведомления при изменении состояния датчиков, разделов и реле. Данные adc push уведомлениями не передаются, чтобы не увеличивать размер базы данных home assistant

# Пример рабочей интеграции


![Скриншот](https://github.com/Regressor/hass-hubc2000pp/blob/master/hass_bolid.png?raw=true)

![Конфигуратор](https://github.com/Regressor/hass-hubc2000pp/blob/master/configurator.png?raw=true)
