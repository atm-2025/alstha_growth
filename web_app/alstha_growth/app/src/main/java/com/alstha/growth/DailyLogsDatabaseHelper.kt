package com.alstha.growth

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import com.alstha.growth.LLMChatMessage

class DailyLogsDatabaseHelper(context: Context) : SQLiteOpenHelper(context, DB_NAME, null, DB_VERSION) {
    companion object {
        private const val DB_NAME = "daily_logs.db"
        private const val DB_VERSION = 2
        private const val TABLE_NAME = "daily_logs"
        private const val COL_NO = "no"
        private const val COL_DATE = "date"
        private const val COL_NAME = "name"
        private const val COL_TYPE = "type"
        private const val COL_STATUS = "status"
        private const val COL_REMARK = "remark"
        private const val COL_DURATION = "duration"
        private const val COL_ATTENTION = "attention"
        private const val COL_DESCP = "descp"
        private const val COL_ENERGY = "energyLevel"
        private const val COL_LINKS = "links"
    }

    override fun onCreate(db: SQLiteDatabase) {
        val createTable = """
            CREATE TABLE $TABLE_NAME (
                $COL_NO INTEGER,
                $COL_DATE TEXT,
                $COL_NAME TEXT,
                $COL_TYPE TEXT,
                $COL_STATUS TEXT,
                $COL_REMARK TEXT,
                $COL_DURATION TEXT,
                $COL_ATTENTION INTEGER,
                $COL_DESCP TEXT,
                $COL_ENERGY INTEGER,
                $COL_LINKS TEXT
            )
        """.trimIndent()
        db.execSQL(createTable)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        if (oldVersion < 2) {
            db.execSQL("ALTER TABLE $TABLE_NAME ADD COLUMN $COL_LINKS TEXT")
        }
    }

    fun insertLog(log: DailyLogEntry) {
        val db = writableDatabase
        val values = ContentValues().apply {
            put(COL_NO, log.no)
            put(COL_DATE, log.date)
            put(COL_NAME, log.name)
            put(COL_TYPE, log.type)
            put(COL_STATUS, log.status)
            put(COL_REMARK, log.remark)
            put(COL_DURATION, log.duration)
            put(COL_ATTENTION, log.attention)
            put(COL_DESCP, log.descp)
            put(COL_ENERGY, log.energyLevel)
            put(COL_LINKS, log.links)
        }
        db.insert(TABLE_NAME, null, values)
        db.close()
    }

    fun updateLog(log: DailyLogEntry) {
        val db = writableDatabase
        val values = ContentValues().apply {
            put(COL_NAME, log.name)
            put(COL_TYPE, log.type)
            put(COL_STATUS, log.status)
            put(COL_REMARK, log.remark)
            put(COL_DURATION, log.duration)
            put(COL_ATTENTION, log.attention)
            put(COL_DESCP, log.descp)
            put(COL_ENERGY, log.energyLevel)
            put(COL_LINKS, log.links)
        }
        db.update(TABLE_NAME, values, "$COL_NO=? AND $COL_DATE=?", arrayOf(log.no.toString(), log.date))
        db.close()
    }

    fun deleteLog(no: Int, date: String) {
        val db = writableDatabase
        db.delete(TABLE_NAME, "$COL_NO=? AND $COL_DATE=?", arrayOf(no.toString(), date))
        db.close()
    }

    fun getLogsForDate(date: String): List<DailyLogEntry> {
        val db = readableDatabase
        val cursor = db.query(TABLE_NAME, null, "$COL_DATE=?", arrayOf(date), null, null, "$COL_NO ASC")
        val logs = mutableListOf<DailyLogEntry>()
        if (cursor.moveToFirst()) {
            do {
                logs.add(
                    DailyLogEntry(
                        no = cursor.getInt(cursor.getColumnIndexOrThrow(COL_NO)),
                        date = cursor.getString(cursor.getColumnIndexOrThrow(COL_DATE)),
                        name = cursor.getString(cursor.getColumnIndexOrThrow(COL_NAME)),
                        type = cursor.getString(cursor.getColumnIndexOrThrow(COL_TYPE)),
                        status = cursor.getString(cursor.getColumnIndexOrThrow(COL_STATUS)),
                        remark = cursor.getString(cursor.getColumnIndexOrThrow(COL_REMARK)),
                        duration = cursor.getString(cursor.getColumnIndexOrThrow(COL_DURATION)),
                        attention = cursor.getInt(cursor.getColumnIndexOrThrow(COL_ATTENTION)),
                        descp = cursor.getString(cursor.getColumnIndexOrThrow(COL_DESCP)),
                        energyLevel = cursor.getInt(cursor.getColumnIndexOrThrow(COL_ENERGY)),
                        links = if (cursor.getColumnIndex(COL_LINKS) != -1) cursor.getString(cursor.getColumnIndexOrThrow(COL_LINKS)) else null
                    )
                )
            } while (cursor.moveToNext())
        }
        cursor.close()
        db.close()
        return logs
    }

    fun getAllLogs(): List<DailyLogEntry> {
        val db = readableDatabase
        val cursor = db.query(TABLE_NAME, null, null, null, null, null, "$COL_DATE DESC, $COL_NO ASC")
        val logs = mutableListOf<DailyLogEntry>()
        if (cursor.moveToFirst()) {
            do {
                logs.add(
                    DailyLogEntry(
                        no = cursor.getInt(cursor.getColumnIndexOrThrow(COL_NO)),
                        date = cursor.getString(cursor.getColumnIndexOrThrow(COL_DATE)),
                        name = cursor.getString(cursor.getColumnIndexOrThrow(COL_NAME)),
                        type = cursor.getString(cursor.getColumnIndexOrThrow(COL_TYPE)),
                        status = cursor.getString(cursor.getColumnIndexOrThrow(COL_STATUS)),
                        remark = cursor.getString(cursor.getColumnIndexOrThrow(COL_REMARK)),
                        duration = cursor.getString(cursor.getColumnIndexOrThrow(COL_DURATION)),
                        attention = cursor.getInt(cursor.getColumnIndexOrThrow(COL_ATTENTION)),
                        descp = cursor.getString(cursor.getColumnIndexOrThrow(COL_DESCP)),
                        energyLevel = cursor.getInt(cursor.getColumnIndexOrThrow(COL_ENERGY)),
                        links = if (cursor.getColumnIndex(COL_LINKS) != -1) cursor.getString(cursor.getColumnIndexOrThrow(COL_LINKS)) else null
                    )
                )
            } while (cursor.moveToNext())
        }
        cursor.close()
        db.close()
        return logs
    }

    fun insertLLMMessage(msg: LLMChatMessage) {
        val db = writableDatabase
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS llm_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER,
                provider TEXT,
                role TEXT,
                message TEXT
            )
        """)
        val values = ContentValues().apply {
            put("timestamp", msg.timestamp)
            put("provider", msg.provider)
            put("role", msg.role)
            put("message", msg.message)
        }
        db.insert("llm_conversations", null, values)
        db.close()
    }

    fun getLLMHistory(limit: Int, offset: Int): List<LLMChatMessage> {
        val db = readableDatabase
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS llm_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER,
                provider TEXT,
                role TEXT,
                message TEXT
            )
        """)
        val list = mutableListOf<LLMChatMessage>()
        val cursor = db.rawQuery(
            "SELECT timestamp, provider, role, message FROM llm_conversations ORDER BY id DESC LIMIT ? OFFSET ?",
            arrayOf(limit.toString(), offset.toString())
        )
        if (cursor.moveToFirst()) {
            do {
                val ts = cursor.getLong(0)
                val provider = cursor.getString(1)
                val role = cursor.getString(2)
                val message = cursor.getString(3)
                list.add(LLMChatMessage(ts, provider, role, message))
            } while (cursor.moveToNext())
        }
        cursor.close()
        db.close()
        return list
    }
} 