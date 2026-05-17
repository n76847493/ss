package com.damirlukash.warmth;

import com.damirlukash.warmth.logic.WarmthTicker;
import com.damirlukash.warmth.networking.WarmthNetworking;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.util.Identifier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class WarmthMod implements ModInitializer {
    public static final String MOD_ID = "warmth";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    public static Identifier id(String path) {
        return new Identifier(MOD_ID, path);
    }

    @Override
    public void onInitialize() {
        WarmthNetworking.registerCommon();
        ServerTickEvents.END_WORLD_TICK.register(WarmthTicker::onWorldTick);
        LOGGER.info("[Warmth] mod initialized");
    }
}
