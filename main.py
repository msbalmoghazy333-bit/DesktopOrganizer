import sys
from PySide6.QtWidgets import QApplication
from ui.window import Window

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Window()
    ex.show()
    sys.exit(app.exec())
