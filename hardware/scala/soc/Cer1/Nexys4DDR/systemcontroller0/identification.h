#ifndef IDENTIFICATION_HEADER
#define IDENTIFICATION_HEADER

struct chiplet_block {
	int arch_id;
	short service_mask;
	char blocks;
	char routes;
	short chiplet_id;
};

struct memory_block {
	char driver;
	int data[128];
};

struct peripheral {
	long long name;
	long long base_address;
	long long page_count;
};

struct peripheral_block {
	int count;
	struct peripheral peripherals[32];
};

struct computing_block {
	char cpu_arch;
	int  cpu_info;
};

struct service_block {
	char type;
	union {
		struct memory_block memory;
		struct peripheral_block peripheral;
		struct computing_block computing;
	} service;
};

struct partition_block {
	long long base_address;
	long long page_count;
	short chiplet_id;
	char permission;
};

struct translation_block {
	long long physical_addr;
	long long virtual_addr;
	char page_size;
};

struct interrupt_block {
	short chiplet_id;
	char physical_line;
	char virtual_line;
};

struct info_block {
	char type;
	union {
		struct service_block service;
		struct partition_block partition;
		struct translation_block translation;
		struct interrupt_block interrupt;
	} block;
};

char id_get_api();
int *id_get_signature();
short id_chiplet_count();
short *id_chiplet_ids();
short id_get_chiplet_id(int index);

struct chiplet_block* id_get_chiplet_block(short chiplet_id);
struct info_block* id_get_info_blocks(short chiplet_id);

#endif
