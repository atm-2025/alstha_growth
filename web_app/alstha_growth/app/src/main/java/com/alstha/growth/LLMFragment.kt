package com.alstha.growth

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import java.text.SimpleDateFormat
import java.util.*
import com.alstha.growth.LLMChatMessage
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.widget.Toolbar
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class LLMFragment : Fragment() {
    private lateinit var providerSpinner: Spinner
    private lateinit var chatRecycler: RecyclerView
    private lateinit var inputBox: TextInputEditText
    private lateinit var sendBtn: MaterialButton
    private lateinit var micBtn: MaterialButton
    private lateinit var seeMoreBtn: Button
    private lateinit var chatAdapter: LLMChatAdapter
    private lateinit var dbHelper: DailyLogsDatabaseHelper
    private var selectedProvider: String = "Groq"
    private var offset = 0
    private val pageSize = 10
    private val chatList = mutableListOf<LLMChatMessage>()
    private val providerList = listOf("Groq", "Cohere", "OpenRouter", "Gemini", "Cerebras", "Mistral", "Mixtral")
    private val providerDisplay = mapOf(
        "Groq" to "Groq",
        "Cohere" to "Cohere",
        "OpenRouter" to "DeepSeek",
        "Gemini" to "Gemini",
        "Cerebras" to "Cerebras",
        "Mistral" to "Mistral",
        "Mixtral" to "Mixtral"
    )
    private val apiKeys = mapOf(
        "Groq" to "YOUR_GROQ_API_KEY_HERE",
        "Cohere" to "YOUR_COHERE_API_KEY_HERE",
        "OpenRouter" to "YOUR_OPENROUTER_API_KEY_HERE",
        "GoogleGemini" to "YOUR_GOOGLE_GEMINI_API_KEY_HERE",
        "Cerebras" to "YOUR_CEREBRAS_API_KEY_HERE",
        "Mistral" to "YOUR_MISTRAL_API_KEY_HERE",
        "Mixtral" to "YOUR_MIXTRAL_API_KEY_HERE"
    )
    private val modelMap = mapOf(
        "Groq" to "llama3-70b-8192",
        "Cohere" to "command-r-plus",
        "OpenRouter" to "deepseek/deepseek-chat-v3-0324",
        "GoogleGemini" to "gemini-2.5-flash",
        "Cerebras" to "cerebras/cerebras-gpt-4-256k",
        "Mistral" to "mistralai/mistral-7b-instruct",
        "Mixtral" to "mistralai/mixtral-8x7b-instruct"
    )
    private val REQ_CODE_SPEECH = 1001
    private var backCallback: OnBackPressedCallback? = null
    private lateinit var toolbar: Toolbar

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_llm, container, false)
        // Removed toolbar navigation icon (back button) setup
        providerSpinner = view.findViewById(R.id.providerSpinner)
        chatRecycler = view.findViewById(R.id.chatRecycler)
        inputBox = view.findViewById(R.id.inputBox)
        sendBtn = view.findViewById(R.id.sendBtn)
        micBtn = view.findViewById(R.id.micBtn)
        micBtn.setIconResource(android.R.drawable.ic_btn_speak_now)
        seeMoreBtn = view.findViewById(R.id.seeMoreBtn)
        dbHelper = DailyLogsDatabaseHelper(requireContext())
        setupProviderSelection()
        setupChatRecycler()
        setupInput()
        loadHistory(reset = true)
        // Set input box hint color to black
        inputBox.setHintTextColor(0xFF222222.toInt())
        // Set spinner text color to black
        val adapter = providerSpinner.adapter as? ArrayAdapter<*>
        adapter?.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        providerSpinner.setPopupBackgroundResource(android.R.color.white)
        // Removed reference to top_empty_band
        return view
    }

    override fun onResume() {
        super.onResume()
        backCallback = object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                (activity as? MainActivity)?.showFragment(HomeFragment.newInstance())
                (activity as? MainActivity)?.supportActionBar?.title = "Home"
            }
        }
        requireActivity().onBackPressedDispatcher.addCallback(this, backCallback!!)
    }

    override fun onPause() {
        super.onPause()
        backCallback?.remove()
    }

    private fun setupProviderSelection() {
        val adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, providerList.map { providerDisplay[it] })
        providerSpinner.adapter = adapter
        providerSpinner.setSelection(providerList.indexOf(selectedProvider))
        providerSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>, view: View?, position: Int, id: Long) {
                selectedProvider = providerList[position]
            }
            override fun onNothingSelected(parent: AdapterView<*>) {}
        }
    }

    private fun setupChatRecycler() {
        chatAdapter = LLMChatAdapter(chatList)
        val layoutManager = LinearLayoutManager(requireContext())
        layoutManager.isItemPrefetchEnabled = true
        layoutManager.initialPrefetchItemCount = 10
        chatRecycler.layoutManager = layoutManager
        chatRecycler.adapter = chatAdapter
        chatRecycler.setHasFixedSize(false)
        chatRecycler.isNestedScrollingEnabled = true
    }

    private fun setupInput() {
        sendBtn.setOnClickListener { sendMessage() }
        micBtn.setOnClickListener { startSpeechToText() }
        seeMoreBtn.setOnClickListener { loadHistory(reset = false) }
    }

    private fun sendMessage() {
        val text = inputBox.text?.toString()?.trim() ?: ""
        if (text.isEmpty()) return
        val msg = LLMChatMessage(
            timestamp = System.currentTimeMillis(),
            provider = selectedProvider,
            role = "user",
            message = text
        )
        dbHelper.insertLLMMessage(msg)
        chatList.add(0, msg)
        chatAdapter.notifyItemInserted(0)
        chatRecycler.scrollToPosition(0)
        inputBox.setText("")
        // Call LLM API and add assistant response
        CoroutineScope(Dispatchers.IO).launch {
            val responseText = callLLMApi(selectedProvider, text)
            withContext(Dispatchers.Main) {
                val response = LLMChatMessage(
                    timestamp = System.currentTimeMillis() + 1,
                    provider = selectedProvider,
                    role = "assistant",
                    message = responseText
                )
                dbHelper.insertLLMMessage(response)
                chatList.add(0, response)
                chatAdapter.notifyItemInserted(0)
                chatRecycler.scrollToPosition(0)
            }
        }
    }

    private fun startSpeechToText() {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
        intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak now...")
        startActivityForResult(intent, REQ_CODE_SPEECH)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_CODE_SPEECH && resultCode == Activity.RESULT_OK && data != null) {
            val result = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            if (!result.isNullOrEmpty()) {
                inputBox.setText(result[0])
                inputBox.setSelection(result[0].length)
            }
        }
    }

    private fun loadHistory(reset: Boolean) {
        if (reset) {
            chatList.clear()
            offset = 0
        }
        val newMsgs = dbHelper.getLLMHistory(pageSize, offset)
        chatList.addAll(newMsgs)
        chatAdapter.notifyDataSetChanged()
        offset += newMsgs.size
        seeMoreBtn.visibility = if (newMsgs.size < pageSize) View.GONE else View.VISIBLE
    }

    private fun callLLMApi(provider: String, prompt: String): String {
        return try {
            when (provider) {
                "Groq" -> {
                    val url = URL("https://api.groq.com/openai/v1/chat/completions")
                    val conn = url.openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.setRequestProperty("Authorization", "Bearer ${apiKeys[provider]}")
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.doOutput = true
                    val body = JSONObject()
                    body.put("model", modelMap[provider])
                    val messages = org.json.JSONArray()
                    messages.put(JSONObject().put("role", "user").put("content", prompt))
                    body.put("messages", messages)
                    conn.outputStream.use { it.write(body.toString().toByteArray()) }
                    val resp = conn.inputStream.bufferedReader().readText()
                    val json = JSONObject(resp)
                    json.getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content")
                }
                "Cohere" -> {
                    val url = URL("https://api.cohere.ai/v1/chat")
                    val conn = url.openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.setRequestProperty("Authorization", "Bearer ${apiKeys[provider]}")
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.doOutput = true
                    val body = JSONObject()
                    body.put("model", modelMap[provider])
                    body.put("message", prompt)
                    conn.outputStream.use { it.write(body.toString().toByteArray()) }
                    val resp = conn.inputStream.bufferedReader().readText()
                    val json = JSONObject(resp)
                    json.optString("text") ?: json.optString("response") ?: json.optString("reply") ?: resp
                }
                "OpenRouter" -> {
                    val url = URL("https://openrouter.ai/api/v1/chat/completions")
                    val conn = url.openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.setRequestProperty("Authorization", "Bearer ${apiKeys[provider]}")
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.doOutput = true
                    val body = JSONObject()
                    body.put("model", modelMap[provider])
                    val messages = org.json.JSONArray()
                    messages.put(JSONObject().put("role", "user").put("content", prompt))
                    body.put("messages", messages)
                    conn.outputStream.use { it.write(body.toString().toByteArray()) }
                    val resp = conn.inputStream.bufferedReader().readText()
                    val json = JSONObject(resp)
                    json.getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content")
                }
                "Gemini" -> {
                    val model = modelMap["GoogleGemini"] ?: ""
                    val apiKey = apiKeys["GoogleGemini"] ?: ""
                    if (model.isBlank() || apiKey.isBlank()) {
                        return "Gemini model or API key not set."
                    }
                    val url = URL("https://generativelanguage.googleapis.com/v1beta/models/$model:generateContent?key=$apiKey")
                    val conn = url.openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.doOutput = true
                    val body = JSONObject()
                    val contents = org.json.JSONArray()
                    contents.put(JSONObject().put("role", "user").put("parts", org.json.JSONArray().put(JSONObject().put("text", prompt))))
                    body.put("contents", contents)
                    conn.outputStream.use { it.write(body.toString().toByteArray()) }
                    val resp = conn.inputStream.bufferedReader().readText()
                    val json = JSONObject(resp)
                    json.getJSONArray("candidates").getJSONObject(0).getJSONObject("content").getJSONArray("parts").getJSONObject(0).getString("text")
                }
                "Cerebras" -> {
                    try {
                        val url = URL("https://api.cerebras.ai/v1/chat/completions")
                        val conn = url.openConnection() as HttpURLConnection
                        conn.requestMethod = "POST"
                        conn.setRequestProperty("Authorization", "Bearer ${apiKeys[provider]}")
                        conn.setRequestProperty("Content-Type", "application/json")
                        conn.doOutput = true
                        val body = JSONObject()
                        body.put("model", "llama-4-scout-17b-16e-instruct")
                        val messages = org.json.JSONArray()
                        messages.put(JSONObject().put("role", "user").put("content", prompt))
                        body.put("messages", messages)
                        conn.outputStream.use { it.write(body.toString().toByteArray()) }
                        val resp = conn.inputStream.bufferedReader().readText()
                        val json = JSONObject(resp)
                        json.getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content")
                    } catch (e: java.net.UnknownHostException) {
                        "Cerebras API not reachable. Please check your internet connection."
                    }
                }
                "Mistral", "Mixtral" -> {
                    val url = URL("https://openrouter.ai/api/v1/chat/completions")
                    val conn = url.openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.setRequestProperty("Authorization", "Bearer ${apiKeys[provider]}")
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.doOutput = true
                    val body = JSONObject()
                    body.put("model", modelMap[provider])
                    val messages = org.json.JSONArray()
                    messages.put(JSONObject().put("role", "user").put("content", prompt))
                    body.put("messages", messages)
                    conn.outputStream.use { it.write(body.toString().toByteArray()) }
                    val resp = conn.inputStream.bufferedReader().readText()
                    val json = JSONObject(resp)
                    json.getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content")
                }
                else -> "Provider not implemented."
            }
        } catch (e: Exception) {
            "Error: ${e.message}"
        }
    }

    companion object {
        fun newInstance(): LLMFragment {
            return LLMFragment()
        }
    }
}

// RecyclerView Adapter for chat bubbles
class LLMChatAdapter(private val items: List<LLMChatMessage>) : RecyclerView.Adapter<LLMChatAdapter.ChatViewHolder>() {
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ChatViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_llm_chat, parent, false)
        return ChatViewHolder(view)
    }
    override fun onBindViewHolder(holder: ChatViewHolder, position: Int) {
        holder.bind(items[position])
    }
    override fun getItemCount() = items.size
    class ChatViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        private val meta: TextView = view.findViewById(R.id.meta)
        private val message: TextView = view.findViewById(R.id.message)
        fun bind(msg: LLMChatMessage) {
            val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
            meta.text = "${msg.provider} | ${msg.role.capitalize()} | ${sdf.format(Date(msg.timestamp))}"
            meta.setTextColor(0xFF222222.toInt())
            message.text = msg.message
            val params = message.layoutParams as ViewGroup.MarginLayoutParams
            if (msg.role == "user") {
                params.marginStart = 64
                params.marginEnd = 8
                message.setBackgroundColor(0xFFE3F2FD.toInt()) // light blue
                message.setTextColor(0xFF222222.toInt())
                message.textAlignment = View.TEXT_ALIGNMENT_VIEW_END
            } else {
                params.marginStart = 8
                params.marginEnd = 64
                message.setBackgroundColor(0xFFF5F5F5.toInt()) // light gray
                message.setTextColor(0xFF222222.toInt())
                message.textAlignment = View.TEXT_ALIGNMENT_VIEW_START
            }
            message.layoutParams = params
        }
    }
} 