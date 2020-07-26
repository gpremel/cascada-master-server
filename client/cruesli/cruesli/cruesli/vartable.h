//
//  vartable.h
//  cruesli
//
//  Created by Guillaume Prémel on 24/07/2020.
//  Copyright © 2020 Guillaume Prémel. All rights reserved.
//

#ifndef vartable_h
#define vartable_h

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>

#define VARTYPE_U8 0     /* uint8_t  */
#define VARTYPE_U32 1    /* uint32_t */
#define VARTYPE_U64 2    /* uint64_t */
#define VARTYPE_FLOAT 3  /* float    */
#define VARTYPE_DOUBLE 4 /* double   */
#define VARTYPE_I32 5    /* int32_t  */
#define VARTYPE_I64 6    /* int64_t  */

#define VAR_CALQUE_TYPE_INCOMPATIBLE 1
#define VAR_CALQUE_NON_TROUVE 2


typedef uint8_t csc_var_type;

struct csc_var {
    csc_var_type type;
    char* name;
    void* value;
};

struct csc_var_list {
    struct csc_var* local;
    struct csc_var_list* next;
};


typedef struct csc_var csc_var;
typedef struct csc_var_list csc_var_list;

csc_var_list* nouvelle_liste(void);
bool ajouter_variable(csc_var_type type, char* nom, void* ptr, csc_var_list* list);
csc_var* recup_variable(char* nom, csc_var_list* list);
void detruire_liste(csc_var_list* liste);
void afficher_variable(csc_var* myvar);
void afficher_liste(csc_var_list* liste);
int calquer_liste(csc_var_list* list, csc_var_list* src);
double var2double(csc_var* var);

#endif /* vartable_h */
