package com.example.ui.viewmodel

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.data.model.CategorySummary
import com.example.data.model.DuplicateGroup
import com.example.data.model.ExtensionSummary
import com.example.data.model.FileCategory
import com.example.data.model.FileItem
import com.example.data.model.OrganizePreviewItem
import com.example.data.model.OrganizeStrategy
import com.example.data.model.SizeTierSummary
import com.example.data.model.TimelineSummary
import com.example.data.repository.FileRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

// These are the 6 main tabs in our app that show up in the bottom bar and side menu
enum class AppTab(val title: String, val iconName: String) {
    DASHBOARD("Dashboard", "grid"),
    FILES("All Files", "list"),
    DUPLICATES("Duplicates", "copy"),
    CHARTS("Charts", "chart"),
    ORGANIZE("Organize", "folder"),
    EXPORT("Export", "file-down")
}

// These are the 4 ways a user can sort the list on the All Files screen
enum class SortField {
    NAME, SIZE, DATE, EXTENSION
}

// This ViewModel is like the brain of the app that connects our screen UI to the FileRepository.
// The best part about using a ViewModel is that if you rotate your phone, your data and filters stay safe.
class FileOrganizerViewModel(application: Application) : AndroidViewModel(application) {

    // We create our repository object here because it holds all the real file data
    val repository = FileRepository(application.applicationContext)

    // We pass the live data streams from the repository straight to our screens
    val allFiles = repository.files
    val rootFolderName = repository.rootFolderName
    val lastScanTime = repository.lastScanTime
    val isScanning = repository.isScanning
    val scanProgress = repository.scanProgress
    val scanStatusMessage = repository.scanStatusMessage
    val scanSnapshots = repository.scanSnapshots

    // This keeps track of which tab the user is looking at right now, starting with the Dashboard
    private val _activeTab = MutableStateFlow(AppTab.DASHBOARD)
    val activeTab: StateFlow<AppTab> = _activeTab.asStateFlow()

    // These variables remember what the user typed or picked in the search and filter boxes
    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    private val _selectedCategory = MutableStateFlow<FileCategory?>(null)
    val selectedCategory: StateFlow<FileCategory?> = _selectedCategory.asStateFlow()

    private val _sortField = MutableStateFlow(SortField.NAME)
    val sortField: StateFlow<SortField> = _sortField.asStateFlow()

    private val _sortAscending = MutableStateFlow(true)
    val sortAscending: StateFlow<Boolean> = _sortAscending.asStateFlow()

    // This remembers if the user wants a normal list or a 2 column grid
    private val _isGridView = MutableStateFlow(false)
    val isGridView: StateFlow<Boolean> = _isGridView.asStateFlow()

    // When the user taps the Filters button, this opens or closes the extra filter box
    private val _isMoreFiltersOpen = MutableStateFlow(false)
    val isMoreFiltersOpen: StateFlow<Boolean> = _isMoreFiltersOpen.asStateFlow()

    private val _selectedFolder = MutableStateFlow<String?>(null)
    val selectedFolder: StateFlow<String?> = _selectedFolder.asStateFlow()

    private val _selectedExtension = MutableStateFlow<String?>(null)
    val selectedExtension: StateFlow<String?> = _selectedExtension.asStateFlow()

    private val _minSizeMb = MutableStateFlow("")
    val minSizeMb: StateFlow<String> = _minSizeMb.asStateFlow()

    private val _maxSizeMb = MutableStateFlow("")
    val maxSizeMb: StateFlow<String> = _maxSizeMb.asStateFlow()

    private val _dateFrom = MutableStateFlow("")
    val dateFrom: StateFlow<String> = _dateFrom.asStateFlow()

    private val _dateTo = MutableStateFlow("")
    val dateTo: StateFlow<String> = _dateTo.asStateFlow()

    // These variables hold the duplicate file groups and the progress bar status while scanning
    private val _duplicateGroups = MutableStateFlow<List<DuplicateGroup>>(emptyList())
    val duplicateGroups: StateFlow<List<DuplicateGroup>> = _duplicateGroups.asStateFlow()

    private val _isAnalyzingDuplicates = MutableStateFlow(false)
    val isAnalyzingDuplicates: StateFlow<Boolean> = _isAnalyzingDuplicates.asStateFlow()

    private val _duplicateProgress = MutableStateFlow(0f)
    val duplicateProgress: StateFlow<Float> = _duplicateProgress.asStateFlow()

    private val _duplicateStatusText = MutableStateFlow("")
    val duplicateStatusText: StateFlow<String> = _duplicateStatusText.asStateFlow()

    // When the user taps on any file, we store it here so the details popup knows what to show
    private val _selectedFileForDetails = MutableStateFlow<FileItem?>(null)
    val selectedFileForDetails: StateFlow<FileItem?> = _selectedFileForDetails.asStateFlow()

    // This stores the chosen organization rule and the preview list showing old and new folders
    private val _organizeStrategy = MutableStateFlow(OrganizeStrategy.BY_CATEGORY)
    val organizeStrategy: StateFlow<OrganizeStrategy> = _organizeStrategy.asStateFlow()

    private val _organizePreview = MutableStateFlow<List<OrganizePreviewItem>>(emptyList())
    val organizePreview: StateFlow<List<OrganizePreviewItem>> = _organizePreview.asStateFlow()

    // This holds short popup messages that appear at the bottom of the screen
    private val _toastMessage = MutableStateFlow<String?>(null)
    val toastMessage: StateFlow<String?> = _toastMessage.asStateFlow()

    init {
        // Right when the app starts, build the organize preview and look for duplicates in the demo files
        refreshOrganizePreview()
        runDuplicateAnalysis()
    }

    // Whenever any filter or sort option changes, combine automatically builds a fresh list of files
    val filteredFiles: StateFlow<List<FileItem>> = combine(
        allFiles,
        searchQuery,
        selectedCategory,
        selectedFolder,
        selectedExtension,
        minSizeMb,
        maxSizeMb,
        dateFrom,
        dateTo,
        sortField,
        sortAscending
    ) { _ ->
        filterAndSortFiles()
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // This function checks every filter one by one and then sorts the final list
    private fun filterAndSortFiles(): List<FileItem> {
        var list = allFiles.value

        // Step 1: If the user typed something in the search box, check the file name, path, extension, and folder
        val query = _searchQuery.value.trim().lowercase()
        if (query.isNotEmpty()) {
            list = list.filter {
                it.name.lowercase().contains(query) ||
                it.path.lowercase().contains(query) ||
                it.extension.lowercase().contains(query) ||
                it.parentFolder.lowercase().contains(query)
            }
        }

        // Step 2: If a category like Image or Audio is picked, keep only files from that category
        val category = _selectedCategory.value
        if (category != null) {
            list = list.filter { it.category == category }
        }

        // Step 3: If a specific subfolder is chosen, hide files from other folders
        val folder = _selectedFolder.value
        if (!folder.isNullOrEmpty() && folder != "All folders") {
            list = list.filter { it.parentFolder == folder }
        }

        // Step 4: If a file extension like .pdf is chosen, only show matching files
        val ext = _selectedExtension.value
        if (!ext.isNullOrEmpty() && ext != "All extensions") {
            list = list.filter { it.extension.equals(ext, ignoreCase = true) }
        }

        // Step 5: Turn the minimum MB number into bytes and hide anything smaller
        val minBytes = _minSizeMb.value.toDoubleOrNull()?.let { (it * 1024 * 1024).toLong() }
        if (minBytes != null) {
            list = list.filter { it.sizeBytes >= minBytes }
        }

        // Step 6: Turn the maximum MB number into bytes and hide anything bigger
        val maxBytes = _maxSizeMb.value.toDoubleOrNull()?.let { (it * 1024 * 1024).toLong() }
        if (maxBytes != null) {
            list = list.filter { it.sizeBytes <= maxBytes }
        }

        // Step 7: Check if the file date is on or after the start date
        val fromDate = _dateFrom.value.trim()
        if (fromDate.isNotEmpty()) {
            list = list.filter { it.modifiedTime.take(10) >= fromDate }
        }

        val toDate = _dateTo.value.trim()
        if (toDate.isNotEmpty()) {
            list = list.filter { it.modifiedTime.take(10) <= toDate }
        }

        // Step 8: Sort the remaining files by whichever button the user picked
        val sorted = when (_sortField.value) {
            SortField.NAME -> list.sortedWith(compareBy(String.CASE_INSENSITIVE_ORDER) { it.name })
            SortField.SIZE -> list.sortedBy { it.sizeBytes }
            SortField.DATE -> list.sortedBy { it.modifiedTime }
            SortField.EXTENSION -> list.sortedWith(compareBy(String.CASE_INSENSITIVE_ORDER) { it.extension })
        }

        // If ascending is true, return the list in normal order, otherwise flip it backwards
        return if (_sortAscending.value) sorted else sorted.reversed()
    }

    // Below are simple helper functions that run when the user taps buttons on the screen

    fun setActiveTab(tab: AppTab) {
        _activeTab.value = tab
    }

    fun setSearchQuery(query: String) {
        _searchQuery.value = query
    }

    fun selectCategory(cat: FileCategory?) {
        _selectedCategory.value = cat
    }

    fun setSortField(field: SortField) {
        // If the user taps the same sort button again, just flip the arrow up or down
        if (_sortField.value == field) {
            _sortAscending.value = !_sortAscending.value
        } else {
            _sortField.value = field
            _sortAscending.value = true
        }
    }

    fun toggleViewMode() {
        _isGridView.value = !_isGridView.value
    }

    fun toggleMoreFilters() {
        _isMoreFiltersOpen.value = !_isMoreFiltersOpen.value
    }

    fun setFolderFilter(folder: String?) {
        _selectedFolder.value = folder
    }

    fun setExtensionFilter(ext: String?) {
        _selectedExtension.value = ext
    }

    fun setMinSizeMb(mb: String) {
        _minSizeMb.value = mb
    }

    fun setMaxSizeMb(mb: String) {
        _maxSizeMb.value = mb
    }

    fun setDateFrom(date: String) {
        _dateFrom.value = date
    }

    fun setDateTo(date: String) {
        _dateTo.value = date
    }

    // Tapping the Clear button resets all search and filter boxes back to normal
    fun clearAllFilters() {
        _searchQuery.value = ""
        _selectedCategory.value = null
        _selectedFolder.value = null
        _selectedExtension.value = null
        _minSizeMb.value = ""
        _maxSizeMb.value = ""
        _dateFrom.value = ""
        _dateTo.value = ""
        _sortField.value = SortField.NAME
        _sortAscending.value = true
    }

    fun showFileDetails(file: FileItem) {
        _selectedFileForDetails.value = file
    }

    fun dismissFileDetails() {
        _selectedFileForDetails.value = null
    }

    // When the user picks a real folder from their phone, this scans it in the background
    fun scanFolderUri(uri: Uri) {
        viewModelScope.launch {
            repository.scanFolderUri(uri)
            refreshOrganizePreview()
            runDuplicateAnalysis()
            _toastMessage.value = "Folder scanned successfully."
        }
    }

    // Tapping the Demo button reloads our 220 sample files right away
    fun resetToDemoData() {
        repository.loadDemoDataset()
        clearAllFilters()
        refreshOrganizePreview()
        runDuplicateAnalysis()
        _toastMessage.value = "Mandatory 220-file test dataset loaded across 11 subfolders."
    }

    // Runs the two step check in the repository to find exact duplicate files
    fun runDuplicateAnalysis() {
        viewModelScope.launch {
            _isAnalyzingDuplicates.value = true
            val results = repository.detectDuplicates { prog, text ->
                _duplicateProgress.value = prog
                _duplicateStatusText.value = text
            }
            _duplicateGroups.value = results
            _isAnalyzingDuplicates.value = false
            _toastMessage.value = if (results.isNotEmpty()) "Identified ${results.size} duplicate groups." else "No duplicate files found."
        }
    }

    // Deletes the extra copies in one duplicate group while keeping the first original file safe
    fun resolveGroup(group: DuplicateGroup) {
        repository.resolveDuplicateGroup(group)
        _duplicateGroups.value = _duplicateGroups.value.filter { it.hash != group.hash }
        refreshOrganizePreview()
        _toastMessage.value = "Removed duplicate copies in group."
    }

    // Cleans up the extra copies in every duplicate group all at once
    fun resolveAllDuplicates() {
        val count = _duplicateGroups.value.size
        repository.resolveAllDuplicates(_duplicateGroups.value)
        _duplicateGroups.value = emptyList()
        refreshOrganizePreview()
        _toastMessage.value = "Cleaned up all $count duplicate groups!"
    }

    // Deletes a single file and updates any duplicate group it belonged to
    fun deleteFile(file: FileItem) {
        repository.deleteFile(file.id)
        _duplicateGroups.value = _duplicateGroups.value.mapNotNull { group ->
            val remaining = group.files.filter { it.id != file.id }
            if (remaining.size > 1) {
                val size = remaining.first().sizeBytes
                group.copy(
                    files = remaining,
                    wastedBytes = size * (remaining.size - 1)
                )
            } else null
        }
        if (_selectedFileForDetails.value?.id == file.id) {
            _selectedFileForDetails.value = null
        }
        refreshOrganizePreview()
        _toastMessage.value = "Deleted ${file.name}"
    }

    fun setOrganizeStrategy(strategy: OrganizeStrategy) {
        _organizeStrategy.value = strategy
        refreshOrganizePreview()
    }

    private fun refreshOrganizePreview() {
        _organizePreview.value = repository.generateOrganizePreview(_organizeStrategy.value)
    }

    // Moves the files into their new organized folders when the user taps Apply
    fun applyOrganization() {
        val preview = _organizePreview.value
        repository.applyOrganization(preview)
        refreshOrganizePreview()
        _toastMessage.value = "Organized ${preview.size} files into structured folders."
    }

    fun clearToast() {
        _toastMessage.value = null
    }

    // Quick helper functions used by the Dashboard, Charts, and Export screens
    fun getFolderCount(): Int = repository.getFolderCount()
    fun getUniqueFolders(): List<String> = repository.getUniqueFolders()
    fun getUniqueExtensions(): List<String> = repository.getUniqueExtensions()
    fun getCategorySummaries(): List<CategorySummary> = repository.getCategorySummaries()
    fun getExtensionSummaries(): List<ExtensionSummary> = repository.getExtensionSummaries()
    fun getSizeTierSummaries(): List<SizeTierSummary> = repository.getSizeTierSummaries()
    fun getTimelineSummaries(): List<TimelineSummary> = repository.getTimelineSummaries()
    fun exportCsv(): String = repository.exportToCsv()
    fun exportJson(): String = repository.exportToJson()
}
