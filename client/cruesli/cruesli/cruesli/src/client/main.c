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
#include <stdlib.h>
#include <time.h>
#include <limits.h>

#include <pthread.h>

#include <cruesli/cruesli.h>

#include "safe_malloc.h"


#define NB_TH 8


typedef struct csc_th_spawn_info {
    csc_node_info* nodeinfo;
    csc_master_info* masterinfo;
    pthread_t threadid;
} csc_th_spawn_info;

void th_calcul(csc_th_spawn_info* inf);

int main(int argc, const char * argv[]) {
    
    char hostname[_POSIX_HOST_NAME_MAX];
    gethostname(hostname, _POSIX_HOST_NAME_MAX);
    
    csc_master_info info;

    const char* master_server_address = "127.0.0.1:8088";
    const char* master_server_pwd = "ABRACADABRA";

    if(argc > 1)
        master_server_address = argv[1];
    if(argc > 2)
        master_server_pwd = argv[2];
    if(argc > 3){
        fprintf(stderr, "usage: %s <address>:<port> <password>\n"
                "\t - address:port defaults to 127.0.0.1:8088\n"
                "\t\tif the port is left unspecified, it defaults to 80\n"
                "\t - password defaults to ABRACADABRA\n", argv[0]);
        exit(1);
    }
    
    printf("Connecting to the cascada master server at %s...\n", master_server_address);

    info = init_cruesli(master_server_address, master_server_pwd);
    int res = connecter_cascada(&info, hostname);
    if(res != CSC_NO_ERROR){
        fprintf(stderr, "An error happenned during connection\n");
        exit(2);
    }

    res = allouer_noeuds(&info, NB_TH);
    if(res != CSC_NO_ERROR){
        fprintf(stderr, "An error happenned during node allocation\n");
        exit(2);
    }



    printf("My name is %s (code %s)\n", info.nom, info.authcode);
    printf("I work on the project %s with the algorithm %s\n", info.nom_projet, info.algo);
    //printf("Input scheme:\n");
    //afficher_liste(info.sch_in);
    //printf("Output scheme:\n");
    //afficher_liste(info.sch_out);
    
    /*** SPAWN ***/
    printf("I will now spawn the %d threads...\n", NB_TH);
    
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
    
    printf("Thread succesfully spawned !\n");
    
    ajouter_variable(VARTYPE_FLOAT, "X", &X, monnoeud->localvars);
    ajouter_variable(VARTYPE_FLOAT, "Y", &Y, monnoeud->localvars);
    ajouter_variable(VARTYPE_FLOAT, "Z", &Z, monnoeud->localvars);
    ajouter_variable(VARTYPE_FLOAT, "mE", &d, monnoeud->localvars);

    while(!code){
        code = allouer_travail(masterinfo, monnoeud);
        if(!code){
            d = (-1)*(sqrtf(X*X + Y*Y + Z*Z)+1);
            code = soumettre_travail(masterinfo, monnoeud);
            if(code)
                printf("Submission failed !\n");
        } else {
            if(code == 7)
                printf("No more work \\°_°\\ \n");
            else
                printf("Couldn't allocate work ! (nothing to do with malloc...)\n");
        }
        
    }

    return;
    
}
