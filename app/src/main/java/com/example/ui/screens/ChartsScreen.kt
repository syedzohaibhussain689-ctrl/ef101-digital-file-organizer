package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.formatReadableSize
import com.example.ui.components.CategoryBadge
import com.example.ui.components.CategoryProgressBar
import com.example.ui.components.HorizontalStatusBar
import com.example.ui.components.PageHeader
import com.example.ui.components.getCategoryColor
import com.example.ui.components.letterSpaced
import com.example.ui.theme.ACCENT
import com.example.ui.theme.BORDER
import com.example.ui.theme.BORDER_LIGHT
import com.example.ui.theme.SURFACE
import com.example.ui.theme.TEXT
import com.example.ui.theme.TEXT_MUTED
import com.example.ui.theme.TEXT_SEC
import com.example.ui.viewmodel.FileOrganizerViewModel

// ChartsScreen builds 4 easy to read visual summaries and graphs of our scanned files:
// 1. Storage by Category, 2. File Size Distribution, 3. Files Modified Over Time, 4. Top Extensions
@Composable
fun ChartsScreen(
    viewModel: FileOrganizerViewModel,
    modifier: Modifier = Modifier
) {
    val allFiles by viewModel.allFiles.collectAsState()
    val categorySummaries = viewModel.getCategorySummaries()
    val extensionSummaries = viewModel.getExtensionSummaries()
    val sizeTierSummaries = viewModel.getSizeTierSummaries()
    val timelineSummaries = viewModel.getTimelineSummaries()
    val totalBytes = allFiles.sumOf { it.sizeBytes }

    // Find the biggest counts so our horizontal bars scale cleanly from 0 to 100 percent
    val maxTimelineCount = timelineSummaries.maxOfOrNull { it.count } ?: 1
    val maxTierCount = sizeTierSummaries.maxOfOrNull { it.count } ?: 1

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .testTag("charts_screen"),
        contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 16.dp, bottom = 48.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            PageHeader(
                title = "Visual Summaries",
                rightText = "${allFiles.size} files cataloged"
            )
        }

        // Chart 1: Storage by Category with a multi color bar on top and single rows below
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
                        text = letterSpaced("Summary 1: Storage by Category"),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TEXT_MUTED,
                        letterSpacing = 1.sp
                    )
                    Spacer(modifier = Modifier.height(14.dp))

                    CategoryProgressBar(summaries = categorySummaries)

                    Spacer(modifier = Modifier.height(16.dp))

                    categorySummaries.forEach { item ->
                        val catColor = getCategoryColor(item.category)
                        val fraction = if (totalBytes > 0) item.totalBytes.toFloat() / totalBytes else 0f
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 5.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
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

                            HorizontalStatusBar(
                                fraction = fraction,
                                color = catColor,
                                modifier = Modifier
                                    .weight(1f)
                                    .padding(horizontal = 10.dp)
                            )

                            Text(
                                text = formatReadableSize(item.totalBytes),
                                fontSize = 13.sp,
                                color = TEXT_SEC,
                                modifier = Modifier.width(76.dp),
                                textAlign = androidx.compose.ui.text.style.TextAlign.End
                            )

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

        // Chart 2: File Size Distribution grouped into Small, Medium, Large, and Huge buckets
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
                        text = letterSpaced("Summary 2: File-Size Distribution"),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TEXT_MUTED,
                        letterSpacing = 1.sp
                    )
                    Spacer(modifier = Modifier.height(14.dp))

                    sizeTierSummaries.forEach { tier ->
                        val fraction = tier.count.toFloat() / maxTierCount.coerceAtLeast(1)
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.width(110.dp)) {
                                Text(
                                    text = tier.tier.label,
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = TEXT
                                )
                                Text(
                                    text = tier.tier.rangeDesc,
                                    fontSize = 10.sp,
                                    color = TEXT_MUTED
                                )
                            }

                            HorizontalStatusBar(
                                fraction = fraction,
                                color = ACCENT,
                                modifier = Modifier
                                    .weight(1f)
                                    .padding(horizontal = 10.dp)
                            )

                            Text(
                                text = "${tier.count} files",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Medium,
                                color = TEXT,
                                modifier = Modifier.width(60.dp),
                                textAlign = androidx.compose.ui.text.style.TextAlign.End
                            )

                            Text(
                                text = formatReadableSize(tier.totalBytes),
                                fontSize = 12.sp,
                                color = TEXT_SEC,
                                modifier = Modifier.width(70.dp),
                                textAlign = androidx.compose.ui.text.style.TextAlign.End
                            )
                        }
                    }
                }
            }
        }

        // Chart 3: Files Modified Over Time grouped by year and month
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
                        text = letterSpaced("Summary 3: Files Modified Over Time"),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TEXT_MUTED,
                        letterSpacing = 1.sp
                    )
                    Spacer(modifier = Modifier.height(14.dp))

                    timelineSummaries.forEach { period ->
                        val fraction = period.count.toFloat() / maxTimelineCount.coerceAtLeast(1)
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 5.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = period.period,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Medium,
                                color = TEXT,
                                modifier = Modifier.width(70.dp)
                            )

                            HorizontalStatusBar(
                                fraction = fraction,
                                color = ACCENT,
                                modifier = Modifier
                                    .weight(1f)
                                    .padding(horizontal = 10.dp)
                            )

                            Text(
                                text = "${period.count} files",
                                fontSize = 12.sp,
                                color = TEXT_SEC,
                                modifier = Modifier.width(60.dp),
                                textAlign = androidx.compose.ui.text.style.TextAlign.End
                            )

                            Text(
                                text = formatReadableSize(period.totalBytes),
                                fontSize = 12.sp,
                                color = TEXT_MUTED,
                                modifier = Modifier.width(70.dp),
                                textAlign = androidx.compose.ui.text.style.TextAlign.End
                            )
                        }
                    }
                }
            }
        }

        // Chart 4: Table of the top file extensions
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
                        text = letterSpaced("Summary 4: Top File Extensions"),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TEXT_MUTED,
                        letterSpacing = 1.sp
                    )
                    Spacer(modifier = Modifier.height(14.dp))

                    extensionSummaries.forEachIndexed { index, ext ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = ext.extension.uppercase(),
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                color = TEXT,
                                modifier = Modifier.width(64.dp)
                            )

                            CategoryBadge(category = ext.category)

                            Spacer(modifier = Modifier.weight(1f))

                            Text(
                                text = "${ext.count} files",
                                fontSize = 12.sp,
                                color = TEXT_MUTED,
                                modifier = Modifier.padding(end = 16.dp)
                            )

                            Text(
                                text = formatReadableSize(ext.totalBytes),
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Medium,
                                color = TEXT_SEC
                            )
                        }

                        if (index < extensionSummaries.size - 1) {
                            HorizontalDivider(color = BORDER_LIGHT)
                        }
                    }
                }
            }
        }
    }
}
