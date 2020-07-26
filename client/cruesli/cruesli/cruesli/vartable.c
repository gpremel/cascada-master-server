//
//  vartable.c
//  cruesli
//
//  Created by Guillaume Prémel on 24/07/2020.
//  Copyright © 2020 Guillaume Prémel. All rights reserved.
//


#include <string.h>
#include <inttypes.h>

#include "util.h"
#include "safe_malloc.h"
#include "vartable.h"


#define CMP_NOMATCH 0
#define CMP_NAME_MATCH 1
#define CMP_NAME_TYPE_MATCH 2
#define CMP_NAME_TYPE_VALUE_MATCH 3


int cmp_var_noval(csc_var* v1, csc_var* v2);

csc_var_list* nouvelle_liste(void){
    csc_var_list* liste=safe_malloc(sizeof(csc_var_list));
    liste->local = NULL;
    liste->next = NULL;

    return liste;
}


int cmp_var_noval(csc_var* v1, csc_var* v2){
    
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



bool ajouter_variable(csc_var_type type, char* nom, void* ptr, csc_var_list* list){

    // On ne peut rien faire sur un pointeur NULL
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
                // On a trouvé la variable, qui existe donc déjà...
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
    
    // On est arrivé au bout de la liste sans encombre;
    // On peut donc rajouter myvar à la liste
    
    // Soit on a trouvé un trou dans la liste
    if(premier_null != NULL){
        premier_null->local = myvar;
    } else {
        // On doit allouer un nouveau maillon de la chaîne, que l'on va ranger dans
        // prec->next
        prec->next = safe_malloc(sizeof(csc_var_list));
        prec->next->local = myvar;
        prec->next->next  = NULL;
    }
    
    return true;
}


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


void afficher_variable(csc_var* myvar){
    
    if(myvar == NULL){
        return;
    }
    
    // Cas où l'on a enregistré une variable sans valeur
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

void afficher_liste(csc_var_list* liste){
    while(liste){
        afficher_variable(liste->local);
        printf("\n");
        liste = liste->next;
    }
}



int calquer_liste(csc_var_list* list, csc_var_list* src){
    // Pour chaque valeur de list, on regarde si elle est dans src;
    // si c'est le cas, on change la valeur de l'élément de liste pour
    // le faire coincider avec l'élément de src correspondant
    
    csc_var_list* orig_src = src;
    
    int retcode = 0;
    bool found;
    
    while(list){
        found = false;
        if(list->local){
            while(src){
                if(src->local && !strcmp(src->local->name, list->local->name)){
                    /* Type compatible ? */
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
