package com.alstha.growth

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.provider.Settings
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.button.MaterialButton
import com.google.android.material.card.MaterialCardView
import com.google.android.material.progressindicator.LinearProgressIndicator
import com.google.android.material.textview.MaterialTextView
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors
// CameraX imports (if used)
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView

class FileListFragment : Fragment() {
    
    private lateinit var progressBar: LinearProgressIndicator
    private var serverUrl: String = ""
    private var backCallback: OnBackPressedCallback? = null
    private lateinit var cameraExecutor: java.util.concurrent.ExecutorService
    private lateinit var previewView: PreviewView
    private lateinit var imageCapture: ImageCapture
    private var lensFacing = CameraSelector.LENS_FACING_BACK
    private var filePickerLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let { selectedUri ->
            try {
                val inputStream = requireContext().contentResolver.openInputStream(selectedUri)
                val fileName = getFileName(selectedUri)
                val tempFile = File(requireContext().cacheDir, fileName)
                inputStream?.use { input ->
                    tempFile.outputStream().use { output ->
                        input.copyTo(output)
                    }
                }
                selectedFile = tempFile
                uploadCapturedBtn.visibility = View.VISIBLE
                uploadCapturedBtn.isEnabled = true
                Toast.makeText(requireContext(), "File selected: ${tempFile.name}", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                Toast.makeText(requireContext(), "Error selecting file: ${e.message}", Toast.LENGTH_SHORT).show()
                Log.e("FileListFragment", "Error selecting file", e)
            }
        }
    }
    private lateinit var cameraPreview: PreviewView
    private lateinit var capturedImagePreview: ImageView
    private lateinit var uploadCapturedBtn: MaterialButton
    private var capturedPhotoFile: File? = null
    private var selectedFile: File? = null
    private lateinit var uploadStatusBar: LinearLayout
    private lateinit var uploadingStatusText: TextView
    private lateinit var uploadTickIcon: ImageView
    private lateinit var imageFileRecycler: RecyclerView
    private lateinit var imageFileAdapter: FileListAdapter
    private var imageFiles: List<File> = emptyList()
    private val PERMISSION_REQUEST_CODE = 1002
    private lateinit var emptyListText: TextView
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_file_list, container, false)
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        // Remove toolbar setup
        cameraPreview = view.findViewById(R.id.cameraPreview)
        capturedImagePreview = view.findViewById(R.id.capturedImagePreview)
        uploadCapturedBtn = view.findViewById(R.id.uploadCapturedBtn)
        uploadStatusBar = view.findViewById(R.id.uploadStatusBar)
        uploadingStatusText = view.findViewById(R.id.uploadingStatusText)
        uploadTickIcon = view.findViewById(R.id.uploadTickIcon)
        cameraPreview.visibility = View.GONE
        capturedImagePreview.visibility = View.GONE
        uploadCapturedBtn.visibility = View.GONE
        uploadStatusBar.visibility = View.GONE
        uploadTickIcon.visibility = View.GONE
        cameraExecutor = Executors.newSingleThreadExecutor()
        imageCapture = ImageCapture.Builder().build()
        view.findViewById<MaterialButton?>(R.id.cameraBtn)?.setOnClickListener {
            cameraPreview.visibility = View.VISIBLE
            capturedImagePreview.visibility = View.GONE
            uploadCapturedBtn.visibility = View.GONE
            uploadStatusBar.visibility = View.GONE
            uploadTickIcon.visibility = View.GONE
            selectedFile = null
            startCameraPreview()
        }
        view.findViewById<MaterialButton?>(R.id.selectFileBtn)?.setOnClickListener {
            filePickerLauncher.launch("*/*")
        }
        // Download button can be implemented later if needed
        cameraPreview.setOnClickListener {
            takePhoto()
        }
        uploadCapturedBtn.setOnClickListener {
            // Upload selected file or captured photo
            val fileToUpload = selectedFile ?: capturedPhotoFile
            fileToUpload?.let {
                showUploadingStatus()
                (activity as? MainActivity)?.uploadFile(it)
                cameraPreview.postDelayed({
                    showUploadComplete()
                }, 2000)
            }
        }
        imageFileRecycler = view.findViewById(R.id.imageFileRecycler)
        imageFileAdapter = FileListAdapter(
            onFileClick = { fileInfo ->
                val file = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), fileInfo.name)
                selectedFile = file
                uploadCapturedBtn.visibility = View.VISIBLE
                uploadCapturedBtn.isEnabled = true
                Toast.makeText(requireContext(), "Selected: ${file.name}", Toast.LENGTH_SHORT).show()
            },
            onDownloadClick = {},
            onDeleteClick = {}
        )
        imageFileRecycler.layoutManager = LinearLayoutManager(requireContext())
        imageFileRecycler.adapter = imageFileAdapter
        // Add a TextView for empty state in the layout (if not present, add programmatically)
        emptyListText = view.findViewById(R.id.emptyListText) ?: TextView(requireContext()).apply {
            id = View.generateViewId()
            text = "No screenshots found."
            textSize = 16f
            setTextColor(ContextCompat.getColor(requireContext(), android.R.color.darker_gray))
            visibility = View.GONE
            (view as ViewGroup).addView(this)
        }
        // Request correct permissions for screenshots
        val needsMediaImages = Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
        val needsReadStorage = Build.VERSION.SDK_INT in Build.VERSION_CODES.Q..Build.VERSION_CODES.S
        val hasMediaImages = !needsMediaImages || ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.READ_MEDIA_IMAGES) == PackageManager.PERMISSION_GRANTED
        val hasReadStorage = !needsReadStorage || ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.READ_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED
        if (!hasMediaImages || !hasReadStorage) {
            val permissions = mutableListOf<String>()
            if (needsMediaImages) permissions.add(Manifest.permission.READ_MEDIA_IMAGES)
            if (needsReadStorage) permissions.add(Manifest.permission.READ_EXTERNAL_STORAGE)
            if (shouldShowRequestPermissionRationale(permissions.first())) {
                androidx.appcompat.app.AlertDialog.Builder(requireContext())
                    .setTitle("Permission Required")
                    .setMessage("This app needs permission to access your screenshots. Please grant storage or media permissions in settings.")
                    .setPositiveButton("OK") { _, _ ->
                        requestPermissions(permissions.toTypedArray(), PERMISSION_REQUEST_CODE)
                    }
                    .show()
                } else {
                requestPermissions(permissions.toTypedArray(), PERMISSION_REQUEST_CODE)
            }
            return
        }
        // Query MediaStore for both Pictures/Screenshots and DCIM/Screenshots
        try {
            val imageExts = listOf("jpg", "jpeg", "png", "gif", "bmp", "webp")
            val fileInfos = mutableListOf<com.alstha.growth.FileInfo>()
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val projection = arrayOf(
                    MediaStore.Images.Media._ID,
                    MediaStore.Images.Media.DISPLAY_NAME,
                    MediaStore.Images.Media.SIZE,
                    MediaStore.Images.Media.DATE_MODIFIED,
                    MediaStore.Images.Media.DATA
                )
                val selection = MediaStore.Images.Media.RELATIVE_PATH + " LIKE ? OR " + MediaStore.Images.Media.RELATIVE_PATH + " LIKE ?"
                val selectionArgs = arrayOf("%Pictures/Screenshots%", "%DCIM/Screenshots%")
                val sortOrder = MediaStore.Images.Media.DATE_MODIFIED + " DESC"
                val cursor = requireContext().contentResolver.query(
                    MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                    projection,
                    selection,
                    selectionArgs,
                    sortOrder
                )
                cursor?.use {
                    val nameCol = it.getColumnIndexOrThrow(MediaStore.Images.Media.DISPLAY_NAME)
                    val sizeCol = it.getColumnIndexOrThrow(MediaStore.Images.Media.SIZE)
                    val dateCol = it.getColumnIndexOrThrow(MediaStore.Images.Media.DATE_MODIFIED)
                    val dataCol = it.getColumnIndexOrThrow(MediaStore.Images.Media.DATA)
                    while (it.moveToNext()) {
                        val name = it.getString(nameCol)
                        val sizeBytes = it.getLong(sizeCol)
                        val size = android.text.format.Formatter.formatShortFileSize(requireContext(), sizeBytes)
                        val modified = it.getLong(dateCol)
                        val path = it.getString(dataCol)
                        val ext = name.substringAfterLast('.', "").lowercase()
                        if (imageExts.contains(ext)) {
                            fileInfos.add(
                                com.alstha.growth.FileInfo(
                                    name = name,
                                    size = size,
                                    sizeBytes = sizeBytes,
                                    modified = modified,
                                    extension = ext,
                                    path = path
                                )
                            )
                        }
                    }
                }
            } else {
                // Fallback to File API for older Android
                val allFiles = mutableListOf<java.io.File>()
                val picsDir = java.io.File(android.os.Environment.getExternalStorageDirectory(), "Pictures/Screenshots")
                val dcimDir = java.io.File(android.os.Environment.getExternalStorageDirectory(), "DCIM/Screenshots")
                if (picsDir.exists()) allFiles.addAll(picsDir.listFiles()?.toList() ?: emptyList())
                if (dcimDir.exists()) allFiles.addAll(dcimDir.listFiles()?.toList() ?: emptyList())
                val files = allFiles.filter {
                    it.isFile && imageExts.contains(it.extension.lowercase())
                }.sortedByDescending { it.lastModified() }
                if (files.isNotEmpty()) {
                    fileInfos.addAll(files.map {
                        com.alstha.growth.FileInfo(
                            name = it.name,
                            size = android.text.format.Formatter.formatShortFileSize(requireContext(), it.length()),
                            sizeBytes = it.length(),
                            modified = it.lastModified() / 1000,
                            extension = it.extension,
                            path = it.absolutePath
                        )
                    })
                }
            }
            val top3 = fileInfos.sortedByDescending { it.modified }.take(3)
            Log.d("FileListFragment", "Screenshots found: ${top3.size}")
            top3.forEach { Log.d("FileListFragment", "Screenshot: ${it.path}") }
            if (top3.isNotEmpty()) {
                imageFileAdapter.updateFiles(top3)
                emptyListText.visibility = View.GONE
                // Auto-select first file
                selectedFile = java.io.File(top3[0].path ?: "")
                uploadCapturedBtn.visibility = View.VISIBLE
                uploadCapturedBtn.isEnabled = true
            } else {
                imageFileAdapter.updateFiles(emptyList())
                emptyListText.visibility = View.VISIBLE
                Toast.makeText(requireContext(), "No screenshots found in Pictures/Screenshots or DCIM/Screenshots.", Toast.LENGTH_LONG).show()
            }
        } catch (e: SecurityException) {
            emptyListText.text = "Permission denied. Cannot show screenshots."
            emptyListText.visibility = View.VISIBLE
            showPermissionSettingsDialog()
        } catch (e: Exception) {
            Log.e("FileListFragment", "Error listing screenshot image files", e)
            Toast.makeText(requireContext(), "Error accessing screenshots folder.", Toast.LENGTH_LONG).show()
        }
        val ip = SettingsActivity.getServerIp(requireContext())
        serverUrl = "http://$ip:5000"
    }

    override fun onResume() {
        super.onResume()
        backCallback = object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                (activity as? MainActivity)?.showFragment(HomeFragment.newInstance())
                (activity as? MainActivity)?.supportActionBar?.title = "Home"
            }
        }
        requireActivity().onBackPressedDispatcher.addCallback(this, backCallback!!)
    }

    override fun onPause() {
        super.onPause()
        backCallback?.remove()
    }
    
    private fun showLoading(show: Boolean) {
        progressBar.visibility = if (show) View.VISIBLE else View.GONE
    }
    
    private fun startCameraPreview() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(requireContext())
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(cameraPreview.surfaceProvider)
            }
            val cameraSelector = CameraSelector.Builder().requireLensFacing(lensFacing).build()
            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageCapture)
            } catch (e: Exception) {
                Log.e("FileListFragment", "Camera binding failed", e)
            }
        }, ContextCompat.getMainExecutor(requireContext()))
    }

    private fun takePhoto() {
        val dateFormat = SimpleDateFormat("ddMMyyyy_HHmmss", Locale.getDefault())
        val timestamp = dateFormat.format(Date())
        val photoFile = File(requireContext().cacheDir, "photo_$timestamp.jpg")
        val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()
        imageCapture.takePicture(outputOptions, ContextCompat.getMainExecutor(requireContext()), object : ImageCapture.OnImageSavedCallback {
            override fun onImageSaved(outputFileResults: ImageCapture.OutputFileResults) {
                capturedPhotoFile = photoFile
                val bitmap = android.graphics.BitmapFactory.decodeFile(photoFile.absolutePath)
                capturedImagePreview.setImageBitmap(bitmap)
                capturedImagePreview.visibility = View.VISIBLE
                cameraPreview.visibility = View.GONE
                uploadCapturedBtn.visibility = View.VISIBLE
                Toast.makeText(requireContext(), "Photo captured! Tap Upload to send.", Toast.LENGTH_SHORT).show()
            }
            override fun onError(exception: ImageCaptureException) {
                Toast.makeText(requireContext(), "Capture failed: ${exception.message}", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun getFileName(uri: android.net.Uri): String {
        val cursor = requireContext().contentResolver.query(uri, null, null, null, null)
        return cursor?.use {
            val nameIndex = it.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
            it.moveToFirst()
            it.getString(nameIndex) ?: "selected_file"
        } ?: "selected_file"
    }

    private fun showUploadingStatus() {
        uploadStatusBar.visibility = View.VISIBLE
        uploadingStatusText.text = "Uploading file"
        uploadTickIcon.visibility = View.GONE
    }

    private fun showUploadComplete() {
        uploadStatusBar.visibility = View.VISIBLE
        uploadingStatusText.text = "Uploading file"
        uploadTickIcon.visibility = View.VISIBLE
        selectedFile = null
        capturedPhotoFile = null
        uploadCapturedBtn.visibility = View.GONE
    }
    
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                Toast.makeText(requireContext(), "Permission granted. Please reopen the tab to see screenshots.", Toast.LENGTH_SHORT).show()
                Log.d("FileListFragment", "All permissions granted.")
            } else {
                Toast.makeText(requireContext(), "Permission denied. Cannot show screenshots list.", Toast.LENGTH_LONG).show()
                Log.d("FileListFragment", "Permission denied.")
                emptyListText.text = "Permission denied. Cannot show screenshots."
                emptyListText.visibility = View.VISIBLE
                showPermissionSettingsDialog()
            }
        }
    }

    private fun showPermissionSettingsDialog() {
        androidx.appcompat.app.AlertDialog.Builder(requireContext())
            .setTitle("Permission Required")
            .setMessage("This app needs permission to access your screenshots. Please grant storage or media permissions in settings.")
            .setPositiveButton("Open Settings") { _, _ ->
                val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                intent.data = Uri.fromParts("package", requireContext().packageName, null)
                startActivity(intent)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
    
    companion object {
        fun newInstance(): FileListFragment {
            return FileListFragment()
        }
    }
} 