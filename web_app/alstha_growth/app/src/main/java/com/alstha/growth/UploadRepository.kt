package com.alstha.growth

import android.util.Log
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.ResponseBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.io.File
import com.alstha.growth.ApiService
import okhttp3.RequestBody
import okio.BufferedSink
import okio.source

// Define your ApiService interface if it's not already defined elsewhere
// For example:
//interface ApiService {
//    @Multipart
//    @POST("upload") // Replace "upload" with your actual upload endpoint
//    fun uploadImage(@Part image: MultipartBody.Part): Call<ResponseBody>
//}

class UploadRepository(private val serverIp: String) {
    private val api: ApiService
    private val baseUrl: String = "http://$serverIp:5000/"

    init {
        Log.d("NETWORK", "Using server URL: $baseUrl")
        val client = OkHttpClient.Builder()
            .connectTimeout(60, java.util.concurrent.TimeUnit.SECONDS)
            .readTimeout(300, java.util.concurrent.TimeUnit.SECONDS)  // 5 minutes for large files
            .writeTimeout(300, java.util.concurrent.TimeUnit.SECONDS) // 5 minutes for large files
            .addInterceptor { chain ->
                val original = chain.request()
                val requestBuilder = original.newBuilder()
                    .header("Source", "mobile")
                    .method(original.method, original.body)
                chain.proceed(requestBuilder.build())
            }
            .build()
            
        val retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        api = retrofit.create(ApiService::class.java)
    }

    fun uploadImage(file: File, onResult: (String?) -> Unit) {
        uploadFile(file, onResult)
    }

    fun uploadFile(file: File, onResult: (String?) -> Unit, onProgress: ((Int) -> Unit)? = null) {
        val mimeType = getMimeType(file)
        val reqFile = ProgressRequestBody(file, mimeType, onProgress)
        val body = MultipartBody.Part.createFormData("file", file.name, reqFile)
        val sourcePart = "mobile".toRequestBody("text/plain".toMediaTypeOrNull())

        api.uploadFile(body, sourcePart).enqueue(object : Callback<ResponseBody> {
            override fun onResponse(call: Call<ResponseBody>, response: Response<ResponseBody>) {
                if (response.isSuccessful) {
                    val result = response.body()?.string()
                    onResult(result)
                    Log.d("UploadRepository", "Upload successful: $result")
                } else {
                    val errorBody = response.errorBody()?.string()
                    onResult("Upload failed: ${response.code()} - $errorBody")
                    Log.e("UploadRepository", "Upload failed: ${response.code()} - $errorBody")
                }
            }

            override fun onFailure(call: Call<ResponseBody>, t: Throwable) {
                Log.e("UploadRepository", "Upload error", t)
                onResult("Error: ${t.message}")
            }
        })
    }

    private fun getMimeType(file: File): String {
        val fileName = file.name.lowercase()
        return when {
            // Images
            fileName.endsWith(".jpg") || fileName.endsWith(".jpeg") -> "image/jpeg"
            fileName.endsWith(".png") -> "image/png"
            fileName.endsWith(".gif") -> "image/gif"
            fileName.endsWith(".bmp") -> "image/bmp"
            fileName.endsWith(".webp") -> "image/webp"
            fileName.endsWith(".tiff") || fileName.endsWith(".tif") -> "image/tiff"
            fileName.endsWith(".svg") -> "image/svg+xml"
            
            // Videos
            fileName.endsWith(".mp4") -> "video/mp4"
            fileName.endsWith(".avi") -> "video/x-msvideo"
            fileName.endsWith(".mov") -> "video/quicktime"
            fileName.endsWith(".mkv") -> "video/x-matroska"
            fileName.endsWith(".wmv") -> "video/x-ms-wmv"
            fileName.endsWith(".flv") -> "video/x-flv"
            fileName.endsWith(".webm") -> "video/webm"
            fileName.endsWith(".3gp") -> "video/3gpp"
            fileName.endsWith(".m4v") -> "video/x-m4v"
            
            // Audio
            fileName.endsWith(".mp3") -> "audio/mpeg"
            fileName.endsWith(".wav") -> "audio/wav"
            fileName.endsWith(".flac") -> "audio/flac"
            fileName.endsWith(".aac") -> "audio/aac"
            fileName.endsWith(".ogg") -> "audio/ogg"
            fileName.endsWith(".wma") -> "audio/x-ms-wma"
            fileName.endsWith(".m4a") -> "audio/mp4"
            
            // Documents
            fileName.endsWith(".pdf") -> "application/pdf"
            fileName.endsWith(".doc") -> "application/msword"
            fileName.endsWith(".docx") -> "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            fileName.endsWith(".xls") -> "application/vnd.ms-excel"
            fileName.endsWith(".xlsx") -> "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            fileName.endsWith(".ppt") -> "application/vnd.ms-powerpoint"
            fileName.endsWith(".pptx") -> "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            fileName.endsWith(".txt") -> "text/plain"
            fileName.endsWith(".csv") -> "text/csv"
            fileName.endsWith(".json") -> "application/json"
            fileName.endsWith(".xml") -> "application/xml"
            fileName.endsWith(".html") || fileName.endsWith(".htm") -> "text/html"
            fileName.endsWith(".css") -> "text/css"
            fileName.endsWith(".js") -> "application/javascript"
            fileName.endsWith(".md") -> "text/markdown"
            fileName.endsWith(".rtf") -> "application/rtf"
            
            // Archives
            fileName.endsWith(".zip") -> "application/zip"
            fileName.endsWith(".rar") -> "application/x-rar-compressed"
            fileName.endsWith(".7z") -> "application/x-7z-compressed"
            fileName.endsWith(".tar") -> "application/x-tar"
            fileName.endsWith(".gz") -> "application/gzip"
            fileName.endsWith(".bz2") -> "application/x-bzip2"
            
            // Executables and binaries
            fileName.endsWith(".apk") -> "application/vnd.android.package-archive"
            fileName.endsWith(".exe") -> "application/x-msdownload"
            fileName.endsWith(".dmg") -> "application/x-apple-diskimage"
            fileName.endsWith(".deb") -> "application/vnd.debian.binary-package"
            fileName.endsWith(".rpm") -> "application/x-rpm"
            
            // Other common formats
            fileName.endsWith(".iso") -> "application/x-iso9660-image"
            fileName.endsWith(".torrent") -> "application/x-bittorrent"
            fileName.endsWith(".epub") -> "application/epub+zip"
            fileName.endsWith(".mobi") -> "application/x-mobipocket-ebook"
            
            else -> "application/octet-stream" // Default for unknown file types
        }
    }

    fun testConnection(onResult: (Boolean) -> Unit) {
        // Create a simple test call to the server root endpoint
        val client = OkHttpClient.Builder()
            .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
            .readTimeout(60, java.util.concurrent.TimeUnit.SECONDS)
            .addInterceptor { chain ->
                val original = chain.request()
                val requestBuilder = original.newBuilder()
                    .header("Source", "mobile")
                    .method(original.method, original.body)
                chain.proceed(requestBuilder.build())
            }
            .build()
            
        val retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        
        val testApi = retrofit.create(TestApiService::class.java)
        testApi.testConnection().enqueue(object : Callback<ResponseBody> {
            override fun onResponse(call: Call<ResponseBody>, response: Response<ResponseBody>) {
                onResult(response.isSuccessful)
            }

            override fun onFailure(call: Call<ResponseBody>, t: Throwable) {
                onResult(false)
            }
        })
    }
}

// Simple interface for testing connection
interface TestApiService {
    @retrofit2.http.GET("/")
    fun testConnection(): Call<ResponseBody>
}

class ProgressRequestBody(
    private val file: File,
    private val contentType: String,
    private val onProgress: ((Int) -> Unit)?
) : RequestBody() {
    override fun contentType() = contentType.toMediaTypeOrNull()
    override fun contentLength() = file.length()
    override fun writeTo(sink: BufferedSink) {
        val length = contentLength()
        val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
        file.inputStream().use { input ->
            var uploaded = 0L
            var read: Int
            while (input.read(buffer).also { read = it } != -1) {
                sink.write(buffer, 0, read)
                uploaded += read
                val progress = (100 * uploaded / length).toInt()
                onProgress?.invoke(progress)
            }
        }
    }
    companion object {
        private const val DEFAULT_BUFFER_SIZE = 2048
    }
}

