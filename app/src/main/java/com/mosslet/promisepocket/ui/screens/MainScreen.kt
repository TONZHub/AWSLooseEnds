package com.mosslet.promisepocket.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.FilterList
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.outlined.BookmarkBorder
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mosslet.promisepocket.data.model.CommitmentStatus
import com.mosslet.promisepocket.ui.components.AttentionSection
import com.mosslet.promisepocket.ui.components.ClarificationDialog
import com.mosslet.promisepocket.ui.components.CommitmentCard
import com.mosslet.promisepocket.ui.components.CommitmentDetailDialog
import com.mosslet.promisepocket.ui.components.QuickCaptureBar
import com.mosslet.promisepocket.ui.theme.PromiseCream
import com.mosslet.promisepocket.ui.theme.PromisePeach
import com.mosslet.promisepocket.ui.theme.PromisePink
import com.mosslet.promisepocket.ui.theme.Slate400
import com.mosslet.promisepocket.ui.theme.Slate600
import com.mosslet.promisepocket.ui.theme.Slate700
import com.mosslet.promisepocket.ui.theme.Slate900
import com.mosslet.promisepocket.ui.viewmodel.FilterTab
import com.mosslet.promisepocket.ui.viewmodel.PromisePocketViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    viewModel: PromisePocketViewModel,
    modifier: Modifier = Modifier
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    var isSearchOpen by remember { mutableStateOf(false) }

    LaunchedEffect(state.userNotification) {
        state.userNotification?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.dismissNotification()
        }
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Surface(color = PromisePink, shape = RoundedCornerShape(0.dp)) {
                            Text("R", modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                                color = PromiseCream, fontWeight = FontWeight.Black, fontSize = 22.sp)
                        }
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                text = "Receipts",
                                style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = "WE HAVE THE RECEIPTS",
                                style = MaterialTheme.typography.labelSmall,
                                color = PromisePink.copy(alpha = 0.86f)
                            )
                        }
                    }
                },
                actions = {
                    IconButton(
                        onClick = { isSearchOpen = !isSearchOpen },
                        modifier = Modifier.testTag("btn_toggle_search")
                    ) {
                        Icon(
                            imageVector = if (isSearchOpen) Icons.Default.Close else Icons.Default.Search,
                            contentDescription = "Search",
                            tint = MaterialTheme.colorScheme.onSurface
                        )
                    }

                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
        contentWindowInsets = WindowInsets.statusBars
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(MaterialTheme.colorScheme.background)
        ) {
            AnimatedVisibility(visible = isSearchOpen) {
                Surface(
                    color = MaterialTheme.colorScheme.surface,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    OutlinedTextField(
                        value = state.searchQuery,
                        onValueChange = { viewModel.setSearchQuery(it) },
                        placeholder = { Text("Filter commitments or people...") },
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 8.dp)
                            .testTag("input_search_query"),
                        singleLine = true
                    )
                }
            }

            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
                contentPadding = PaddingValues(
                    start = 16.dp,
                    end = 16.dp,
                    top = 12.dp,
                    bottom = 100.dp
                ),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                item {
                    HeroBannerCard()
                }

                if (state.attentionItems.isNotEmpty() && state.filterTab != FilterTab.COMPLETED) {
                    item {
                        AttentionSection(
                            items = state.attentionItems,
                            onClarifyClick = { viewModel.openClarification(it) },
                            onResolveClick = { viewModel.setStatus(it, CommitmentStatus.COMPLETED) },
                            onItemClick = { viewModel.openDetail(it) }
                        )
                    }
                }

                item {
                    FilterTabsRow(
                        currentTab = state.filterTab,
                        onTabSelected = { viewModel.setFilterTab(it) },
                        pendingCount = state.totalPendingCount,
                        attentionCount = state.attentionItems.size,
                        honoredCount = state.totalHonoredCount
                    )
                }

                if (state.displayedCommitments.isEmpty()) {
                    item {
                        EmptyCommitmentsView(state.filterTab)
                    }
                } else {
                    items(
                        items = state.displayedCommitments,
                        key = { it.commitmentId }
                    ) { commitment ->
                        CommitmentCard(
                            commitment = commitment,
                            onStatusToggle = { newStatus ->
                                viewModel.setStatus(commitment.commitmentId, newStatus)
                            },
                            onClick = {
                                viewModel.openDetail(commitment.commitmentId)
                            }
                        )
                    }
                }
            }

            Surface(
                color = MaterialTheme.colorScheme.surface,
                shadowElevation = 8.dp,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(WindowInsets.navigationBars.asPaddingValues())
                    .imePadding()
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 12.dp)
                ) {
                    QuickCaptureBar(
                        isCapturing = state.isCapturing,
                        onCapture = { rawText ->
                            viewModel.capturePromise(rawText)
                        }
                    )
                }
            }
        }
    }

    state.activeClarificationItem?.let { item ->
        ClarificationDialog(
            item = item,
            onDismiss = { viewModel.closeClarification() },
            onConfirm = { answer, resolvedDueAtIso ->
                viewModel.clarifyTime(answer, resolvedDueAtIso)
            }
        )
    }

    state.activeDetailCommitment?.let { commitment ->
        CommitmentDetailDialog(
            commitment = commitment,
            onDismiss = { viewModel.closeDetail() },
            onStatusChange = { newStatus ->
                viewModel.setStatus(commitment.commitmentId, newStatus)
            },
            onSetBlockedReason = { reason ->
                viewModel.setBlockedReason(commitment.commitmentId, reason)
            },
            onDelete = {
                viewModel.deleteCommitment(commitment.commitmentId)
            }
        )
    }

}

@Composable
private fun HeroBannerCard() {
    Surface(
        shape = RoundedCornerShape(2.dp),
        color = PromiseCream,
        border = BorderStroke(2.dp, Slate900),
        shadowElevation = 10.dp,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 18.dp, vertical = 22.dp)
        ) {
            Text("●  THE WATCHER IS ALIVE", color = PromisePink,
                style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 1.4.sp, fontWeight = FontWeight.Bold))
            Spacer(modifier = Modifier.height(14.dp))
            ReceiptsWordmark()
            Spacer(modifier = Modifier.height(16.dp))
            Text("Every promise captured becomes EVIDENCE.",
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold), color = Slate900)
            Spacer(modifier = Modifier.height(5.dp))
            Text("Every deadline—recorded. The ledger does not sleep.",
                style = MaterialTheme.typography.bodyMedium, color = Slate600)
        }
    }
}

@Composable
private fun ReceiptsWordmark() {
    val cuts = listOf("R", "e", "C", "i", "E", "PT", "S")
    val colors = listOf(PromisePeach, PromiseCream, PromisePink, Slate900, PromiseCream, Slate900, PromiseCream)
    Row(verticalAlignment = Alignment.CenterVertically) {
        cuts.forEachIndexed { index, cut ->
            Surface(
                color = colors[index],
                border = BorderStroke(1.dp, Slate900),
                shape = RoundedCornerShape(0.dp),
                shadowElevation = 3.dp,
                modifier = Modifier.rotate(if (index % 2 == 0) -3f else 3f)
            ) {
                Text(cut, modifier = Modifier.padding(horizontal = 5.dp, vertical = 2.dp),
                    color = if (colors[index] == Slate900 || colors[index] == PromisePink) PromiseCream else Slate900,
                    fontFamily = androidx.compose.ui.text.font.FontFamily.Serif,
                    fontWeight = FontWeight.Black, fontSize = if (cut.length > 1) 20.sp else 27.sp)
            }
        }
    }
}

@Composable
private fun FilterTabsRow(
    currentTab: FilterTab,
    onTabSelected: (FilterTab) -> Unit,
    pendingCount: Int,
    attentionCount: Int,
    honoredCount: Int
) {
    val selectedColors = FilterChipDefaults.filterChipColors(
        selectedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
        selectedLabelColor = PromisePink
    )

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        FilterChip(
            selected = currentTab == FilterTab.ALL,
            onClick = { onTabSelected(FilterTab.ALL) },
            label = { Text("Active ($pendingCount)") },
            colors = selectedColors,
            modifier = Modifier.testTag("tab_all")
        )

        if (attentionCount > 0) {
            FilterChip(
                selected = currentTab == FilterTab.ATTENTION,
                onClick = { onTabSelected(FilterTab.ATTENTION) },
                label = { Text("Needs Attention ($attentionCount)") },
                colors = selectedColors,
                modifier = Modifier.testTag("tab_attention")
            )
        }

        FilterChip(
            selected = currentTab == FilterTab.COMPLETED,
            onClick = { onTabSelected(FilterTab.COMPLETED) },
            label = { Text("Honored ($honoredCount)") },
            colors = selectedColors,
            modifier = Modifier.testTag("tab_completed")
        )
    }
}

@Composable
private fun EmptyCommitmentsView(tab: FilterTab) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 24.dp)
    ) {
        Column(
            modifier = Modifier.padding(28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = Icons.Outlined.BookmarkBorder,
                contentDescription = null,
                tint = Slate400,
                modifier = Modifier.size(36.dp)
            )
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                text = when (tab) {
                    FilterTab.COMPLETED -> "No honored commitments yet"
                    FilterTab.ATTENTION -> "Nothing currently needs your attention"
                    else -> "No open commitments in your pocket"
                },
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Medium),
                color = MaterialTheme.colorScheme.onSurface,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "Capture a promise below in plain speech or text.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )
        }
    }
}
