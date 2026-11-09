package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.CategorySummary
import com.example.data.model.FileCategory
import com.example.data.model.FileItem
import com.example.ui.theme.BORDER
import com.example.ui.theme.BORDER_LIGHT
import com.example.ui.theme.CatArchive
import com.example.ui.theme.CatAudio
import com.example.ui.theme.CatDocument
import com.example.ui.theme.CatImage
import com.example.ui.theme.CatOther
import com.example.ui.theme.CatVideo
import com.example.ui.theme.SURFACE
import com.example.ui.theme.TEXT
import com.example.ui.theme.TEXT_MUTED
import com.example.ui.theme.TEXT_SEC

// This file holds reusable UI building blocks (like badges, progress bars, and summary cards)
// so we can use them across multiple screens without repeating code.

// Returns the matching shade of grey for each file category
fun getCategoryColor(category: FileCategory): Color {
    return when (category) {
        FileCategory.IMAGE -> CatImage
        FileCategory.DOCUMENT -> CatDocument
        FileCategory.AUDIO -> CatAudio
        FileCategory.VIDEO -> CatVideo
        FileCategory.ARCHIVE -> CatArchive
        FileCategory.OTHER -> CatOther
    }
}

// Adds spaces between uppercase letters so small section headings look clean and easy to read
fun letterSpaced(text: String): String {
    return text.uppercase().map { "$it " }.joinToString("").trimEnd()
}

// Small tag box shown next to a file with a colored dot and the category name
@Composable
fun CategoryBadge(category: FileCategory, modifier: Modifier = Modifier) {
    val color = getCategoryColor(category)
    Surface(
        color = SURFACE,
        shape = RoundedCornerShape(4.dp),
        modifier = modifier.border(1.dp, BORDER, RoundedCornerShape(4.dp))
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Small 7dp square color dot
            Box(
                modifier = Modifier
                    .size(7.dp)
                    .background(color)
            )
            Spacer(modifier = Modifier.width(6.dp))
            // Category name in lowercase letters
            Text(
                text = category.label.lowercase(),
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = TEXT_SEC
            )
        }
    }
}

// Horizontal progress bar used on the Dashboard and Charts screens to show storage share
@Composable
fun HorizontalStatusBar(
    fraction: Float,
    color: Color,
    modifier: Modifier = Modifier
) {
    // Light grey background track with a darker bar filled according to the percentage fraction
    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(6.dp)
            .background(BORDER_LIGHT, RoundedCornerShape(2.dp))
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(fraction.coerceIn(0f, 1f))
                .height(6.dp)
                .background(color, RoundedCornerShape(2.dp))
        )
    }
}

// Combined multi category bar at the top of the Charts screen showing how all categories share the storage
@Composable
fun CategoryProgressBar(
    summaries: List<CategorySummary>,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp)
                .background(BORDER_LIGHT, RoundedCornerShape(2.dp))
        ) {
            summaries.forEach { item ->
                // Only draw a segment if the category takes up more than half a percent of space
                if (item.percentage > 0.005f) {
                    Box(
                        modifier = Modifier
                            .weight(item.percentage.coerceAtLeast(0.01f))
                            .height(8.dp)
                            .background(getCategoryColor(item.category))
                    )
                }
            }
        }
    }
}

// Summary card box used at the top of the Dashboard (for Total Files, Total Storage, etc.)
@Composable
fun StatCard(
    title: String,
    value: String,
    subtitle: String? = null,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.border(1.dp, BORDER, RoundedCornerShape(8.dp)),
        colors = CardDefaults.cardColors(containerColor = SURFACE),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            // Small uppercase title at the top of the card
            Text(
                text = letterSpaced(title),
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = TEXT_MUTED,
                letterSpacing = 1.sp
            )
            Spacer(modifier = Modifier.height(6.dp))
            // Large main number in the center (like 220 or 4.2 GB)
            Text(
                text = value,
                fontSize = 28.sp,
                fontWeight = FontWeight.SemiBold,
                color = TEXT
            )
            // Optional small note at the bottom of the card
            if (subtitle != null) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = subtitle,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Normal,
                    color = TEXT_SEC
                )
            }
        }
    }
}

// Top title row for each screen with the page heading on the left and a short status text on the right
@Composable
fun PageHeader(
    title: String,
    rightText: String = "",
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(bottom = 16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = title,
            fontSize = 20.sp,
            fontWeight = FontWeight.SemiBold,
            color = TEXT
        )
        if (rightText.isNotEmpty()) {
            Text(
                text = rightText,
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium,
                color = TEXT_MUTED
            )
        }
    }
}

// Reusable card row for displaying a single file's name, path, size, and category badge
@Composable
fun FileRowItem(
    file: FileItem,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .border(1.dp, BORDER, RoundedCornerShape(8.dp))
            .testTag("file_item_${file.id}"),
        colors = CardDefaults.cardColors(containerColor = SURFACE),
        shape = RoundedCornerShape(8.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = file.name,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Medium,
                        color = TEXT,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f, fill = false)
                    )
                    // Show a small COPY badge if this file is an extra duplicate copy
                    if (file.isCopy) {
                        Spacer(modifier = Modifier.width(6.dp))
                        Surface(
                            color = BORDER_LIGHT,
                            shape = RoundedCornerShape(3.dp),
                            modifier = Modifier.border(1.dp, BORDER, RoundedCornerShape(3.dp))
                        ) {
                            Text(
                                text = "COPY",
                                fontSize = 9.sp,
                                fontWeight = FontWeight.Bold,
                                color = TEXT_MUTED,
                                modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                            )
                        }
                    }
                }
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = file.path,
                    fontSize = 11.sp,
                    color = TEXT_MUTED,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            // Human readable file size on top and exact byte count underneath
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = file.readableSize,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    color = TEXT_SEC
                )
                Text(
                    text = "${file.sizeBytes} B",
                    fontSize = 11.sp,
                    color = TEXT_MUTED
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            CategoryBadge(category = file.category)
        }
    }
}
