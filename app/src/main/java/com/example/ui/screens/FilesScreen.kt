package com.example.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.FilterAlt
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.FileCategory
import com.example.ui.components.CategoryBadge
import com.example.ui.components.getCategoryColor
import com.example.ui.components.letterSpaced
import com.example.ui.theme.ACCENT
import com.example.ui.theme.ACCENT_SOFT
import com.example.ui.theme.BORDER
import com.example.ui.theme.BORDER_LIGHT
import com.example.ui.theme.SURFACE
import com.example.ui.theme.TEXT
import com.example.ui.theme.TEXT_MUTED
import com.example.ui.theme.TEXT_SEC
import com.example.ui.viewmodel.FileOrganizerViewModel
import com.example.ui.viewmodel.SortField

// FilesScreen is the tab where the user can browse, search, filter, and sort all their files.
// It also has a button at the top to switch between a table List view and a 2 column Grid view.
@Composable
fun FilesScreen(
    viewModel: FileOrganizerViewModel,
    modifier: Modifier = Modifier
) {
    // Get all the current filter settings and the matching file list from the ViewModel
    val files by viewModel.filteredFiles.collectAsState()
    val allFiles by viewModel.allFiles.collectAsState()
    val searchQuery by viewModel.searchQuery.collectAsState()
    val selectedCategory by viewModel.selectedCategory.collectAsState()
    val sortField by viewModel.sortField.collectAsState()
    val sortAscending by viewModel.sortAscending.collectAsState()
    val isGridView by viewModel.isGridView.collectAsState()
    val isMoreOpen by viewModel.isMoreFiltersOpen.collectAsState()
    val selectedFolder by viewModel.selectedFolder.collectAsState()
    val selectedExt by viewModel.selectedExtension.collectAsState()
    val minSizeMb by viewModel.minSizeMb.collectAsState()
    val maxSizeMb by viewModel.maxSizeMb.collectAsState()
    val dateFrom by viewModel.dateFrom.collectAsState()
    val dateTo by viewModel.dateTo.collectAsState()

    // Lists of all folders and file extensions for the dropdown filter menus
    val uniqueFolders = remember(allFiles) { listOf("All folders") + viewModel.getUniqueFolders() }
    val uniqueExtensions = remember(allFiles) { listOf("All extensions") + viewModel.getUniqueExtensions() }

    var folderDropdownOpen by remember { mutableStateOf(false) }
    var extDropdownOpen by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .testTag("files_screen"),
        contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 16.dp, bottom = 48.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // Top header showing the screen name, how many files matched, and the List or Grid switch
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "All Files",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = TEXT
                )

                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = "${files.size} of ${allFiles.size} results",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Medium,
                        color = TEXT_MUTED,
                        modifier = Modifier.padding(end = 12.dp)
                    )

                    // Small two button switch to flip between List view and Grid view
                    Row(
                        modifier = Modifier
                            .border(1.dp, BORDER, RoundedCornerShape(6.dp))
                            .background(SURFACE, RoundedCornerShape(6.dp))
                    ) {
                        Surface(
                            color = if (!isGridView) ACCENT else SURFACE,
                            shape = RoundedCornerShape(topStart = 5.dp, bottomStart = 5.dp),
                            modifier = Modifier
                                .clickable { if (isGridView) viewModel.toggleViewMode() }
                                .padding(horizontal = 12.dp, vertical = 6.dp)
                        ) {
                            Text(
                                text = "List",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Medium,
                                color = if (!isGridView) androidx.compose.ui.graphics.Color.White else TEXT
                            )
                        }

                        Box(modifier = Modifier.width(1.dp).height(24.dp).background(BORDER))

                        Surface(
                            color = if (isGridView) ACCENT else SURFACE,
                            shape = RoundedCornerShape(topEnd = 5.dp, bottomEnd = 5.dp),
                            modifier = Modifier
                                .clickable { if (!isGridView) viewModel.toggleViewMode() }
                                .padding(horizontal = 12.dp, vertical = 6.dp)
                        ) {
                            Text(
                                text = "Grid",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Medium,
                                color = if (isGridView) androidx.compose.ui.graphics.Color.White else TEXT
                            )
                        }
                    }
                }
            }
        }

        // Search box along with the Filters button and Clear button
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { viewModel.setSearchQuery(it) },
                    modifier = Modifier
                        .weight(1f)
                        .testTag("search_input"),
                    placeholder = { Text("Search name, extension, path...", fontSize = 13.sp, color = TEXT_MUTED) },
                    leadingIcon = {
                        Icon(
                            imageVector = Icons.Default.Search,
                            contentDescription = "Search",
                            tint = TEXT_MUTED,
                            modifier = Modifier.size(18.dp)
                        )
                    },
                    trailingIcon = {
                        if (searchQuery.isNotEmpty()) {
                            IconButton(onClick = { viewModel.setSearchQuery("") }) {
                                Icon(
                                    imageVector = Icons.Default.Clear,
                                    contentDescription = "Clear",
                                    tint = TEXT_MUTED,
                                    modifier = Modifier.size(16.dp)
                                )
                            }
                        }
                    },
                    singleLine = true,
                    shape = RoundedCornerShape(6.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = ACCENT,
                        unfocusedBorderColor = BORDER,
                        focusedContainerColor = SURFACE,
                        unfocusedContainerColor = SURFACE
                    )
                )

                OutlinedButton(
                    onClick = { viewModel.toggleMoreFilters() },
                    shape = RoundedCornerShape(6.dp),
                    modifier = Modifier.testTag("more_filters_btn")
                ) {
                    Icon(
                        imageVector = Icons.Default.FilterAlt,
                        contentDescription = null,
                        modifier = Modifier.size(14.dp),
                        tint = if (isMoreOpen) ACCENT else TEXT_SEC
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = if (isMoreOpen) "Fewer" else "Filters",
                        fontSize = 12.sp,
                        color = if (isMoreOpen) ACCENT else TEXT_SEC
                    )
                }

                OutlinedButton(
                    onClick = { viewModel.clearAllFilters() },
                    shape = RoundedCornerShape(6.dp)
                ) {
                    Text("Clear", fontSize = 12.sp, color = TEXT_SEC)
                }
            }
        }

        // Extra filter box that slides open for Folder, Extension, Size in MB, and Date
        item {
            AnimatedVisibility(visible = isMoreOpen) {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, BORDER, RoundedCornerShape(8.dp)),
                    colors = CardDefaults.cardColors(containerColor = SURFACE),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text(
                            text = letterSpaced("ADVANCED ATTRIBUTE FILTERS"),
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TEXT_MUTED,
                            letterSpacing = 1.sp
                        )

                        // First row: Dropdown menus to pick a specific Folder or Extension
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Box(modifier = Modifier.weight(1f)) {
                                Surface(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clickable { folderDropdownOpen = true }
                                        .border(1.dp, BORDER, RoundedCornerShape(6.dp)),
                                    shape = RoundedCornerShape(6.dp),
                                    color = SURFACE
                                ) {
                                    Text(
                                        text = selectedFolder ?: "All folders",
                                        fontSize = 12.sp,
                                        color = TEXT,
                                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 10.dp),
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                }
                                DropdownMenu(
                                    expanded = folderDropdownOpen,
                                    onDismissRequest = { folderDropdownOpen = false }
                                ) {
                                    uniqueFolders.forEach { f ->
                                        DropdownMenuItem(
                                            text = { Text(f, fontSize = 12.sp) },
                                            onClick = {
                                                viewModel.setFolderFilter(if (f == "All folders") null else f)
                                                folderDropdownOpen = false
                                            }
                                        )
                                    }
                                }
                            }

                            Box(modifier = Modifier.weight(1f)) {
                                Surface(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clickable { extDropdownOpen = true }
                                        .border(1.dp, BORDER, RoundedCornerShape(6.dp)),
                                    shape = RoundedCornerShape(6.dp),
                                    color = SURFACE
                                ) {
                                    Text(
                                        text = selectedExt ?: "All extensions",
                                        fontSize = 12.sp,
                                        color = TEXT,
                                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 10.dp),
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                }
                                DropdownMenu(
                                    expanded = extDropdownOpen,
                                    onDismissRequest = { extDropdownOpen = false }
                                ) {
                                    uniqueExtensions.forEach { ext ->
                                        DropdownMenuItem(
                                            text = { Text(ext, fontSize = 12.sp) },
                                            onClick = {
                                                viewModel.setExtensionFilter(if (ext == "All extensions") null else ext)
                                                extDropdownOpen = false
                                            }
                                        )
                                    }
                                }
                            }
                        }

                        // Second row: Text boxes to type minimum and maximum file size in MB
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            OutlinedTextField(
                                value = minSizeMb,
                                onValueChange = { viewModel.setMinSizeMb(it) },
                                placeholder = { Text("Min Size (MB)", fontSize = 11.sp, color = TEXT_MUTED) },
                                singleLine = true,
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(6.dp),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = ACCENT,
                                    unfocusedBorderColor = BORDER,
                                    focusedContainerColor = SURFACE,
                                    unfocusedContainerColor = SURFACE
                                )
                            )

                            OutlinedTextField(
                                value = maxSizeMb,
                                onValueChange = { viewModel.setMaxSizeMb(it) },
                                placeholder = { Text("Max Size (MB)", fontSize = 11.sp, color = TEXT_MUTED) },
                                singleLine = true,
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(6.dp),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = ACCENT,
                                    unfocusedBorderColor = BORDER,
                                    focusedContainerColor = SURFACE,
                                    unfocusedContainerColor = SURFACE
                                )
                            )
                        }

                        // Third row: Text boxes to filter files between two dates
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            OutlinedTextField(
                                value = dateFrom,
                                onValueChange = { viewModel.setDateFrom(it) },
                                placeholder = { Text("From (YYYY-MM-DD)", fontSize = 11.sp, color = TEXT_MUTED) },
                                singleLine = true,
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(6.dp),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = ACCENT,
                                    unfocusedBorderColor = BORDER,
                                    focusedContainerColor = SURFACE,
                                    unfocusedContainerColor = SURFACE
                                )
                            )

                            OutlinedTextField(
                                value = dateTo,
                                onValueChange = { viewModel.setDateTo(it) },
                                placeholder = { Text("To (YYYY-MM-DD)", fontSize = 11.sp, color = TEXT_MUTED) },
                                singleLine = true,
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(6.dp),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = ACCENT,
                                    unfocusedBorderColor = BORDER,
                                    focusedContainerColor = SURFACE,
                                    unfocusedContainerColor = SURFACE
                                )
                            )
                        }
                    }
                }
            }
        }

        // Side scrolling row of category filter pills like All, Image, Document, and Audio
        item {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                CategoryFilterPill(
                    label = "All (${allFiles.size})",
                    isSelected = selectedCategory == null,
                    onClick = { viewModel.selectCategory(null) }
                )

                FileCategory.entries.forEach { cat ->
                    val count = allFiles.count { it.category == cat }
                    CategoryFilterPill(
                        label = "${cat.label} ($count)",
                        isSelected = selectedCategory == cat,
                        color = getCategoryColor(cat),
                        onClick = { viewModel.selectCategory(cat) }
                    )
                }
            }
        }

        // Row of sort buttons for Name, Size, Date, and Extension with up or down arrows
        item {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 2.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = letterSpaced("SORT"),
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = TEXT_MUTED,
                    letterSpacing = 1.sp
                )

                SortField.entries.forEach { field ->
                    val isSelected = sortField == field
                    Surface(
                        shape = RoundedCornerShape(4.dp),
                        color = if (isSelected) ACCENT_SOFT else SURFACE,
                        modifier = Modifier
                            .clickable { viewModel.setSortField(field) }
                            .border(1.dp, if (isSelected) ACCENT else BORDER, RoundedCornerShape(4.dp))
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = field.name.lowercase().replaceFirstChar { it.uppercase() },
                                fontSize = 11.sp,
                                fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Medium,
                                color = if (isSelected) ACCENT else TEXT_SEC
                            )
                            if (isSelected) {
                                Spacer(modifier = Modifier.width(3.dp))
                                Text(
                                    text = if (sortAscending) "↑" else "↓",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = ACCENT
                                )
                            }
                        }
                    }
                }
            }
        }

        // Show the main file list or grid below
        if (files.isEmpty()) {
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
                            .padding(vertical = 48.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(
                                text = "No files match these filters",
                                fontSize = 13.sp,
                                color = TEXT_MUTED
                            )
                        }
                    }
                }
            }
        } else if (isGridView) {
            // 2 column Grid View that groups files into pairs of 2 per row
            item {
                val chunked = files.chunked(2)
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    chunked.forEach { pair ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            pair.forEach { file ->
                                Card(
                                    modifier = Modifier
                                        .weight(1f)
                                        .clickable { viewModel.showFileDetails(file) }
                                        .border(1.dp, BORDER, RoundedCornerShape(8.dp)),
                                    colors = CardDefaults.cardColors(containerColor = SURFACE),
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    Column(modifier = Modifier.padding(14.dp)) {
                                        if (file.previewResId != null) {
                                            Image(
                                                painter = painterResource(id = file.previewResId),
                                                contentDescription = file.name,
                                                contentScale = ContentScale.Crop,
                                                modifier = Modifier
                                                    .fillMaxWidth()
                                                    .height(92.dp)
                                                    .clip(RoundedCornerShape(6.dp))
                                                    .border(1.dp, BORDER_LIGHT, RoundedCornerShape(6.dp))
                                            )
                                            Spacer(modifier = Modifier.height(8.dp))
                                        }
                                        CategoryBadge(category = file.category)
                                        Spacer(modifier = Modifier.height(10.dp))
                                        Text(
                                            text = file.name,
                                            fontSize = 13.sp,
                                            fontWeight = FontWeight.Medium,
                                            color = TEXT,
                                            maxLines = 2,
                                            overflow = TextOverflow.Ellipsis
                                        )
                                        Spacer(modifier = Modifier.height(4.dp))
                                        Text(
                                            text = "${file.parentFolder} • ${file.readableSize}",
                                            fontSize = 11.sp,
                                            color = TEXT_MUTED
                                        )
                                    }
                                }
                            }
                            if (pair.size == 1) {
                                Spacer(modifier = Modifier.weight(1f))
                            }
                        }
                    }
                }
            }
        } else {
            // Clean Table List View where Name, Type badge, and Size appear in neat rows
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, BORDER, RoundedCornerShape(8.dp)),
                    colors = CardDefaults.cardColors(containerColor = SURFACE),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Column {
                        // Column headers at the top of the table
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = letterSpaced("NAME"),
                                fontSize = 11.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = TEXT_MUTED,
                                modifier = Modifier.weight(1f)
                            )
                            Text(
                                text = letterSpaced("TYPE"),
                                fontSize = 11.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = TEXT_MUTED,
                                modifier = Modifier.width(84.dp)
                            )
                            Text(
                                text = letterSpaced("SIZE"),
                                fontSize = 11.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = TEXT_MUTED,
                                modifier = Modifier.width(68.dp),
                                textAlign = androidx.compose.ui.text.style.TextAlign.End
                            )
                        }

                        HorizontalDivider(color = BORDER)

                        files.forEachIndexed { index, file ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { viewModel.showFileDetails(file) }
                                    .padding(horizontal = 16.dp, vertical = 10.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                if (file.previewResId != null) {
                                    Image(
                                        painter = painterResource(id = file.previewResId),
                                        contentDescription = file.name,
                                        contentScale = ContentScale.Crop,
                                        modifier = Modifier
                                            .size(34.dp)
                                            .clip(RoundedCornerShape(4.dp))
                                            .border(1.dp, BORDER_LIGHT, RoundedCornerShape(4.dp))
                                    )
                                    Spacer(modifier = Modifier.width(10.dp))
                                }
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = file.name,
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.Medium,
                                        color = TEXT,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                    Text(
                                        text = file.path,
                                        fontSize = 11.sp,
                                        color = TEXT_MUTED,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                }

                                Spacer(modifier = Modifier.width(8.dp))

                                CategoryBadge(
                                    category = file.category,
                                    modifier = Modifier.width(84.dp)
                                )

                                Text(
                                    text = file.readableSize,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = TEXT_SEC,
                                    modifier = Modifier.width(68.dp),
                                    textAlign = androidx.compose.ui.text.style.TextAlign.End
                                )
                            }

                            if (index < files.size - 1) {
                                HorizontalDivider(color = BORDER_LIGHT)
                            }
                        }
                    }
                }
            }
        }
    }
}

// Small button pill used in the horizontal category bar
@Composable
private fun CategoryFilterPill(
    label: String,
    isSelected: Boolean,
    color: androidx.compose.ui.graphics.Color? = null,
    onClick: () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(6.dp),
        color = if (isSelected) ACCENT else SURFACE,
        modifier = Modifier
            .clickable(onClick = onClick)
            .border(1.dp, if (isSelected) ACCENT else BORDER, RoundedCornerShape(6.dp))
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            if (color != null && !isSelected) {
                Box(
                    modifier = Modifier
                        .size(6.dp)
                        .background(color)
                )
                Spacer(modifier = Modifier.width(6.dp))
            }
            Text(
                text = label,
                fontSize = 12.sp,
                fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Medium,
                color = if (isSelected) androidx.compose.ui.graphics.Color.White else TEXT_SEC
            )
        }
    }
}
