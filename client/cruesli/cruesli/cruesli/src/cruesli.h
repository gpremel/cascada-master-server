//
//  cruesli.h
//  cruesli
//
//  Created by Guillaume Prémel on 23/07/2020.
//  Copyright © 2020 Guillaume Prémel. All rights reserved.
//

#ifndef cruesli_h
#define cruesli_h


// Actually declared in entities.h
typedef struct csc_node_info csc_node_info;
typedef struct csc_master_info csc_master_info;

csc_node_info* trouver_noeud_par_id(const csc_master_info* info, const char* nodename);

csc_master_info init_cruesli(const char* url_serveur, const char* mdp);
void cleanup_cruesli(csc_master_info* info);
int connecter_cascada(csc_master_info* info, char* nom_suggere);
int deconnecter_cascada(csc_master_info* info);
int allouer_noeuds(csc_master_info* info, size_t nb_noeuds);
int allouer_travail(csc_master_info* info, csc_node_info* mon_noeud);
int soumettre_travail(csc_master_info* info, csc_node_info* mon_noeud);
int connexion(char* adresse);

#endif /* cruesli_h */
