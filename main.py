import json
import sys
from pathlib import Path

from platformdirs import user_config_dir
from rapidfuzz import fuzz

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "PhysicalConstants"
APP_AUTHOR = "YourName"


def app_dir() -> Path:
    return Path(__file__).resolve().parent


def constants_path() -> Path:
    return app_dir() / "constants.json"


def get_config_path() -> Path:
    config_dir = Path(user_config_dir(APP_NAME, APP_AUTHOR))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "settings.json"


def load_constants() -> list[dict]:
    path = constants_path()
    return json.loads(path.read_text(encoding="utf-8"))


def load_settings() -> dict:
    path = get_config_path()

    if not path.exists():
        return {"favorites": []}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"favorites": []}


def save_settings(settings: dict) -> None:
    path = get_config_path()
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def searchable_text(c: dict) -> str:
    aliases = " ".join(c.get("aliases", []))
    return f"{c.get('name', '')} {c.get('symbol', '')} {c.get('category', '')} {aliases}"


def search_constants(query: str, constants: list[dict], favorites: set[str]) -> list[dict]:
    query = query.strip().lower()

    if not query:
        return sorted(
            constants,
            key=lambda c: (c["id"] not in favorites, c["name"].lower()),
        )

    scored = []

    for c in constants:
        text = searchable_text(c).lower()
        score = fuzz.partial_ratio(query, text)

        if c.get("symbol", "").lower() == query:
            score += 40

        if c.get("name", "").lower().startswith(query):
            score += 20

        if c["id"] in favorites:
            score += 5

        if score >= 45:
            scored.append((score, c))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [c for _, c in scored]


def format_constant_for_copy(c: dict) -> str:
    return f"{c['value']} {c['unit']}"


class ConstantsWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings = load_settings()
        self.favorites = set(self.settings.get("favorites", []))
        self.constants = load_constants()
        self.current_results = []

        self.setWindowTitle("Physical Constants")
        self.resize(540, 460)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search constants... e.g. planck, c, boltzmann")
        self.search_box.textChanged.connect(self.refresh_results)
        self.search_box.returnPressed.connect(self.copy_selected)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(lambda _: self.copy_selected())

        self.copy_button = QPushButton("Copy")
        self.copy_button.clicked.connect(self.copy_selected)

        self.favorite_button = QPushButton("★ Toggle Favorite")
        self.favorite_button.clicked.connect(self.toggle_selected_favorite)

        button_row = QHBoxLayout()
        button_row.addWidget(self.copy_button)
        button_row.addWidget(self.favorite_button)

        hint = QLabel("Enter/double-click: copy value + unit. Favorites appear first.")
        hint.setStyleSheet("color: gray;")

        root = QVBoxLayout()
        root.addWidget(self.search_box)
        root.addWidget(self.list_widget)
        root.addLayout(button_row)
        root.addWidget(hint)

        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)

        self.refresh_results()

    def show_and_focus(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.search_box.setFocus()
        self.search_box.selectAll()

    def refresh_results(self):
        query = self.search_box.text()
        self.current_results = search_constants(query, self.constants, self.favorites)

        self.list_widget.clear()

        for c in self.current_results:
            item = QListWidgetItem()
            star = "★" if c["id"] in self.favorites else "☆"
            symbol = c.get("symbol", "")
            value = c.get("value", "")
            unit = c.get("unit", "")

            item.setText(f"{star}  {symbol} — {c['name']}\n     {value} {unit}")
            item.setData(Qt.UserRole, c["id"])
            item.setSizeHint(QSize(100, 48))
            self.list_widget.addItem(item)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def get_selected_constant(self):
        item = self.list_widget.currentItem()

        if item is None:
            return None

        constant_id = item.data(Qt.UserRole)
        return next((c for c in self.constants if c["id"] == constant_id), None)

    def copy_selected(self):
        c = self.get_selected_constant()

        if c is None:
            return

        text = format_constant_for_copy(c)
        QApplication.clipboard().setText(text)

        self.hide()

    def toggle_selected_favorite(self):
        c = self.get_selected_constant()

        if c is None:
            return

        constant_id = c["id"]

        if constant_id in self.favorites:
            self.favorites.remove(constant_id)
        else:
            self.favorites.add(constant_id)

        self.settings["favorites"] = sorted(self.favorites)
        save_settings(self.settings)

        self.refresh_results()


class TrayApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.window = ConstantsWindow()

        self.tray = QSystemTrayIcon()
        self.tray.setToolTip("Physical Constants")

        icon = self.app.style().standardIcon(QApplication.style().StandardPixmap.SP_ComputerIcon)
        self.tray.setIcon(icon)

        menu = QMenu()

        show_action = QAction("Show Constants")
        show_action.triggered.connect(self.window.show_and_focus)
        menu.addAction(show_action)

        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

        self.window.show_and_focus()

    def on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            if self.window.isVisible():
                self.window.hide()
            else:
                self.window.show_and_focus()

    def quit(self):
        self.tray.hide()
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    TrayApp().run()