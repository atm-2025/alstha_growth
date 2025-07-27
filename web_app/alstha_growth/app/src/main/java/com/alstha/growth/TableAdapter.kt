package com.alstha.growth

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class TableAdapter(private val logs: List<DailyLogEntry>) : RecyclerView.Adapter<TableAdapter.ViewHolder>() {
    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val date: TextView = view.findViewById(R.id.cellDate)
        val name: TextView = view.findViewById(R.id.cellName)
        val type: TextView = view.findViewById(R.id.cellType)
        val status: TextView = view.findViewById(R.id.cellStatus)
        val remarks: TextView = view.findViewById(R.id.cellRemarks)
        val duration: TextView = view.findViewById(R.id.cellDuration)
        val attention: TextView = view.findViewById(R.id.cellAttention)
        val energy: TextView = view.findViewById(R.id.cellEnergy)
        val links: TextView = view.findViewById(R.id.cellLinks)
        val desp: TextView = view.findViewById(R.id.cellDesp)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_table_row, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val log = logs[position]
        holder.date.text = log.date
        holder.name.text = log.name
        holder.type.text = log.type
        holder.status.text = log.status
        holder.remarks.text = log.remark
        holder.duration.text = log.duration
        holder.attention.text = log.attention.toString()
        holder.energy.text = log.energyLevel.toString()
        holder.links.text = log.links ?: ""
        holder.desp.text = log.descp
    }

    override fun getItemCount(): Int = logs.size
} 