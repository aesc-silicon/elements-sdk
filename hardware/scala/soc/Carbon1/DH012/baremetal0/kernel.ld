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

	.rodata : {
		*(.rodata)
	} > BOOTROM

	.bss (NOLOAD) : {
		__bss_start = . ;
		*(.bss*)
		*(COMMON)
		__bss_end = . ;
	} > OCRAM

	.data : {
		*(.data)
	} > OCRAM

	/DISCARD/ : {
		*(*)
	}
}
