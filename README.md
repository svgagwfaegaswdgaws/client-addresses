# Адреса клиентов — вариант 2

Небольшое клиент-серверное приложение для ведения адресов клиентов.

Приложение: https://svgagwfaegaswdgaws.pythonanywhere.com

Исходники: https://github.com/svgagwfaegaswdgaws/client-addresses

[Скачать APK и исходники версии 1.0](https://github.com/svgagwfaegaswdgaws/client-addresses/releases/tag/v1.0)

- Четыре раздела: адреса, города, регионы, страны.
- Добавление, просмотр, изменение, удаление и поиск.
- Зависимые списки: страна → регион → город.
- SQLite хранит данные на сервере, а не в браузере или телефоне.
- Сообщения об ошибках соединения и повторная загрузка.
- Android-клиент на Java с настройкой адреса сервера.

## Быстрый запуск

Нужен Python 3.10 или новее. Сторонние Python-библиотеки не требуются.

```bash
python server.py
```

Откройте <http://127.0.0.1:8000>. В Windows также можно запустить `start.bat`.
База создаётся автоматически в `data/addresses.sqlite3`.
Чтобы получить примеры, нажмите «Добавить учебные примеры» в пустой базе.
Без примеров начните со стран, затем добавьте регионы, города и адреса.

## Структура проекта

```text
server.py                  HTTP API, проверка данных, работа с SQLite, WSGI
schema.sql                 схема базы данных с внешними ключами
web/index.html             интерфейс
web/app.js                 запросы к API, формы, поиск
web/style.css              оформление для компьютера и телефона
android/                   исходный Android-проект на Java
tests/test_server.py       интеграционные тесты API и SQLite
wsgi.py                    точка входа для WSGI-хостинга
DEPLOY.md                  размещение на PythonAnywhere
REPORT.md                  описание проекта для защиты
HANDOVER.md                порядок передачи заказчице
Dockerfile                 альтернативный запуск в Docker
```

## Android APK

APK — устанавливаемый Android-клиент с WebView. Он открывает интерфейс с сервера;
операции и база данных находятся на сервере. Поддерживается Android 8.0 и новее.

В APK уже указан адрес `https://svgagwfaegaswdgaws.pythonanywhere.com`.
После установки приложение открывает его автоматически. Чтобы сменить хостинг,
нажмите «Сервер» и введите новый адрес. Адрес сохраняется в настройках.
Если сервер недоступен, приложение покажет ошибку и кнопки повторного подключения.
Серверный URL можно изменить без пересборки APK.

Для локального теста телефона и компьютера в одной Wi-Fi сети:

```powershell
$env:HOST='0.0.0.0'
python server.py
```

В APK укажите `http://IP-КОМПЬЮТЕРА:8000`. При необходимости разрешите входящее
подключение Python в брандмауэре только для частной сети. `localhost` на телефоне
указывает на телефон. Для эмулятора Android адрес компьютера — `http://10.0.2.2:8000`.

### Пересборка

Откройте каталог `android` в Android Studio и дождитесь синхронизации.
Проект использует Android Gradle Plugin 9.4.1, Gradle 9.6.0, SDK 37.0 и Java 17+.
Используйте JDK, поставляемый с совместимой Android Studio.

```powershell
cd android
.\gradlew.bat assembleDebug
```

Результат: `android/app/build/outputs/apk/debug/app-debug.apk`.
При желании заранее укажите URL:

```powershell
.\gradlew.bat assembleDebug -PserverUrl=https://USERNAME.pythonanywhere.com
```

Debug APK автоматически подписан и подходит для установки и демонстрации.
Для публикации в Google Play требуется отдельная release-подпись.

## Тестирование

```bash
python -m unittest discover -s tests -v
```

Тесты используют отдельные временные базы. Они проверяют CRUD, связи, ограничения,
повторную инициализацию базы без потери данных, учебные примеры и обработку ошибок.

## Размещение

См. [DEPLOY.md](DEPLOY.md). GitHub хранит исходники. Для Python-сервера нужен WSGI-хостинг,
например PythonAnywhere. GitHub Pages обслуживает только статические файлы.

Дополнительные параметры окружения:

| Параметр | По умолчанию | Назначение |
|---|---|---|
| `HOST` | `127.0.0.1` | Интерфейс локального HTTP-сервера |
| `PORT` | `8000` | Порт локального HTTP-сервера |
| `DATABASE_PATH` | `data/addresses.sqlite3` | Путь к базе на сервере |

Учебная версия работает без авторизации. Все посетители используют общую базу;
для демонстрации предусмотрены вымышленные данные.

## Источники документации

- [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
- [PythonAnywhere: тарифы](https://www.pythonanywhere.com/pricing/)
- [PythonAnywhere: ограничения бесплатного аккаунта](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/)
- [Сборка Android APK](https://developer.android.com/build/building-cmdline)
