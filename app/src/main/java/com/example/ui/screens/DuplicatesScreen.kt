package com.example.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.Image
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.DuplicateGroup
import com.example.data.model.FileItem
import com.example.data.model.formatReadableSize
import com.example.ui.components.PageHeader
import com.example.ui.components.letterSpaced
import com.example.ui.theme.ACCENT
import com.example.ui.theme.BORDER
import com.example.ui.theme.BORDER_LIGHT
import com.example.ui.theme.DANGER
import com.example.ui.theme.SURFACE
import com.example.ui.theme.TEXT
import com.example.ui.theme.TEXT_MUTED
import com.example.ui.theme.TEXT_SEC
import com.example.ui.viewmodel.FileOrganizerViewModel

// DuplicatesScreen shows the groups of identical files found by our 2 step SHA 256 check.
// It also includes a helpful note explaining why we cannot just trust file names to find duplicates.
@Composable
fun DuplicatesScreen(
    viewModel: FileOrganizerViewModel,
    modifier: Modifier = Modifier
) {
    val groups by viewModel.duplicateGroups.collectAsState()
    val isAnalyzing by viewModel.isAnalyzingDuplicates.collectAsState()
    val progress by viewModel.duplicateProgress.collectAsState()
    val statusText by viewModel.duplicateStatusText.collectAsState()
    val allFiles by viewModel.allFiles.collectAsState()

    val totalWastedBytes = groups.sumOf { it.wastedBytes }
    var explanationOpen by remember { mutableStateOf(true) }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .testTag("duplicates_screen"),
        contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 16.dp, bottom = 48.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Screen header that displays the total wasted space on the right side
        item {
            PageHeader(
                title = "Duplicate Files",
                rightText = if (groups.isNotEmpty()) "${groups.size} groups, ${formatReadableSize(totalWastedBytes)} wasted" else ""
            )
        }

        // Info card that explains why we check both file size and the SHA 256 digital fingerprint
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, BORDER, RoundedCornerShape(8.dp)),
                colors = CardDefaults.cardColors(containerColor = SURFACE),
                shape = RoundedCornerShape(8.dp)
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { explanationOpen = !explanationOpen },
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = letterSpaced("Required Understanding: Why Name != Duplicate"),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TEXT_MUTED,
                            letterSpacing = 1.sp
                        )
                        Icon(
                            imageVector = if (explanationOpen) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                            contentDescription = null,
                            tint = TEXT_MUTED,
                            modifier = Modifier.size(16.dp)
                        )
                    }

                    AnimatedVisibility(visible = explanationOpen) {
                        Column(modifier = Modifier.padding(top = 10.dp)) {
                            Text(
                                text = "1. Name Collisions: Different files frequently share identical names across different folders (e.g. 'report.pdf' or 'notes.txt'), but contain entirely distinct content.",
                                fontSize = 12.sp,
                                color = TEXT_SEC,
                                lineHeight = 17.sp
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "2. Renamed Duplicates: Exact duplicate files often have different names (e.g. 'DSC_005.jpg', 'DSC_005_copy.jpg', or 'vacation_hero.jpg').",
                                fontSize = 12.sp,
                                color = TEXT_SEC,
                                lineHeight = 17.sp
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "3. Two-Step Detection: Stage 1 groups files by identical byte size. Stage 2 computes a SHA-256 cryptographic digest so identical content is verified with mathematical certainty.",
                                fontSize = 12.sp,
                                color = TEXT_SEC,
                                lineHeight = 17.sp
                            )
                        }
                    }
                }
            }
        }

        // Card with the Scan button, Clean button, and live progress bar while checking files
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, BORDER, RoundedCornerShape(8.dp)),
                colors = CardDefaults.cardColors(containerColor = SURFACE),
                shape = RoundedCornerShape(8.dp)
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Text(
                        text = "Duplicate reporting is informational only and does not automatically delete files. Review matches below before taking action.",
                        fontSize = 13.sp,
                        color = TEXT_SEC,
                        lineHeight = 18.sp
                    )

                    if (isAnalyzing) {
                        Spacer(modifier = Modifier.height(14.dp))
                        LinearProgressIndicator(
                            progress = { progress },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(4.dp),
                            color = ACCENT,
                            trackColor = BORDER_LIGHT
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = statusText,
                            fontSize = 12.sp,
                            color = TEXT_SEC
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Button(
                            onClick = { viewModel.runDuplicateAnalysis() },
                            enabled = !isAnalyzing && allFiles.isNotEmpty(),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = ACCENT,
                                contentColor = androidx.compose.ui.graphics.Color.White,
                                disabledContainerColor = ACCENT.copy(alpha = 0.4f),
                                disabledContentColor = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.7f)
                            ),
                            shape = RoundedCornerShape(6.dp),
                            modifier = Modifier
                                .weight(1f)
                                .testTag("run_duplicate_scan_btn")
                        ) {
                            Text(
                                text = if (groups.isEmpty()) "Scan Duplicates" else "Rescan Duplicates",
                                fontSize = 13.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = androidx.compose.ui.graphics.Color.White
                            )
                        }

                        if (groups.isNotEmpty()) {
                            OutlinedButton(
                                onClick = { viewModel.resolveAllDuplicates() },
                                shape = RoundedCornerShape(6.dp),
                                modifier = Modifier
                                    .weight(1f)
                                    .testTag("clean_all_duplicates_btn")
                            ) {
                                Text("Remove Duplicate Copies", fontSize = 13.sp, color = DANGER)
                            }
                        }
                    }
                }
            }
        }

        // List all the duplicate groups found below
        if (groups.isEmpty() && !isAnalyzing) {
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, BORDER, RoundedCornerShape(8.dp)),
                    colors = CardDefaults.cardColors(containerColor = SURFACE),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 40.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "No duplicate files found",
                            fontSize = 13.sp,
                            color = TEXT_MUTED
                        )
                    }
                }
            }
        } else {
            items(groups, key = { it.hash }) { group ->
                DuplicateGroupCard(
                    group = group,
                    onFileClick = { viewModel.showFileDetails(it) },
                    onResolveGroup = { viewModel.resolveGroup(group) }
                )
            }
        }
    }
}

// This card shows all the matching files inside one duplicate group along with their shared SHA 256 hash
@Composable
private fun DuplicateGroupCard(
    group: DuplicateGroup,
    onFileClick: (FileItem) -> Unit,
    onResolveGroup: () -> Unit
) {
    var isExpanded by remember { mutableStateOf(true) }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, BORDER, RoundedCornerShape(8.dp))
            .testTag("duplicate_group_${group.hash.take(8)}"),
        colors = CardDefaults.cardColors(containerColor = SURFACE),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column {
            // Tapping the group header opens or closes the card
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { isExpanded = !isExpanded }
                    .padding(horizontal = 20.dp, vertical = 14.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "${group.files.size} identical files — ${formatReadableSize(group.sizeBytes)} each",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = TEXT
                )

                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = "${formatReadableSize(group.wastedBytes)} wasted",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium,
                        color = TEXT_SEC
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (isExpanded) "▲" else "▼",
                        fontSize = 10.sp,
                        color = TEXT_MUTED
                    )
                }
            }

            AnimatedVisibility(visible = isExpanded) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 20.dp, vertical = 12.dp)
                ) {
                    HorizontalDivider(color = BORDER_LIGHT)
                    Spacer(modifier = Modifier.height(10.dp))

                    // The shared SHA 256 digital fingerprint for this group
                    Row(
                        modifier = Modifier.padding(bottom = 10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "SHA-256: ",
                            fontSize = 12.sp,
                            color = TEXT_MUTED
                        )
                        Text(
                            text = group.hash,
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            color = TEXT_MUTED,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }

                    // Show each file in the group, marking the first one as KEEP and the rest as COPY
                    group.files.forEachIndexed { index, file ->
                        val isKeep = index == 0
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = if (isKeep) "KEEP" else "COPY",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = if (isKeep) TEXT else TEXT_MUTED,
                                modifier = Modifier.width(48.dp)
                            )

                            if (file.previewResId != null) {
                                Image(
                                    painter = painterResource(id = file.previewResId),
                                    contentDescription = file.name,
                                    contentScale = ContentScale.Crop,
                                    modifier = Modifier
                                        .size(30.dp)
                                        .clip(RoundedCornerShape(4.dp))
                                        .border(1.dp, BORDER_LIGHT, RoundedCornerShape(4.dp))
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                            }

                            Text(
                                text = file.path,
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Medium,
                                color = TEXT,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                modifier = Modifier.weight(1f)
                            )

                            Spacer(modifier = Modifier.width(8.dp))

                            Text(
                                text = formatReadableSize(file.sizeBytes),
                                fontSize = 13.sp,
                                color = TEXT_SEC,
                                modifier = Modifier.padding(end = 12.dp)
                            )

                            Surface(
                                shape = RoundedCornerShape(4.dp),
                                color = SURFACE,
                                modifier = Modifier
                                    .border(1.dp, BORDER, RoundedCornerShape(4.dp))
                                    .clickable { onFileClick(file) }
                            ) {
                                Text(
                                    text = "Details",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = TEXT,
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                                )
                            }
                        }

                        if (index < group.files.size - 1) {
                            HorizontalDivider(color = BORDER_LIGHT)
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        text = "This report is informational only. Review and manage files manually.",
                        fontSize = 12.sp,
                        color = TEXT_MUTED
                    )

                    Spacer(modifier = Modifier.height(10.dp))
                    OutlinedButton(
                        onClick = onResolveGroup,
                        shape = RoundedCornerShape(6.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("resolve_group_btn")
                    ) {
                        Text("Delete Extra Copies", fontSize = 12.sp, color = DANGER)
                    }
                }
            }
        }
    }
}
