//
//  main.c
//  cruesli
//
//  Created by Guillaume Prémel on 23/07/2020.
//  Copyright © 2020 Guillaume Prémel. All rights reserved.
//

#include <stdio.h>
#include <math.h>
#include <unistd.h>

#include <pthread.h>

#include "safe_malloc.h"
#include "vartable.h"
#include "cruesli.h"

#define NB_TH 10

struct csc_th_spawn_info {
    csc_node_info* nodeinfo;
    csc_master_info* masterinfo;
    pthread_t threadid;
};
typedef struct csc_th_spawn_info csc_th_spawn_info;

void th_calcul(csc_th_spawn_info* inf);

int main(int argc, const char * argv[]) {
    
    char hostname[_POSIX_HOST_NAME_MAX];
    gethostname(hostname, _POSIX_HOST_NAME_MAX);
    
    csc_master_info info;
    info = init_cruesli("127.0.0.1:8088", "ABRACADABRA");
    connecter_cascada(&info, hostname);
    allouer_noeuds(&info, NB_TH);
    
    printf("Je m'appelle %s (code %s)\n", info.nom, info.authcode);
    printf("Je bosse sur le projet %s avec l'algorithme %s\n", info.nom_projet, info.algo);
    printf("Schéma d'entrée:\n");
    afficher_liste(info.sch_in);
    printf("Schéma de sortie:\n");
    afficher_liste(info.sch_out);
    
    /*** SPAWN ***/
    printf("Je vais maitenant spawner les threads...\n");
    
    csc_th_spawn_info** th_info_list = safe_malloc(sizeof(csc_th_spawn_info*)*NB_TH);
    csc_node_info* spawner = info.nodes;
    
    int i = 0;
    while(spawner){
        th_info_list[i] = safe_malloc(sizeof(csc_th_spawn_info));
        th_info_list[i]->masterinfo = &info;
        th_info_list[i]->nodeinfo   = spawner;
        
        pthread_create(&(th_info_list[i]->threadid), NULL, (void*)th_calcul, th_info_list[i]);
        spawner = spawner->next;
        i += 1;
    }
    
    for(int i = 0; i < NB_TH; i++)
        pthread_join(th_info_list[i]->threadid, NULL);
    
    
    deconnecter_cascada(&info);
    
    cleanup_cruesli(&info);
    
    return 0;
}


void th_calcul(csc_th_spawn_info* inf){
    
    
    csc_master_info* masterinfo = inf->masterinfo;
    csc_node_info*   monnoeud   = inf->nodeinfo;
    
    float X = 0;
    float Y = 0;
    float Z = 0;
    float d = 0;
    
    int code = 0;
    
    printf("Thread spawné avec succès !\n");
    
    ajouter_variable(VARTYPE_FLOAT, "X", &X, monnoeud->localvars);
    ajouter_variable(VARTYPE_FLOAT, "Y", &Y, monnoeud->localvars);
    ajouter_variable(VARTYPE_FLOAT, "Z", &Z, monnoeud->localvars);
    ajouter_variable(VARTYPE_FLOAT, "d", &d, monnoeud->localvars);

    while(!code){
        code = allouer_travail(masterinfo, monnoeud);
        if(!code){
            d = (-1)*sqrtf(X*X + Y*Y + Z*Z);
            code = soumettre_travail(masterinfo, monnoeud);
            if(code)
                printf("Envoi raté !\n");
        } else {
            if(code == 7)
                printf("Plus de boulot \\°_°\\ \n");
            else
                printf("Allocation ratée !\n");
        }
        
    }

    return;
    
}
