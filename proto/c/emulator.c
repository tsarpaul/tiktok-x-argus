#include <unicorn/unicorn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Assuming these are defined somewhere
#define EMU_BASE 0x7babb4b000
#define START_ADDRESS (EMU_BASE + 0x9EB4C)
#define END_ADDRESS (EMU_BASE + 0xA05D8)

// Function to read a file into a buffer
unsigned char *read_file(const char *filename, size_t *length) {
    FILE *file = fopen(filename, "rb");
    if (!file) {
        perror("Error opening file");
        return NULL;
    }

    // Get the size of the file
    fseek(file, 0, SEEK_END);
    *length = ftell(file);
    fseek(file, 0, SEEK_SET);

    // Allocate memory for the file content
    unsigned char *buffer = malloc(*length);
    if (!buffer) {
        perror("Error allocating memory");
        fclose(file);
        return NULL;
    }

    // Read the file into the buffer
    if (fread(buffer, 1, *length, file) != *length) {
        perror("Error reading file");
        fclose(file);
        free(buffer);
        return NULL;
    }

    fclose(file);
    return buffer;
}

typedef struct {
    uc_engine *uc;
    uint64_t base;
    uint64_t start_address;
    uint64_t end_address;
    uint64_t sp;
    uint64_t x0;
    uint64_t x1;
    uint64_t x2;
    uint64_t x3;
    uint64_t x4;
    uint64_t x1_1_address;
    uint64_t x1_2_address;
    uint64_t x1_3_address;
    char *stack;
    char *lib;
} MainEncryptEmulator;

uint64_t kb4_align(uint64_t addr) {
    return (addr + 0xFFF) & 0xFFFFFFFFFFFFF000;
}

uint64_t kb4_round_down(uint64_t addr) {
    return addr & 0xFFFFFFFFFFFFF000;
}

void kb4_prepare(uint64_t *addr, uint64_t *size) {
    *addr = kb4_round_down(*addr);
    *size = kb4_align(*size + 0xFFF);
}

void debugger(uc_engine *uc, uint64_t address, uint32_t size, void *user_data) {
    MainEncryptEmulator *emu = (MainEncryptEmulator *)user_data;

    if (address == END_ADDRESS) {
        // Stop the emulation
        uc_emu_stop(uc);

        // Read memory at x1_3_address
        unsigned char result[16];
        if (uc_mem_read(uc, emu->x1_3_address, result, sizeof(result)) == UC_ERR_OK) {
            printf("Memory at 0x%llx: ", emu->x1_3_address);
            for (int i = 0; i < sizeof(result); i++) {
                printf("%02x ", result[i]);
            }
            printf("\n");
        } else {
            printf("Failed to read memory at 0x%llx\n", emu->x1_3_address);
        }
    }
}

void initialize_emulator(MainEncryptEmulator *emu) {
    // Initialize base, start and end addresses
    emu->base = EMU_BASE; // Example base address
    emu->start_address = START_ADDRESS; // Example start address
    emu->end_address = END_ADDRESS+4; // Example end address

    // read lib and stack and assign to emu
    size_t lib_length, stack_length;
    emu->lib = read_file("dump/libmetasec", &lib_length);
    emu->stack = read_file("dump/stack", &stack_length);

    // Initialize registers
    emu->sp = 0x0000007ba19822c0;
    emu->x0 = 0x0000007babc569b0;
    emu->x1 = 0x0000007ba19822c8;
    emu->x2 = EMU_BASE + 0x9DBEC;
    emu->x3 = 0;
    emu->x4 = 0x0000007ba19822e0;

    // Initialize the Unicorn engine
    if (uc_open(UC_ARCH_ARM64, UC_MODE_ARM, &emu->uc)) {
        fprintf(stderr, "Failed to initialize Unicorn engine!\n");
        exit(-1);
    }

    // Map memory for the executable
    uint64_t exec_size = kb4_align(sizeof(emu->lib));  // Adjust size as per your actual executable size
    uint64_t exec_addr = emu->base;
    kb4_prepare(&exec_addr, &exec_size);
    uc_mem_map(emu->uc, exec_addr, exec_size, UC_PROT_ALL);
    uc_mem_write(emu->uc, exec_addr, emu->lib, sizeof(emu->lib));

    // Map memory for the stack
    uint64_t stack_size = 0x20000; // Example size, adjust as needed
    uint64_t stack_addr = emu->sp - stack_size;
    uc_mem_map(emu->uc, stack_addr, stack_size, UC_PROT_ALL);
    uc_mem_write(emu->uc, stack_addr, emu->stack, sizeof(emu->stack));
}

void setup_registers(MainEncryptEmulator *emu, const unsigned char* key, const unsigned char* protobuf) {
    uc_reg_write(emu->uc, UC_ARM64_REG_SP, &emu->sp);
    uc_reg_write(emu->uc, UC_ARM64_REG_X0, &emu->x0);
    uc_reg_write(emu->uc, UC_ARM64_REG_X1, &emu->x1);
    uc_reg_write(emu->uc, UC_ARM64_REG_X2, &emu->x2);
    uc_reg_write(emu->uc, UC_ARM64_REG_X3, &emu->x3);
    uc_reg_write(emu->uc, UC_ARM64_REG_X4, &emu->x4);

    // Read memory at x1 and unpack into three addresses
    uint64_t val[3];
    if (uc_mem_read(emu->uc, emu->x1, val, sizeof(val)) != UC_ERR_OK) {
        fprintf(stderr, "Failed to read memory at 0x%llx\n", emu->x1);
        exit(-1);
    }
    emu->x1_1_address = val[0];
    emu->x1_2_address = val[1];
    emu->x1_3_address = val[2];

    // Map and write to the memory locations
    uint64_t size1 = 0x1000, size2 = 0x10, size3 = 0x10;
    kb4_prepare(&emu->x1_1_address, &size1);
    uc_mem_map(emu->uc, emu->x1_1_address, size1, UC_PROT_ALL);
    uc_mem_write(emu->uc, emu->x1_1_address, key, size1);

    kb4_prepare(&emu->x1_2_address, &size2);
    uc_mem_map(emu->uc, emu->x1_2_address, size2, UC_PROT_ALL);
    uc_mem_write(emu->uc, emu->x1_2_address, protobuf, size2);

    kb4_prepare(&emu->x1_3_address, &size3);
    uc_mem_map(emu->uc, emu->x1_3_address, size3, UC_PROT_ALL);
}

void run_emulation(const unsigned char *key, const unsigned char *protobuf) {
    MainEncryptEmulator emu;
    uc_err err;

    // Initialize the emulator
    initialize_emulator(&emu);
    setup_registers(&emu, key, protobuf);

    // Start the emulation
    err = uc_emu_start(emu.uc, emu.start_address, emu.end_address, 0, 0);

    // Check for errors
    if (err) {
        fprintf(stderr, "Failed on uc_emu_start() with error returned: %u (%s)\n",
                err, uc_strerror(err));

        // Retrieve and print the program counter and stack pointer
        uint64_t pc;
        uc_reg_read(emu.uc, UC_ARM64_REG_PC, &pc);
        uint64_t sp;
        uc_reg_read(emu.uc, UC_ARM64_REG_SP, &sp);
        fprintf(stderr, "Error at 0x%llx (SP: 0x%llx)\n", pc, sp);

        exit(-1);
    }

    // Clean up
    uc_close(emu.uc);
}

int main() {
    size_t key_length, protobuf_length;
    unsigned char *key = read_file("dump/x1_1", &key_length);
    unsigned char *protobuf = read_file("dump/x1_2", &protobuf_length);

    if (!key || !protobuf) {
        fprintf(stderr, "Failed to read key or protobuf files\n");
        free(key);
        free(protobuf);
        return -1;
    }

    // Process protobuf in chunks of 0x10 bytes
    for (size_t i = 0; i < protobuf_length; i += 0x10) {
        if (memcmp(&protobuf[i], "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 0x10) == 0) {
            break; // Stop if the chunk is all zeros
        }

        run_emulation(key, &protobuf[i]);
    }

    free(key);
    free(protobuf);

    return 0;
}

