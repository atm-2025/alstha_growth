package com.alstha.growth

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class ResultActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_result)
        val resultText = intent.getStringExtra("result") ?: "No result"
        findViewById<TextView>(R.id.resultTextView).text = resultText
    }
} 