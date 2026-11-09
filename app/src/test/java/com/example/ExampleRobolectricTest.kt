package com.example

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.core.app.ApplicationProvider
import com.example.ui.viewmodel.AppTab
import com.example.ui.viewmodel.FileOrganizerViewModel
import androidx.activity.viewModels
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import android.os.Looper
import java.io.File
import java.io.FileOutputStream

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [36], qualifiers = "w1024dp-h768dp-xhdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class ExampleRobolectricTest {

  @get:Rule
  val composeTestRule = createAndroidComposeRule<MainActivity>()

  @Test
  fun `capture all six screens`() {
    val context = ApplicationProvider.getApplicationContext<Context>()
    assertEquals("FileOrganizer", context.getString(R.string.app_name))

    val outDir = File("/.aistudio/artifacts/brain/fb9f9974-f14d-4438-9399-b453ae46f69b")
    outDir.mkdirs()

    val viewModel = composeTestRule.activity.viewModels<FileOrganizerViewModel>().value

    val tabs = listOf(
      AppTab.DASHBOARD to "screenshot_1_dashboard.png",
      AppTab.FILES to "screenshot_2_all_files.png",
      AppTab.DUPLICATES to "screenshot_3_duplicates.png",
      AppTab.CHARTS to "screenshot_4_charts.png",
      AppTab.ORGANIZE to "screenshot_5_organize.png",
      AppTab.EXPORT to "screenshot_6_export.png"
    )

    for ((tab, filename) in tabs) {
      composeTestRule.activity.runOnUiThread {
        viewModel.setActiveTab(tab)
      }
      shadowOf(Looper.getMainLooper()).idle()
      composeTestRule.waitForIdle()
      shadowOf(Looper.getMainLooper()).idle()

      val decorView = composeTestRule.activity.window.decorView
      val width = decorView.width.coerceAtLeast(1024)
      val height = decorView.height.coerceAtLeast(768)
      val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
      val canvas = Canvas(bitmap)
      decorView.draw(canvas)

      FileOutputStream(File(outDir, filename)).use { fos ->
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, fos)
      }
    }
  }
}

