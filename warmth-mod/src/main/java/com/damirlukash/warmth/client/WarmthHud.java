package com.damirlukash.warmth.client;

import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.world.GameMode;

/**
 * Renders the yellow warmth bar in the HUD, placed just above the food bar
 * on the right side of the hotbar. Style is intentionally vanilla-looking:
 * a flat 81x6 bar with a 1px dark border and yellow fill.
 */
@Environment(EnvType.CLIENT)
public class WarmthHud implements HudRenderCallback {

    private static final int BAR_WIDTH = 81;
    private static final int BAR_HEIGHT = 6;
    private static final int BORDER_COLOR = 0xFF1A1A1A;
    private static final int BG_COLOR = 0xFF3F3F3F;
    private static final int FILL_COLOR = 0xFFFFC832;       // warm yellow
    private static final int FILL_COLOR_LOW = 0xFFFF7A2A;   // orange when below half
    private static final int FILL_COLOR_FREEZE = 0xFF6FB7FF;// cyan when at zero — freezing

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

        int screenWidth = ctx.getScaledWindowWidth();
        int screenHeight = ctx.getScaledWindowHeight();

        // Place above the food bar (which sits at y = screenHeight - 39 with 9px height).
        int x = screenWidth / 2 + 10;
        int y = screenHeight - 49 - BAR_HEIGHT - 2;

        // Border / background
        ctx.fill(x - 1, y - 1, x + BAR_WIDTH + 1, y + BAR_HEIGHT + 1, BORDER_COLOR);
        ctx.fill(x, y, x + BAR_WIDTH, y + BAR_HEIGHT, BG_COLOR);

        int fillWidth = Math.round(BAR_WIDTH * ratio);
        int color;
        if (ratio <= 0.0001f) {
            color = FILL_COLOR_FREEZE;
        } else if (ratio < 0.5f) {
            color = FILL_COLOR_LOW;
        } else {
            color = FILL_COLOR;
        }

        if (fillWidth > 0) {
            ctx.fill(x, y, x + fillWidth, y + BAR_HEIGHT, color);
        }

        // Mid-line indicator at 50% so players can see the "safe" threshold.
        int mid = x + BAR_WIDTH / 2;
        ctx.fill(mid, y, mid + 1, y + BAR_HEIGHT, 0x80FFFFFF);
    }
}
