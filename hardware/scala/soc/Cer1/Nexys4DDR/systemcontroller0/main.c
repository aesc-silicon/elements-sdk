#include "soc.h"
#include "uart.h"
#include "identification.h"

extern void hang(void);
extern void setup_sys(void (*)(void));

#define ADDR_ID(base, offset)						\
	(((base) + (offset) + (0x10000 / sizeof(unsigned int))))
#define ADDR_PARTITION(base, offset)					\
	(((base) + (offset) + (0x20000 / sizeof(unsigned int))))
#define ADDR_BLOCKAGE(base, offset)					\
	(((base) + (offset) + (0x30000 / sizeof(unsigned int))))
#define ADDR_ROUTER(base, offset)					\
	(((base) + (offset) + (0x40000 / sizeof(unsigned int))))
#define ADDR_EXTENSION(base, offset)					\
	(((base) + (offset) + (0x50000 / sizeof(unsigned int))))
#define ADDR_TRANSLATION(base, offset)					\
	(((base) + (offset) + (0x60000 / sizeof(unsigned int))))

#define PNTR_ID(base, offset)		(*ADDR_ID(base, offset))
#define PNTR_PARTITION(base, offset)	(*ADDR_PARTITION(base, offset))
#define PNTR_BLOCKAGE(base, offset)	(*ADDR_BLOCKAGE(base, offset))
#define PNTR_ROUTER(base, offset)	(*ADDR_ROUTER(base, offset))
#define PNTR_EXTENSION(base, offset)	(*ADDR_EXTENSION(base, offset))
#define PNTR_TRANSLATION(base, offset)	(*ADDR_TRANSLATION(base, offset))

#define LOCK_IP			0x1

#define CORE_ADDR(id)		((unsigned int *)((id << 28) | (1 << 27)))


int set_chiplet_id(volatile unsigned int *address, unsigned int id)
{
	PNTR_ID(address, 1) = id;
	if ((PNTR_ID(address, 1)) != id)
		return 1;
	PNTR_ID(address, 0) = LOCK_IP;
	if ((PNTR_ID(address, 0) & 0x1) == LOCK_IP)
		return 1;
	return 0;
}

int init_router(volatile unsigned int *address, unsigned int directions,
		unsigned int id)
{
	unsigned int config = (directions << 16) | id;
	PNTR_ROUTER(address, 1) = config;
	if ((PNTR_ROUTER(address, 1)) != config)
		return 1;
	PNTR_ROUTER(address, 0) = LOCK_IP;
	if ((PNTR_ROUTER(address, 0) & 0x1) == LOCK_IP)
		return 1;
	return 0;
}

int disable_blockage(volatile unsigned int *address)
{
	PNTR_BLOCKAGE(address, 0) = 0x1;
	if ((PNTR_BLOCKAGE(address, 0) & 0x1) == 0x0)
		return 1;
	return 0;
}

int add_memory_partition(volatile unsigned int *address, int entry,
	unsigned int id, unsigned long long lower, unsigned long long upper,
	unsigned int permission)
{

	unsigned int offset = 1 + (entry * 5);

	// Remove 4kB page because the memory partition ignores these bits.
	lower = lower >> 12;
	upper = upper >> 12;

	PNTR_PARTITION(address, offset + 0) = (unsigned int)lower;
	PNTR_PARTITION(address, offset + 1) = (unsigned int)(lower >> 32);
	PNTR_PARTITION(address, offset + 2) = (unsigned int)upper;
	PNTR_PARTITION(address, offset + 3) = (unsigned int)(upper >> 32);
	PNTR_PARTITION(address, offset + 4) =
		(id << 16) | ((permission & 0xFF) << 8);

	return 1;
}

int lock_memory_partition(volatile unsigned int *address, unsigned int id)
{
	PNTR_PARTITION(address, 0) = (id << 16) | 0x1;

	if ((PNTR_PARTITION(address, 0) & 0x1) == 0x1)
		return 1;
	return 0;
}

int add_memory_extension(volatile unsigned int *address, int entry,
			 short physical, short virtual)
{
	unsigned int value = physical | (virtual << 10);

	PNTR_EXTENSION(address, entry + 1) = value;

	return 1;
}

int lock_memory_extension(volatile unsigned int *address)
{
	PNTR_EXTENSION(address, 0) = 0x1;

	if ((PNTR_EXTENSION(address, 0) & 0x1) == 0x1)
		return 1;
	return 0;
}

int add_memory_translation(volatile unsigned int *address, int entry,
			   unsigned long long physical,
			   unsigned long long virtual,
			   unsigned int page_type)
{

	unsigned int offset = 1 + (entry * 5);

	// Remove 4kB page because the memory translation ignores these bits.
	physical = physical >> 12;
	virtual = virtual >> 12;

	PNTR_TRANSLATION(address, offset + 0) = (unsigned int)physical;
	PNTR_TRANSLATION(address, offset + 1) = (unsigned int)(physical >> 32);
	PNTR_TRANSLATION(address, offset + 2) = (unsigned int)virtual;
	PNTR_TRANSLATION(address, offset + 3) = (unsigned int)(virtual >> 32);
	PNTR_TRANSLATION(address, offset + 4) = (page_type & 0xFF) << 8;

	return 1;
}

int lock_memory_translation(volatile unsigned int *address)
{
	PNTR_TRANSLATION(address, 0) = 0x1;

	if ((PNTR_TRANSLATION(address, 0) & 0x1) == 0x1)
		return 1;
	return 0;
}

void init_chiplet_blocks(short chiplet_id, struct chiplet_block *chiplet_block,
			 struct info_block *info_block,
			 struct uart_driver *uartStd) {

	int j;
	int partition = 0;
	int translation = 0;
	struct partition_block *part;
	struct translation_block *trans;
	unsigned char error[7] = "Error2\0";

	for (j = 0; j < chiplet_block->blocks; j++) {
		switch (info_block[j].type) {
		case 'P':
			part = &info_block[j].block.partition;
			if (!add_memory_partition(CORE_ADDR(chiplet_block->chiplet_id),
						  partition, part->chiplet_id,
						  part->base_address,
						  part->page_count,
						  part->permission)) {
				uart_puts(uartStd, error);
				hang();
			}
			partition++;
			break;
		case 'T':
			trans = &info_block[j].block.translation;
			if (!add_memory_translation(CORE_ADDR(chiplet_block->chiplet_id),
						    translation,
						    trans->physical_addr,
						    trans->virtual_addr,
						    trans->page_size)) {
				uart_puts(uartStd, error);
				hang();
			}
			translation++;
			break;
		default:
			uart_putc(uartStd, 'S');
		}
	}

	if (partition) {
		if (!lock_memory_partition(CORE_ADDR(chiplet_block->chiplet_id),
					   chiplet_id)) {
			uart_puts(uartStd, error);
			hang();
		}
	}


	if (translation) {
		if (!lock_memory_translation(CORE_ADDR(chiplet_block->chiplet_id))) {
			uart_puts(uartStd, error);
			hang();
		}
	}
}


void _kernel(void)
{
	unsigned char prompt[6] = "Start\0";
	unsigned char error1[7] = "Error1\0";
	unsigned char error3[7] = "Error3\0";
	unsigned char finish[7] = "Finish\0";

	int i;
	int chiplet_count;
	short chiplet_id;
	unsigned int *chiplet_addr;
	struct chiplet_block *chiplet_block;
	struct info_block *info_block;
	struct uart_driver uartStd;

	uart_init(&uartStd, UARTSTDCTRL_BASE,
		UART_CALC_FREQUENCY(UARTSTDCTRL_FREQ, UARTSTDCTRL_BAUD, 8));

	uart_puts(&uartStd, prompt);

	/*
	* Step 1
	*   Set Chiplet IDs in all routers and enable active chip-to-chip
	*   connections.
	*/
	chiplet_count = id_chiplet_count();

	for (i = 0; i < chiplet_count; i++) {
		chiplet_id = id_get_chiplet_id(i);
		chiplet_block = id_get_chiplet_block(chiplet_id);
		chiplet_addr = CORE_ADDR(chiplet_block->chiplet_id);

		/* Enable router directions */
		if (!init_router(chiplet_addr, chiplet_block->routes,
				 chiplet_id)) {
			uart_puts(&uartStd, error1);
			hang();
		}

		/* Set chiplet ID */
		if (!set_chiplet_id(chiplet_addr, chiplet_id)) {
			uart_puts(&uartStd, error1);
			hang();
		}
	}

	/* Step 2
	*    Initialize memory partitions + translation and interrupts for
	*    each component one by one.
	*/

	for (i = 0; i < chiplet_count; i++) {
		chiplet_id = id_get_chiplet_id(i);
		chiplet_block = id_get_chiplet_block(chiplet_id);
		info_block = id_get_info_blocks(chiplet_id);

		init_chiplet_blocks(chiplet_id, chiplet_block, info_block,
				    &uartStd);
	}

	/* Step 3
	 *   Disable all blockages to finalize the initialization.
	 */

	for (i = 1; i < chiplet_count; i++) {
		chiplet_id = id_get_chiplet_id(i);
		chiplet_block = id_get_chiplet_block(chiplet_id);
		chiplet_addr = CORE_ADDR(chiplet_block->chiplet_id);

		/* Disable blockages */
		if (!disable_blockage(chiplet_addr)) {
			uart_puts(&uartStd, error3);
			hang();
		}
	}

	uart_puts(&uartStd, finish);
	hang();
}
