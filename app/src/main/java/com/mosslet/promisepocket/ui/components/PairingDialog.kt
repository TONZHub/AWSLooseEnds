package com.mosslet.promisepocket.ui.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Link
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mosslet.promisepocket.ui.theme.PromisePink

import androidx.compose.material.icons.filled.LinkOff
import com.mosslet.promisepocket.ui.theme.GreenSuccess
import com.mosslet.promisepocket.ui.theme.Slate900

@Composable
fun PairingDialog(
    isPairing: Boolean,
    errorMessage: String?,
    isLinked: Boolean = false,
    actorId: String? = null,
    onDismiss: () -> Unit,
    onPair: (String) -> Unit,
    onUnlink: () -> Unit = {}
) {
    var code by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = { if (!isPairing) onDismiss() },
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = if (isLinked) Icons.Default.Link else Icons.Default.LinkOff,
                    contentDescription = null,
                    tint = if (isLinked) GreenSuccess else PromisePink,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = if (isLinked) "Receipts Ledger Linked" else "Pair with Receipts Ledger",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                )
            }
        },
        text = {
            Column(modifier = Modifier.fillMaxWidth()) {
                if (isLinked) {
                    Text(
                        text = "Your device is connected to the shared evidence ledger:",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = actorId ?: "Unknown Actor",
                        style = MaterialTheme.typography.bodySmall.copy(
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.SemiBold
                        ),
                        color = Slate900
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "Unlinking revokes the local session token and returns the app to local offline mode.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline
                    )
                } else {
                    Text(
                        text = "Enter the 6-digit one-time code from the Receipts web desk (/mobile/pair):",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    OutlinedTextField(
                        value = code,
                        onValueChange = { input ->
                            val digits = input.filter { it.isDigit() }.take(6)
                            code = digits
                        },
                        label = { Text("6-digit pairing code") },
                        placeholder = { Text("123456") },
                        singleLine = true,
                        isError = errorMessage != null,
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("input_pairing_code"),
                        textStyle = MaterialTheme.typography.headlineMedium.copy(
                            fontFamily = FontFamily.Monospace,
                            textAlign = TextAlign.Center,
                            letterSpacing = 4.sp,
                            fontWeight = FontWeight.Bold
                        )
                    )
                    if (errorMessage != null) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = errorMessage,
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "Single-use. The phone receives a revocable token; raw pairing codes are never stored.",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.outline
                    )
                }
            }
        },
        confirmButton = {
            if (isLinked) {
                Button(
                    onClick = onUnlink,
                    colors = androidx.compose.material3.ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error
                    ),
                    modifier = Modifier.testTag("btn_unlink_device"),
                    shape = RoundedCornerShape(2.dp)
                ) {
                    Text("Unlink Device")
                }
            } else {
                Button(
                    onClick = { onPair(code) },
                    enabled = code.length == 6 && !isPairing,
                    modifier = Modifier.testTag("btn_confirm_pair"),
                    shape = RoundedCornerShape(2.dp)
                ) {
                    if (isPairing) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            strokeWidth = 2.dp,
                            color = Color.White
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Pairing...")
                    } else {
                        Text("Pair Device")
                    }
                }
            }
        },
        dismissButton = {
            OutlinedButton(
                onClick = onDismiss,
                enabled = !isPairing,
                modifier = Modifier.testTag("btn_cancel_pair"),
                shape = RoundedCornerShape(2.dp)
            ) {
                Text(if (isLinked) "Close" else "Cancel")
            }
        },
        shape = RoundedCornerShape(2.dp)
    )
}
