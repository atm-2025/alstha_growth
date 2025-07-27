import os
import threading
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, 
    QGroupBox, QSlider, QComboBox, QMessageBox, QProgressBar, QFrame,
    QStackedWidget
)
from PySide6.QtCore import Qt, QTimer, QUrl, QThread, Signal, QMutex, QWaitCondition
from PySide6.QtWidgets import QStyle
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from modules.streaming_player import StreamingMediaPlayer
from modules.utils import format_time

class SafeMediaWorker(QThread):
    """Thread-safe media worker for loading files"""
    loaded = Signal(str)  # file_path
    error = Signal(str)   # error_message
    progress = Signal(str)  # progress message
    
    def __init__(self, file_path, file_type="video"):
        super().__init__()
        self.file_path = file_path
        self.file_type = file_type
        self._is_running = True
        self._mutex = QMutex()
        self._condition = QWaitCondition()
    
    def run(self):
        try:
            self._mutex.lock()
            if not self._is_running:
                self._mutex.unlock()
                return
                
            self.progress.emit(f"Checking {self.file_type} file...")
                
            # Check if file exists
            if not os.path.exists(self.file_path):
                self.error.emit(f"{self.file_type.capitalize()} file not found: {self.file_path}")
                self._mutex.unlock()
                return
            
            # Check file size
            file_size = os.path.getsize(self.file_path)
            max_size = 500 * 1024 * 1024  # 500MB limit
            
            if file_size > max_size:
                size_mb = file_size // (1024 * 1024)
                self.error.emit(f"{self.file_type.capitalize()} file is too large ({size_mb}MB). Please use a smaller file.")
                self._mutex.unlock()
                return
            
            # Test file readability
            self.progress.emit(f"Testing {self.file_type} file access...")
            try:
                with open(self.file_path, 'rb') as f:
                    f.read(1024)  # Read first 1KB
            except Exception as e:
                self.error.emit(f"Cannot read {self.file_type} file: {str(e)}")
                self._mutex.unlock()
                return
            
            if self._is_running:
                self.progress.emit(f"{self.file_type.capitalize()} file ready for playback")
                self.loaded.emit(self.file_path)
                
            self._mutex.unlock()
                
        except Exception as e:
            if self._mutex.tryLock():
                self.error.emit(f"Error loading {self.file_type}: {str(e)}")
                self._mutex.unlock()
    
    def stop(self):
        """Safely stop the worker"""
        self._mutex.lock()
        self._is_running = False
        self._condition.wakeAll()
        self._mutex.unlock()
        
        # Give thread time to finish gracefully
        if self.isRunning():
            self.wait(2000)  # Wait up to 2 seconds
            if self.isRunning():
                self.terminate()
                self.wait(1000)  # Wait another second after terminate

class PlayerTab(QWidget):
    def __init__(self):
        super().__init__()
        
        # Thread safety
        self._audio_mutex = QMutex()
        self._video_mutex = QMutex()
        self._audio_worker = None
        self._video_worker = None
        
        # State flags
        self._audio_switching = False
        self._video_switching = False
        self._audio_loaded = False
        self._video_loaded = False
        
        # Safety timer to prevent stuck states
        self._safety_timer = QTimer()
        self._safety_timer.timeout.connect(self._check_stuck_states)
        self._safety_timer.start(5000)  # Check every 5 seconds
        
        # Directories
        self.audio_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../web_app/files/Audio'))
        self.video_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../web_app/files/Video'))
        
        # Ensure directories exist
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)
        
        # Initialize UI
        self._init_ui()
        self._init_players()
        self._load_file_lists()
        # File lists enabled at startup
        self.audio_list.setEnabled(True)
        self.video_list.setEnabled(True)
        # Initialize player mode
        self.current_mode = "standard"
        self.switch_player_mode("Standard Player")
        self._audio_list_unlocked = False
        self._video_list_unlocked = False
    
    def _check_stuck_states(self):
        """Check for stuck states and trigger emergency cleanup if needed"""
        try:
            # Check if switching flags are stuck for too long
            if self._audio_switching or self._video_switching:
                # Check if workers are actually running
                audio_worker_running = (self._audio_worker and self._audio_worker.isRunning())
                video_worker_running = (self._video_worker and self._video_worker.isRunning())
                
                # If flags are set but no workers are running, we're stuck
                if (self._audio_switching and not audio_worker_running) or \
                   (self._video_switching and not video_worker_running):
                    print("Detected stuck state, triggering emergency cleanup")
                    self._emergency_cleanup()
                    
        except Exception as e:
            print(f"Error in stuck state check: {e}")
            # If we can't even check, trigger emergency cleanup
            self._emergency_cleanup()
    
    def _init_ui(self):
        """Initialize the user interface"""
        # Apply white/light theme
        self.setStyleSheet('''
            QWidget {
                background: #ffffff;
                color: #222222;
                font-size: 15px;
            }
            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin-top: 10px;
                background: #fafafa;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: #444444;
                font-weight: bold;
            }
            QPushButton {
                background: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px 12px;
                color: #222222;
            }
            QPushButton:checked, QPushButton:pressed {
                background: #e0e0e0;
                border: 1px solid #aaaaaa;
            }
            QPushButton:hover {
                background: #f0f0f0;
            }
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: #eee;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #cccccc;
                border: 1px solid #888;
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QListWidget {
                background: #ffffff;
                border: 1px solid #cccccc;
            }
            QLabel {
                color: #222222;
            }
            QProgressBar {
                background: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
                color: #222222;
            }
        ''')
        layout = QVBoxLayout()
        
        # --- Player Mode Switch (Offline/Online) ---
        self.mode_switch_layout = QHBoxLayout()
        self.offline_btn = QPushButton("Offline")
        self.online_btn = QPushButton("Online")
        self.offline_btn.setCheckable(True)
        self.online_btn.setCheckable(True)
        self.offline_btn.setChecked(True)
        self.mode_switch_layout.addWidget(self.offline_btn)
        self.mode_switch_layout.addWidget(self.online_btn)
        self.mode_switch_layout.addStretch()
        layout.addLayout(self.mode_switch_layout)
        self.offline_btn.clicked.connect(lambda: self.set_player_mode("offline"))
        self.online_btn.clicked.connect(lambda: self.set_player_mode("online"))

        # --- Offline/Online Stacked Layout ---
        from PySide6.QtWidgets import QStackedWidget, QLabel
        self.mode_stack = QStackedWidget()
        layout.addWidget(self.mode_stack)

        # --- Offline Widget (current player UI) ---
        self.offline_widget = QWidget()
        offline_layout = QVBoxLayout()

        # Audio Section
        audio_group = QGroupBox("Audio Player")
        audio_layout = QVBoxLayout()
        self.audio_list = QListWidget()
        self.audio_list.setMaximumHeight(150)
        audio_layout.addWidget(QLabel("Audio Files:"))
        audio_layout.addWidget(self.audio_list)
        self.audio_standard_container = QFrame()
        audio_standard_layout = QHBoxLayout()
        self.audio_play_btn = QPushButton("▶")
        self.audio_pause_btn = QPushButton("⏸")
        self.audio_stop_btn = QPushButton("⏹")
        self.audio_slider = QSlider(Qt.Horizontal)
        self.audio_time_label = QLabel("00:00 / 00:00")
        self.audio_volume = QSlider(Qt.Horizontal)
        self.audio_volume.setMaximum(100)
        self.audio_volume.setValue(50)
        audio_standard_layout.addWidget(self.audio_play_btn)
        audio_standard_layout.addWidget(self.audio_pause_btn)
        audio_standard_layout.addWidget(self.audio_stop_btn)
        audio_standard_layout.addWidget(self.audio_slider)
        audio_standard_layout.addWidget(self.audio_time_label)
        audio_standard_layout.addWidget(QLabel("Vol"))
        audio_standard_layout.addWidget(self.audio_volume)
        self.audio_standard_container.setLayout(audio_standard_layout)
        audio_layout.addWidget(self.audio_standard_container)
        self.audio_streaming_player = StreamingMediaPlayer("audio")
        self.audio_streaming_player.setVisible(False)
        audio_layout.addWidget(self.audio_streaming_player)
        audio_group.setLayout(audio_layout)
        offline_layout.addWidget(audio_group)

        # Video Section
        video_group = QGroupBox("Video Player")
        video_layout = QVBoxLayout()
        self.video_list = QListWidget()
        self.video_list.setMaximumHeight(150)
        video_layout.addWidget(QLabel("Video Files:"))
        video_layout.addWidget(self.video_list)
        self.video_standard_container = QFrame()
        video_standard_layout = QHBoxLayout()
        self.video_play_btn = QPushButton("▶")
        self.video_pause_btn = QPushButton("⏸")
        self.video_stop_btn = QPushButton("⏹")
        # Full Screen Toggle Button
        self.video_fullscreen_btn = QPushButton("⛶")
        self.video_fullscreen_btn.setToolTip("Full Screen")
        self.video_fullscreen_btn.setFixedWidth(32)
        self.video_fullscreen_btn.clicked.connect(self.toggle_video_fullscreen)
        self.video_slider = QSlider(Qt.Horizontal)
        self.video_time_label = QLabel("00:00 / 00:00")
        self.video_volume = QSlider(Qt.Horizontal)
        self.video_volume.setMaximum(100)
        self.video_volume.setValue(50)
        video_standard_layout.addWidget(self.video_play_btn)
        video_standard_layout.addWidget(self.video_pause_btn)
        video_standard_layout.addWidget(self.video_stop_btn)
        video_standard_layout.addWidget(self.video_fullscreen_btn)
        video_standard_layout.addWidget(self.video_slider)
        video_standard_layout.addWidget(self.video_time_label)
        video_standard_layout.addWidget(QLabel("Vol"))
        video_standard_layout.addWidget(self.video_volume)
        self.video_standard_container.setLayout(video_standard_layout)
        video_layout.addWidget(self.video_standard_container)
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(240)
        video_layout.addWidget(self.video_widget)
        self.video_streaming_player = StreamingMediaPlayer("video")
        self.video_streaming_player.setVisible(False)
        video_layout.addWidget(self.video_streaming_player)
        video_group.setLayout(video_layout)
        offline_layout.addWidget(video_group)

        # Progress bar for loading
        self.loading_progress = QProgressBar()
        self.loading_progress.setVisible(False)
        offline_layout.addWidget(self.loading_progress)
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        offline_layout.addWidget(self.status_label)
        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh Files")
        refresh_btn.clicked.connect(self._load_file_lists)
        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addStretch()
        offline_layout.addLayout(refresh_layout)
        self.offline_widget.setLayout(offline_layout)
        self.mode_stack.addWidget(self.offline_widget)

        # --- Online Widget (Coming Soon) ---
        self.online_widget = QWidget()
        online_layout = QVBoxLayout()
        coming_soon_label = QLabel("<h2>Coming Soon</h2>")
        coming_soon_label.setAlignment(Qt.AlignCenter)
        online_layout.addWidget(coming_soon_label)
        self.online_widget.setLayout(online_layout)
        self.mode_stack.addWidget(self.online_widget)

        self.setLayout(layout)
        self.set_player_mode("offline")

    def set_player_mode(self, mode):
        if mode == "offline":
            self.mode_stack.setCurrentWidget(self.offline_widget)
            self.offline_btn.setChecked(True)
            self.online_btn.setChecked(False)
        else:
            self.mode_stack.setCurrentWidget(self.online_widget)
            self.offline_btn.setChecked(False)
            self.online_btn.setChecked(True)

    def toggle_video_fullscreen(self):
        if not hasattr(self, '_video_fullscreen'):
            self._video_fullscreen = False
        if not self._video_fullscreen:
            self._video_fullscreen = True
            self._prev_video_parent = self.video_widget.parentWidget()
            self._prev_video_geometry = self.video_widget.geometry()
            self.video_widget.setParent(None)
            self._fullscreen_window = QWidget()
            self._fullscreen_window.setWindowFlags(Qt.Window)
            self._fullscreen_window.setWindowTitle("Full Screen Video")
            layout = QVBoxLayout(self._fullscreen_window)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.video_widget)
            self._fullscreen_window.showFullScreen()
            self._fullscreen_window.show()
            self._fullscreen_window.keyPressEvent = self._exit_fullscreen_on_escape
            self._fullscreen_window.mouseDoubleClickEvent = self._exit_fullscreen_on_escape
        else:
            self._exit_video_fullscreen()

    def _exit_video_fullscreen(self):
        if hasattr(self, '_fullscreen_window') and self._fullscreen_window:
            self._fullscreen_window.close()
            self.video_widget.setParent(self._prev_video_parent)
            self._prev_video_parent.layout().addWidget(self.video_widget)
            self.video_widget.setGeometry(self._prev_video_geometry)
            self._video_fullscreen = False

    def _exit_fullscreen_on_escape(self, event):
        from PySide6.QtGui import QKeyEvent
        if isinstance(event, QKeyEvent) and event.key() == Qt.Key_Escape:
            self._exit_video_fullscreen()
        else:
            self._exit_video_fullscreen()
    
    def _init_players(self):
        """Initialize media players"""
        # Audio player
        self.audio_player = QMediaPlayer()
        self.audio_audio_output = QAudioOutput()
        self.audio_player.setAudioOutput(self.audio_audio_output)
        
        # Video player
        self.video_player = QMediaPlayer()
        self.video_player.setVideoOutput(self.video_widget)
        self.video_audio_output = QAudioOutput()
        self.video_player.setAudioOutput(self.video_audio_output)
        
        # Connect signals
        self._connect_audio_signals()
        self._connect_video_signals()
        
        # Connect list clicks
        self.audio_list.itemClicked.connect(self._safe_play_audio)
        self.video_list.itemClicked.connect(self._safe_play_video)
    
    def _connect_audio_signals(self):
        """Connect audio player signals"""
        self.audio_play_btn.clicked.connect(self.audio_player.play)
        self.audio_pause_btn.clicked.connect(self.audio_player.pause)
        self.audio_stop_btn.clicked.connect(self.audio_player.stop)
        self.audio_stop_btn.clicked.connect(self._on_audio_stop)
        self.audio_slider.sliderMoved.connect(self._seek_audio)
        self.audio_player.positionChanged.connect(self._update_audio_slider)
        self.audio_player.durationChanged.connect(self._update_audio_duration)
        self.audio_volume.valueChanged.connect(lambda v: self.audio_audio_output.setVolume(v/100))
        self.audio_player.errorOccurred.connect(self._on_audio_error)
        self.audio_audio_output.setVolume(self.audio_volume.value()/100)
        # Connect to stateChanged to detect when stopped
        self.audio_player.playbackStateChanged.connect(self._on_audio_playback_state_changed)
    
    def _connect_video_signals(self):
        """Connect video player signals"""
        self.video_play_btn.clicked.connect(self.video_player.play)
        self.video_pause_btn.clicked.connect(self.video_player.pause)
        self.video_stop_btn.clicked.connect(self.video_player.stop)
        self.video_stop_btn.clicked.connect(self._on_video_stop)
        self.video_slider.sliderMoved.connect(self._seek_video)
        self.video_player.positionChanged.connect(self._update_video_slider)
        self.video_player.durationChanged.connect(self._update_video_duration)
        self.video_volume.valueChanged.connect(lambda v: self.video_audio_output.setVolume(v/100))
        self.video_player.errorOccurred.connect(self._on_video_error)
        self.video_player.mediaStatusChanged.connect(self._on_video_media_status_changed)
        self.video_audio_output.setVolume(self.video_volume.value()/100)
        # Connect to stateChanged to detect when stopped
        self.video_player.playbackStateChanged.connect(self._on_video_playback_state_changed)
    
    def _load_file_lists(self):
        """Load audio and video file lists"""
        try:
            # Load audio files
            audio_files = []
            if os.path.exists(self.audio_dir):
                audio_files = [f for f in os.listdir(self.audio_dir) 
                             if os.path.isfile(os.path.join(self.audio_dir, f))]
            
            self.audio_list.clear()
            self.audio_list.addItems(audio_files)
            
            # Load video files
            video_files = []
            if os.path.exists(self.video_dir):
                video_files = [f for f in os.listdir(self.video_dir) 
                             if os.path.isfile(os.path.join(self.video_dir, f))]
            
            self.video_list.clear()
            self.video_list.addItems(video_files)
            
            self.status_label.setText(f"Loaded {len(audio_files)} audio, {len(video_files)} video files")
            
        except Exception as e:
            self.status_label.setText(f"Error loading files: {str(e)}")
            print(f"Error loading file lists: {e}")
    
    def _safe_play_audio(self, item):
        """Safely play audio file with thread safety and a short delay after stop to prevent unresponsiveness"""
        if self._audio_switching:
            print("Audio switching already in progress, ignoring click")
            return
        self._audio_switching = True
        self.status_label.setText("Loading audio...")
        try:
            file_path = os.path.join(self.audio_dir, item.text())
            # Always stop current audio before playing new one
            self.audio_player.stop()
            self.audio_player.setSource(QUrl())
            import gc
            gc.collect()
            # Wait 200ms before loading the new file
            from PySide6.QtCore import QTimer
            def play_after_delay():
                if self.current_mode == "streaming":
                    self.audio_streaming_player.stream_file(file_path)
                    self._audio_switching = False
                    self.status_label.setText("Audio streaming started")
                else:
                    self._immediate_audio_switch(file_path)
            QTimer.singleShot(200, play_after_delay)
        except Exception as e:
            self._audio_switching = False
            self.status_label.setText(f"Audio error: {str(e)}")
            QMessageBox.critical(self, "Audio Error", f"Failed to play audio: {str(e)}")

    def _safe_play_video(self, item):
        """Safely play video file with thread safety and a short delay after stop to prevent unresponsiveness"""
        if self._video_switching:
            print("Video switching already in progress, ignoring click")
            return
        self._video_switching = True
        self.status_label.setText("Loading video...")
        self.loading_progress.setVisible(True)
        try:
            file_path = os.path.join(self.video_dir, item.text())
            # Always stop current video before playing new one
            self.video_player.stop()
            self.video_player.setSource(QUrl())
            import gc
            gc.collect()
            # Wait 200ms before loading the new file
            from PySide6.QtCore import QTimer
            def play_after_delay():
                if self.current_mode == "streaming":
                    self.video_streaming_player.stream_file(file_path)
                    self._video_switching = False
                    self.status_label.setText("Video streaming started")
                    self.loading_progress.setVisible(False)
                else:
                    self._immediate_video_switch(file_path)
            QTimer.singleShot(200, play_after_delay)
        except Exception as e:
            self._video_switching = False
            self.status_label.setText(f"Video error: {str(e)}")
            self.loading_progress.setVisible(False)
            QMessageBox.critical(self, "Video Error", f"Failed to play video: {str(e)}")
    
    def _immediate_audio_switch(self, file_path):
        """Immediately switch audio without background worker for better responsiveness"""
        try:
            # Stop current playback
            self.audio_player.stop()
            self.audio_player.setSource(QUrl())
            self.audio_slider.setValue(0)
            self.audio_time_label.setText("00:00 / 00:00")
            # Only disable if not unlocked
            if not self._audio_list_unlocked:
                self.audio_list.setEnabled(False)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            # File size check removed
            self.audio_player.setSource(QUrl.fromLocalFile(file_path))
            self.audio_player.play()
            self._audio_switching = False
            self._audio_loaded = True
            self.status_label.setText("Audio playing")
        except Exception as e:
            self._audio_switching = False
            self.status_label.setText(f"Audio play error: {str(e)}")
            QMessageBox.critical(self, "Audio Error", f"Failed to play audio: {str(e)}")
            self.audio_list.setEnabled(True)

    def _immediate_video_switch(self, file_path):
        """Immediately switch video without background worker for better responsiveness and resource cleanup"""
        try:
            self.video_player.stop()
            self.video_player.setSource(QUrl())
            import gc
            gc.collect()
            self.video_slider.setValue(0)
            self.video_time_label.setText("00:00 / 00:00")
            # Only disable if not unlocked
            if not self._video_list_unlocked:
                self.video_list.setEnabled(False)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Video file not found: {file_path}")
            # File size check removed
            self.video_player.setSource(QUrl.fromLocalFile(file_path))
            self.video_player.play()
            self._video_switching = False
            self._video_loaded = True
            self.status_label.setText("Video playing")
            self.loading_progress.setVisible(False)
        except Exception as e:
            self._video_switching = False
            self.status_label.setText(f"Video play error: {str(e)}")
            self.loading_progress.setVisible(False)
            QMessageBox.critical(self, "Video Error", f"Failed to play video: {str(e)}")
            self.video_list.setEnabled(True)

    def _load_audio_in_background(self, file_path):
        """Load audio file in background thread (fallback method)"""
        # Stop any existing worker
        self._stop_audio_worker()
        
        # Create and start new worker
        self._audio_worker = SafeMediaWorker(file_path, "audio")
        self._audio_worker.loaded.connect(self._on_audio_loaded)
        self._audio_worker.error.connect(self._on_audio_error_worker)
        self._audio_worker.progress.connect(self._update_loading_progress)
        self._audio_worker.start()
        
        # Set timeout
        QTimer.singleShot(15000, self._check_audio_timeout)
    
    def _load_video_in_background(self, file_path):
        """Load video file in background thread (fallback method)"""
        # Stop any existing worker
        self._stop_video_worker()
        
        # Create and start new worker
        self._video_worker = SafeMediaWorker(file_path, "video")
        self._video_worker.loaded.connect(self._on_video_loaded)
        self._video_worker.error.connect(self._on_video_error_worker)
        self._video_worker.progress.connect(self._update_loading_progress)
        self._video_worker.start()
        
        # Set timeout
        QTimer.singleShot(15000, self._check_video_timeout)
    
    def _stop_audio_worker(self):
        """Stop audio worker thread"""
        if self._audio_worker and self._audio_worker.isRunning():
            self._audio_worker.stop()
            self._audio_worker = None
    
    def _stop_video_worker(self):
        """Stop video worker thread"""
        if self._video_worker and self._video_worker.isRunning():
            self._video_worker.stop()
            self._video_worker = None
    
    def _on_audio_loaded(self, file_path):
        try:
            self.audio_player.stop()
            self.audio_player.setSource(QUrl.fromLocalFile(file_path))
            self.audio_player.play()
            self._audio_switching = False
            self._audio_loaded = True
            self.status_label.setText("Audio playing")
            # Disable file list during playback
            self.audio_list.setEnabled(False)
        except Exception as e:
            self._audio_switching = False
            self.status_label.setText(f"Audio play error: {str(e)}")
            QMessageBox.critical(self, "Audio Error", f"Failed to play audio: {str(e)}")
            self.audio_list.setEnabled(True)

    def _on_video_loaded(self, file_path):
        try:
            self.video_player.stop()
            self.video_player.setSource(QUrl.fromLocalFile(file_path))
            self.video_player.play()
            self._video_switching = False
            self._video_loaded = True
            self.status_label.setText("Video playing")
            self.loading_progress.setVisible(False)
            # Disable file list during playback
            self.video_list.setEnabled(False)
        except Exception as e:
            self._video_switching = False
            self.status_label.setText(f"Video play error: {str(e)}")
            self.loading_progress.setVisible(False)
            QMessageBox.critical(self, "Video Error", f"Failed to play video: {str(e)}")
            self.video_list.setEnabled(True)

    def _on_audio_error_worker(self, error_message):
        """Called when audio loading fails in worker"""
        self._audio_switching = False
        self.status_label.setText(f"Audio error: {error_message}")
        QMessageBox.warning(self, "Audio Load Error", error_message)
    
    def _on_video_error_worker(self, error_message):
        """Called when video loading fails in worker"""
        self._video_switching = False
        self.status_label.setText(f"Video error: {error_message}")
        self.loading_progress.setVisible(False)
        QMessageBox.warning(self, "Video Load Error", error_message)
    
    def _check_audio_timeout(self):
        """Check if audio loading has timed out"""
        if self._audio_worker and self._audio_worker.isRunning():
            self._stop_audio_worker()
            self._audio_switching = False
            self.status_label.setText("Audio loading timed out")
            QMessageBox.warning(self, "Audio Timeout", "Audio loading took too long. Please try again.")
    
    def _check_video_timeout(self):
        """Check if video loading has timed out"""
        if self._video_worker and self._video_worker.isRunning():
            self._stop_video_worker()
            self._video_switching = False
            self.status_label.setText("Video loading timed out")
            self.loading_progress.setVisible(False)
            QMessageBox.warning(self, "Video Timeout", "Video loading took too long. Please try again.")
    
    def _update_loading_progress(self, message):
        """Update loading progress message"""
        self.status_label.setText(message)
    
    def _seek_audio(self, pos):
        """Seek audio position"""
        try:
            if self.audio_player.duration() > 0:
                self.audio_player.setPosition(int(pos/100 * self.audio_player.duration()))
        except Exception as e:
            print(f"Audio seek error: {e}")
    
    def _seek_video(self, pos):
        """Seek video position"""
        try:
            if self.video_player.duration() > 0:
                self.video_player.setPosition(int(pos/100 * self.video_player.duration()))
        except Exception as e:
            print(f"Video seek error: {e}")
    
    def _update_audio_slider(self, position):
        """Update audio slider position"""
        try:
            duration = self.audio_player.duration()
            if duration > 0:
                percent = int(position / duration * 100)
                self.audio_slider.blockSignals(True)
                self.audio_slider.setValue(percent)
                self.audio_slider.blockSignals(False)
                self.audio_time_label.setText(f"{format_time(position)} / {format_time(duration)}")
        except Exception as e:
            print(f"Audio slider update error: {e}")
    
    def _update_video_slider(self, position):
        """Update video slider position"""
        try:
            duration = self.video_player.duration()
            if duration > 0:
                percent = int(position / duration * 100)
                self.video_slider.blockSignals(True)
                self.video_slider.setValue(percent)
                self.video_slider.blockSignals(False)
                self.video_time_label.setText(f"{format_time(position)} / {format_time(duration)}")
        except Exception as e:
            print(f"Video slider update error: {e}")
    
    def _update_audio_duration(self, duration):
        """Update audio duration display"""
        try:
            position = self.audio_player.position()
            if duration > 0:
                percent = int(position / duration * 100)
                self.audio_slider.blockSignals(True)
                self.audio_slider.setValue(percent)
                self.audio_slider.blockSignals(False)
                self.audio_time_label.setText(f"{format_time(position)} / {format_time(duration)}")
        except Exception as e:
            print(f"Audio duration update error: {e}")
    
    def _update_video_duration(self, duration):
        """Update video duration display"""
        try:
            position = self.video_player.position()
            if duration > 0:
                percent = int(position / duration * 100)
                self.video_slider.blockSignals(True)
                self.video_slider.setValue(percent)
                self.video_slider.blockSignals(False)
                self.video_time_label.setText(f"{format_time(position)} / {format_time(duration)}")
        except Exception as e:
            print(f"Video duration update error: {e}")
    
    def _on_audio_error(self, error, error_string):
        self.status_label.setText(f"Audio error: {error_string}")
        QMessageBox.critical(self, "Audio Error", f"Audio playback error: {error_string}")
        self._audio_switching = False
        # Re-enable file list on error
        self.audio_list.setEnabled(True)

    def _on_video_error(self, error, error_string):
        self.status_label.setText(f"Video error: {error_string}")
        QMessageBox.critical(
            self,
            "Video Error",
            f"Video playback error: {error_string}\n\nThis may be due to a corrupted or unsupported video file. "
            "Try re-encoding the video with FFmpeg or use a different file."
        )
        self._video_switching = False
        self.loading_progress.setVisible(False)
        # Re-enable file list on error
        self.video_list.setEnabled(True)
    
    def _on_video_media_status_changed(self, status):
        """Handle video media status changes"""
        try:
            if status == QMediaPlayer.LoadedMedia:
                self.status_label.setText("Video loaded successfully")
            elif status == QMediaPlayer.InvalidMedia:
                self.status_label.setText("Invalid video file")
                QMessageBox.warning(self, "Invalid Media", "The selected video file is not supported or corrupted.")
                self._video_switching = False
                self.loading_progress.setVisible(False)
            elif status == QMediaPlayer.NoMedia:
                self.video_slider.setValue(0)
                self.video_time_label.setText("00:00 / 00:00")
        except Exception as e:
            print(f"Video media status change error: {e}")
    
    def switch_player_mode(self, mode):
        """Switch between standard and streaming player modes"""
        if mode == "Standard Player":
            self.current_mode = "standard"
            # Show standard containers
            self.audio_standard_container.setVisible(True)
            self.video_standard_container.setVisible(True)
            self.video_widget.setVisible(True)
            # Hide streaming players
            self.audio_streaming_player.setVisible(False)
            self.video_streaming_player.setVisible(False)
        else:  # Streaming Player
            self.current_mode = "streaming"
            # Hide standard containers
            self.audio_standard_container.setVisible(False)
            self.video_standard_container.setVisible(False)
            self.video_widget.setVisible(False)
            # Show streaming players
            self.audio_streaming_player.setVisible(True)
            self.video_streaming_player.setVisible(True)
    
    def cleanup_media(self):
        """Clean up media resources when tab is closed or app is shutting down"""
        try:
            # Force stop all workers
            self._force_cleanup_workers()
            
            # Force stop players
            self._force_cleanup_players()
            
            # Stop streaming players
            if hasattr(self, 'audio_streaming_player'):
                self.audio_streaming_player.stop_streaming()
            if hasattr(self, 'video_streaming_player'):
                self.video_streaming_player.stop_streaming()
                
        except Exception as e:
            print(f"Media cleanup error: {e}")
    
    def _force_cleanup_workers(self):
        """Force cleanup all worker threads"""
        try:
            # Stop audio worker
            if hasattr(self, '_audio_worker') and self._audio_worker:
                if self._audio_worker.isRunning():
                    self._audio_worker.stop()
                    self._audio_worker.wait(1000)  # Wait 1 second
                    if self._audio_worker.isRunning():
                        self._audio_worker.terminate()
                        self._audio_worker.wait(1000)
                self._audio_worker = None
            
            # Stop video worker
            if hasattr(self, '_video_worker') and self._video_worker:
                if self._video_worker.isRunning():
                    self._video_worker.stop()
                    self._video_worker.wait(1000)  # Wait 1 second
                    if self._video_worker.isRunning():
                        self._video_worker.terminate()
                        self._video_worker.wait(1000)
                self._video_worker = None
            
        except Exception as e:
            print(f"Worker cleanup error: {e}")
    
    def _force_cleanup_players(self):
        """Force cleanup media players"""
        try:
            # Stop and clear audio player
            if hasattr(self, 'audio_player'):
                self.audio_player.stop()
                self.audio_player.setSource(QUrl())
            
            # Stop and clear video player
            if hasattr(self, 'video_player'):
                self.video_player.stop()
            self.video_player.setSource(QUrl())
            
            # Reset state flags
            self._audio_switching = False
            self._video_switching = False
            self._audio_loaded = False
            self._video_loaded = False
            
            # Hide loading progress
            if hasattr(self, 'loading_progress'):
                self.loading_progress.setVisible(False)
            
        except Exception as e:
            print(f"Player cleanup error: {e}")
    
    def _emergency_cleanup(self):
        """Emergency cleanup when things go wrong"""
        try:
            print("Performing emergency cleanup...")
            
            # Force cleanup everything
            self._force_cleanup_workers()
            self._force_cleanup_players()
            
            # Reset UI
            if hasattr(self, 'status_label'):
                self.status_label.setText("Ready")
            if hasattr(self, 'loading_progress'):
                self.loading_progress.setVisible(False)
            
            # Force garbage collection
            import gc
            gc.collect()
            
            print("Emergency cleanup completed")
            
        except Exception as e:
            print(f"Emergency cleanup error: {e}")
    
    def closeEvent(self, event):
        """Clean up when tab is closed"""
        self.cleanup_media()
        super().closeEvent(event) 

    def _on_audio_playback_state_changed(self, state):
        from PySide6.QtMultimedia import QMediaPlayer
        if state == QMediaPlayer.StoppedState:
            self._on_audio_stop()

    def _on_video_playback_state_changed(self, state):
        from PySide6.QtMultimedia import QMediaPlayer
        if state == QMediaPlayer.StoppedState:
            self._on_video_stop() 

    def _on_audio_stop(self):
        """Re-enable audio file list when stopped (and keep it enabled for the rest of the session)"""
        self._audio_list_unlocked = True
        self.audio_list.setEnabled(True)

    def _on_video_stop(self):
        """Re-enable video file list when stopped (and keep it enabled for the rest of the session)"""
        self._video_list_unlocked = True
        self.video_list.setEnabled(True) 