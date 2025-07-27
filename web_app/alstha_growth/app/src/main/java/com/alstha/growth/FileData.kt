package com.alstha.growth

import com.google.gson.annotations.SerializedName

data class FileInfo(
    @SerializedName("name")
    val name: String = "",
    
    @SerializedName("size")
    val size: String = "",
    
    @SerializedName("size_bytes")
    val sizeBytes: Long = 0L,
    
    @SerializedName("modified")
    val modified: Long? = 0L,
    
    @SerializedName("extension")
    val extension: String = "",
    
    val path: String? = null
)

data class FileListResponse(
    @SerializedName("status")
    val status: String,
    
    @SerializedName("files")
    val files: List<FileInfo>,
    
    @SerializedName("count")
    val count: Int
)

data class FileDetailResponse(
    @SerializedName("status")
    val status: String,
    
    @SerializedName("file")
    val file: FileDetail
)

data class FileDetail(
    @SerializedName("name")
    val name: String,
    
    @SerializedName("size")
    val size: String,
    
    @SerializedName("size_bytes")
    val sizeBytes: Long,
    
    @SerializedName("modified")
    val modified: Long,
    
    @SerializedName("created")
    val created: Long,
    
    @SerializedName("extension")
    val extension: String,
    
    @SerializedName("path")
    val path: String
)

data class ApiResponse(
    @SerializedName("status")
    val status: String,
    
    @SerializedName("message")
    val message: String? = null,
    
    @SerializedName("error")
    val error: String? = null
) 