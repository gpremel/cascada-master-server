//
//  safe_malloc.c
//  cruesli
//
//  Created by Guillaume Prémel on 23/07/2020.
//  Copyright © 2020 Guillaume Prémel. All rights reserved.
//

#include <stdlib.h>
#include <stdio.h>

#include "safe_malloc.h"


void* safe_malloc(size_t size){
    void* ptr;
    
    ptr = malloc(size);
    if(! ptr){
        printf("Erreur fatale d'allocation\n");
        exit(0);
    }
    
    return ptr;
}


void die(char* message){
    printf("%s", message);
    exit(0);
}
