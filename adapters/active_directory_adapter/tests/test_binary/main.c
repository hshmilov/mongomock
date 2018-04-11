#include <stdio.h>

int main(int argc, const char * const argv[]) {
    if (argc == 1) {
        printf("Did not get any paramters!\n");
        return -1;
    }
    
    for (int i = 1; i < argc; i++) {
        printf("param %d: %s\n", i, argv[i]);
    }

    return 0;
}