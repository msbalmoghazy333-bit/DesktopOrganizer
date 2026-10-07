"""Universal Windows Shell resolver.

Resolves ANY dragged item (standard .exe, .lnk shortcut, folder, or
UWP / Windows Store app) to:
  - the exact display name as seen by the user in Windows Explorer
  - a crisp, original, full-resolution icon WITHOUT shortcut arrow
    overlays or badges
  - a reliable launch command that works universally

Resolution strategy:
  * .lnk  -> custom IconLocation (if any) -> resolved target -> UWP
             package logo -> shell-resolved shortcut icon
  * .exe  -> native shell icon (QFileIconProvider uses SHGetFileInfoW
             without the SHGFI_LINKOVERLAY flag, so no arrow badge)
  * dir   -> shell folder icon
  * UWP   -> package logo parsed from AppxManifest.xml
"""

import os
import glob
import xml.etree.ElementTree as ET

from PySide6.QtGui import QIcon, QPixmap

from core.icon_extractor import extract_native_icon, resolve_shortcut_target

# UWP package root marker
PACKAGE_MANIFEST = "AppxManifest.xml"

# Visual element logo attributes (largest first for preference)
LOGO_ATTRIBUTES = (
    "Square310x310Logo",
    "Square150x150Logo",
    "Wide310x150Logo",
    "Square71x71Logo",
    "Square44x44Logo",
    "StoreLogo",
)


class ShellItemInfo:
    """Fully resolved information for a dragged shell item."""

    def __init__(self, name, command, icon):
        self.name = name          # display name (as seen in Explorer)
        self.command = command    # reliable universal launch command
        self.icon = icon          # clean QIcon (no overlay badges)


def resolve_shell_item(path):
    """Resolve any dragged file / shortcut / folder / UWP app."""
    if not path:
        return None

    path = os.path.abspath(path)

    return ShellItemInfo(
        name=display_name(path),
        command=launch_command(path),
        icon=clean_icon(path),
    )


def display_name(path):
    """The exact display name as seen by the user in Windows Explorer.

    Payloads inside a UWP package use the manifest friendly name
    (never raw package hashes/IDs). Otherwise the file/folder name
    is used -- which is exactly what Explorer renders for
    shortcuts, executables and folders.
    """
    uwp_name = _uwp_display_name(path)
    if uwp_name:
        return uwp_name

    base = os.path.basename(path.rstrip("\\/"))
    name, _ = os.path.splitext(base)
    return name if name else base


def _uwp_display_name(path):
    """Friendly display name from a UWP package manifest (if applicable)."""
    package_dir = _find_package_dir(path)
    if not package_dir:
        return ""

    manifest_path = os.path.join(package_dir, PACKAGE_MANIFEST)
    if not os.path.exists(manifest_path):
        return ""

    try:
        tree = ET.parse(manifest_path)
        root = tree.getroot()
    except Exception:
        return ""

    ns = {"m": "http://schemas.microsoft.com/appx/manifest/foundation/windows10"}
    props = root.find("m:Properties", ns)
    if props is None:
        return ""

    name = (props.findtext("m:DisplayName", default="", namespaces=ns) or "").strip()
    # Resource references (ms-resource:...) require PRI parsing; skip them
    if not name or name.lower().startswith("ms-resource:"):
        return ""
    return name


def launch_command(path):
    """A reliable launch command that works universally.

    The original path is kept intentionally: launching a .lnk through
    the shell preserves its target, arguments, working directory, icon
    and even UWP AppUserModelID activation -- far more reliable than
    launching a resolved target executable directly.
    """
    return path


def clean_icon(path):
    """Extract the crisp original icon without any shortcut arrow."""
    lowered = path.lower()

    if lowered.endswith(".lnk"):
        # 1) Custom icon location embedded in the shortcut (exact icon)
        icon = _icon_from_shortcut_icon_location(path)
        if not icon.isNull():
            return icon

        # 2) Resolve the real target and extract its clean icon
        target = resolve_shortcut_target(path)
        if target and target != path and not _is_explorer(target):
            icon = _uwp_package_icon(target)
            if not icon.isNull():
                return icon
            icon = extract_native_icon(target)
            if not icon.isNull():
                return icon

        # 3) Fallback: the shell resolves the shortcut itself (handles
        #    UWP app shortcuts whose target is an AppUserModelID)
        return extract_native_icon(path)

    # UWP package payload dragged from WindowsApps
    icon = _uwp_package_icon(path)
    if not icon.isNull():
        return icon

    # Standard file / folder / executable icon (clean, no overlay)
    return extract_native_icon(path)


def _is_explorer(path):
    """Check whether a resolved target is just explorer.exe."""
    explorer = os.path.join(
        os.environ.get("SystemRoot", r"C:\Windows"), "explorer.exe"
    )
    return path.lower() == explorer.lower()


def _icon_from_shortcut_icon_location(path):
    """Extract the custom icon specified in the shortcut (IconLocation)."""
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(os.path.abspath(path))
        icon_location = shortcut.IconLocation or ""
        if not icon_location:
            return QIcon()
        parts = icon_location.split(",")
        icon_path = parts[0].strip()
        index = 0
        if len(parts) > 1 and parts[1].strip().isdigit():
            index = int(parts[1].strip())
        if not icon_path or not os.path.exists(icon_path) or index != 0:
            return QIcon()
        if icon_path.lower().endswith(".ico"):
            return QIcon(icon_path)
        pixmap = QPixmap(icon_path)
        return QIcon(pixmap) if not pixmap.isNull() else QIcon()
    except Exception:
        return QIcon()


def _uwp_package_icon(path):
    """Extract the native app logo from a UWP package manifest."""
    package_dir = _find_package_dir(path)
    if not package_dir:
        return QIcon()

    manifest_path = os.path.join(package_dir, PACKAGE_MANIFEST)
    if not os.path.exists(manifest_path):
        return QIcon()

    try:
        tree = ET.parse(manifest_path)
        root = tree.getroot()
    except Exception:
        return QIcon()

    ns = {"m": "http://schemas.microsoft.com/appx/manifest/foundation/windows10"}
    candidates = []

    props = root.find("m:Properties", ns)
    if props is not None:
        logo = props.findtext("m:Logo", default="", namespaces=ns)
        if logo:
            candidates.append(logo)

    for elem in root.iter():
        for attr in LOGO_ATTRIBUTES:
            value = elem.get(attr)
            if value:
                candidates.append(value)

    best_pixmap = None
    best_scale = -1
    for candidate in candidates:
        full = os.path.join(package_dir, candidate)
        files = _scaled_variants(full)
        for file_path in files:
            scale = _scale_of(file_path)
            if scale > best_scale:
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    best_pixmap = pixmap
                    best_scale = scale

    return QIcon(best_pixmap) if best_pixmap is not None else QIcon()


def _scaled_variants(base_path):
    """Return a path and its scaled/targetsize variants (e.g. .scale-200)."""
    variants = []
    if os.path.exists(base_path):
        variants.append(base_path)
    # Scaled assets replace the extension: logo.png -> logo.scale-200.png
    stem = os.path.splitext(base_path)[0]
    for pattern in (stem + ".scale-*.png", stem + ".targetsize-*.png"):
        variants.extend(sorted(glob.glob(pattern)))
    return variants


def _scale_of(filename):
    """Extract the scale factor from a scaled asset filename."""
    base = os.path.basename(filename)
    for marker in (".scale-", ".targetsize-"):
        if marker in base:
            try:
                return int(base.split(marker)[1].split(".")[0])
            except (IndexError, ValueError):
                return 100
    return 100


def _find_package_dir(path):
    """Walk up from a path to find the UWP package root directory."""
    candidates = []
    if os.path.isdir(path):
        candidates.append(os.path.abspath(path))
    current = os.path.dirname(os.path.abspath(path))
    for _ in range(6):
        candidates.append(current)
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    for candidate in candidates:
        if os.path.exists(os.path.join(candidate, PACKAGE_MANIFEST)):
            return candidate
    return None
