package com.damirlukash.warmth.mixin;

import com.damirlukash.warmth.WarmthHolder;
import com.damirlukash.warmth.logic.WarmthLogic;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.nbt.NbtCompound;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(PlayerEntity.class)
public abstract class PlayerEntityWarmthMixin implements WarmthHolder {

    @Unique
    private float warmth$warmth = WarmthLogic.MAX_WARMTH;

    @Unique
    private boolean warmth$damaging = false;

    @Unique
    private int warmth$damageCounter = 0;

    @Override
    public float warmth$getWarmth() {
        return warmth$warmth;
    }

    @Override
    public void warmth$setWarmth(float value) {
        if (value < 0.0f) value = 0.0f;
        if (value > WarmthLogic.MAX_WARMTH) value = WarmthLogic.MAX_WARMTH;
        this.warmth$warmth = value;
    }

    @Override
    public boolean warmth$isDamaging() {
        return warmth$damaging;
    }

    @Override
    public void warmth$setDamaging(boolean damaging) {
        this.warmth$damaging = damaging;
    }

    @Override
    public int warmth$getDamageCounter() {
        return warmth$damageCounter;
    }

    @Override
    public void warmth$setDamageCounter(int counter) {
        this.warmth$damageCounter = counter;
    }

    @Inject(method = "writeCustomDataToNbt", at = @At("RETURN"))
    private void warmth$writeNbt(NbtCompound nbt, CallbackInfo ci) {
        nbt.putFloat("WarmthMod.Warmth", this.warmth$warmth);
        nbt.putBoolean("WarmthMod.Damaging", this.warmth$damaging);
        nbt.putInt("WarmthMod.DamageCounter", this.warmth$damageCounter);
    }

    @Inject(method = "readCustomDataFromNbt", at = @At("RETURN"))
    private void warmth$readNbt(NbtCompound nbt, CallbackInfo ci) {
        if (nbt.contains("WarmthMod.Warmth")) {
            this.warmth$warmth = nbt.getFloat("WarmthMod.Warmth");
        }
        if (nbt.contains("WarmthMod.Damaging")) {
            this.warmth$damaging = nbt.getBoolean("WarmthMod.Damaging");
        }
        if (nbt.contains("WarmthMod.DamageCounter")) {
            this.warmth$damageCounter = nbt.getInt("WarmthMod.DamageCounter");
        }
    }
}
