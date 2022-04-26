/* Specify the memory areas */

MEMORY
{
	OCRAM   (xrw): ORIGIN = 0xF0000000, LENGTH = 32K
}

stack_size = 16K;
heap_size = 0;

/* define beginning and ending of stack */

_stack_start = ORIGIN(OCRAM) + LENGTH(OCRAM);
_stack_end = _stack_start - stack_size;

SECTIONS {

	.init : {
		*(.init)
	} > OCRAM

	.text : {
		*(.text)
	} > OCRAM

	.irs_handler : {
		*(.irs_handler)
	} > OCRAM

	.rodata : {
		*(.rodata)
	} > OCRAM

	.sdata : {
		*(.sdata)
	} > OCRAM

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
