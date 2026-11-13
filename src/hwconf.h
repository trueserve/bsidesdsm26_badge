#ifndef __HWCONF_H
#define __HWCONF_H



#ifndef ENABLE_PB8_STATUS_LED
#define ENABLE_PB8_STATUS_LED 0
#endif

#if ENABLE_PB8_STATUS_LED
#define LED PB8
#endif

#ifndef STATUS_SK6812_PIN
#define STATUS_SK6812_PIN PB6
#endif

#ifndef SK6812_DISABLE
#define SK6812_DISABLE 0
#endif

#ifndef SK6812_PROFILE
#define SK6812_PROFILE 5
#endif

#ifndef SK6812_LSB_FIRST
#define SK6812_LSB_FIRST 0
#endif

#ifndef SK6812_IS_RGBW
#define SK6812_IS_RGBW 0
#endif

#ifndef SK6812_BRIGHT
#define SK6812_BRIGHT 24
#endif

#ifndef SK6812_W_BRIGHT
#define SK6812_W_BRIGHT 0
#endif

#define IDLE_RESUME_DELAY_MS 5000u
#define IDLE_RAINBOW_DURATION_MS 12000u
#define IDLE_EFFECT_DURATION_MS 9000u
#define IDLE_FRAME_INTERVAL_MS 75u

// --- BUT1 (PB23) gesture + marquee mode ------------------------------------
#define BTN_DEBOUNCE_MS        15u   // raw level must be stable this long
#define BTN_TAP_MAX_MS         400u  // press shorter than this counts as a tap
#define BTN_HOLD_MS            800u  // press-and-hold threshold (toggle marquee)
#define MARQUEE_DEFAULT_BPM    10u
#define MARQUEE_MIN_BPM        10u
#define MARQUEE_MAX_BPM        300u
#define MARQUEE_TAP_TIMEOUT_MS 8000u // taps farther apart than this restart tempo
#define MARQUEE_LED_COUNT      4u    // physical SK6812 pixels on the strip
#define MARQUEE_FRAME_MS       16u   // cap LED hardware writes at ~60 fps (keeps USB responsive)

#define AUDIO_OUTPUT_PIN         PB0

#define NOTE_C5 523u
#define NOTE_E5 659u
#define NOTE_G5 784u
#define NOTE_A5 880u

#define R8_NFC_CMD                    (*(vu8*)0x4000E000)
#define  RB_NFC_ANTENNA_ON            0x4
#define R8_NFC_STATUS                 (*(vu8*)0x4000E001)
#define R16_NFC_INTF_STATUS           (*(vu16*)0x4000E004)
#define R16_NFC_RXTX_LEN              (*(vu16*)0x4000E008)
#define R16_NFC_FIFO                  (*(vu16*)0x4000E00C)
#define R16_NFC_TMR                   (*(vu16*)0x4000E010)
#define R32_NFC_DRV                   (*(vu32*)0x4000E014)

#define PLUSMIN_7(t,r)                ((t >> 3) == (r >> 3))
#define PLUSMIN_15(t,r)               ((t >> 4) == (r >> 4))

#define RB_TMR_FREQ_13_56             0x20

#define USB_DATA_BUF_SIZE                        512 // max nfca frame size is 256, add a bit of headroom (could go up to at least 16384)
#define USB_APP_MAX_PAYLOAD                      (USB_DATA_BUF_SIZE - 2) // 2 bytes reserved for length
#define USBFS_MAX_PACKET                         64

// PB8/PB9 are NFC analog pins (NFCM/NFCI) on CH585. Don't enable INTX remap / GPIO interrupts that
// route through PB8/PB9, or NFC reception can break.
#ifndef ENABLE_BOOT_BUTTON
#define ENABLE_BOOT_BUTTON                        0
#endif
#define NFCA_DATA_BUF_SIZE                       256 // we use FSDI 8, so max frame size is 256
#define NFCA_PCD_MAX_SEND_NUM                    NFCA_DATA_BUF_SIZE
#define NFCA_PCD_MAX_RECV_NUM                    NFCA_DATA_BUF_SIZE
#define NFCA_MAX_PARITY_NUM                      NFCA_PCD_MAX_RECV_NUM
#define NFCA_PCD_CHAINING_BUFFERS                4
#define NFCA_PCD_LPCD_THRESHOLD_PERMIL           5
#define NFCA_PCD_LPCD_THRESHOLD_MAX_LIMIT_PERMIL 20
#define NFCA_PCD_WAIT_MAX_MS                     1000
#define NFCA_PCD_TICKS_PER_MILLISECOND           1725

// Debug/bring-up: bypass LPCD gating and always attempt REQA/WUPA.
// This keeps the RF field active during scans and is higher power, but avoids tuning/threshold issues.
#ifndef NFCA_FORCE_ACTIVE_SCAN
#define NFCA_FORCE_ACTIVE_SCAN                   1
#endif

// Optional: drive the NFC_CTR pin (often used in reference designs to improve drive/sensitivity
// or to allow wider-voltage operation via an external resistor network).
// If your board doesn't wire NFC_CTR, enabling this is harmless.
#ifndef NFCA_ENABLE_CTR_PIN
#define NFCA_ENABLE_CTR_PIN                      1
#endif

// Bring-up / weak-antenna assist: force the highest driver strength.
// If you see unstable USB resets or excessive current draw, turn this off.
#ifndef NFCA_FORCE_MAX_DRIVE
#define NFCA_FORCE_MAX_DRIVE                     1
#endif

// Number of quick poll attempts per scan window.
#ifndef NFCA_REQA_RETRIES
#define NFCA_REQA_RETRIES                        5
#endif

// Extra delay after RF field is enabled before polling.
#ifndef NFCA_FIELD_SETTLE_MS
#define NFCA_FIELD_SETTLE_MS                     10
#endif

#define CMD_REQA               0x26
#define CMD_WUPA               0x52
#define CMD_ANTICOLL1          0x93
#define CMD_ANTICOLL2          0x95
#define CMD_ANTICOLL3          0x97
#define CMD_RATS               0xE0
#define CMD_HALT               0x50
#define CMD_IBLOCK             0x02
#define CMD_WTX                0xF2
#define CMD_RBLOCK             0xA0
#define CMD_T2T_GET_VERSION    0x60
#define CMD_T2T_READ           0x30

#define PCD_ANTICOLL_OVER_TIME 10
#define PCD_SELECT_OVER_TIME   10
#define PCD_APDU_OVER_TIME     100
#define PCD_T2T_OVER_TIME      20

#define USB_PKT_NTAG_VERSION   0xA1
#define USB_PKT_NTAG_PAGE_DATA 0xA2
#define USB_PKT_NTAG_DONE      0xA3

#define NTAG21X_VERSION_LEN    8
#define NTAG_T2T_READ_BYTES    16
#define NTAG215_TOTAL_PAGES    135

#define ISO14443A_CHECK_BCC(B)    ((B[0] ^ B[1] ^ B[2] ^ B[3]) == B[4])
// Preserve low NFC_DRV configuration bits when adjusting output drive.
// The original mask (0x9ff) clears bits 9..10 which appear to affect the analog front-end on some boards.
#define NFCA_PCD_SET_OUT_DRV(lvl) (R32_NFC_DRV = ((R32_NFC_DRV & 0x1fff) | lvl))



#endif /* __HWCONF_H */
