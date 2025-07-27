package com.alstha.growth

data class LLMChatMessage(
    val timestamp: Long,
    val provider: String,
    val role: String,
    val message: String
) 