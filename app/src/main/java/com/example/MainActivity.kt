package com.example

import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.DriveFileMove
import androidx.compose.material.icons.filled.FileDownload
import androidx.compose.material.icons.filled.FormatListBulleted
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScaffoldDefaults
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.components.FileDetailDialog
import com.example.ui.components.letterSpaced
import com.example.ui.screens.ChartsScreen
import com.example.ui.screens.DashboardScreen
import com.example.ui.screens.DuplicatesScreen
import com.example.ui.screens.ExportScreen
import com.example.ui.screens.FilesScreen
import com.example.ui.screens.OrganizeScreen
import com.example.ui.theme.ACCENT
import com.example.ui.theme.ACCENT_SOFT
import com.example.ui.theme.BG
import com.example.ui.theme.BORDER
import com.example.ui.theme.BORDER_LIGHT
import com.example.ui.theme.DANGER
import com.example.ui.theme.FileOrganizerTheme
import com.example.ui.theme.SURFACE
import com.example.ui.theme.TEXT
import com.example.ui.theme.TEXT_MUTED
import com.example.ui.theme.TEXT_SEC
import com.example.ui.viewmodel.AppTab
import com.example.ui.viewmodel.FileOrganizerViewModel

// MainActivity is the front door of our Android app. When you tap the app icon on your phone, this runs first.
class MainActivity : ComponentActivity() {

    // Create the ViewModel which holds our app data safely even if you rotate your phone screen
    private val viewModel: FileOrganizerViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Let the app draw cleanly all the way to the edges of the phone screen
        enableEdgeToEdge()

        setContent {
            // Apply our custom colors and fonts and launch the main screen layout
            FileOrganizerTheme {
                MainAppShell(viewModel = viewModel)
            }
        }
    }
}

// MainAppShell builds the overall frame of the app: the top bar, the 6 navigation tabs, and the active screen
@Composable
fun MainAppShell(viewModel: FileOrganizerViewModel) {
    // Watch these values from the ViewModel so the screen updates automatically whenever data changes
    val activeTab by viewModel.activeTab.collectAsState()
    val duplicateGroups by viewModel.duplicateGroups.collectAsState()
    val selectedFile by viewModel.selectedFileForDetails.collectAsState()
    val toastMessage by viewModel.toastMessage.collectAsState()
    val rootFolder by viewModel.rootFolderName.collectAsState()
    val lastScanTime by viewModel.lastScanTime.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    // Opens the built in Android folder picker when the user taps the Scan button
    val folderPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocumentTree()
    ) { uri: Uri? ->
        if (uri != null) {
            viewModel.scanFolderUri(uri)
        }
    }

    // Whenever a new popup message arrives, show it in a small bar at the bottom of the screen
    LaunchedEffect(toastMessage) {
        toastMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearToast()
        }
    }

    // Check how wide the screen is: use a left sidebar on tablets or a bottom bar on phones
    BoxWithConstraints(modifier = Modifier.fillMaxSize().background(SURFACE)) {
        val isWide = maxWidth >= 600.dp

        if (isWide) {
            // Wide screen layout with a sidebar on the left and the main page on the right
            Row(modifier = Modifier.fillMaxSize()) {
                Column(
                    modifier = Modifier
                        .width(240.dp)
                        .fillMaxHeight()
                        .background(BG)
                        .border(1.dp, BORDER)
                        .padding(horizontal = 16.dp, vertical = 24.dp)
                ) {
                    // App title and project code at the top of the sidebar
                    Column(modifier = Modifier.padding(horizontal = 8.dp)) {
                        Text(
                            text = "FileOrganizer",
                            fontSize = 15.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TEXT
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = letterSpaced("EF101-P19"),
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Medium,
                            color = TEXT_MUTED
                        )
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    Text(
                        text = letterSpaced("MAIN"),
                        fontSize = 10.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TEXT_MUTED,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 6.dp)
                    )

                    // Loop through all 6 tabs and create a clickable menu button for each one
                    AppTab.entries.forEach { tab ->
                        val isSelected = activeTab == tab
                        val count = if (tab == AppTab.DUPLICATES && duplicateGroups.isNotEmpty()) duplicateGroups.size else null

                        SidebarNavItem(
                            title = tab.title,
                            icon = getTabIcon(tab),
                            isSelected = isSelected,
                            badgeCount = count,
                            onClick = { viewModel.setActiveTab(tab) }
                        )
                    }

                    Spacer(modifier = Modifier.weight(1f))

                    // Primary dark Scan Folder button at the bottom of the sidebar
                    Button(
                        onClick = { folderPickerLauncher.launch(null) },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = ACCENT,
                            contentColor = androidx.compose.ui.graphics.Color.White
                        ),
                        shape = RoundedCornerShape(6.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("sidebar_scan_btn")
                    ) {
                        Text(
                            text = "Scan Folder",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = androidx.compose.ui.graphics.Color.White
                        )
                    }
                }

                // Right side area: top bar with folder name and action buttons, plus the main page below
                Column(modifier = Modifier.weight(1f).fillMaxHeight().background(SURFACE)) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(SURFACE)
                            .padding(horizontal = 32.dp, vertical = 16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = rootFolder,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Medium,
                            color = TEXT_MUTED,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f)
                        )

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            if (lastScanTime.isNotEmpty()) {
                                Text(
                                    text = lastScanTime,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = TEXT_MUTED,
                                    modifier = Modifier.padding(end = 16.dp)
                                )
                            }

                            OutlinedButton(
                                onClick = { folderPickerLauncher.launch(null) },
                                shape = RoundedCornerShape(6.dp),
                                modifier = Modifier.padding(end = 8.dp)
                            ) {
                                Text("Rescan", fontSize = 12.sp, color = TEXT)
                            }

                            OutlinedButton(
                                onClick = { viewModel.resetToDemoData() },
                                shape = RoundedCornerShape(6.dp)
                            ) {
                                Text("Demo", fontSize = 12.sp, color = TEXT)
                            }
                        }
                    }

                    HorizontalDivider(color = BORDER_LIGHT)

                    Box(modifier = Modifier.weight(1f).fillMaxWidth().background(SURFACE)) {
                        TabContent(activeTab, viewModel, onPickFolder = { folderPickerLauncher.launch(null) })
                    }
                }
            }
        } else {
            // Phone screen layout: clean top bar, main page in the middle, and 6 tab buttons at the bottom
            Scaffold(
                modifier = Modifier.fillMaxSize().testTag("main_scaffold"),
                contentWindowInsets = ScaffoldDefaults.contentWindowInsets,
                snackbarHost = { SnackbarHost(snackbarHostState) },
                topBar = {
                    Column(
                        modifier = Modifier
                            .background(SURFACE)
                            .statusBarsPadding()
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 20.dp, vertical = 12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = "FileOrganizer",
                                    fontSize = 16.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = TEXT
                                )
                                Text(
                                    text = letterSpaced("EF101-P19"),
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = TEXT_MUTED
                                )
                            }

                            Row(verticalAlignment = Alignment.CenterVertically) {
                                OutlinedButton(
                                    onClick = { folderPickerLauncher.launch(null) },
                                    shape = RoundedCornerShape(6.dp),
                                    modifier = Modifier.padding(end = 6.dp)
                                ) {
                                    Text("Scan", fontSize = 12.sp, fontWeight = FontWeight.Medium, color = TEXT)
                                }

                                OutlinedButton(
                                    onClick = { viewModel.resetToDemoData() },
                                    shape = RoundedCornerShape(6.dp)
                                ) {
                                    Text("Demo", fontSize = 12.sp, fontWeight = FontWeight.Medium, color = TEXT)
                                }
                            }
                        }
                        HorizontalDivider(color = BORDER)
                    }
                },
                bottomBar = {
                    NavigationBar(
                        containerColor = SURFACE,
                        tonalElevation = 3.dp,
                        windowInsets = WindowInsets.navigationBars,
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, BORDER)
                            .testTag("main_bottom_nav")
                    ) {
                        AppTab.entries.forEach { tab ->
                            val isSelected = activeTab == tab
                            val tabIcon = getTabIcon(tab)
                            // Short names so all 6 tabs fit comfortably side by side on a phone screen
                            val shortLabel = when (tab) {
                                AppTab.DASHBOARD -> "Home"
                                AppTab.FILES -> "Files"
                                AppTab.DUPLICATES -> "Dupes"
                                AppTab.CHARTS -> "Charts"
                                AppTab.ORGANIZE -> "Organize"
                                AppTab.EXPORT -> "Export"
                            }

                            NavigationBarItem(
                                selected = isSelected,
                                onClick = { viewModel.setActiveTab(tab) },
                                icon = {
                                    // Show a small red count badge on the Dupes icon if duplicate files exist
                                    if (tab == AppTab.DUPLICATES && duplicateGroups.isNotEmpty()) {
                                        BadgedBox(
                                            badge = {
                                                Badge(
                                                    containerColor = DANGER,
                                                    contentColor = androidx.compose.ui.graphics.Color.White
                                                ) {
                                                    Text(
                                                        text = "${duplicateGroups.size}",
                                                        color = androidx.compose.ui.graphics.Color.White,
                                                        fontSize = 9.sp,
                                                        fontWeight = FontWeight.Bold
                                                    )
                                                }
                                            }
                                        ) {
                                            Icon(imageVector = tabIcon, contentDescription = tab.title)
                                        }
                                    } else {
                                        Icon(imageVector = tabIcon, contentDescription = tab.title)
                                    }
                                },
                                label = {
                                    Text(
                                        text = shortLabel,
                                        fontSize = 10.sp,
                                        maxLines = 1,
                                        softWrap = false,
                                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Medium
                                    )
                                },
                                colors = NavigationBarItemDefaults.colors(
                                    selectedIconColor = TEXT,
                                    selectedTextColor = TEXT,
                                    indicatorColor = ACCENT_SOFT,
                                    unselectedIconColor = TEXT_MUTED,
                                    unselectedTextColor = TEXT_SEC
                                ),
                                modifier = Modifier.testTag("nav_tab_${tab.name.lowercase()}")
                            )
                        }
                    }
                }
            ) { innerPadding ->
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(innerPadding)
                        .background(SURFACE)
                ) {
                    TabContent(activeTab, viewModel, onPickFolder = { folderPickerLauncher.launch(null) })
                }
            }
        }

        // If the user tapped on a file row, show its full details in a popup dialog box
        selectedFile?.let { file ->
            FileDetailDialog(
                file = file,
                onDismiss = { viewModel.dismissFileDetails() },
                onDelete = { viewModel.deleteFile(file) }
            )
        }
    }
}

// Draws one clickable menu item row inside the tablet sidebar
@Composable
private fun SidebarNavItem(
    title: String,
    icon: ImageVector,
    isSelected: Boolean,
    badgeCount: Int? = null,
    onClick: () -> Unit
) {
    Surface(
        color = if (isSelected) ACCENT_SOFT else BG,
        shape = RoundedCornerShape(6.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 2.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = if (isSelected) ACCENT else TEXT_SEC,
                modifier = Modifier.size(16.dp)
            )
            Spacer(modifier = Modifier.width(12.dp))
            Text(
                text = title,
                fontSize = 13.sp,
                fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Medium,
                color = if (isSelected) ACCENT else TEXT_SEC,
                modifier = Modifier.weight(1f)
            )
            if (badgeCount != null && badgeCount > 0) {
                Text(
                    text = "$badgeCount",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    color = TEXT_MUTED
                )
            }
        }
    }
}

// Switches the center screen based on which tab the user tapped
@Composable
private fun TabContent(
    activeTab: AppTab,
    viewModel: FileOrganizerViewModel,
    onPickFolder: () -> Unit
) {
    when (activeTab) {
        AppTab.DASHBOARD -> DashboardScreen(
            viewModel = viewModel,
            onPickFolder = onPickFolder
        )
        AppTab.FILES -> FilesScreen(viewModel = viewModel)
        AppTab.DUPLICATES -> DuplicatesScreen(viewModel = viewModel)
        AppTab.CHARTS -> ChartsScreen(viewModel = viewModel)
        AppTab.ORGANIZE -> OrganizeScreen(viewModel = viewModel)
        AppTab.EXPORT -> ExportScreen(viewModel = viewModel)
    }
}

// Returns the matching icon picture for each of the 6 navigation tabs
private fun getTabIcon(tab: AppTab): ImageVector {
    return when (tab) {
        AppTab.DASHBOARD -> Icons.Default.Dashboard
        AppTab.FILES -> Icons.Default.FormatListBulleted
        AppTab.DUPLICATES -> Icons.Default.ContentCopy
        AppTab.CHARTS -> Icons.Default.BarChart
        AppTab.ORGANIZE -> Icons.Default.DriveFileMove
        AppTab.EXPORT -> Icons.Default.FileDownload
    }
}
