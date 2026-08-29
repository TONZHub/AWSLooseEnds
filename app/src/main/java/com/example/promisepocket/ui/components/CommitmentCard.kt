package com.example.promisepocket.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.Block
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PersonOutline
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.example.promisepocket.data.model.CommitmentEntity
import com.example.promisepocket.data.model.CommitmentStatus
import com.example.promisepocket.domain.TimeUtils
import com.example.promisepocket.ui.theme.AmberClarify
import com.example.promisepocket.ui.theme.AmberClarifyBg
import com.example.promisepocket.ui.theme.GreenSuccess
import com.example.promisepocket.ui.theme.GreenSuccessBg
import com.example.promisepocket.ui.theme.IndigoBlocked
import com.example.promisepocket.ui.theme.IndigoBlockedBg
import com.example.promisepocket.ui.theme.SandGold
import com.example.promisepocket.ui.theme.SandGoldLight
import com.example.promisepocket.ui.theme.Slate200
import com.example.promisepocket.ui.theme.Slate400
import com.example.promisepocket.ui.theme.Slate600
import com.example.promisepocket.ui.theme.Slate700

@Composable
fun CommitmentCard(
    commitment: CommitmentEntity,
    onStatusToggle: (CommitmentStatus) -> Unit,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val isCompleted = commitment.status == CommitmentStatus.COMPLETED
    val isCanceled = commitment.status == CommitmentStatus.CANCELED

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .clickable(onClick = onClick)
            .testTag("commitment_card_${commitment.commitmentId}"),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isCompleted || isCanceled) {
                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
            } else {
                MaterialTheme.colorScheme.surface
            }
        ),
        border = BorderStroke(
            1.dp,
            if (isCompleted) Slate200 else MaterialTheme.colorScheme.outlineVariant
        ),
        elevation = CardDefaults.cardElevation(
            defaultElevation = if (isCompleted || isCanceled) 0.dp else 1.5.dp
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.Top
        ) {
            // Checkbox for rapid status toggle
            IconButton(
                onClick = {
                    val next = if (isCompleted) CommitmentStatus.PENDING else CommitmentStatus.COMPLETED
                    onStatusToggle(next)
                },
                modifier = Modifier
                    .size(32.dp)
                    .clip(CircleShape)
                    .testTag("check_toggle_${commitment.commitmentId}")
            ) {
                Box(
                    modifier = Modifier
                        .size(24.dp)
                        .clip(CircleShape)
                        .background(
                            if (isCompleted) GreenSuccess else Color.Transparent
                        )
                        .let {
                            if (!isCompleted) it.background(Color.Transparent, CircleShape)
                            else it
                        },
                    contentAlignment = Alignment.Center
                ) {
                    if (isCompleted) {
                        Icon(
                            imageVector = Icons.Default.Check,
                            contentDescription = "Completed",
                            tint = Color.White,
                            modifier = Modifier.size(16.dp)
                        )
                    } else {
                        Surface(
                            shape = CircleShape,
                            border = BorderStroke(1.5.dp, MaterialTheme.colorScheme.outline),
                            color = Color.Transparent,
                            modifier = Modifier.size(22.dp)
                        ) {}
                    }
                }
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                // Top row: timing / badges
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    if (commitment.dueAt != null) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.AccessTime,
                                contentDescription = null,
                                tint = if (isCompleted) Slate400 else SandGold,
                                modifier = Modifier.size(13.dp)
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = TimeUtils.formatDisplayDate(commitment.dueAt),
                                style = MaterialTheme.typography.labelSmall,
                                color = if (isCompleted) Slate400 else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    } else if (commitment.missingInformation.isNotEmpty()) {
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = AmberClarifyBg
                        ) {
                            Text(
                                text = "Time missing",
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Medium),
                                color = AmberClarify
                            )
                        }
                    } else {
                        Text(
                            text = "Unscheduled",
                            style = MaterialTheme.typography.labelSmall,
                            color = Slate400
                        )
                    }

                    // Human vs Agent badge
                    Surface(
                        shape = RoundedCornerShape(6.dp),
                        color = if (commitment.humanActionRequired) SandGoldLight else Slate100
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = if (commitment.humanActionRequired) Icons.Default.PersonOutline else Icons.Default.SmartToy,
                                contentDescription = null,
                                tint = if (commitment.humanActionRequired) SandGoldDark else Slate600,
                                modifier = Modifier.size(12.dp)
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = if (commitment.humanActionRequired) "You" else "Agent",
                                style = MaterialTheme.typography.labelSmall,
                                color = if (commitment.humanActionRequired) SandGoldDark else Slate700
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(6.dp))

                // Summary
                Text(
                    text = commitment.summary,
                    style = MaterialTheme.typography.titleMedium.copy(
                        fontWeight = if (isCompleted) FontWeight.Normal else FontWeight.SemiBold,
                        textDecoration = if (isCompleted) TextDecoration.LineThrough else TextDecoration.None
                    ),
                    color = if (isCompleted) Slate400 else MaterialTheme.colorScheme.onSurface,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )

                // People / Blocked tags
                if (commitment.people.isNotEmpty() || !commitment.blockedReason.isNullOrBlank()) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        commitment.people.forEach { person ->
                            Surface(
                                shape = RoundedCornerShape(6.dp),
                                color = MaterialTheme.colorScheme.surfaceVariant
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Person,
                                        contentDescription = null,
                                        modifier = Modifier.size(11.dp),
                                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                    Spacer(modifier = Modifier.width(3.dp))
                                    Text(
                                        text = person,
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                        }

                        if (!commitment.blockedReason.isNullOrBlank()) {
                            Surface(
                                shape = RoundedCornerShape(6.dp),
                                color = IndigoBlockedBg
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Block,
                                        contentDescription = null,
                                        modifier = Modifier.size(11.dp),
                                        tint = IndigoBlocked
                                    )
                                    Spacer(modifier = Modifier.width(3.dp))
                                    Text(
                                        text = "Blocked",
                                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                        color = IndigoBlocked
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

val Slate100 = Color(0xFFF1F5F9)
val SandGoldDark = Color(0xFF946332)
