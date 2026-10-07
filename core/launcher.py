import os
import subprocess
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

def launch_target(path_or_command):
    if path_or_command.startswith('http'):
        QDesktopServices.openUrl(QUrl(path_or_command))
    else:
        try:
            os.startfile(path_or_command)
        except FileNotFoundError:
            subprocess.Popen(path_or_command, shell=True)
