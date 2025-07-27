package com.alstha.growth

data class DailyLogEntry(
    val no: Int,
    val date: String,
    val name: String,
    val type: String,
    val status: String,
    val remark: String,
    val duration: String,
    val attention: Int,
    val descp: String,
    val energyLevel: Int,
    val links: String? = null
) 