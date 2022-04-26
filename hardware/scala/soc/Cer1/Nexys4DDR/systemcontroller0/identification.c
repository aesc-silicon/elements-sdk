#include "identification.h"

#define ENABLE_NORTH		0x1 << 3
#define ENABLE_EAST		0x1 << 2
#define ENABLE_SOUTH		0x1 << 1
#define ENABLE_WEST		0x1 << 0

#define CHIPLET_ID_X(x)		((x & 0x1F) << 5)
#define CHIPLET_ID_Y(y)		((y & 0x1F) << 0)

#define CORE_ID_X(x)		((x & 0x3) << 2)
#define CORE_ID_Y(y)		((y & 0x3) << 0)

#define PERMISSION_R		0x4
#define PERMISSION_W		0x2
#define PERMISSION_X		0x1
#define PERMISSION_RWX		(PERMISSION_R | PERMISSION_W | PERMISSION_X)
#define PERMISSION_RW		(PERMISSION_R | PERMISSION_W)

#define PAGE_TYPE_4KB		(0 & 0x7)
#define PAGE_TYPE_64KB		(1 & 0x7)
#define PAGE_TYPE_2MB		(2 & 0x7)
#define PAGE_TYPE_4MB		(3 & 0x7)
#define PAGE_TYPE_1GB		(4 & 0x7)
#define PAGE_TYPE_1TB		(5 & 0x7)
#define PAGE_TYPE_ID		(6 & 0x7)

#define SERVICE_COMPUTING	1 << 0
#define SERVICE_VMEMORY		1 << 1
#define SERVICE_NVMEMORY	1 << 2
#define SERVICE_PERIPHERAL	1 << 3


#define CHIPLET_ID_SYSC		(CHIPLET_ID_X(0) | CHIPLET_ID_Y(0))
#define CHIPLET_ID_COMPa	(CHIPLET_ID_X(1) | CHIPLET_ID_Y(0))
#define CHIPLET_ID_COMPb	(CHIPLET_ID_X(2) | CHIPLET_ID_Y(0))
#define CHIPLET_ID_PERIa	(CHIPLET_ID_X(1) | CHIPLET_ID_Y(1))

#define CORE_ID_SYSC		(CORE_ID_X(0) | CORE_ID_Y(0))
#define CORE_ID_COMPa		(CORE_ID_X(1) | CORE_ID_Y(0))
#define CORE_ID_COMPb		(CORE_ID_X(2) | CORE_ID_Y(0))
#define CORE_ID_PERIa		(CORE_ID_X(1) | CORE_ID_Y(1))

static char api_version = 1;

static int signature[] = {1, 0, 0, 0, 0, 0, 0, 0};

static int chiplet_count = 4;
static short chiplet_ids[] = {
	CHIPLET_ID_SYSC, CHIPLET_ID_COMPa, CHIPLET_ID_COMPb, CHIPLET_ID_PERIa
};
static struct chiplet_block chiplet_blocks[] = {
	{
		.arch_id = 0xcafecafe,
		.service_mask = SERVICE_VMEMORY,
		.blocks = 3,
		.routes = ENABLE_EAST,
		.chiplet_id = CORE_ID_SYSC
	},
	{
		.arch_id = 0xcafecafe,
		.service_mask = SERVICE_COMPUTING,
		.blocks = 3,
		.routes = ENABLE_NORTH | ENABLE_EAST | ENABLE_WEST,
		.chiplet_id = CORE_ID_COMPa
	},
	{
		.arch_id = 0xcafebabe,
		.service_mask = SERVICE_COMPUTING,
		.blocks = 3,
		.routes = ENABLE_WEST,
		.chiplet_id = CORE_ID_COMPb
	},
	{
		.arch_id = 0xcafecafe,
		.service_mask = SERVICE_PERIPHERAL,
		.blocks = 4,
		.routes = ENABLE_SOUTH,
		.chiplet_id = CORE_ID_PERIa
	}
};

static struct info_block systemcontroller[] = {
	{
		.type = 'S',
		.block.service = {
			.type = 'M',
			.service.memory = {
				.driver = 1
			}
		}
	},
	{
		.type = 'P',
		.block.partition = {
			.base_address = 0x0000000000000000,
			.page_count = 0x0000000000010000,
			.chiplet_id = CHIPLET_ID_COMPa,
			.permission = PERMISSION_RWX
		}
	},
	{
		.type = 'P',
		.block.partition = {
			.base_address = 0x0000000000010000,
			.page_count = 0x0000000000020000,
			.chiplet_id = CHIPLET_ID_COMPb,
			.permission = PERMISSION_RWX
		}
	}
};

static struct info_block computingA[] = {
	{
		.type = 'S',
		.block.service = {
			.type = 'C',
			.service.computing = {
				.cpu_arch = 0x1,
				.cpu_info = 0x2
			}
		}
	},
	{
		.type = 'T',
		.block.translation = {
			.physical_addr = 0x0,
			.virtual_addr = 0x0,
			.page_size = PAGE_TYPE_64KB
		}
	},
	{
		.type = 'T',
		.block.translation = {
			.physical_addr = 0x0000000001010000,
			.virtual_addr = 0x0840000000000000,
			.page_size = PAGE_TYPE_4KB
		}
	}
};

static struct info_block computingB[] = {
	{
		.type = 'S',
		.block.service = {
			.type = 'C',
			.service.computing = {
				.cpu_arch = 0x1,
				.cpu_info = 0x2
			}
		}
	},
	{
		.type = 'T',
		.block.translation = {
			.physical_addr = 0x0,
			.virtual_addr = 0x0000000000010000,
			.page_size = PAGE_TYPE_64KB
		}
	},
	{
		.type = 'T',
		.block.translation = {
			.physical_addr = 0x0000000001010000,
			.virtual_addr = 0x0840000000010000,
			.page_size = PAGE_TYPE_4KB
		}
	}
};

static struct info_block peripheralA[] = {
	{
		.type = 'S',
		.block.service = {
			.type = 'P',
			.service.peripheral = {
				.count = 2,
				.peripherals = {
					{
						.name = 0x2020206770696F30,
						.base_address = 0x00000,
						.page_count = 1
					},
					{
						.name = 0x2020206770696F31,
						.base_address = 0x10000,
						.page_count = 1
					}
				}
			}
		}
	},
	{
		.type = 'P',
		.block.partition = {
			.base_address = 0x0000000000000000,
			.page_count = 0x0000000000020000,
			.chiplet_id = CHIPLET_ID_SYSC,
			.permission = PERMISSION_RW
		}
	},
	{
		.type = 'P',
		.block.partition = {
			.base_address = 0x0000000000000000,
			.page_count = 0x0000000000010000,
			.chiplet_id = CHIPLET_ID_COMPa,
			.permission = PERMISSION_RW
		}
	},
	{
		.type = 'P',
		.block.partition = {
			.base_address = 0x0000000000010000,
			.page_count = 0x0000000000020000,
			.chiplet_id = CHIPLET_ID_COMPb,
			.permission = PERMISSION_RW
		}
	}
};

static struct info_block *info_blocks[] = {
	systemcontroller,
	computingA,
	computingB,
	peripheralA
};

char id_get_api() {
	return api_version;
}

int *id_get_signature() {
	return signature;
}
short id_chiplet_count() {
	return chiplet_count;
}

short *id_chiplet_ids() {
	return chiplet_ids;
}

static int check_chiplet_id(short chiplet_id) {
	int index;

	for (index = 0; index < chiplet_count; index++) {
		if (chiplet_id == chiplet_ids[index]) {
			return index;
		}
	}

	return -1;
}

short id_get_chiplet_id(int index) {
	if (index > chiplet_count)
		return -1;

	return chiplet_ids[index];
}

struct chiplet_block* id_get_chiplet_block(short chiplet_id) {
	int index = check_chiplet_id(chiplet_id);
	if (index == -1)
		return 0;

	return &chiplet_blocks[index];
}

struct info_block* id_get_info_blocks(short chiplet_id) {
	int index = check_chiplet_id(chiplet_id);
	if (index == -1)
		return 0;

	return info_blocks[index];
}
