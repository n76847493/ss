package com.damirlukash.warmth.logic;

import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.block.Blocks;
import net.minecraft.registry.tag.BlockTags;

import java.util.Set;

/**
 * Identifies blocks that count as "made by a player" — used to distinguish a
 * proper house from a hand-dug dirt burrow. A burrow with only natural blocks
 * (dirt / stone / sand / etc.) around does NOT count as shelter for warmth.
 */
public final class HouseBlocks {
    private HouseBlocks() {}

    private static final Set<Block> EXTRA_HOUSE_BLOCKS = Set.of(
            Blocks.CRAFTING_TABLE,
            Blocks.FURNACE,
            Blocks.BLAST_FURNACE,
            Blocks.SMOKER,
            Blocks.SMITHING_TABLE,
            Blocks.FLETCHING_TABLE,
            Blocks.CARTOGRAPHY_TABLE,
            Blocks.LOOM,
            Blocks.STONECUTTER,
            Blocks.GRINDSTONE,
            Blocks.ANVIL,
            Blocks.CHIPPED_ANVIL,
            Blocks.DAMAGED_ANVIL,
            Blocks.BREWING_STAND,
            Blocks.ENCHANTING_TABLE,
            Blocks.GLASS,
            Blocks.GLASS_PANE,
            Blocks.WHITE_STAINED_GLASS,
            Blocks.BRICKS,
            Blocks.NETHER_BRICKS,
            Blocks.RED_NETHER_BRICKS,
            Blocks.STONE_BRICKS,
            Blocks.MOSSY_STONE_BRICKS,
            Blocks.CRACKED_STONE_BRICKS,
            Blocks.CHISELED_STONE_BRICKS,
            Blocks.POLISHED_BLACKSTONE_BRICKS,
            Blocks.PRISMARINE_BRICKS,
            Blocks.LADDER,
            Blocks.TORCH,
            Blocks.WALL_TORCH,
            Blocks.LANTERN,
            Blocks.SOUL_LANTERN,
            Blocks.SOUL_TORCH,
            Blocks.CAMPFIRE,
            Blocks.SOUL_CAMPFIRE,
            Blocks.CHEST,
            Blocks.TRAPPED_CHEST,
            Blocks.BARREL,
            Blocks.BOOKSHELF
    );

    public static boolean isHouseBlock(BlockState state) {
        Block b = state.getBlock();
        if (EXTRA_HOUSE_BLOCKS.contains(b)) return true;
        if (state.isIn(BlockTags.PLANKS)) return true;
        if (state.isIn(BlockTags.WOODEN_DOORS)) return true;
        if (state.isIn(BlockTags.WOODEN_TRAPDOORS)) return true;
        if (state.isIn(BlockTags.WOODEN_SLABS)) return true;
        if (state.isIn(BlockTags.WOODEN_STAIRS)) return true;
        if (state.isIn(BlockTags.WOOL)) return true;
        if (state.isIn(BlockTags.WOOL_CARPETS)) return true;
        if (state.isIn(BlockTags.BEDS)) return true;
        if (state.isIn(BlockTags.WALLS)) return true;
        return false;
    }
}
