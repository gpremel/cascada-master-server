#include "cscerrs.h"
#include "entities.h"
#include "varstructs.h"

// For size_t
#include <stddef.h>
// For bool
#include <stdbool.h>

/*!
    This header is desgined to enable the use of cascada as a shared library.
 */

#define CSC_CRUESLI_VERSION 20200800

extern csc_node_info* trouver_noeud_par_id(const csc_master_info* info, const char* nodename);
csc_master_info init_cruesli(const char* url_serveur, const char* mdp);
extern void cleanup_cruesli(csc_master_info* info);
extern int connecter_cascada(csc_master_info* info, char* nom_suggere);
extern int deconnecter_cascada(csc_master_info* info);
extern int allouer_noeuds(csc_master_info* info, size_t nb_noeuds);
extern int allouer_travail(csc_master_info* info, csc_node_info* mon_noeud);
extern int soumettre_travail(csc_master_info* info, csc_node_info* mon_noeud);
extern bool ajouter_variable(csc_var_type type, char* nom, void* ptr, csc_var_list* list);
