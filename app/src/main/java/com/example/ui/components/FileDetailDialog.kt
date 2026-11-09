package com.example.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.example.data.model.FileCategory
import com.example.data.model.FileItem
import com.example.ui.theme.ACCENT
import com.example.ui.theme.BORDER
import com.example.ui.theme.BORDER_LIGHT
import com.example.ui.theme.DANGER
import com.example.ui.theme.SURFACE
import com.example.ui.theme.TEXT
import com.example.ui.theme.TEXT_MUTED
import com.example.ui.theme.TEXT_SEC

// Popup dialog window that opens whenever the user taps on any file row.
// It shows the file location, byte size, SHA 256 fingerprint, and camera EXIF details for photos.
@Composable
fun FileDetailDialog(
    file: FileItem,
    onDismiss: () -> Unit,
    onDelete: () -> Unit
) {
    Dialog(onDismissRequest = onDismiss) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 16.dp)
                .border(1.dp, BORDER, RoundedCornerShape(8.dp))
                .testTag("file_detail_dialog"),
            shape = RoundedCornerShape(8.dp),
            colors = CardDefaults.cardColors(containerColor = SURFACE)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .padding(20.dp)
            ) {
                // Top row with the file name, category badge, and the X button to close the popup
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = file.name,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TEXT,
                            maxLines = 1
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        CategoryBadge(category = file.category)
                    }
                    IconButton(
                        onClick = onDismiss,
                        modifier = Modifier.testTag("close_detail_button")
                    ) {
                        Icon(imageVector = Icons.Default.Close, contentDescription = "Close", tint = TEXT_MUTED)
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))
                HorizontalDivider(color = BORDER_LIGHT)
                Spacer(modifier = Modifier.height(14.dp))

                // If this file has a sample photo picture attached, show the image right at the top
                if (file.previewResId != null) {
                    Image(
                        painter = painterResource(id = file.previewResId),
                        contentDescription = file.name,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(160.dp)
                            .clip(RoundedCornerShape(6.dp))
                            .border(1.dp, BORDER, RoundedCornerShape(6.dp))
                    )
                    Spacer(modifier = Modifier.height(14.dp))
                }

                // Basic file information: folder path, byte size, extension, and dates
                DetailRow(label = "Location", value = file.path)
                DetailRow(label = "Parent Folder", value = file.parentFolder)
                DetailRow(label = "File Size", value = "${file.readableSize} (${file.sizeBytes} bytes)")
                DetailRow(label = "Extension", value = file.extension.ifEmpty { "—" })
                DetailRow(label = "Created", value = file.createdTime)
                DetailRow(label = "Modified", value = file.modifiedTime)

                // If a SHA 256 fingerprint was calculated for this file, display it in a neat box
                if (file.hash != null) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = letterSpaced("SHA-256 HASH"),
                        fontSize = 10.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TEXT_MUTED,
                        letterSpacing = 1.sp
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Surface(
                        color = SURFACE,
                        shape = RoundedCornerShape(4.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, BORDER_LIGHT, RoundedCornerShape(4.dp))
                    ) {
                        Text(
                            text = file.hash,
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            color = TEXT_MUTED,
                            modifier = Modifier.padding(8.dp)
                        )
                    }
                }

                // If this file is a photo, display its pixel resolution, megapixels, and camera details
                if (file.category == FileCategory.IMAGE && file.imageMetadata != null) {
                    val meta = file.imageMetadata
                    Spacer(modifier = Modifier.height(14.dp))
                    HorizontalDivider(color = BORDER_LIGHT)
                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        text = letterSpaced("PHOTO EXIF METADATA"),
                        fontSize = 10.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TEXT_MUTED,
                        letterSpacing = 1.sp
                    )

                    Spacer(modifier = Modifier.height(8.dp))
                    DetailRow(label = "Resolution", value = "${meta.width} × ${meta.height} px (${meta.aspectRatio})")
                    DetailRow(label = "Megapixels", value = "${meta.megapixels} MP")
                    DetailRow(label = "Format", value = meta.format)
                    if (meta.camera != null) {
                        DetailRow(label = "Camera Model", value = meta.camera)
                    }
                    if (meta.capturedDate != null) {
                        DetailRow(label = "Date Taken", value = meta.capturedDate)
                    }
                    if (meta.hasGps) {
                        DetailRow(label = "GPS", value = "Geotag Embedded")
                    }
                }

                // If this file has a sample text or content preview, show it in a neat box
                if (file.sampleSnippet != null) {
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = letterSpaced("SAMPLE FILE PREVIEW"),
                        fontSize = 10.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TEXT_MUTED,
                        letterSpacing = 1.sp
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Surface(
                        color = SURFACE,
                        shape = RoundedCornerShape(4.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, BORDER_LIGHT, RoundedCornerShape(4.dp))
                    ) {
                        Text(
                            text = file.sampleSnippet,
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            color = TEXT_SEC,
                            modifier = Modifier.padding(10.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(20.dp))

                // Bottom buttons to either delete the file or close the popup window
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    OutlinedButton(
                        onClick = onDelete,
                        shape = RoundedCornerShape(6.dp),
                        modifier = Modifier
                            .weight(1f)
                            .testTag("delete_file_button")
                    ) {
                        Text("Delete File", fontSize = 12.sp, color = DANGER)
                    }

                    Button(
                        onClick = onDismiss,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = ACCENT,
                            contentColor = androidx.compose.ui.graphics.Color.White
                        ),
                        shape = RoundedCornerShape(6.dp),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text(
                            text = "Close",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = androidx.compose.ui.graphics.Color.White
                        )
                    }
                }
            }
        }
    }
}

// Helper row that places a grey label on the left and its value on the right
@Composable
private fun DetailRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.Top
    ) {
        Text(
            text = label,
            fontSize = 12.sp,
            color = TEXT_SEC,
            modifier = Modifier.width(96.dp)
        )
        Text(
            text = value,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium,
            color = TEXT,
            modifier = Modifier.weight(1f)
        )
    }
}
