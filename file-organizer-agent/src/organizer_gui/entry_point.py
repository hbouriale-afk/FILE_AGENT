"""Entry point for launching the PyQt6 GUI."""

import sys
from pathlib import Path

# Add src to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from organizer_gui.main_window import FileOrganizerGUI
from PyQt6.QtWidgets import QApplication


def main():
    """Launch the GUI application."""
    app = QApplication(sys.argv)
    window = FileOrganizerGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
