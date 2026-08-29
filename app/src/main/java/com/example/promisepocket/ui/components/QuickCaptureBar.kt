package com.example.promisepocket.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
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
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
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
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.promisepocket.ui.theme.PromisePink
import com.example.promisepocket.ui.theme.Slate900

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun QuickCaptureBar(
    isCapturing: Boolean,
    onCapture: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    var text by remember { mutableStateOf("") }
    var showSuggestions by remember { mutableStateOf(false) }

    val samplePromises = listOf(
        "I promised Mom I'd call the dentist tomorrow at noon",
        "I need to email the quarterly review on Friday at 2pm",
        "I promised Sarah to return the borrowed book",
        "Prepare dentist options quietly without calling"
    )

    Column(modifier = modifier.fillMaxWidth()) {
        Surface(
            shape = RoundedCornerShape(24.dp),
            color = MaterialTheme.colorScheme.surface,
            shadowElevation = 4.dp,
            border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 8.dp, vertical = 6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = { showSuggestions = !showSuggestions },
                    modifier = Modifier.testTag("btn_capture_suggestions")
                ) {
                    Icon(
                        imageVector = Icons.Default.AutoAwesome,
                        contentDescription = "Examples",
                        tint = PromisePink,
                        modifier = Modifier.size(20.dp)
                    )
                }

                OutlinedTextField(
                    value = text,
                    onValueChange = { text = it },
                    placeholder = {
                        Text(
                            "“I promised Mom I’d call tomorrow at noon…”",
                            fontSize = 14.sp,
                            maxLines = 1
                        )
                    },
                    modifier = Modifier
                        .weight(1f)
                        .testTag("input_promise_capture"),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Color.Transparent,
                        unfocusedBorderColor = Color.Transparent,
                        disabledBorderColor = Color.Transparent
                    ),
                    maxLines = 3,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                    keyboardActions = KeyboardActions(onDone = {
                        if (text.isNotBlank() && !isCapturing) {
                            onCapture(text)
                            text = ""
                        }
                    })
                )

                if (isCapturing) {
                    CircularProgressIndicator(
                        modifier = Modifier
                            .size(28.dp)
                            .padding(4.dp),
                        strokeWidth = 2.5.dp,
                        color = PromisePink
                    )
                } else {
                    IconButton(
                        onClick = {
                            if (text.isNotBlank()) {
                                onCapture(text)
                                text = ""
                            }
                        },
                        enabled = text.isNotBlank(),
                        colors = IconButtonDefaults.iconButtonColors(
                            containerColor = if (text.isNotBlank()) PromisePink else Color.Transparent,
                            contentColor = if (text.isNotBlank()) Slate900 else MaterialTheme.colorScheme.onSurfaceVariant
                        ),
                        modifier = Modifier
                            .size(40.dp)
                            .testTag("btn_submit_promise")
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.Send,
                            contentDescription = "Keep Promise",
                            modifier = Modifier.size(18.dp)
                        )
                    }
                }
            }
        }

        AnimatedVisibility(
            visible = showSuggestions,
            enter = fadeIn(),
            exit = fadeOut()
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 10.dp, start = 4.dp, end = 4.dp)
            ) {
                Text(
                    text = "Try saying or typing:",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(4.dp))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    samplePromises.forEach { sample ->
                        FilterChip(
                            selected = false,
                            onClick = {
                                text = sample
                                showSuggestions = false
                            },
                            label = {
                                Text(sample, style = MaterialTheme.typography.labelSmall)
                            }
                        )
                    }
                }
            }
        }
    }
}
