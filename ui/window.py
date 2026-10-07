import sys
import os
import json
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics, QMouseEvent
from PySide6.QtWidgets import (
    QWidget, QApplication, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QMenu,
    QInputDialog, QMessageBox
)
from core.launcher import launch_target
from core.shell_resolver import resolve_shell_item, clean_icon

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'categories.json')
SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'settings.json')

def save_config(categories_data):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump({"categories": categories_data}, f, indent=2, ensure_ascii=False)
        print("Config updated successfully via Drag & Drop.")
    except Exception as e:
        print(f"Error saving config: {e}")

# نمط القوائم المنبثقة الداكنة (زجاجي) — مشترك بين كل القوائم
DARK_MENU_STYLE = """
    QMenu {
        background-color: rgba(30, 30, 32, 245);
        border: 1px solid rgba(80, 80, 85, 200);
        border-radius: 8px;
        padding: 4px;
    }
    QMenu::item {
        color: #f0f0f0;
        padding: 6px 20px;
        border-radius: 5px;
    }
    QMenu::item:selected {
        background-color: rgba(90, 90, 100, 255);
        color: #ffffff;
    }
    QMenu::separator {
        height: 1px;
        background: rgba(80, 80, 85, 180);
        margin: 4px 12px;
    }
"""

class CategoryBubble(QPushButton):
    def __init__(self, category_data, on_click_callback, on_drop_callback, on_context_callback, parent=None):
        super().__init__(parent)
        self.category_data = category_data
        self.on_click_callback = on_click_callback
        self.on_drop_callback = on_drop_callback
        self.on_context_callback = on_context_callback
        
        self.setFixedSize(54, 54)
        self.setCursor(Qt.PointingHandCursor)
        self.setText(category_data.get('icon', '📁'))
        self.setToolTip(category_data.get('name', 'Category'))
        
        font = QFont("Segoe UI Emoji", 18)
        self.setFont(font)
        self.setAcceptDrops(True)
        
        self.default_style = """
            QPushButton {
                background-color: rgba(45, 45, 48, 220);
                color: #ffffff;
                border: 1px solid rgba(80, 80, 80, 180);
                border-radius: 27px;
            }
            QPushButton:hover {
                background-color: rgba(70, 70, 75, 240);
                border: 1px solid rgba(120, 120, 130, 255);
            }
        """
        self.highlight_style = """
            QPushButton {
                background-color: rgba(50, 90, 150, 240);
                color: #ffffff;
                border: 2px solid #58a6ff;
                border-radius: 27px;
            }
        """
        self.setStyleSheet(self.default_style)
        self.clicked.connect(lambda: self.on_click_callback(self, self.category_data))
        # قائمة يمين خاصة بالفئة
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda pos: self.on_context_callback(pos, self, self.category_data)
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self.highlight_style)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.default_style)
        event.accept()

    def dropEvent(self, event):
        self.setStyleSheet(self.default_style)
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path:
                    # حل شامل عبر Windows Shell: الاسم + أمر التشغيل
                    info = resolve_shell_item(file_path)
                    clean_name = info.name if info and info.name else "New Item"
                    
                    new_item = {
                        "name": clean_name,
                        "command": info.command if info else file_path
                    }
                    self.on_drop_callback(self, self.category_data, new_item)
            event.acceptProposedAction()
        else:
            event.ignore()

class DrawerItemButton(QPushButton):
    """A single row inside the drawer: native system icon + application name."""

    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.command = item_data.get('command', '')

        # استخراج الأيقونة الأصلية النظيفة (.exe / .lnk / UWP / ملف)
        icon = clean_icon(self.command)

        self.setFixedHeight(42)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        # صف أفقي: أيقونة + نص (محاذاة مرتبة)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 5, 14, 5)
        row.setSpacing(12)

        icon_label = QLabel(self)
        icon_label.setFixedSize(28, 28)
        icon_label.setAlignment(Qt.AlignCenter)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(QSize(28, 28)))
        row.addWidget(icon_label)

        text_label = QLabel(item_data.get('name', 'App'), self)
        text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        row.addWidget(text_label, 1)

        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(35, 35, 38, 230);
                border: 1px solid rgba(70, 70, 75, 180);
                border-radius: 8px;
                padding: 4px 6px;
            }
            QPushButton:hover {
                background-color: rgba(55, 55, 60, 255);
                border-color: rgba(100, 100, 110, 255);
            }
            QLabel {
                background: transparent;
                color: #f0f0f0;
                font-size: 13px;
            }
            QPushButton:hover QLabel {
                color: #ffffff;
            }
        """)

class Drawer(QWidget):
    def __init__(self, on_remove_callback, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.current_cat_name = None
        self.current_bubble = None
        self.current_category_data = None
        self.on_remove_callback = on_remove_callback
        
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(8)
        self.setLayout(self.layout)
        self.hide()

    def _fit_width(self, category_data):
        """Compute a comfortable width that fits the longest item name."""
        names = [item.get('name', '') for item in category_data.get('items', [])]
        names.append(category_data.get('name', ''))
        font = QFont()
        font.setPixelSize(13)
        metrics = QFontMetrics(font)
        longest = max((metrics.horizontalAdvance(name) for name in names), default=0)
        # icon + spacing + text + drawer margins + button padding + borders + breathing room
        width = 28 + 12 + longest + (12 * 2) + (14 * 2) + (2 * 2) + 28
        return max(220, min(width, 420))

    def show_category(self, bubble_widget, category_data):
        cat_name = category_data.get('name', '')
        
        if self.isVisible() and self.current_cat_name == cat_name:
            self.hide()
            self.current_cat_name = None
            self.current_bubble = None
            self.current_category_data = None
            return

        self.current_cat_name = cat_name
        self.current_bubble = bubble_widget
        self.current_category_data = category_data
        # ضبط العرض ديناميكياً لاستيعاب أطول اسم دون اقتطاع
        self.setMinimumWidth(self._fit_width(category_data))
        self.render_items(category_data)
        self.adjustSize()

        geo = bubble_widget.mapToGlobal(QPoint(0, 0))
        self.move(geo.x(), geo.y() + bubble_widget.height() + 10)
        self.show()

    def render_items(self, category_data):
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        cat_name = category_data.get('name', '')
        title_label = QLabel(cat_name)
        title_label.setStyleSheet("color: #aaaaaa; font-size: 11px; font-weight: bold; padding-left: 4px;")
        self.layout.addWidget(title_label)

        items = category_data.get('items', [])
        for item in items:
            # زر مزوّد بالأيقونة الأصلية للنظام + اسم التطبيق
            btn = DrawerItemButton(item)
            btn.clicked.connect(lambda checked=False, target=btn.command: self.launch_and_close(target))
            # قائمة يمين (Context Menu) لحذف العنصر
            btn.customContextMenuRequested.connect(lambda pos, item_data=item: self.show_item_menu(pos, item_data))
            self.layout.addWidget(btn)

    def show_item_menu(self, pos, item_data):
        # قائمة منبثقة داكنة أنيقة
        menu = QMenu(self)
        menu.setStyleSheet(DARK_MENU_STYLE)
        remove_action = menu.addAction("Remove")
        action = menu.exec_(self.mapToGlobal(pos))
        if action == remove_action and self.current_category_data is not None:
            self.on_remove_callback(self.current_category_data, item_data)

    def refresh_if_open(self, category_data):
        if self.isVisible() and self.current_cat_name == category_data.get('name'):
            self.setMinimumWidth(self._fit_width(category_data))
            self.render_items(category_data)
            self.adjustSize()

    def launch_and_close(self, command):
        launch_target(command)
        self.hide()
        self.current_cat_name = None
        self.current_bubble = None
        self.current_category_data = None

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        brush = QBrush(QColor(24, 24, 26, 235))
        qp.setBrush(brush)
        qp.setPen(QPen(QColor(70, 70, 75, 180), 1))
        qp.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        qp.end()

class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.drawer = Drawer(self.on_item_remove)
        self.drag_position = None
        self.categories = []
        self.bubbles = []
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(10)

        self.load_categories()
        self.rebuild_bubbles()

        self.setLayout(self.main_layout)

        # قائمة يمين على سطح الـ Dock (المناطق الفارغة)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_dock_context_menu)
        # استعادة آخر موقع محفوظ (أو الافتراضي 120,120)
        pos_x, pos_y = self.load_position()
        self.setGeometry(pos_x, pos_y, self.sizeHint().width(), self.sizeHint().height())
        self.show()

    def load_categories(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    self.categories = data.get('categories', [])
            except Exception as e:
                print(f"Error loading JSON: {e}")

    def on_category_clicked(self, bubble_widget, category_data):
        self.drawer.show_category(bubble_widget, category_data)

    def on_item_dropped(self, bubble_widget, category_data, new_item):
        if 'items' not in category_data:
            category_data['items'] = []
        category_data['items'].append(new_item)
        print(f"Added '{new_item['name']}' to '{category_data['name']}'")
        
        # حفظ التعديل فورياً في JSON
        save_config(self.categories)
        
        # تحديث المنيو لو مفتوح في نفس اللحظة
        self.drawer.refresh_if_open(category_data)

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        brush = QBrush(QColor(20, 20, 22, 180))
        qp.setBrush(brush)
        qp.setPen(QPen(QColor(60, 60, 65, 140), 1))
        qp.drawRoundedRect(0, 0, self.width(), self.height(), 35, 35)
        qp.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            if self.drawer.isVisible():
                self.drawer.hide()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        # عند الانتهاء من سحب النافذة -> حفظ الموقع الجديد
        if event.button() == Qt.LeftButton and self.drag_position is not None:
            self.drag_position = None
            self.save_position()
            event.accept()

    def load_position(self):
        try:
            with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return int(data.get('x', 120)), int(data.get('y', 120))
        except Exception:
            return 120, 120

    def save_position(self):
        try:
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump({"x": self.x(), "y": self.y()}, f, indent=2)
        except Exception as e:
            print(f"Error saving position: {e}")

    def on_item_remove(self, category_data, item_data):
        items = category_data.get('items', [])
        if item_data in items:
            items.remove(item_data)
            print(f"Removed '{item_data.get('name')}' from '{category_data.get('name')}'")
        # حفظ فوري في JSON ثم تحديث المنيو إن كان مفتوحاً
        save_config(self.categories)
        self.drawer.refresh_if_open(category_data)

    # ---------- قائمة سطح الـ Dock (النافذة الرئيسية) ----------

    def show_dock_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(DARK_MENU_STYLE)
        add_action = menu.addAction("+ Add New Category")
        config_action = menu.addAction("Open Config Folder")
        menu.addSeparator()
        exit_action = menu.addAction("Exit Desktop Organizer")

        action = menu.exec_(self.mapToGlobal(pos))
        if action == add_action:
            self.add_category()
        elif action == config_action:
            self.open_config_folder()
        elif action == exit_action:
            QApplication.quit()

    def add_category(self):
        name, ok = QInputDialog.getText(self, "Add Category", "Category Name:")
        if not ok or not name.strip():
            return
        emoji, ok_emoji = QInputDialog.getText(self, "Add Category", "Icon / Emoji:", text="📁")
        if not ok_emoji:
            return
        new_category = {
            "name": name.strip(),
            "icon": emoji.strip() or "📁",
            "items": [],
        }
        self.categories.append(new_category)
        save_config(self.categories)
        self.rebuild_bubbles()

    def open_config_folder(self):
        config_dir = os.path.dirname(CONFIG_PATH)
        if os.path.isdir(config_dir):
            os.startfile(config_dir)

    # ---------- قائمة الفقاعات (الفئات) ----------

    def on_category_context(self, pos, bubble, category_data):
        menu = QMenu(self)
        menu.setStyleSheet(DARK_MENU_STYLE)
        edit_action = menu.addAction("Edit Category")
        delete_action = menu.addAction("Delete Category")

        action = menu.exec_(bubble.mapToGlobal(pos))
        if action == edit_action:
            self.edit_category(category_data)
        elif action == delete_action:
            self.delete_category(category_data)

    def edit_category(self, category_data):
        current_name = category_data.get('name', '')
        current_icon = category_data.get('icon', '📁')
        name, ok = QInputDialog.getText(
            self, "Edit Category", "Category Name:", text=current_name
        )
        if not ok or not name.strip():
            return
        emoji, ok_emoji = QInputDialog.getText(
            self, "Edit Category", "Icon / Emoji:", text=current_icon
        )
        if not ok_emoji:
            return
        category_data['name'] = name.strip()
        category_data['icon'] = emoji.strip() or current_icon

        # إغلاق القائمة إن كانت مفتوحة لهذه الفئة (تغيّر الاسم)
        if self.drawer.current_category_data is category_data:
            self.drawer.hide()
            self.drawer.current_cat_name = None
            self.drawer.current_bubble = None
            self.drawer.current_category_data = None

        save_config(self.categories)
        self.rebuild_bubbles()

    def delete_category(self, category_data):
        reply = QMessageBox.question(
            self,
            "Delete Category",
            f"Delete '{category_data.get('name', '')}' and all its items?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # إغلاق القائمة إن كانت مفتوحة لهذه الفئة
        if self.drawer.current_category_data is category_data:
            self.drawer.hide()
            self.drawer.current_cat_name = None
            self.drawer.current_bubble = None
            self.drawer.current_category_data = None

        self.categories.remove(category_data)
        save_config(self.categories)
        self.rebuild_bubbles()

    def rebuild_bubbles(self):
        """إعادة بناء كل فقاعات الفئات من self.categories."""
        for bubble in self.bubbles:
            self.main_layout.removeWidget(bubble)
            bubble.deleteLater()
        self.bubbles = []

        for cat in self.categories:
            bubble = CategoryBubble(
                cat,
                self.on_category_clicked,
                self.on_item_dropped,
                self.on_category_context,
                self,
            )
            self.bubbles.append(bubble)
            self.main_layout.addWidget(bubble)

        self.adjustSize()