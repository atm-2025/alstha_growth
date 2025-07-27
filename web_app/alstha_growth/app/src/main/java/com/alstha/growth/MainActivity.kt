package com.alstha.growth

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import android.os.IBinder
import android.util.Log
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.widget.Toolbar
import com.google.android.material.button.MaterialButton
import com.google.android.material.progressindicator.LinearProgressIndicator
import com.google.android.material.textfield.TextInputEditText
import java.io.File
import android.os.Build
import android.Manifest
import android.content.pm.PackageManager
import androidx.core.app.ActivityCompat
import androidx.fragment.app.Fragment
import com.alstha.growth.HomeFragment
import com.google.android.material.bottomnavigation.BottomNavigationView

class MainActivity : AppCompatActivity() {
    private var uploadService: UploadService? = null
    private var bound = false
    
    // UI Components
    private lateinit var toolbar: Toolbar
    private lateinit var progressContainer: View
    private lateinit var progressText: TextView
    private lateinit var progressBar: LinearProgressIndicator
    
    private val connection = object : ServiceConnection {
        override fun onServiceConnected(className: ComponentName, service: IBinder) {
            val binder = service as UploadService.LocalBinder
            uploadService = binder.getService()
            bound = true
            Log.d("MainActivity", "Service connected")
        }
        
        override fun onServiceDisconnected(arg0: ComponentName) {
            bound = false
            Log.d("MainActivity", "Service disconnected")
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        try {
            super.onCreate(savedInstanceState)
            setContentView(R.layout.activity_main)
            requestNotificationPermissionIfNeeded()
            Log.d("MainActivity", "onCreate: Starting initialization")
            
            // Initialize connection manager
            ConnectionManager.getInstance(this).initializeConnection { connectedIp ->
                Log.d("MainActivity", "Connected to server: $connectedIp")
            }
            
            initializeViews()
            setupToolbar()
            setupClickListeners()
            // Removed bottomNav logic
            if (savedInstanceState == null) {
                try {
                    supportFragmentManager.beginTransaction()
                        .replace(R.id.fragment_container, HomeFragment.newInstance())
                        .commitNow()
                    Log.d("MainActivity", "onCreate: HomeFragment added successfully")
                } catch (e: Exception) {
                    Log.e("MainActivity", "onCreate: Error adding HomeFragment", e)
                    Toast.makeText(this, "Error initializing home: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
            
            Log.d("MainActivity", "onCreate: Initialization completed successfully")
        } catch (e: Exception) {
            Log.e("MainActivity", "onCreate: Critical error during initialization", e)
            Toast.makeText(this, "App initialization failed: ${e.message}", Toast.LENGTH_LONG).show()
            // Show a simple error dialog
            androidx.appcompat.app.AlertDialog.Builder(this)
                .setTitle("App Error")
                .setMessage("Failed to initialize app: ${e.message}\n\nPlease restart the app.")
                .setPositiveButton("OK") { _, _ -> finish() }
                .setCancelable(false)
                .show()
        }
    }
    
    private fun initializeViews() {
        try {
            toolbar = findViewById<Toolbar>(R.id.toolbar)
            progressContainer = findViewById<View>(R.id.progressContainer)
            progressText = findViewById<TextView>(R.id.progressText)
            progressBar = findViewById<LinearProgressIndicator>(R.id.progressBar)
            Log.d("MainActivity", "initializeViews: All views initialized successfully")
        } catch (e: Exception) {
            Log.e("MainActivity", "initializeViews: Error initializing views", e)
            Toast.makeText(this, "Error initializing UI: ${e.message}", Toast.LENGTH_LONG).show()
            throw e // Re-throw to be caught by onCreate
        }
    }
    
    private fun setupToolbar() {
        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(false)
    }
    
    private fun setupClickListeners() {
        // No-op: removed cameraBtn, selectFileBtn, downloadFilesBtn
    }
    
    fun showFragment(fragment: Fragment) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragment_container, fragment)
            .commit()
        supportFragmentManager.executePendingTransactions()
        // uploadOptionsCard.visibility = ... (removed)
    }
    
    fun switchToCameraFragment() {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragment_container, CameraFragment.newInstance())
            .commit()
    }
    
    private fun switchToFileListFragment() {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragment_container, FileListFragment.newInstance())
            .commit()
    }
    
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }
    
    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_settings -> {
                val intent = Intent(this, SettingsActivity::class.java)
                startActivity(intent)
                true
            }
            R.id.action_clear_logs -> {
                clearLogs()
                true
            }
            R.id.action_about -> {
                showAboutDialog()
                true
            }
            R.id.action_upload_text -> {
                showUploadTextDialog()
                true
            }
            R.id.action_daily_logs -> {
                showFragment(DailyLogsFragment.newInstance())
                supportActionBar?.title = "Daily Logs"
                true
            }
            R.id.action_llm -> {
                showFragment(LLMFragment.newInstance())
                supportActionBar?.title = "LLM"
                true
            }
            R.id.action_file_upload -> {
                showFragment(FileListFragment.newInstance())
                supportActionBar?.title = "File Upload"
                true
            }
            R.id.action_command -> {
                showFragment(CommandFragment.newInstance())
                supportActionBar?.title = "Command"
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
    
    private fun clearLogs() {
        val fragment = supportFragmentManager.findFragmentById(R.id.fragment_container)
        if (fragment is CameraFragment) {
            fragment.clearLogs()
        }
    }
    
    private fun showAboutDialog() {
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("About")
            .setMessage("File Upload App\nVersion 1.0\n\nUpload files to your server with ease!")
            .setPositiveButton("OK", null)
            .show()
    }
    
    override fun onStart() {
        super.onStart()
        // Bind to UploadService
        Intent(this, UploadService::class.java).also { intent ->
            bindService(intent, connection, Context.BIND_AUTO_CREATE)
        }
    }
    
    override fun onStop() {
        super.onStop()
        // Unbind from service
        if (bound) {
            unbindService(connection)
            bound = false
        }
    }

    fun uploadImage(file: File) {
        uploadFile(file)
    }

    fun uploadFile(file: File) {
        val serverIp = ConnectionManager.getInstance(this).getCurrentServerIp()
        
        // Show progress
        showProgress("Starting upload: ${file.name}")
        
        if (bound && uploadService != null) {
            // Use background service for upload
            Log.d("MainActivity", "Starting background upload: ${file.name}")
            addToLog("Starting background upload: ${file.name}")
            
            uploadService?.uploadFile(file, serverIp) { result ->
                runOnUiThread {
                    hideProgress()
                    Toast.makeText(this@MainActivity, "Upload result: $result", Toast.LENGTH_LONG).show()
                    addToLog("Upload completed: $result")
                }
                Log.d("MainActivity", "Upload result: $result")
            }
        } else {
            // Fallback to direct upload if service not available
            Log.d("MainActivity", "Service not bound, using direct upload")
            addToLog("Using direct upload (service not available)")
            val uploadRepository = UploadRepository(serverIp)
            
            uploadRepository.uploadFile(file, { result ->
                runOnUiThread {
                    hideProgress()
                    Toast.makeText(this@MainActivity, "Upload result: $result", Toast.LENGTH_LONG).show()
                    addToLog("Upload completed: $result")
                }
                Log.d("MainActivity", "Upload result: $result")
            })
        }
        
        Log.d("MainActivity", "Attempting to upload file: ${file.name} to server: $serverIp")
    }
    
    fun showProgress(message: String) {
        progressText.text = message
        progressContainer.visibility = View.VISIBLE
    }
    
    fun hideProgress() {
        progressContainer.visibility = View.GONE
    }
    
    fun addToLog(message: String) {
        val fragment = supportFragmentManager.findFragmentById(R.id.fragment_container)
        if (fragment is CameraFragment) {
            fragment.addToLog(message)
        }
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ActivityCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1001)
            }
        }
    }

    fun showUploadTextDialog() {
        val editText = android.widget.EditText(this)
        editText.hint = "Enter text to upload"
        editText.minLines = 4
        editText.maxLines = 10
        editText.setPadding(32, 32, 32, 32)

        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("Upload Text")
            .setView(editText)
            .setPositiveButton("Upload") { _, _ ->
                val text = editText.text.toString()
                if (text.isNotBlank()) {
                    uploadTextAsFile(text)
                } else {
                    Toast.makeText(this, "Text is empty!", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun uploadTextAsFile(text: String) {
        try {
            val tempFile = File.createTempFile("uploaded_text_", ".txt", cacheDir)
            tempFile.writeText(text)
            uploadFile(tempFile)
        } catch (e: Exception) {
            Toast.makeText(this, "Failed to save text: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }
}