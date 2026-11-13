all : flash

TARGET:=bsidesdsmbadge
TARGET_MCU:=CH585
TARGET_MCU_PACKAGE:=CH585M

override GENERATED_LD_FILE:=generated_$(TARGET_MCU_PACKAGE)_$(TARGET_MCU_MEMORY_SPLIT).ld
override LINKER_SCRIPT:=$(GENERATED_LD_FILE)

# Prefer the xpack riscv-none-elf toolchain (ships with newlib) if installed.
# The Homebrew riscv64-elf-gcc is bare-metal and lacks the C library headers.
# Use the absolute path as PREFIX so the build does not depend on PATH.
XPACK_RISCV_BIN:=$(firstword $(wildcard $(HOME)/Library/xPacks/@xpack-dev-tools/riscv-none-elf-gcc/*/.content/bin))
ifneq ($(XPACK_RISCV_BIN),)
PREFIX?=$(XPACK_RISCV_BIN)/riscv-none-elf
endif

CH32FUN_MK:=ch32fun/ch32fun/ch32fun.mk
ifeq ($(wildcard $(CH32FUN_MK)),)
CH32FUN_MK:=~/src/ch32fun/ch32fun/ch32fun.mk
endif

include $(CH32FUN_MK)

flash : cv_flash
clean : cv_clean
