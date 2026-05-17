package com.damirlukash.warmth.networking;

import com.damirlukash.warmth.WarmthMod;
import io.netty.buffer.Unpooled;
import net.fabricmc.fabric.api.networking.v1.PacketByteBufs;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.network.PacketByteBuf;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.util.Identifier;

/** Sends warmth state from server to client every logic tick. */
public final class WarmthNetworking {
    private WarmthNetworking() {}

    public static final Identifier WARMTH_SYNC = WarmthMod.id("warmth_sync");

    public static void registerCommon() {
        // No server-bound packets yet — placeholder for future input packets.
    }

    public static void sendToClient(ServerPlayerEntity player, float warmth, float max) {
        PacketByteBuf buf = PacketByteBufs.create();
        buf.writeFloat(warmth);
        buf.writeFloat(max);
        ServerPlayNetworking.send(player, WARMTH_SYNC, buf);
    }
}
