"""Entry point for launching the PyQt6 GUI."""

import sys
from PyQt6.QtWidgets import QApplication
from organizer_gui.main_window import FileOrganizerGUI


def main():
    """Launch the GUI application."""
    app = QApplication(sys.argv)
    window = FileOrganizerGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
