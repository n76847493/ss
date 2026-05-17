package com.damirlukash.warmth.client;

import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;

/** Holds the last warmth values received from the server for HUD rendering. */
@Environment(EnvType.CLIENT)
public final class ClientWarmthState {
    private ClientWarmthState() {}

    public static volatile float warmth = 100.0f;
    public static volatile float max = 100.0f;
    public static volatile boolean hasData = false;
}
