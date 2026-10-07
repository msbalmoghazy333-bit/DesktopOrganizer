"""Native Windows icon extraction utility.

Extracts the real system icon for executables (.exe), shortcuts (.lnk),
folders and files using the Windows Shell API (Shell32) with a
QFileIconProvider fallback, and a clean default icon as a last resort.
"""

import os
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QFileInfo
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileIconProvider, QApplication, QStyle

# Optional: high-fidelity HICON -> QPixmap conversion (Windows only)
try:
    from PySide6.QtWinExtras import QtWin
    _HAS_QTWIN_EXTRAS = True
except ImportError:
    _HAS_QTWIN_EXTRAS = False

# Shell32 flags
SHGFI_ICON = 0x000000100
SHGFI_LARGEICON = 0x000000000


class _SHFILEINFO(ctypes.Structure):
    _fields_ = [
        ("hIcon", wintypes.HICON),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", wintypes.DWORD),
        ("szDisplayName", wintypes.WCHAR * 260),
        ("szTypeName", wintypes.WCHAR * 80),
    ]


def _extract_via_shell32(path):
    """Extract the native icon via Shell32.SHGetFileInfo.

    Highest fidelity: resolves the real icon of .exe files and the
    target icon of .lnk shortcuts.
    """
    if os.name != "nt" or not _HAS_QTWIN_EXTRAS:
        return QIcon()

    sfi = _SHFILEINFO()
    flags = SHGFI_ICON | SHGFI_LARGEICON
    shell32 = ctypes.windll.Shell32
    result = shell32.SHGetFileInfoW(
        path, 0, ctypes.byref(sfi), ctypes.sizeof(sfi), flags
    )
    if result and sfi.hIcon:
        try:
            pixmap = QtWin.fromHICON(sfi.hIcon)
            if not pixmap.isNull():
                return QIcon(pixmap)
        finally:
            # We own the returned HICON -> must destroy it to avoid a GDI leak
            ctypes.windll.User32.DestroyIcon(sfi.hIcon)
    return QIcon()


def _extract_via_file_icon_provider(path):
    """Fallback extraction using Qt's platform-aware QFileIconProvider."""
    provider = QFileIconProvider()
    icon = provider.icon(QFileInfo(path))
    return icon if not icon.isNull() else QIcon()


def _default_icon():
    """Clean final fallback: the platform's standard file icon."""
    style = QApplication.style()
    if style is not None:
        return style.standardIcon(QStyle.SP_FileIcon)
    return QIcon()


def extract_native_icon(path):
    """Return a QIcon for the given file / shortcut / executable path.

    Priority:
      1. Shell32 native extraction (handles .exe and .lnk targets)
      2. QFileIconProvider (platform-aware fallback)
      3. Clean default icon
    """
    icon = _extract_via_shell32(path)
    if icon.isNull():
        icon = _extract_via_file_icon_provider(path)
    if icon.isNull():
        icon = _default_icon()
    return icon
