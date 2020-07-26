//
//  www.h
//  cruesli
//
//  Created by Guillaume Prémel on 24/07/2020.
//  Copyright © 2020 Guillaume Prémel. All rights reserved.
//

#ifndef www_h
#define www_h

#include <stdio.h>

struct www_writestruct {
    char* ptr;
    size_t size;
};

typedef struct www_writestruct www_writestruct;
size_t dl2string(char *ptr, size_t size, size_t nmemb, www_writestruct* writeinfo);

#endif /* www_h */
