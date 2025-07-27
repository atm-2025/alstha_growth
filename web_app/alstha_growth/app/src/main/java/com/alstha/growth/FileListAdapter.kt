package com.alstha.growth

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.button.MaterialButton
import java.text.SimpleDateFormat
import java.util.*
import android.graphics.BitmapFactory

class FileListAdapter(
    private val onFileClick: (FileInfo) -> Unit,
    private val onDownloadClick: (FileInfo) -> Unit,
    private val onDeleteClick: (FileInfo) -> Unit
) : RecyclerView.Adapter<FileListAdapter.FileViewHolder>() {
    
    private var files: List<FileInfo> = emptyList()
    
    fun updateFiles(newFiles: List<FileInfo>) {
        files = newFiles
        notifyDataSetChanged()
    }
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): FileViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_file, parent, false)
        return FileViewHolder(view)
    }
    
    override fun onBindViewHolder(holder: FileViewHolder, position: Int) {
        holder.bind(files[position])
    }
    
    override fun getItemCount(): Int = files.size
    
    inner class FileViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val thumbnailPreview: ImageView = itemView.findViewById(R.id.thumbnailPreview)
        private val fileIcon: ImageView = itemView.findViewById(R.id.fileIcon)
        private val fileName: TextView = itemView.findViewById(R.id.fileName)
        private val fileType: TextView = itemView.findViewById(R.id.fileType)
        private val fileSize: TextView = itemView.findViewById(R.id.fileSize)
        private val fileDate: TextView = itemView.findViewById(R.id.fileDate)
        private val downloadBtn: MaterialButton = itemView.findViewById(R.id.downloadBtn)
        // Removed deleteBtn
        fun bind(fileInfo: FileInfo) {
            fileName.text = fileInfo.name
            fileType.text = fileInfo.extension.uppercase()
            fileSize.text = fileInfo.size
            // Format date safely
            try {
                val modified = fileInfo.modified ?: 0L
                val date = Date(modified * 1000)
                val dateFormat = SimpleDateFormat("MMM dd, HH:mm", Locale.getDefault())
                fileDate.text = dateFormat.format(date)
            } catch (e: Exception) {
                fileDate.text = "-"
            }
            val imageExts = listOf("jpg", "jpeg", "png", "gif", "bmp", "webp")
            if (imageExts.contains(fileInfo.extension.lowercase())) {
                // Show thumbnail
                try {
                    val filePath = fileInfo.path ?: (android.os.Environment.getExternalStorageDirectory().absolutePath + "/Pictures/Screenshots/" + fileInfo.name)
                    android.util.Log.d("FileListAdapter", "Loading thumbnail: $filePath")
                    val file = java.io.File(filePath)
                    if (file.exists()) {
                        val bmp = BitmapFactory.decodeFile(file.absolutePath)
                        thumbnailPreview.setImageBitmap(bmp)
                        thumbnailPreview.visibility = View.VISIBLE
                        fileIcon.visibility = View.GONE
                    } else {
                        thumbnailPreview.visibility = View.GONE
                        fileIcon.visibility = View.VISIBLE
                    }
                } catch (e: Exception) {
                    thumbnailPreview.visibility = View.GONE
                    fileIcon.visibility = View.VISIBLE
                }
            } else {
                thumbnailPreview.visibility = View.GONE
                fileIcon.visibility = View.VISIBLE
            }
            itemView.setOnClickListener { onFileClick(fileInfo) }
            downloadBtn.setOnClickListener { onDownloadClick(fileInfo) }
        }
    }
} 