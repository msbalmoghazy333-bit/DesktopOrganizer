import sys
import os
import json
from PySide6.QtCore import Qt, QPoint, QSize, QMimeData, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics, QMouseEvent, QDrag
from PySide6.QtWidgets import (
    QWidget, QApplication, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QMenu, QDialog
)
from core.launcher import launch_target
from core.shell_resolver import resolve_shell_item, clean_icon
from ui.dialogs import CategoryDialog, AboutDialog, SettingsDialog, ConfirmDialog

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
        self._drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_start_pos is not None:
            distance = (event.globalPosition().toPoint() - self._drag_start_pos).manhattanLength()
            if distance >= QApplication.startDragDistance():
                self._start_reorder_drag()
                return
        super().mouseMoveEvent(event)

    def _start_reorder_drag(self):
        self._drag_start_pos = None
        parent = self.parent()
        if parent is None or not hasattr(parent, 'categories'):
            return
        try:
            source_index = parent.categories.index(self.category_data)
        except ValueError:
            return
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData("application/x-category-bubble", str(source_index).encode())
        drag.setMimeData(mime_data)
        drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-category-bubble"):
            event.acceptProposedAction()
            self.setStyleSheet(self.highlight_style)
        elif event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self.highlight_style)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.default_style)
        event.accept()

    def dropEvent(self, event):
        self.setStyleSheet(self.default_style)
        if event.mimeData().hasFormat("application/x-category-bubble"):
            self._handle_reorder_drop(event)
        elif event.mimeData().hasUrls():
            self._handle_file_drop(event)
        else:
            event.ignore()

    def _handle_reorder_drop(self, event):
        parent = self.parent()
        if parent is None or not hasattr(parent, 'categories'):
            event.ignore()
            return
        try:
            source_index = int(event.mimeData().data("application/x-category-bubble").data().decode())
            target_index = parent.categories.index(self.category_data)
        except (ValueError, AttributeError):
            event.ignore()
            return
        if source_index != target_index:
            categories = parent.categories
            item = categories.pop(source_index)
            categories.insert(target_index, item)
            save_config(categories)
            parent.rebuild_bubbles()
        event.acceptProposedAction()

    def _handle_file_drop(self, event):
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
        self.snapped_edge = None
        self._dock_visible = True

        # Auto-hide timer
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_dock)

        # Slide animations
        self.hide_animation = QPropertyAnimation(self, b"pos", self)
        self.hide_animation.setDuration(350)
        self.hide_animation.setEasingCurve(QEasingCurve.OutCubic)

        self.show_animation = QPropertyAnimation(self, b"pos", self)
        self.show_animation.setDuration(300)
        self.show_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Snap-to-edge animation
        self.snap_animation = QPropertyAnimation(self, b"pos", self)
        self.snap_animation.setDuration(400)
        self.snap_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.snap_animation.finished.connect(self._on_snap_finished)

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
        self.snapped_edge = self.load_snapped_edge()
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
            self.cancel_hide()
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            new_pos = event.globalPosition().toPoint() - self.drag_position

            # Clamp to keep at least 30px visible
            screen = self.screen()
            if screen:
                geo = screen.availableGeometry()
                new_pos.setX(max(geo.left() - self.width() + 30, min(new_pos.x(), geo.right() - 30)))
                new_pos.setY(max(geo.top() - self.height() + 30, min(new_pos.y(), geo.bottom() - 30)))

            self.move(new_pos)
            if self.drawer.isVisible():
                self.drawer.hide()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        # عند الانتهاء من سحب النافذة -> الالتصاق بالحافة ثم حفظ الموقع
        if event.button() == Qt.LeftButton and self.drag_position is not None:
            self.drag_position = None
            self.snap_to_edge()
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
                json.dump({
                    "x": self.x(),
                    "y": self.y(),
                    "snapped_edge": self.snapped_edge
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving position: {e}")

    def load_snapped_edge(self):
        """Load the snapped edge state from settings."""
        try:
            with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('snapped_edge', None)
        except Exception:
            return None

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
        settings_action = menu.addAction("Settings / Preferences")
        menu.addSeparator()
        about_action = menu.addAction("About")
        exit_action = menu.addAction("Exit")

        action = menu.exec_(self.mapToGlobal(pos))
        if action == add_action:
            self.add_category()
        elif action == settings_action:
            self.show_settings()
        elif action == about_action:
            self.show_about()
        elif action == exit_action:
            QApplication.quit()

    def add_category(self):
        dialog = CategoryDialog(self, title="Add New Category")
        if dialog.exec() == QDialog.Accepted and dialog.category_name:
            self.categories.append({
                "name": dialog.category_name,
                "icon": dialog.category_emoji,
                "items": [],
            })
            save_config(self.categories)
            self.rebuild_bubbles()

    def show_settings(self):
        SettingsDialog(self).exec()

    def show_about(self):
        AboutDialog(self).exec()

    # ---------- قائمة الفقاعات (الفئات) ----------

    def on_category_context(self, pos, bubble, category_data):
        menu = QMenu(self)
        menu.setStyleSheet(DARK_MENU_STYLE)
        rename_action = menu.addAction("Rename / Change Icon")
        move_left_action = menu.addAction("Move Left")
        move_right_action = menu.addAction("Move Right")
        remove_action = menu.addAction("Remove Category")

        action = menu.exec_(bubble.mapToGlobal(pos))
        if action == rename_action:
            self.edit_category(category_data)
        elif action == move_left_action:
            self.move_category(category_data, -1)
        elif action == move_right_action:
            self.move_category(category_data, 1)
        elif action == remove_action:
            self.delete_category(category_data)

    def move_category(self, category_data, direction):
        index = self.categories.index(category_data)
        new_index = index + direction
        if 0 <= new_index < len(self.categories):
            self.categories[index], self.categories[new_index] = \
                self.categories[new_index], self.categories[index]
            save_config(self.categories)
            self.rebuild_bubbles()

    def edit_category(self, category_data):
        dialog = CategoryDialog(
            self,
            title="Rename / Change Icon",
            name=category_data.get('name', ''),
            emoji=category_data.get('icon', '📁'),
        )
        if dialog.exec() == QDialog.Accepted and dialog.category_name:
            category_data['name'] = dialog.category_name
            category_data['icon'] = dialog.category_emoji

            # إغلاق القائمة إن كانت مفتوحة لهذه الفئة (تغيّر الاسم)
            if self.drawer.current_category_data is category_data:
                self.drawer.hide()
                self.drawer.current_cat_name = None
                self.drawer.current_bubble = None
                self.drawer.current_category_data = None

            save_config(self.categories)
            self.rebuild_bubbles()

    def delete_category(self, category_data):
        dialog = ConfirmDialog(
            self,
            title="Remove Category",
            message=f"Remove '{category_data.get('name', '')}' and all its items?",
        )
        dialog.exec()
        if not dialog.confirmed:
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

    # ---------- Edge Snapping & Auto-Hide ----------

    def snap_to_edge(self):
        """Find the nearest screen edge and smoothly glide to it."""
        screen = self.screen()
        if screen is None:
            return
        geo = screen.availableGeometry()

        x, y = self.x(), self.y()
        w, h = self.width(), self.height()

        # Calculate distance to each edge
        dist_left = abs(x - geo.left())
        dist_right = abs((x + w) - (geo.right() + 1))
        dist_top = abs(y - geo.top())

        # Find the closest edge
        distances = {
            "left": dist_left,
            "right": dist_right,
            "top": dist_top,
        }
        closest_edge = min(distances, key=distances.get)

        # Calculate target position for the closest edge
        if closest_edge == "left":
            target = QPoint(geo.left(), max(geo.top(), min(y, geo.bottom() - h + 1)))
        elif closest_edge == "right":
            target = QPoint(geo.right() - w + 1, max(geo.top(), min(y, geo.bottom() - h + 1)))
        else:  # top
            target = QPoint(max(geo.left(), min(x, geo.right() - w + 1)), geo.top())

        self.snapped_edge = closest_edge

        # Animate to the target position
        self.snap_animation.stop()
        self.snap_animation.setStartValue(self.pos())
        self.snap_animation.setEndValue(target)
        self.snap_animation.start()

    def _on_snap_finished(self):
        """Called when snap animation completes."""
        self.save_position()
        self.start_hide_timer()

    def start_hide_timer(self):
        """Start the auto-hide timer if docked to an edge."""
        if self.snapped_edge and not self.hide_timer.isActive():
            self.hide_timer.start(1200)

    def cancel_hide(self):
        """Cancel the hide timer and any ongoing animations."""
        self.hide_timer.stop()
        if self.hide_animation.state() == QPropertyAnimation.Running:
            self.hide_animation.stop()
        if self.show_animation.state() == QPropertyAnimation.Running:
            self.show_animation.stop()
        if self.snap_animation.state() == QPropertyAnimation.Running:
            self.snap_animation.stop()

    def hide_dock(self):
        """Animate the dock sliding off-screen, leaving a small handle visible."""
        if not self.snapped_edge:
            return

        self._dock_visible = False

        # Close drawer
        if self.drawer.isVisible():
            self.drawer.hide()
            self.drawer.current_cat_name = None
            self.drawer.current_bubble = None
            self.drawer.current_category_data = None

        screen = self.screen()
        if screen is None:
            return
        geo = screen.availableGeometry()

        target = self.pos()
        if self.snapped_edge == "left":
            target = QPoint(-self.width() + 8, self.y())
        elif self.snapped_edge == "right":
            target = QPoint(geo.right() - 8 + 1, self.y())
        elif self.snapped_edge == "top":
            target = QPoint(self.x(), -self.height() + 8)

        self.hide_animation.stop()
        self.hide_animation.setStartValue(self.pos())
        self.hide_animation.setEndValue(target)
        self.hide_animation.start()

    def show_dock(self):
        """Animate the dock sliding back to its snapped position."""
        if not self.snapped_edge:
            return

        self._dock_visible = True

        screen = self.screen()
        if screen is None:
            return
        geo = screen.availableGeometry()

        target = self.pos()
        if self.snapped_edge == "left":
            target = QPoint(geo.left(), self.y())
        elif self.snapped_edge == "right":
            target = QPoint(geo.right() - self.width() + 1, self.y())
        elif self.snapped_edge == "top":
            target = QPoint(self.x(), geo.top())

        self.show_animation.stop()
        self.show_animation.setStartValue(self.pos())
        self.show_animation.setEndValue(target)
        self.show_animation.start()

    def enterEvent(self, event):
        self.cancel_hide()
        if self.snapped_edge and not self._dock_visible:
            self.show_dock()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.start_hide_timer()
        super().leaveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.snapped_edge:
            self.snap_to_edge()