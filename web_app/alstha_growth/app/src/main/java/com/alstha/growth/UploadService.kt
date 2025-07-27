package com.alstha.growth

import android.app.*
import android.content.Intent
import android.os.Binder
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import android.widget.Toast
import androidx.core.app.NotificationCompat
import java.io.File

class UploadService : Service() {
    private val binder = LocalBinder()
    private var uploadRepository: UploadRepository? = null
    private var currentUploadJob: String? = null
    private var wakeLock: PowerManager.WakeLock? = null
    
    companion object {
        private const val NOTIFICATION_ID = 1001
        private const val CHANNEL_ID = "upload_channel"
        private const val CHANNEL_NAME = "File Uploads"
    }
    
    inner class LocalBinder : Binder() {
        fun getService(): UploadService = this@UploadService
    }
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        
        // Initialize wake lock
        val powerManager = getSystemService(android.content.Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "AlsthaGrowth::UploadWakeLock"
        )
        
        Log.d("UploadService", "Service created")
    }
    
    override fun onBind(intent: Intent): IBinder {
        return binder
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d("UploadService", "Service started")
        return START_STICKY // Restart service if killed
    }
    
    private fun createNotificationChannel() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows upload progress"
                setShowBadge(false)
            }
            
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }
    
    fun uploadFile(file: File, serverIp: String, onResult: (String?) -> Unit) {
        // Acquire wake lock to prevent device sleep
        wakeLock?.acquire(10 * 60 * 1000L) // 10 minutes timeout
        
        // Create notification for foreground service
        startForeground(NOTIFICATION_ID, createUploadNotification("Starting upload...", file.name))
        
        // Initialize upload repository
        val serverIp = SettingsActivity.getServerIp(this)
        if (uploadRepository == null) {
            uploadRepository = UploadRepository(serverIp)
        }
        
        // Generate unique job ID
        currentUploadJob = "${file.name}_${System.currentTimeMillis()}"
        
        Log.d("UploadService", "Starting background upload: ${file.name}")
        
        // Update notification
        updateNotification("Uploading ${file.name}...", file.name)
        
        uploadRepository?.uploadFile(file, 
            onResult = { result ->
                Log.d("UploadService", "Upload completed: $result")
                
                // Release wake lock
                if (wakeLock?.isHeld == true) {
                    wakeLock?.release()
                }
                
                // Update notification with result
                if (result?.contains("successful") == true || result?.contains("Processed") == true) {
                    updateNotification("Upload completed: ${file.name}", file.name)
                } else {
                    updateNotification("Upload failed: ${file.name}", file.name)
                }
                
                // Call the callback
                onResult(result)
                
                // Stop foreground service after a delay
                android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                    stopForeground(false)
                    stopSelf()
                }, 3000) // Show result for 3 seconds
            },
            onProgress = { progress ->
                // Update notification with progress
                updateNotification("Uploading ${file.name}... (${progress}%)", file.name)
            }
        )
    }
    
    private fun createUploadNotification(message: String, fileName: String): Notification {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("File Upload")
            .setContentText(message)
            .setSmallIcon(android.R.drawable.ic_menu_upload)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setAutoCancel(false)
            .build()
    }
    
    private fun updateNotification(message: String, fileName: String) {
        val notification = createUploadNotification(message, fileName)
        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager.notify(NOTIFICATION_ID, notification)
    }
    
    override fun onDestroy() {
        super.onDestroy()
        
        // Release wake lock if still held
        if (wakeLock?.isHeld == true) {
            wakeLock?.release()
        }
        
        Log.d("UploadService", "Service destroyed")
    }
} 