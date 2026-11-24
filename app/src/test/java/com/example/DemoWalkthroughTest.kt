package com.example

import android.graphics.Bitmap
import android.graphics.Canvas
import android.os.Looper
import androidx.activity.viewModels
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertTextContains
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import com.example.data.model.FileCategory
import com.example.data.model.OrganizeStrategy
import com.example.ui.viewmodel.AppTab
import com.example.ui.viewmodel.ExportFormat
import com.example.ui.viewmodel.FileOrganizerViewModel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import java.io.FileOutputStream

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [36], qualifiers = "w1024dp-h768dp-xhdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class DemoWalkthroughTest {

    @get:Rule
    val composeTestRule = createAndroidComposeRule<MainActivity>()

    private fun settle() {
        shadowOf(Looper.getMainLooper()).idle()
        composeTestRule.waitForIdle()
        shadowOf(Looper.getMainLooper()).idle()
    }

    private fun maybeCaptureScreenshot(filename: String, minWidth: Int, minHeight: Int) {
        val dirPath = System.getProperty("demo.screenshot.dir") ?: return
        val dir = File(dirPath).apply { mkdirs() }
        val decorView = composeTestRule.activity.window.decorView
        val width = decorView.width.coerceAtLeast(minWidth)
        val height = decorView.height.coerceAtLeast(minHeight)
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        decorView.draw(Canvas(bitmap))
        FileOutputStream(File(dir, filename)).use { fos ->
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, fos)
        }
    }

    @Test
    fun fullGuidedWalkthroughDemonstratesAllSixFeaturesAndRestoresDataset() {
        val viewModel = composeTestRule.activity.viewModels<FileOrganizerViewModel>().value
        settle()

        // Initially demo walkthrough is inactive
        assertFalse(viewModel.demoState.value.isActive)
        composeTestRule.onNodeWithTag("demo_button").assertIsDisplayed()

        // Start Guided Demo Walkthrough
        composeTestRule.onNodeWithTag("demo_button").performClick()
        settle()

        assertTrue(viewModel.demoState.value.isActive)
        assertEquals(AppTab.DASHBOARD, viewModel.activeTab.value)
        composeTestRule.onNodeWithTag("demo_walkthrough_card").assertIsDisplayed()
        composeTestRule.onNodeWithTag("demo_step_counter").assertTextContains("DEMO 1/6")
        composeTestRule.onNodeWithTag("demo_back_btn").assertIsNotEnabled()
        maybeCaptureScreenshot("demo_tablet_step1.png", 1024, 768)

        // Step 1 action: Inspect Largest File opens FileDetailDialog
        composeTestRule.onNodeWithTag("demo_action_btn").performClick()
        settle()
        assertNotNull(viewModel.selectedFileForDetails.value)
        composeTestRule.onNodeWithTag("file_detail_dialog").assertIsDisplayed()
        composeTestRule.onNodeWithTag("close_detail_button").performClick()
        settle()

        // Step 2: All Files — Photo filter + Grid view
        composeTestRule.onNodeWithTag("demo_next_btn").performClick()
        settle()
        assertEquals(AppTab.FILES, viewModel.activeTab.value)
        composeTestRule.onNodeWithTag("demo_step_counter").assertTextContains("DEMO 2/6")
        composeTestRule.onNodeWithTag("demo_back_btn").assertIsEnabled()

        composeTestRule.onNodeWithTag("demo_action_btn").performClick()
        settle()
        assertEquals(FileCategory.IMAGE, viewModel.selectedCategory.value)
        assertEquals("DSC", viewModel.searchQuery.value)
        assertTrue(viewModel.isGridView.value)
        composeTestRule.onNodeWithTag("demo_action_note").assertIsDisplayed()
        maybeCaptureScreenshot("demo_tablet_step2_grid.png", 1024, 768)

        // Step 3: Duplicates — Clean 1 duplicate group live
        composeTestRule.onNodeWithTag("demo_next_btn").performClick()
        settle()
        assertEquals(AppTab.DUPLICATES, viewModel.activeTab.value)
        composeTestRule.onNodeWithTag("demo_step_counter").assertTextContains("DEMO 3/6")

        // Ensure duplicate analysis has completed on background dispatcher before clicking action
        val deadline = System.currentTimeMillis() + 5000L
        while (viewModel.duplicateGroups.value.isEmpty() && System.currentTimeMillis() < deadline) {
            Thread.sleep(50)
            settle()
        }
        val initialGroupCount = viewModel.duplicateGroups.value.size
        assertTrue("Expected demo dataset to contain duplicate groups", initialGroupCount >= 2)

        composeTestRule.onNodeWithTag("demo_action_btn").performClick()
        settle()
        assertEquals(initialGroupCount - 1, viewModel.duplicateGroups.value.size)

        // Step 4: Charts — Inspect Photo EXIF
        composeTestRule.onNodeWithTag("demo_next_btn").performClick()
        settle()
        assertEquals(AppTab.CHARTS, viewModel.activeTab.value)
        composeTestRule.onNodeWithTag("demo_step_counter").assertTextContains("DEMO 4/6")

        composeTestRule.onNodeWithTag("demo_action_btn").performClick()
        settle()
        assertNotNull(viewModel.selectedFileForDetails.value?.imageMetadata)
        composeTestRule.onNodeWithTag("close_detail_button").performClick()
        settle()

        // Step 5: Organize — Preview By Date & Apply
        composeTestRule.onNodeWithTag("demo_next_btn").performClick()
        settle()
        assertEquals(AppTab.ORGANIZE, viewModel.activeTab.value)
        composeTestRule.onNodeWithTag("demo_step_counter").assertTextContains("DEMO 5/6")

        composeTestRule.onNodeWithTag("demo_action_btn").performClick()
        settle()
        assertEquals(OrganizeStrategy.BY_DATE, viewModel.organizeStrategy.value)
        assertTrue(viewModel.allFiles.value.first().path.startsWith("Organized/"))

        // Step 6: Export — Toggle CSV to JSON
        composeTestRule.onNodeWithTag("demo_next_btn").performClick()
        settle()
        assertEquals(AppTab.EXPORT, viewModel.activeTab.value)
        composeTestRule.onNodeWithTag("demo_step_counter").assertTextContains("DEMO 6/6")
        assertEquals(ExportFormat.CSV, viewModel.exportFormat.value)

        composeTestRule.onNodeWithTag("demo_action_btn").performClick()
        settle()
        assertEquals(ExportFormat.JSON, viewModel.exportFormat.value)

        // Back button moves cleanly to Step 5, then jump back to Step 6 via dot
        composeTestRule.onNodeWithTag("demo_back_btn").performClick()
        settle()
        assertEquals(AppTab.ORGANIZE, viewModel.activeTab.value)

        composeTestRule.onNodeWithTag("demo_step_dot_5").performClick()
        settle()
        assertEquals(AppTab.EXPORT, viewModel.activeTab.value)

        // Finish Demo exits walkthrough and restores clean 200-file sample dataset
        composeTestRule.onNodeWithTag("demo_next_btn").performClick()
        settle()
        assertFalse(viewModel.demoState.value.isActive)
        assertEquals(200, viewModel.allFiles.value.size)
        assertEquals(ExportFormat.CSV, viewModel.exportFormat.value)
    }

    @Test
    fun exitButtonClosesDemoWalkthroughImmediately() {
        val viewModel = composeTestRule.activity.viewModels<FileOrganizerViewModel>().value
        settle()

        composeTestRule.onNodeWithTag("demo_button").performClick()
        settle()
        assertTrue(viewModel.demoState.value.isActive)

        // Tapping top-bar Exit Demo button closes walkthrough
        composeTestRule.onNodeWithTag("demo_button").performClick()
        settle()
        assertFalse(viewModel.demoState.value.isActive)
    }

    @Test
    @Config(qualifiers = "w390dp-h844dp-xhdpi")
    fun phoneLayoutRendersCompactWalkthroughAndSyncsWithBottomNav() {
        val viewModel = composeTestRule.activity.viewModels<FileOrganizerViewModel>().value
        settle()

        composeTestRule.onNodeWithTag("main_bottom_nav").assertIsDisplayed()
        composeTestRule.onNodeWithTag("demo_button").performClick()
        settle()

        composeTestRule.onNodeWithTag("demo_walkthrough_card").assertIsDisplayed()
        composeTestRule.onNodeWithTag("demo_step_counter").assertTextContains("DEMO 1/6")
        maybeCaptureScreenshot("demo_phone_step1.png", 390, 844)

        // Manually tapping Charts in the bottom navigation syncs walkthrough to Step 4
        composeTestRule.onNodeWithTag("nav_tab_charts").performClick()
        settle()

        assertEquals(AppTab.CHARTS, viewModel.activeTab.value)
        assertEquals(3, viewModel.demoState.value.currentStepIndex)
        composeTestRule.onNodeWithTag("demo_step_counter").assertTextContains("DEMO 4/6")

        // Close button inside the walkthrough card exits Demo mode cleanly
        composeTestRule.onNodeWithTag("demo_close_btn").performClick()
        settle()
        assertFalse(viewModel.demoState.value.isActive)
    }
}
