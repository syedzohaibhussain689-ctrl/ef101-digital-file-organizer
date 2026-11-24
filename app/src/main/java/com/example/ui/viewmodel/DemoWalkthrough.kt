package com.example.ui.viewmodel

// Represents one interactive stop along the 6-step Guided Demo Walkthrough.
data class DemoStep(
    val index: Int,
    val tab: AppTab,
    val badgeLabel: String,
    val title: String,
    val description: String,
    val actionLabel: String,
    val completedActionLabel: String
)

// Holds the ordered walkthrough steps covering all 6 screens of FileOrganizer.
object DemoSteps {
    val all: List<DemoStep> = listOf(
        DemoStep(
            index = 0,
            tab = AppTab.DASHBOARD,
            badgeLabel = "Dashboard",
            title = "Storage Dashboard Overview",
            description = "See total files, storage usage, recoverable duplicate space, category breakdown bars, and your 10 largest files in one view.",
            actionLabel = "Inspect Largest File",
            completedActionLabel = "Inspect Again"
        ),
        DemoStep(
            index = 1,
            tab = AppTab.FILES,
            badgeLabel = "All Files",
            title = "Smart Search, Filters & Grid View",
            description = "Search names, paths, or extensions, filter by category, size, or date range, sort any column, and switch between List and thumbnail Grid view.",
            actionLabel = "Try Photo Filter + Grid",
            completedActionLabel = "Reset to All List"
        ),
        DemoStep(
            index = 2,
            tab = AppTab.DUPLICATES,
            badgeLabel = "Duplicates",
            title = "Two-Step SHA-256 Duplicate Finder",
            description = "Identifies identical files even when renamed across folders by grouping exact byte sizes first, then verifying SHA-256 hashes.",
            actionLabel = "Clean 1 Duplicate Group",
            completedActionLabel = "Restore Demo Duplicates"
        ),
        DemoStep(
            index = 3,
            tab = AppTab.CHARTS,
            badgeLabel = "Charts",
            title = "Visual Storage Analytics",
            description = "Explore 4 live analytics cards: Storage by Category, File-Size Distribution (Small to Huge), Activity Timeline, and Top Extensions.",
            actionLabel = "Inspect Photo EXIF",
            completedActionLabel = "Inspect Photo Again"
        ),
        DemoStep(
            index = 4,
            tab = AppTab.ORGANIZE,
            badgeLabel = "Organize",
            title = "Safe Dry-Run Folder Organization",
            description = "Choose By Category, By Date, or By Extension and review every planned folder move before applying changes.",
            actionLabel = "Preview By Date & Apply",
            completedActionLabel = "Switch to By Category"
        ),
        DemoStep(
            index = 5,
            tab = AppTab.EXPORT,
            badgeLabel = "Export",
            title = "Export Inventory to CSV or JSON",
            description = "Generate complete inventory reports with scan metadata and SHA-256 hashes, switch formats live, and copy or share in one tap.",
            actionLabel = "Switch to JSON Preview",
            completedActionLabel = "Switch to CSV Preview"
        )
    )

    fun indexForTab(tab: AppTab): Int = all.indexOfFirst { it.tab == tab }.coerceAtLeast(0)
}

// Tracks whether the Guided Demo Walkthrough is active, which step is showing,
// whether auto-play is running, and which interactive step actions have been tried.
data class DemoWalkthroughState(
    val isActive: Boolean = false,
    val currentStepIndex: Int = 0,
    val isAutoPlaying: Boolean = false,
    val completedSteps: Set<Int> = emptySet(),
    val lastActionNote: String? = null
) {
    val currentStep: DemoStep
        get() = DemoSteps.all[currentStepIndex.coerceIn(0, DemoSteps.all.lastIndex)]

    val totalSteps: Int
        get() = DemoSteps.all.size

    val isFirstStep: Boolean
        get() = currentStepIndex <= 0

    val isLastStep: Boolean
        get() = currentStepIndex >= DemoSteps.all.lastIndex

    val isCurrentActionDone: Boolean
        get() = currentStepIndex in completedSteps

    val progressFraction: Float
        get() = (currentStepIndex + 1).toFloat() / totalSteps.toFloat()
}
