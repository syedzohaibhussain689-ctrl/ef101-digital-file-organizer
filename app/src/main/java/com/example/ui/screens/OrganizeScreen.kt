package com.example.ui.screens

import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.RadioButton
import androidx.compose.material3.RadioButtonDefaults
import androidx.compose.material3.Surface
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
import com.example.data.model.OrganizeStrategy
import com.example.ui.components.CategoryBadge
import com.example.ui.components.PageHeader
import com.example.ui.components.letterSpaced
import com.example.ui.theme.ACCENT
import com.example.ui.theme.ACCENT_SOFT
import com.example.ui.theme.BORDER
import com.example.ui.theme.SURFACE
import com.example.ui.theme.TEXT
import com.example.ui.theme.TEXT_MUTED
import com.example.ui.theme.TEXT_SEC
import com.example.ui.viewmodel.FileOrganizerViewModel

// OrganizeScreen lets the user pick a sorting rule like By Category, By Date, or By Extension,
// check a preview showing every file moving from its Old Folder to its New Folder, and then tap Apply
@Composable
fun OrganizeScreen(
    viewModel: FileOrganizerViewModel,
    modifier: Modifier = Modifier
) {
    val currentStrategy by viewModel.organizeStrategy.collectAsState()
    val previewList by viewModel.organizePreview.collectAsState()

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .testTag("organize_screen"),
        contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 16.dp, bottom = 48.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            PageHeader(
                title = "Organize Files",
                rightText = "${previewList.size} files in plan"
            )
        }

        // Safety note card explaining that we always show a preview before moving any files
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, BORDER, RoundedCornerShape(8.dp)),
                colors = CardDefaults.cardColors(containerColor = SURFACE),
                shape = RoundedCornerShape(8.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = letterSpaced("DATA SAFETY GUARANTEE"),
                        fontSize = 10.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TEXT_MUTED,
                        letterSpacing = 1.sp
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Before any reorganization operation, the system previews all planned changes. Files are safely mapped and never silently overwritten.",
                        fontSize = 12.sp,
                        color = TEXT_SEC,
                        lineHeight = 17.sp
                    )
                }
            }
        }

        // Card with radio buttons where the user picks how they want their files organized
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
                        text = letterSpaced("Strategy"),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TEXT_MUTED,
                        letterSpacing = 1.sp
                    )
                    Spacer(modifier = Modifier.height(12.dp))

                    OrganizeStrategy.entries.forEach { strategy ->
                        val isSelected = currentStrategy == strategy
                        Surface(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { viewModel.setOrganizeStrategy(strategy) }
                                .padding(vertical = 4.dp)
                                .border(
                                    1.dp,
                                    if (isSelected) ACCENT else BORDER,
                                    RoundedCornerShape(6.dp)
                                ),
                            shape = RoundedCornerShape(6.dp),
                            color = if (isSelected) ACCENT_SOFT else SURFACE
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                RadioButton(
                                    selected = isSelected,
                                    onClick = { viewModel.setOrganizeStrategy(strategy) },
                                    colors = RadioButtonDefaults.colors(selectedColor = ACCENT)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Column {
                                    Text(
                                        text = strategy.title,
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        color = TEXT
                                    )
                                    Spacer(modifier = Modifier.height(2.dp))
                                    Text(
                                        text = strategy.description,
                                        fontSize = 12.sp,
                                        color = TEXT_SEC
                                    )
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    Button(
                        onClick = { viewModel.applyOrganization() },
                        enabled = previewList.isNotEmpty(),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = ACCENT,
                            contentColor = androidx.compose.ui.graphics.Color.White,
                            disabledContainerColor = ACCENT.copy(alpha = 0.4f),
                            disabledContentColor = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.7f)
                        ),
                        shape = RoundedCornerShape(6.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("apply_organize_btn")
                    ) {
                        Text(
                            text = "Apply Reorganization Plan",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = androidx.compose.ui.graphics.Color.White
                        )
                    }
                }
            }
        }

        // List below showing each file's current folder and the new folder it will move into
        item {
            Text(
                text = letterSpaced("Proposed Reorganization"),
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = TEXT_MUTED,
                letterSpacing = 1.sp
            )
        }

        items(previewList, key = { it.file.id }) { item ->
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, BORDER, RoundedCornerShape(8.dp)),
                colors = CardDefaults.cardColors(containerColor = SURFACE),
                shape = RoundedCornerShape(8.dp)
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = item.file.name,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Medium,
                            color = TEXT,
                            modifier = Modifier.weight(1f),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        CategoryBadge(category = item.file.category)
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = item.file.parentFolder,
                            fontSize = 11.sp,
                            color = TEXT_MUTED
                        )
                        Text(
                            text = "  →  ",
                            fontSize = 11.sp,
                            color = TEXT_SEC
                        )
                        Text(
                            text = item.destinationFolder,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TEXT
                        )
                    }
                }
            }
        }
    }
}
