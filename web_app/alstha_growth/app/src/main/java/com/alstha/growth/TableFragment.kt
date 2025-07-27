package com.alstha.growth

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView

class TableFragment : Fragment() {
    private lateinit var recyclerView: RecyclerView
    private lateinit var btnBack: Button
    private lateinit var dbHelper: DailyLogsDatabaseHelper
    private lateinit var adapter: TableAdapter

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_table, container, false)
        recyclerView = view.findViewById(R.id.recyclerView)
        btnBack = view.findViewById(R.id.btnBack)
        dbHelper = DailyLogsDatabaseHelper(requireContext())
        return view
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        recyclerView.layoutManager = LinearLayoutManager(context)
        val logs = dbHelper.getAllLogs()
        adapter = TableAdapter(logs)
        recyclerView.adapter = adapter
        btnBack.setOnClickListener {
            requireActivity().supportFragmentManager.popBackStack()
        }
    }

    companion object {
        fun newInstance(): TableFragment {
            return TableFragment()
        }
    }
} 