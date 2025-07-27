package com.alstha.growth

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class DailyLogsAdapter(
    private val logs: List<DailyLogEntry>,
    private val onEdit: (DailyLogEntry) -> Unit,
    private val onDelete: (DailyLogEntry) -> Unit
) : RecyclerView.Adapter<DailyLogsAdapter.LogViewHolder>() {
    class LogViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val noText: TextView = itemView.findViewById(R.id.logNoText)
        val dateText: TextView = itemView.findViewById(R.id.logDateText)
        val nameText: TextView = itemView.findViewById(R.id.logNameText)
        val typeText: TextView = itemView.findViewById(R.id.logTypeText)
        val statusText: TextView = itemView.findViewById(R.id.logStatusText)
        val remarkText: TextView = itemView.findViewById(R.id.logRemarkText)
        val durationText: TextView = itemView.findViewById(R.id.logDurationText)
        val attentionText: TextView = itemView.findViewById(R.id.logAttentionText)
        val descpText: TextView = itemView.findViewById(R.id.logDescpText)
        val energyLevelText: TextView = itemView.findViewById(R.id.logEnergyLevelText)
        val editBtn: Button = itemView.findViewById(R.id.editLogBtn)
        val deleteBtn: Button = itemView.findViewById(R.id.deleteLogBtn)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): LogViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_daily_log, parent, false)
        return LogViewHolder(view)
    }

    override fun onBindViewHolder(holder: LogViewHolder, position: Int) {
        val log = logs[position]
        holder.noText.text = "No: ${log.no}"
        holder.dateText.text = "Date: ${log.date}"
        holder.nameText.text = "Name: ${log.name}"
        holder.typeText.text = "Type: ${log.type}"
        holder.statusText.text = "Status: ${log.status}"
        holder.remarkText.text = "Remark: ${log.remark}"
        holder.durationText.text = "Duration: ${log.duration}"
        holder.attentionText.text = "Attention: ${log.attention}"
        holder.descpText.text = "Description: ${log.descp}"
        holder.energyLevelText.text = "Energy Level: ${log.energyLevel}"
        holder.editBtn.setOnClickListener { onEdit(log) }
        holder.deleteBtn.setOnClickListener { onDelete(log) }
    }

    override fun getItemCount(): Int = logs.size
}
