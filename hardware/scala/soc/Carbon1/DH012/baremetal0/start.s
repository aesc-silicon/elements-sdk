.equ REGBYTES, 0x4

.section .init
.global hang
.global timer_enable
.global timer_disable
.global interrupt_enable
.global interrupt_disable
_head:
	jal	_init_regs
	jal	_init_bss
	li	sp, 0x80000200
	jal	_init_trap

	j	_kernel
	nop


hang:
	nop
	beq	zero, zero, hang


_init_regs:
	li	x2 , 0xA2A2A2A2
	li	x3 , 0xA3A3A3A3
	li	x4 , 0xA4A4A4A4
	li	x5 , 0xA5A5A5A5
	li	x6 , 0xA6A6A6A6
	li	x7 , 0xA7A7A7A7
	li	x8 , 0xA8A8A8A8
	li	x9 , 0xA9A9A9A9
	li	x10, 0xB0B0B0B0
	li	x11, 0xB1B1B1B1
	li	x12, 0xB2B2B2B2
	li	x13, 0xB3B3B3B3
	li	x14, 0xB4B4B4B4
	li	x15, 0xB5B5B5B5
	li	x16, 0xB6B6B6B6
	li	x17, 0xB7B7B7B7
	li	x18, 0xB8B8B8B8
	li	x19, 0xB9B9B9B9
	li	x20, 0xC0C0C0C0
	li	x21, 0xC1C1C1C1
	li	x22, 0xC2C2C2C2
	li	x23, 0xC3C3C3C3
	li	x24, 0xC4C4C4C4
	li	x25, 0xC5C5C5C5
	li	x26, 0xC6C6C6C6
	li	x27, 0xC7C7C7C7
	li	x28, 0xC8C8C8C8
	li	x29, 0xC9C9C9C9
	li	x30, 0xD0D0D0D0
	li	x31, 0xD1D1D1D1
	ret


_init_bss:
	la	t0, __bss_start
	la	t1, __bss_end
loop_head:
	sw	zero, 0(t0)
	beq	t0, t1, loop_end
	addi	t0, t0, 4
	j	loop_head
loop_end:
	ret
	nop


_init_trap:
	la	t0, _irq_wrapper
	csrw	mtvec, t0
	ret


_irq_wrapper:
	add	sp, sp, -12*REGBYTES
	sw	a0, 1*REGBYTES(sp)
	sw	ra, 2*REGBYTES(sp)
	sw	t0, 3*REGBYTES(sp)

	csrr	a0, mcause
	jal	isr_handle

	lw	a0, 1*REGBYTES(sp)
	lw	ra, 2*REGBYTES(sp)
	lw	t0, 3*REGBYTES(sp)
	addi	sp, sp, 12*REGBYTES
	mret

isr_handle:
	# disable rx irq
	li	t0, 0xf0000000
	sw	zero, 20(t0)

loop_s:
	lw	a0, 0(t0)
	mv	t0, a0
	srli	a0, a0, 16
	beq	a0, zero, loop_e
	mv	a0, t0
	li	t0, 0xf0000000
	sw	a0, 0(t0)
	beq	zero, zero, loop_s

loop_e:
	# enable rx irq
	li	t0, 0xf0000000
	li	a0, 0x2
	sw	a0, 16(t0)
	sw	a0, 20(t0)
	# claim irq
	li	t0, 0xf00ff000
	li	a0, 2
	sw	a0, 4(t0)
	ret


timer_enable:
	csrr	a0, mie
	ori	a0, a0, 0x80
	csrw	mie, a0
	ret

timer_disable:
	csrr	a0, mie
	xori	a0, a0, 0x80
	csrw	mie, a0
	ret

interrupt_enable:
	csrr	a0, mie
	li	a1, 0x800
	or	a0, a0, a1
	csrw	mie, a0
	csrr	a0, mstatus
	ori	a0, a0, 0x8
	csrw	mstatus, a0
	ret

interrupt_disable:
	csrr	a0, mie
	li	a1, 0x800
	xor	a0, a0, a1
	csrw	mie, a0
	csrr	a0, mstatus
	xori	a0, a0, 0x8
	csrw	mstatus, a0
	ret
