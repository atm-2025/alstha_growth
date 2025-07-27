package com.alstha.growth

import android.content.Context
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.util.concurrent.TimeUnit

class ConnectionManager private constructor(private val context: Context) {
    
    companion object {
        private const val TAG = "ConnectionManager"
        private const val PRIMARY_IP = "192.168.1.111"
        private const val SECONDARY_IP = "192.168.1.112"
        private const val PORT = "5000"
        private const val TIMEOUT_SECONDS = 3L
        
        @Volatile
        private var INSTANCE: ConnectionManager? = null
        
        fun getInstance(context: Context): ConnectionManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: ConnectionManager(context).also { INSTANCE = it }
            }
        }
    }
    
    private var currentServerIp: String = PRIMARY_IP
    private val client = OkHttpClient.Builder()
        .connectTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .readTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .writeTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .build()
    
    private var isCheckingConnection = false
    private var connectionCheckCallback: ((String) -> Unit)? = null
    
    fun getCurrentServerIp(): String {
        return currentServerIp
    }
    
    fun getServerUrl(): String {
        return "http://$currentServerIp:$PORT"
    }
    
    fun initializeConnection(callback: (String) -> Unit) {
        connectionCheckCallback = callback
        checkAndSwitchConnection()
    }
    
    private fun checkAndSwitchConnection() {
        if (isCheckingConnection) return
        
        isCheckingConnection = true
        CoroutineScope(Dispatchers.IO).launch {
            try {
                Log.d(TAG, "Starting connection check...")
                
                // First try the primary IP (192.168.1.111)
                if (isServerReachable(PRIMARY_IP)) {
                    currentServerIp = PRIMARY_IP
                    Log.d(TAG, "Connected to primary server: $PRIMARY_IP")
                    withContext(Dispatchers.Main) {
                        connectionCheckCallback?.invoke(PRIMARY_IP)
                    }
                    isCheckingConnection = false
                    return@launch
                }
                
                // If primary is not reachable, try secondary IP (192.168.1.112)
                if (isServerReachable(SECONDARY_IP)) {
                    currentServerIp = SECONDARY_IP
                    Log.d(TAG, "Connected to secondary server: $SECONDARY_IP")
                    withContext(Dispatchers.Main) {
                        connectionCheckCallback?.invoke(SECONDARY_IP)
                    }
                    isCheckingConnection = false
                    return@launch
                }
                
                // If both are unreachable, try to detect the actual IP
                Log.d(TAG, "Both expected IPs failed, trying to detect actual server IP...")
                val detectedIp = detectServerIp()
                if (detectedIp != null && isServerReachable(detectedIp)) {
                    currentServerIp = detectedIp
                    Log.d(TAG, "Connected to detected server: $detectedIp")
                    withContext(Dispatchers.Main) {
                        connectionCheckCallback?.invoke(detectedIp)
                    }
                    isCheckingConnection = false
                    return@launch
                }
                
                // If all attempts fail, keep current IP and log error
                Log.e(TAG, "All connection attempts failed")
                withContext(Dispatchers.Main) {
                    connectionCheckCallback?.invoke(currentServerIp)
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Error checking connection: ${e.message}")
                withContext(Dispatchers.Main) {
                    connectionCheckCallback?.invoke(currentServerIp)
                }
            } finally {
                isCheckingConnection = false
            }
        }
    }
    
    private fun isServerReachable(ip: String): Boolean {
        return try {
            Log.d(TAG, "Checking server reachability for $ip")
            
            // First check the main server on port 5000
            val mainUrl = "http://$ip:$PORT/"
            Log.d(TAG, "Testing main server: $mainUrl")
            val mainRequest = Request.Builder().url(mainUrl).build()
            val mainResponse = client.newCall(mainRequest).execute()
            val mainSuccess = mainResponse.isSuccessful
            mainResponse.close()
            
            if (!mainSuccess) {
                Log.e(TAG, "Main server $ip:$PORT is not reachable - HTTP ${mainResponse.code}")
                return false
            }
            
            Log.d(TAG, "Main server $ip:$PORT is reachable")
            
            // Then check the command server on port 5000 (same port as main server)
            val commandUrl = "http://$ip:5000/command"
            Log.d(TAG, "Testing command server: $commandUrl")
            val commandRequest = Request.Builder().url(commandUrl).build()
            val commandResponse = client.newCall(commandRequest).execute()
            val commandSuccess = commandResponse.isSuccessful
            commandResponse.close()
            
            if (!commandSuccess) {
                Log.e(TAG, "Command server $ip:5000 is not reachable - HTTP ${commandResponse.code}")
                return false
            }
            
            Log.d(TAG, "Both servers on $ip are reachable")
            true
        } catch (e: Exception) {
            when (e) {
                is ConnectException, is SocketTimeoutException -> {
                    Log.e(TAG, "Server $ip is not reachable: ${e.message}")
                    false
                }
                else -> {
                    Log.e(TAG, "Error checking server $ip: ${e.message}")
                    false
                }
            }
        }
    }
    
    private fun detectServerIp(): String? {
        // Try common local network IP ranges
        val commonRanges = listOf(
            "192.168.1", "192.168.0", "10.0.0", "172.16.0"
        )
        
        for (range in commonRanges) {
            for (i in 1..254) {
                val testIp = "$range.$i"
                if (testIp != "192.168.1.11") { // Skip Android device IP
                    Log.d(TAG, "Trying to detect server at: $testIp")
                    if (isServerReachable(testIp)) {
                        Log.d(TAG, "Detected server at: $testIp")
                        return testIp
                    }
                }
            }
        }
        return null
    }
    
    fun forceReconnect() {
        Log.d(TAG, "Forcing reconnection...")
        checkAndSwitchConnection()
    }
    
    fun isPrimaryServerActive(): Boolean {
        return currentServerIp == PRIMARY_IP
    }
    
    fun getConnectionStatus(): String {
        return if (isPrimaryServerActive()) {
            "Connected to primary server ($PRIMARY_IP)"
        } else {
            "Connected to secondary server ($SECONDARY_IP)"
        }
    }
} 