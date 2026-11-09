package com.example.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.components.PageHeader
import com.example.ui.components.letterSpaced
import com.example.ui.theme.ACCENT
import com.example.ui.theme.BORDER
import com.example.ui.theme.SURFACE
import com.example.ui.theme.TEXT
import com.example.ui.theme.TEXT_MUTED
import com.example.ui.theme.TEXT_SEC
import com.example.ui.viewmodel.FileOrganizerViewModel

// We support two export formats: CSV for spreadsheet apps like Excel, and JSON for code tools
enum class ExportFormat {
    CSV, JSON
}

// ExportScreen creates a full report of all scanned files in CSV or JSON format,
// so the user can copy it to their clipboard or share it to another app with one tap
@Composable
fun ExportScreen(
    viewModel: FileOrganizerViewModel,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val allFiles by viewModel.allFiles.collectAsState()
    var selectedFormat by remember { mutableStateOf(ExportFormat.CSV) }

    // Whenever the user switches between CSV and JSON, build the new report text right away
    val exportText = remember(allFiles, selectedFormat) {
        if (selectedFormat == ExportFormat.CSV) viewModel.exportCsv() else viewModel.exportJson()
    }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .testTag("export_screen"),
        contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 16.dp, bottom = 48.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            PageHeader(
                title = "Export Inventory",
                rightText = "${allFiles.size} records"
            )
        }

        // Card where the user picks CSV or JSON and taps Copy or Share
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
                        text = letterSpaced("Format Selection"),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TEXT_MUTED,
                        letterSpacing = 1.sp
                    )
                    Spacer(modifier = Modifier.height(12.dp))

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(
                            selected = selectedFormat == ExportFormat.CSV,
                            onClick = { selectedFormat = ExportFormat.CSV },
                            label = { Text("CSV Format", fontSize = 12.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = ACCENT,
                                selectedLabelColor = androidx.compose.ui.graphics.Color.White,
                                containerColor = SURFACE,
                                labelColor = TEXT_SEC
                            ),
                            border = FilterChipDefaults.filterChipBorder(
                                enabled = true,
                                selected = selectedFormat == ExportFormat.CSV,
                                borderColor = if (selectedFormat == ExportFormat.CSV) ACCENT else BORDER
                            ),
                            modifier = Modifier.testTag("format_csv_chip")
                        )

                        FilterChip(
                            selected = selectedFormat == ExportFormat.JSON,
                            onClick = { selectedFormat = ExportFormat.JSON },
                            label = { Text("JSON Format", fontSize = 12.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = ACCENT,
                                selectedLabelColor = androidx.compose.ui.graphics.Color.White,
                                containerColor = SURFACE,
                                labelColor = TEXT_SEC
                            ),
                            border = FilterChipDefaults.filterChipBorder(
                                enabled = true,
                                selected = selectedFormat == ExportFormat.JSON,
                                borderColor = if (selectedFormat == ExportFormat.JSON) ACCENT else BORDER
                            ),
                            modifier = Modifier.testTag("format_json_chip")
                        )
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        // Button that copies the generated report text to the phone clipboard
                        Button(
                            onClick = {
                                val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                val clip = ClipData.newPlainText("FileOrganizer Export", exportText)
                                clipboard.setPrimaryClip(clip)
                            },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = ACCENT,
                                contentColor = androidx.compose.ui.graphics.Color.White
                            ),
                            shape = RoundedCornerShape(6.dp),
                            modifier = Modifier
                                .weight(1f)
                                .testTag("copy_export_btn")
                        ) {
                            Text(
                                text = "Copy to Clipboard",
                                fontSize = 13.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = androidx.compose.ui.graphics.Color.White
                            )
                        }

                        // Button that opens the Android Share menu so the user can send the report to Drive or Email
                        OutlinedButton(
                            onClick = {
                                val shareIntent = Intent(Intent.ACTION_SEND).apply {
                                    type = "text/plain"
                                    putExtra(Intent.EXTRA_SUBJECT, "FileOrganizer Inventory Report")
                                    putExtra(Intent.EXTRA_TEXT, exportText)
                                }
                                context.startActivity(Intent.createChooser(shareIntent, "Share Inventory"))
                            },
                            shape = RoundedCornerShape(6.dp),
                            modifier = Modifier
                                .weight(1f)
                                .testTag("share_export_btn")
                        ) {
                            Text("Share Report", fontSize = 13.sp, color = TEXT)
                        }
                    }
                }
            }
        }

        // Preview box at the bottom that shows the first 2500 characters of the exported file
        item {
            Text(
                text = letterSpaced("Preview (${selectedFormat.name})"),
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = TEXT_MUTED,
                letterSpacing = 1.sp
            )
        }

        item {
            Surface(
                color = SURFACE,
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, BORDER, RoundedCornerShape(8.dp))
            ) {
                Text(
                    text = exportText.take(2500) + if (exportText.length > 2500) "\n\n... (${exportText.length - 2500} more characters truncated)" else "",
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    color = TEXT_SEC,
                    modifier = Modifier.padding(14.dp)
                )
            }
        }
    }
}
