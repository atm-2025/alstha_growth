package com.alstha.growth

import retrofit2.Call
import retrofit2.http.*
import okhttp3.MultipartBody

interface ApiService {
    @GET("test")
    fun testConnection(): Call<Map<String, Any>>
    
    @GET("health")
    fun healthCheck(): Call<Map<String, Any>>
    
    @GET("files")
    fun getFileList(): Call<FileListResponse>
    
    @GET("file-info/{filename}")
    fun getFileInfo(@Path("filename") filename: String): Call<FileDetailResponse>
    
    @DELETE("delete/{filename}")
    fun deleteFile(@Path("filename") filename: String): Call<ApiResponse>

    @Multipart
    @POST("upload")
    fun uploadFile(
        @Part file: MultipartBody.Part,
        @Part("source") source: okhttp3.RequestBody
    ): Call<okhttp3.ResponseBody>
}