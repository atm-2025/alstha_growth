package com.alstha.growth

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import com.google.common.util.concurrent.ListenableFuture
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import com.google.android.material.button.MaterialButton

class CameraFragment : Fragment() {
    private lateinit var imageCapture: ImageCapture
    private lateinit var cameraExecutor: ExecutorService
    private lateinit var previewView: androidx.camera.view.PreviewView
    private lateinit var imageView: ImageView
    private lateinit var captureBtn: MaterialButton
    private lateinit var uploadBtn: MaterialButton
    private lateinit var clearLogBtn: MaterialButton
    private lateinit var logText: TextView
    private lateinit var fileInfoCard: View
    private lateinit var fileNameText: TextView
    private lateinit var fileSizeText: TextView
    private lateinit var fileTypeText: TextView
    private var photoFile: File? = null
    private var selectedFile: File? = null
    private var lensFacing = CameraSelector.LENS_FACING_BACK

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_camera, container, false)
        previewView = view.findViewById<androidx.camera.view.PreviewView>(R.id.previewView)
        imageView = view.findViewById<ImageView>(R.id.imageView)
        captureBtn = view.findViewById<MaterialButton>(R.id.captureBtn)
        uploadBtn = view.findViewById<MaterialButton>(R.id.uploadBtn)
        clearLogBtn = view.findViewById<MaterialButton>(R.id.clearLogBtn)
        logText = view.findViewById<TextView>(R.id.logText)
        fileInfoCard = view.findViewById<View>(R.id.fileInfoCard)
        fileNameText = view.findViewById<TextView>(R.id.fileNameText)
        fileSizeText = view.findViewById<TextView>(R.id.fileSizeText)
        fileTypeText = view.findViewById<TextView>(R.id.fileTypeText)
        
        // Hide camera controls initially
        previewView.visibility = View.GONE
        imageView.visibility = View.GONE
        captureBtn.visibility = View.GONE
        uploadBtn.visibility = View.GONE
        uploadBtn.isEnabled = false
        fileInfoCard.visibility = View.GONE
        
        return view
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        try {
            super.onViewCreated(view, savedInstanceState)
            cameraExecutor = Executors.newSingleThreadExecutor()
            
            // Verify all views are properly initialized
            if (!::logText.isInitialized || !::clearLogBtn.isInitialized || 
                !::captureBtn.isInitialized || !::uploadBtn.isInitialized) {
                Log.e("CameraFragment", "onViewCreated: Views not properly initialized")
                return
            }
            
            clearLogBtn.setOnClickListener {
                clearLogs()
            }
            
            captureBtn.setOnClickListener { takePhoto() }
            uploadBtn.setOnClickListener { 
                selectedFile?.let { (activity as MainActivity).uploadFile(it) }
                photoFile?.let { (activity as MainActivity).uploadFile(it) }
            }
            
            val switchCameraBtn = view.findViewById<Button>(R.id.switchCameraBtn)
            switchCameraBtn.setOnClickListener {
                lensFacing = if (lensFacing == CameraSelector.LENS_FACING_BACK)
                    CameraSelector.LENS_FACING_FRONT
                else
                    CameraSelector.LENS_FACING_BACK
                startCamera()
                addToLog("Switched camera: ${if (lensFacing == CameraSelector.LENS_FACING_BACK) "Back" else "Front"}")
            }
            
            // Only call addToLog after ensuring everything is initialized
            addToLog("Camera fragment initialized")
        } catch (e: Exception) {
            Log.e("CameraFragment", "onViewCreated: Error during initialization", e)
        }
    }
    
    fun openCamera() {
        try {
            if (ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                showCameraControls()
                // Hide imageView and disable uploadBtn on camera open
                imageView.visibility = View.GONE
                uploadBtn.isEnabled = false
                startCamera()
                addToLog("Camera opened")
            } else {
                requestPermissionLauncher.launch(Manifest.permission.CAMERA)
                addToLog("Requesting camera permission")
            }
        } catch (e: Exception) {
            Log.e("CameraFragment", "openCamera: Error opening camera", e)
        }
    }
    
    fun openFilePicker() {
        try {
            filePickerLauncher.launch("*/*")
            addToLog("Opening file picker")
        } catch (e: Exception) {
            Log.e("CameraFragment", "openFilePicker: Error opening file picker", e)
        }
    }
    
    fun clearLogs() {
        try {
            if (!::logText.isInitialized || logText == null) {
                Log.e("CameraFragment", "clearLogs: logText is null")
                return
            }
            logText.text = "Ready to upload files..."
            addToLog("Logs cleared")
        } catch (e: Exception) {
            Log.e("CameraFragment", "clearLogs: Error clearing logs", e)
        }
    }
    
    fun addToLog(message: String) {
        try {
            val timestamp = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault()).format(java.util.Date())
            val logEntry = "[$timestamp] $message\n"
            
            // Check if activity and logText are available
            if (activity == null || !::logText.isInitialized) {
                Log.d("CameraFragment", "addToLog: Activity or logText not available, logging to console: $logEntry")
                return
            }
            
            activity?.runOnUiThread {
                try {
                    // Double-check logText is still valid
                    if (!::logText.isInitialized || logText == null) {
                        Log.e("CameraFragment", "addToLog: logText is null in runOnUiThread")
                        return@runOnUiThread
                    }
                    
                    logText.append(logEntry)
                    
                    // Safe scrolling - check if layout is available
                    try {
                        val layout = logText.layout
                        if (layout != null) {
                            val scrollAmount = layout.getLineTop(logText.lineCount) - logText.height
                            if (scrollAmount > 0) {
                                logText.scrollTo(0, scrollAmount)
                            }
                        }
                    } catch (e: Exception) {
                        Log.e("CameraFragment", "addToLog: Error scrolling log", e)
                        // Continue without scrolling
                    }
                } catch (e: Exception) {
                    Log.e("CameraFragment", "addToLog: Error updating log text", e)
                }
            }
        } catch (e: Exception) {
            Log.e("CameraFragment", "addToLog: Critical error", e)
        }
    }

    private val filePickerLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        uri?.let { selectedUri ->
            try {
                // Create a temporary file from the selected URI
                val inputStream = requireContext().contentResolver.openInputStream(selectedUri)
                val fileName = getFileName(selectedUri)
                val tempFile = File(requireContext().cacheDir, fileName)
                
                inputStream?.use { input ->
                    tempFile.outputStream().use { output ->
                        input.copyTo(output)
                    }
                }
                
                selectedFile = tempFile
                photoFile = null
                
                // Show file info
                showFileInfo(tempFile)
                uploadBtn.isEnabled = true
                
                Toast.makeText(requireContext(), "File selected: ${tempFile.name}", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                Toast.makeText(requireContext(), "Error selecting file: ${e.message}", Toast.LENGTH_SHORT).show()
                Log.e("CameraFragment", "Error selecting file", e)
            }
        }
    }

    private fun getFileName(uri: android.net.Uri): String {
        val cursor = requireContext().contentResolver.query(uri, null, null, null, null)
        return cursor?.use {
            val nameIndex = it.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
            it.moveToFirst()
            it.getString(nameIndex) ?: "selected_file"
        } ?: "selected_file"
    }

    private fun showFileInfo(file: File) {
        try {
            // Check if all required views are initialized
            if (!::previewView.isInitialized || !::imageView.isInitialized || 
                !::captureBtn.isInitialized || !::uploadBtn.isInitialized || 
                !::fileInfoCard.isInitialized || !::fileNameText.isInitialized || 
                !::fileSizeText.isInitialized || !::fileTypeText.isInitialized) {
                Log.e("CameraFragment", "showFileInfo: Views not initialized")
                return
            }
            
            // Hide camera preview and show file info
            previewView.visibility = View.GONE
            imageView.visibility = View.GONE
            captureBtn.visibility = View.GONE
            
            // Show upload button for selected file
            uploadBtn.visibility = View.VISIBLE
            uploadBtn.isEnabled = true
            
            // Show file info card
            fileInfoCard.visibility = View.VISIBLE
            
            // Update file information
            val fileSize = file.length()
            val fileSizeFormatted = when {
                fileSize < 1024 -> "$fileSize B"
                fileSize < 1024 * 1024 -> "${fileSize / 1024} KB"
                else -> "${fileSize / (1024 * 1024)} MB"
            }
            
            val fileExtension = file.extension.uppercase()
            
            fileNameText.text = "Name: ${file.name}"
            fileSizeText.text = "Size: $fileSizeFormatted"
            fileTypeText.text = "Type: $fileExtension"
            
            addToLog("File selected: ${file.name} ($fileSizeFormatted)")
        } catch (e: Exception) {
            Log.e("CameraFragment", "showFileInfo: Error showing file info", e)
        }
    }

    private fun showCameraControls() {
        try {
            if (!::previewView.isInitialized || !::imageView.isInitialized || 
                !::captureBtn.isInitialized || !::uploadBtn.isInitialized || 
                !::fileInfoCard.isInitialized) {
                Log.e("CameraFragment", "showCameraControls: Views not initialized")
                return
            }
            previewView.visibility = View.VISIBLE
            imageView.visibility = View.GONE
            captureBtn.visibility = View.VISIBLE
            uploadBtn.visibility = View.VISIBLE
            uploadBtn.isEnabled = false
            fileInfoCard.visibility = View.GONE
            selectedFile = null
            addToLog("Camera controls shown")
        } catch (e: Exception) {
            Log.e("CameraFragment", "showCameraControls: Error showing camera controls", e)
        }
    }

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            showCameraControls()
            startCamera()
        } else Toast.makeText(requireContext(), "Camera permission denied", Toast.LENGTH_SHORT).show()
    }

    private fun startCamera() {
        try {
            // Check if previewView is initialized
            if (!::previewView.isInitialized) {
                Log.e("CameraFragment", "startCamera: previewView not initialized")
                return
            }
            
            val cameraProviderFuture: ListenableFuture<ProcessCameraProvider> = ProcessCameraProvider.getInstance(requireContext())
            cameraProviderFuture.addListener({
                try {
                    val cameraProvider = cameraProviderFuture.get()
                    val preview = Preview.Builder().build().also {
                        it.setSurfaceProvider(previewView.surfaceProvider)
                    }
                    imageCapture = ImageCapture.Builder().build()
                    val cameraSelector = CameraSelector.Builder()
                        .requireLensFacing(lensFacing)
                        .build()
                    try {
                        cameraProvider.unbindAll()
                        cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageCapture)
                    } catch (e: Exception) {
                        Log.e("CameraFragment", "Camera binding failed", e)
                    }
                } catch (e: Exception) {
                    Log.e("CameraFragment", "startCamera: Error in camera provider listener", e)
                }
            }, ContextCompat.getMainExecutor(requireContext()))
        } catch (e: Exception) {
            Log.e("CameraFragment", "startCamera: Error starting camera", e)
        }
    }

    private fun takePhoto() {
        try {
            // Check if required components are initialized
            if (!::imageCapture.isInitialized || !::imageView.isInitialized || !::uploadBtn.isInitialized) {
                Log.e("CameraFragment", "takePhoto: Required components not initialized")
                return
            }
            val dateFormat = SimpleDateFormat("ddMMyyyy_HHmmss", Locale.getDefault())
            val timestamp = dateFormat.format(Date())
            val photoFile = File(requireContext().cacheDir, "photo_$timestamp.jpg")
            val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()
            imageCapture.takePicture(outputOptions, ContextCompat.getMainExecutor(requireContext()), object : ImageCapture.OnImageSavedCallback {
                override fun onImageSaved(outputFileResults: ImageCapture.OutputFileResults) {
                    try {
                        this@CameraFragment.photoFile = photoFile
                        selectedFile = null
                        val bitmap = BitmapFactory.decodeFile(photoFile.absolutePath)
                        imageView.setImageBitmap(bitmap)
                        imageView.visibility = View.VISIBLE
                        uploadBtn.isEnabled = true
                        addToLog("Photo captured: ${photoFile.name}")
                    } catch (e: Exception) {
                        Log.e("CameraFragment", "takePhoto: Error in onImageSaved", e)
                    }
                }
                override fun onError(exception: ImageCaptureException) {
                    try {
                        Toast.makeText(requireContext(), "Capture failed: ${exception.message}", Toast.LENGTH_SHORT).show()
                        addToLog("Photo capture failed: ${exception.message}")
                    } catch (e: Exception) {
                        Log.e("CameraFragment", "takePhoto: Error in onError", e)
                    }
                }
            })
        } catch (e: Exception) {
            Log.e("CameraFragment", "takePhoto: Error taking photo", e)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }
    companion object {
        @JvmStatic // Optional: if you need to call this from Java
        fun newInstance(): CameraFragment {
            // If you need to pass arguments to the fragment:
            // val fragment = CameraFragment()
            // val args = Bundle()
            // args.putString("some_key", "some_value")
            // fragment.arguments = args
            // return fragment
            return CameraFragment() // Simple version if no arguments
        }
    }
} 