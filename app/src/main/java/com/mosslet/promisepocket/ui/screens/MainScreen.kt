package com.mosslet.promisepocket.ui.screens

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
import androidx.compose.foundation.layout.imePadding
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
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.FilterList
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.outlined.BookmarkBorder
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
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
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mosslet.promisepocket.R
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
import com.mosslet.promisepocket.ui.theme.Slate700
import com.mosslet.promisepocket.ui.theme.Slate900
import com.mosslet.promisepocket.ui.viewmodel.FilterTab
import com.mosslet.promisepocket.ui.viewmodel.PromisePocketViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    viewModel: PromisePocketViewModel,
    onSignInWithAmazon: () -> Unit,
    onSignOutFromAmazon: () -> Unit,
    modifier: Modifier = Modifier
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    var isSearchOpen by remember { mutableStateOf(false) }
    var isAccountDialogOpen by remember { mutableStateOf(false) }

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
                            painter = painterResource(id = R.drawable.promise_pocket_icon_actual),
                            contentDescription = "Promise Pocket Logo",
                            contentScale = ContentScale.Crop,
                            modifier = Modifier
                                .size(38.dp)
                                .clip(CircleShape)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                text = "Promise Pocket",
                                style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = "Exact ledger of obligations",
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

                    Box {
                        Surface(
                            shape = RoundedCornerShape(20.dp),
                            color = MaterialTheme.colorScheme.surfaceVariant,
                            modifier = Modifier
                                .clip(RoundedCornerShape(20.dp))
                                .clickable { isAccountDialogOpen = true }
                                .testTag("btn_actor_menu")
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.Default.AccountCircle,
                                    contentDescription = null,
                                    tint = PromisePeach,
                                    modifier = Modifier.size(16.dp)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    text = if (state.isAmazonSignedIn) {
                                        state.amazonAccountName
                                            ?.substringBefore(' ')
                                            ?.takeIf(String::isNotBlank)
                                            ?: "Amazon"
                                    } else {
                                        "Local"
                                    },
                                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                                    color = MaterialTheme.colorScheme.onSurface
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

    if (isAccountDialogOpen) {
        AmazonAccountDialog(
            isSignedIn = state.isAmazonSignedIn,
            isLoading = state.isAmazonAuthLoading,
            accountName = state.amazonAccountName,
            accountEmail = state.amazonAccountEmail,
            onSignIn = onSignInWithAmazon,
            onSignOut = onSignOutFromAmazon,
            onDismiss = { isAccountDialogOpen = false }
        )
    }
}

@Composable
private fun AmazonAccountDialog(
    isSignedIn: Boolean,
    isLoading: Boolean,
    accountName: String?,
    accountEmail: String?,
    onSignIn: () -> Unit,
    onSignOut: () -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (isSignedIn) "Amazon account connected" else "Your Promise Pocket") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                if (isSignedIn) {
                    Text(
                        text = accountName ?: "Amazon account",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold)
                    )
                    accountEmail?.let {
                        Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Text(
                        "This is the shared identity Promise Pocket will use for the app and Alexa. " +
                            "Commitments still stay on this phone until cloud sync is switched on.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    Text(
                        "Sign in to give this phone and the Alexa skill one shared Amazon identity. " +
                            "You can keep using Promise Pocket locally without an account.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        },
        confirmButton = {
            when {
                isLoading -> CircularProgressIndicator(
                    modifier = Modifier.size(28.dp),
                    strokeWidth = 3.dp
                )
                isSignedIn -> TextButton(onClick = onSignOut) { Text("Sign out") }
                else -> Image(
                    painter = painterResource(R.drawable.btnlwa_gold_loginwithamazon),
                    contentDescription = "Sign in with Amazon",
                    contentScale = ContentScale.Fit,
                    modifier = Modifier
                        .width(210.dp)
                        .height(48.dp)
                        .semantics { role = Role.Button }
                        .clickable(onClick = onSignIn)
                        .testTag("btn_sign_in_with_amazon")
                )
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Close") }
        }
    )
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
                        color = PromiseCream,
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
