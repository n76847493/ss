package com.damirlukash.warmth.logic;

import net.minecraft.entity.EquipmentSlot;
import net.minecraft.item.ArmorItem;
import net.minecraft.item.ItemStack;
import net.minecraft.registry.entry.RegistryEntry;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.biome.Biome;
import net.minecraft.server.world.ServerWorld;

/**
 * Pure functions that compute how the warmth scale changes for a given player
 * each logic tick. The ticker calls {@link #computeWarmthDelta(ServerPlayerEntity)}
 * and applies the returned value (in warmth units per second).
 */
public final class WarmthLogic {
    private WarmthLogic() {}

    public static final float MAX_WARMTH = 100.0f;
    public static final float HALF_WARMTH = 50.0f;

    /** Logic runs once every TICK_INTERVAL ticks. 20 == once per second. */
    public static final int TICK_INTERVAL = 20;

    /** Frozen-damage interval (in logic ticks of {@link #TICK_INTERVAL}). */
    public static final int DAMAGE_INTERVAL_SECONDS = 2;
    public static final float DAMAGE_AMOUNT = 1.0f; // 0.5 hearts

    // Base rates per second (positive == warming, negative == cooling)
    private static final float BASE_NIGHT_COOL = -1.6f;
    private static final float BASE_DAY_OUTDOOR_NEUTRAL = 0.0f;
    private static final float SUN_WARM_BONUS = 0.7f;
    private static final float COLD_BIOME_EXTRA = -1.4f;
    private static final float WARM_BIOME_BONUS = 0.4f;
    private static final float RAIN_PENALTY = -0.6f;
    private static final float WATER_PENALTY = -1.2f;
    private static final float UNDERGROUND_COOL = -0.4f;
    private static final float SHELTER_HOUSE_REGEN = 1.2f;
    private static final float SHELTER_DIRT_HOLE_PENALTY = -0.2f; // dirt holes are not real shelter

    public static float computeWarmthDelta(ServerPlayerEntity player) {
        ServerWorld world = player.getServerWorld();
        BlockPos pos = player.getBlockPos();
        BlockPos head = pos.up();

        // 1. Environmental heat sources scan (lava / fire / campfire / etc.)
        float heatGain = HeatSources.computeHeatGain(world, head);

        // 2. Time-of-day / sky exposure
        boolean canSeeSky = world.isSkyVisible(head);
        boolean isNight = !world.isDay();
        boolean isThundering = world.isThundering();

        float environmentalDelta;
        if (canSeeSky) {
            if (isNight) {
                environmentalDelta = BASE_NIGHT_COOL;
            } else if (isThundering) {
                environmentalDelta = BASE_NIGHT_COOL * 0.6f;
            } else {
                environmentalDelta = BASE_DAY_OUTDOOR_NEUTRAL + SUN_WARM_BONUS;
            }
        } else {
            // Indoors / underground — depends on shelter quality
            ShelterDetector.ShelterQuality q = ShelterDetector.evaluate(world, pos);
            switch (q) {
                case PROPER_HOUSE -> environmentalDelta = SHELTER_HOUSE_REGEN;
                case DIRT_HOLE -> environmentalDelta = SHELTER_DIRT_HOLE_PENALTY;
                case OPEN_AIR_OR_NONE -> environmentalDelta = UNDERGROUND_COOL;
                default -> environmentalDelta = UNDERGROUND_COOL;
            }
        }

        // 3. Biome temperature
        RegistryEntry<Biome> biomeEntry = world.getBiome(pos);
        Biome biome = biomeEntry.value();
        float biomeTemp = biome.getTemperature();
        float biomeDelta;
        if (biomeTemp <= 0.0f) {
            biomeDelta = COLD_BIOME_EXTRA;
        } else if (biomeTemp < 0.3f) {
            biomeDelta = COLD_BIOME_EXTRA * 0.5f;
        } else if (biomeTemp > 1.0f) {
            biomeDelta = WARM_BIOME_BONUS;
        } else {
            biomeDelta = 0.0f;
        }

        // 4. Weather / water
        float weatherDelta = 0.0f;
        if (world.isRaining() && canSeeSky && biomeTemp > 0.15f) {
            weatherDelta += RAIN_PENALTY;
        }
        if (player.isSubmergedInWater() || player.isInsideWaterOrBubbleColumn()) {
            weatherDelta += WATER_PENALTY;
        }

        // 5. Sum cold / warm components separately so armor only slows cooling.
        float coolingComponent = Math.min(0.0f, environmentalDelta + biomeDelta + weatherDelta);
        float warmingComponent = Math.max(0.0f, environmentalDelta + biomeDelta + weatherDelta);

        // Armor insulation only mitigates cooling; it doesn't amplify warming.
        float insulation = computeArmorInsulation(player);
        coolingComponent *= (1.0f - insulation);

        // 6. Total = heatGain (always positive) + warming + (mitigated) cooling
        return heatGain + warmingComponent + coolingComponent;
    }

    /**
     * Insulation in [0, 0.85]. Each armor piece contributes; leather contributes
     * more than other materials to encourage building cold-weather gear.
     */
    public static float computeArmorInsulation(ServerPlayerEntity player) {
        float total = 0.0f;
        for (EquipmentSlot slot : EquipmentSlot.values()) {
            if (slot.getType() != EquipmentSlot.Type.ARMOR) continue;
            ItemStack stack = player.getEquippedStack(slot);
            if (stack.isEmpty()) continue;
            if (!(stack.getItem() instanceof ArmorItem armor)) continue;
            String matName = armor.getMaterial().getName(); // e.g. "leather", "iron", "netherite"
            float pieceInsulation = switch (matName) {
                case "leather" -> 0.22f;
                case "netherite" -> 0.18f;
                case "gold" -> 0.10f;
                case "iron" -> 0.13f;
                case "chainmail" -> 0.12f;
                case "diamond" -> 0.14f;
                case "turtle" -> 0.10f;
                default -> 0.10f;
            };
            total += pieceInsulation;
        }
        return Math.min(0.85f, total);
    }
}
