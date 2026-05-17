package com.damirlukash.warmth;

/**
 * Duck-type interface implemented by PlayerEntity via mixin so the rest of the
 * mod can read and mutate per-player warmth state without an extra component
 * system. All accessors are prefixed with "warmth$" to avoid clashing with any
 * vanilla or other-mod fields.
 */
public interface WarmthHolder {
    float warmth$getWarmth();

    void warmth$setWarmth(float value);

    boolean warmth$isDamaging();

    void warmth$setDamaging(boolean damaging);

    int warmth$getDamageCounter();

    void warmth$setDamageCounter(int counter);
}
