package com.example.promisepocket.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.Image
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
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.FilterList
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.outlined.BookmarkBorder
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.promisepocket.R
import com.example.promisepocket.data.model.CommitmentStatus
import com.example.promisepocket.ui.components.AttentionSection
import com.example.promisepocket.ui.components.ClarificationDialog
import com.example.promisepocket.ui.components.CommitmentCard
import com.example.promisepocket.ui.components.CommitmentDetailDialog
import com.example.promisepocket.ui.components.QuickCaptureBar
import com.example.promisepocket.ui.theme.SandGold
import com.example.promisepocket.ui.theme.SandGoldLight
import com.example.promisepocket.ui.theme.Slate100
import com.example.promisepocket.ui.theme.Slate200
import com.example.promisepocket.ui.theme.Slate400
import com.example.promisepocket.ui.theme.Slate600
import com.example.promisepocket.ui.theme.Slate800
import com.example.promisepocket.ui.theme.Slate900
import com.example.promisepocket.ui.viewmodel.FilterTab
import com.example.promisepocket.ui.viewmodel.PromisePocketViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    viewModel: PromisePocketViewModel,
    modifier: Modifier = Modifier
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    var isSearchOpen by remember { mutableStateOf(false) }
    var isActorMenuOpen by remember { mutableStateOf(false) }

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
                        Image(
                            painter = painterResource(id = R.drawable.promise_pocket_icon_1788013703332),
                            contentDescription = "Promise Pocket Logo",
                            modifier = Modifier
                                .size(34.dp)
                                .clip(CircleShape)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                text = "Promise Pocket",
                                style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                                color = Slate900
                            )
                            Text(
                                text = "Exact ledger of obligations",
                                style = MaterialTheme.typography.labelSmall,
                                color = Slate600
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
                            tint = Slate800
                        )
                    }

                    Box {
                        Surface(
                            shape = RoundedCornerShape(20.dp),
                            color = Slate100,
                            modifier = Modifier
                                .clip(RoundedCornerShape(20.dp))
                                .clickable { isActorMenuOpen = true }
                                .testTag("btn_actor_menu")
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.Default.AccountCircle,
                                    contentDescription = null,
                                    tint = Slate700,
                                    modifier = Modifier.size(16.dp)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    text = state.currentActor,
                                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                                    color = Slate900
                                )
                            }
                        }

                        DropdownMenu(
                            expanded = isActorMenuOpen,
                            onDismissRequest = { isActorMenuOpen = false }
                        ) {
                            state.availableActors.forEach { actor ->
                                DropdownMenuItem(
                                    text = {
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            modifier = Modifier.fillMaxWidth()
                                        ) {
                                            Text(actor)
                                            if (actor == state.currentActor) {
                                                Icon(
                                                    imageVector = Icons.Default.Check,
                                                    contentDescription = null,
                                                    tint = SandGold,
                                                    modifier = Modifier.size(16.dp)
                                                )
                                            }
                                        }
                                    },
                                    onClick = {
                                        viewModel.setActor(actor)
                                        isActorMenuOpen = false
                                    }
                                )
                            }
                        }
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
            // Optional Search Bar
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
                // Calm Hero Banner
                item {
                    HeroBannerCard()
                }

                // Needs Human Attention Section (Deterministic Policy)
                if (state.attentionItems.isNotEmpty() && state.filterTab != FilterTab.COMPLETED) {
                    item {
                        AttentionSection(
                            items = state.attentionItems,
                            onClarifyClick = { viewModel.openClarification(it) },
                            onResolveClick = { viewModel.setStatus(it, com.example.promisepocket.data.model.CommitmentStatus.COMPLETED) },
                            onItemClick = { viewModel.openDetail(it) }
                        )
                    }
                }

                // Filter Tabs
                item {
                    FilterTabsRow(
                        currentTab = state.filterTab,
                        onTabSelected = { viewModel.setFilterTab(it) },
                        pendingCount = state.totalPendingCount,
                        attentionCount = state.attentionItems.size,
                        honoredCount = state.totalHonoredCount
                    )
                }

                // Empty State or List
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

            // Quick Capture Input Bar at Bottom
            Surface(
                color = MaterialTheme.colorScheme.surface,
                shadowElevation = 8.dp,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(WindowInsets.navigationBars.asPaddingValues())
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

    // Clarification Dialog
    state.activeClarificationItem?.let { item ->
        ClarificationDialog(
            item = item,
            onDismiss = { viewModel.closeClarification() },
            onConfirm = { answer, resolvedDueAtIso ->
                viewModel.clarifyTime(answer, resolvedDueAtIso)
            }
        )
    }

    // Commitment Detail Dialog
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
        shape = RoundedCornerShape(20.dp),
        color = Slate900,
        modifier = Modifier.fillMaxWidth()
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(130.dp)
        ) {
            Image(
                painter = painterResource(id = R.drawable.promise_pocket_hero_1788013716030),
                contentDescription = "Quiet Pocket Desk",
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .fillMaxSize()
                    .clip(RoundedCornerShape(20.dp))
            )

            // Gradient scrim
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        Brush.horizontalGradient(
                            colors = listOf(
                                Slate900.copy(alpha = 0.90f),
                                Slate900.copy(alpha = 0.60f),
                                Color.Transparent
                            )
                        )
                    )
            )

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(18.dp),
                verticalArrangement = Arrangement.Center
            ) {
                Text(
                    text = "A quiet place for what you mean to do.",
                    style = MaterialTheme.typography.titleMedium.copy(
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White
                    )
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Captures ordinary commitments. Interrupts only when truly needed.",
                    style = MaterialTheme.typography.bodyMedium.copy(
                        color = SandGoldLight,
                        fontSize = 13.sp
                    )
                )
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
            colors = FilterChipDefaults.filterChipColors(
                selectedContainerColor = Slate800,
                selectedLabelColor = Color.White
            ),
            modifier = Modifier.testTag("tab_all")
        )

        if (attentionCount > 0) {
            FilterChip(
                selected = currentTab == FilterTab.ATTENTION,
                onClick = { onTabSelected(FilterTab.ATTENTION) },
                label = { Text("Needs Attention ($attentionCount)") },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = Slate800,
                    selectedLabelColor = Color.White
                ),
                modifier = Modifier.testTag("tab_attention")
            )
        }

        FilterChip(
            selected = currentTab == FilterTab.COMPLETED,
            onClick = { onTabSelected(FilterTab.COMPLETED) },
            label = { Text("Honored ($honoredCount)") },
            colors = FilterChipDefaults.filterChipColors(
                selectedContainerColor = Slate800,
                selectedLabelColor = Color.White
            ),
            modifier = Modifier.testTag("tab_completed")
        )
    }
}

@Composable
private fun EmptyCommitmentsView(tab: FilterTab) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = androidx.compose.foundation.BorderStroke(1.dp, Slate200),
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
                color = Slate800,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "Capture a promise below in plain speech or text.",
                style = MaterialTheme.typography.bodyMedium,
                color = Slate600,
                textAlign = TextAlign.Center
            )
        }
    }
}

val Slate700 = Color(0xFF334155)
