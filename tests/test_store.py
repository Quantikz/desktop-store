from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from desktop_store.db import Store
from desktop_store.lan import LanServer, local_url
from desktop_store.money import naira, parse_amount


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["DESKTOP_STORE_DB"] = str(Path(self.tmp.name) / "store.db")
        self.store = Store(Path(self.tmp.name) / "store.db")

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def test_starts_empty(self) -> None:
        self.assertFalse(self.store.registered())
        self.assertEqual(self.store.products(), [])
        with self.assertRaises(ValueError):
            self.store.shop()

    def test_register_then_login(self) -> None:
        user = self.store.register(
            shop_name="Green Basket",
            owner_name="Ada Okafor",
            username="ada",
            password="secret123",
            city="Lagos",
        )
        self.assertEqual(user["role"], "owner")
        self.assertTrue(self.store.registered())
        self.assertEqual(self.store.shop()["name"], "Green Basket")
        with self.assertRaises(ValueError):
            self.store.login("ada", "wrongpass")
        again = self.store.login("Ada", "secret123")
        self.assertEqual(again["id"], user["id"])

    def test_no_demo_password(self) -> None:
        self.store.register(
            shop_name="Mart",
            owner_name="Owner",
            username="owner",
            password="realpass1",
        )
        for guess in ("1234", "admin", "password", "demo"):
            with self.assertRaises(ValueError):
                self.store.login("owner", guess)

    def test_sale_profit_uses_buying_cost(self) -> None:
        owner = self.store.register(
            shop_name="Mart",
            owner_name="Owner",
            username="owner",
            password="realpass1",
        )
        rice = self.store.save_product(
            {
                "name": "Rice 5kg",
                "sku": "RICE5",
                "price_cents": 800000,
                "cost_cents": 620000,
                "stock": 10,
            }
        )
        sale = self.store.checkout(owner["id"], [{"product_id": rice["id"], "qty": 2}], "cash")
        self.assertEqual(sale["total_cents"], 1_600_000)
        self.assertEqual(sale["cost_cents"], 1_240_000)
        self.assertEqual(sale["profit_cents"], 360_000)

    def test_cannot_sell_more_than_stock(self) -> None:
        owner = self.store.register(
            shop_name="Mart",
            owner_name="Owner",
            username="owner",
            password="realpass1",
        )
        milk = self.store.save_product({"name": "Milk", "price_cents": 1000, "cost_cents": 700, "stock": 1})
        with self.assertRaises(ValueError):
            self.store.checkout(owner["id"], [{"product_id": milk["id"], "qty": 2}])

    def test_money(self) -> None:
        self.assertEqual(naira(123456), "₦1,234.56")
        self.assertEqual(parse_amount("1,234.56"), 123456)

    def test_lan_opens_on_this_computer(self) -> None:
        self.store.register(
            shop_name="Mart",
            owner_name="Owner",
            username="owner",
            password="realpass1",
        )
        server = LanServer(self.store.path, port=18787)
        server.start()
        try:
            page = urlopen(local_url(server.port) + "/", timeout=3).read().decode()
            self.assertIn("Sign in", page)
            self.assertIn("Mart", page)
        finally:
            server.stop()

    def test_lan_register_on_first_use(self) -> None:
        self.assertFalse(self.store.registered())
        server = LanServer(self.store.path, port=18788)
        server.start()
        try:
            page = urlopen(local_url(server.port) + "/", timeout=3).read().decode()
            self.assertIn("Register this store", page)
            data = urlencode(
                {
                    "shop_name": "Termux Mart",
                    "owner_name": "Ada",
                    "username": "ada",
                    "password": "secret123",
                    "confirm": "secret123",
                    "city": "Lagos",
                }
            ).encode()
            req = Request(local_url(server.port) + "/register", data=data, method="POST")
            try:
                urlopen(req, timeout=3)
            except Exception:
                pass
        finally:
            server.stop()
        self.store.close()
        self.store = Store(Path(os.environ["DESKTOP_STORE_DB"]))
        self.assertTrue(self.store.registered())
        self.assertEqual(self.store.shop()["name"], "Termux Mart")


if __name__ == "__main__":
    unittest.main()
