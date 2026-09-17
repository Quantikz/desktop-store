from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from desktop_store.auth import hash_password, valid_username, verify_password
from desktop_store.paths import db_path, images_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS shop (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL,
    tagline TEXT NOT NULL DEFAULT '',
    street TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    hours TEXT NOT NULL DEFAULT '',
    currency TEXT NOT NULL DEFAULT 'NGN',
    ticket_prefix TEXT NOT NULL DEFAULT 'DS',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'staff')),
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    subtitle TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'Other',
    unit TEXT NOT NULL DEFAULT 'each',
    price_cents INTEGER NOT NULL DEFAULT 0,
    cost_cents INTEGER NOT NULL DEFAULT 0,
    stock INTEGER NOT NULL DEFAULT 0,
    reorder_at INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    image_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    number TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    cashier_id INTEGER NOT NULL,
    pay_method TEXT NOT NULL DEFAULT 'cash',
    subtotal_cents INTEGER NOT NULL,
    total_cents INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (cashier_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER,
    sku TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    unit TEXT NOT NULL DEFAULT 'each',
    qty INTEGER NOT NULL,
    price_cents INTEGER NOT NULL,
    cost_cents INTEGER NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CATEGORIES = [
    "Fruits & vegetables",
    "Dairy & eggs",
    "Bread & pastry",
    "Meat & fish",
    "Dry food",
    "Frozen",
    "Drinks",
    "Home",
    "Other",
]

UNITS = ["each", "pack", "kg", "g", "litre", "ml", "bunch", "loaf"]
PAY_METHODS = ["cash", "transfer", "card"]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class Store:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        images_dir().mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def registered(self) -> bool:
        n = self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        return int(n) > 0

    def register(
        self,
        *,
        shop_name: str,
        owner_name: str,
        username: str,
        password: str,
        tagline: str = "",
        street: str = "",
        city: str = "",
        phone: str = "",
        hours: str = "",
    ) -> dict[str, Any]:
        if self.registered():
            raise ValueError("This computer already has a store. Sign in instead.")
        shop_name = shop_name.strip()
        owner_name = owner_name.strip()
        username = username.strip()
        if len(shop_name) < 2:
            raise ValueError("Enter the store name.")
        if len(owner_name) < 2:
            raise ValueError("Enter your full name.")
        if not valid_username(username):
            raise ValueError("Username must start with a letter and be 3–32 characters.")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        salt, digest = hash_password(password)
        created = now_iso()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO shop (id, name, tagline, street, city, phone, hours, created_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                """,
                (shop_name, tagline.strip(), street.strip(), city.strip(), phone.strip(), hours.strip(), created),
            )
            cur = self.conn.execute(
                """
                INSERT INTO users (full_name, username, password_salt, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'owner', ?)
                """,
                (owner_name, username, salt, digest, created),
            )
        return self.user_by_id(int(cur.lastrowid))

    def login(self, username: str, password: str) -> dict[str, Any]:
        row = _row(
            self.conn.execute(
                "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
                (username.strip(),),
            ).fetchone()
        )
        if not row or not row["active"]:
            raise ValueError("Wrong username or password.")
        if not verify_password(password, row["password_salt"], row["password_hash"]):
            raise ValueError("Wrong username or password.")
        return row

    def shop(self) -> dict[str, Any]:
        row = _row(self.conn.execute("SELECT * FROM shop WHERE id = 1").fetchone())
        if not row:
            raise ValueError("Store is not registered yet.")
        return row

    def save_shop(self, **fields: Any) -> dict[str, Any]:
        allowed = {"name", "tagline", "street", "city", "phone", "hours", "currency", "ticket_prefix"}
        current = self.shop()
        for key, value in fields.items():
            if key not in allowed:
                continue
            current[key] = str(value).strip()
        if len(current["name"]) < 2:
            raise ValueError("Store name is required.")
        with self.conn:
            self.conn.execute(
                """
                UPDATE shop SET name=?, tagline=?, street=?, city=?, phone=?, hours=?,
                    currency=?, ticket_prefix=? WHERE id = 1
                """,
                (
                    current["name"],
                    current["tagline"],
                    current["street"],
                    current["city"],
                    current["phone"],
                    current["hours"],
                    current["currency"] or "NGN",
                    (current["ticket_prefix"] or "DS").upper()[:8],
                ),
            )
        return self.shop()

    def users(self) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self.conn.execute(
                "SELECT id, full_name, username, role, active, created_at FROM users ORDER BY id"
            )
        ]

    def user_by_id(self, user_id: int) -> dict[str, Any]:
        row = _row(self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
        if not row:
            raise ValueError("User not found.")
        return row

    def add_staff(self, full_name: str, username: str, password: str) -> dict[str, Any]:
        full_name = full_name.strip()
        username = username.strip()
        if len(full_name) < 2:
            raise ValueError("Enter the staff name.")
        if not valid_username(username):
            raise ValueError("Username must start with a letter and be 3–32 characters.")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if self.conn.execute("SELECT 1 FROM users WHERE username = ? COLLATE NOCASE", (username,)).fetchone():
            raise ValueError("That username is already used.")
        salt, digest = hash_password(password)
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO users (full_name, username, password_salt, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'staff', ?)
                """,
                (full_name, username, salt, digest, now_iso()),
            )
        return self.user_by_id(int(cur.lastrowid))

    def set_user_active(self, user_id: int, active: bool) -> None:
        user = self.user_by_id(user_id)
        if user["role"] == "owner" and not active:
            raise ValueError("The owner account cannot be turned off.")
        with self.conn:
            self.conn.execute("UPDATE users SET active = ? WHERE id = ?", (1 if active else 0, user_id))

    def change_password(self, user_id: int, current: str, new: str) -> None:
        user = self.user_by_id(user_id)
        if not verify_password(current, user["password_salt"], user["password_hash"]):
            raise ValueError("Current password is wrong.")
        if len(new) < 8:
            raise ValueError("New password must be at least 8 characters.")
        salt, digest = hash_password(new)
        with self.conn:
            self.conn.execute(
                "UPDATE users SET password_salt = ?, password_hash = ? WHERE id = ?",
                (salt, digest, user_id),
            )

    def products(self, active_only: bool = False) -> list[dict[str, Any]]:
        sql = "SELECT * FROM products"
        if active_only:
            sql += " WHERE active = 1"
        sql += " ORDER BY name COLLATE NOCASE"
        return [dict(r) for r in self.conn.execute(sql)]

    def product(self, product_id: int) -> dict[str, Any]:
        row = _row(self.conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone())
        if not row:
            raise ValueError("Product not found.")
        return row

    def find_product(self, query: str) -> dict[str, Any] | None:
        q = query.strip()
        if not q:
            return None
        row = _row(
            self.conn.execute(
                """
                SELECT * FROM products
                WHERE active = 1 AND (sku = ? COLLATE NOCASE OR name = ? COLLATE NOCASE)
                """,
                (q, q),
            ).fetchone()
        )
        if row:
            return row
        rows = self.conn.execute(
            "SELECT * FROM products WHERE active = 1 AND name LIKE ? ORDER BY name LIMIT 2",
            (f"%{q}%",),
        ).fetchall()
        if len(rows) == 1:
            return dict(rows[0])
        return None

    def save_product(self, data: dict[str, Any], product_id: int | None = None) -> dict[str, Any]:
        name = str(data.get("name") or "").strip()
        sku = str(data.get("sku") or "").strip().upper()
        if len(name) < 1:
            raise ValueError("Enter the product name.")
        price = int(data.get("price_cents") or 0)
        cost = int(data.get("cost_cents") or 0)
        stock = int(data.get("stock") or 0)
        reorder = int(data.get("reorder_at") or 0)
        if price < 0 or cost < 0:
            raise ValueError("Price and buying cost cannot be negative.")
        if stock < 0 or reorder < 0:
            raise ValueError("Stock cannot be negative.")
        if not sku:
            sku = self._next_sku()
        payload = (
            sku,
            name,
            str(data.get("subtitle") or "").strip(),
            str(data.get("category") or "Other").strip() or "Other",
            str(data.get("unit") or "each").strip() or "each",
            price,
            cost,
            stock,
            reorder,
            1 if data.get("active", True) else 0,
            str(data.get("image_path") or ""),
        )
        try:
            with self.conn:
                if product_id:
                    self.conn.execute(
                        """
                        UPDATE products SET sku=?, name=?, subtitle=?, category=?, unit=?,
                            price_cents=?, cost_cents=?, stock=?, reorder_at=?, active=?, image_path=?
                        WHERE id=?
                        """,
                        (*payload, product_id),
                    )
                    pid = product_id
                else:
                    cur = self.conn.execute(
                        """
                        INSERT INTO products (
                            sku, name, subtitle, category, unit, price_cents, cost_cents,
                            stock, reorder_at, active, image_path, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (*payload, now_iso()),
                    )
                    pid = int(cur.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ValueError("That SKU is already used.") from exc
        return self.product(pid)

    def delete_product(self, product_id: int) -> None:
        with self.conn:
            self.conn.execute("UPDATE products SET active = 0 WHERE id = ?", (product_id,))

    def adjust_stock(self, product_id: int, qty: int) -> dict[str, Any]:
        product = self.product(product_id)
        next_stock = int(product["stock"]) + int(qty)
        if next_stock < 0:
            raise ValueError("Stock cannot go below zero.")
        with self.conn:
            self.conn.execute("UPDATE products SET stock = ? WHERE id = ?", (next_stock, product_id))
        return self.product(product_id)

    def checkout(
        self,
        cashier_id: int,
        items: list[dict[str, Any]],
        pay_method: str = "cash",
        note: str = "",
    ) -> dict[str, Any]:
        if not items:
            raise ValueError("Add at least one item.")
        if pay_method not in PAY_METHODS:
            pay_method = "cash"
        lines = []
        for item in items:
            product = self.product(int(item["product_id"]))
            qty = int(item["qty"])
            if qty < 1:
                raise ValueError("Quantity must be at least 1.")
            if int(product["stock"]) < qty:
                raise ValueError(f"Not enough {product['name']} in stock.")
            lines.append((product, qty))
        subtotal = sum(product["price_cents"] * qty for product, qty in lines)
        number = self._next_ticket()
        created = now_iso()
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO orders (number, created_at, cashier_id, pay_method, subtotal_cents, total_cents, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (number, created, cashier_id, pay_method, subtotal, subtotal, note.strip()),
            )
            order_id = int(cur.lastrowid)
            for product, qty in lines:
                self.conn.execute(
                    """
                    INSERT INTO order_items (
                        order_id, product_id, sku, name, unit, qty, price_cents, cost_cents
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_id,
                        product["id"],
                        product["sku"],
                        product["name"],
                        product["unit"],
                        qty,
                        product["price_cents"],
                        product["cost_cents"],
                    ),
                )
                self.conn.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ?",
                    (qty, product["id"]),
                )
        return self.order(order_id)

    def orders(self) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self.conn.execute(
                """
                SELECT o.*, u.full_name AS cashier
                FROM orders o JOIN users u ON u.id = o.cashier_id
                ORDER BY o.id DESC
                """
            )
        ]

    def order(self, order_id: int) -> dict[str, Any]:
        row = _row(
            self.conn.execute(
                """
                SELECT o.*, u.full_name AS cashier
                FROM orders o JOIN users u ON u.id = o.cashier_id
                WHERE o.id = ?
                """,
                (order_id,),
            ).fetchone()
        )
        if not row:
            raise ValueError("Sale not found.")
        items = [
            dict(r)
            for r in self.conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
        ]
        row["items"] = items
        row["cost_cents"] = sum(i["cost_cents"] * i["qty"] for i in items)
        row["profit_cents"] = row["total_cents"] - row["cost_cents"]
        return row

    def performance(self) -> dict[str, Any]:
        orders = [self.order(o["id"]) for o in self.orders()]
        products = self.products()
        revenue = sum(o["total_cents"] for o in orders)
        cost = sum(o["cost_cents"] for o in orders)
        profit = revenue - cost
        today = datetime.now().date().isoformat()
        today_orders = [o for o in orders if str(o["created_at"])[:10] == today]
        on_hand = [p for p in products if p["active"]]
        stock_cost = sum(p["stock"] * p["cost_cents"] for p in on_hand)
        stock_retail = sum(p["stock"] * p["price_cents"] for p in on_hand)
        low = [p for p in on_hand if p["stock"] <= p["reorder_at"]]
        by_product: dict[int, dict[str, Any]] = {}
        for order in orders:
            for item in order["items"]:
                key = int(item["product_id"] or 0)
                cur = by_product.setdefault(
                    key,
                    {"name": item["name"], "qty": 0, "sales": 0, "cost": 0, "profit": 0},
                )
                qty = int(item["qty"])
                sales = int(item["price_cents"]) * qty
                cogs = int(item["cost_cents"]) * qty
                cur["qty"] += qty
                cur["sales"] += sales
                cur["cost"] += cogs
                cur["profit"] += sales - cogs
        ranking = sorted(by_product.values(), key=lambda r: r["profit"], reverse=True)[:12]
        days = []
        for i in range(6, -1, -1):
            d = datetime.now().date().fromordinal(datetime.now().date().toordinal() - i).isoformat()
            slice_ = [o for o in orders if str(o["created_at"])[:10] == d]
            days.append(
                {
                    "day": d,
                    "sales": sum(o["total_cents"] for o in slice_),
                    "cost": sum(o["cost_cents"] for o in slice_),
                    "profit": sum(o["profit_cents"] for o in slice_),
                    "count": len(slice_),
                }
            )
        return {
            "sales": revenue,
            "cost": cost,
            "profit": profit,
            "count": len(orders),
            "today_sales": sum(o["total_cents"] for o in today_orders),
            "today_profit": sum(o["profit_cents"] for o in today_orders),
            "today_count": len(today_orders),
            "stock_cost": stock_cost,
            "stock_retail": stock_retail,
            "stock_units": sum(p["stock"] for p in on_hand),
            "low": low,
            "ranking": ranking,
            "days": days,
        }

    def _next_sku(self) -> str:
        n = self.conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        return f"SKU-{int(n) + 1:04d}"

    def _next_ticket(self) -> str:
        prefix = self.shop()["ticket_prefix"] or "DS"
        n = self.conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        return f"{prefix}-{int(n) + 1:05d}"
