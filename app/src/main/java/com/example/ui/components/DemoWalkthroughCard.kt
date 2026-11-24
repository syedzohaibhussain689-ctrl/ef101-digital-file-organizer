package com.example.ui.components

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.theme.ACCENT
import com.example.ui.theme.ACCENT_SOFT
import com.example.ui.theme.BG
import com.example.ui.theme.BORDER
import com.example.ui.theme.BORDER_LIGHT
import com.example.ui.theme.SURFACE
import com.example.ui.theme.TEXT
import com.example.ui.theme.TEXT_MUTED
import com.example.ui.theme.TEXT_SEC
import com.example.ui.viewmodel.DemoSteps
import com.example.ui.viewmodel.DemoWalkthroughState

// Docked interactive walkthrough panel shown while Guided Demo mode is active.
// Lets the user step through all 6 screens, trigger live demonstrations, or toggle Auto-Play.
@Composable
fun DemoWalkthroughPanel(
    state: DemoWalkthroughState,
    isCompact: Boolean,
    onPrevious: () -> Unit,
    onNext: () -> Unit,
    onSelectStep: (Int) -> Unit,
    onRunStepAction: () -> Unit,
    onToggleAutoPlay: () -> Unit,
    onExit: () -> Unit,
    modifier: Modifier = Modifier
) {
    val step = state.currentStep
    val actionText = if (state.isCurrentActionDone) step.completedActionLabel else step.actionLabel

    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(BG)
            .testTag("demo_walkthrough_card")
    ) {
        HorizontalDivider(color = BORDER)

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = if (isCompact) 12.dp else 24.dp, vertical = 10.dp),
            contentAlignment = Alignment.Center
        ) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .widthIn(max = 780.dp)
                    .border(1.dp, ACCENT, RoundedCornerShape(10.dp))
                    .animateContentSize(),
                shape = RoundedCornerShape(10.dp),
                colors = CardDefaults.cardColors(containerColor = SURFACE),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(modifier = Modifier.fillMaxWidth()) {
                    // Top progress strip showing how far along the 6-step tour we are
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(3.dp)
                            .background(BORDER_LIGHT)
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth(state.progressFraction.coerceIn(0f, 1f))
                                .height(3.dp)
                                .background(ACCENT)
                        )
                    }

                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 12.dp)
                    ) {
                        // Top row: Step badge, clickable progress dots, Auto-Play toggle, and Close
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Surface(
                                    color = ACCENT,
                                    shape = RoundedCornerShape(4.dp)
                                ) {
                                    Text(
                                        text = "DEMO ${state.currentStepIndex + 1}/${state.totalSteps}",
                                        fontSize = 10.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        color = Color.White,
                                        modifier = Modifier
                                            .padding(horizontal = 7.dp, vertical = 3.dp)
                                            .testTag("demo_step_counter")
                                    )
                                }

                                // Interactive step dots so the user can jump directly to any screen
                                Row(
                                    horizontalArrangement = Arrangement.spacedBy(5.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    DemoSteps.all.forEach { item ->
                                        val isCurrent = item.index == state.currentStepIndex
                                        val isDone = item.index in state.completedSteps
                                        Box(
                                            modifier = Modifier
                                                .height(7.dp)
                                                .width(if (isCurrent) 20.dp else 7.dp)
                                                .clip(CircleShape)
                                                .background(
                                                    when {
                                                        isCurrent -> ACCENT
                                                        isDone -> TEXT_SEC
                                                        else -> BORDER
                                                    }
                                                )
                                                .clickable { onSelectStep(item.index) }
                                                .testTag("demo_step_dot_${item.index}")
                                        )
                                    }
                                }
                            }

                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(4.dp)
                            ) {
                                // Auto-Play / Pause toggle pill
                                Surface(
                                    color = if (state.isAutoPlaying) ACCENT_SOFT else SURFACE,
                                    shape = RoundedCornerShape(5.dp),
                                    modifier = Modifier
                                        .border(
                                            1.dp,
                                            if (state.isAutoPlaying) ACCENT else BORDER,
                                            RoundedCornerShape(5.dp)
                                        )
                                        .clickable(onClick = onToggleAutoPlay)
                                        .testTag("demo_autoplay_btn")
                                ) {
                                    Row(
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Icon(
                                            imageVector = if (state.isAutoPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                                            contentDescription = if (state.isAutoPlaying) "Pause Auto-Play" else "Auto-Play Demo",
                                            tint = if (state.isAutoPlaying) ACCENT else TEXT_SEC,
                                            modifier = Modifier.size(13.dp)
                                        )
                                        Spacer(modifier = Modifier.width(3.dp))
                                        Text(
                                            text = if (state.isAutoPlaying) "Pause" else "Auto",
                                            fontSize = 11.sp,
                                            fontWeight = FontWeight.Medium,
                                            color = if (state.isAutoPlaying) ACCENT else TEXT_SEC
                                        )
                                    }
                                }

                                IconButton(
                                    onClick = onExit,
                                    modifier = Modifier
                                        .size(28.dp)
                                        .testTag("demo_close_btn")
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Close,
                                        contentDescription = "Exit Guided Demo",
                                        tint = TEXT_MUTED,
                                        modifier = Modifier.size(16.dp)
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        // Current step title and concise explanation
                        Text(
                            text = step.title,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TEXT,
                            modifier = Modifier.testTag("demo_step_title")
                        )

                        Spacer(modifier = Modifier.height(3.dp))

                        Text(
                            text = step.description,
                            fontSize = 12.sp,
                            color = TEXT_SEC,
                            lineHeight = 17.sp
                        )

                        // Live feedback chip showing what the interactive Try It action just did
                        if (state.lastActionNote != null) {
                            Spacer(modifier = Modifier.height(8.dp))
                            Surface(
                                color = ACCENT_SOFT,
                                shape = RoundedCornerShape(6.dp),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .border(1.dp, BORDER, RoundedCornerShape(6.dp))
                                    .testTag("demo_action_note")
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.CheckCircle,
                                        contentDescription = null,
                                        tint = ACCENT,
                                        modifier = Modifier.size(14.dp)
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text(
                                        text = state.lastActionNote,
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Medium,
                                        color = TEXT,
                                        maxLines = 2,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        // Bottom controls: stacked cleanly on narrow phone widths, single row on tablets
                        if (isCompact) {
                            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                DemoTryActionButton(
                                    label = actionText,
                                    isDone = state.isCurrentActionDone,
                                    onClick = onRunStepAction,
                                    modifier = Modifier.fillMaxWidth()
                                )
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    DemoBackButton(
                                        enabled = !state.isFirstStep,
                                        onClick = onPrevious,
                                        modifier = Modifier.weight(1f)
                                    )
                                    DemoNextButton(
                                        isLastStep = state.isLastStep,
                                        onClick = onNext,
                                        modifier = Modifier.weight(1f)
                                    )
                                }
                            }
                        } else {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                DemoTryActionButton(
                                    label = actionText,
                                    isDone = state.isCurrentActionDone,
                                    onClick = onRunStepAction
                                )

                                Row(
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    DemoBackButton(
                                        enabled = !state.isFirstStep,
                                        onClick = onPrevious
                                    )
                                    DemoNextButton(
                                        isLastStep = state.isLastStep,
                                        onClick = onNext
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun DemoTryActionButton(
    label: String,
    isDone: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    OutlinedButton(
        onClick = onClick,
        shape = RoundedCornerShape(6.dp),
        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
        colors = ButtonDefaults.outlinedButtonColors(
            containerColor = if (isDone) ACCENT_SOFT else SURFACE,
            contentColor = ACCENT
        ),
        modifier = modifier.testTag("demo_action_btn")
    ) {
        Icon(
            imageVector = if (isDone) Icons.Default.Check else Icons.Default.Bolt,
            contentDescription = null,
            tint = ACCENT,
            modifier = Modifier.size(14.dp)
        )
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            text = label,
            fontSize = 12.sp,
            fontWeight = FontWeight.SemiBold,
            color = TEXT,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
    }
}

@Composable
private fun DemoBackButton(
    enabled: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        shape = RoundedCornerShape(6.dp),
        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
        modifier = modifier.testTag("demo_back_btn")
    ) {
        Icon(
            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
            contentDescription = null,
            modifier = Modifier.size(14.dp)
        )
        Spacer(modifier = Modifier.width(4.dp))
        Text(
            text = "Back",
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium
        )
    }
}

@Composable
private fun DemoNextButton(
    isLastStep: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Button(
        onClick = onClick,
        colors = ButtonDefaults.buttonColors(
            containerColor = ACCENT,
            contentColor = Color.White
        ),
        shape = RoundedCornerShape(6.dp),
        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp),
        modifier = modifier.testTag("demo_next_btn")
    ) {
        Text(
            text = if (isLastStep) "Finish Demo" else "Next",
            fontSize = 12.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White
        )
        Spacer(modifier = Modifier.width(4.dp))
        Icon(
            imageVector = if (isLastStep) Icons.Default.Check else Icons.AutoMirrored.Filled.ArrowForward,
            contentDescription = null,
            tint = Color.White,
            modifier = Modifier.size(14.dp)
        )
    }
}
