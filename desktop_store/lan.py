from __future__ import annotations

import os
import socket
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from desktop_store.db import Store
from desktop_store.money import parse_amount
from desktop_store.paths import db_path
from desktop_store import phone_html

PORT = int(os.environ.get("DESKTOP_STORE_PORT") or 8080)
HOST = "0.0.0.0"


def lan_urls(port: int = PORT) -> list[str]:
    urls: list[str] = []
    for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
        ip = info[4][0]
        if ip.startswith("127.") or ip.startswith("169.254."):
            continue
        urls.append(f"http://{ip}:{port}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if not ip.startswith("127."):
                urls.insert(0, f"http://{ip}:{port}")
    except OSError:
        pass
    seen: list[str] = []
    for url in urls:
        if url not in seen:
            seen.append(url)
    seen.sort(key=lambda u: (0 if "192.168." in u else 1, u))
    return seen


def local_url(port: int = PORT) -> str:
    return f"http://127.0.0.1:{port}"


def open_private_network(port: int = PORT) -> None:
    if os.name != "nt":
        return
    from subprocess import DEVNULL, Popen

    Popen(
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            "name=Desktop Store",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            f"localport={port}",
            "profile=private",
        ],
        stdout=DEVNULL,
        stderr=DEVNULL,
    )


class LanState:
    def __init__(self, db: Path, port: int) -> None:
        self.db = db
        self.port = port
        self.carts: dict[int, list[dict]] = {}

    def store(self) -> Store:
        return Store(self.db)


class Handler(BaseHTTPRequestHandler):
    state: LanState

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def store(self) -> Store:
        return self.state.store()

    def shop_name(self) -> str:
        try:
            return self.store().shop()["name"]
        except Exception:
            return "Desktop Store"

    def user(self):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        raw = cookie.get("ds_user")
        if not raw:
            return None
        try:
            return self.store().user_by_id(int(raw.value))
        except Exception:
            return None

    def cart_for(self, user_id: int) -> list[dict]:
        return self.state.carts.setdefault(user_id, [])

    def send_html(self, body: bytes, status: int = 200, extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location: str, cookie: str | None = None) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def read_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        parsed = parse_qs(raw, keep_blank_values=True)
        return {k: v[-1] if v else "" for k, v in parsed.items()}

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        shop = self.shop_name()
        if path == "/manifest.webmanifest":
            self.send_bytes(phone_html.manifest(shop), "application/manifest+json")
            return
        if path.startswith("/image/"):
            self.serve_image(path.split("/", 2)[-1])
            return
        if path == "/logout":
            self.redirect("/", "ds_user=; Max-Age=0; Path=/")
            return
        user = self.user()
        if not user:
            self.send_html(phone_html.login(shop))
            return
        if path == "/shop":
            self.send_html(self.shop_view(shop, user))
            return
        if path == "/till":
            self.send_html(phone_html.till(shop))
            return
        if path == "/products":
            self.send_html(phone_html.products(shop, self.store().products()))
            return
        if path == "/performance":
            self.send_html(phone_html.performance(shop, self.store().performance()))
            return
        self.send_html(
            phone_html.home(
                shop,
                user["full_name"],
                local_url(self.state.port),
                lan_urls(self.state.port),
                self.store().performance(),
            )
        )

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        form = self.read_form()
        store = self.store()
        shop = self.shop_name()
        if path == "/login":
            try:
                user = store.login(form.get("username", ""), form.get("password", ""))
            except ValueError as exc:
                self.send_html(phone_html.login(shop, str(exc)))
                return
            self.redirect("/", f"ds_user={user['id']}; Path=/; SameSite=Lax")
            return
        user = self.user()
        if not user:
            self.redirect("/")
            return
        if path == "/cart/add":
            self.add_cart(user["id"], int(form.get("product_id") or 0))
            self.redirect("/shop")
            return
        if path == "/cart/clear":
            self.state.carts[user["id"]] = []
            self.redirect("/shop")
            return
        if path == "/checkout":
            items = [{"product_id": i["product_id"], "qty": i["qty"]} for i in self.cart_for(user["id"])]
            try:
                store.checkout(user["id"], items, form.get("pay") or "cash")
                self.state.carts[user["id"]] = []
            except ValueError:
                pass
            self.redirect("/shop")
            return
        if path == "/till":
            product = store.find_product(form.get("sku") or "")
            message = "No matching product."
            if product:
                try:
                    sale = store.checkout(
                        user["id"],
                        [{"product_id": product["id"], "qty": int(form.get("qty") or 1)}],
                        form.get("pay") or "cash",
                    )
                    message = f"Saved {sale['number']}"
                except ValueError as exc:
                    message = str(exc)
            self.send_html(phone_html.till(shop, message))
            return
        if path == "/products":
            try:
                store.save_product(
                    {
                        "name": form.get("name") or "",
                        "sku": form.get("sku") or "",
                        "price_cents": parse_amount(form.get("price") or "0"),
                        "cost_cents": parse_amount(form.get("cost") or "0"),
                        "stock": int(form.get("stock") or 0),
                        "reorder_at": int(form.get("reorder") or 0),
                    }
                )
                message = "Product saved."
            except ValueError as exc:
                message = str(exc)
            self.send_html(phone_html.products(shop, store.products(), message))
            return
        self.redirect("/")

    def shop_view(self, shop: str, user: dict) -> bytes:
        store = self.store()
        cart_rows = []
        total = 0
        for line in self.cart_for(user["id"]):
            product = store.product(line["product_id"])
            cart_rows.append({**product, "qty": line["qty"]})
            total += product["price_cents"] * line["qty"]
        return phone_html.shop(shop, store.products(active_only=True), cart_rows, total)

    def add_cart(self, user_id: int, product_id: int) -> None:
        if product_id < 1:
            return
        cart = self.cart_for(user_id)
        for line in cart:
            if line["product_id"] == product_id:
                line["qty"] += 1
                return
        cart.append({"product_id": product_id, "qty": 1})

    def serve_image(self, product_id: str) -> None:
        try:
            product = self.store().product(int(product_id))
        except ValueError:
            self.send_error(404)
            return
        path = Path(product.get("image_path") or "")
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        kind = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
        self.send_bytes(data, kind)


class LanServer:
    def __init__(self, db: Path | None = None, port: int = PORT) -> None:
        self.port = port
        self.db = Path(db) if db else db_path()
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        last_error: OSError | None = None
        for port in (self.port, 8787, 9090):
            try:
                Handler.state = LanState(self.db, port)
                self.httpd = ThreadingHTTPServer((HOST, port), Handler)
                self.port = port
                self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
                self.thread.start()
                open_private_network(port)
                return
            except OSError as exc:
                last_error = exc
        raise last_error or OSError("Could not open the shop on this computer.")

    def stop(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
