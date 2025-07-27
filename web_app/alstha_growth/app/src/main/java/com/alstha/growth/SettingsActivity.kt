package com.alstha.growth

import android.content.Context
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class SettingsActivity : AppCompatActivity() {
    
    private lateinit var connectionStatusText: TextView
    private lateinit var reconnectButton: Button
    private lateinit var connectionManager: ConnectionManager
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)
        
        connectionStatusText = findViewById(R.id.connectionStatusText)
        reconnectButton = findViewById(R.id.reconnectButton)
        connectionManager = ConnectionManager.getInstance(this)
        
        reconnectButton.setOnClickListener {
            connectionManager.forceReconnect()
            updateConnectionStatus()
        }
        
        // Initialize connection and update status
        connectionManager.initializeConnection { connectedIp ->
            runOnUiThread {
                updateConnectionStatus()
                Toast.makeText(this, "Connected to: $connectedIp", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    private fun updateConnectionStatus() {
        val status = connectionManager.getConnectionStatus()
        connectionStatusText.text = status
        
        // Update text color based on connection
        if (connectionManager.isPrimaryServerActive()) {
            connectionStatusText.setTextColor(0xFF4CAF50.toInt()) // Green for primary
        } else {
            connectionStatusText.setTextColor(0xFFFF9800.toInt()) // Orange for secondary
        }
    }
    
    companion object {
        fun getServerIp(context: Context): String {
            return ConnectionManager.getInstance(context).getCurrentServerIp()
        }
        
        fun getServerUrl(context: Context): String {
            return ConnectionManager.getInstance(context).getServerUrl()
        }
    }
} 