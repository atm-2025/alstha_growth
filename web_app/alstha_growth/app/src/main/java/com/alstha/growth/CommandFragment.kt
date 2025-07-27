// CommandFragment: Fragment for command input and output. Executes commands on the Windows client via HTTP.
package com.alstha.growth

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Spinner
import android.widget.ArrayAdapter
import android.widget.TextView
import com.google.android.material.button.MaterialButton
import androidx.fragment.app.Fragment
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class CommandFragment : Fragment() {
    private lateinit var commandSpinner: Spinner
    private lateinit var sendBtn: MaterialButton
    private lateinit var outputView: TextView
    private lateinit var connectionStatusView: TextView

    private val commands = listOf(
        "Sleep",
        "Shutdown",
        "Hibernate",
        "Restart",
        "Open Notepad",
        "Lock Workstation",
        "Open Calculator",
        "Show IP Address",
        "Take Screenshot",
        "Show Message Box"
    )
    private val commandActions = mapOf(
        "Sleep" to "sleep",
        "Shutdown" to "shutdown",
        "Hibernate" to "hibernate",
        "Restart" to "restart",
        "Open Notepad" to "open_notepad",
        "Lock Workstation" to "lock_workstation",
        "Open Calculator" to "open_calculator",
        "Show IP Address" to "show_ip_address",
        "Take Screenshot" to "take_screenshot",
        "Show Message Box" to "show_message_box"
    )

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_command, container, false)
        commandSpinner = view.findViewById(R.id.commandSpinner)
        sendBtn = view.findViewById(R.id.sendBtn)
        outputView = view.findViewById(R.id.outputView)
        connectionStatusView = view.findViewById(R.id.connectionStatusView)
        
        val adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, commands)
        commandSpinner.adapter = adapter
        sendBtn.setOnClickListener { executeCommand() }
        
        // Update connection status
        updateConnectionStatus()
        
        return view
    }
    
    private fun updateConnectionStatus() {
        val connectionManager = ConnectionManager.getInstance(requireContext())
        val status = connectionManager.getConnectionStatus()
        connectionStatusView.text = status
        
        // Update text color based on connection
        if (connectionManager.isPrimaryServerActive()) {
            connectionStatusView.setTextColor(0xFF4CAF50.toInt()) // Green for primary
        } else {
            connectionStatusView.setTextColor(0xFFFF9800.toInt()) // Orange for secondary
        }
    }

    private fun executeCommand() {
        val command = commandSpinner.selectedItem?.toString() ?: ""
        val action = commandActions[command] ?: return
        outputView.text = "Sending command: $command..."
        
        // Update connection status before sending
        updateConnectionStatus()
        
        CoroutineScope(Dispatchers.IO).launch {
            val result = sendCommandToWindows(action)
            withContext(Dispatchers.Main) {
                outputView.text = result
                // Update connection status after sending
                updateConnectionStatus()
            }
        }
    }

    private fun sendCommandToWindows(action: String): String {
        return try {
            val connectionManager = ConnectionManager.getInstance(requireContext())
            val serverIp = connectionManager.getCurrentServerIp()
            val url = "http://$serverIp:5000/command"
            
            // Use shorter timeout to match ConnectionManager
            val client = OkHttpClient.Builder()
                .connectTimeout(3, TimeUnit.SECONDS)
                .readTimeout(3, TimeUnit.SECONDS)
                .writeTimeout(3, TimeUnit.SECONDS)
                .build()
                
            val json = JSONObject().put("action", action).toString()
            val body = json.toRequestBody("application/json".toMediaTypeOrNull())
            val request = Request.Builder().url(url).post(body).build()
            val response = client.newCall(request).execute()
            if (response.isSuccessful) {
                val respJson = JSONObject(response.body?.string() ?: "")
                "Result: ${respJson.optString("result", "No result")}".also { response.close() }
            } else {
                "Error: ${response.code} ${response.message}".also { response.close() }
            }
        } catch (e: Exception) {
            // If connection fails, try to reconnect and retry once
            if (e.message?.contains("failed to connect") == true || e.message?.contains("timeout") == true) {
                try {
                    // Force reconnection to try secondary IP
                    val connectionManager = ConnectionManager.getInstance(requireContext())
                    connectionManager.forceReconnect()
                    
                    // Wait a moment for reconnection
                    Thread.sleep(1000)
                    
                    // Try again with new IP
                    val newServerIp = connectionManager.getCurrentServerIp()
                    val url = "http://$newServerIp:5000/command"
                    
                    // Use shorter timeout for retry too
                    val client = OkHttpClient.Builder()
                        .connectTimeout(3, TimeUnit.SECONDS)
                        .readTimeout(3, TimeUnit.SECONDS)
                        .writeTimeout(3, TimeUnit.SECONDS)
                        .build()
                        
                    val json = JSONObject().put("action", action).toString()
                    val body = json.toRequestBody("application/json".toMediaTypeOrNull())
                    val request = Request.Builder().url(url).post(body).build()
                    val response = client.newCall(request).execute()
                    if (response.isSuccessful) {
                        val respJson = JSONObject(response.body?.string() ?: "")
                        "Result: ${respJson.optString("result", "No result")} (Connected to: $newServerIp)".also { response.close() }
                    } else {
                        "Error: ${response.code} ${response.message}".also { response.close() }
                    }
                } catch (retryException: Exception) {
                    "Failed to send command after retry: ${retryException.message}"
                }
            } else {
                "Failed to send command: ${e.message}"
            }
        }
    }

    companion object {
        fun newInstance() = CommandFragment()
    }
} 