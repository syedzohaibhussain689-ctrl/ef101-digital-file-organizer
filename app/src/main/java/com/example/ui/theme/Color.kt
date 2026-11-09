package com.example.ui.theme

import androidx.compose.ui.graphics.Color

// All colors used in our app are kept right here so every screen matches nicely.
// We use a clean off white background with crisp white cards and dark charcoal buttons.
val BG = Color(0xFFF9F9F8)            // Soft off white color for the sidebar and background panels
val SURFACE = Color(0xFFFFFFFF)       // Pure white color for cards and main pages
val BORDER = Color(0xFFE8E8E5)        // Thin border line color around cards
val BORDER_LIGHT = Color(0xFFF0F0EE)  // Very light divider line between table rows
val TEXT = Color(0xFF171716)          // Dark charcoal color for main headings and important text
val TEXT_SEC = Color(0xFF5E5E5A)      // Medium grey color for secondary details
val TEXT_MUTED = Color(0xFF8F8F8A)    // Light grey color for small labels and hints
val ACCENT = Color(0xFF171716)        // Dark accent color for primary action buttons
val ACCENT_SOFT = Color(0xFFF2F2F0)   // Soft highlight color behind selected tabs
val DANGER = Color(0xFF9B2C2C)        // Red color for delete buttons and duplicate badges
val DANGER_SOFT = Color(0xFFFEF2F2)   // Light pink background for warning boxes

// Six distinct shades of grey to tell the 6 file categories apart in charts and badges
val CatImage = Color(0xFF111111)
val CatDocument = Color(0xFF444444)
val CatAudio = Color(0xFF666666)
val CatVideo = Color(0xFF888888)
val CatArchive = Color(0xFFAAAAAA)
val CatOther = Color(0xFFCCCCCC)
