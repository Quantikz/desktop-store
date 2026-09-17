from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop_store import APP_NAME
from desktop_store.db import CATEGORIES, PAY_METHODS, UNITS, Store
from desktop_store.lan import LanServer, lan_urls, local_url
from desktop_store.money import naira, parse_amount
from desktop_store.paths import app_data_dir, images_dir
from desktop_store.theme import QSS


def _card() -> QFrame:
    frame = QFrame()
    frame.setObjectName("Card")
    return frame


def _title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Title")
    return label


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Muted")
    label.setWordWrap(True)
    return label


def _stat(label: str, value: str, hint: str = "") -> QFrame:
    card = _card()
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    kicker = QLabel(label.upper())
    kicker.setObjectName("Hint")
    kicker.setStyleSheet("letter-spacing: 1.4px; font-size: 11px; color: #6B645C;")
    amount = QLabel(value)
    amount.setObjectName("StatValue")
    layout.addWidget(kicker)
    layout.addWidget(amount)
    if hint:
        layout.addWidget(_muted(hint))
    return card


def warn(parent: QWidget, message: str) -> None:
    QMessageBox.warning(parent, APP_NAME, message)


def info(parent: QWidget, message: str) -> None:
    QMessageBox.information(parent, APP_NAME, message)


class RegisterPage(QWidget):
    def __init__(self, store: Store, on_done) -> None:
        super().__init__()
        self.store = store
        self.on_done = on_done
        self.fields: dict[str, QLineEdit] = {}
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        panel = QFrame()
        panel.setFixedWidth(420)
        panel.setStyleSheet("background:#2F4A3C;")
        side = QVBoxLayout(panel)
        side.setContentsMargins(36, 48, 36, 48)
        brand = QLabel("Desktop Store")
        brand.setObjectName("Brand")
        brand.setStyleSheet("color:#F4EFE6; font-size:28px; font-weight:600;")
        blurb = QLabel(
            "This computer is empty until you register.\n\n"
            "Choose the store name and your own sign-in. Nothing is saved until you create the store."
        )
        blurb.setWordWrap(True)
        blurb.setStyleSheet("color:#C9D5CC; font-size:14px;")
        side.addWidget(brand)
        side.addSpacing(12)
        side.addWidget(blurb)
        side.addStretch()
        form_wrap = QWidget()
        form = QVBoxLayout(form_wrap)
        form.setContentsMargins(48, 40, 48, 40)
        form.addWidget(_title("Register this store"))
        form.addWidget(_muted("All of this is stored only on this computer."))
        grid = QFormLayout()
        grid.setSpacing(10)
        for key, label in [
            ("shop_name", "Store name"),
            ("city", "City"),
            ("street", "Street"),
            ("phone", "Phone"),
            ("owner_name", "Your full name"),
            ("username", "Username"),
            ("password", "Password"),
            ("confirm", "Confirm password"),
        ]:
            field = QLineEdit()
            if key in {"password", "confirm"}:
                field.setEchoMode(QLineEdit.Password)
            self.fields[key] = field
            grid.addRow(label, field)
        form.addLayout(grid)
        self.error = _muted("")
        self.error.setStyleSheet("color:#9B2C2C;")
        form.addWidget(self.error)
        go = QPushButton("Create store")
        go.clicked.connect(self.submit)
        form.addWidget(go)
        form.addStretch()
        root.addWidget(panel)
        root.addWidget(form_wrap, 1)

    def submit(self) -> None:
        data = {k: v.text() for k, v in self.fields.items()}
        if data["password"] != data["confirm"]:
            self.error.setText("Passwords do not match.")
            return
        try:
            user = self.store.register(
                shop_name=data["shop_name"],
                owner_name=data["owner_name"],
                username=data["username"],
                password=data["password"],
                street=data["street"],
                city=data["city"],
                phone=data["phone"],
            )
        except ValueError as exc:
            self.error.setText(str(exc))
            return
        self.on_done(user)


class LoginPage(QWidget):
    def __init__(self, store: Store, on_done) -> None:
        super().__init__()
        self.store = store
        self.on_done = on_done
        wrap = QVBoxLayout(self)
        wrap.setAlignment(Qt.AlignCenter)
        card = _card()
        card.setFixedWidth(420)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 28)
        shop = self.store.shop()
        layout.addWidget(_muted("This computer"))
        layout.addWidget(_title(shop["name"]))
        layout.addWidget(_muted("Sign in with the account you created for this store."))
        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Password")
        self.error = _muted("")
        self.error.setStyleSheet("color:#9B2C2C;")
        go = QPushButton("Sign in")
        go.clicked.connect(self.submit)
        self.password.returnPressed.connect(self.submit)
        layout.addSpacing(12)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(self.error)
        layout.addWidget(go)
        wrap.addWidget(card)

    def submit(self) -> None:
        try:
            user = self.store.login(self.username.text(), self.password.text())
        except ValueError as exc:
            self.error.setText(str(exc))
            return
        self.on_done(user)


class ProductDialog(QDialog):
    def __init__(self, parent: QWidget, store: Store, product: dict | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.product = product
        self.image_path = product["image_path"] if product else ""
        self.setWindowTitle("Product" if product else "Add product")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit(product["name"] if product else "")
        self.sku = QLineEdit(product["sku"] if product else "")
        self.sku.setPlaceholderText("Leave blank to assign automatically")
        self.subtitle = QLineEdit(product["subtitle"] if product else "")
        self.category = QComboBox()
        self.category.addItems(CATEGORIES)
        if product:
            self.category.setCurrentText(product["category"])
        self.unit = QComboBox()
        self.unit.addItems(UNITS)
        if product:
            self.unit.setCurrentText(product["unit"])
        self.price = QLineEdit("" if not product else f"{product['price_cents'] / 100:.2f}")
        self.cost = QLineEdit("" if not product else f"{product['cost_cents'] / 100:.2f}")
        self.stock = QSpinBox()
        self.stock.setMaximum(1_000_000)
        self.stock.setValue(product["stock"] if product else 0)
        self.reorder = QSpinBox()
        self.reorder.setMaximum(1_000_000)
        self.reorder.setValue(product["reorder_at"] if product else 0)
        self.photo = QLabel("No photo")
        pick = QPushButton("Add photo")
        pick.setObjectName("Ghost")
        pick.clicked.connect(self.pick_photo)
        form.addRow("Name", self.name)
        form.addRow("SKU", self.sku)
        form.addRow("Details", self.subtitle)
        form.addRow("Category", self.category)
        form.addRow("Unit", self.unit)
        form.addRow("Selling price", self.price)
        form.addRow("Buying cost", self.cost)
        form.addRow("Stock", self.stock)
        form.addRow("Reorder at", self.reorder)
        form.addRow("Photo", self.photo)
        layout.addLayout(form)
        layout.addWidget(pick)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh_photo()

    def pick_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Product photo", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.image_path = path
            self._refresh_photo()

    def _refresh_photo(self) -> None:
        if self.image_path and Path(self.image_path).exists():
            pix = QPixmap(self.image_path).scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.photo.setPixmap(pix)
        else:
            self.photo.setText("No photo")

    def payload(self) -> dict:
        return {
            "name": self.name.text(),
            "sku": self.sku.text(),
            "subtitle": self.subtitle.text(),
            "category": self.category.currentText(),
            "unit": self.unit.currentText(),
            "price_cents": parse_amount(self.price.text()),
            "cost_cents": parse_amount(self.cost.text()),
            "stock": self.stock.value(),
            "reorder_at": self.reorder.value(),
            "active": True,
            "image_path": self.image_path,
        }


class MainWindow(QMainWindow):
    def __init__(self, store: Store, user: dict) -> None:
        super().__init__()
        self.store = store
        self.user = user
        self.cart: list[dict] = []
        self.lan: LanServer | None = None
        try:
            self.lan = LanServer(store.path)
            self.lan.start()
        except OSError:
            self.lan = None
        shop = store.shop()
        self.setWindowTitle(f"{shop['name']} — {APP_NAME}")
        self.resize(1280, 800)
        shell = QWidget()
        self.setCentralWidget(shell)
        layout = QHBoxLayout(shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(232)
        nav = QVBoxLayout(side)
        nav.setContentsMargins(16, 24, 16, 16)
        brand = QLabel(shop["name"])
        brand.setObjectName("Brand")
        brand.setWordWrap(True)
        who = QLabel(f"{user['full_name']}\n{user['role']}")
        who.setObjectName("BrandSub")
        nav.addWidget(brand)
        nav.addWidget(who)
        nav.addSpacing(18)
        self.stack = QStackedWidget()
        self.buttons: list[QPushButton] = []
        pages = [
            ("Home", self._home),
            ("Till", self._till),
            ("Products", self._catalog),
            ("Stock", self._stock),
            ("Orders", self._orders),
            ("Performance", self._performance),
            ("Company", self._company),
        ]
        if user["role"] == "owner":
            pages.append(("Staff", self._staff))
        for i, (label, factory) in enumerate(pages):
            page = factory()
            self.stack.addWidget(page)
            btn = QPushButton(label)
            btn.setObjectName("Nav")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, index=i: self._go(index))
            self.buttons.append(btn)
            nav.addWidget(btn)
        nav.addStretch()
        out = QPushButton("Sign out")
        out.setObjectName("Nav")
        out.clicked.connect(self.sign_out)
        nav.addWidget(out)
        layout.addWidget(side)
        layout.addWidget(self.stack, 1)
        self._go(0)

    def _go(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == index)
        page = self.stack.currentWidget()
        if hasattr(page, "reload"):
            page.reload()

    def sign_out(self) -> None:
        self.close()
        start(self.store)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.lan:
            self.lan.stop()
            self.lan = None
        super().closeEvent(event)

    def _wrap(self, widget: QWidget) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        return scroll

    def _home(self) -> QWidget:
        page = QWidget()
        page.reload = lambda: self._fill_home(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        page._layout = layout
        return self._wrap(page)

    def _fill_home(self, page: QWidget) -> None:
        layout: QVBoxLayout = page._layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        shop = self.store.shop()
        stats = self.store.performance()
        layout.addWidget(_muted(shop["city"] or "This computer"))
        layout.addWidget(_title(shop["name"]))
        layout.addWidget(_muted("This computer is the shop. Phones on the same Wi‑Fi open the address below, then sign in with the account you created."))
        port = self.lan.port if self.lan else 8080
        layout.addWidget(_stat("This computer", local_url(port), "Opens on this PC"))
        phones = lan_urls(port)
        layout.addWidget(
            _stat(
                "Phones on this Wi‑Fi",
                phones[0] if phones else "Connect Wi‑Fi",
                "Allow Desktop Store on private networks if Windows asks",
            )
        )
        grid = QGridLayout()
        grid.addWidget(_stat("Today", naira(stats["today_sales"]), f"{stats['today_count']} sales"), 0, 0)
        grid.addWidget(_stat("Gross profit", naira(stats["profit"]), "Sales minus buying cost"), 0, 1)
        grid.addWidget(_stat("Stock at cost", naira(stats["stock_cost"]), f"{stats['stock_units']} units"), 0, 2)
        grid.addWidget(_stat("Low stock", str(len(stats["low"])), "Need to restock"), 0, 3)
        layout.addLayout(grid)
        if not self.store.products():
            empty = _card()
            box = QVBoxLayout(empty)
            box.addWidget(_title("No products yet"))
            box.addWidget(_muted("Add the first item with selling price and buying cost. Performance stays at zero until you record a sale."))
            add = QPushButton("Add a product")
            add.clicked.connect(lambda: self._go(2))
            box.addWidget(add, alignment=Qt.AlignLeft)
            layout.addWidget(empty)
        layout.addStretch()

    def _till(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(_title("Till"))
        layout.addWidget(_muted("Record what a customer buys in the store. Stock falls when the sale is saved."))
        row = QHBoxLayout()
        self.scan = QLineEdit()
        self.scan.setPlaceholderText("Name or SKU")
        self.scan.returnPressed.connect(self._add_scanned)
        add = QPushButton("Add")
        add.clicked.connect(self._add_scanned)
        row.addWidget(self.scan, 1)
        row.addWidget(add)
        layout.addLayout(row)
        self.cart_table = QTableWidget(0, 5)
        self.cart_table.setHorizontalHeaderLabels(["Item", "Qty", "Price", "Cost", ""])
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.cart_table, 1)
        pay_row = QHBoxLayout()
        self.pay = QComboBox()
        self.pay.addItems(PAY_METHODS)
        self.total_label = QLabel("Total ₦0.00")
        self.total_label.setObjectName("StatValue")
        sell = QPushButton("Complete sale")
        sell.clicked.connect(self._complete_sale)
        pay_row.addWidget(QLabel("Pay by"))
        pay_row.addWidget(self.pay)
        pay_row.addStretch()
        pay_row.addWidget(self.total_label)
        pay_row.addWidget(sell)
        layout.addLayout(pay_row)
        page.reload = self._render_cart
        return page

    def _add_scanned(self) -> None:
        query = self.scan.text().strip()
        if not query:
            return
        product = self.store.find_product(query)
        if not product:
            warn(self, "No matching product. Add it under Products first.")
            return
        for line in self.cart:
            if line["product_id"] == product["id"]:
                line["qty"] += 1
                self.scan.clear()
                self._render_cart()
                return
        self.cart.append({"product_id": product["id"], "qty": 1})
        self.scan.clear()
        self._render_cart()

    def _render_cart(self) -> None:
        self.cart_table.setRowCount(0)
        total = 0
        for i, line in enumerate(list(self.cart)):
            product = self.store.product(line["product_id"])
            total += product["price_cents"] * line["qty"]
            self.cart_table.insertRow(i)
            self.cart_table.setItem(i, 0, QTableWidgetItem(product["name"]))
            self.cart_table.setItem(i, 1, QTableWidgetItem(str(line["qty"])))
            self.cart_table.setItem(i, 2, QTableWidgetItem(naira(product["price_cents"])))
            self.cart_table.setItem(i, 3, QTableWidgetItem(naira(product["cost_cents"])))
            remove = QPushButton("Remove")
            remove.setObjectName("Ghost")
            remove.clicked.connect(lambda _=False, index=i: self._remove_line(index))
            self.cart_table.setCellWidget(i, 4, remove)
        self.total_label.setText(f"Total {naira(total)}")

    def _remove_line(self, index: int) -> None:
        if 0 <= index < len(self.cart):
            self.cart.pop(index)
            self._render_cart()

    def _complete_sale(self) -> None:
        if not self.cart:
            warn(self, "Add items first.")
            return
        try:
            order = self.store.checkout(self.user["id"], self.cart, self.pay.currentText())
        except ValueError as exc:
            warn(self, str(exc))
            return
        self.cart = []
        self._render_cart()
        info(self, f"Sale {order['number']} saved.\nTotal {naira(order['total_cents'])}\nProfit {naira(order['profit_cents'])}")

    def _catalog(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        head = QHBoxLayout()
        col = QVBoxLayout()
        col.addWidget(_title("Products"))
        col.addWidget(_muted("Every product needs a selling price and the cost of buying it."))
        head.addLayout(col, 1)
        add = QPushButton("Add product")
        add.clicked.connect(lambda: self._edit_product(None))
        head.addWidget(add, alignment=Qt.AlignTop)
        layout.addLayout(head)
        self.product_table = QTableWidget(0, 6)
        self.product_table.setHorizontalHeaderLabels(["Name", "SKU", "Price", "Buying cost", "Stock", ""])
        self.product_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.product_table, 1)
        page.reload = self._fill_catalog
        return page

    def _fill_catalog(self) -> None:
        products = self.store.products()
        self.product_table.setRowCount(0)
        for i, product in enumerate(products):
            self.product_table.insertRow(i)
            self.product_table.setItem(i, 0, QTableWidgetItem(product["name"]))
            self.product_table.setItem(i, 1, QTableWidgetItem(product["sku"]))
            self.product_table.setItem(i, 2, QTableWidgetItem(naira(product["price_cents"])))
            self.product_table.setItem(i, 3, QTableWidgetItem(naira(product["cost_cents"])))
            self.product_table.setItem(i, 4, QTableWidgetItem(str(product["stock"])))
            edit = QPushButton("Edit")
            edit.setObjectName("Ghost")
            edit.clicked.connect(lambda _=False, p=product: self._edit_product(p))
            self.product_table.setCellWidget(i, 5, edit)

    def _edit_product(self, product: dict | None) -> None:
        dialog = ProductDialog(self, self.store, product)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            saved = self.store.save_product(dialog.payload(), product["id"] if product else None)
            src = dialog.image_path
            if src and Path(src).exists() and Path(src).parent != images_dir():
                dest = images_dir() / f"{saved['id']}{Path(src).suffix.lower() or '.jpg'}"
                shutil.copy2(src, dest)
                self.store.save_product({**saved, "image_path": str(dest)}, saved["id"])
        except ValueError as exc:
            warn(self, str(exc))
            return
        self._fill_catalog()

    def _stock(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(_title("Stock"))
        layout.addWidget(_muted("Adjust what is on the shelf. Low stock is highlighted."))
        self.stock_table = QTableWidget(0, 5)
        self.stock_table.setHorizontalHeaderLabels(["Name", "On hand", "Reorder at", "Value at cost", ""])
        self.stock_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.stock_table, 1)
        page.reload = self._fill_stock
        return page

    def _fill_stock(self) -> None:
        self.stock_table.setRowCount(0)
        for i, product in enumerate(self.store.products(active_only=True)):
            self.stock_table.insertRow(i)
            name = QTableWidgetItem(product["name"])
            if product["stock"] <= product["reorder_at"]:
                name.setForeground(Qt.red)
            self.stock_table.setItem(i, 0, name)
            self.stock_table.setItem(i, 1, QTableWidgetItem(str(product["stock"])))
            self.stock_table.setItem(i, 2, QTableWidgetItem(str(product["reorder_at"])))
            self.stock_table.setItem(i, 3, QTableWidgetItem(naira(product["stock"] * product["cost_cents"])))
            btn = QPushButton("Add stock")
            btn.setObjectName("Ghost")
            btn.clicked.connect(lambda _=False, p=product: self._add_stock(p))
            self.stock_table.setCellWidget(i, 4, btn)

    def _add_stock(self, product: dict) -> None:
        qty, ok = _ask_int(self, f"How many {product['name']} arrived?", 1)
        if not ok:
            return
        try:
            self.store.adjust_stock(product["id"], qty)
        except ValueError as exc:
            warn(self, str(exc))
            return
        self._fill_stock()

    def _orders(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(_title("Orders"))
        layout.addWidget(_muted("Only sales recorded at this till."))
        self.order_table = QTableWidget(0, 6)
        self.order_table.setHorizontalHeaderLabels(["Ticket", "When", "Cashier", "Paid", "Total", "Profit"])
        self.order_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.order_table, 1)
        page.reload = self._fill_orders
        return page

    def _fill_orders(self) -> None:
        self.order_table.setRowCount(0)
        for i, order in enumerate(self.store.orders()):
            full = self.store.order(order["id"])
            self.order_table.insertRow(i)
            self.order_table.setItem(i, 0, QTableWidgetItem(full["number"]))
            self.order_table.setItem(i, 1, QTableWidgetItem(str(full["created_at"]).replace("T", " ")[:16]))
            self.order_table.setItem(i, 2, QTableWidgetItem(full["cashier"]))
            self.order_table.setItem(i, 3, QTableWidgetItem(full["pay_method"]))
            self.order_table.setItem(i, 4, QTableWidgetItem(naira(full["total_cents"])))
            self.order_table.setItem(i, 5, QTableWidgetItem(naira(full["profit_cents"])))

    def _performance(self) -> QWidget:
        page = QWidget()
        page.reload = lambda: self._fill_performance(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        page._layout = layout
        return self._wrap(page)

    def _fill_performance(self, page: QWidget) -> None:
        layout: QVBoxLayout = page._layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        stats = self.store.performance()
        layout.addWidget(_title("Performance"))
        layout.addWidget(_muted("Profit is selling price minus buying cost. Stock value is what you paid for what is still on the shelf."))
        grid = QGridLayout()
        grid.addWidget(_stat("Sales", naira(stats["sales"]), f"{stats['count']} recorded"), 0, 0)
        grid.addWidget(_stat("Cost of stock sold", naira(stats["cost"]), "Buying cost of what left the shop"), 0, 1)
        grid.addWidget(_stat("Gross profit", naira(stats["profit"]), f"Today {naira(stats['today_profit'])}"), 0, 2)
        margin = 0 if stats["sales"] == 0 else round(stats["profit"] / stats["sales"] * 100, 1)
        grid.addWidget(_stat("Margin", f"{margin}%", ""), 0, 3)
        grid.addWidget(_stat("Stock on hand at cost", naira(stats["stock_cost"]), f"{stats['stock_units']} units"), 1, 0)
        grid.addWidget(_stat("Stock on hand at price", naira(stats["stock_retail"]), "If everything sold today"), 1, 1)
        layout.addLayout(grid)
        days = QTableWidget(len(stats["days"]), 4)
        days.setHorizontalHeaderLabels(["Day", "Sales", "Cost", "Profit"])
        days.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for i, row in enumerate(stats["days"]):
            days.setItem(i, 0, QTableWidgetItem(row["day"]))
            days.setItem(i, 1, QTableWidgetItem(naira(row["sales"])))
            days.setItem(i, 2, QTableWidgetItem(naira(row["cost"])))
            days.setItem(i, 3, QTableWidgetItem(naira(row["profit"])))
        days.setMaximumHeight(280)
        layout.addWidget(_muted("Last seven days"))
        layout.addWidget(days)
        rank = QTableWidget(max(len(stats["ranking"]), 1), 4)
        rank.setHorizontalHeaderLabels(["Product", "Qty", "Sales", "Profit"])
        rank.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        if not stats["ranking"]:
            rank.setItem(0, 0, QTableWidgetItem("No sales yet"))
        else:
            for i, row in enumerate(stats["ranking"]):
                rank.setItem(i, 0, QTableWidgetItem(row["name"]))
                rank.setItem(i, 1, QTableWidgetItem(str(row["qty"])))
                rank.setItem(i, 2, QTableWidgetItem(naira(row["sales"])))
                rank.setItem(i, 3, QTableWidgetItem(naira(row["profit"])))
        layout.addWidget(_muted("Products by profit"))
        layout.addWidget(rank)
        layout.addStretch()

    def _company(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(_title("Company"))
        layout.addWidget(_muted("Name and address appear on this computer only."))
        shop = self.store.shop()
        form = QFormLayout()
        self.company_fields = {}
        for key, label in [
            ("name", "Store name"),
            ("tagline", "Tagline"),
            ("street", "Street"),
            ("city", "City"),
            ("phone", "Phone"),
            ("hours", "Hours"),
            ("ticket_prefix", "Ticket prefix"),
        ]:
            field = QLineEdit(str(shop.get(key) or ""))
            self.company_fields[key] = field
            form.addRow(label, field)
        layout.addLayout(form)
        save = QPushButton("Save company")
        save.clicked.connect(self._save_company)
        layout.addWidget(save, alignment=Qt.AlignLeft)
        layout.addWidget(_muted(f"Database folder: {app_data_dir()}"))
        layout.addSpacing(16)
        layout.addWidget(_title("Your password"))
        pw = QFormLayout()
        self.pw_current = QLineEdit()
        self.pw_current.setEchoMode(QLineEdit.Password)
        self.pw_new = QLineEdit()
        self.pw_new.setEchoMode(QLineEdit.Password)
        pw.addRow("Current password", self.pw_current)
        pw.addRow("New password", self.pw_new)
        layout.addLayout(pw)
        change = QPushButton("Change password")
        change.setObjectName("Ghost")
        change.clicked.connect(self._change_password)
        layout.addWidget(change, alignment=Qt.AlignLeft)
        layout.addStretch()
        page.reload = lambda: None
        return page

    def _save_company(self) -> None:
        try:
            self.store.save_shop(**{k: v.text() for k, v in self.company_fields.items()})
        except ValueError as exc:
            warn(self, str(exc))
            return
        info(self, "Company saved.")
        self.setWindowTitle(f"{self.store.shop()['name']} — {APP_NAME}")

    def _change_password(self) -> None:
        try:
            self.store.change_password(self.user["id"], self.pw_current.text(), self.pw_new.text())
        except ValueError as exc:
            warn(self, str(exc))
            return
        self.pw_current.clear()
        self.pw_new.clear()
        info(self, "Password changed.")

    def _staff(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(_title("Staff"))
        layout.addWidget(_muted("Add people who can use this computer. Each person chooses their own username and password. There is no demo account."))
        form = QHBoxLayout()
        self.staff_name = QLineEdit()
        self.staff_name.setPlaceholderText("Full name")
        self.staff_user = QLineEdit()
        self.staff_user.setPlaceholderText("Username")
        self.staff_pass = QLineEdit()
        self.staff_pass.setEchoMode(QLineEdit.Password)
        self.staff_pass.setPlaceholderText("Password")
        add = QPushButton("Add staff")
        add.clicked.connect(self._add_staff)
        form.addWidget(self.staff_name)
        form.addWidget(self.staff_user)
        form.addWidget(self.staff_pass)
        form.addWidget(add)
        layout.addLayout(form)
        self.staff_table = QTableWidget(0, 4)
        self.staff_table.setHorizontalHeaderLabels(["Name", "Username", "Role", "Status"])
        self.staff_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.staff_table, 1)
        page.reload = self._fill_staff
        return page

    def _fill_staff(self) -> None:
        self.staff_table.setRowCount(0)
        for i, user in enumerate(self.store.users()):
            self.staff_table.insertRow(i)
            self.staff_table.setItem(i, 0, QTableWidgetItem(user["full_name"]))
            self.staff_table.setItem(i, 1, QTableWidgetItem(user["username"]))
            self.staff_table.setItem(i, 2, QTableWidgetItem(user["role"]))
            self.staff_table.setItem(i, 3, QTableWidgetItem("Active" if user["active"] else "Off"))

    def _add_staff(self) -> None:
        try:
            self.store.add_staff(self.staff_name.text(), self.staff_user.text(), self.staff_pass.text())
        except ValueError as exc:
            warn(self, str(exc))
            return
        self.staff_name.clear()
        self.staff_user.clear()
        self.staff_pass.clear()
        self._fill_staff()


def _ask_int(parent: QWidget, label: str, default: int = 1) -> tuple[int, bool]:
    dialog = QDialog(parent)
    dialog.setWindowTitle(APP_NAME)
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel(label))
    spin = QSpinBox()
    spin.setRange(-1_000_000, 1_000_000)
    spin.setValue(default)
    layout.addWidget(spin)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    if dialog.exec() != QDialog.Accepted:
        return 0, False
    return spin.value(), True


def start(store: Store | None = None) -> None:
    store = store or Store()
    host = QWidget()
    host.setWindowTitle(APP_NAME)
    stack = QStackedWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(stack)

    def opened(user: dict) -> None:
        host.hide()
        window = MainWindow(store, user)
        window.show()
        host._window = window

    if store.registered():
        stack.addWidget(LoginPage(store, opened))
    else:
        stack.addWidget(RegisterPage(store, opened))
    host.resize(980, 640)
    host.show()
    app = QApplication.instance()
    holders = getattr(app, "_holders", [])
    holders.append(host)
    app._holders = holders


def run() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(QSS)
    start()
    raise SystemExit(app.exec())
