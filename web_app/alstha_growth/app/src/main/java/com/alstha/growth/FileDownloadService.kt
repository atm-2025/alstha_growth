package com.alstha.growth

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.app.Notification
import android.app.PendingIntent
import android.content.Context
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.io.InputStream
import android.os.Environment
import android.provider.MediaStore
import android.content.ContentValues
import android.widget.Toast
import android.net.Uri
import java.io.OutputStream
import android.os.Handler
import android.os.Looper
import android.app.NotificationManager

class FileDownloadService : Service() {
    companion object {
        private const val CHANNEL_ID = "file_download_channel"
        private const val NOTIFICATION_ID = 1001
        private const val TAG = "FileDownloadService"
        const val ACTION_START_DOWNLOAD = "com.alstha.growth.action.START_DOWNLOAD"
        const val EXTRA_SERVER_URL = "serverUrl"
        const val EXTRA_FILENAME = "filename"
    }

    private val client = OkHttpClient.Builder().build()

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        createNotificationChannel() // Ensure channel before startForeground
        if (intent?.action == ACTION_START_DOWNLOAD) {
            val serverUrl = intent.getStringExtra(EXTRA_SERVER_URL) ?: return START_NOT_STICKY
            val filename = intent.getStringExtra(EXTRA_FILENAME) ?: return START_NOT_STICKY
            Log.d(TAG, "Starting foreground with notification for $filename")
            startForeground(NOTIFICATION_ID, buildNotification(filename, 0))
            downloadFile(serverUrl, filename)
        }
        return START_STICKY
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = android.app.NotificationChannel(
                CHANNEL_ID,
                "File Downloads",
                android.app.NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows download progress"
            }
            val notificationManager = getSystemService(android.app.NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
            Log.d(TAG, "Notification channel created/ensured")
        }
    }

    private fun buildNotification(filename: String, progress: Int): Notification {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val pendingIntent = PendingIntent.getActivity(this, 0, intent, PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Downloading: $filename")
            .setContentText("$progress% complete")
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setProgress(100, progress, false)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun ensureHttpScheme(url: String): String {
        return if (url.startsWith("http://") || url.startsWith("https://")) url else "http://$url"
    }

    private fun downloadFile(serverUrl: String, filename: String) {
        Thread {
            try {
                val fixedUrl = ensureHttpScheme(serverUrl)
                val downloadUrl = "$fixedUrl/download/$filename"
                Log.d(TAG, "Starting download from: $downloadUrl")
                val request = Request.Builder().url(downloadUrl).build()
                val response = client.newCall(request).execute()
                if (!response.isSuccessful) {
                    stopForeground(true)
                    stopSelf()
                    return@Thread
                }
                val body = response.body ?: run {
                    stopForeground(true)
                    stopSelf()
                    return@Thread
                }
                val contentLength = body.contentLength()
                val inputStream: InputStream = body.byteStream()
                var outputFile: File? = null
                var outputStream: OutputStream? = null
                var fileUri: Uri? = null
                try {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        val values = ContentValues().apply {
                            put(MediaStore.Downloads.DISPLAY_NAME, filename)
                            put(MediaStore.Downloads.MIME_TYPE, "application/octet-stream")
                            put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                        }
                        val resolver = contentResolver
                        val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                        if (uri == null) throw IOException("Failed to create MediaStore entry")
                        outputStream = resolver.openOutputStream(uri)
                        fileUri = uri
                    } else {
                        val downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                        if (!downloadsDir.exists()) downloadsDir.mkdirs()
                        // Insert number before extension if file exists (robust)
                        val dotIndex = filename.lastIndexOf('.')
                        val baseName = if (dotIndex != -1) filename.substring(0, dotIndex) else filename
                        val ext = if (dotIndex != -1) filename.substring(dotIndex) else ""
                        var uniqueName = filename
                        var counter = 1
                        var file = File(downloadsDir, uniqueName)
                        while (file.exists()) {
                            uniqueName = if (ext.isNotEmpty()) "$baseName ($counter)$ext" else "$baseName ($counter)"
                            file = File(downloadsDir, uniqueName)
                            counter++
                        }
                        Log.d(TAG, "Saving file as: $uniqueName")
                        outputFile = file
                        outputStream = FileOutputStream(outputFile)
                    }
                    val buffer = ByteArray(8192)
                    var bytesRead: Int
                    var totalBytesRead = 0L
                    while (inputStream.read(buffer).also { bytesRead = it } != -1) {
                        outputStream?.write(buffer, 0, bytesRead)
                        totalBytesRead += bytesRead
                        if (contentLength > 0) {
                            val progress = ((totalBytesRead * 100) / contentLength).toInt()
                            val notification = buildNotification(filename, progress)
                            (getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).notify(NOTIFICATION_ID, notification)
                        }
                    }
                    outputStream?.flush()
                    val notification = NotificationCompat.Builder(this, CHANNEL_ID)
                        .setContentTitle("Download Complete")
                        .setContentText("$filename saved to Downloads")
                        .setSmallIcon(android.R.drawable.stat_sys_download_done)
                        .setAutoCancel(true)
                        .build()
                    (getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).notify(NOTIFICATION_ID, notification)
                } catch (e: Exception) {
                    Log.e(TAG, "File write error", e)
                } finally {
                    try {
                        outputStream?.close()
                        inputStream.close()
                    } catch (e: Exception) {
                        Log.e(TAG, "Error closing streams", e)
                    }
                }
                stopForeground(true)
                stopSelf()
            } catch (e: Exception) {
                Log.e(TAG, "Download error", e)
                stopForeground(true)
                stopSelf()
            }
        }.start()
    }
} 