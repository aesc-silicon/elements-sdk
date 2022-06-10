#include "soc.h"
#include "uart.h"
#include "gpio.h"
#include "mtimer.h"
#include "i2c.h"
#include "plic.h"

#define PLIC_BASE	0xF00F0000

extern void hang(void);
extern void timer_enable(void);
extern void timer_disable(void);
extern void interrupt_enable(void);
extern void interrupt_disable(void);

static struct uart_driver uartStd;
/*
void isr_handle(unsigned int mcause)
{
	unsigned char chr;

	interrupt_disable();
	if (uart_irq_rx_ready(&uartStd)) {
		uart_irq_rx_disable(&uartStd);

		while (uart_getc(&uartStd, &chr) == 0) {
			uart_putc(&uartStd, chr);
		}

		uart_irq_rx_enable(&uartStd);
	}

	interrupt_enable();
}
*/
void _kernel(void)
{
	unsigned char prompt[4] = ">_ \0";

	struct plic_driver plic;

	plic_init(&plic, PLIC_BASE);
	uart_init(&uartStd, UARTSTDCTRL_BASE,
		UART_CALC_FREQUENCY(UARTSTDCTRL_FREQ, UARTSTDCTRL_BAUD, 8));

	interrupt_enable();
	plic_irq_enable(&plic, 2);
	uart_irq_rx_enable(&uartStd);

	uart_puts(&uartStd, prompt);




/*
	unsigned char response[2];

	struct gpio_driver gpioStatus;
	struct mtimer_driver mtimer;
	struct i2c_driver i2cA;
*/


//	mtimer_init(&mtimer, MTIMERCTRL_BASE);
//	gpio_init(&gpioStatus, GPIOSTATUSCTRL_BASE);
//	i2c_init(&i2cA, I2CCONTROLLERACTRL_BASE,
//		I2C_CALC_CLOCK(I2CCONTROLLERACTRL_FREQ, I2C_SPEED_STANDARD));


//	i2c_read(&i2cA, 0x49, 0x0, 2, response);


	hang();
}
