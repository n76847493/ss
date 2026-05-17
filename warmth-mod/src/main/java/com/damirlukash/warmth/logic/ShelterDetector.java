package com.damirlukash.warmth.logic;

import net.minecraft.block.BlockState;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;

/**
 * Detects whether a player is inside something that should count as a real
 * shelter (regenerates warmth) or just a dirt-burrow exploit (gives almost
 * nothing).
 *
 * <p>A "proper house" must satisfy two conditions:
 * <ul>
 *   <li>The player cannot see the sky.</li>
 *   <li>At least {@code MIN_HOUSE_BLOCKS} blocks within a 5x4x5 box around the
 *       player are crafted "house" blocks (planks / glass / wool / crafting
 *       table / doors / etc.).</li>
 * </ul>
 *
 * Otherwise, if the player is enclosed but their surroundings are all natural
 * blocks (dirt, stone, gravel, sand), it counts as a DIRT_HOLE — provides
 * almost no warmth bonus, encouraging players to actually build.
 */
public final class ShelterDetector {

    /** Minimum count of crafted "house blocks" required around the player. */
    private static final int MIN_HOUSE_BLOCKS = 6;
    private static final int RADIUS_H = 3;
    private static final int RADIUS_V = 2;

    public enum ShelterQuality {
        PROPER_HOUSE,
        DIRT_HOLE,
        OPEN_AIR_OR_NONE
    }

    public static ShelterQuality evaluate(World world, BlockPos playerPos) {
        BlockPos head = playerPos.up();

        // Must be enclosed: can't see sky directly above head AND must be
        // surrounded by solid blocks within a small radius in each cardinal
        // direction (otherwise being on a covered balcony would count).
        if (world.isSkyVisible(head)) {
            return ShelterQuality.OPEN_AIR_OR_NONE;
        }
        if (!isEnclosed(world, head)) {
            return ShelterQuality.OPEN_AIR_OR_NONE;
        }

        int houseBlockCount = 0;
        BlockPos.Mutable mp = new BlockPos.Mutable();
        for (int dx = -RADIUS_H; dx <= RADIUS_H; dx++) {
            for (int dy = -RADIUS_V; dy <= RADIUS_V; dy++) {
                for (int dz = -RADIUS_H; dz <= RADIUS_H; dz++) {
                    mp.set(playerPos.getX() + dx, playerPos.getY() + dy, playerPos.getZ() + dz);
                    BlockState s = world.getBlockState(mp);
                    if (HouseBlocks.isHouseBlock(s)) {
                        houseBlockCount++;
                        if (houseBlockCount >= MIN_HOUSE_BLOCKS) {
                            return ShelterQuality.PROPER_HOUSE;
                        }
                    }
                }
            }
        }
        return ShelterQuality.DIRT_HOLE;
    }

    /**
     * Player is "enclosed" when in every cardinal direction within a short
     * range there is at least one opaque block stopping the wind. This is what
     * stops a 1x1x2 dirt-hole from being trivially detectable as proper shelter
     * — but combined with the house-block check above, even a fully enclosed
     * dirt hole counts only as a DIRT_HOLE.
     */
    private static boolean isEnclosed(World world, BlockPos head) {
        return blocksWithin(world, head, 1, 0, 0, 8)
                && blocksWithin(world, head, -1, 0, 0, 8)
                && blocksWithin(world, head, 0, 0, 1, 8)
                && blocksWithin(world, head, 0, 0, -1, 8)
                && blocksWithin(world, head, 0, 1, 0, 6)
                && blocksWithin(world, head, 0, -1, 0, 4);
    }

    private static boolean blocksWithin(World world, BlockPos origin, int sx, int sy, int sz, int maxDist) {
        BlockPos.Mutable mp = new BlockPos.Mutable();
        for (int i = 1; i <= maxDist; i++) {
            mp.set(origin.getX() + sx * i, origin.getY() + sy * i, origin.getZ() + sz * i);
            BlockState s = world.getBlockState(mp);
            if (s.isOpaqueFullCube(world, mp)) return true;
        }
        return false;
    }
}
