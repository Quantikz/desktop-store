QSS = """
QWidget {
    background: #F4EFE6;
    color: #1C1917;
    font-family: "Segoe UI", "Outfit", "Helvetica Neue", sans-serif;
    font-size: 14px;
}
QMainWindow, QDialog {
    background: #F4EFE6;
}
QFrame#Card, QFrame#Sidebar, QFrame#TopBar {
    background: #FFFBF5;
    border: 1px solid #E6DFD2;
    border-radius: 14px;
}
QFrame#Sidebar {
    border-radius: 0;
    border: none;
    border-right: 1px solid #E6DFD2;
    background: #2F4A3C;
}
QLabel#Brand {
    color: #F4EFE6;
    font-size: 20px;
    font-weight: 600;
    letter-spacing: -0.4px;
}
QLabel#Muted, QLabel#Hint {
    color: #6B645C;
}
QLabel#BrandSub {
    color: #C9D5CC;
    font-size: 12px;
}
QLabel#Title {
    font-size: 28px;
    font-weight: 600;
    letter-spacing: -0.6px;
}
QLabel#StatValue {
    font-size: 22px;
    font-weight: 600;
}
QPushButton {
    background: #2F4A3C;
    color: #F4EFE6;
    border: none;
    border-radius: 10px;
    padding: 10px 16px;
    font-weight: 600;
}
QPushButton:hover { background: #3B5C4B; }
QPushButton:disabled { background: #C9C2B5; color: #7A746C; }
QPushButton#Ghost, QPushButton#Nav {
    background: transparent;
    color: #D7E2DA;
    text-align: left;
    padding: 10px 14px;
    border-radius: 10px;
    font-weight: 500;
}
QPushButton#Nav:hover { background: rgba(255,255,255,0.08); }
QPushButton#Nav:checked {
    background: #F4EFE6;
    color: #2F4A3C;
}
QPushButton#Ghost {
    color: #2F4A3C;
    border: 1px solid #D7CFC0;
    background: #FFFBF5;
}
QPushButton#Danger {
    background: #9B2C2C;
    color: white;
}
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #FFFBF5;
    border: 1px solid #D7CFC0;
    border-radius: 10px;
    padding: 9px 12px;
    selection-background-color: #2F4A3C;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #2F4A3C;
}
QTableWidget {
    background: #FFFBF5;
    border: 1px solid #E6DFD2;
    border-radius: 12px;
    gridline-color: #EFE8DC;
    selection-background-color: #E4EDE6;
    selection-color: #1C1917;
}
QHeaderView::section {
    background: #F7F1E8;
    border: none;
    border-bottom: 1px solid #E6DFD2;
    padding: 8px;
    font-weight: 600;
}
QScrollArea { border: none; }
"""
