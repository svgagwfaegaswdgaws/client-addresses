"""Интеграционные тесты WSGI + настоящая SQLite в отдельном временном каталоге."""
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from wsgiref.util import setup_testing_defaults

ROOT = Path(__file__).resolve().parents[1]


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial = tempfile.TemporaryDirectory()
        previous = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(Path(cls.initial.name) / "init.sqlite3")
        try:
            spec = importlib.util.spec_from_file_location("tested_server", ROOT / "server.py")
            cls.server = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.server)
        finally:
            if previous is None:
                os.environ.pop("DATABASE_PATH", None)
            else:
                os.environ["DATABASE_PATH"] = previous

    @classmethod
    def tearDownClass(cls):
        cls.initial.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server.DB_PATH = Path(self.temp.name) / "test.sqlite3"
        self.server.init_database()
        self.addCleanup(self.temp.cleanup)

    def request(self, path, method="GET", data=None, raw=None, content_type="application/json", origin=None):
        environ = {}
        setup_testing_defaults(environ)
        body = raw if raw is not None else json.dumps(data).encode() if data is not None else b""
        environ.update(PATH_INFO=path, REQUEST_METHOD=method, CONTENT_TYPE=content_type,
                       CONTENT_LENGTH=str(len(body)), HTTP_HOST="localhost", **{"wsgi.input": io.BytesIO(body)})
        if origin:
            environ["HTTP_ORIGIN"] = origin
        response = {}
        def start_response(status, headers):
            response.update(status=int(status[:3]), headers=dict(headers))
        payload = b"".join(self.server.application(environ, start_response))
        response["body"] = json.loads(payload) if "application/json" in response["headers"]["Content-Type"] and payload else payload
        return response

    def create(self, entity, data):
        response = self.request("/api/" + entity, "POST", data)
        self.assertEqual(response["status"], 201, response)
        return response["body"]["ID"]

    def graph(self):
        country = self.create("countries", {"CountryFull": "Республика Беларусь", "CountryShort": "Беларусь"})
        region = self.create("regions", {"CountryID": country, "Region": "Минская область"})
        city = self.create("cities", {"RegionID": region, "City": "Минск"})
        data = {"Person": "Учебный клиент", "CityID": city, "Street": "Тестовая", "Building": "10А", "Office": "2"}
        address = self.create("addresses", data)
        return country, region, city, address, data

    def test_full_crud_and_foreign_key_protection(self):
        country, region, city, address, data = self.graph()
        for entity, record_id in [("countries", country), ("regions", region), ("cities", city)]:
            self.assertEqual(self.request(f"/api/{entity}/{record_id}", "DELETE")["status"], 409)
        data["Building"] = "20Б"
        self.assertEqual(self.request(f"/api/addresses/{address}", "PUT", data)["body"]["Building"], "20Б")
        self.assertEqual(self.request(f"/api/addresses/{address}")["body"]["Office"], "2")
        for entity, record_id in [("addresses", address), ("cities", city), ("regions", region), ("countries", country)]:
            self.assertEqual(self.request(f"/api/{entity}/{record_id}", "DELETE")["status"], 200)
        self.assertEqual(self.request(f"/api/addresses/{address}", "PUT", data)["status"], 404)
        self.assertTrue(all(not rows for rows in self.request("/api/snapshot")["body"].values()))

    def test_validation_duplicates_and_missing_foreign_keys(self):
        self.assertEqual(self.request("/api/countries", "POST", {"CountryFull": " ", "CountryShort": "BY"})["status"], 400)
        self.assertEqual(self.request("/api/regions", "POST", {"CountryID": True, "Region": "A"})["status"], 400)
        self.assertEqual(self.request("/api/regions", "POST", {"CountryID": 99, "Region": "A"})["status"], 409)
        data = {"CountryFull": "Test country", "CountryShort": "TC"}
        self.create("countries", data)
        self.assertEqual(self.request("/api/countries", "POST", data)["status"], 409)
        self.assertEqual(self.request("/api/countries", "POST", {**data, "ID": 20})["status"], 400)
        self.assertEqual(self.request("/api/countries", "POST", {"CountryFull": "X" * 121, "CountryShort": "X"})["status"], 400)

    def test_updates_of_all_reference_tables(self):
        country, region, city, _, _ = self.graph()
        updates = [("countries", country, {"CountryFull": "Belarus", "CountryShort": "BY"}),
                   ("regions", region, {"CountryID": country, "Region": "Region updated"}),
                   ("cities", city, {"RegionID": region, "City": "City updated"})]
        for entity, record_id, data in updates:
            self.assertEqual(self.request(f"/api/{entity}/{record_id}", "PUT", data)["status"], 200)
            self.assertEqual(self.request(f"/api/{entity}/{record_id}")["body"], {"ID": record_id, **data})

    def test_persistence_and_optional_office(self):
        _, _, _, _, data = self.graph()
        data.pop("Office")
        self.create("addresses", data)
        self.server.init_database()
        snapshot = self.request("/api/snapshot")["body"]
        self.assertEqual(len(snapshot["addresses"]), 2)
        self.assertEqual(snapshot["addresses"][0]["Office"], "")
        self.assertEqual(self.request("/api/health")["body"]["status"], "ok")

    def test_demo_is_atomic_and_does_not_overwrite_data(self):
        self.assertEqual(self.request("/api/demo", "POST")["status"], 200)
        before = self.request("/api/snapshot")["body"]
        self.assertEqual([len(before[key]) for key in ["countries", "regions", "cities", "addresses"]], [2, 3, 3, 4])
        self.assertEqual(self.request("/api/demo", "POST")["status"], 409)
        self.assertEqual(before, self.request("/api/snapshot")["body"])

    def test_bad_requests_and_origin(self):
        self.assertEqual(self.request("/api/countries", "POST", raw=b"{")["status"], 400)
        self.assertEqual(self.request("/api/countries", "POST", raw=b"{}", content_type="text/plain")["status"], 415)
        self.assertEqual(self.request("/api/countries", "POST", raw=b"x" * 17000)["status"], 413)
        self.assertEqual(self.request("/api/demo", "POST", origin="https://another-site.example")["status"], 403)
        self.assertEqual(self.request("/api/countries", "PATCH")["status"], 405)

    def test_static_files_and_database_cannot_be_downloaded(self):
        response = self.request("/")
        self.assertEqual(response["status"], 200)
        self.assertIn("Адреса клиентов".encode(), response["body"])
        for path in ["/../server.py", "/%2e%2e/schema.sql", "/data/addresses.sqlite3", "/api/unknown"]:
            self.assertEqual(self.request(path)["status"], 404)
        self.assertEqual(self.request("/", "HEAD")["body"], b"")


if __name__ == "__main__":
    unittest.main()
