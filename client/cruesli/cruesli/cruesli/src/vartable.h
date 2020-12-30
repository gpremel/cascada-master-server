//
//  vartable.h
//  cruesli
//
//  Created by Guillaume Prémel on 24/07/2020.
//  Copyright © 2020 Guillaume Prémel. All rights reserved.
//

#ifndef vartable_h
#define vartable_h

#include <stdbool.h>
#include "varstructs.h"   // needed for csc_var_type

#define VAR_CALQUE_TYPE_INCOMPATIBLE 1
#define VAR_CALQUE_NON_TROUVE 2


typedef struct csc_var_list csc_var_list;
typedef struct csc_var csc_var;

csc_var_list* nouvelle_liste(void);
bool ajouter_variable(csc_var_type type, char* nom, void* ptr, csc_var_list* list);
csc_var* recup_variable(char* nom, csc_var_list* list);
void detruire_liste(csc_var_list* liste);
void afficher_variable(csc_var* myvar);
void afficher_liste(csc_var_list* liste);
int calquer_liste(csc_var_list* list, csc_var_list* src);
double var2double(csc_var* var);

#endif /* vartable_h */
