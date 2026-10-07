import sys
import os
import json
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QMouseEvent
from PySide6.QtWidgets import (
    QWidget, QApplication, QHBoxLayout, QVBoxLayout, QPushButton, QLabel
)
from core.launcher import launch_target

class CategoryBubble(QPushButton):
    def __init__(self, category_data, on_click_callback, parent=None):
        super().__init__(parent)
        self.category_data = category_data
        self.on_click_callback = on_click_callback
        
        self.setFixedSize(54, 54)
        self.setCursor(Qt.PointingHandCursor)
        self.setText(category_data.get('icon', '📁'))
        self.setToolTip(category_data.get('name', 'Category'))
        
        # خط للأيقونة التعبيرية
        font = QFont("Segoe UI Emoji", 18)
        self.setFont(font)
        
        self.setStyleSheet("""
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
        """)
        self.clicked.connect(lambda: self.on_click_callback(self, self.category_data))

class Drawer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.current_cat_name = None
        
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(8)
        self.setLayout(self.layout)
        self.hide()

    def show_category(self, bubble_widget, category_data):
        cat_name = category_data.get('name', '')
        
        # إذا ضغط المستخدم على نفس التصنيف المفتوح، يتم إغلاقه
        if self.isVisible() and self.current_cat_name == cat_name:
            self.hide()
            self.current_cat_name = None
            return

        self.current_cat_name = cat_name

        # تفريغ الأزرار السابقة
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # عنوان التصنيف
        title_label = QLabel(cat_name)
        title_label.setStyleSheet("color: #aaaaaa; font-size: 11px; font-weight: bold; padding-left: 4px;")
        self.layout.addWidget(title_label)

        # إضافة أزرار العناصر
        items = category_data.get('items', [])
        for item in items:
            btn = QPushButton(item.get('name', 'App'))
            btn.setFixedHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(35, 35, 38, 230);
                    color: #f0f0f0;
                    border: 1px solid rgba(70, 70, 75, 180);
                    border-radius: 8px;
                    padding: 6px 14px;
                    font-size: 13px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: rgba(55, 55, 60, 255);
                    border-color: rgba(100, 100, 110, 255);
                    color: #ffffff;
                }
            """)
            cmd = item.get('command', '')
            btn.clicked.connect(lambda checked=False, target=cmd: self.launch_and_close(target))
            self.layout.addWidget(btn)

        self.adjustSize()

        # محاذاة القائمة بجوار الزر الذي تم النقر عليه
        geo = bubble_widget.mapToGlobal(QPoint(0, 0))
        self.move(geo.x(), geo.y() + bubble_widget.height() + 10)
        self.show()

    def launch_and_close(self, command):
        launch_target(command)
        self.hide()
        self.current_cat_name = None

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
        self.drawer = Drawer()
        self.drag_position = None
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        # قراءة categories.json
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, 'config', 'categories.json')
        
        categories = []
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    categories = data.get('categories', [])
            except Exception as e:
                print(f"Error loading JSON: {e}")

        # إنشاء دائرة لكل تصنيف
        for cat in categories:
            bubble = CategoryBubble(cat, self.on_category_clicked, self)
            main_layout.addWidget(bubble)

        self.setLayout(main_layout)
        self.setGeometry(120, 120, self.sizeHint().width(), self.sizeHint().height())
        self.show()

    def on_category_clicked(self, bubble_widget, category_data):
        self.drawer.show_category(bubble_widget, category_data)

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        # خلفية الـ Dock الشفافة
        brush = QBrush(QColor(20, 20, 22, 180))
        qp.setBrush(brush)
        qp.setPen(QPen(QColor(60, 60, 65, 140), 1))
        qp.drawRoundedRect(0, 0, self.width(), self.height(), 35, 35)
        qp.end()

    # ميزة السحب بالماوس للـ Dock
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