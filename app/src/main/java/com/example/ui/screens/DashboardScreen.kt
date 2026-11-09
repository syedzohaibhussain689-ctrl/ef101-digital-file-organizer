package com.example.ui.screens

import androidx.compose.foundation.background
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.formatReadableSize
import com.example.ui.components.HorizontalStatusBar
import com.example.ui.components.PageHeader
import com.example.ui.components.StatCard
import com.example.ui.components.getCategoryColor
import com.example.ui.components.letterSpaced
import com.example.ui.theme.BORDER
import com.example.ui.theme.BORDER_LIGHT
import com.example.ui.theme.SURFACE
import com.example.ui.theme.TEXT
import com.example.ui.theme.TEXT_MUTED
import com.example.ui.theme.TEXT_SEC
import com.example.ui.viewmodel.FileOrganizerViewModel

// DashboardScreen is our main home tab where you can see the total files, total storage,
// category breakdown bars, and the top 10 largest files all in one place
@Composable
fun DashboardScreen(
    viewModel: FileOrganizerViewModel,
    onPickFolder: () -> Unit,
    modifier: Modifier = Modifier
) {
    // We watch the live file list and duplicate groups from the ViewModel
    val files by viewModel.allFiles.collectAsState()
    val lastScan by viewModel.lastScanTime.collectAsState()
    val duplicateGroups by viewModel.duplicateGroups.collectAsState()
    val snapshots by viewModel.scanSnapshots.collectAsState()

    // Here we do the math for the 4 summary cards at the top of the screen
    val count = files.size
    val folderCount = viewModel.getFolderCount()
    val totalBytes = files.sumOf { it.sizeBytes }
    val wastedBytes = duplicateGroups.sumOf { it.wastedBytes }
    val extraCopies = duplicateGroups.sumOf { it.files.size - 1 }
    val categories = viewModel.getCategorySummaries()
    val topCategory = categories.maxByOrNull { it.totalBytes }

    // Sort the files from biggest to smallest and grab the top 10 largest ones
    val largestFiles = files.sortedByDescending { it.sizeBytes }.take(10)
    val maxFileBytes = largestFiles.firstOrNull()?.sizeBytes ?: 1L

    val avgBytes = if (count > 0) totalBytes / count else 0L

    // We use a LazyColumn so the whole dashboard scrolls smoothly up and down
    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .testTag("dashboard_screen"),
        contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 16.dp, bottom = 48.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp)
    ) {
        // The main page title and the time of the last scan on the right
        item {
            PageHeader(
                title = "Dashboard",
                rightText = if (lastScan.isNotEmpty()) "Scanned $lastScan" else ""
            )
        }

        // The 4 summary cards arranged in a 2 by 2 grid
        item {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    StatCard(
                        title = "Total Files",
                        value = "$count",
                        subtitle = "$folderCount subfolders",
                        modifier = Modifier.weight(1f)
                    )
                    StatCard(
                        title = "Total Storage",
                        value = formatReadableSize(totalBytes),
                        subtitle = "${formatReadableSize(avgBytes)} avg per file",
                        modifier = Modifier.weight(1f)
                    )
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    StatCard(
                        title = "Duplicates Found",
                        value = "$extraCopies",
                        subtitle = "${formatReadableSize(wastedBytes)} recoverable",
                        modifier = Modifier.weight(1f)
                    )
                    StatCard(
                        title = "Categories",
                        value = "${categories.size}",
                        subtitle = topCategory?.let { "largest: ${it.category.label} (${formatReadableSize(it.totalBytes)})" } ?: "—",
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }

        // The By Category card that shows a colored bar and total size for each file type
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, BORDER, RoundedCornerShape(8.dp)),
                colors = CardDefaults.cardColors(containerColor = SURFACE),
                shape = RoundedCornerShape(8.dp)
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(
                        text = letterSpaced("By Category"),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TEXT_MUTED,
                        letterSpacing = 1.sp
                    )
                    Spacer(modifier = Modifier.height(14.dp))

                    categories.forEach { item ->
                        val catColor = getCategoryColor(item.category)
                        val fraction = if (totalBytes > 0) item.totalBytes.toFloat() / totalBytes else 0f
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 5.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            // The category name and its small colored square
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier.width(96.dp)
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(8.dp)
                                        .background(catColor)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = item.category.label,
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = TEXT
                                )
                            }

                            // Horizontal progress bar showing how much space this category uses
                            HorizontalStatusBar(
                                fraction = fraction,
                                color = catColor,
                                modifier = Modifier
                                    .weight(1f)
                                    .padding(horizontal = 10.dp)
                            )

                            // The easy to read size of this category in MB or GB
                            Text(
                                text = formatReadableSize(item.totalBytes),
                                fontSize = 13.sp,
                                color = TEXT_SEC,
                                modifier = Modifier.width(76.dp),
                                textAlign = androidx.compose.ui.text.style.TextAlign.End
                            )

                            // How many files are inside this category
                            Text(
                                text = "${item.count} files",
                                fontSize = 12.sp,
                                color = TEXT_MUTED,
                                modifier = Modifier.width(60.dp),
                                textAlign = androidx.compose.ui.text.style.TextAlign.End
                            )
                        }
                    }
                }
            }
        }

        // Card showing the 10 largest files, and tapping any row opens its details popup
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, BORDER, RoundedCornerShape(8.dp)),
                colors = CardDefaults.cardColors(containerColor = SURFACE),
                shape = RoundedCornerShape(8.dp)
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(
                        text = letterSpaced("10 Largest Files"),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TEXT_MUTED,
                        letterSpacing = 1.sp
                    )
                    Spacer(modifier = Modifier.height(14.dp))

                    largestFiles.forEachIndexed { index, file ->
                        val rank = index + 1
                        val catColor = getCategoryColor(file.category)
                        val fraction = if (maxFileBytes > 0) file.sizeBytes.toFloat() / maxFileBytes else 0f

                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { viewModel.showFileDetails(file) }
                                .padding(vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "$rank",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = TEXT_MUTED,
                                modifier = Modifier.width(22.dp)
                            )

                            Text(
                                text = file.name,
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Medium,
                                color = TEXT,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                modifier = Modifier.width(130.dp)
                            )

                            HorizontalStatusBar(
                                fraction = fraction,
                                color = catColor,
                                modifier = Modifier
                                    .weight(1f)
                                    .padding(horizontal = 10.dp)
                            )

                            Text(
                                text = file.readableSize,
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Medium,
                                color = TEXT_SEC,
                                modifier = Modifier.width(68.dp),
                                textAlign = androidx.compose.ui.text.style.TextAlign.End
                            )
                        }
                    }
                }
            }
        }

        // Card at the bottom that shows the history of folders we scanned earlier
        if (snapshots.isNotEmpty()) {
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, BORDER, RoundedCornerShape(8.dp)),
                    colors = CardDefaults.cardColors(containerColor = SURFACE),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Text(
                            text = letterSpaced("Saved Scan History Snapshots"),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TEXT_MUTED,
                            letterSpacing = 1.sp
                        )
                        Spacer(modifier = Modifier.height(10.dp))

                        snapshots.forEachIndexed { index, snap ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 6.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = snap.folderPath,
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Medium,
                                        color = TEXT,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                    Text(
                                        text = snap.timestamp,
                                        fontSize = 11.sp,
                                        color = TEXT_MUTED
                                    )
                                }
                                Text(
                                    text = "${snap.fileCount} files • ${formatReadableSize(snap.totalBytes)}",
                                    fontSize = 12.sp,
                                    color = TEXT_SEC
                                )
                            }
                            if (index < snapshots.size - 1) {
                                HorizontalDivider(color = BORDER_LIGHT)
                            }
                        }
                    }
                }
            }
        }
    }
}
