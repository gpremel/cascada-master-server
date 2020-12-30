//
//  vartable.c
//  cruesli
//
//  Created by Guillaume Prémel on 24/07/2020.
//  Copyright © 2020 Guillaume Prémel. All rights reserved.
//

/*!
    Defines several useful functions for manipulating the Cascada variables and variables lists.
*/


#include <string.h>
#include <inttypes.h>

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>


#include "util.h"
#include "safe_malloc.h"
#include "vartable.h"
#include "varstructs.h"


#define CMP_NOMATCH 0
#define CMP_NAME_MATCH 1
#define CMP_NAME_TYPE_MATCH 2
#define CMP_NAME_TYPE_VALUE_MATCH 3


int cmp_var_noval(const csc_var* v1, const csc_var* v2);



/*!
    \brief Creates a new variable list.
    
    \return A pointer to a new, empty, list                
*/

csc_var_list* nouvelle_liste(void){
    csc_var_list* liste=safe_malloc(sizeof(csc_var_list));
    liste->local = NULL;
    liste->next = NULL;

    return liste;
}

/*!
    \brief Safely compares two pointers to cascada variables.
    
    \param v1 A pointer to the first variable
    \param v2 A pointer to the second variable
    \return - CMP_NAME_TYPE_MATCH if both the names and the types match
            - CMP_NAME_MATCH if only the names match
            - CMP_NOMATCH if nothing matches
                    
*/
int cmp_var_noval(const csc_var* v1, const csc_var* v2){
    
    if(!strcmp(v1->name, v2->name)){
        if(v1->type == v2->type){
                return CMP_NAME_TYPE_MATCH;
            } else {
                return CMP_NAME_MATCH;
        }
    }  else {
        return CMP_NOMATCH;
    }
    
}


/*!
    \brief Adds a variable named nom, having type type, pointed to by ptr, to the variable list list.
    
    \param type The cascada type of the variable, can be
                - VARTYPE_U8 
                - VARTYPE_U32
                - VARTYPE_U64    
                - VARTYPE_FLOAT 
                - VARTYPE_DOUBLE  
                - VARTYPE_I32 
                - VARTYPE_I64

    \param nom The name of the variable. Should match the name provided in the scheme sent by the master server.
    \param ptr The adress of the underlying C variable.
    \param list A pointer to the list of variables that the new variable should be added to.
    \return true if the variable was successfully added, false if not.

    \note If a variable with the same name already exists, its value WILL NOT BE UPDATED; nothing will happen.            
    \note The name parameter has nothing to do with the name of the underlying C variable.
    \note The name of the variable is copied, and therefore ownership of the array nom is NOT shared.
*/
bool ajouter_variable(csc_var_type type, char* nom, void* ptr, csc_var_list* list){

    // Can't do anything with a NULL pointer
    if(list == NULL){
        return false;
    }
    
    int res_cmp;

    csc_var_list* prec = NULL;
    csc_var_list* premier_null = NULL;
    
    csc_var* myvar = safe_malloc(sizeof(csc_var));
    myvar->name = strdup(nom);
    myvar->type = type;
    myvar->value = ptr;
    
    
    
    while(list != NULL){
        if(list->local != NULL)
        {
            res_cmp = cmp_var_noval(myvar, list->local);
            if(res_cmp != CMP_NOMATCH){
                // We found the variable, which therefore does already exist
                free(myvar->name);
                free(myvar);
                return false;
            }
        } else {
            if(!premier_null){
                premier_null = list;
            }
        }
        prec = list;
        list = list->next;
        
    }
    
    // We made it to the end of the list without issue
    // We can therefore add myvar to the list
    
    // Either we found a hole in the list
    if(premier_null != NULL){
        premier_null->local = myvar;
    } else {

        // Or we didn't, and we have to allocate a new link in the linked list
        // That we'll store in prec->next
        prec->next = safe_malloc(sizeof(csc_var_list));
        prec->next->local = myvar;
        prec->next->next  = NULL;
    }
    
    return true;
}

/*!
    \brief Fetches the variable named nom from the variable list.
    
    \param nom The name of the variable.
    \param list A pointer to the list of variables that will be searched.
    \return A pointer to the variable if it does exist in the list; NULL if not
*/
csc_var* recup_variable(char* nom, csc_var_list* list){
    while(list != NULL){
        if(list->local != NULL){
            if(!strcmp(nom, list->local->name)){
                return list->local;
            }
        }
        list = list->next;
    }
    return NULL;
}


/*!
    \brief Destroys the variable list liste.
    
    \param liste A pointer to the list of variable that should be disposed of.
*/

void detruire_liste(csc_var_list* liste){
    csc_var_list* suivant = NULL;
    
    while(liste != NULL){
        suivant = liste->next;
        if(liste->local){
            free(liste->local->name);
        }
        free(liste->local);
        free(liste);
        liste = suivant;
    }
    
}

/*!
    \brief Prints the content and type of the cascada variable myvar.
    
    \param myvar A pointer to the vairable that should be printed.
*/
void afficher_variable(csc_var* myvar){
    
    if(myvar == NULL){
        return;
    }
    
    // Registered a variable without its value
    if(!myvar->value){
        printf("%s: None", myvar->name);
        return;
    }
    
    switch (myvar->type) {
        case VARTYPE_U8:
            printf("%s: %"PRIu8, myvar->name, *((uint8_t*)(myvar->value)));
            break;
        
        case VARTYPE_I32:
            printf("%s: %"PRId32, myvar->name, *((int32_t*)(myvar->value)));
            break;
        
        case VARTYPE_I64:
            printf("%s: %"PRId64, myvar->name, *((int64_t*)(myvar->value)));
            break;

        case VARTYPE_U32:
            printf("%s: %"PRIu32, myvar->name, *((uint32_t*)(myvar->value)));
            break;
            
        case VARTYPE_U64:
            printf("%s: %"PRIu64, myvar->name, *((uint64_t*)(myvar->value)));
            break;
            
        case VARTYPE_FLOAT:
            printf("%s: %f", myvar->name, *((float*)(myvar->value)));
            break;
            
        case VARTYPE_DOUBLE:
            printf("%s: %lf", myvar->name, *((double*)(myvar->value)));
            break;

        
        default:
            printf("%s: ??? [%d]", myvar->name, myvar->type);
            break;
    }
}

/*!
    \brief Prints the content and type of the cascada variable list liste.
    
    \param liste A pointer to the cascada variable list that should be printed.
*/
void afficher_liste(csc_var_list* liste){
    while(liste){
        afficher_variable(liste->local);
        printf("\n");
        liste = liste->next;
    }
}


/*!
    \brief Fills in the values of the variables of list with the values of the corresponding variables of src.
    
    \param list A pointer to the cascada variable list that should be completed.
    \param src  A pointer to the cascada variable list that should be used to complete list.
    \return 0 if everything went fine and an error code if not.

    \warning All the variables of list must exist in src. 
*/
int calquer_liste(csc_var_list* list, csc_var_list* src){

    // For each value of list, we check if it is in src.
    // If it's the case, we change the value of the element to
    // have it equal to the corresponding element of src
    
    csc_var_list* orig_src = src;
    
    int retcode = 0;
    bool found;
    
    while(list){
        found = false;
        if(list->local){
            while(src){
                if(src->local && !strcmp(src->local->name, list->local->name)){
                    // Compatible type ? 
                    if(src->local->type == list->local->type)
                        list->local->value = src->local->value;
                    else
                        retcode |= VAR_CALQUE_TYPE_INCOMPATIBLE;
                    src = orig_src;
                    found = true;
                    break;
                }
                src = src->next;
            }
        }
        if(!found)
            retcode |= VAR_CALQUE_NON_TROUVE;
        list = list->next;
    }
    
    return retcode;
}


/*!
    \brief Casts the cascada variable var to a double.
    
    \param var  A pointer to the cascada variable that should be cast.
    \return The value of the variable casted as a double.

    \note If the variable can't be cast because its type is unknown (which should not happen), the function returns 0.0.
*/
double var2double(csc_var* var){
    switch (var->type) {
        case VARTYPE_U8:
            return (double)(*((uint8_t*)(var->value)));
            break;
            
        case VARTYPE_I32:
            return (double)(*((int32_t*)(var->value)));
            break;
            
        case VARTYPE_I64:
            return (double)(*((int64_t*)(var->value)));
            break;
            
        case VARTYPE_U32:
            return (double)(*((uint32_t*)(var->value)));
            break;
            
        case VARTYPE_U64:
            return (double)(*((uint64_t*)(var->value)));
            break;
            
        case VARTYPE_FLOAT:
            return (double)(*((float*)(var->value)));
            break;
            
        case VARTYPE_DOUBLE:
            return *((double*)(var->value));
            break;
            
        default:
            return 0.0;
    }
}
