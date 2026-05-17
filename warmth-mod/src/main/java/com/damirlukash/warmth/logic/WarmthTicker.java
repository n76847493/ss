package com.damirlukash.warmth.logic;

import com.damirlukash.warmth.WarmthHolder;
import com.damirlukash.warmth.networking.WarmthNetworking;
import net.minecraft.entity.damage.DamageSource;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;

/**
 * Drives the warmth simulation on the server. Called every world tick by
 * {@code ServerTickEvents.END_WORLD_TICK}; only runs the heavy logic every
 * {@link WarmthLogic#TICK_INTERVAL} ticks (1 second by default).
 */
public final class WarmthTicker {
    private WarmthTicker() {}

    private static int tickCounter = 0;

    public static void onWorldTick(ServerWorld world) {
        tickCounter++;
        if (tickCounter % WarmthLogic.TICK_INTERVAL != 0) {
            return;
        }
        // Reset to keep numbers small.
        if (tickCounter > 1_000_000) tickCounter = 0;

        for (ServerPlayerEntity player : world.getPlayers()) {
            tickPlayer(player);
        }
    }

    private static void tickPlayer(ServerPlayerEntity player) {
        if (!player.isAlive()) return;
        if (player.isCreative() || player.isSpectator()) {
            // Keep warmth maxed in creative / spectator so HUD looks normal if they switch back.
            WarmthHolder holder = (WarmthHolder) player;
            holder.warmth$setWarmth(WarmthLogic.MAX_WARMTH);
            holder.warmth$setDamaging(false);
            WarmthNetworking.sendToClient(player, WarmthLogic.MAX_WARMTH, WarmthLogic.MAX_WARMTH);
            return;
        }

        WarmthHolder holder = (WarmthHolder) player;
        float warmth = holder.warmth$getWarmth();
        float delta = WarmthLogic.computeWarmthDelta(player);
        warmth += delta;
        if (warmth < 0.0f) warmth = 0.0f;
        if (warmth > WarmthLogic.MAX_WARMTH) warmth = WarmthLogic.MAX_WARMTH;
        holder.warmth$setWarmth(warmth);

        // Damaging state machine — once at zero, the player keeps losing HP
        // until warmth comes back up to half.
        boolean damaging = holder.warmth$isDamaging();
        if (warmth <= 0.0f) damaging = true;
        if (warmth >= WarmthLogic.HALF_WARMTH) damaging = false;
        holder.warmth$setDamaging(damaging);

        if (damaging) {
            int counter = holder.warmth$getDamageCounter();
            counter++;
            if (counter >= WarmthLogic.DAMAGE_INTERVAL_SECONDS) {
                applyFrostDamage(player);
                counter = 0;
            }
            holder.warmth$setDamageCounter(counter);
        } else {
            holder.warmth$setDamageCounter(0);
        }

        WarmthNetworking.sendToClient(player, warmth, WarmthLogic.MAX_WARMTH);
    }

    private static void applyFrostDamage(ServerPlayerEntity player) {
        DamageSource src = player.getDamageSources().freeze();
        player.damage(src, WarmthLogic.DAMAGE_AMOUNT);
    }
}
