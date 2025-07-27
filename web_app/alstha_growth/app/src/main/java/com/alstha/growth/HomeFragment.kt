package com.alstha.growth

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import androidx.fragment.app.Fragment
import androidx.appcompat.widget.Toolbar

class HomeFragment : Fragment() {
    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_home, container, false)
        val btnDailyLogs = view.findViewById<Button>(R.id.btnDailyLogs)
        val btnLLMs = view.findViewById<Button>(R.id.btnLLMs)
        val btnFileUpload = view.findViewById<Button>(R.id.btnFileUpload)
        val btnUploadText = view.findViewById<Button>(R.id.btnUploadText)
        btnDailyLogs.setOnClickListener {
            (activity as? MainActivity)?.showFragment(DailyLogsFragment.newInstance())
            (activity as? MainActivity)?.supportActionBar?.title = "Daily Logs"
        }
        btnLLMs.setOnClickListener {
            (activity as? MainActivity)?.showFragment(LLMFragment.newInstance())
            (activity as? MainActivity)?.supportActionBar?.title = "LLM"
        }
        btnFileUpload.setOnClickListener {
            (activity as? MainActivity)?.showFragment(FileListFragment.newInstance())
            (activity as? MainActivity)?.supportActionBar?.title = "File Upload"
        }
        btnUploadText.setOnClickListener {
            (activity as? MainActivity)?.showUploadTextDialog()
        }
        return view
    }
    companion object {
        fun newInstance(): HomeFragment {
            return HomeFragment()
        }
    }
} 