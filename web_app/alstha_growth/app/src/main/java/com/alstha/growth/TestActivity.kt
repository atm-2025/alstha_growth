package com.alstha.growth

import android.os.Bundle
import android.util.Log
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class TestActivity : AppCompatActivity() {
    
    override fun onCreate(savedInstanceState: Bundle?) {
        try {
            super.onCreate(savedInstanceState)
            
            // Create a simple layout programmatically
            val textView = TextView(this)
            textView.text = "App is working!\n\nIf you can see this, the basic app functionality is working."
            textView.textSize = 18f
            textView.setPadding(50, 50, 50, 50)
            
            setContentView(textView)
            
            Log.d("TestActivity", "TestActivity created successfully")
            
        } catch (e: Exception) {
            Log.e("TestActivity", "Error in TestActivity", e)
            // Show error on screen
            val errorView = TextView(this)
            errorView.text = "Error: ${e.message}\n\n${e.stackTraceToString()}"
            errorView.textSize = 12f
            errorView.setPadding(20, 20, 20, 20)
            setContentView(errorView)
        }
    }
} 