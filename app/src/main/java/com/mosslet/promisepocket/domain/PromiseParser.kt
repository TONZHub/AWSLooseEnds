package com.mosslet.promisepocket.domain

import android.util.Log
import com.mosslet.promisepocket.BuildConfig
import com.mosslet.promisepocket.data.remote.Content
import com.mosslet.promisepocket.data.remote.GenerateContentRequest
import com.mosslet.promisepocket.data.remote.GenerationConfig
import com.mosslet.promisepocket.data.remote.Part
import com.mosslet.promisepocket.data.remote.RetrofitClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

@Serializable
data class ParsedPromise(
    val isCommitment: Boolean = true,
    val summary: String,
    val dueAt: String? = null,
    val people: List<String> = emptyList(),
    val humanActionRequired: Boolean = true,
    val missingInformation: List<String> = emptyList()
)

class PromiseParser {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    suspend fun parseUserUtterance(rawText: String, userTimezone: ZoneId = ZoneId.systemDefault()): ParsedPromise =
        withContext(Dispatchers.IO) {
            val apiKey = try {
                BuildConfig.GEMINI_API_KEY
            } catch (e: Exception) {
                ""
            }

            if (apiKey.isNotBlank() && apiKey != "null" && apiKey != "placeholder_api_key") {
                try {
                    val parsed = callGemini(rawText, apiKey, userTimezone)
                    if (parsed != null) {
                        return@withContext parsed
                    }
                } catch (e: Exception) {
                    Log.w("PromiseParser", "Gemini call fallback: ${e.message}")
                }
            }

            // High quality local fallback parsing
            return@withContext parseLocally(rawText, userTimezone)
        }

    private suspend fun callGemini(
        rawText: String,
        apiKey: String,
        userTimezone: ZoneId
    ): ParsedPromise? {
        val nowZdt = ZonedDateTime.now(userTimezone)
        val nowIso = nowZdt.format(DateTimeFormatter.ISO_OFFSET_DATE_TIME)

        val systemPrompt = """
            You are Promise Pocket, a quiet memory for real commitments.
            The current reference time is: $nowIso.
            The user timezone is: ${userTimezone.id}.
            
            Rules:
            1. Notice when the user expresses a promise, obligation, deadline, or follow-up.
            2. Normalize it without changing its meaning.
            3. Do not capture wishes or casual possibilities as commitments.
            4. Never invent a person, deadline, or missing fact.
            5. Convert relative times to an absolute ISO-8601 datetime with timezone offset ONLY IF the user utterance includes an explicit clock time (e.g., 'noon', 'midnight', '2pm', '14:00', 'at 5').
            6. If no explicit clock time is present, set dueAt to null, and put "What time should I bring this back?" in missingInformation.
            7. humanActionRequired is true when the user must personally act, call, decide, approve, send, pay, book, or communicate.
            8. Return strictly valid JSON adhering to:
            {
               "isCommitment": true,
               "summary": "Short faithful description",
               "dueAt": "ISO-8601 string or null",
               "people": ["Mom"],
               "humanActionRequired": true,
               "missingInformation": []
            }
        """.trimIndent()

        val prompt = "User statement: \"$rawText\""

        val request = GenerateContentRequest(
            contents = listOf(
                Content(parts = listOf(Part(text = prompt)))
            ),
            generationConfig = GenerationConfig(
                responseMimeType = "application/json",
                temperature = 0.1f
            ),
            systemInstruction = Content(parts = listOf(Part(text = systemPrompt)))
        )

        val response = RetrofitClient.service.generateContent(apiKey, request)
        val text = response.candidates?.firstOrNull()?.content?.parts?.firstOrNull()?.text
            ?: return null

        return try {
            json.decodeFromString<ParsedPromise>(text)
        } catch (e: Exception) {
            // Strip markdown block if model wrapped in ```json
            val clean = text.replace("```json", "").replace("```", "").trim()
            json.decodeFromString<ParsedPromise>(clean)
        }
    }

    fun parseLocally(rawText: String, userTimezone: ZoneId = ZoneId.systemDefault()): ParsedPromise {
        val trimmed = rawText.trim()
        val lower = trimmed.lowercase()

        // Extract people mentions
        val detectedPeople = mutableListOf<String>()
        val commonNames = listOf("Mom", "Dad", "Sarah", "John", "Mike", "Emma", "Alex", "David", "Dr.", "Doctor", "Boss", "Manager", "Client")
        for (name in commonNames) {
            val pattern = Regex("""\b$name\b""", RegexOption.IGNORE_CASE)
            if (pattern.containsMatchIn(trimmed)) {
                detectedPeople.add(name)
            }
        }

        // Summary cleanup
        var summary = trimmed
        val promisePrefixes = listOf(
            "i promised mom i would", "i promised mom i'd", "i promised to", "i promised i would",
            "i need to", "i have to", "i must", "i will", "don't forget to", "remember to", "remind me to"
        )
        for (prefix in promisePrefixes) {
            if (lower.startsWith(prefix)) {
                summary = trimmed.substring(prefix.length).trim()
                if (summary.isNotEmpty()) {
                    summary = summary.replaceFirstChar { it.uppercase() }
                }
                break
            }
        }

        val hasClock = TimeUtils.hasExplicitClockTime(trimmed)
        var dueAt: String? = null
        val missing = mutableListOf<String>()

        if (hasClock) {
            // Parse a reasonable time relative to today/tomorrow
            val today = LocalDate.now(userTimezone)
            val targetDate = if (lower.contains("tomorrow")) today.plusDays(1) else today

            var hour = 12
            var minute = 0
            when {
                lower.contains("noon") -> { hour = 12; minute = 0 }
                lower.contains("midnight") -> { hour = 0; minute = 0 }
                else -> {
                    val matchPm = Regex("""(\d{1,2})(?::(\d{2}))?\s*p\.?m\.?""", RegexOption.IGNORE_CASE).find(trimmed)
                    val matchAm = Regex("""(\d{1,2})(?::(\d{2}))?\s*a\.?m\.?""", RegexOption.IGNORE_CASE).find(trimmed)
                    val match24 = Regex("""(\d{1,2}):(\d{2})""").find(trimmed)
                    val matchAt = Regex("""at\s+(\d{1,2})""", RegexOption.IGNORE_CASE).find(trimmed)

                    if (matchPm != null) {
                        val h = matchPm.groupValues[1].toInt()
                        hour = if (h == 12) 12 else h + 12
                        minute = matchPm.groupValues.getOrNull(2)?.toIntOrNull() ?: 0
                    } else if (matchAm != null) {
                        val h = matchAm.groupValues[1].toInt()
                        hour = if (h == 12) 0 else h
                        minute = matchAm.groupValues.getOrNull(2)?.toIntOrNull() ?: 0
                    } else if (match24 != null) {
                        hour = match24.groupValues[1].toInt()
                        minute = match24.groupValues[2].toInt()
                    } else if (matchAt != null) {
                        val h = matchAt.groupValues[1].toInt()
                        hour = if (h in 1..7) h + 12 else h
                    }
                }
            }

            val zdt = ZonedDateTime.of(targetDate, LocalTime.of(hour, minute), userTimezone)
            dueAt = zdt.toInstant().toString()
        } else {
            missing.add("What time should I bring this back?")
        }

        val humanAction = !lower.contains("research") && !lower.contains("prepare options") && !lower.contains("draft quietly")

        return ParsedPromise(
            isCommitment = true,
            summary = summary.ifBlank { trimmed },
            dueAt = dueAt,
            people = detectedPeople.distinct(),
            humanActionRequired = humanAction,
            missingInformation = missing
        )
    }
}
