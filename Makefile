all : flash

TARGET:=bsidesdsmbadge
TARGET_MCU:=CH585
TARGET_MCU_PACKAGE:=CH585M

override GENERATED_LD_FILE:=generated_$(TARGET_MCU_PACKAGE)_$(TARGET_MCU_MEMORY_SPLIT).ld
override LINKER_SCRIPT:=$(GENERATED_LD_FILE)

CH32FUN_MK:=~/src/ch32fun/ch32fun/ch32fun.mk
ifeq ($(wildcard $(CH32FUN_MK)),)
CH32FUN_MK:=~/src/ch32fun/ch32fun/ch32fun.mk
endif

include $(CH32FUN_MK)

flash : cv_flash
clean : cv_clean
