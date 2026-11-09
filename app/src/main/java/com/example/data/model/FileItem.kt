package com.example.data.model

import java.util.Locale

// This is our main blueprint (data class) that holds all the information about one single file.
// Using a Kotlin data class gives us helpful tools like copying and comparing items automatically.
data class FileItem(
    val id: String,
    val name: String,
    val path: String,
    val extension: String,
    val category: FileCategory,
    val sizeBytes: Long,
    val createdTime: String,
    val modifiedTime: String,
    val parentFolder: String,
    val hash: String? = null, // The SHA 256 digital fingerprint used to check if two files have the exact same content
    val isCopy: Boolean = false, // Marked true if this file is an extra copy inside a duplicate group
    val imageMetadata: ImageMetadata? = null, // Holds camera and pixel info if this file is a photo
    val previewResId: Int? = null, // Holds the sample photo picture so we can show it on screen
    val sampleSnippet: String? = null // Holds a short sample preview of what is inside a text or data file
) {
    // Turns the byte size into an easy to read string like 4.5 MB
    val readableSize: String get() = formatReadableSize(sizeBytes)

    // Places the file into one of four size buckets (Small, Medium, Large, or Huge) for the Charts screen
    val sizeTier: FileSizeTier
        get() = when {
            sizeBytes < 1024 * 1024 -> FileSizeTier.SMALL
            sizeBytes < 10L * 1024 * 1024 -> FileSizeTier.MEDIUM
            sizeBytes < 100L * 1024 * 1024 -> FileSizeTier.LARGE
            else -> FileSizeTier.HUGE
        }
}

// The 6 main categories used to sort every file in our app
enum class FileCategory(val label: String) {
    IMAGE("Image"),
    DOCUMENT("Document"),
    AUDIO("Audio"),
    VIDEO("Video"),
    ARCHIVE("Archive"),
    OTHER("Other");

    companion object {
        // Looks at the file ending (like .jpg or .pdf) and returns the matching category
        fun fromExtension(ext: String): FileCategory {
            // Convert the ending to lowercase and make sure it starts with a dot
            val clean = ext.lowercase(Locale.ROOT).let { if (it.startsWith(".")) it else ".$it" }
            return when (clean) {
                ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".svg", ".tiff" -> IMAGE
                ".pdf", ".doc", ".docx", ".txt", ".xlsx", ".pptx", ".csv", ".md", ".rtf", ".odt" -> DOCUMENT
                ".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma" -> AUDIO
                ".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv" -> VIDEO
                ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz" -> ARCHIVE
                else -> OTHER
            }
        }
    }
}

// Four size buckets used to group files by how much space they take up on the Charts screen
enum class FileSizeTier(val label: String, val rangeDesc: String) {
    SMALL("Small", "< 1 MB"),
    MEDIUM("Medium", "1 MB – 10 MB"),
    LARGE("Large", "10 MB – 100 MB"),
    HUGE("Huge", "> 100 MB")
}

// Stores photo details like pixel width and height, camera model, and GPS status when a user taps an image
data class ImageMetadata(
    val format: String,
    val width: Int,
    val height: Int,
    val megapixels: Double,
    val aspectRatio: String,
    val camera: String?,
    val capturedDate: String?,
    val hasGps: Boolean
)

// Groups together files that share the exact same SHA 256 fingerprint
data class DuplicateGroup(
    val hash: String,
    val files: List<FileItem>,
    val sizeBytes: Long,
    val wastedBytes: Long // How much storage space we can save by deleting the extra copies
)

// The four classes below hold ready to display numbers for the Dashboard and Charts screens
data class CategorySummary(
    val category: FileCategory,
    val count: Int,
    val totalBytes: Long,
    val percentage: Float
)

// Keeps track of how many times a specific file extension (like .jpg or .pdf) appears
data class ExtensionSummary(
    val extension: String,
    val category: FileCategory,
    val count: Int,
    val totalBytes: Long
)

// Keeps track of how many files and bytes belong in each size bucket
data class SizeTierSummary(
    val tier: FileSizeTier,
    val count: Int,
    val totalBytes: Long,
    val percentage: Float
)

// Keeps track of how many files were modified in a specific year and month
data class TimelineSummary(
    val period: String, // Year and month formatted like 2024 07
    val count: Int,
    val totalBytes: Long
)

// Saves a short record of each scan so we can show recent scan history on the Dashboard
data class ScanSnapshot(
    val id: String,
    val timestamp: String,
    val folderPath: String,
    val fileCount: Int,
    val totalBytes: Long,
    val folderCount: Int
)

// Shows the current file path and the new planned path before moving files in the Organize tab
data class OrganizePreviewItem(
    val file: FileItem,
    val originalPath: String,
    val proposedPath: String,
    val destinationFolder: String
)

// The 3 ways a user can choose to sort their messy folder on the Organize screen
enum class OrganizeStrategy(val title: String, val description: String) {
    BY_CATEGORY("By Category", "Organize files into Images, Documents, Audio, Video, Archives"),
    BY_DATE("By Date (Year/Month)", "Group files into Year and Month folders based on modified date"),
    BY_EXTENSION("By Extension", "Sort files into subfolders named after their extension (.jpg, .pdf, etc.)")
}

// Divides a byte count by 1024 step by step to turn it into KB, MB, GB, or TB
fun formatReadableSize(bytes: Long): String {
    if (bytes <= 0) return "0 B"
    val units = arrayOf("B", "KB", "MB", "GB", "TB")
    var size = bytes.toDouble()
    var unitIndex = 0
    while (size >= 1024 && unitIndex < units.size - 1) {
        size /= 1024
        unitIndex++
    }
    return String.format(Locale.US, "%.1f %s", size, units[unitIndex])
}
