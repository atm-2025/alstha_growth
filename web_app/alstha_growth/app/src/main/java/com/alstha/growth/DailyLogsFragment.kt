package com.alstha.growth

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.fragment.app.Fragment
import java.text.SimpleDateFormat
import java.util.*
import org.json.JSONObject
import java.io.File
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.widget.Toolbar

class DailyLogsFragment : Fragment() {
    private lateinit var inputName: EditText
    private lateinit var inputDate: EditText
    private lateinit var inputType: Spinner
    private lateinit var inputStatus: Spinner
    private lateinit var inputRemarks: EditText
    private lateinit var btnShowMore: Button
    private lateinit var layoutShowMore: LinearLayout
    private lateinit var inputLinks: EditText
    private lateinit var inputDuration: EditText
    private lateinit var inputAttention: Spinner
    private lateinit var inputEnergyLevel: Spinner
    private lateinit var inputDesp: EditText
    private lateinit var btnCancel: ImageButton
    private lateinit var btnDone: ImageButton
    private lateinit var btnAdd: ImageButton
    // Removed btnNavAdd and btnNavTable
    private lateinit var dbHelper: DailyLogsDatabaseHelper
    private var selectedDate: String = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
    private var backCallback: OnBackPressedCallback? = null
    private lateinit var toolbar: Toolbar

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_daily_logs, container, false)
        // Removed toolbar navigation icon (back button) setup
        inputName = view.findViewById(R.id.inputName)
        inputDate = view.findViewById(R.id.inputDate)
        inputType = view.findViewById(R.id.inputType)
        inputStatus = view.findViewById(R.id.inputStatus)
        inputRemarks = view.findViewById(R.id.inputRemarks)
        btnShowMore = view.findViewById(R.id.btnShowMore)
        layoutShowMore = view.findViewById(R.id.layoutShowMore)
        inputLinks = view.findViewById(R.id.inputLinks)
        inputDuration = view.findViewById(R.id.inputDuration)
        inputAttention = view.findViewById(R.id.inputAttention)
        inputEnergyLevel = view.findViewById(R.id.inputEnergyLevel)
        inputDesp = view.findViewById(R.id.inputDesp)
        btnCancel = view.findViewById<ImageButton>(R.id.btnCancel)
        btnDone = view.findViewById<ImageButton>(R.id.btnDone)
        btnAdd = view.findViewById<ImageButton>(R.id.btnAdd)
        // Removed btnNavAdd and btnNavTable
        dbHelper = DailyLogsDatabaseHelper(requireContext())
        return view
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        inputDate.setText(selectedDate)
        inputDate.setOnClickListener { showDatePickerDialog() }
        btnShowMore.setOnClickListener { toggleShowMore() }
        btnCancel.setOnClickListener { clearForm() }
        btnDone.setOnClickListener { saveLog(update = true) }
        btnAdd.setOnClickListener { saveLog(update = false) }
        // Removed btnNavAdd and btnNavTable logic
        // Set up spinners
        val typeOptions = loadDropdownOptions("type")
        val statusOptions = loadDropdownOptions("status")
        inputType.adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, typeOptions)
        inputStatus.adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, statusOptions)
        inputAttention.adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, listOf("0%", "25%", "50%", "75%", "100%"))
        inputEnergyLevel.adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, listOf("Low", "Medium", "High"))
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

    private fun showDatePickerDialog() {
        val calendar = Calendar.getInstance()
        val parts = inputDate.text.toString().split("-")
        if (parts.size == 3) {
            calendar.set(Calendar.YEAR, parts[0].toInt())
            calendar.set(Calendar.MONTH, parts[1].toInt() - 1)
            calendar.set(Calendar.DAY_OF_MONTH, parts[2].toInt())
        }
        val datePicker = android.app.DatePickerDialog(requireContext(), { _, year, month, dayOfMonth ->
            val pickedDate = String.format("%04d-%02d-%02d", year, month + 1, dayOfMonth)
            inputDate.setText(pickedDate)
            selectedDate = pickedDate
        }, calendar.get(Calendar.YEAR), calendar.get(Calendar.MONTH), calendar.get(Calendar.DAY_OF_MONTH))
        datePicker.show()
    }

    private fun toggleShowMore() {
        if (layoutShowMore.visibility == View.GONE) {
            layoutShowMore.visibility = View.VISIBLE
            btnShowMore.text = "Show Less"
        } else {
            layoutShowMore.visibility = View.GONE
            btnShowMore.text = "Show More"
        }
    }

    private fun clearForm() {
        inputName.text.clear()
        inputType.setSelection(0)
        inputStatus.setSelection(0)
        inputRemarks.text.clear()
        inputLinks.text.clear()
        inputDuration.text.clear()
        inputAttention.setSelection(0)
        inputEnergyLevel.setSelection(0)
        inputDesp.text.clear()
        inputDate.setText(selectedDate)
        layoutShowMore.visibility = View.GONE
        btnShowMore.text = "Show More"
    }

    private fun saveLog(update: Boolean) {
        val name = inputName.text.toString()
        val date = inputDate.text.toString()
        val type = inputType.selectedItem.toString()
        val status = inputStatus.selectedItem.toString()
        val remarks = inputRemarks.text.toString()
        val links = inputLinks.text.toString()
        val duration = inputDuration.text.toString()
        val attentionStr = inputAttention.selectedItem.toString()
        val attention = when (attentionStr) {
            "0%" -> 0
            "25%" -> 25
            "50%" -> 50
            "75%" -> 75
            "100%" -> 100
            else -> 0
        }
        val energyLevelStr = inputEnergyLevel.selectedItem.toString()
        val energyLevel = when (energyLevelStr) {
            "Low" -> 1
            "Medium" -> 2
            "High" -> 3
            else -> 1
        }
        val desp = inputDesp.text.toString()
        val todayLogs = dbHelper.getLogsForDate(date)
        val nextNo = if (update && todayLogs.isNotEmpty()) todayLogs[0].no else (todayLogs.maxOfOrNull { it.no } ?: 0) + 1
        val log = DailyLogEntry(
            no = nextNo,
            date = date,
            name = name,
            type = type,
            status = status,
            remark = remarks,
            duration = duration,
            attention = attention,
            descp = desp,
            energyLevel = energyLevel,
            links = links
        )
        if (update && todayLogs.isNotEmpty()) {
            dbHelper.updateLog(log)
            Toast.makeText(requireContext(), "Log updated!", Toast.LENGTH_SHORT).show()
        } else {
            dbHelper.insertLog(log)
            Toast.makeText(requireContext(), "Log added!", Toast.LENGTH_SHORT).show()
        }
        clearForm()
    }

    private fun loadDropdownOptions(key: String): List<String> {
        return try {
            val file = File(requireContext().filesDir, "../../windows_client/modules/json/dropdown_options.json")
            val json = JSONObject(file.readText())
            val arr = json.optJSONArray(key)
            if (arr != null) List(arr.length()) { arr.getString(it) } else listOf("-")
        } catch (e: Exception) {
            listOf("-")
        }
    }

    companion object {
        fun newInstance(): DailyLogsFragment {
            return DailyLogsFragment()
        }
    }
}
