package com.damirlukash.warmth.client;

import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.world.GameMode;

/**
 * Vanilla-style flame icons rendered above the food bar. Ten 9x9 flame icons
 * are stamped at an 8-pixel stride (matching the food bar's drumstick layout),
 * so the total HUD footprint stays 81 pixels wide. Each icon represents
 * 10 warmth points and can be empty, half-lit (right side only), or fully
 * lit. Lit icons have a brighter tip highlight to read like fire.
 *
 * Colors shift as warmth drains:
 *   - warmth >= 50%  → yellow / amber palette
 *   - warmth < 50%   → orange / red palette
 *   - warmth == 0    → cyan / freezing palette
 *
 * Hidden in Creative / Spectator gamemodes (matches the rest of the survival HUD).
 */
@Environment(EnvType.CLIENT)
public class WarmthHud implements HudRenderCallback {

    private static final int SLOT_COUNT = 10;
    private static final int SLOT_WIDTH = 9;
    private static final int SLOT_HEIGHT = 9;
    private static final int SLOT_STRIDE = 8; // 1-pixel overlap, like vanilla food bar

    // ── Hot / yellow flame palette (warmth >= 50%) ─────────────────────
    private static final int HOT_TIP    = 0xFFFFF2A0;
    private static final int HOT_BODY   = 0xFFFFC832;
    private static final int HOT_SHADOW = 0xFFB87A1A;

    // ── Warm / orange flame palette (0 < warmth < 50%) ────────────────
    private static final int WARM_TIP    = 0xFFFFC880;
    private static final int WARM_BODY   = 0xFFFF7A2A;
    private static final int WARM_SHADOW = 0xFFA03A10;

    // ── Freezing / cyan flame palette (warmth == 0) ───────────────────
    private static final int FREEZE_TIP    = 0xFFCFEBFF;
    private static final int FREEZE_BODY   = 0xFF6FB7FF;
    private static final int FREEZE_SHADOW = 0xFF2A5F94;

    // ── Empty / unfilled flame outline (rendered behind every slot) ───
    private static final int EMPTY_BODY    = 0xFF2A2A2A;
    private static final int EMPTY_SHADOW  = 0xFF000000;

    // 9x9 flame silhouette: 1 = body pixel, 0 = transparent.
    private static final int[][] FLAME_SHAPE = {
            {0, 0, 0, 0, 1, 0, 0, 0, 0},
            {0, 0, 0, 1, 1, 1, 0, 0, 0},
            {0, 0, 1, 1, 1, 1, 1, 0, 0},
            {0, 1, 1, 1, 1, 1, 1, 1, 0},
            {0, 1, 1, 1, 1, 1, 1, 1, 0},
            {1, 1, 1, 1, 1, 1, 1, 1, 1},
            {1, 1, 1, 1, 1, 1, 1, 1, 1},
            {0, 1, 1, 1, 1, 1, 1, 1, 0},
            {0, 0, 1, 0, 1, 0, 1, 0, 0},
    };

    // Highlight (brighter "tip" pixels rendered on top of body).
    private static final int[][] FLAME_TIP = {
            {0, 0, 0, 0, 1, 0, 0, 0, 0},
            {0, 0, 0, 0, 1, 0, 0, 0, 0},
            {0, 0, 0, 0, 1, 0, 0, 0, 0},
            {0, 0, 0, 0, 1, 0, 0, 0, 0},
            {0, 0, 0, 0, 0, 0, 0, 0, 0},
            {0, 0, 0, 0, 0, 0, 0, 0, 0},
            {0, 0, 0, 0, 0, 0, 0, 0, 0},
            {0, 0, 0, 0, 0, 0, 0, 0, 0},
            {0, 0, 0, 0, 0, 0, 0, 0, 0},
    };

    private enum SlotState { EMPTY, HALF, FULL }

    @Override
    public void onHudRender(DrawContext ctx, float tickDelta) {
        MinecraftClient client = MinecraftClient.getInstance();
        if (client.player == null) return;
        if (client.options.hudHidden) return;
        if (client.interactionManager == null) return;
        GameMode gm = client.interactionManager.getCurrentGameMode();
        if (gm == GameMode.SPECTATOR || gm == GameMode.CREATIVE) return;

        if (!ClientWarmthState.hasData) return;

        float max = ClientWarmthState.max;
        if (max <= 0) return;
        float warmth = Math.max(0.0f, Math.min(max, ClientWarmthState.warmth));
        float ratio = warmth / max;

        // Pick the palette based on overall warmth ratio.
        int tipColor, bodyColor, shadowColor;
        if (ratio <= 0.0001f) {
            tipColor = FREEZE_TIP;
            bodyColor = FREEZE_BODY;
            shadowColor = FREEZE_SHADOW;
        } else if (ratio < 0.5f) {
            tipColor = WARM_TIP;
            bodyColor = WARM_BODY;
            shadowColor = WARM_SHADOW;
        } else {
            tipColor = HOT_TIP;
            bodyColor = HOT_BODY;
            shadowColor = HOT_SHADOW;
        }

        int screenWidth = ctx.getScaledWindowWidth();
        int screenHeight = ctx.getScaledWindowHeight();

        // Above the food bar (food bar = y from screenHeight-39, height 9).
        int baseX = screenWidth / 2 + 10;
        int baseY = screenHeight - 39 - SLOT_HEIGHT - 2;

        // At warmth = 0 the freeze state needs to be visible even though no slot
        // is "lit" in the usual sense. Render all 10 slots as cyan "ice flames"
        // so the player sees a clear visual danger signal.
        if (ratio <= 0.0001f) {
            for (int i = 0; i < SLOT_COUNT; i++) {
                int slotX = baseX + i * SLOT_STRIDE;
                drawFlame(ctx, slotX, baseY, SlotState.FULL, tipColor, bodyColor, shadowColor);
            }
            return;
        }

        // Convert warmth to "half-slot" units: 20 half-slots == max warmth.
        int halfUnitsLit = Math.round(warmth / max * (SLOT_COUNT * 2));

        for (int i = 0; i < SLOT_COUNT; i++) {
            int slotX = baseX + i * SLOT_STRIDE;
            SlotState state;
            int leftHalfUnit = i * 2;
            int rightHalfUnit = i * 2 + 1;
            if (halfUnitsLit > rightHalfUnit) {
                state = SlotState.FULL;
            } else if (halfUnitsLit > leftHalfUnit) {
                state = SlotState.HALF;
            } else {
                state = SlotState.EMPTY;
            }
            drawFlame(ctx, slotX, baseY, state, tipColor, bodyColor, shadowColor);
        }
    }

    private void drawFlame(DrawContext ctx, int x, int y, SlotState state,
                           int tipColor, int bodyColor, int shadowColor) {
        // 1) Empty silhouette behind every slot so partial states stay readable.
        for (int row = 0; row < SLOT_HEIGHT; row++) {
            for (int col = 0; col < SLOT_WIDTH; col++) {
                if (FLAME_SHAPE[row][col] == 0) continue;
                ctx.fill(x + col, y + row, x + col + 1, y + row + 1, EMPTY_BODY);
            }
        }

        if (state == SlotState.EMPTY) {
            drawOutline(ctx, x, y, EMPTY_SHADOW);
            return;
        }

        // 2) Lit body (full slot or right half only).
        for (int row = 0; row < SLOT_HEIGHT; row++) {
            for (int col = 0; col < SLOT_WIDTH; col++) {
                if (FLAME_SHAPE[row][col] == 0) continue;
                if (state == SlotState.HALF && col < 4) continue;
                int color = bodyColor;
                if (row >= 6 && (col == 1 || col == 2 || col == 6 || col == 7)) {
                    color = shadowColor;
                }
                ctx.fill(x + col, y + row, x + col + 1, y + row + 1, color);
            }
        }

        // 3) Bright tip on lit pixels.
        for (int row = 0; row < SLOT_HEIGHT; row++) {
            for (int col = 0; col < SLOT_WIDTH; col++) {
                if (FLAME_TIP[row][col] == 0) continue;
                if (state == SlotState.HALF && col < 4) continue;
                ctx.fill(x + col, y + row, x + col + 1, y + row + 1, tipColor);
            }
        }

        drawOutline(ctx, x, y, EMPTY_SHADOW);
    }

    /**
     * Draws a 1-pixel-thick dark outline around the flame silhouette by
     * stamping a shadow pixel wherever an empty cell touches a filled cell.
     */
    private void drawOutline(DrawContext ctx, int x, int y, int color) {
        for (int row = 0; row < SLOT_HEIGHT; row++) {
            for (int col = 0; col < SLOT_WIDTH; col++) {
                if (FLAME_SHAPE[row][col] != 0) continue;
                if ((row > 0 && FLAME_SHAPE[row - 1][col] == 1)
                        || (row < SLOT_HEIGHT - 1 && FLAME_SHAPE[row + 1][col] == 1)
                        || (col > 0 && FLAME_SHAPE[row][col - 1] == 1)
                        || (col < SLOT_WIDTH - 1 && FLAME_SHAPE[row][col + 1] == 1)) {
                    ctx.fill(x + col, y + row, x + col + 1, y + row + 1, color);
                }
            }
        }
    }
}
