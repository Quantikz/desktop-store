from __future__ import annotations

import html
import os
import socket
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from desktop_store.db import Store
from desktop_store.money import naira
from desktop_store.paths import db_path

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


def css() -> str:
    return """
    :root { --ink:#1C1917; --paper:#F4EFE6; --card:#FFFBF5; --line:#E6DFD2; --forest:#2F4A3C; --muted:#6B645C; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: Segoe UI, Helvetica Neue, sans-serif; background:var(--paper); color:var(--ink); }
    header { background:var(--forest); color:#F4EFE6; padding:16px 20px; }
    header a { color:#F4EFE6; margin-right:14px; text-decoration:none; }
    main { max-width: 920px; margin: 0 auto; padding: 20px; }
    .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; margin:12px 0; }
    h1 { font-size: 28px; margin: 0 0 8px; }
    p.muted { color:var(--muted); }
    input, select, button { font: inherit; padding:10px 12px; border-radius:10px; border:1px solid #D7CFC0; width:100%; }
    button { background:var(--forest); color:#F4EFE6; border:0; font-weight:600; cursor:pointer; }
    .row { display:flex; gap:10px; align-items:center; }
    .grid { display:grid; gap:12px; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); }
    .stat { font-size: 22px; font-weight: 600; }
    .error { color:#9B2C2C; }
    img.thumb { width:100%; height:140px; object-fit:cover; border-radius:10px; background:#EFE8DC; }
    """


def page(title: str, body: str, shop_name: str) -> bytes:
    doc = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{css()}</style>
</head><body>
<header>
  <strong>{html.escape(shop_name)}</strong>
  <div style="margin-top:8px">
    <a href="/">Home</a>
    <a href="/shop">Shop</a>
    <a href="/till">Till</a>
    <a href="/performance">Performance</a>
    <a href="/logout">Sign out</a>
  </div>
</header>
<main>{body}</main>
</body></html>"""
    return doc.encode("utf-8")


class LanState:
    def __init__(self, db: Path, port: int) -> None:
        self.db = db
        self.port = port
        self.secret = f"desktop-store:{db}"

    def store(self) -> Store:
        return Store(self.db)


class Handler(BaseHTTPRequestHandler):
    state: LanState

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def store(self) -> Store:
        return self.state.store()

    def user(self):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        raw = cookie.get("ds_user")
        if not raw:
            return None
        try:
            user_id = int(raw.value)
            return self.store().user_by_id(user_id)
        except Exception:
            return None

    def send_html(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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
        if path.startswith("/image/"):
            self.serve_image(path.split("/", 2)[-1])
            return
        shop_name = "Desktop Store"
        try:
            shop_name = self.store().shop()["name"]
        except Exception:
            pass
        user = self.user()
        if path == "/logout":
            self.redirect("/", "ds_user=; Max-Age=0; Path=/")
            return
        if path == "/login" or not user:
            body = """
            <div class="card">
              <p class="muted">This computer</p>
              <h1>Sign in</h1>
              <p class="muted">Same username and password you created on this PC. Phones on this Wi‑Fi use it too.</p>
              <form method="post" action="/login">
                <p><input name="username" placeholder="Username" autocomplete="username"></p>
                <p><input name="password" type="password" placeholder="Password" autocomplete="current-password"></p>
                <p><button type="submit">Open</button></p>
              </form>
            </div>"""
            self.send_html(page("Sign in", body, shop_name))
            return
        if path == "/shop":
            self.send_html(self.shop_page(shop_name, user))
            return
        if path == "/till":
            self.send_html(self.till_page(shop_name))
            return
        if path == "/performance":
            self.send_html(self.performance_page(shop_name))
            return
        self.send_html(self.home_page(shop_name, user))

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        form = self.read_form()
        store = self.store()
        if path == "/login":
            try:
                user = store.login(form.get("username", ""), form.get("password", ""))
            except ValueError:
                self.redirect("/login")
                return
            self.redirect("/", f"ds_user={user['id']}; Path=/; SameSite=Lax")
            return
        user = self.user()
        if not user:
            self.redirect("/login")
            return
        if path == "/buy":
            try:
                store.checkout(user["id"], [{"product_id": int(form["product_id"]), "qty": int(form.get("qty") or 1)}], "cash")
            except (ValueError, KeyError):
                self.redirect("/shop")
                return
            self.redirect("/shop")
            return
        if path == "/till":
            sku = (form.get("sku") or "").strip()
            qty = int(form.get("qty") or 1)
            product = store.find_product(sku)
            if not product:
                self.redirect("/till")
                return
            try:
                store.checkout(user["id"], [{"product_id": product["id"], "qty": qty}], form.get("pay") or "cash")
            except ValueError:
                self.redirect("/till")
                return
            self.redirect("/till")
            return
        self.redirect("/")

    def home_page(self, shop_name: str, user: dict) -> bytes:
        stats = self.store().performance()
        phones = "".join(f"<p><code>{html.escape(u)}</code></p>" for u in lan_urls(self.state.port)) or "<p class='muted'>Connect Wi‑Fi to share with phones.</p>"
        body = f"""
        <p class="muted">{html.escape(user['full_name'])}</p>
        <h1>{html.escape(shop_name)}</h1>
        <p class="muted">This computer is the shop. Phones on the same Wi‑Fi open the address below, then sign in.</p>
        <div class="card"><p class="muted">This computer</p><p class="stat">{html.escape(local_url(self.state.port))}</p></div>
        <div class="card"><p class="muted">Phones on this Wi‑Fi</p>{phones}</div>
        <div class="grid">
          <div class="card"><p class="muted">Today</p><p class="stat">{naira(stats['today_sales'])}</p></div>
          <div class="card"><p class="muted">Gross profit</p><p class="stat">{naira(stats['profit'])}</p></div>
          <div class="card"><p class="muted">Stock at cost</p><p class="stat">{naira(stats['stock_cost'])}</p></div>
        </div>"""
        return page(shop_name, body, shop_name)

    def shop_page(self, shop_name: str, user: dict) -> bytes:
        products = self.store().products(active_only=True)
        if not products:
            inner = "<div class='card'><h1>No products yet</h1><p class='muted'>Add them on this computer first.</p></div>"
        else:
            cards = []
            for product in products:
                img = f"/image/{product['id']}" if product.get("image_path") else ""
                photo = f"<img class='thumb' src='{img}' alt=''>" if img else ""
                cards.append(
                    f"""<div class="card">{photo}
                    <strong>{html.escape(product['name'])}</strong>
                    <p class="muted">{naira(product['price_cents'])} · buying {naira(product['cost_cents'])} · stock {product['stock']}</p>
                    <form method="post" action="/buy">
                      <input type="hidden" name="product_id" value="{product['id']}">
                      <div class="row"><input type="number" name="qty" value="1" min="1">
                      <button type="submit">Sell 1</button></div>
                    </form></div>"""
                )
            inner = "<h1>Shop</h1><div class='grid'>" + "".join(cards) + "</div>"
        return page("Shop", inner, shop_name)

    def till_page(self, shop_name: str) -> bytes:
        body = """
        <h1>Till</h1>
        <p class="muted">Type the product name or SKU. Stock falls when the sale is saved.</p>
        <form class="card" method="post" action="/till">
          <p><input name="sku" placeholder="Name or SKU" autofocus></p>
          <p><input name="qty" type="number" value="1" min="1"></p>
          <p><select name="pay"><option>cash</option><option>transfer</option><option>card</option></select></p>
          <p><button type="submit">Complete sale</button></p>
        </form>"""
        return page("Till", body, shop_name)

    def performance_page(self, shop_name: str) -> bytes:
        stats = self.store().performance()
        body = f"""
        <h1>Performance</h1>
        <p class="muted">Profit is selling price minus buying cost.</p>
        <div class="grid">
          <div class="card"><p class="muted">Sales</p><p class="stat">{naira(stats['sales'])}</p></div>
          <div class="card"><p class="muted">Cost of stock sold</p><p class="stat">{naira(stats['cost'])}</p></div>
          <div class="card"><p class="muted">Gross profit</p><p class="stat">{naira(stats['profit'])}</p></div>
          <div class="card"><p class="muted">Stock on hand at cost</p><p class="stat">{naira(stats['stock_cost'])}</p></div>
        </div>"""
        return page("Performance", body, shop_name)

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
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


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
