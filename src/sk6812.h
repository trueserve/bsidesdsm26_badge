#ifndef __SK6812_H
#define __SK6812_H



#if SK6812_PROFILE == 1
#ifndef SK6812_T0H_NOPS
#define SK6812_T0H_NOPS 2
#endif
#ifndef SK6812_T0L_NOPS
#define SK6812_T0L_NOPS 24
#endif
#ifndef SK6812_T1H_NOPS
#define SK6812_T1H_NOPS 6
#endif
#ifndef SK6812_T1L_NOPS
#define SK6812_T1L_NOPS 14
#endif
#elif SK6812_PROFILE == 3
#ifndef SK6812_T0H_NOPS
#define SK6812_T0H_NOPS 4
#endif
#ifndef SK6812_T0L_NOPS
#define SK6812_T0L_NOPS 22
#endif
#ifndef SK6812_T1H_NOPS
#define SK6812_T1H_NOPS 10
#endif
#ifndef SK6812_T1L_NOPS
#define SK6812_T1L_NOPS 12
#endif
#elif SK6812_PROFILE == 4
#ifndef SK6812_T0H_NOPS
#define SK6812_T0H_NOPS 30
#endif
#ifndef SK6812_T0L_NOPS
#define SK6812_T0L_NOPS 80
#endif
#ifndef SK6812_T1H_NOPS
#define SK6812_T1H_NOPS 70
#endif
#ifndef SK6812_T1L_NOPS
#define SK6812_T1L_NOPS 40
#endif
#elif SK6812_PROFILE == 5
#ifndef SK6812_T0H_NOPS
#define SK6812_T0H_NOPS 0
#endif
#ifndef SK6812_T0L_NOPS
#define SK6812_T0L_NOPS 40
#endif
#ifndef SK6812_T1H_NOPS
#define SK6812_T1H_NOPS 12
#endif
#ifndef SK6812_T1L_NOPS
#define SK6812_T1L_NOPS 28
#endif
#elif SK6812_PROFILE == 2
#ifndef SK6812_T0H_NOPS
#define SK6812_T0H_NOPS 8
#endif
#ifndef SK6812_T0L_NOPS
#define SK6812_T0L_NOPS 18
#endif
#ifndef SK6812_T1H_NOPS
#define SK6812_T1H_NOPS 22
#endif
#ifndef SK6812_T1L_NOPS
#define SK6812_T1L_NOPS 10
#endif
#else
#ifndef SK6812_T0H_NOPS
#define SK6812_T0H_NOPS 6
#endif
#ifndef SK6812_T0L_NOPS
#define SK6812_T0L_NOPS 20
#endif
#ifndef SK6812_T1H_NOPS
#define SK6812_T1H_NOPS 16
#endif
#ifndef SK6812_T1L_NOPS
#define SK6812_T1L_NOPS 10
#endif
#endif

#define SK6812__ADD_N_NOPS(n) asm volatile( ".rept " #n "\nc.nop\n.endr" );
#define SK6812_ADD_N_NOPS(n)  SK6812__ADD_N_NOPS(n)

struct RGBW {
	uint8_t g; // 0
	uint8_t r; // 1
	uint8_t b; // 2
	uint8_t w; // 3
} RGBW;



#endif /* __SK6812_H */