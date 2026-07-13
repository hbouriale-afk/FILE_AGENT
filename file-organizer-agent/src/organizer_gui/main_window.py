"""Main application window for the File Organizer GUI."""

from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem,
    QProgressBar, QMessageBox, QTabWidget, QTextEdit, QHeaderView,
    QProgressDialog, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor, QFont
from PyQt6.QtCore import QTimer

from organizer.scanner import scan_directory
from organizer.duplicates import find_duplicates
from organizer.archives import find_archives
from organizer.planner import build_plan
from organizer.executor import apply_plan, undo as undo_actions
from organizer.classifier import summarize

import json


class ScanWorker(QThread):
    """Background thread for scanning folders."""
    progress = pyqtSignal(str)  # status message
    finished = pyqtSignal(list, list)  # duplicates, archives
    error = pyqtSignal(str)

    def __init__(self, folder_path: str):
        super().__init__()
        self.folder_path = folder_path

    def run(self):
        try:
            self.progress.emit("Scanning directory...")
            files = scan_directory(self.folder_path)
            self.progress.emit(f"Found {len(files)} files. Checking for duplicates...")
            
            dup_groups = find_duplicates(files)
            self.progress.emit(f"Found {len(dup_groups)} duplicate group(s). Checking for archives...")
            
            archives = find_archives(files)
            self.progress.emit("Scan complete!")
            
            self.finished.emit(dup_groups, archives)
        except Exception as e:
            self.error.emit(str(e))


class CleanupWorker(QThread):
    """Background thread for applying cleanup plan."""
    progress = pyqtSignal(int)  # progress percentage
    finished = pyqtSignal(str)  # log path
    error = pyqtSignal(str)

    def __init__(self, plan, root: Path, dry_run: bool = True):
        super().__init__()
        self.plan = plan
        self.root = root
        self.dry_run = dry_run

    def run(self):
        try:
            log_path = apply_plan(self.plan, self.root, dry_run=self.dry_run)
            self.finished.emit(str(log_path))
        except Exception as e:
            self.error.emit(str(e))


class FileOrganizerGUI(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Organizer Agent")
        self.setGeometry(100, 100, 1200, 700)
        self.setStyleSheet(self._load_stylesheet())

        # State
        self.selected_folder = None
        self.dup_groups = []
        self.archives = []
        self.plan = []
        self.scan_worker = None

        # Main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout()
        self.central_widget.setLayout(main_layout)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Scan
        self._setup_scan_tab()
        # Tab 2: Results
        self._setup_results_tab()
        # Tab 3: Cleanup
        self._setup_cleanup_tab()
        # Tab 4: Undo
        self._setup_undo_tab()

    def _setup_scan_tab(self):
        """Set up the scan tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select a folder to scan...")
        self.folder_input.setReadOnly(True)
        folder_layout.addWidget(QLabel("Folder:"))
        folder_layout.addWidget(self.folder_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse)
        folder_layout.addWidget(browse_btn)

        layout.addLayout(folder_layout)

        # Scan button
        self.scan_btn = QPushButton("Start Scan")
        self.scan_btn.setFixedHeight(40)
        self.scan_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.scan_btn.clicked.connect(self._on_scan)
        layout.addWidget(self.scan_btn)

        # Progress
        self.scan_progress = QProgressBar()
        self.scan_progress.setVisible(False)
        layout.addWidget(self.scan_progress)

        self.status_label = QLabel("Ready to scan.")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        widget.setLayout(layout)
        self.tabs.addTab(widget, "📁 Scan")

    def _setup_results_tab(self):
        """Set up the results tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Summary
        self.summary_label = QLabel("No scan results yet.")
        self.summary_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.summary_label)

        # AI Summary
        ai_label = QLabel("AI Summary (if available):")
        ai_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(ai_label)

        self.ai_summary_text = QTextEdit()
        self.ai_summary_text.setReadOnly(True)
        self.ai_summary_text.setMaximumHeight(100)
        layout.addWidget(self.ai_summary_text)

        # Duplicates table
        dup_label = QLabel("Duplicate Files:")
        dup_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(dup_label)

        self.dup_table = QTableWidget()
        self.dup_table.setColumnCount(3)
        self.dup_table.setHorizontalHeaderLabels(["Size", "Original File", "Duplicates"])
        self.dup_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.dup_table)

        # Archives table
        arch_label = QLabel("Archives Found:")
        arch_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(arch_label)

        self.arch_table = QTableWidget()
        self.arch_table.setColumnCount(2)
        self.arch_table.setHorizontalHeaderLabels(["File Path", "Entries"])
        self.arch_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.arch_table)

        widget.setLayout(layout)
        self.tabs.addTab(widget, "📊 Results")

    def _setup_cleanup_tab(self):
        """Set up the cleanup tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        info_label = QLabel(
            "Review the plan and choose whether to apply the cleanup.\n"
            "Files will be moved to '_organizer_review/' folder (not deleted)."
        )
        info_label.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 5px; color: #0d47a1;")
        layout.addWidget(info_label)

        # Mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Cleanup Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Dry Run (Preview Only)", "Apply (Move Files)"])
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Action plan
        plan_label = QLabel("Action Plan:")
        plan_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(plan_label)

        self.plan_text = QTextEdit()
        self.plan_text.setReadOnly(True)
        layout.addWidget(self.plan_text)

        # Buttons
        btn_layout = QHBoxLayout()
        self.build_plan_btn = QPushButton("Build Cleanup Plan")
        self.build_plan_btn.clicked.connect(self._on_build_plan)
        btn_layout.addWidget(self.build_plan_btn)

        self.apply_cleanup_btn = QPushButton("Execute Cleanup")
        self.apply_cleanup_btn.setFixedHeight(40)
        self.apply_cleanup_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.apply_cleanup_btn.clicked.connect(self._on_apply_cleanup)
        btn_layout.addWidget(self.apply_cleanup_btn)

        layout.addLayout(btn_layout)
        widget.setLayout(layout)
        self.tabs.addTab(widget, "🧹 Cleanup")

    def _setup_undo_tab(self):
        """Set up the undo tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        info_label = QLabel(
            "Undo a previous cleanup operation by loading the undo log.\n"
            "This will restore all files to their original locations."
        )
        info_label.setStyleSheet("background-color: #fff3e0; padding: 10px; border-radius: 5px; color: #e65100;")
        layout.addWidget(info_label)

        # Log file selection
        log_layout = QHBoxLayout()
        self.undo_log_input = QLineEdit()
        self.undo_log_input.setPlaceholderText("Select undo_log.json...")
        self.undo_log_input.setReadOnly(True)
        log_layout.addWidget(QLabel("Log File:"))
        log_layout.addWidget(self.undo_log_input)

        browse_log_btn = QPushButton("Browse...")
        browse_log_btn.clicked.connect(self._on_browse_undo_log)
        log_layout.addWidget(browse_log_btn)

        layout.addLayout(log_layout)

        # Undo button
        self.undo_btn = QPushButton("Restore Files")
        self.undo_btn.setFixedHeight(40)
        self.undo_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        self.undo_btn.clicked.connect(self._on_undo)
        layout.addWidget(self.undo_btn)

        self.undo_result_text = QTextEdit()
        self.undo_result_text.setReadOnly(True)
        layout.addWidget(self.undo_result_text)

        layout.addStretch()
        widget.setLayout(layout)
        self.tabs.addTab(widget, "↩️ Undo")

    def _on_browse(self):
        """Browse for a folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan")
        if folder:
            self.selected_folder = folder
            self.folder_input.setText(folder)

    def _on_scan(self):
        """Start scanning the selected folder."""
        if not self.selected_folder:
            QMessageBox.warning(self, "Error", "Please select a folder first.")
            return

        self.scan_btn.setEnabled(False)
        self.scan_progress.setVisible(True)
        self.scan_progress.setValue(0)
        self.status_label.setText("Scanning in progress...")

        self.scan_worker = ScanWorker(self.selected_folder)
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.error.connect(self._on_scan_error)
        self.scan_worker.start()

    def _on_scan_progress(self, message: str):
        """Update scan progress."""
        self.status_label.setText(message)
        self.scan_progress.setValue((self.scan_progress.value() + 20) % 100)

    def _on_scan_finished(self, dup_groups, archives):
        """Handle scan completion."""
        self.dup_groups = dup_groups
        self.archives = archives
        self.scan_btn.setEnabled(True)
        self.scan_progress.setVisible(False)

        # Update results tab
        self._populate_results()

        # Show results
        self.tabs.setCurrentIndex(1)
        self.status_label.setText(f"Scan complete! Found {len(dup_groups)} duplicate groups and {len(archives)} archives.")

    def _on_scan_error(self, error: str):
        """Handle scan error."""
        self.scan_btn.setEnabled(True)
        self.scan_progress.setVisible(False)
        QMessageBox.critical(self, "Scan Error", f"An error occurred during scan:\n{error}")

    def _populate_results(self):
        """Populate the results tab with scan data."""
        # Summary
        total_wasted = sum(g.wasted_bytes for g in self.dup_groups)
        summary = f"Found {len(self.dup_groups)} duplicate group(s) with {total_wasted / 1e6:.1f}MB reclaimable. {len(self.archives)} archive(s) detected."
        self.summary_label.setText(summary)

        # AI Summary
        ai_summary = summarize(self.dup_groups, self.archives)
        self.ai_summary_text.setText(ai_summary or "(Set GEMINI_API_KEY for AI summary)")

        # Duplicates table
        self.dup_table.setRowCount(len(self.dup_groups))
        for i, group in enumerate(self.dup_groups):
            size_mb = group.files[0].size / 1e6
            size_item = QTableWidgetItem(f"{size_mb:.1f}MB")
            original_item = QTableWidgetItem(str(group.files[0].path))
            dup_count_item = QTableWidgetItem(f"{len(group.files) - 1} duplicate(s)")
            self.dup_table.setItem(i, 0, size_item)
            self.dup_table.setItem(i, 1, original_item)
            self.dup_table.setItem(i, 2, dup_count_item)

        # Archives table
        self.arch_table.setRowCount(len(self.archives))
        for i, arch in enumerate(self.archives):
            path_item = QTableWidgetItem(str(arch.file.path))
            entries = arch.entry_count if arch.entry_count is not None else "unknown"
            entries_item = QTableWidgetItem(str(entries))
            self.arch_table.setItem(i, 0, path_item)
            self.arch_table.setItem(i, 1, entries_item)

    def _on_build_plan(self):
        """Build the cleanup plan."""
        if not self.dup_groups and not self.archives:
            QMessageBox.warning(self, "Warning", "No duplicates or archives found. Run a scan first.")
            return

        root = Path(self.selected_folder).resolve()
        self.plan = build_plan(root, self.dup_groups, self.archives)

        plan_text = f"Cleanup Plan ({len(self.plan)} action(s)):\n\n"
        for action in self.plan[:50]:  # Show first 50
            plan_text += f"[{action.type}]\n  From: {action.src}\n  To: {action.dest}\n\n"
        if len(self.plan) > 50:
            plan_text += f"... and {len(self.plan) - 50} more action(s)"

        self.plan_text.setText(plan_text)
        self.tabs.setCurrentIndex(2)
        QMessageBox.information(self, "Plan Ready", f"Plan built with {len(self.plan)} action(s).")

    def _on_apply_cleanup(self):
        """Apply the cleanup plan."""
        if not self.plan:
            QMessageBox.warning(self, "Warning", "Build a plan first using 'Build Cleanup Plan'.")
            return

        dry_run = self.mode_combo.currentIndex() == 0
        mode_str = "dry run (preview)" if dry_run else "apply (move files)"

        reply = QMessageBox.question(
            self,
            "Confirm Cleanup",
            f"Execute cleanup in {mode_str} mode?\n\n"
            f"This will {'' if dry_run else 'move'} {len(self.plan)} file(s) "
            f"into '_organizer_review/' folder.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.No:
            return

        root = Path(self.selected_folder).resolve()
        self.cleanup_worker = CleanupWorker(self.plan, root, dry_run=dry_run)
        self.cleanup_worker.finished.connect(self._on_cleanup_finished)
        self.cleanup_worker.error.connect(self._on_cleanup_error)
        self.cleanup_worker.start()

        QMessageBox.information(self, "Processing", "Cleanup in progress...")

    def _on_cleanup_finished(self, log_path: str):
        """Handle cleanup completion."""
        mode = "dry run" if self.mode_combo.currentIndex() == 0 else "cleanup"
        QMessageBox.information(
            self,
            "Success",
            f"Cleanup {mode} complete!\n\nLog file: {log_path}",
        )

    def _on_cleanup_error(self, error: str):
        """Handle cleanup error."""
        QMessageBox.critical(self, "Cleanup Error", f"An error occurred:\n{error}")

    def _on_browse_undo_log(self):
        """Browse for an undo log file."""
        log_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select undo_log.json",
            filter="JSON Files (*.json)",
        )
        if log_file:
            self.undo_log_input.setText(log_file)

    def _on_undo(self):
        """Undo a previous cleanup."""
        log_path = self.undo_log_input.text()
        if not log_path:
            QMessageBox.warning(self, "Error", "Please select an undo log file.")
            return

        try:
            restored = undo_actions(Path(log_path))
            result = f"Successfully restored {restored} file(s) to their original locations."
            self.undo_result_text.setText(result)
            QMessageBox.information(self, "Success", result)
        except Exception as e:
            QMessageBox.critical(self, "Undo Error", f"An error occurred during undo:\n{str(e)}")

    def _load_stylesheet(self) -> str:
        """Load application stylesheet."""
        return """
            QMainWindow {
                background-color: #ffffff;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
                font-family: Courier;
                font-size: 10px;
            }
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                border: none;
                padding: 5px;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
            }
        """
