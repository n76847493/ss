package com.damirlukash.warmth.client;

import com.damirlukash.warmth.networking.WarmthNetworking;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;

@Environment(EnvType.CLIENT)
public class WarmthClient implements ClientModInitializer {
    @Override
    public void onInitializeClient() {
        ClientPlayNetworking.registerGlobalReceiver(WarmthNetworking.WARMTH_SYNC, (client, handler, buf, sender) -> {
            float warmth = buf.readFloat();
            float max = buf.readFloat();
            client.execute(() -> {
                ClientWarmthState.warmth = warmth;
                ClientWarmthState.max = max;
                ClientWarmthState.hasData = true;
            });
        });

        HudRenderCallback.EVENT.register(new WarmthHud());
    }
}
