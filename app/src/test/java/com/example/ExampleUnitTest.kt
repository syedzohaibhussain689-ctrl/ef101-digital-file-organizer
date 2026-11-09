package com.example

import com.example.data.model.FileCategory
import com.example.data.model.formatReadableSize
import org.junit.Assert.assertEquals
import org.junit.Test

class ExampleUnitTest {

    @Test
    fun testFileCategoryClassification() {
        assertEquals(FileCategory.IMAGE, FileCategory.fromExtension(".jpg"))
        assertEquals(FileCategory.IMAGE, FileCategory.fromExtension(".png"))
        assertEquals(FileCategory.DOCUMENT, FileCategory.fromExtension(".pdf"))
        assertEquals(FileCategory.DOCUMENT, FileCategory.fromExtension(".docx"))
        assertEquals(FileCategory.AUDIO, FileCategory.fromExtension(".mp3"))
        assertEquals(FileCategory.VIDEO, FileCategory.fromExtension(".mp4"))
        assertEquals(FileCategory.ARCHIVE, FileCategory.fromExtension(".zip"))
        assertEquals(FileCategory.OTHER, FileCategory.fromExtension(".xyz"))
    }

    @Test
    fun testReadableSizeFormatting() {
        assertEquals("0 B", formatReadableSize(0))
        assertEquals("500.0 B", formatReadableSize(500))
        assertEquals("1.0 KB", formatReadableSize(1024))
        assertEquals("1.0 MB", formatReadableSize(1024 * 1024))
        assertEquals("1.5 MB", formatReadableSize((1.5 * 1024 * 1024).toLong()))
    }
}
