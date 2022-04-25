#include "soc.h"
#include "uart.h"

extern void hang(void);
extern void setup_sys(void (*)(void));

void _kernel(void)
{
	unsigned char prompt[4] = ">_ \0";

	struct uart_driver uartStd;

	uart_init(&uartStd, UARTSTDCTRL_BASE,
		UART_CALC_FREQUENCY(UARTSTDCTRL_FREQ, UARTSTDCTRL_BAUD, 8));

	uart_puts(&uartStd, prompt);

	hang();
}
