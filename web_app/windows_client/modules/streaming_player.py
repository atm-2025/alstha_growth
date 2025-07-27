import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel, 
    QProgressBar, QMessageBox, QStyle
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from workers import StreamingWorker
from utils import format_time

class StreamingMediaPlayer(QWidget):
    """Advanced streaming media player with chunked loading and buffering"""
    
    def __init__(self, media_type="audio"):
        super().__init__()
        self.media_type = media_type
        self.streaming_worker = None
        self.temp_file_path = None
        
        layout = QVBoxLayout()
        
        # Media player
        self.player = QMediaPlayer()
        if media_type == "video":
            self.video_widget = QVideoWidget()
            self.player.setVideoOutput(self.video_widget)
            layout.addWidget(self.video_widget)
        
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Play/Pause/Stop buttons
        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.pause_btn = QPushButton()
        self.pause_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.stop_btn)
        
        # Progress and time
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.time_label = QLabel("00:00 / 00:00")
        
        controls_layout.addWidget(self.progress_slider, 2)
        controls_layout.addWidget(self.time_label)
        
        # Volume
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        controls_layout.addWidget(QLabel("Vol"))
        controls_layout.addWidget(self.volume_slider)
        
        layout.addLayout(controls_layout)
        
        # Buffer progress
        buffer_layout = QHBoxLayout()
        buffer_layout.addWidget(QLabel("Buffer:"))
        self.buffer_progress = QProgressBar()
        self.buffer_progress.setRange(0, 100)
        self.buffer_progress.setVisible(False)
        buffer_layout.addWidget(self.buffer_progress)
        buffer_layout.addStretch()
        layout.addLayout(buffer_layout)
        
        # Connect signals
        self.play_btn.clicked.connect(self.player.play)
        self.pause_btn.clicked.connect(self.player.pause)
        self.stop_btn.clicked.connect(self.stop_streaming)
        self.progress_slider.sliderMoved.connect(self.seek)
        self.player.positionChanged.connect(self.update_progress)
        self.player.durationChanged.connect(self.update_duration)
        self.volume_slider.valueChanged.connect(lambda v: self.audio_output.setVolume(v/100))
        self.audio_output.setVolume(self.volume_slider.value()/100)
        
        self.setLayout(layout)
    
    def stream_file(self, file_path):
        """Start streaming a file in chunks"""
        try:
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "File Not Found", f"File not found: {file_path}")
                return
            
            # Stop any current streaming and wait for cleanup
            self.stop_streaming()
            
            # Small delay to ensure proper cleanup
            QTimer.singleShot(200, lambda: self._start_streaming(file_path))
                
        except Exception as e:
            QMessageBox.critical(self, "Streaming Error", f"Failed to stream file: {str(e)}")
            self.stop_streaming()
    
    def _start_streaming(self, file_path):
        """Internal method to start streaming after cleanup delay"""
        try:
            # Start streaming worker
            self.streaming_worker = StreamingWorker(file_path)
            self.streaming_worker.buffer_progress.connect(self.update_buffer_progress)
            self.streaming_worker.streaming_complete.connect(self.on_streaming_complete)
            self.streaming_worker.start()
            
            # Show buffer progress
            self.buffer_progress.setVisible(True)
            self.buffer_progress.setValue(0)
            
        except Exception as e:
            QMessageBox.critical(self, "Streaming Error", f"Failed to start streaming: {str(e)}")
            self.stop_streaming()
    
    def update_buffer_progress(self, percent):
        """Update buffer progress bar"""
        try:
            self.buffer_progress.setValue(percent)
            
            # Start playing when we have enough buffer (10% or 1MB)
            if percent >= 10 and not self.player.mediaStatus() == QMediaPlayer.PlayingState:
                if hasattr(self, 'temp_file_path') and self.temp_file_path:
                    self.player.setSource(QUrl.fromLocalFile(self.temp_file_path))
                    self.player.play()
        except Exception as e:
            print(f"Buffer progress update error: {e}")
    
    def on_streaming_complete(self, temp_file_path):
        """Called when streaming is complete"""
        try:
            self.temp_file_path = temp_file_path
            self.buffer_progress.setValue(100)
            
            # Start playing if not already playing
            if not self.player.mediaStatus() == QMediaPlayer.PlayingState:
                self.player.setSource(QUrl.fromLocalFile(temp_file_path))
                self.player.play()
        except Exception as e:
            print(f"Streaming complete error: {e}")
    
    def stop_streaming(self):
        """Stop streaming and cleanup"""
        try:
            # Stop the player first
            self.player.stop()
            self.player.setSource(QUrl())
            
            # Stop streaming worker
            if self.streaming_worker:
                # Disconnect signals first to prevent memory leaks
                try:
                    self.streaming_worker.buffer_progress.disconnect()
                    self.streaming_worker.streaming_complete.disconnect()
                    self.streaming_worker.finished.disconnect()
                except:
                    pass
                
                self.streaming_worker.stop()
                # Wait a bit for worker to stop, but don't block UI
                if self.streaming_worker.isRunning():
                    self.streaming_worker.wait(1000)  # Wait max 1 second
                
                self.streaming_worker = None
            
            # Hide buffer progress
            self.buffer_progress.setVisible(False)
            self.buffer_progress.setValue(0)
            
            # Clean up temp file
            if self.temp_file_path and os.path.exists(self.temp_file_path):
                try:
                    os.unlink(self.temp_file_path)
                except:
                    pass
                self.temp_file_path = None
                
        except Exception as e:
            print(f"Error stopping streaming: {e}")
    
    def seek(self, pos):
        """Seek to position"""
        if self.player.duration() > 0:
            self.player.setPosition(int(pos/100 * self.player.duration()))
    
    def update_progress(self, position):
        """Update progress slider"""
        duration = self.player.duration()
        if duration > 0:
            percent = int(position / duration * 100)
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(percent)
            self.progress_slider.blockSignals(False)
            self.time_label.setText(f"{format_time(position)} / {format_time(duration)}")
    
    def update_duration(self, duration):
        """Update duration display"""
        position = self.player.position()
        if duration > 0:
            percent = int(position / duration * 100)
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(percent)
            self.progress_slider.blockSignals(False)
            self.time_label.setText(f"{format_time(position)} / {format_time(duration)}")
    
    def closeEvent(self, event):
        """Clean up when widget is closed"""
        self.stop_streaming()
        super().closeEvent(event) 