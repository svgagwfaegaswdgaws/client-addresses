# Размещение на PythonAnywhere

Исходники: https://github.com/svgagwfaegaswdgaws/client-addresses

Размещённое приложение: https://svgagwfaegaswdgaws.pythonanywhere.com

На 16.10.2026 приложение настроено на Python 3.12, Force HTTPS включён.
Текущая дата отключения бесплатного веб-приложения — 16.11.2026; до неё
зайдите в Web и нажмите «Run until 1 month from today».

PythonAnywhere предлагает бесплатный Beginner-аккаунт с одним веб-приложением,
HTTPS и 512 MiB диска. Согласно документации на 16.10.2026, у бесплатного
веб-приложения срок активности — один месяц. Продлевайте его в разделе Web до
истечения срока. Условия сервиса могут меняться.

## 1. Аккаунт

Создайте Beginner-аккаунт на https://www.pythonanywhere.com/registration/register/beginner/
и подтвердите почту. Используйте почту, которую можно передать заказчице.
Пароли и коды подтверждения не помещайте в репозиторий.

## 2. Загрузка проекта

В PythonAnywhere откройте Consoles → Bash:

```bash
git clone https://github.com/svgagwfaegaswdgaws/client-addresses.git
cd client-addresses
python3 -m unittest discover -s tests -v
```

Если проект уже загружен, используйте `git pull` в его каталоге.
Файл базы находится вне Git и при обновлении кода не заменяется.

## 3. Веб-приложение

Откройте Web → Add a new web app → бесплатный домен → Manual configuration.
Выберите доступный Python версии 3.10 или новее.

В поле Source code укажите `/home/USERNAME/client-addresses`.
Откройте файл WSGI configuration file и замените его содержимое:

```python
import sys

project_path = '/home/USERNAME/client-addresses'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

from server import application
```

Замените `USERNAME` на действительный логин PythonAnywhere.
Виртуальное окружение и установка пакетов не нужны.
Нажмите Save, затем Reload в разделе Web. Включите Force HTTPS.

## 4. Проверка

Откройте `https://USERNAME.pythonanywhere.com/api/health`.
Ожидаемый ответ:

```json
{"status":"ok","database":"sqlite","variant":2}
```

Откройте главную страницу, добавьте учебные примеры и проверьте сохранение адреса.
Введите тот же HTTPS-адрес в APK кнопкой «Сервер».

## 5. Резервная копия

В PythonAnywhere откройте Files → `client-addresses/data/addresses.sqlite3` и скачайте базу,
когда никто не редактирует данные. Для переноса восстановите её в том же каталоге
и нажмите Reload. Не загружайте базу с данными клиентов в публичный репозиторий.

## Если не подключается

- Проверьте `/api/health` в обычном браузере телефона.
- В APK вводите корень адреса с `https://`, без `/api` и других путей.
- Посмотрите error log в Web на PythonAnywhere.
- При ошибке импорта проверьте `project_path` и логин.
- После изменения кода нажмите Reload.
- Проверьте, не истёк ли срок бесплатного веб-приложения.

Документация: [тарифы](https://www.pythonanywhere.com/pricing/),
[бесплатные аккаунты](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/).
