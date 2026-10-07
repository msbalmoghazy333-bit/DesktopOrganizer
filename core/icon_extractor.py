"""Native Windows icon extraction utility.

Extracts the real system icon for executables (.exe), shortcuts (.lnk),
folders and files. Shortcut targets are resolved first so the extracted
icon is the clean, original application icon (no shortcut arrow overlay).

Extraction priority:
  1. Shell32 native extraction (when PySide6.QtWinExtras is available)
  2. QFileIconProvider (platform-aware fallback)
  3. Clean default icon (standard file icon from the current style)
"""

import os
import subprocess
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


def resolve_shortcut_target(path):
    """Resolve a .lnk shortcut to its real target path.

    Returns the target path (e.g. the underlying .exe) so the extracted
    icon is the clean original application icon without the Windows
    shortcut arrow overlay. Non-shortcut paths are returned unchanged.
    """
    if not path or not path.lower().endswith('.lnk'):
        return path

    # 1) win32com (fast, in-process COM)
    target = _resolve_target_via_win32com(path)
    if target:
        return target

    # 2) PowerShell COM fallback (no extra dependencies)
    target = _resolve_target_via_powershell(path)
    if target:
        return target

    # 3) Fallback: use the shortcut path as-is
    return path


def _resolve_target_via_win32com(path):
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(os.path.abspath(path))
        target = shortcut.TargetPath
        if target and os.path.exists(target):
            return target
    except Exception:
        pass
    return None


def _resolve_target_via_powershell(path):
    try:
        escaped = path.replace("'", "''")
        ps_script = (
            "$sh = New-Object -ComObject WScript.Shell; "
            f"$lnk = $sh.CreateShortcut('{escaped}'); "
            "if ($lnk.TargetPath) { $lnk.TargetPath }"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        target = (result.stdout or "").strip()
        if target and os.path.exists(target):
            return target
    except Exception:
        pass
    return None


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

    .lnk shortcuts are resolved to their real target first so the icon
    is the clean original application icon (no arrow overlay).
    """
    resolved_path = resolve_shortcut_target(path)
    icon = _extract_via_shell32(resolved_path)
    if icon.isNull():
        icon = _extract_via_file_icon_provider(resolved_path)
    if icon.isNull():
        icon = _default_icon()
    return icon
