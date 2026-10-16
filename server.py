"""Вариант 2. HTTP/WSGI-сервер без сторонних библиотек. Python >= 3.10."""
import json
import logging
import mimetypes
import os
import re
import sqlite3
from contextlib import closing
from http import HTTPStatus
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import unquote, urlsplit
from wsgiref.simple_server import WSGIServer, make_server

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", ROOT / "data" / "addresses.sqlite3"))
STATIC = ROOT / "web"
FIELDS = {
    "countries": ("Country", {"CountryFull": 120, "CountryShort": 20}),
    "regions": ("Region", {"CountryID": int, "Region": 120}),
    "cities": ("City", {"RegionID": int, "City": 120}),
    "addresses": ("Address", {"Person": 160, "CityID": int, "Street": 160, "Building": 30, "Office": 30}),
}
LABELS = {"CountryFull": "Название страны", "CountryShort": "Краткое название", "Region": "Регион",
          "City": "Город", "Person": "Клиент", "Street": "Улица", "Building": "Дом", "Office": "Офис"}


class ApiError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def connect():
    db = sqlite3.connect(str(DB_PATH), timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect()) as db, db:
        db.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))


def validate(entity, data):
    if not isinstance(data, dict):
        raise ApiError("Ожидается JSON-объект.")
    fields = FIELDS[entity][1]
    if set(data) - set(fields):
        raise ApiError("В запросе есть неизвестные поля.")
    result = {}
    for key, rule in fields.items():
        value = data.get(key, "" if key == "Office" else None)
        if rule is int:
            if type(value) is not int or value < 1:
                raise ApiError("Выберите существующую запись из справочника.")
        else:
            if not isinstance(value, str):
                raise ApiError(f"Заполните поле «{LABELS[key]}».")
            value = value.strip()
            if len(value) > rule or (not value and key != "Office"):
                raise ApiError(f"Поле «{LABELS[key]}»: от 1 до {rule} символов." if key != "Office" else "Офис: не более 30 символов.")
        result[key] = value
    return result


def read_body(environ):
    if environ.get("CONTENT_TYPE", "").split(";")[0].lower() != "application/json":
        raise ApiError("Нужен Content-Type: application/json.", 415)
    try:
        size = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        raise ApiError("Некорректный размер запроса.")
    if size <= 0 or size > 16384:
        raise ApiError("Запрос пустой или слишком большой.", 413)
    try:
        return json.loads(environ["wsgi.input"].read(size))
    except (ValueError, UnicodeDecodeError):
        raise ApiError("Некорректный JSON.")


def snapshot(db):
    # Один read transaction даёт согласованный снимок всех четырёх таблиц.
    db.execute("BEGIN")
    result = {entity: [dict(row) for row in db.execute(f'SELECT * FROM "{table}" ORDER BY ID DESC')]
              for entity, (table, _) in FIELDS.items()}
    db.commit()
    return result


def seed_demo(db):
    db.execute("BEGIN IMMEDIATE")
    if any(db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] for table, _ in FIELDS.values()):
        raise ApiError("Примеры можно добавить только в пустую базу.", 409)
    by = db.execute("INSERT INTO Country(CountryFull,CountryShort) VALUES (?,?)", ("Республика Беларусь", "Беларусь")).lastrowid
    ru = db.execute("INSERT INTO Country(CountryFull,CountryShort) VALUES (?,?)", ("Российская Федерация", "Россия")).lastrowid
    minsk_region = db.execute("INSERT INTO Region(CountryID,Region) VALUES (?,?)", (by, "Минская область")).lastrowid
    brest_region = db.execute("INSERT INTO Region(CountryID,Region) VALUES (?,?)", (by, "Брестская область")).lastrowid
    moscow_region = db.execute("INSERT INTO Region(CountryID,Region) VALUES (?,?)", (ru, "Москва")).lastrowid
    minsk = db.execute("INSERT INTO City(RegionID,City) VALUES (?,?)", (minsk_region, "Минск")).lastrowid
    brest = db.execute("INSERT INTO City(RegionID,City) VALUES (?,?)", (brest_region, "Брест")).lastrowid
    moscow = db.execute("INSERT INTO City(RegionID,City) VALUES (?,?)", (moscow_region, "Москва")).lastrowid
    db.executemany("INSERT INTO Address(Person,CityID,Street,Building,Office) VALUES (?,?,?,?,?)", [
        ("ООО «Пример»", minsk, "Независимости", "25", "12"),
        ("Анна Иванова (пример)", minsk, "Козлова", "7А", ""),
        ("ООО «Образец»", brest, "Советская", "40", "3"),
        ("Иван Петров (пример)", moscow, "Лесная", "8", "15")])
    return {"ok": True}


def api(environ, path, method):
    if method not in ("GET", "POST", "PUT", "DELETE"):
        raise ApiError("Метод не поддерживается.", 405)
    if method != "GET":
        origin = environ.get("HTTP_ORIGIN")
        if origin and urlsplit(origin).netloc != environ.get("HTTP_HOST"):
            raise ApiError("Запрос с другого сайта запрещён.", 403)
    with closing(connect()) as db, db:
        if path == "/api/health" and method == "GET":
            db.execute("SELECT COUNT(*) FROM Address").fetchone()
            return {"status": "ok", "database": "sqlite", "variant": 2}
        if path == "/api/snapshot" and method == "GET":
            return snapshot(db)
        if path == "/api/demo" and method == "POST":
            return seed_demo(db)
        match = re.fullmatch(r"/api/(countries|regions|cities|addresses)(?:/([1-9][0-9]{0,15}))?", path)
        if not match:
            raise ApiError("Ресурс не найден.", 404)
        entity, raw_id = match.groups()
        table = FIELDS[entity][0]
        record_id = int(raw_id) if raw_id else None
        if method == "GET":
            if record_id:
                row = db.execute(f'SELECT * FROM "{table}" WHERE ID=?', (record_id,)).fetchone()
                if row is None:
                    raise ApiError("Запись уже удалена.", 404)
                return dict(row)
            return [dict(row) for row in db.execute(f'SELECT * FROM "{table}" ORDER BY ID DESC')]
        if method == "POST" and record_id is None:
            data = validate(entity, read_body(environ))
            names = ",".join(f'"{key}"' for key in data)
            cursor = db.execute(f'INSERT INTO "{table}" ({names}) VALUES ({",".join("?" for _ in data)})', tuple(data.values()))
            return dict(db.execute(f'SELECT * FROM "{table}" WHERE ID=?', (cursor.lastrowid,)).fetchone())
        if record_id is None:
            raise ApiError("Укажите ID записи.", 405)
        if not db.execute(f'SELECT 1 FROM "{table}" WHERE ID=?', (record_id,)).fetchone():
            raise ApiError("Запись уже удалена. Обновите список.", 404)
        if method == "PUT":
            data = validate(entity, read_body(environ))
            assignments = ",".join(f'"{key}"=?' for key in data)
            db.execute(f'UPDATE "{table}" SET {assignments} WHERE ID=?', (*data.values(), record_id))
            return dict(db.execute(f'SELECT * FROM "{table}" WHERE ID=?', (record_id,)).fetchone())
        if method == "DELETE":
            db.execute(f'DELETE FROM "{table}" WHERE ID=?', (record_id,))
            return {"ok": True}
        raise ApiError("Метод не поддерживается.", 405)


def application(environ, start_response):
    path = unquote(environ.get("PATH_INFO", "/"))
    method = environ.get("REQUEST_METHOD", "GET")
    headers = [("X-Content-Type-Options", "nosniff"), ("X-Frame-Options", "DENY"),
               ("Cache-Control", "no-store"), ("Referrer-Policy", "same-origin")]
    status = 200
    try:
        if path.startswith("/api/"):
            body = json.dumps(api(environ, path, method), ensure_ascii=False).encode("utf-8")
            content_type = "application/json; charset=utf-8"
            if method == "POST" and path != "/api/demo":
                status = 201
        else:
            if method not in ("GET", "HEAD"):
                raise ApiError("Метод не поддерживается.", 405)
            file = (STATIC / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
            if not file.is_relative_to(STATIC.resolve()) or not file.is_file():
                raise ApiError("Страница не найдена.", 404)
            body = file.read_bytes()
            content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
            if file.suffix in (".html", ".css", ".js", ".svg"):
                content_type += "; charset=utf-8"
            headers.append(("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"))
    except ApiError as error:
        status, body = error.status, json.dumps({"error": error.message}, ensure_ascii=False).encode("utf-8")
        content_type = "application/json; charset=utf-8"
    except sqlite3.IntegrityError as error:
        status = 409
        message = ("Эта запись используется в других данных. Сначала удалите связанные записи." if method == "DELETE"
                   else "Связанная запись не существует или такая запись уже есть. Проверьте данные.")
        body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        content_type = "application/json; charset=utf-8"
    except Exception:
        logging.exception("Request failed: %s %s", method, path)
        status, body, content_type = 500, json.dumps({"error": "Ошибка сервера. Повторите запрос позже."}, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8"
    headers += [("Content-Type", content_type), ("Content-Length", str(len(body)))]
    start_response(f"{status} {HTTPStatus(status).phrase}", headers)
    return [] if method == "HEAD" else [body]


init_database()


class ThreadingServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    with make_server(host, port, application, server_class=ThreadingServer) as server:
        print(f"Адреса клиентов: http://{host}:{port}", flush=True)
        print(f"База данных: {DB_PATH}", flush=True)
        server.serve_forever()
