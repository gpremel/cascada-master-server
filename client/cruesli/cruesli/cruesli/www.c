//
//  www.c
//  cruesli
//
//  Created by Guillaume Prémel on 24/07/2020.
//  Copyright © 2020 Guillaume Prémel. All rights reserved.
//

#include <stdlib.h>
#include <string.h>

#include <curl/curl.h>

#include "util.h"
#include "safe_malloc.h"
#include "www.h"


size_t dl2string(char *ptr, size_t size, size_t nmemb, www_writestruct* writeinfo){
    char* newalloc = NULL;
    newalloc = realloc(writeinfo->ptr, writeinfo->size + nmemb*size + sizeof(char));
    if(newalloc == NULL){
        die("Erreur d'allocation\n");
    }
    writeinfo->ptr = newalloc;
    memcpy(&(writeinfo->ptr[writeinfo->size]), ptr, size*nmemb);
    writeinfo->size += size*nmemb;
    writeinfo->ptr[writeinfo->size] = '\0';     // on termine la chaîne
    
    return size*nmemb;
}
