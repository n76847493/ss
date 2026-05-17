package com.damirlukash.warmth.logic;

import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.block.Blocks;
import net.minecraft.state.property.Properties;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;

/**
 * Scans blocks around the player to compute incoming heat from fires, lava,
 * lit furnaces, etc. The closer the source and the bigger its radius, the
 * more warmth it grants per second.
 */
public final class HeatSources {
    private HeatSources() {}

    private static final int SCAN_R_HORIZONTAL = 5;
    private static final int SCAN_R_VERTICAL = 3;
    private static final float MAX_GAIN_PER_TICK = 5.0f;

    /** Returns the effective heat radius of the block in blocks, or 0 if not a heat source. */
    public static float getHeatRadius(BlockState state) {
        Block b = state.getBlock();
        if (b == Blocks.LAVA) return 6.0f;
        if (b == Blocks.MAGMA_BLOCK) return 3.0f;
        if (b == Blocks.FIRE) return 4.0f;
        if (b == Blocks.SOUL_FIRE) return 4.0f;
        if (b == Blocks.CAMPFIRE || b == Blocks.SOUL_CAMPFIRE) {
            return isLit(state) ? 5.0f : 0.0f;
        }
        if (b == Blocks.TORCH || b == Blocks.WALL_TORCH) return 2.0f;
        if (b == Blocks.SOUL_TORCH || b == Blocks.SOUL_WALL_TORCH) return 1.5f;
        if (b == Blocks.LANTERN) return 2.5f;
        if (b == Blocks.SOUL_LANTERN) return 1.8f;
        if (b == Blocks.JACK_O_LANTERN) return 2.0f;
        if (b == Blocks.GLOWSTONE) return 1.0f;
        if (b == Blocks.SHROOMLIGHT) return 1.0f;
        if (b == Blocks.FURNACE || b == Blocks.BLAST_FURNACE || b == Blocks.SMOKER) {
            return isLit(state) ? 3.0f : 0.0f;
        }
        return 0.0f;
    }

    private static boolean isLit(BlockState state) {
        if (state.contains(Properties.LIT)) {
            return state.get(Properties.LIT);
        }
        return false;
    }

    /**
     * Sum of contributions from heat sources within a box around {@code center}.
     * Each source contributes (1 - distance/radius) * intensity if within range.
     */
    public static float computeHeatGain(World world, BlockPos center) {
        float total = 0.0f;
        BlockPos.Mutable mp = new BlockPos.Mutable();

        int cx = center.getX();
        int cy = center.getY();
        int cz = center.getZ();

        for (int dx = -SCAN_R_HORIZONTAL; dx <= SCAN_R_HORIZONTAL; dx++) {
            for (int dy = -SCAN_R_VERTICAL; dy <= SCAN_R_VERTICAL; dy++) {
                for (int dz = -SCAN_R_HORIZONTAL; dz <= SCAN_R_HORIZONTAL; dz++) {
                    mp.set(cx + dx, cy + dy, cz + dz);
                    BlockState s = world.getBlockState(mp);
                    float radius = getHeatRadius(s);
                    if (radius <= 0.0f) continue;
                    double distSq = dx * dx + dy * dy + dz * dz;
                    double dist = Math.sqrt(distSq);
                    if (dist >= radius) continue;
                    float falloff = 1.0f - (float) (dist / radius);
                    total += falloff * 1.6f;
                    if (total >= MAX_GAIN_PER_TICK) {
                        return MAX_GAIN_PER_TICK;
                    }
                }
            }
        }
        return total;
    }
}
