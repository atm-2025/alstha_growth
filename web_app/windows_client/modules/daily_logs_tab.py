import sqlite3
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QTableWidget, QTableWidgetItem, QDateEdit, QSpinBox, QGroupBox, QCheckBox, QButtonGroup, QHBoxLayout, QInputDialog, QAbstractItemView, QToolButton, QMessageBox, QSpinBox, QAbstractItemView, QToolButton
)
from PySide6.QtCore import Qt, QDate, QEvent
from PySide6.QtWidgets import QApplication
import os
import json
import re
from PySide6.QtGui import QIntValidator, QIcon, QFont
import datetime
import subprocess
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QIntValidator, QKeySequence
import platform
from functools import partial

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../daily_logs.db'))
def ensure_task_entry_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS Task_Entry (
            no INTEGER,
            data TEXT,
            name TEXT,
            type TEXT,
            status TEXT,
            remark TEXT,
            duration TEXT,
            attention INTEGER,
            descp TEXT,
            energy_level INTEGER
        )
    ''')
    conn.commit()
    conn.close()

class DailyLogsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_edit_mode = False
        self.editing_task_id = None
        self.options_json_path = os.path.join(os.path.dirname(__file__), 'json', 'dropdown_options.json')
        self.db_path = os.path.join(os.path.dirname(__file__), '../../daily_logs.db')
        self.init_db()
        # --- Main Layout: Horizontal split ---
        main_hlayout = QHBoxLayout()
        # --- Left column: All fields vertical ---
        left_vbox = QVBoxLayout()
        self.form_group = QGroupBox("Task Entry")
        form_layout = QVBoxLayout()
        # Add Task fields
        self.no_edit = QSpinBox()
        self.no_edit.setMinimum(1)
        self.no_edit.setMaximum(9999)
        self.no_edit.setReadOnly(True)
        form_layout.addWidget(QLabel("No:"))
        form_layout.addWidget(self.no_edit)
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setMaximumDate(QDate.currentDate())
        form_layout.addWidget(QLabel("Date:"))
        form_layout.addWidget(self.date_edit)
        self.name_edit = QLineEdit()
        form_layout.addWidget(QLabel("Name:"))
        form_layout.addWidget(self.name_edit)
        self.type_edit = QComboBox()
        self.type_edit.addItems(self.load_dropdown_options('type'))
        form_layout.addWidget(QLabel("Type:"))
        form_layout.addWidget(self.type_edit)
        self.status_edit = QComboBox()
        self.status_edit.addItems(self.load_dropdown_options('status'))
        form_layout.addWidget(QLabel("Status:"))
        form_layout.addWidget(self.status_edit)
        self.remark_edit = QLineEdit()
        form_layout.addWidget(QLabel("Remark:"))
        form_layout.addWidget(self.remark_edit)
        self.duration_edit = QLineEdit()
        self.duration_edit.setValidator(QIntValidator(1, 1440, self))
        form_layout.addWidget(QLabel("Duration (minutes):"))
        form_layout.addWidget(self.duration_edit)
        form_layout.addWidget(QLabel("Attention:"))
        self.attention_group = QButtonGroup(self)
        self.attention_group.setExclusive(True)
        self.attention_layout = QHBoxLayout()
        self.attention_checks = []
        for i, label in enumerate(["0%", "25%", "50%", "75%", "100%"]):
            cb = QCheckBox(label)
            cb.setStyleSheet("""
                QCheckBox::indicator {
                    border: 2px solid blue;
                    width: 18px;
                    height: 18px;
                }
                QCheckBox::indicator:checked {
                    background-color: blue;
                    border: 2px solid blue;
                }
                QCheckBox { padding: 2px; }
            """)
            self.attention_group.addButton(cb, i)
            self.attention_layout.addWidget(cb)
            self.attention_checks.append(cb)
        form_layout.addLayout(self.attention_layout)
        desc_layout = QHBoxLayout()
        desc_label = QLabel("Description:")
        desc_layout.addWidget(desc_label)
        self.desc_voice_btn = QPushButton("🎤")
        self.desc_voice_btn.setFixedWidth(30)
        desc_layout.addWidget(self.desc_voice_btn)
        form_layout.addLayout(desc_layout)
        self.description_edit = QTextEdit()
        self.description_edit.setFixedHeight(50)
        form_layout.addWidget(self.description_edit)
        form_layout.addWidget(QLabel("Energy Level:"))
        self.energy_group = QButtonGroup(self)
        self.energy_group.setExclusive(True)
        self.energy_layout = QHBoxLayout()
        self.energy_checks = []
        for i, (label, color) in enumerate([("Low", "red"), ("Medium", "orange"), ("High", "green")]):
            cb = QCheckBox(label)
            cb.setStyleSheet(f"""
                QCheckBox::indicator {{
                    border: 2px solid blue;
                    width: 18px;
                    height: 18px;
                }}
                QCheckBox::indicator:checked {{
                    background-color: blue;
                    border: 2px solid blue;
                }}
                QCheckBox {{ color: {color}; font-weight: bold; padding: 2px; }}
            """)
            self.energy_group.addButton(cb, i)
            self.energy_layout.addWidget(cb)
            self.energy_checks.append(cb)
        form_layout.addLayout(self.energy_layout)
        # Buttons
        self.settings_btn = QPushButton("Settings")
        self.cancel_btn = QPushButton("Cancel")
        self.additional_done_btn = QPushButton("DONE")
        btn_hbox = QHBoxLayout()
        btn_hbox.addWidget(self.settings_btn)
        btn_hbox.addWidget(self.cancel_btn)
        form_layout.addLayout(btn_hbox)
        form_layout.addWidget(self.additional_done_btn)
        self.cancel_btn.clicked.connect(self.cancel_edit)
        self.form_group.setLayout(form_layout)
        self.form_group.setStyleSheet("""
            QGroupBox:disabled {
                background-color: #cccccc;
                color: #888;
                border: 2px solid #bbbbbb;
            }
            QGroupBox:disabled:title {
                color: #888;
            }
            QGroupBox {
                background-color: white;
            }
        """)
        self.form_group.setDisabled(True)
        self.form_group.installEventFilter(self)
        left_vbox.addWidget(self.form_group)
        left_vbox.addStretch()
        main_hlayout.addLayout(left_vbox, 1)
        # --- Right column: Today's Details, Past 3 Records, Buttons ---
        main_vlayout = QVBoxLayout()
        # Date picker and record count for details section
        details_date_layout = QHBoxLayout()
        self.details_date_edit = QDateEdit()
        self.details_date_edit.setDate(QDate.currentDate())
        self.details_date_edit.setMaximumDate(QDate.currentDate())
        details_date_layout.addWidget(QLabel("Date:"))
        details_date_layout.addWidget(self.details_date_edit)
        details_date_layout.addStretch()
        details_date_layout.addWidget(QLabel("Past records to show:"))
        self.past_count_spin = QSpinBox()
        self.past_count_spin.setMinimum(1)
        self.past_count_spin.setMaximum(100)
        self.past_count_spin.setValue(12)
        details_date_layout.addWidget(self.past_count_spin)
        main_vlayout.addLayout(details_date_layout)
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_tables)
        main_vlayout.addWidget(self.refresh_btn)
        # Today's Details Section
        self.details_group = QGroupBox("Today's Details")
        today_layout = QVBoxLayout()
        self.today_table = QTableWidget(0, 12)
        self.today_table.setHorizontalHeaderLabels(["No", "Date", "Name", "Type", "Status", "Remark", "Duration", "Attention", "Description", "Energy Level", "", "rowid"])
        self.today_table.setColumnHidden(11, True)  # Hide rowid column
        today_layout.addWidget(self.today_table)
        # Add Delete Selected button below today's table
        # self.delete_selected_today_btn = QPushButton("Delete Selected")
        # self.delete_selected_today_btn.setStyleSheet("background-color: #e53935; color: white; font-weight: bold;")
        # self.delete_selected_today_btn.clicked.connect(lambda: self.delete_selected_tasks(self.today_table, today=True))
        # today_layout.addWidget(self.delete_selected_today_btn)
        # Best, Worst, etc.
        energy_layout = QHBoxLayout()
        energy_layout.addWidget(QLabel("Best:"))
        self.best_edit = QLineEdit()
        energy_layout.addWidget(self.best_edit)
        energy_layout.addWidget(QLabel("Worst:"))
        self.worst_edit = QLineEdit()
        energy_layout.addWidget(self.worst_edit)
        today_layout.addLayout(energy_layout)
        self.details_group.setLayout(today_layout)
        main_vlayout.addWidget(self.details_group)
        # Past Details Section
        past_group = QGroupBox("Past Details")
        past_layout = QVBoxLayout()
        self.past_table = QTableWidget(12, 10)
        self.past_table.setHorizontalHeaderLabels(["No", "Date", "Name", "Type", "Status", "Remark", "Duration", "Attention", "Description", "Energy Level"])
        # self.past_table.setColumnHidden(9, True)  # We'll hide rowid after adding it
        past_layout.addWidget(self.past_table)
        # Add Delete Selected button below both tables
        self.delete_selected_btn = QPushButton("Delete Selected")
        self.delete_selected_btn.setStyleSheet("background-color: #e53935; color: white; font-weight: bold;")
        self.delete_selected_btn.clicked.connect(self.delete_selected_footer)
        past_layout.addWidget(self.delete_selected_btn)
        # Add stylesheet for grey overlay on selected rows
        self.today_table.setStyleSheet("QTableWidget::item:selected { background: #b0b0b0; }")
        self.past_table.setStyleSheet("QTableWidget::item:selected { background: #b0b0b0; }")
        past_group.setLayout(past_layout)
        main_vlayout.addWidget(past_group)
        # Buttons
        # self.done_btn = QPushButton("DONE")
        # self.clear_btn = QPushButton("CLEAR")
        # self.delete_btn = QPushButton("DELETE")
        # self.exit_btn = QPushButton("EXIT")
        # self.showall_btn = QPushButton("SHOW ALL")
        # self.close_btn = QPushButton("CLOSE")
        # btn_layout = QHBoxLayout()
        # btn_layout.addWidget(self.done_btn)
        # btn_layout.addWidget(self.clear_btn)
        # btn_layout.addWidget(self.delete_btn)
        # btn_layout.addWidget(self.exit_btn)
        # btn_layout.addWidget(self.showall_btn)
        # btn_layout.addWidget(self.close_btn)
        # main_vlayout.addLayout(btn_layout)
        main_hlayout.addLayout(main_vlayout, 3)
        self.setLayout(main_hlayout)
        # Connect signals
        self.date_edit.dateChanged.connect(self.update_no_edit)
        self.type_edit.currentIndexChanged.connect(self.update_no_edit)
        self.additional_done_btn.clicked.connect(self.save_additional)
        self.details_date_edit.dateChanged.connect(self.on_details_date_changed)
        self.past_count_spin.valueChanged.connect(self.load_past_records)
        # Remove go_btn
        # self.go_btn.clicked.connect(self.on_go_btn_clicked)
        self.desc_voice_btn.clicked.connect(self.trigger_win_h_and_focus_desc)
        self.today_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.today_table.cellDoubleClicked.connect(self.on_table_double_click)
        self.past_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.past_table.cellDoubleClicked.connect(self.on_table_double_click)
        # Deselect rows when tables lose focus
        # Data storage
        self.tasks = []
        self.past_records = []
        # Load from DB
        self.load_today_tasks()
        self.load_past_records()
        self.ensure_options_json()
        ensure_task_entry_table()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            no INTEGER,
            date TEXT,
            name TEXT,
            type TEXT,
            status TEXT,
            remark TEXT,
            duration TEXT,
            attention TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS energy (
            date TEXT PRIMARY KEY,
            level INTEGER,
            best TEXT,
            worst TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS dropdowns (key TEXT PRIMARY KEY, options TEXT)''')
        conn.commit()
        conn.close()

    def add_task(self):
        # Validate duration
        duration_val = self.duration_edit.text().strip()
        if not re.match(r'^\d{2}:\d{2}:\d{2}$', duration_val):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Duration", "Duration must be in hh:mm:ss format.")
            return
        attention_val = self.attention_edit.text().strip()
        if not re.match(r'^\(\d{1,3},\d{1,3},\d{1,3}\)$', attention_val):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Attention", "Attention must be in format (10,20,30).")
            return
        row = self.today_table.rowCount()
        self.today_table.insertRow(row)
        self.today_table.setItem(row, 0, QTableWidgetItem(str(self.no_edit.value())))
        self.today_table.setItem(row, 1, QTableWidgetItem(self.date_edit.text()))
        self.today_table.setItem(row, 2, QTableWidgetItem(self.name_edit.text()))
        self.today_table.setItem(row, 3, QTableWidgetItem(self.type_edit.currentText()))
        self.today_table.setItem(row, 4, QTableWidgetItem(self.status_edit.currentText()))
        self.today_table.setItem(row, 5, QTableWidgetItem(self.remark_edit.text()))
        self.today_table.setItem(row, 6, QTableWidgetItem(duration_val))
        self.today_table.setItem(row, 7, QTableWidgetItem(attention_val))
        self.tasks.append({
            "no": self.no_edit.value(),
            "date": self.date_edit.text(),
            "name": self.name_edit.text(),
            "type": self.type_edit.currentText(),
            "status": self.status_edit.currentText(),
            "remark": self.remark_edit.text(),
            "duration": duration_val,
            "attention": attention_val
        })
        # Save to DB
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO tasks (no, date, name, type, status, remark, duration, attention) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (self.no_edit.value(), self.date_edit.text(), self.name_edit.text(), self.type_edit.currentText(), self.status_edit.currentText(), self.remark_edit.text(), duration_val, attention_val))
        conn.commit()
        conn.close()
        self.clear_form()
        self.load_today_tasks()
        self.load_past_records()
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Saved", "Task saved successfully!")

    def delete_task(self):
        row = self.today_table.currentRow()
        if row < 0:
            return
        no = self.today_table.item(row, 0).text()
        date = self.today_table.item(row, 1).text()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM Task_Entry WHERE no=? AND data=?", (no, date))
        conn.commit()
        conn.close()
        self.today_table.removeRow(row)
        self.load_past_records()
        self.update_no_edit()

    def edit_task(self, item):
        row = item.row()
        no = self.today_table.item(row, 0).text()
        date = self.today_table.item(row, 1).text()
        name = self.today_table.item(row, 2).text()
        type_ = self.today_table.item(row, 3).text()
        status = self.today_table.item(row, 4).text()
        remark = self.today_table.item(row, 5).text()
        duration = self.today_table.item(row, 6).text()
        attention = self.today_table.item(row, 7).text()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            UPDATE Task_Entry SET name=?, type=?, status=?, remark=?, duration=?, attention=? WHERE no=? AND data=?
        """, (name, type_, status, remark, duration, attention, no, date))
        conn.commit()
        conn.close()
        self.load_past_records()

    def clear_form(self):
        self.name_edit.clear()
        self.type_edit.setCurrentIndex(0)
        self.status_edit.setCurrentIndex(0)
        self.remark_edit.clear()
        self.duration_edit.clear()
        # Clear attention checkboxes
        for cb in self.attention_checks:
            cb.setChecked(False)
        # Clear energy checkboxes
        for cb in self.energy_checks:
            cb.setChecked(False)
        self.best_edit.clear()
        self.worst_edit.clear()
        self.no_edit.setReadOnly(False)  # Allow editing No when not in edit mode
        # Do not clear all tasks for today here
        # Do not call update_no_edit() here

    def mark_done(self):
        today = self.date_edit.date().toString("yyyy-MM-dd")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE Task_Entry SET status='Done' WHERE data=?", (today,))
        conn.commit()
        conn.close()
        self.load_today_tasks()

    def exit_app(self):
        QApplication.instance().quit()

    def close_tab(self):
        self.setVisible(False)

    def show_all_tasks(self):
        # For demo: just print all tasks to console
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT no, data, name, type, status, remark FROM Task_Entry ORDER BY data DESC, no ASC")
        for row in c.fetchall():
            print(row)
        conn.close()

    def load_today_tasks(self):
        self.today_table.setRowCount(0)
        self.today_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.today_table.setSelectionMode(QAbstractItemView.MultiSelection)
        selected_date = self.details_date_edit.date().toString("yyyy-MM-dd")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT no, data, name, type, status, remark, duration, attention, descp, energy_level, rowid FROM Task_Entry WHERE data=? ORDER BY no ASC", (selected_date,))
        for row in c.fetchall():
            r = self.today_table.rowCount()
            self.today_table.insertRow(r)
            for col, val in enumerate(row[:-1]):  # Exclude rowid from display
                self.today_table.setItem(r, col, QTableWidgetItem(str(val)))
            # Store rowid as data in the last column (hidden)
            self.today_table.setItem(r, 11, QTableWidgetItem(str(row[-1])))
        conn.close()
        self.today_table.setColumnHidden(11, True)
        self.update_best_worst()

    def load_past_records(self):
        self.past_table.setRowCount(0)
        self.past_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.past_table.setSelectionMode(QAbstractItemView.MultiSelection)
        count = self.past_count_spin.value()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT no, data, name, type, status, remark, duration, attention, descp, energy_level, rowid FROM Task_Entry ORDER BY data DESC, no ASC LIMIT ?", (count,))
        for row in c.fetchall():
            r = self.past_table.rowCount()
            self.past_table.insertRow(r)
            for col, val in enumerate(row[:-1]):  # Exclude rowid from display
                self.past_table.setItem(r, col, QTableWidgetItem(str(val)))
            # Store rowid as data in the last column (hidden)
            self.past_table.setItem(r, 10, QTableWidgetItem(str(row[-1])))
        conn.close()
        # Hide the rowid column
        self.past_table.setColumnHidden(10, True)

    def save_additional(self):
        # When DONE is pressed, add the task to the database
        type_val = self.type_edit.currentText()
        status_val = self.status_edit.currentText()
        date_val = self.date_edit.date().toString("yyyy-MM-dd")
        name_val = self.name_edit.text()
        remark_val = self.remark_edit.text()
        duration_val = self.duration_edit.text()
        descp_val = self.description_edit.toPlainText()
        # Attention: get checked index (0-4)
        attention_val = None
        for i, cb in enumerate(self.attention_checks):
            if cb.isChecked():
                attention_val = i
                break
        # Energy: get checked index (0-2)
        energy_val = None
        for i, cb in enumerate(self.energy_checks):
            if cb.isChecked():
                energy_val = i
                break
        # Validation: all fields except descp must be filled
        if not name_val or not type_val or not status_val or not remark_val or not duration_val or attention_val is None or energy_val is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Missing Fields", "All fields except Description must be filled.")
            return
        if not duration_val or not duration_val.isdigit() or int(duration_val) < 1:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Duration", "Duration must be a positive integer (minutes).")
            return
        if self.is_edit_mode:
            rowid = self.editing_task_id
            if not rowid:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Edit Error", "Cannot update: missing rowid. Please select a valid row to edit.")
                self.is_edit_mode = False
                self.editing_task_id = None
                self.clear_form()
                self.form_group.setDisabled(True)
                return
            # Update existing using rowid
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''UPDATE Task_Entry SET no=?, data=?, name=?, type=?, status=?, remark=?, duration=?, attention=?, descp=?, energy_level=? WHERE rowid=?''',
                      (self.no_edit.value(), date_val, name_val, type_val, status_val, remark_val, duration_val, attention_val, descp_val, energy_val, rowid))
            conn.commit()
            conn.close()
            self.is_edit_mode = False
            self.editing_task_id = None
            self.form_group.setTitle("Task Entry")
            self.load_today_tasks()
            self.load_past_records()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Saved", "Task updated successfully!")
            self.clear_form()
            self.form_group.setDisabled(True)
            return  # Prevent insert logic from running after update
        else:
            # Insert new
            no_val = self.no_edit.value()
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''INSERT INTO Task_Entry (no, data, name, type, status, remark, duration, attention, descp, energy_level) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (no_val, date_val, name_val, type_val, status_val, remark_val, duration_val, attention_val, descp_val, energy_val))
            conn.commit()
            conn.close()
            self.load_today_tasks()
            self.load_past_records()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Saved", "Task saved successfully!")
            self.update_no_edit()  # Only update No after adding a new entry
            self.clear_form()
            self.form_group.setDisabled(True)
            self.is_edit_mode = False
            self.editing_task_id = None
            self.form_group.setTitle("Task Entry")

    def open_settings_dialog(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QLineEdit, QMessageBox
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Dropdown Options")
        layout = QVBoxLayout()
        # Type options
        layout.addWidget(QLabel("Type Options:"))
        type_list = QListWidget()
        type_options = self.load_dropdown_options('type')
        type_list.addItems(type_options)
        layout.addWidget(type_list)
        type_input = QLineEdit()
        layout.addWidget(type_input)
        add_type_btn = QPushButton("Add Type")
        del_type_btn = QPushButton("Delete Selected Type")
        layout.addWidget(add_type_btn)
        layout.addWidget(del_type_btn)
        # Status options
        layout.addWidget(QLabel("Status Options:"))
        status_list = QListWidget()
        status_options = self.load_dropdown_options('status')
        status_list.addItems(status_options)
        layout.addWidget(status_list)
        status_input = QLineEdit()
        layout.addWidget(status_input)
        add_status_btn = QPushButton("Add Status")
        del_status_btn = QPushButton("Delete Selected Status")
        layout.addWidget(add_status_btn)
        layout.addWidget(del_status_btn)
        # Save and close
        save_btn = QPushButton("Save and Close")
        layout.addWidget(save_btn)
        dialog.setLayout(layout)
        # Add/Del logic
        def add_type():
            val = type_input.text().strip()
            if val and val not in [type_list.item(i).text() for i in range(type_list.count())]:
                type_list.addItem(val)
                type_input.clear()
        def del_type():
            for item in type_list.selectedItems():
                type_list.takeItem(type_list.row(item))
        def add_status():
            val = status_input.text().strip()
            if val and val not in [status_list.item(i).text() for i in range(status_list.count())]:
                status_list.addItem(val)
                status_input.clear()
        def del_status():
            for item in status_list.selectedItems():
                status_list.takeItem(status_list.row(item))
        add_type_btn.clicked.connect(add_type)
        del_type_btn.clicked.connect(del_type)
        add_status_btn.clicked.connect(add_status)
        del_status_btn.clicked.connect(del_status)
        def save_and_close():
            new_types = [type_list.item(i).text() for i in range(type_list.count())]
            new_statuses = [status_list.item(i).text() for i in range(status_list.count())]
            self.save_dropdown_options('type', new_types)
            self.save_dropdown_options('status', new_statuses)
            self.update_dropdowns()
            dialog.accept()
        save_btn.clicked.connect(save_and_close)
        dialog.exec()

    def ensure_options_json(self):
        if not os.path.exists(self.options_json_path):
            default_options = {
                'type': ["Work", "Personal", "Other"],
                'status': ["Pending", "In Progress", "Done"]
            }
            with open(self.options_json_path, 'w', encoding='utf-8') as f:
                json.dump(default_options, f, indent=2)

    def load_dropdown_options(self, key):
        self.ensure_options_json()
        with open(self.options_json_path, 'r', encoding='utf-8') as f:
            options = json.load(f)
        return options.get(key, [])

    def save_dropdown_options(self, key, options):
        self.ensure_options_json()
        with open(self.options_json_path, 'r', encoding='utf-8') as f:
            all_options = json.load(f)
        all_options[key] = options
        with open(self.options_json_path, 'w', encoding='utf-8') as f:
            json.dump(all_options, f, indent=2)
        self.update_dropdowns()

    def update_dropdowns(self):
        self.type_edit.clear()
        self.type_edit.addItems(self.load_dropdown_options('type'))
        self.status_edit.clear()
        self.status_edit.addItems(self.load_dropdown_options('status'))

    def update_no_edit(self):
        # Set 'no' to 1 + count of tasks for this date
        date_val = self.date_edit.date().toString("yyyy-MM-dd")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM Task_Entry WHERE data=?", (date_val,))
        count = c.fetchone()[0]
        conn.close()
        self.no_edit.setValue(count + 1)

    def refresh_tables(self):
        self.load_today_tasks()
        self.load_past_records()

    def on_details_date_changed(self):
        self.update_details_label()
        self.load_today_tasks()
        self.update_best_worst()
        self.update_no_edit()

    def on_go_btn_clicked(self):
        self.update_details_label()
        self.load_today_tasks()
        self.update_best_worst()

    def update_details_label(self):
        selected_date = self.details_date_edit.date().toString("yyyy-MM-dd")
        today = QDate.currentDate().toString("yyyy-MM-dd")
        if selected_date == today:
            self.details_group.setTitle("Today's Details")
        else:
            self.details_group.setTitle("Past Details")

    def update_best_worst(self):
        # Find best and worst task by (attention + energy_level)
        selected_date = self.details_date_edit.date().toString("yyyy-MM-dd")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT name, attention, energy_level FROM Task_Entry WHERE data=?", (selected_date,))
        tasks = c.fetchall()
        conn.close()
        if not tasks:
            self.best_edit.setText("")
            self.worst_edit.setText("")
            return
        scored = [(name, (att if att is not None else 0) + (en if en is not None else 0)) for name, att, en in tasks]
        best = max(scored, key=lambda x: x[1])
        worst = min(scored, key=lambda x: x[1])
        self.best_edit.setText(best[0])
        self.worst_edit.setText(worst[0])

    def trigger_win_h_and_focus_desc(self):
        # Trigger Win+H (voice typing) and focus the description box
        try:
            if platform.system() == 'Windows':
                import ctypes
                ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)  # Win key down
                ctypes.windll.user32.keybd_event(0x48, 0, 0, 0)  # H key down
                ctypes.windll.user32.keybd_event(0x48, 0, 2, 0)  # H key up
                ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)  # Win key up
            elif platform.system() == 'Darwin':
                subprocess.run(['osascript', '-e', 'tell application "System Events" to keystroke "h" using {command down}'])
            # On Linux, no Win+H equivalent
        except Exception:
            pass
        self.description_edit.setFocus()

    def eventFilter(self, obj, event):
        if obj == self.form_group and event.type() == QEvent.MouseButtonPress:
            if not self.form_group.isEnabled():
                self.form_group.setEnabled(True)
                self.date_edit.setDate(QDate.currentDate())
                if not self.is_edit_mode:  # Only update No for new entry
                    self.update_no_edit()
            return True
        return super().eventFilter(obj, event)

    def on_table_double_click(self, row, col):
        # Determine which table
        sender = self.sender()
        if sender == self.today_table:
            table = self.today_table
            # Column mapping for today_table
            no = table.item(row, 0).text() if table.item(row, 0) else ''
            data = table.item(row, 1).text() if table.item(row, 1) else ''
            name = table.item(row, 2).text() if table.item(row, 2) else ''
            type_ = table.item(row, 3).text() if table.item(row, 3) else ''
            status = table.item(row, 4).text() if table.item(row, 4) else ''
            remark = table.item(row, 5).text() if table.item(row, 5) else ''
            duration = table.item(row, 6).text() if table.item(row, 6) else ''
            att_val = table.item(row, 7).text() if table.item(row, 7) else ''
            try:
                attention = int(att_val)
            except (ValueError, TypeError):
                attention = 0
            descp = table.item(row, 8).text() if table.item(row, 8) else ''
            en_val = table.item(row, 9).text() if table.item(row, 9) else ''
            try:
                energy_level = int(en_val)
            except (ValueError, TypeError):
                energy_level = 0
            # Get rowid from hidden column (index 11)
            rowid = table.item(row, 11).text() if table.item(row, 11) else None
        else:
            table = self.past_table
            # Column mapping for past_table (same as today_table after fix)
            no = table.item(row, 0).text() if table.item(row, 0) else ''
            data = table.item(row, 1).text() if table.item(row, 1) else ''
            name = table.item(row, 2).text() if table.item(row, 2) else ''
            type_ = table.item(row, 3).text() if table.item(row, 3) else ''
            status = table.item(row, 4).text() if table.item(row, 4) else ''
            remark = table.item(row, 5).text() if table.item(row, 5) else ''
            duration = table.item(row, 6).text() if table.item(row, 6) else ''
            att_val = table.item(row, 7).text() if table.item(row, 7) else ''
            try:
                attention = int(att_val)
            except (ValueError, TypeError):
                attention = 0
            descp = table.item(row, 8).text() if table.item(row, 8) else ''
            en_val = table.item(row, 9).text() if table.item(row, 9) else ''
            try:
                energy_level = int(en_val)
            except (ValueError, TypeError):
                energy_level = 0
            # Get rowid from hidden column (index 10)
            rowid = table.item(row, 10).text() if table.item(row, 10) else None
        # Enable form and fill
        self.form_group.setEnabled(True)
        self.is_edit_mode = True
        self.form_group.setTitle("Task Entry (Edit Mode)")
        self.no_edit.setReadOnly(True)  # Make No read-only during edit
        try:
            self.no_edit.setValue(int(no))  # Explicitly set No to the value from the row
        except Exception:
            pass
        self.date_edit.setDate(QDate.fromString(data, "yyyy-MM-dd"))
        self.name_edit.setText(name)
        self.type_edit.setCurrentText(type_)
        self.status_edit.setCurrentText(status)
        self.remark_edit.setText(remark)
        self.duration_edit.setText(duration)
        for i, cb in enumerate(self.attention_checks):
            cb.setChecked(i == attention)
        self.description_edit.setPlainText(descp)
        for i, cb in enumerate(self.energy_checks):
            cb.setChecked(i == energy_level)
        # Store editing id (rowid)
        self.editing_task_id = rowid
        # Only update 'No' for new entry, not during edit
        # self.update_no_edit()  # REMOVE or GUARD this line

    def cancel_edit(self):
        self.clear_form()
        self.form_group.setDisabled(True)
        self.is_edit_mode = False
        self.editing_task_id = None
        self.form_group.setTitle("Task Entry")
        self.no_edit.setReadOnly(False)  # Allow editing No when not in edit mode

    def delete_task_by_rowid(self, rowid):
        reply = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this task?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("DELETE FROM Task_Entry WHERE rowid=?", (rowid,))
            conn.commit()
            conn.close()
            self.load_today_tasks()
            self.load_past_records()
            self.update_no_edit()

    def delete_selected_tasks(self, table, today=True):
        selected = table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select at least one row to delete.")
            return
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete {len(selected)} selected task(s)?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        for idx in selected:
            row = idx.row()
            # Gather all visible fields for the row
            if today:
                fields = [table.item(row, col).text() if table.item(row, col) else None for col in range(10)]
                query = ("DELETE FROM Task_Entry WHERE no=? AND data=? AND name=? AND type=? AND status=? AND remark=? "
                         "AND duration=? AND attention=? AND descp=? AND energy_level=?")
            else:
                # Past table: skip 'No' column, so shift indices
                fields = [table.item(row, col).text() if table.item(row, col) else None for col in range(9)]
                query = ("DELETE FROM Task_Entry WHERE data=? AND name=? AND type=? AND status=? AND remark=? "
                         "AND duration=? AND attention=? AND descp=? AND energy_level=?")
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(query, tuple(fields))
            conn.commit()
            conn.close()
        self.load_today_tasks()
        self.load_past_records()
        self.update_no_edit()

    def delete_selected_footer(self):
        # Determine which table is active (by focus or last clicked)
        today_selected = self.today_table.selectionModel().selectedRows()
        past_selected = self.past_table.selectionModel().selectedRows()
        if today_selected:
            table = self.today_table
            today = True
        elif past_selected:
            QMessageBox.information(self, "Not Allowed", "Deletion is only allowed for Today's Details.")
            return
        else:
            QMessageBox.information(self, "No Selection", "Please select at least one row to delete in Today's Details.")
            return
        # Store indices of selected rows before deletion
        selected_indices = sorted([idx.row() for idx in table.selectionModel().selectedRows()])
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete {len(table.selectionModel().selectedRows())} selected task(s)?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        for idx in table.selectionModel().selectedRows():
            row = idx.row()
            fields = [table.item(row, col).text() if table.item(row, col) else None for col in range(10)]
            query = ("DELETE FROM Task_Entry WHERE no=? AND data=? AND name=? AND type=? AND status=? AND remark=? "
                     "AND duration=? AND attention=? AND descp=? AND energy_level=?")
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(query, tuple(fields))
            conn.commit()
            conn.close()
        self.load_today_tasks()
        self.load_past_records()
        self.update_no_edit()
        # Restore selection to the next logical row
        row_count = table.rowCount()
        if row_count > 0:
            # Select the row after the last deleted, or the last row if at the end
            next_row = min(selected_indices[0], row_count - 1)
            table.selectRow(next_row) 