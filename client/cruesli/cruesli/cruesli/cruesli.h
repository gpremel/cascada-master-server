//
//  cruesli.h
//  cruesli
//
//  Created by Guillaume Prémel on 23/07/2020.
//  Copyright © 2020 Guillaume Prémel. All rights reserved.
//

#ifndef cruesli_h
#define cruesli_h

#include <stdio.h>

#include <curl/curl.h>

#include "vartable.h"

int connexion(char* adresse);

struct csc_node_info {
    char* id;
    struct csc_node_info* next;
    struct csc_var_list* localvars;
};

struct csc_master_info{
    char* authcode;
    struct csc_node_info* nodes;
    CURL* handler;
    char* server_base_url;
    char* mdp;
    char* nom;
    
    char* algo;
    char* nom_projet;
    
    csc_var_list* sch_in;
    csc_var_list* sch_out
};

#define CSC_ERR_FATAL_JSON_INTERNAL     -1
#define CSC_ERR_FATAL_MISSINGINFO       -2
#define CSC_ERR_NONFATAL_MISSINGINFO    -3
#define CSC_ERR_FATAL_UNREGISTERED_VAR  -4
#define CSC_ERR_FATAL_INVALID_TYPE      -5
#define CSC_FATAL_NULL_INFO             -6


typedef struct csc_node_info csc_node_info;
typedef struct csc_master_info csc_master_info;

csc_node_info* trouver_noeud_par_id(csc_master_info* info, const char* nodename);

csc_master_info init_cruesli(char* url_serveur, char* mdp);
void cleanup_cruesli(csc_master_info* info);
int connecter_cascada(csc_master_info* info, char* nom_suggere);
int deconnecter_cascada(csc_master_info* info);
int allouer_noeuds(csc_master_info* info, size_t nb_noeuds);
int allouer_travail(csc_master_info* info, csc_node_info* mon_noeud);
int soumettre_travail(csc_master_info* info, csc_node_info* mon_noeud);

#endif /* cruesli_h */
