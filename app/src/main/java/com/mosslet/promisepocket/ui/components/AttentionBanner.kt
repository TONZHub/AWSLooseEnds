package com.mosslet.promisepocket.ui.components

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
import androidx.compose.material.icons.filled.Block
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.NotificationsActive
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mosslet.promisepocket.data.model.AttentionItem
import com.mosslet.promisepocket.data.model.AttentionReason
import com.mosslet.promisepocket.ui.theme.AmberClarify
import com.mosslet.promisepocket.ui.theme.AmberClarifyBg
import com.mosslet.promisepocket.ui.theme.CoralDue
import com.mosslet.promisepocket.ui.theme.CoralDueBg
import com.mosslet.promisepocket.ui.theme.IndigoBlocked
import com.mosslet.promisepocket.ui.theme.IndigoBlockedBg
import com.mosslet.promisepocket.ui.theme.PromisePink
import com.mosslet.promisepocket.ui.theme.Slate900

@Composable
fun AttentionSection(
    items: List<AttentionItem>,
    onClarifyClick: (AttentionItem) -> Unit,
    onResolveClick: (String) -> Unit,
    onItemClick: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    if (items.isEmpty()) return

    Column(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 4.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .clip(CircleShape)
                        .background(CoralDue)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "NEEDS YOUR ATTENTION",
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.2.sp
                    ),
                    color = CoralDue
                )
            }
            Surface(
                shape = CircleShape,
                color = CoralDueBg,
                modifier = Modifier.padding(start = 6.dp)
            ) {
                Text(
                    text = "${items.size}",
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                    color = AmberClarify
                )
            }
        }

        items.forEach { item ->
            AttentionCard(
                item = item,
                onClarifyClick = { onClarifyClick(item) },
                onResolveClick = { onResolveClick(item.commitmentId) },
                onClick = { onItemClick(item.commitmentId) },
                modifier = Modifier.padding(vertical = 4.dp)
            )
        }
    }
}

@Composable
fun AttentionCard(
    item: AttentionItem,
    onClarifyClick: () -> Unit,
    onResolveClick: () -> Unit,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val (bgColor, accentColor, icon, badgeText) = when (item.reason) {
        AttentionReason.CLARIFICATION -> Quadruple(
            AmberClarifyBg,
            AmberClarify,
            Icons.Default.HelpOutline,
            "Clarification Needed"
        )
        AttentionReason.BLOCKED -> Quadruple(
            IndigoBlockedBg,
            IndigoBlocked,
            Icons.Default.Block,
            "Blocked"
        )
        AttentionReason.DUE -> Quadruple(
            CoralDueBg,
            AmberClarify,
            Icons.Default.NotificationsActive,
            "Due Now"
        )
    }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(2.dp))
            .clickable(onClick = onClick)
            .testTag("attention_card_${item.commitmentId}"),
        shape = RoundedCornerShape(2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 9.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Surface(
                    shape = RoundedCornerShape(0.dp),
                    color = bgColor
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = icon,
                            contentDescription = null,
                            tint = accentColor,
                            modifier = Modifier.size(14.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = badgeText,
                            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                            color = accentColor
                        )
                    }
                }

                if (item.people.isNotEmpty()) {
                    Text(
                        text = "with ${item.people.joinToString(", ")}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            Text(
                text = item.summary,
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                color = MaterialTheme.colorScheme.onSurface
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = item.prompt,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (item.reason == AttentionReason.CLARIFICATION) {
                    FilledTonalButton(
                        onClick = onClarifyClick,
                        colors = ButtonDefaults.filledTonalButtonColors(
                            containerColor = PromisePink,
                            contentColor = Slate900
                        ),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.testTag("btn_clarify_${item.commitmentId}")
                    ) {
                        Text("Set Exact Time", style = MaterialTheme.typography.labelLarge)
                    }
                } else if (item.reason == AttentionReason.DUE) {
                    FilledTonalButton(
                        onClick = onResolveClick,
                        colors = ButtonDefaults.filledTonalButtonColors(
                            containerColor = PromisePink,
                            contentColor = Slate900
                        ),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.testTag("btn_resolve_${item.commitmentId}")
                    ) {
                        Icon(
                            imageVector = Icons.Default.CheckCircle,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Mark Done", style = MaterialTheme.typography.labelLarge)
                    }
                }
            }
        }
    }
}

private data class Quadruple<A, B, C, D>(val first: A, val second: B, val third: C, val fourth: D)
