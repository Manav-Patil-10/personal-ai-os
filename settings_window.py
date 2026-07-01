#!/usr/bin/env python3
import os
from pathlib import Path
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFrame, QCheckBox, QMessageBox, QTabWidget, QWidget, QSpinBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

ENV_FILE = Path(".env")

def load_env():
    if not ENV_FILE.exists():
        return {}
    settings = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            settings[key.strip()] = value.strip()
    return settings

def save_env(settings):
    lines = [f"{k}={v}" for k, v in settings.items()]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings — Personal AI OS")
        self.setMinimumWidth(500)
        self.setModal(True)
        self.settings = load_env()
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("QDialog { background: #f8f8f6; } QWidget { background: #f8f8f6; } QTabWidget::pane { border: 1px solid #e0ded8; border-radius: 6px; background: #ffffff; } QTabBar::tab { background: #f1efea; border: 1px solid #e0ded8; padding: 8px 20px; font-size: 13px; } QTabBar::tab:selected { background: #ffffff; color: #534AB7; font-weight: 500; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 16, QFont.Medium))
        title.setStyleSheet("color: #1a1a1a;")
        layout.addWidget(title)
        tabs = QTabWidget()
        tabs.addTab(self.build_api_tab(), "API & Model")
        tabs.addTab(self.build_prefs_tab(), "Preferences")
        tabs.addTab(self.build_about_tab(), "About")
        layout.addWidget(tabs)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("QPushButton { background: #f1efea; border: 1px solid #e0ded8; border-radius: 6px; padding: 8px 20px; font-size: 13px; color: #1a1a1a; } QPushButton:hover { border-color: #534AB7; color: #534AB7; }")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Save settings")
        save_btn.setStyleSheet("QPushButton { background: #534AB7; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: 500; } QPushButton:hover { background: #3C3489; }")
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def build_api_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self.section_label("Groq API Key"))
        layout.addWidget(self.desc("Get a free key at console.groq.com/keys"))
        key_layout = QHBoxLayout()
        self.api_key_field = QLineEdit()
        self.api_key_field.setPlaceholderText("gsk_...")
        self.api_key_field.setEchoMode(QLineEdit.Password)
        self.api_key_field.setText(self.settings.get("GROQ_API_KEY", ""))
        self.api_key_field.setStyleSheet(self.inp())
        key_layout.addWidget(self.api_key_field)
        show_btn = QPushButton("Show")
        show_btn.setStyleSheet("QPushButton { background: #f1efea; border: 1px solid #e0ded8; border-radius: 6px; padding: 8px 14px; font-size: 12px; } QPushButton:hover { border-color: #534AB7; color: #534AB7; }")
        show_btn.setCheckable(True)
        show_btn.toggled.connect(lambda c: self.api_key_field.setEchoMode(QLineEdit.Normal if c else QLineEdit.Password))
        show_btn.toggled.connect(lambda c: show_btn.setText("Hide" if c else "Show"))
        key_layout.addWidget(show_btn)
        layout.addLayout(key_layout)
        layout.addWidget(self.section_label("Cloud Model"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["llama-3.3-70b-versatile","llama-3.1-8b-instant","mixtral-8x7b-32768"])
        idx = self.model_combo.findText(self.settings.get("GROQ_MODEL","llama-3.3-70b-versatile"))
        if idx >= 0: self.model_combo.setCurrentIndex(idx)
        self.model_combo.setStyleSheet(self.inp())
        layout.addWidget(self.model_combo)
        layout.addWidget(self.section_label("Local Model (Ollama)"))
        self.local_model_field = QLineEdit()
        self.local_model_field.setText(self.settings.get("OLLAMA_MODEL","llama3.2"))
        self.local_model_field.setStyleSheet(self.inp())
        layout.addWidget(self.local_model_field)
        layout.addStretch()
        return tab

    def build_prefs_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self.section_label("Memory — history limit"))
        hl = QHBoxLayout()
        self.history_spin = QSpinBox()
        self.history_spin.setRange(1,50)
        self.history_spin.setValue(int(self.settings.get("HISTORY_LIMIT","10")))
        self.history_spin.setStyleSheet(self.inp())
        hl.addWidget(self.history_spin)
        hl.addStretch()
        layout.addLayout(hl)
        layout.addWidget(self.section_label("Briefing time (HH:MM)"))
        self.briefing_time_field = QLineEdit()
        self.briefing_time_field.setText(self.settings.get("BRIEFING_TIME","08:00"))
        self.briefing_time_field.setFixedWidth(80)
        self.briefing_time_field.setStyleSheet(self.inp())
        layout.addWidget(self.briefing_time_field)
        layout.addWidget(self.section_label("Privacy"))
        self.use_local_check = QCheckBox("Use local model by default (requires Ollama)")
        self.use_local_check.setChecked(self.settings.get("USE_LOCAL","false").lower()=="true")
        self.use_local_check.setStyleSheet("font-size: 13px; color: #1a1a1a;")
        layout.addWidget(self.use_local_check)
        layout.addStretch()
        return tab

    def build_about_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        about = QLabel("<h3 style='color:#534AB7'>Personal AI OS</h3><p style='color:#666;font-size:13px'>A self-hosted AI operating system that remembers you, learns from your notes, manages your tasks.</p><br><p style='color:#666;font-size:12px'><b>Version:</b> 1.0.0<br><b>Built by:</b> Manav Patil<br><b>GitHub:</b> <a href='https://github.com/Manav-Patil-10/personal-ai-os' style='color:#534AB7'>github.com/Manav-Patil-10/personal-ai-os</a><br><b>License:</b> MIT</p>")
        about.setTextFormat(Qt.RichText)
        about.setOpenExternalLinks(True)
        about.setWordWrap(True)
        layout.addWidget(about)
        layout.addStretch()
        return tab

    def save_settings(self):
        self.settings["GROQ_API_KEY"] = self.api_key_field.text().strip()
        self.settings["GROQ_MODEL"] = self.model_combo.currentText()
        self.settings["OLLAMA_MODEL"] = self.local_model_field.text().strip() or "llama3.2"
        self.settings["HISTORY_LIMIT"] = str(self.history_spin.value())
        self.settings["BRIEFING_TIME"] = self.briefing_time_field.text().strip() or "08:00"
        self.settings["USE_LOCAL"] = "true" if self.use_local_check.isChecked() else "false"
        save_env(self.settings)
        for k, v in self.settings.items():
            os.environ[k] = v
        QMessageBox.information(self, "Saved", "Settings saved successfully.")
        self.accept()

    def section_label(self, text):
        l = QLabel(text)
        l.setFont(QFont("Segoe UI", 12, QFont.Medium))
        l.setStyleSheet("color: #1a1a1a; margin-top: 4px;")
        return l

    def desc(self, text):
        l = QLabel(text)
        l.setStyleSheet("color: #888; font-size: 12px;")
        return l

    def inp(self):
        return "QLineEdit, QComboBox, QSpinBox { background: #fff; border: 1px solid #e0ded8; border-radius: 6px; padding: 8px 12px; font-size: 13px; color: #1a1a1a; } QLineEdit:focus { border-color: #534AB7; }"
