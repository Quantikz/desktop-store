from __future__ import annotations

import html

from desktop_store.money import naira


def css() -> str:
    return """
:root{--ink:#1C1917;--paper:#F4EFE6;--card:#FFFBF5;--line:#E6DFD2;--forest:#2F4A3C;--muted:#6B645C;--danger:#9B2C2C}
*{box-sizing:border-box}
html,body{margin:0;background:var(--paper);color:var(--ink);font-family:"Segoe UI",system-ui,sans-serif}
body{padding-bottom:84px}
header{position:sticky;top:0;z-index:20;background:var(--forest);color:#F4EFE6;padding:14px 16px}
header strong{display:block;font-size:18px}
header span{display:block;font-size:12px;opacity:.8;margin-top:2px}
main{max-width:560px;margin:0 auto;padding:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;margin:0 0 12px}
h1{font-size:26px;letter-spacing:-.4px;margin:0 0 8px}
.muted{color:var(--muted);font-size:14px;line-height:1.45}
.stat{font-size:22px;font-weight:650;word-break:break-all}
label{display:block;font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:10px 0 6px}
input,select,button,textarea{font:inherit;width:100%;padding:12px 14px;border-radius:12px;border:1px solid #D7CFC0;background:#fff}
button{background:var(--forest);color:#F4EFE6;border:0;font-weight:650;min-height:48px}
button.ghost{background:#fff;color:var(--forest);border:1px solid #D7CFC0}
button.danger{background:var(--danger)}
.row{display:flex;gap:8px;align-items:center}
.grid{display:grid;gap:10px;grid-template-columns:1fr 1fr}
.list{display:flex;flex-direction:column;gap:10px}
.item{display:flex;gap:12px;align-items:center}
.item img,.thumb{width:64px;height:64px;border-radius:12px;object-fit:cover;background:#EFE8DC;flex:none}
.error{color:var(--danger)}
code{font-size:13px}
nav.tab{position:fixed;left:0;right:0;bottom:0;background:#2F4A3C;display:flex;padding:8px 6px calc(8px + env(safe-area-inset-bottom));z-index:30}
nav.tab a{flex:1;text-align:center;color:#C9D5CC;text-decoration:none;font-size:11px;padding:8px 4px;border-radius:10px}
nav.tab a.on{background:#F4EFE6;color:#2F4A3C;font-weight:650}
@media(min-width:800px){main{max-width:860px}.grid3{grid-template-columns:repeat(3,1fr)}}
"""


def shell(shop: str, title: str, body: str, active: str, extra_head: str = "") -> bytes:
    def tab(href: str, key: str, label: str) -> str:
        on = " on" if active == key else ""
        return f'<a class="{on}" href="{href}">{label}</a>'

    nav = ""
    if active != "login":
        nav = (
            '<nav class="tab">'
            + tab("/", "home", "Home")
            + tab("/shop", "shop", "Shop")
            + tab("/till", "till", "Till")
            + tab("/products", "products", "Products")
            + tab("/performance", "performance", "Performance")
            + "</nav>"
        )
    doc = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#2F4A3C">
<link rel="manifest" href="/manifest.webmanifest">
<title>{html.escape(title)}</title>
<style>{css()}</style>{extra_head}
</head><body>
<header><strong>{html.escape(shop)}</strong><span>This computer and phones on this Wi‑Fi</span></header>
<main>{body}</main>
{nav}
</body></html>"""
    return doc.encode("utf-8")


def register(error: str = "") -> bytes:
    err = f'<p class="error">{html.escape(error)}</p>' if error else ""
    body = f"""
    <div class="card">
      <p class="muted">First use on this phone</p>
      <h1>Register this store</h1>
      <p class="muted">Nothing is saved until you create the store. Choose your own username and password. There is no demo account.</p>
      {err}
      <form method="post" action="/register">
        <label>Store name</label><input name="shop_name" required>
        <label>City</label><input name="city">
        <label>Your full name</label><input name="owner_name" required>
        <label>Username</label><input name="username" autocomplete="username" required>
        <label>Password</label><input name="password" type="password" autocomplete="new-password" required>
        <label>Confirm password</label><input name="confirm" type="password" required>
        <p><button type="submit">Create store</button></p>
      </form>
    </div>"""
    return shell("Desktop Store", "Register", body, "login")


def login(shop: str, error: str = "") -> bytes:
    err = f'<p class="error">{html.escape(error)}</p>' if error else ""
    body = f"""
    <div class="card">
      <p class="muted">Phone and this computer</p>
      <h1>Sign in</h1>
      <p class="muted">Use the username and password created on this computer. Other phones on the same Wi‑Fi use the same address.</p>
      {err}
      <form method="post" action="/login">
        <label>Username</label><input name="username" autocomplete="username">
        <label>Password</label><input name="password" type="password" autocomplete="current-password">
        <p><button type="submit">Open</button></p>
      </form>
    </div>"""
    return shell(shop, "Sign in", body, "login")


def home(shop: str, user: str, local: str, phones: list[str], stats: dict) -> bytes:
    phone_block = "".join(f"<p class='stat'>{html.escape(u)}</p>" for u in phones) or "<p class='muted'>Connect this computer to Wi‑Fi.</p>"
    body = f"""
    <p class="muted">{html.escape(user)}</p>
    <h1>{html.escape(shop)}</h1>
    <p class="muted">This shop is open on this phone. Other phones on the same Wi‑Fi open the Wi‑Fi address, then sign in.</p>
    <div class="card"><p class="muted">This phone</p><p class="stat">{html.escape(local)}</p></div>
    <div class="card"><p class="muted">Share on this Wi‑Fi</p>{phone_block}
      <p class="muted">If a phone cannot open it, allow the program on private networks when Windows asks.</p>
    </div>
    <div class="grid">
      <div class="card"><p class="muted">Today</p><p class="stat">{naira(stats['today_sales'])}</p></div>
      <div class="card"><p class="muted">Profit</p><p class="stat">{naira(stats['profit'])}</p></div>
      <div class="card"><p class="muted">Stock at cost</p><p class="stat">{naira(stats['stock_cost'])}</p></div>
      <div class="card"><p class="muted">Low stock</p><p class="stat">{len(stats['low'])}</p></div>
    </div>
    <p><a href="/logout"><button class="ghost" type="button">Sign out</button></a></p>
    """
    return shell(shop, shop, body, "home")


def shop(shop_name: str, products: list, cart: list, total: int) -> bytes:
    if not products:
        inner = "<div class='card'><h1>No products yet</h1><p class='muted'>Add them on Products. This phone uses the same book as the computer.</p><p><a href='/products'><button>Add a product</button></a></p></div>"
    else:
        cards = []
        for product in products:
            img = f"<img class='thumb' src='/image/{product['id']}' alt=''>" if product.get("image_path") else "<div class='thumb'></div>"
            cards.append(
                f"""<div class="card item">{img}<div>
                <strong>{html.escape(product['name'])}</strong>
                <p class="muted">{naira(product['price_cents'])} · cost {naira(product['cost_cents'])} · {product['stock']} in stock</p>
                <form method="post" action="/cart/add">
                  <input type="hidden" name="product_id" value="{product['id']}">
                  <button type="submit">Add to bag</button>
                </form></div></div>"""
            )
        inner = "<h1>Shop</h1><div class='list'>" + "".join(cards) + "</div>"
    bag = "<p class='muted'>Bag is empty.</p>"
    if cart:
        lines = "".join(
            f"<p>{html.escape(i['name'])} × {i['qty']} — {naira(i['price_cents'] * i['qty'])}</p>" for i in cart
        )
        bag = f"{lines}<p class='stat'>Total {naira(total)}</p>"
        bag += """<form method="post" action="/checkout">
          <label>Pay by</label>
          <select name="pay"><option>cash</option><option>transfer</option><option>card</option></select>
          <p class="row"><button type="submit">Complete sale</button>
          <button class="ghost" formaction="/cart/clear" formmethod="post">Clear</button></p>
        </form>"""
    body = inner + f"<div class='card'><p class='muted'>Bag</p>{bag}</div>"
    return shell(shop_name, "Shop", body, "shop")


def till(shop_name: str, message: str = "") -> bytes:
    note = f"<p class='muted'>{html.escape(message)}</p>" if message else ""
    body = f"""
    <h1>Till</h1>
    <p class="muted">Type a name or SKU. This records a sale on the same computer book.</p>
    {note}
    <form class="card" method="post" action="/till">
      <label>Name or SKU</label><input name="sku" autofocus>
      <label>Qty</label><input name="qty" type="number" value="1" min="1">
      <label>Pay by</label>
      <select name="pay"><option>cash</option><option>transfer</option><option>card</option></select>
      <p><button type="submit">Complete sale</button></p>
    </form>"""
    return shell(shop_name, "Till", body, "till")


def products(shop_name: str, rows: list, message: str = "") -> bytes:
    note = f"<p class='muted'>{html.escape(message)}</p>" if message else ""
    items = "".join(
        f"<div class='card'><strong>{html.escape(p['name'])}</strong><p class='muted'>{p['sku']} · {naira(p['price_cents'])} · buy {naira(p['cost_cents'])} · stock {p['stock']}</p></div>"
        for p in rows
    ) or "<p class='muted'>None yet.</p>"
    body = f"""
    <h1>Products</h1>
    <p class="muted">Add selling price and buying cost. Saved on this computer.</p>
    {note}
    <form class="card" method="post" action="/products">
      <label>Name</label><input name="name" required>
      <label>SKU</label><input name="sku" placeholder="Optional">
      <div class="grid">
        <div><label>Selling price</label><input name="price" inputmode="decimal" placeholder="0.00"></div>
        <div><label>Buying cost</label><input name="cost" inputmode="decimal" placeholder="0.00"></div>
        <div><label>Stock</label><input name="stock" type="number" value="0" min="0"></div>
        <div><label>Reorder at</label><input name="reorder" type="number" value="0" min="0"></div>
      </div>
      <p><button type="submit">Save product</button></p>
    </form>
    {items}"""
    return shell(shop_name, "Products", body, "products")


def performance(shop_name: str, stats: dict) -> bytes:
    ranking = "".join(
        f"<p>{html.escape(r['name'])} · {naira(r['profit'])} profit</p>" for r in stats["ranking"]
    ) or "<p class='muted'>No sales yet.</p>"
    body = f"""
    <h1>Performance</h1>
    <p class="muted">Profit is selling price minus buying cost.</p>
    <div class="grid">
      <div class="card"><p class="muted">Sales</p><p class="stat">{naira(stats['sales'])}</p></div>
      <div class="card"><p class="muted">Cost of stock sold</p><p class="stat">{naira(stats['cost'])}</p></div>
      <div class="card"><p class="muted">Gross profit</p><p class="stat">{naira(stats['profit'])}</p></div>
      <div class="card"><p class="muted">Stock at cost</p><p class="stat">{naira(stats['stock_cost'])}</p></div>
    </div>
    <div class="card"><p class="muted">Products by profit</p>{ranking}</div>"""
    return shell(shop_name, "Performance", body, "performance")


def manifest(name: str) -> bytes:
    return (
        '{"name":'
        + _json(name)
        + ',"short_name":'
        + _json(name)
        + ',"start_url":"/","display":"standalone","background_color":"#F4EFE6","theme_color":"#2F4A3C"}'
    ).encode("utf-8")


def _json(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
