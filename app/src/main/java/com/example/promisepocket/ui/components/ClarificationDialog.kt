package com.example.promisepocket.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.promisepocket.data.model.AttentionItem
import com.example.promisepocket.domain.TimeUtils
import com.example.promisepocket.ui.theme.AmberClarify
import com.example.promisepocket.ui.theme.AmberClarifyBg
import com.example.promisepocket.ui.theme.GreenSuccess
import com.example.promisepocket.ui.theme.Slate600
import com.example.promisepocket.ui.theme.Slate800
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import java.time.ZonedDateTime

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ClarificationDialog(
    item: AttentionItem,
    onDismiss: () -> Unit,
    onConfirm: (answer: String, resolvedDueAtIso: String) -> Unit
) {
    var timeAnswer by remember { mutableStateOf("") }
    var selectedDayOffset by remember { mutableStateOf(1) } // 0 = today, 1 = tomorrow, 2 = 2 days
    val hasValidClock = TimeUtils.hasExplicitClockTime(timeAnswer)

    val quickPresets = listOf("9:00 AM", "noon", "2:00 PM", "5:00 PM", "8:00 PM", "midnight")

    fun resolveTargetIso(): String {
        val zone = ZoneId.systemDefault()
        val targetDate = LocalDate.now(zone).plusDays(selectedDayOffset.toLong())
        val lower = timeAnswer.lowercase().trim()

        var hour = 12
        var minute = 0
        when {
            lower.contains("noon") -> { hour = 12; minute = 0 }
            lower.contains("midnight") -> { hour = 0; minute = 0 }
            else -> {
                val matchPm = Regex("""(\d{1,2})(?::(\d{2}))?\s*p\.?m\.?""", RegexOption.IGNORE_CASE).find(lower)
                val matchAm = Regex("""(\d{1,2})(?::(\d{2}))?\s*a\.?m\.?""", RegexOption.IGNORE_CASE).find(lower)
                val match24 = Regex("""(\d{1,2}):(\d{2})""").find(lower)
                val matchAt = Regex("""at\s+(\d{1,2})""", RegexOption.IGNORE_CASE).find(lower)

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
        val zdt = ZonedDateTime.of(targetDate, LocalTime.of(hour.coerceIn(0, 23), minute.coerceIn(0, 59)), zone)
        return zdt.toInstant().toString()
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.AccessTime,
                    contentDescription = null,
                    tint = AmberClarify,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Clarify Exact Time",
                    style = MaterialTheme.typography.titleLarge
                )
            }
        },
        text = {
            Column(modifier = Modifier.fillMaxWidth()) {
                Surface(
                    shape = RoundedCornerShape(10.dp),
                    color = AmberClarifyBg,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.Top
                    ) {
                        Icon(
                            imageVector = Icons.Default.HelpOutline,
                            contentDescription = null,
                            tint = AmberClarify,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Column {
                            Text(
                                text = item.summary,
                                style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold),
                                color = Slate800
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = item.prompt,
                                style = MaterialTheme.typography.bodyMedium,
                                color = Slate600
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                Text(
                    text = "Target Day:",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(4.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    listOf("Today" to 0, "Tomorrow" to 1, "In 2 Days" to 2).forEach { (label, offset) ->
                        FilterChip(
                            selected = selectedDayOffset == offset,
                            onClick = { selectedDayOffset = offset },
                            label = { Text(label) },
                            modifier = Modifier.testTag("day_chip_$offset")
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = timeAnswer,
                    onValueChange = { timeAnswer = it },
                    label = { Text("Exact clock time") },
                    placeholder = { Text("e.g. 10:00 AM, noon, 2pm") },
                    singleLine = true,
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("input_time_clarification"),
                    supportingText = {
                        if (timeAnswer.isNotEmpty()) {
                            if (hasValidClock) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(
                                        imageVector = Icons.Default.Check,
                                        contentDescription = null,
                                        tint = GreenSuccess,
                                        modifier = Modifier.size(14.dp)
                                    )
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text(
                                        "Valid clock time recognized",
                                        color = GreenSuccess,
                                        style = MaterialTheme.typography.labelSmall
                                    )
                                }
                            } else {
                                Text(
                                    "Must include an explicit clock time (e.g. 2pm, noon, 10:30)",
                                    color = MaterialTheme.colorScheme.error,
                                    style = MaterialTheme.typography.labelSmall
                                )
                            }
                        }
                    }
                )

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = "Quick Presets:",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(4.dp))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    quickPresets.forEach { preset ->
                        FilterChip(
                            selected = timeAnswer.equals(preset, ignoreCase = true),
                            onClick = { timeAnswer = preset },
                            label = { Text(preset) },
                            modifier = Modifier.testTag("preset_$preset")
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (hasValidClock) {
                        onConfirm(timeAnswer, resolveTargetIso())
                    }
                },
                enabled = hasValidClock,
                colors = ButtonDefaults.buttonColors(containerColor = Slate800),
                modifier = Modifier.testTag("btn_confirm_clarification")
            ) {
                Text("Save Time")
            }
        },
        dismissButton = {
            OutlinedButton(
                onClick = onDismiss,
                modifier = Modifier.testTag("btn_cancel_clarification")
            ) {
                Text("Cancel")
            }
        }
    )
}
