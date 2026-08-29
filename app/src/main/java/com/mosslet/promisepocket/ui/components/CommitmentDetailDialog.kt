package com.mosslet.promisepocket.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.Block
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.FormatQuote
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mosslet.promisepocket.data.model.CommitmentEntity
import com.mosslet.promisepocket.data.model.CommitmentStatus
import com.mosslet.promisepocket.domain.TimeUtils
import com.mosslet.promisepocket.ui.theme.CoralDue
import com.mosslet.promisepocket.ui.theme.GreenSuccess
import com.mosslet.promisepocket.ui.theme.IndigoBlocked
import com.mosslet.promisepocket.ui.theme.IndigoBlockedBg
import com.mosslet.promisepocket.ui.theme.SandGold
import com.mosslet.promisepocket.ui.theme.SandGoldLight
import com.mosslet.promisepocket.ui.theme.Slate100
import com.mosslet.promisepocket.ui.theme.Slate200
import com.mosslet.promisepocket.ui.theme.Slate600
import com.mosslet.promisepocket.ui.theme.Slate800
import com.mosslet.promisepocket.ui.theme.Slate900

@Composable
fun CommitmentDetailDialog(
    commitment: CommitmentEntity,
    onDismiss: () -> Unit,
    onStatusChange: (CommitmentStatus) -> Unit,
    onSetBlockedReason: (String?) -> Unit,
    onDelete: () -> Unit
) {
    var isEditingBlocker by remember { mutableStateOf(false) }
    var blockerInput by remember { mutableStateOf(commitment.blockedReason ?: "") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Commitment Record",
                    style = MaterialTheme.typography.titleLarge
                )
                IconButton(
                    onClick = onDismiss,
                    modifier = Modifier.testTag("btn_close_detail")
                ) {
                    Icon(imageVector = Icons.Default.Close, contentDescription = "Close")
                }
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
            ) {
                // Summary Header
                Text(
                    text = commitment.summary,
                    style = MaterialTheme.typography.headlineMedium.copy(fontSize = 20.sp),
                    color = Slate900
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Raw utterance card
                Surface(
                    shape = RoundedCornerShape(12.dp),
                    color = Slate100,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.Top
                    ) {
                        Icon(
                            imageVector = Icons.Default.FormatQuote,
                            contentDescription = null,
                            tint = Slate600,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "\"${commitment.rawText}\"",
                            style = MaterialTheme.typography.bodyMedium.copy(fontStyle = FontStyle.Italic),
                            color = Slate800
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Metadata Rows
                DetailRow(
                    icon = Icons.Default.AccessTime,
                    label = "Due Timing",
                    value = TimeUtils.formatDisplayDate(commitment.dueAt)
                )

                if (commitment.people.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(10.dp))
                    DetailRow(
                        icon = Icons.Default.Person,
                        label = "People",
                        value = commitment.people.joinToString(", ")
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))
                DetailRow(
                    icon = if (commitment.humanActionRequired) Icons.Default.Person else Icons.Default.SmartToy,
                    label = "Action Policy",
                    value = if (commitment.humanActionRequired) "Human Action Required (Interrupts when due)" else "Safe Autonomous Agent Work"
                )

                Spacer(modifier = Modifier.height(10.dp))
                DetailRow(
                    icon = Icons.Default.CheckCircle,
                    label = "Status",
                    value = commitment.status.value.uppercase()
                )

                // Blocked status section
                Spacer(modifier = Modifier.height(16.dp))
                HorizontalDivider(color = Slate200)
                Spacer(modifier = Modifier.height(12.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.Block,
                            contentDescription = null,
                            tint = if (commitment.blockedReason.isNullOrBlank()) Slate600 else IndigoBlocked,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Blocked Status",
                            style = MaterialTheme.typography.titleMedium.copy(fontSize = 15.sp)
                        )
                    }
                    TextButton(
                        onClick = { isEditingBlocker = !isEditingBlocker },
                        modifier = Modifier.testTag("btn_toggle_edit_blocker")
                    ) {
                        Text(
                            if (isEditingBlocker) "Cancel"
                            else if (commitment.blockedReason.isNullOrBlank()) "Set Blocker"
                            else "Edit Blocker"
                        )
                    }
                }

                if (isEditingBlocker) {
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = blockerInput,
                        onValueChange = { blockerInput = it },
                        placeholder = { Text("Describe what is blocking this promise...") },
                        modifier = Modifier.fillMaxWidth().testTag("input_blocker_reason"),
                        minLines = 2
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.End
                    ) {
                        if (!commitment.blockedReason.isNullOrBlank()) {
                            TextButton(
                                onClick = {
                                    onSetBlockedReason(null)
                                    isEditingBlocker = false
                                }
                            ) {
                                Text("Clear Blocker", color = CoralDue)
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                        }
                        Button(
                            onClick = {
                                onSetBlockedReason(blockerInput.ifBlank { null })
                                isEditingBlocker = false
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = Slate800)
                        ) {
                            Text("Save")
                        }
                    }
                } else if (!commitment.blockedReason.isNullOrBlank()) {
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = IndigoBlockedBg,
                        modifier = Modifier.fillMaxWidth().padding(top = 6.dp)
                    ) {
                        Text(
                            text = commitment.blockedReason,
                            modifier = Modifier.padding(10.dp),
                            style = MaterialTheme.typography.bodyMedium,
                            color = IndigoBlocked
                        )
                    }
                }
            }
        },
        confirmButton = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = onDelete,
                    modifier = Modifier.testTag("btn_delete_commitment")
                ) {
                    Icon(
                        imageVector = Icons.Default.DeleteOutline,
                        contentDescription = "Delete",
                        tint = CoralDue
                    )
                }

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (commitment.status != CommitmentStatus.COMPLETED) {
                        Button(
                            onClick = { onStatusChange(CommitmentStatus.COMPLETED) },
                            colors = ButtonDefaults.buttonColors(containerColor = GreenSuccess),
                            modifier = Modifier.testTag("btn_mark_complete_detail")
                        ) {
                            Text("Mark Honored")
                        }
                    } else {
                        OutlinedButton(
                            onClick = { onStatusChange(CommitmentStatus.PENDING) },
                            modifier = Modifier.testTag("btn_mark_pending_detail")
                        ) {
                            Text("Reopen")
                        }
                    }
                }
            }
        }
    )
}

@Composable
private fun DetailRow(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    value: String
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = Slate600,
            modifier = Modifier.size(16.dp).padding(top = 2.dp)
        )
        Spacer(modifier = Modifier.width(10.dp))
        Column {
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                color = Slate600
            )
            Text(
                text = value,
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Medium),
                color = Slate900
            )
        }
    }
}
