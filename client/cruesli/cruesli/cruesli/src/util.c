//
//  util.c
//  cruesli
//
//  Created by Guillaume Prémel on 23/07/2020.
//  Copyright © 2020 Guillaume Prémel. All rights reserved.
//

#include <stdlib.h>
#include <string.h>

#include "safe_malloc.h"
#include "util.h"



char* strconc(char* str1, char* str2){
    unsigned int len = strlen(str1) + strlen(str2) + 1;
    char* ptr = NULL;
    
    ptr = safe_malloc(len*sizeof(char));
    strcpy(ptr, str1);
    strcat(ptr, str2);
    
    return ptr;
}
