"""Production-ready dialogs for Desktop Organizer.

All dialogs are frameless, translucent dark-glass styled with
consistent border-radius, shadows, and Segoe UI typography.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QGraphicsDropShadowEffect
)

# Shared dark-glass dialog style
DIALOG_STYLE = """
    QDialog {
        background-color: rgba(28, 28, 30, 245);
        border: 1px solid rgba(80, 80, 85, 200);
        border-radius: 14px;
    }
    QLabel {
        color: #f0f0f0;
        font-family: 'Segoe UI';
    }
    QLineEdit {
        background-color: rgba(45, 45, 48, 255);
        color: #f0f0f0;
        border: 1px solid rgba(100, 100, 110, 255);
        border-radius: 8px;
        padding: 8px 12px;
        font-family: 'Segoe UI';
        font-size: 13px;
    }
    QLineEdit:focus {
        border: 1px solid #58a6ff;
    }
    QPushButton {
        background-color: rgba(55, 55, 60, 255);
        color: #f0f0f0;
        border: 1px solid rgba(100, 100, 110, 255);
        border-radius: 8px;
        padding: 8px 20px;
        font-family: 'Segoe UI';
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: rgba(75, 75, 82, 255);
        color: #ffffff;
    }
    QPushButton[emojiBtn="true"] {
        font-family: 'Segoe UI Emoji';
        font-size: 20px;
    }
    QCheckBox {
        color: #f0f0f0;
        font-family: 'Segoe UI';
        font-size: 13px;
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid rgba(100, 100, 110, 255);
        background-color: rgba(45, 45, 48, 255);
    }
    QCheckBox::indicator:checked {
        background-color: #58a6ff;
        border: 1px solid #58a6ff;
    }
"""

# Preset emojis for category icons
EMOJI_PRESETS = [
    "📁", "🌐", "👥", "🎮", "🎵",
    "📷", "💼", "🛒", "📚", "🍔",
    "⚽", "🚀", "💡", "🔧", "🎨",
    "📊", "🏠", "❤️", "⭐", "🔥",
]


def _add_shadow(widget):
    """Add a soft drop shadow to a frameless dialog."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(28)
    shadow.setColor(QColor(0, 0, 0, 180))
    shadow.setOffset(0, 6)
    widget.setGraphicsEffect(shadow)


class _BaseDialog(QDialog):
    """Base class for all frameless dark-glass dialogs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)
        _add_shadow(self)

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        brush = QBrush(QColor(28, 28, 30, 245))
        qp.setBrush(brush)
        qp.setPen(QPen(QColor(80, 80, 85, 200), 1))
        qp.drawRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        qp.end()


class CategoryDialog(_BaseDialog):
    """Elegant dialog for adding or renaming a category with emoji picker."""

    def __init__(self, parent=None, title="Add Category", name="", emoji="📁"):
        super().__init__(parent)
        self.selected_emoji = emoji

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(
            "color: #ffffff; font-size: 18px; font-weight: bold; font-family: 'Segoe UI';"
        )
        layout.addWidget(title_label)

        # Name input
        name_label = QLabel("Category Name")
        name_label.setStyleSheet("color: #aaaaaa; font-size: 12px; font-family: 'Segoe UI';")
        layout.addWidget(name_label)

        self.name_input = QLineEdit(name)
        self.name_input.setPlaceholderText("Enter a name...")
        self.name_input.setMinimumHeight(38)
        layout.addWidget(self.name_input)

        # Emoji picker
        emoji_label = QLabel("Choose an Icon")
        emoji_label.setStyleSheet("color: #aaaaaa; font-size: 12px; font-family: 'Segoe UI';")
        layout.addWidget(emoji_label)

        self.emoji_buttons = []
        grid = QGridLayout()
        grid.setSpacing(6)
        emoji_font = QFont("Segoe UI Emoji", 20)
        for i, e in enumerate(EMOJI_PRESETS):
            btn = QPushButton(e)
            btn.setFixedSize(42, 42)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("emojiBtn", "true")
            btn.setFont(emoji_font)
            if e == emoji:
                btn.setChecked(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(45, 45, 48, 255);
                    border: 1px solid rgba(100, 100, 110, 255);
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: rgba(75, 75, 82, 255);
                    border-color: #58a6ff;
                }
                QPushButton:checked {
                    background-color: rgba(50, 90, 150, 255);
                    border: 2px solid #58a6ff;
                }
            """)
            btn.clicked.connect(lambda checked, em=e: self._select_emoji(em))
            grid.addWidget(btn, i // 5, i % 5)
            self.emoji_buttons.append(btn)
        layout.addLayout(grid)

        # Custom emoji input
        self.emoji_input = QLineEdit(emoji)
        self.emoji_input.setPlaceholderText("Or type a custom emoji...")
        self.emoji_input.setMinimumHeight(38)
        self.emoji_input.textChanged.connect(self._on_custom_emoji)
        emoji_font = QFont("Segoe UI Emoji", 13)
        self.emoji_input.setFont(emoji_font)
        layout.addWidget(self.emoji_input)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setMinimumHeight(40)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #58a6ff;
                color: #ffffff;
                border: 1px solid #58a6ff;
                border-radius: 8px;
                padding: 8px 28px;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a95e8;
            }
        """)
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _select_emoji(self, emoji):
        self.selected_emoji = emoji
        self.emoji_input.setText(emoji)
        for btn in self.emoji_buttons:
            btn.setChecked(btn.text() == emoji)

    def _on_custom_emoji(self, text):
        stripped = text.strip()
        self.selected_emoji = stripped if stripped else "📁"
        for btn in self.emoji_buttons:
            btn.setChecked(btn.text() == stripped)

    @property
    def category_name(self):
        return self.name_input.text().strip()

    @property
    def category_emoji(self):
        return self.selected_emoji


class AboutDialog(_BaseDialog):
    """Clean mini popup with product branding."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        # Branding icon
        icon_label = QLabel("🗂️")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # Product name
        name_label = QLabel("Desktop Organizer")
        name_label.setStyleSheet(
            "color: #ffffff; font-size: 20px; font-weight: bold; font-family: 'Segoe UI';"
        )
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)

        # Version
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet(
            "color: #aaaaaa; font-size: 13px; font-family: 'Segoe UI';"
        )
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        # Tagline
        tagline = QLabel("A minimalist floating dock for your desktop")
        tagline.setStyleSheet(
            "color: #888888; font-size: 12px; font-family: 'Segoe UI';"
        )
        tagline.setAlignment(Qt.AlignCenter)
        layout.addWidget(tagline)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(38)
        close_btn.setMinimumWidth(120)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)


class SettingsDialog(_BaseDialog):
    """Settings / Preferences dialog with startup and snap toggles."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        # Title
        title_label = QLabel("Settings")
        title_label.setStyleSheet(
            "color: #ffffff; font-size: 18px; font-weight: bold; font-family: 'Segoe UI';"
        )
        layout.addWidget(title_label)

        # Startup toggle
        self.startup_checkbox = QCheckBox("Launch at Windows startup")
        self.startup_checkbox.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.startup_checkbox)

        # Snap toggle
        self.snap_checkbox = QCheckBox("Snap to screen edges")
        self.snap_checkbox.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.snap_checkbox)

        layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(40)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class ConfirmDialog(_BaseDialog):
    """Sleek confirmation prompt."""

    def __init__(self, parent=None, title="Confirm", message=""):
        super().__init__(parent)
        self.confirmed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(
            "color: #ffffff; font-size: 16px; font-weight: bold; font-family: 'Segoe UI';"
        )
        layout.addWidget(title_label)

        # Message
        msg_label = QLabel(message)
        msg_label.setStyleSheet(
            "color: #cccccc; font-size: 13px; font-family: 'Segoe UI';"
        )
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        confirm_btn = QPushButton("Remove")
        confirm_btn.setMinimumHeight(40)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #d13438;
                color: #ffffff;
                border: 1px solid #d13438;
                border-radius: 8px;
                padding: 8px 28px;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b02a2e;
            }
        """)
        confirm_btn.clicked.connect(self._confirm)
        btn_row.addWidget(confirm_btn)

        layout.addLayout(btn_row)

    def _confirm(self):
        self.confirmed = True
        self.accept()
