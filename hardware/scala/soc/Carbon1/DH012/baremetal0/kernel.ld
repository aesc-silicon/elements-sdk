/* Specify the memory areas */

MEMORY
{
	BOOTROM (xr ): ORIGIN = 0xA0000000, LENGTH = 4K
	OCRAM   (xrw): ORIGIN = 0x80000000, LENGTH = 512
}

stack_size = 512;
heap_size = 0;

/* define beginning and ending of stack */

_stack_start = ORIGIN(OCRAM) + LENGTH(OCRAM);
_stack_end = _stack_start - stack_size;

SECTIONS {

	.init : {
		*(.init)
	} > BOOTROM

	.text : {
		*(.text)
	} > BOOTROM

	.irs_handler : {
		*(.irs_handler)
	} > BOOTROM

	.rodata : {
		*(.rodata)
	} > BOOTROM

	.data : {
		*(.data)
	} > OCRAM

	COMMON : {
		*(COMMON)
	}

	/DISCARD/ : {
		*(*)
	}
}
