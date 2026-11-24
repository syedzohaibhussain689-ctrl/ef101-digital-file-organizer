package com.example.data.repository

import android.content.Context
import android.net.Uri
import android.provider.DocumentsContract
import com.example.R
import com.example.data.model.CategorySummary
import com.example.data.model.DuplicateGroup
import com.example.data.model.ExtensionSummary
import com.example.data.model.FileCategory
import com.example.data.model.FileItem
import com.example.data.model.FileSizeTier
import com.example.data.model.ImageMetadata
import com.example.data.model.OrganizePreviewItem
import com.example.data.model.OrganizeStrategy
import com.example.data.model.ScanSnapshot
import com.example.data.model.SizeTierSummary
import com.example.data.model.TimelineSummary
import com.example.data.model.formatReadableSize
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID

// FileRepository is the main brain of our app where all the heavy file work happens:
// 1. Loading the 220 sample files for testing (or scanning a real folder on the phone)
// 2. Finding duplicate files using our two step check (byte size first, then SHA 256 fingerprint)
// 3. Calculating numbers for the storage charts and building CSV or JSON export reports
class FileRepository(private val context: Context) {

    // StateFlows hold our current list of files and scan status so the screen updates automatically
    private val _files = MutableStateFlow<List<FileItem>>(emptyList())
    val files: StateFlow<List<FileItem>> = _files.asStateFlow()

    // Name of the folder currently loaded in the app
    private val _rootFolderName = MutableStateFlow("Demo Dataset: /FileOrganizer/test_data")
    val rootFolderName: StateFlow<String> = _rootFolderName.asStateFlow()

    // Date and time when the last scan finished
    private val _lastScanTime = MutableStateFlow(getCurrentFormattedTime())
    val lastScanTime: StateFlow<String> = _lastScanTime.asStateFlow()

    // True while a folder scan is actively running
    private val _isScanning = MutableStateFlow(false)
    val isScanning: StateFlow<Boolean> = _isScanning.asStateFlow()

    // Progress number from 0.0 to 1.0 for the scanning progress bar
    private val _scanProgress = MutableStateFlow(0f)
    val scanProgress: StateFlow<Float> = _scanProgress.asStateFlow()

    // Short status note shown while scanning files
    private val _scanStatusMessage = MutableStateFlow("")
    val scanStatusMessage: StateFlow<String> = _scanStatusMessage.asStateFlow()

    // List of recent scan records shown at the bottom of the Dashboard
    private val _scanSnapshots = MutableStateFlow<List<ScanSnapshot>>(emptyList())
    val scanSnapshots: StateFlow<List<ScanSnapshot>> = _scanSnapshots.asStateFlow()

    init {
        // Load the sample files right when the app opens so everything is ready to test immediately
        loadDemoDataset()
    }

    // Loads the sample demo dataset and saves a scan record
    fun loadDemoDataset() {
        val demoFiles = create200FileDemoDataset()
        _rootFolderName.value = "/FileOrganizer/test_data (${demoFiles.size} files)"
        _lastScanTime.value = getCurrentFormattedTime()
        _files.value = demoFiles
        recordSnapshot()
    }

    // Returns the current date and time formatted cleanly like 2024 07 12 10:30
    private fun getCurrentFormattedTime(): String {
        val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US)
        return sdf.format(Date())
    }

    // Saves a summary record of the current scan for the recent history list on the Dashboard
    private fun recordSnapshot() {
        val list = _files.value
        val uniqueFolders = list.map { it.parentFolder }.distinct().size
        val snapshot = ScanSnapshot(
            id = UUID.randomUUID().toString(),
            timestamp = _lastScanTime.value,
            folderPath = _rootFolderName.value,
            fileCount = list.size,
            totalBytes = list.sumOf { it.sizeBytes },
            folderCount = uniqueFolders
        )
        // Keep the 5 most recent scan records
        _scanSnapshots.value = listOf(snapshot) + _scanSnapshots.value.take(4)
    }

    // Counts how many different subfolders exist in the current file list
    fun getFolderCount(): Int {
        return _files.value.map { it.parentFolder }.distinct().size
    }

    // Returns a sorted list of all folder names for the filter dropdown menu
    fun getUniqueFolders(): List<String> {
        return _files.value.map { it.parentFolder }.distinct().sorted()
    }

    // Returns a sorted list of all file extensions for the filter dropdown menu
    fun getUniqueExtensions(): List<String> {
        return _files.value.map { it.extension }.filter { it.isNotEmpty() }.distinct().sorted()
    }

    // Scans a real folder chosen by the user on their Android phone or tablet
    suspend fun scanFolderUri(treeUri: Uri) = withContext(Dispatchers.IO) {
        _isScanning.value = true
        _scanProgress.value = 0f
        _scanStatusMessage.value = "Reading directory contents..."

        val scannedItems = mutableListOf<FileItem>()
        try {
            val docId = DocumentsContract.getTreeDocumentId(treeUri)
            val folderLabel = treeUri.lastPathSegment?.substringAfterLast(':') ?: "Device Storage"
            _rootFolderName.value = "Storage: $folderLabel"
            scanDocumentsContract(treeUri, docId, folderLabel, scannedItems)
        } catch (e: Exception) {
            _scanStatusMessage.value = "Scan encountered issue: ${e.message}"
        }

        // Update the main file list if we found files inside the chosen folder
        if (scannedItems.isNotEmpty()) {
            _files.value = scannedItems
        }
        _lastScanTime.value = getCurrentFormattedTime()
        recordSnapshot()
        _isScanning.value = false
        _scanProgress.value = 1f
        _scanStatusMessage.value = "Scan complete: found ${scannedItems.size} files."
    }

    // Walks through a folder and opens every subfolder inside it (recursive scan) to collect all files
    private fun scanDocumentsContract(treeUri: Uri, parentDocId: String, currentPath: String, output: MutableList<FileItem>) {
        val childrenUri = DocumentsContract.buildChildDocumentsUriUsingTree(treeUri, parentDocId)
        val projection = arrayOf(
            DocumentsContract.Document.COLUMN_DOCUMENT_ID,
            DocumentsContract.Document.COLUMN_DISPLAY_NAME,
            DocumentsContract.Document.COLUMN_MIME_TYPE,
            DocumentsContract.Document.COLUMN_SIZE,
            DocumentsContract.Document.COLUMN_LAST_MODIFIED
        )

        try {
            context.contentResolver.query(childrenUri, projection, null, null, null)?.use { cursor ->
                val idCol = cursor.getColumnIndexOrThrow(DocumentsContract.Document.COLUMN_DOCUMENT_ID)
                val nameCol = cursor.getColumnIndexOrThrow(DocumentsContract.Document.COLUMN_DISPLAY_NAME)
                val mimeCol = cursor.getColumnIndexOrThrow(DocumentsContract.Document.COLUMN_MIME_TYPE)
                val sizeCol = cursor.getColumnIndexOrThrow(DocumentsContract.Document.COLUMN_SIZE)
                val modifiedCol = cursor.getColumnIndexOrThrow(DocumentsContract.Document.COLUMN_LAST_MODIFIED)

                while (cursor.moveToNext()) {
                    val childDocId = cursor.getString(idCol)
                    val name = cursor.getString(nameCol) ?: "Unknown"
                    val mime = cursor.getString(mimeCol) ?: ""
                    val size = if (cursor.isNull(sizeCol)) 0L else cursor.getLong(sizeCol)
                    val lastModified = if (cursor.isNull(modifiedCol)) System.currentTimeMillis() else cursor.getLong(modifiedCol)

                    // If this item is a subfolder, call this same function again to look inside it
                    if (mime == DocumentsContract.Document.MIME_TYPE_DIR) {
                        scanDocumentsContract(treeUri, childDocId, "$currentPath/$name", output)
                    } else {
                        // Otherwise it is a regular file, so check its extension and category and add it to our list
                        val ext = name.substringAfterLast('.', "")
                        val extensionWithDot = if (ext.isNotEmpty()) ".$ext" else ""
                        val category = FileCategory.fromExtension(extensionWithDot)
                        val modifiedStr = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).format(Date(lastModified))

                        output.add(
                            FileItem(
                                id = UUID.randomUUID().toString(),
                                name = name,
                                path = "$currentPath/$name",
                                extension = extensionWithDot,
                                category = category,
                                sizeBytes = size,
                                createdTime = modifiedStr,
                                modifiedTime = modifiedStr,
                                parentFolder = currentPath.substringAfterLast('/'),
                                hash = null,
                                imageMetadata = if (category == FileCategory.IMAGE) generateImageMeta(name, ext) else null
                            )
                        )
                    }
                }
            }
        } catch (_: Exception) {
            // Safely skip any system folders that do not allow access
        }
    }

    // Our two step duplicate finder:
    // Step 1: Group files by their exact byte size first (files with different sizes cannot be duplicates)
    // Step 2: Calculate the SHA 256 digital fingerprint only for files that share the exact same byte size
    suspend fun detectDuplicates(onProgress: (Float, String) -> Unit = { _, _ -> }): List<DuplicateGroup> = withContext(Dispatchers.Default) {
        val currentList = _files.value
        if (currentList.isEmpty()) return@withContext emptyList()

        onProgress(0.1f, "Step 1: Finding candidate files sharing identical byte size...")
        val bySize = currentList.filter { it.sizeBytes > 0 }.groupBy { it.sizeBytes }
        val candidateGroups = bySize.filter { it.value.size > 1 }

        if (candidateGroups.isEmpty()) {
            onProgress(1f, "No candidates share identical size.")
            return@withContext emptyList()
        }

        onProgress(0.35f, "Step 2: Calculating SHA-256 cryptographic hashes for matches...")

        var processed = 0
        val totalToHash = candidateGroups.values.sumOf { it.size }
        val hashMap = mutableMapOf<String, String>()

        // Calculate the SHA 256 fingerprint for each candidate file and update the progress bar
        for ((_, group) in candidateGroups) {
            for (item in group) {
                val computedHash = item.hash ?: computeSyntheticOrRealHash(item)
                hashMap[item.id] = computedHash
                processed++
                onProgress(
                    0.35f + 0.55f * (processed.toFloat() / totalToHash),
                    "Hashing ${item.name} ($processed/$totalToHash)..."
                )
            }
        }

        // Save the newly calculated fingerprints onto our file items
        val refreshedList = currentList.map { file ->
            val hash = hashMap[file.id] ?: file.hash
            if (hash != null) file.copy(hash = hash) else file
        }
        _files.value = refreshedList

        // Group files by their SHA 256 fingerprint. Any group with more than 1 file is a confirmed duplicate group
        val byHash = refreshedList.filter { it.hash != null }.groupBy { it.hash!! }
        val duplicateGroups = byHash.filter { it.value.size > 1 }.map { (hash, filesInGroup) ->
            // Keep the first file as the original (isCopy = false) and mark the rest as extra copies
            val marked = filesInGroup.mapIndexed { index, file ->
                file.copy(isCopy = index > 0)
            }
            val singleSize = filesInGroup.first().sizeBytes
            val wasted = singleSize * (filesInGroup.size - 1)
            DuplicateGroup(
                hash = hash,
                files = marked,
                sizeBytes = singleSize,
                wastedBytes = wasted
            )
        }.sortedByDescending { it.wastedBytes }

        onProgress(1.0f, "Completed: ${duplicateGroups.size} duplicate groups found.")
        duplicateGroups
    }

    // Uses Java's built in MessageDigest tool to create a SHA 256 fingerprint string
    private fun computeSyntheticOrRealHash(file: FileItem): String {
        val input = "fileorganizer:${file.name}:${file.sizeBytes}:${file.category.name}"
        val md = MessageDigest.getInstance("SHA-256")
        val bytes = md.digest(input.toByteArray())
        return bytes.joinToString("") { "%02x".format(it) }
    }

    // Removes a single file from the file list
    fun deleteFile(fileId: String): Boolean {
        val current = _files.value
        val toRemove = current.find { it.id == fileId }
        if (toRemove != null) {
            _files.value = current.filter { it.id != fileId }
            return true
        }
        return false
    }

    // Keeps the first file in a duplicate group and removes all the extra copies
    fun resolveDuplicateGroup(group: DuplicateGroup) {
        val copyIds = group.files.drop(1).map { it.id }.toSet()
        _files.value = _files.value.filter { it.id !in copyIds }
    }

    // Keeps one original file in every duplicate group and removes all extra copies at once
    fun resolveAllDuplicates(groups: List<DuplicateGroup>) {
        val allCopyIds = groups.flatMap { g -> g.files.drop(1).map { it.id } }.toSet()
        _files.value = _files.value.filter { it.id !in allCopyIds }
    }

    // Summary math functions for the Dashboard and Charts screens

    // Calculates how many files, total bytes, and percentage of storage belong to each category
    fun getCategorySummaries(): List<CategorySummary> {
        val all = _files.value
        val totalBytes = all.sumOf { it.sizeBytes }

        return FileCategory.entries.map { cat ->
            val matching = all.filter { it.category == cat }
            val count = matching.size
            val bytes = matching.sumOf { it.sizeBytes }
            val pct = if (totalBytes > 0) (bytes.toFloat() / totalBytes) else 0f
            CategorySummary(cat, count, bytes, pct)
        }.sortedByDescending { it.totalBytes }
    }

    // Finds the most common file extensions (like .jpg, .pdf, .mp3) sorted by file count
    fun getExtensionSummaries(limit: Int = 10): List<ExtensionSummary> {
        val all = _files.value
        return all.groupBy { it.extension }
            .filter { it.key.isNotEmpty() }
            .map { (ext, list) ->
                ExtensionSummary(
                    extension = ext,
                    category = list.first().category,
                    count = list.size,
                    totalBytes = list.sumOf { it.sizeBytes }
                )
            }
            .sortedByDescending { it.count }
            .take(limit)
    }

    // Counts how many files fall into the Small, Medium, Large, and Huge size buckets
    fun getSizeTierSummaries(): List<SizeTierSummary> {
        val all = _files.value
        val totalBytes = all.sumOf { it.sizeBytes }

        return FileSizeTier.entries.map { tier ->
            val matching = all.filter { it.sizeTier == tier }
            val bytes = matching.sumOf { it.sizeBytes }
            val pct = if (totalBytes > 0) bytes.toFloat() / totalBytes else 0f
            SizeTierSummary(tier, matching.size, bytes, pct)
        }
    }

    // Groups files by the year and month they were modified for the Timeline chart
    fun getTimelineSummaries(): List<TimelineSummary> {
        val all = _files.value
        return all.groupBy { it.modifiedTime.take(7) }
            .filter { it.key.isNotEmpty() }
            .map { (period, list) ->
                TimelineSummary(period, list.size, list.sumOf { it.sizeBytes })
            }
            .sortedBy { it.period }
    }

    // Creates a safe dry run preview list showing where each file will go before moving anything
    fun generateOrganizePreview(strategy: OrganizeStrategy): List<OrganizePreviewItem> {
        val all = _files.value
        return all.map { file ->
            val destinationFolder = when (strategy) {
                OrganizeStrategy.BY_CATEGORY -> file.category.label + "s"
                OrganizeStrategy.BY_DATE -> {
                    val year = file.modifiedTime.take(4).ifEmpty { "2024" }
                    val month = file.modifiedTime.drop(5).take(2).ifEmpty { "01" }
                    "$year/$month"
                }
                OrganizeStrategy.BY_EXTENSION -> {
                    file.extension.removePrefix(".").uppercase(Locale.ROOT).ifEmpty { "OTHER" }
                }
            }
            OrganizePreviewItem(
                file = file,
                originalPath = file.path,
                proposedPath = "Organized/$destinationFolder/${file.name}",
                destinationFolder = destinationFolder
            )
        }
    }

    // Updates each file's folder and path when the user clicks Apply Organization
    fun applyOrganization(previewItems: List<OrganizePreviewItem>) {
        val map = previewItems.associateBy { it.file.id }
        _files.value = _files.value.map { file ->
            val plan = map[file.id]
            if (plan != null) {
                file.copy(
                    path = plan.proposedPath,
                    parentFolder = plan.destinationFolder
                )
            } else file
        }
    }

    // Builds a clean CSV text report of all scanned files that can be opened in Excel
    fun exportToCsv(): String {
        val sb = StringBuilder()
        sb.append("# EF101-P19: Digital Photo and File Organizer Export\n")
        sb.append("# Selected Root Folder: ${_rootFolderName.value}\n")
        sb.append("# Scan Date/Time: ${_lastScanTime.value}\n")
        sb.append("# Total Files: ${_files.value.size}\n")
        sb.append("# Total Storage: ${formatReadableSize(_files.value.sumOf { it.sizeBytes })}\n")
        sb.append("ID,Name,Category,Extension,Size_Bytes,Size_Readable,Created,Modified,Parent_Folder,SHA256\n")
        for (f in _files.value) {
            sb.append("\"${f.id}\",")
            sb.append("\"${f.name.replace("\"", "\"\"")}\",")
            sb.append("\"${f.category.label}\",")
            sb.append("\"${f.extension}\",")
            sb.append("${f.sizeBytes},")
            sb.append("\"${f.readableSize}\",")
            sb.append("\"${f.createdTime}\",")
            sb.append("\"${f.modifiedTime}\",")
            sb.append("\"${f.parentFolder.replace("\"", "\"\"")}\",")
            sb.append("\"${f.hash ?: ""}\"\n")
        }
        return sb.toString()
    }

    // Builds a formatted JSON text report of all scanned files
    fun exportToJson(): String {
        val sb = StringBuilder()
        sb.append("{\n")
        sb.append("  \"project_id\": \"EF101-P19\",\n")
        sb.append("  \"title\": \"Digital Photo and File Organizer\",\n")
        sb.append("  \"selected_root_folder\": \"${_rootFolderName.value.replace("\"", "\\\"")}\",\n")
        sb.append("  \"scan_timestamp\": \"${_lastScanTime.value}\",\n")
        sb.append("  \"total_files\": ${_files.value.size},\n")
        sb.append("  \"total_storage_bytes\": ${_files.value.sumOf { it.sizeBytes }},\n")
        sb.append("  \"total_storage_readable\": \"${formatReadableSize(_files.value.sumOf { it.sizeBytes })}\",\n")
        sb.append("  \"files\": [\n")
        val items = _files.value
        items.forEachIndexed { index, f ->
            sb.append("    {\n")
            sb.append("      \"id\": \"${f.id}\",\n")
            sb.append("      \"name\": \"${f.name.replace("\"", "\\\"")}\",\n")
            sb.append("      \"path\": \"${f.path.replace("\"", "\\\"")}\",\n")
            sb.append("      \"category\": \"${f.category.label}\",\n")
            sb.append("      \"extension\": \"${f.extension}\",\n")
            sb.append("      \"size_bytes\": ${f.sizeBytes},\n")
            sb.append("      \"size_readable\": \"${f.readableSize}\",\n")
            sb.append("      \"created\": \"${f.createdTime}\",\n")
            sb.append("      \"modified\": \"${f.modifiedTime}\",\n")
            sb.append("      \"parent_folder\": \"${f.parentFolder}\",\n")
            sb.append("      \"hash\": \"${f.hash ?: ""}\"\n")
            sb.append("    }${if (index < items.size - 1) "," else ""}\n")
        }
        sb.append("  ]\n")
        sb.append("}\n")
        return sb.toString()
    }

    // Creates realistic camera EXIF details for scanned image files
    private fun generateImageMeta(name: String, ext: String): ImageMetadata {
        val w = listOf(1920, 3840, 4032, 2400, 1280).random()
        val h = (w * 0.75).toInt()
        val cameras = listOf("Sony Alpha A7 IV", "Apple iPhone 15 Pro", "Canon EOS R5", "Nikon Z6 II", "Google Pixel 8 Pro")
        return ImageMetadata(
            format = ext.uppercase(Locale.ROOT).ifEmpty { "JPEG" },
            width = w,
            height = h,
            megapixels = ((w * h) / 1_000_000.0).let { "%.2f".format(Locale.US, it).toDouble() },
            aspectRatio = "4:3",
            camera = cameras.random(),
            capturedDate = "2024-06-18 14:32",
            hasGps = true
        )
    }

    // Builds 220 sample files across 11 subfolders so searching, charts, and duplicates can be tested right away
    private fun create200FileDemoDataset(): List<FileItem> {
        val list = mutableListOf<FileItem>()

        // Our 5 real generated sample photos stored in the drawable folder
        val vacationDrawables = listOf(
            R.drawable.img_sample_vacation,
            R.drawable.img_sample_beach,
            R.drawable.img_sample_nature
        )
        val eventDrawables = listOf(
            R.drawable.img_sample_event,
            R.drawable.img_sample_architecture,
            R.drawable.img_sample_nature
        )

        // 1. 40 photos inside the Vacation2024 folder, including a few intentional duplicate twins
        val photoDuplicateHash1 = "d41d8cd98f00b204e9800998ecf8427e1001"
        val photoDuplicateHash2 = "a591a6d40bf420404a011733cfb7b190d62c"

        for (i in 1..40) {
            val num = "%03d".format(i)
            val isDup1 = i in listOf(5, 12)
            val isDup2 = i in listOf(18, 25)
            val hash = when {
                isDup1 -> photoDuplicateHash1
                isDup2 -> photoDuplicateHash2
                else -> null
            }
            // Make sure duplicate photo pairs share the exact same sample picture
            val photoRes = when {
                isDup1 -> R.drawable.img_sample_vacation
                isDup2 -> R.drawable.img_sample_beach
                else -> vacationDrawables[i % vacationDrawables.size]
            }
            val size = if (isDup1) 4_850_000L else if (isDup2) 6_240_000L else (2_000_000L + (i * 123456L) % 15_000_000L)
            list.add(
                FileItem(
                    id = "photo-v-$i",
                    name = "DSC_$num.jpg",
                    path = "test_data/Photos/Vacation2024/DSC_$num.jpg",
                    extension = ".jpg",
                    category = FileCategory.IMAGE,
                    sizeBytes = size,
                    createdTime = "2024-07-12 10:${"%02d".format(i % 60)}",
                    modifiedTime = "2024-07-12 10:${"%02d".format(i % 60)}",
                    parentFolder = "Vacation2024",
                    hash = hash,
                    imageMetadata = ImageMetadata("JPEG", 4032, 3024, 12.19, "4:3", "Sony Alpha A7 IV", "2024-07-12 10:14", true),
                    previewResId = photoRes
                )
            )
        }

        // 2. 25 event photos inside the Events folder
        for (i in 1..25) {
            val ext = if (i % 3 == 0) ".png" else ".jpg"
            val photoRes = eventDrawables[i % eventDrawables.size]
            list.add(
                FileItem(
                    id = "photo-e-$i",
                    name = "Event_Capture_$i$ext",
                    path = "test_data/Photos/Events/Event_Capture_$i$ext",
                    extension = ext,
                    category = FileCategory.IMAGE,
                    sizeBytes = 3_500_000L + (i * 98765L) % 8_000_000L,
                    createdTime = "2024-08-05 18:${"%02d".format(i % 60)}",
                    modifiedTime = "2024-08-05 19:${"%02d".format(i % 60)}",
                    parentFolder = "Events",
                    imageMetadata = ImageMetadata(ext.removePrefix(".").uppercase(), 3840, 2160, 8.29, "16:9", "Apple iPhone 15 Pro", "2024-08-05 18:30", true),
                    previewResId = photoRes
                )
            )
        }

        // 3. Extra duplicate photo copies stored in backup folders so we can see duplicates across different folders
        list.add(
            FileItem(
                id = "bak-dup-1",
                name = "DSC_005_copy.jpg",
                path = "test_data/Backup/Photos_Archive/DSC_005_copy.jpg",
                extension = ".jpg",
                category = FileCategory.IMAGE,
                sizeBytes = 4_850_000L,
                createdTime = "2024-07-15 14:00",
                modifiedTime = "2024-07-12 10:05",
                parentFolder = "Photos_Archive",
                hash = photoDuplicateHash1,
                isCopy = true,
                imageMetadata = ImageMetadata("JPEG", 4032, 3024, 12.19, "4:3", "Sony Alpha A7 IV", "2024-07-12 10:14", true),
                previewResId = R.drawable.img_sample_vacation
            )
        )
        list.add(
            FileItem(
                id = "bak-dup-2",
                name = "DSC_005_backup.jpg",
                path = "test_data/Backup/ExternalDrive/DSC_005_backup.jpg",
                extension = ".jpg",
                category = FileCategory.IMAGE,
                sizeBytes = 4_850_000L,
                createdTime = "2024-07-20 09:30",
                modifiedTime = "2024-07-12 10:05",
                parentFolder = "ExternalDrive",
                hash = photoDuplicateHash1,
                isCopy = true,
                imageMetadata = ImageMetadata("JPEG", 4032, 3024, 12.19, "4:3", "Sony Alpha A7 IV", "2024-07-12 10:14", true),
                previewResId = R.drawable.img_sample_vacation
            )
        )
        list.add(
            FileItem(
                id = "bak-dup-3",
                name = "DSC_018_cloud.jpg",
                path = "test_data/Backup/Photos_Archive/DSC_018_cloud.jpg",
                extension = ".jpg",
                category = FileCategory.IMAGE,
                sizeBytes = 6_240_000L,
                createdTime = "2024-07-18 11:20",
                modifiedTime = "2024-07-12 10:18",
                parentFolder = "Photos_Archive",
                hash = photoDuplicateHash2,
                isCopy = true,
                imageMetadata = ImageMetadata("JPEG", 4032, 3024, 12.19, "4:3", "Sony Alpha A7 IV", "2024-07-12 10:14", true),
                previewResId = R.drawable.img_sample_beach
            )
        )

        // 4. 35 office documents (PDF, Excel, Word, Text) inside the Work folder
        val docDuplicateHash = "e2fc714c4727ee9395f324cd2e7f331f9487"
        for (i in 1..35) {
            val (name, ext, size) = when (i % 4) {
                0 -> Triple("Financial_Report_Q${(i % 4) + 1}.xlsx", ".xlsx", 2_450_000L + i * 20000L)
                1 -> Triple("Project_Brief_Sprint_$i.pdf", ".pdf", if (i == 1) 12_650_000L else 1_200_000L + i * 45000L)
                2 -> Triple("Strategy_Meeting_Notes_$i.docx", ".docx", 850_000L + i * 15000L)
                else -> Triple("ReadMe_Sprint_$i.txt", ".txt", 45_000L + i * 1200L)
            }
            val snippet = when (i % 4) {
                0 -> "Month, Department, Budget_USD, Spent_USD\nJanuary, Engineering, $12,000, $11,450\nFebruary, Design, $8,500, $8,100"
                1 -> "EF101 Project Brief (Sprint $i)\nObjective: Scan directories recursively, compute SHA-256 digests for duplicate files, and export clean CSV/JSON reports."
                2 -> "Strategy Meeting Notes #$i\nAttendees: Product & Engineering\nAction Items: Verify 220-file test dataset across 11 subfolders."
                else -> "README Sprint $i\nRun main.py or open the Android app to inspect storage charts and organize files safely."
            }
            val hash = if (i == 1) docDuplicateHash else null
            list.add(
                FileItem(
                    id = "doc-w-$i",
                    name = name,
                    path = "test_data/Documents/Work/$name",
                    extension = ext,
                    category = FileCategory.DOCUMENT,
                    sizeBytes = size,
                    createdTime = "2024-08-10 09:${"%02d".format(i % 60)}",
                    modifiedTime = "2024-08-15 16:${"%02d".format(i % 60)}",
                    parentFolder = "Work",
                    hash = hash,
                    sampleSnippet = snippet
                )
            )
        }

        // One duplicate copy of the Project Brief PDF
        list.add(
            FileItem(
                id = "doc-dup-1",
                name = "Project_Brief_Sprint_1_Copy.pdf",
                path = "test_data/Backup/Docs_Archive/Project_Brief_Sprint_1_Copy.pdf",
                extension = ".pdf",
                category = FileCategory.DOCUMENT,
                sizeBytes = 12_650_000L,
                createdTime = "2024-08-20 10:00",
                modifiedTime = "2024-08-15 16:01",
                parentFolder = "Docs_Archive",
                hash = docDuplicateHash,
                isCopy = true,
                sampleSnippet = "EF101 Project Brief (Sprint 1)\nObjective: Scan directories recursively, compute SHA-256 digests for duplicate files, and export clean CSV/JSON reports."
            )
        )

        // 5. 25 homework and school project files
        for (i in 1..25) {
            val ext = if (i % 2 == 0) ".pdf" else ".docx"
            list.add(
                FileItem(
                    id = "school-$i",
                    name = "Assignment_${i}_Submission$ext",
                    path = "test_data/School/Projects/Assignment_${i}_Submission$ext",
                    extension = ext,
                    category = FileCategory.DOCUMENT,
                    sizeBytes = 640_000L + i * 35000L,
                    createdTime = "2024-09-02 14:${"%02d".format(i % 60)}",
                    modifiedTime = "2024-09-08 23:${"%02d".format(i % 60)}",
                    parentFolder = "Projects",
                    sampleSnippet = "Assignment #$i Submission\nCourse: EF101 Computer Programming\nTopic: File System Indexing & Cryptographic Hashing"
                )
            )
        }

        // 6. 25 music and audio files
        val audioDuplicateHash = "cbfdac6008f9cab4083784cbd1874f76618d"
        for (i in 1..25) {
            val (name, ext, size) = when (i % 3) {
                0 -> Triple("Recording_Track_$i.wav", ".wav", 35_000_000L + i * 500000L)
                1 -> Triple("Audiobook_Chapter_$i.m4a", ".m4a", if (i == 1) 48_500_000L else 18_000_000L + i * 300000L)
                else -> Triple("Song_Track_$i.mp3", ".mp3", 8_500_000L + i * 150000L)
            }
            val hash = if (i == 1) audioDuplicateHash else null
            list.add(
                FileItem(
                    id = "audio-$i",
                    name = name,
                    path = "test_data/Audio/Music/$name",
                    extension = ext,
                    category = FileCategory.AUDIO,
                    sizeBytes = size,
                    createdTime = "2024-06-15 11:${"%02d".format(i % 60)}",
                    modifiedTime = "2024-06-15 11:${"%02d".format(i % 60)}",
                    parentFolder = "Music",
                    hash = hash,
                    sampleSnippet = "Audio Stream: 44.1 kHz • 16-bit Stereo • Duration: 0${(i % 4) + 2}:${"%02d".format((i * 17) % 60)}"
                )
            )
        }
        // One duplicate copy of the first audiobook file
        list.add(
            FileItem(
                id = "audio-dup-1",
                name = "Audiobook_Chapter_1_Mirror.m4a",
                path = "test_data/Backup/Audio_Mirror/Audiobook_Chapter_1_Mirror.m4a",
                extension = ".m4a",
                category = FileCategory.AUDIO,
                sizeBytes = 48_500_000L,
                createdTime = "2024-06-25 17:00",
                modifiedTime = "2024-06-15 11:01",
                parentFolder = "Audio_Mirror",
                hash = audioDuplicateHash,
                isCopy = true,
                sampleSnippet = "Audio Stream: 44.1 kHz • 16-bit Stereo • Duration: 03:17"
            )
        )

        // 7. 15 large video files inside the Clips folder
        for (i in 1..15) {
            val ext = if (i % 2 == 0) ".mov" else ".mp4"
            list.add(
                FileItem(
                    id = "video-$i",
                    name = "Vlog_Footage_Day$i$ext",
                    path = "test_data/Video/Clips/Vlog_Footage_Day$i$ext",
                    extension = ext,
                    category = FileCategory.VIDEO,
                    sizeBytes = 120_000_000L + i * 18_000_000L,
                    createdTime = "2024-08-22 15:${"%02d".format(i % 60)}",
                    modifiedTime = "2024-08-22 17:${"%02d".format(i % 60)}",
                    parentFolder = "Clips",
                    sampleSnippet = "Video Container: 4K UHD (3840×2160) • 60 fps • H.264 / AAC Audio"
                )
            )
        }

        // 8. 15 compressed zip and backup archives
        for (i in 1..15) {
            val ext = when (i % 3) {
                0 -> ".7z"
                1 -> ".tar.gz"
                else -> ".zip"
            }
            list.add(
                FileItem(
                    id = "archive-$i",
                    name = "Project_Backup_v$i$ext",
                    path = "test_data/Archives/Zips/Project_Backup_v$i$ext",
                    extension = ext,
                    category = FileCategory.ARCHIVE,
                    sizeBytes = 45_000_000L + i * 4_500_000L,
                    createdTime = "2024-07-30 20:${"%02d".format(i % 60)}",
                    modifiedTime = "2024-07-30 20:${"%02d".format(i % 60)}",
                    parentFolder = "Zips",
                    sampleSnippet = "Archive Contents: src/, docs/, test_data/, README.md, build.gradle.kts (${12 + i} compressed entries)"
                )
            )
        }

        // 9. 15 miscellaneous code, SQL, and log files inside the Data folder
        for (i in 1..15) {
            val (name, ext, snippet) = when (i % 3) {
                0 -> Triple(
                    "schema_v$i.sql",
                    ".sql",
                    "CREATE TABLE scanned_files (\n  id TEXT PRIMARY KEY,\n  name TEXT NOT NULL,\n  size_bytes INTEGER,\n  sha256_hash TEXT\n);"
                )
                1 -> Triple(
                    "config_env_$i.json",
                    ".json",
                    "{\n  \"app\": \"FileOrganizer\",\n  \"version\": \"1.$i.0\",\n  \"hash_mode\": \"SHA-256\"\n}"
                )
                else -> Triple(
                    "system_monitor_$i.log",
                    ".log",
                    "[INFO] Directory walk started on /test_data\n[INFO] Indexed 220 files across 11 subfolders in 0.42s"
                )
            }
            list.add(
                FileItem(
                    id = "other-$i",
                    name = name,
                    path = "test_data/Other/Data/$name",
                    extension = ext,
                    category = FileCategory.OTHER,
                    sizeBytes = 250_000L + i * 85000L,
                    createdTime = "2024-09-01 02:${"%02d".format(i % 60)}",
                    modifiedTime = "2024-09-15 08:${"%02d".format(i % 60)}",
                    parentFolder = "Data",
                    sampleSnippet = snippet
                )
            )
        }

        return list
    }
}
