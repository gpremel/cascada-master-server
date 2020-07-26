//
//  cruesli.c
//  cruesli
//
//  Created by Guillaume Prémel on 23/07/2020.
//  Copyright © 2020 Guillaume Prémel. All rights reserved.
//

#include <string.h>
#include <stdlib.h>

#include <pthread.h>

#include <curl/curl.h>
#include <cjson/cJSON.h>

#include "safe_malloc.h"
#include "util.h"
#include "www.h"
#include "vartable.h"
#include "cruesli.h"

// Global NETwork LOCK pour curl
static pthread_mutex_t g_net_lock = PTHREAD_MUTEX_INITIALIZER;


csc_master_info init_cruesli(char* url_serveur, char* mdp){
    CURL* handler = NULL;
    
    char* url_cpy = NULL;
    url_cpy = safe_malloc((strlen(url_serveur)+1)*sizeof(char));
    strcpy(url_cpy, url_serveur);
    
    char* mdp_cpy = NULL;
    mdp_cpy = safe_malloc((strlen(mdp)+1)*sizeof(char));
    strcpy(mdp_cpy, mdp);
    
    handler = curl_easy_init();
    
    if(!handler){
        die("Erreur d'initialisation du netcode");
    }
    
    csc_master_info info;
    info.handler = handler;
    info.server_base_url = url_cpy;
    info.mdp = mdp_cpy;
    info.authcode = NULL;
    info.nodes = NULL;
    info.nom = NULL;
    
    info.algo = NULL;
    info.nom_projet = NULL;
    
    info.sch_in = nouvelle_liste();
    info.sch_out = nouvelle_liste();
    
    
    return info;
}


csc_node_info* trouver_noeud_par_id(csc_master_info* info, const char* nodename){
    
    csc_node_info* noeud = info->nodes;
    
    
    while(noeud){
        if(!strcmp(nodename, noeud->id))
            return noeud;
    }
    
    return NULL;
}


void cleanup_cruesli(csc_master_info* info){
    free(info->server_base_url);
    free(info->mdp);
    free(info->nom);
    free(info->authcode);
    
    csc_node_info* noeud_courant = info->nodes;
    csc_node_info* suivant;
    while(noeud_courant){
        suivant = noeud_courant->next;
        free(noeud_courant->id);
        detruire_liste(noeud_courant->localvars);
        free(noeud_courant);
        noeud_courant = suivant;
    }
    
    curl_easy_cleanup(info->handler);
    
    detruire_liste(info->sch_in);
    detruire_liste(info->sch_out);
}


int connecter_cascada(csc_master_info* info, char* nom_suggere){
    printf("Connexion au réseau cascada...\n");
    // On s'authentifie sur le réseau cascada
    
    int retcode = 0;
    char url[] = "/api/v1/register-master";
    struct curl_slist *headers = NULL;
    www_writestruct writestruct = { .ptr = NULL, .size = 0};
    char* url_complete = strconc(info->server_base_url, url);
    
    
    curl_easy_setopt(info->handler, CURLOPT_URL, url_complete);
    
    /* Là on construit la requête */
    cJSON* base = cJSON_CreateObject();
    cJSON* json_mdp             = NULL;
    cJSON* json_nom             = NULL;
    
    cJSON* reponse              = NULL;
    cJSON* json_code_statut     = NULL;
    cJSON* json_token           = NULL;
    
    cJSON* json_projet          = NULL;
    cJSON* json_projet_algo     = NULL;
    cJSON* json_projet_nom      = NULL;
    cJSON* json_projet_sch_in   = NULL;
    cJSON* json_projet_sch_out  = NULL;


    if(!base){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end;
    }


    json_mdp = cJSON_CreateString(info->mdp);
    if(!json_mdp){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end;
    }
    cJSON_AddItemToObject(base, "key", json_mdp);
    
    json_nom = cJSON_CreateString(nom_suggere);
    if(!json_nom){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end;
    }
    cJSON_AddItemToObject(base,"name", json_nom);
    
    
    char* str = cJSON_Print(base);

    // str contient les infos de connexion, maintenant il n'y a plus qu'à envoyer la sauce
    headers = curl_slist_append(headers, "Expect:");
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(info->handler, CURLOPT_HTTPHEADER, headers);
    
    curl_easy_setopt(info->handler, CURLOPT_POSTFIELDS, str);
    curl_easy_setopt(info->handler, CURLOPT_POSTFIELDSIZE, -1L);
    
    curl_easy_setopt(info->handler, CURLOPT_WRITEFUNCTION, dl2string);
    curl_easy_setopt(info->handler, CURLOPT_WRITEDATA, &writestruct);
    
    curl_easy_perform(info->handler);
    
    reponse = cJSON_Parse(writestruct.ptr);

    
    json_code_statut = cJSON_GetObjectItemCaseSensitive(reponse, "code");
    if(!cJSON_IsNumber(json_code_statut)){
        retcode = CSC_ERR_FATAL_MISSINGINFO;
        goto end2;
    }
    retcode = json_code_statut->valueint;
    if(json_code_statut->valueint != 0){
        goto end2;
    }
    
    json_token = cJSON_GetObjectItemCaseSensitive(reponse, "master_token");
    if(!cJSON_IsString(json_token)){
        retcode = CSC_ERR_FATAL_MISSINGINFO;
        goto end2;
    }
    info->authcode = strdup(json_token->valuestring);
    
    json_nom = cJSON_GetObjectItemCaseSensitive(reponse, "name");
    if(!cJSON_IsString(json_nom)){
        retcode = CSC_ERR_FATAL_MISSINGINFO;
        goto end2;
    }
    info->nom = strdup(json_nom->valuestring);
    
    json_projet = cJSON_GetObjectItemCaseSensitive(reponse, "project");
    if(!cJSON_IsObject(json_projet)){
        retcode = CSC_ERR_FATAL_MISSINGINFO;
        goto end2;
    }
    
    
    /* Ce sont des propriétés non-critiques donc si on ne les a pas c'est pas grave,
     on continue quand même */
    json_projet_nom = cJSON_GetObjectItemCaseSensitive(json_projet, "name");
    if(!cJSON_IsString(json_projet_nom)){
        retcode = CSC_ERR_NONFATAL_MISSINGINFO;
        //goto end2;
    } else {
        info->nom_projet = strdup(json_projet_nom->valuestring);
    }
    
    json_projet_algo = cJSON_GetObjectItemCaseSensitive(json_projet, "algo");
    if(!cJSON_IsString(json_projet_algo)){
        retcode = CSC_ERR_NONFATAL_MISSINGINFO;
        //goto end2;
    } else {
        info->algo = strdup(json_projet_algo->valuestring);
    }
    
    json_projet_sch_in = cJSON_GetObjectItemCaseSensitive(json_projet, "scheme_in");
    if(!cJSON_IsObject(json_projet_sch_in)){
        retcode = CSC_ERR_FATAL_MISSINGINFO;
        goto end2;
    }
    json_projet_sch_out = cJSON_GetObjectItemCaseSensitive(json_projet, "scheme_out");
    if(!cJSON_IsObject(json_projet_sch_out)){
        retcode = CSC_ERR_FATAL_MISSINGINFO;
        goto end2;
    }

    
    {
        cJSON* var;
        // On itère sur le schéma d'entrée...
        cJSON_ArrayForEach(var, json_projet_sch_in){
            if(!cJSON_IsNumber(var) || !var->string){
                retcode = CSC_ERR_FATAL_MISSINGINFO;
                goto end2;
            }
            ajouter_variable(var->valueint, var->string, NULL, info->sch_in);
        }
        
        // On itère ensuite sur le schéma de sortie
        cJSON_ArrayForEach(var, json_projet_sch_out){
            if(!cJSON_IsNumber(var) || !var->string){
                retcode = CSC_ERR_FATAL_MISSINGINFO;
                goto end2;
            }
            ajouter_variable(var->valueint, var->string, NULL, info->sch_out);
        }
    }

    

end2:
    /* On a pas besoin de faire un cJSON_Delete sur les
     schéma car ils appartienent à reponse */
    cJSON_Delete(reponse);
    free(str);
    free(url_complete);
    free(writestruct.ptr);

    
end:
    cJSON_Delete(base);
    
    return retcode;
}

int deconnecter_cascada(csc_master_info* info){
    
    int retcode = 0;
    char url[] = "/api/v1/unregister-master";
    
    struct curl_slist *headers = NULL;
    www_writestruct writestruct = { .ptr = NULL, .size = 0};
    
    char* url_complete = strconc(info->server_base_url, url);
    char* str = NULL;
    
    curl_easy_setopt(info->handler, CURLOPT_URL, url_complete);
    headers = curl_slist_append(headers, "Expect:");
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(info->handler, CURLOPT_HTTPHEADER, headers);

    
    cJSON* reponse = NULL;
    cJSON* json_code_statut = NULL;
    
    /* Là on construit la requête */
    cJSON* base = cJSON_CreateObject();
    if(!base){
        goto end;
    }
    cJSON* json_token = cJSON_CreateString(info->authcode);
    if(!json_token){
        goto end;
    }
    cJSON_AddItemToObject(base, "mastertoken", json_token);
    
    str = cJSON_Print(base);
    
    curl_easy_setopt(info->handler, CURLOPT_POSTFIELDS, str);
    curl_easy_setopt(info->handler, CURLOPT_POSTFIELDSIZE, -1L);
    
    curl_easy_setopt(info->handler, CURLOPT_WRITEFUNCTION, dl2string);
    curl_easy_setopt(info->handler, CURLOPT_WRITEDATA, &writestruct);
    
    curl_easy_perform(info->handler);
    
    reponse = cJSON_Parse(writestruct.ptr);
    
    json_code_statut = cJSON_GetObjectItemCaseSensitive(reponse, "code");
    if(!cJSON_IsNumber(json_code_statut)){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end2;
    }
    retcode = json_code_statut->valueint;


end2:
    cJSON_Delete(reponse);
    
    
end:
    cJSON_Delete(base);
    free(writestruct.ptr);
    free(url_complete);
    free(str);
    
    return retcode;
}


int allouer_noeuds(csc_master_info* info, size_t nb_noeuds){
    int retcode = 0;
    char url[] = "/api/v1/register-nodes";
    
    struct curl_slist *headers = NULL;
    www_writestruct writestruct = { .ptr = NULL, .size = 0};
    
    char* url_complete = strconc(info->server_base_url, url);
    char* str = NULL;
    
    curl_easy_setopt(info->handler, CURLOPT_URL, url_complete);
    headers = curl_slist_append(headers, "Expect:");
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(info->handler, CURLOPT_HTTPHEADER, headers);
    
    
    cJSON* reponse = NULL;
    cJSON* json_code_statut = NULL;
    cJSON* json_liste_id_noeuds = NULL;
    cJSON* json_id_noeud_courant = NULL;
    
    /* Là on construit la requête */
    cJSON* base = cJSON_CreateObject();
    if(!base){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end;
    }
    cJSON* json_token = cJSON_CreateString(info->authcode);
    if(!json_token){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end;
    }
    cJSON_AddItemToObject(base, "mastertoken", json_token);
    
    cJSON* json_nbnoeuds = cJSON_CreateNumber(nb_noeuds);
    if(!json_nbnoeuds){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end;
    }
    cJSON_AddItemToObject(base, "nodenumber", json_nbnoeuds);

    str = cJSON_Print(base);
    
    
    curl_easy_setopt(info->handler, CURLOPT_POSTFIELDS, str);
    curl_easy_setopt(info->handler, CURLOPT_POSTFIELDSIZE, -1L);
    
    curl_easy_setopt(info->handler, CURLOPT_WRITEFUNCTION, dl2string);
    curl_easy_setopt(info->handler, CURLOPT_WRITEDATA, &writestruct);
    
    curl_easy_perform(info->handler);
    
    reponse = cJSON_Parse(writestruct.ptr);
    
    json_code_statut = cJSON_GetObjectItemCaseSensitive(reponse, "code");
    if(!cJSON_IsNumber(json_code_statut)){
        retcode = CSC_ERR_FATAL_MISSINGINFO;
        goto end2;
    }
    retcode = json_code_statut->valueint;

    json_liste_id_noeuds = cJSON_GetObjectItemCaseSensitive(reponse, "nodenames");
    if(!cJSON_IsArray(json_liste_id_noeuds)){
        retcode = CSC_ERR_FATAL_MISSINGINFO;
        goto end2;
    }
    
    
    csc_node_info* tmp = NULL;
    csc_node_info* newtmp = NULL;
    if (retcode == 0){
        cJSON_ArrayForEach(json_id_noeud_courant, json_liste_id_noeuds){
        newtmp = safe_malloc(sizeof(csc_node_info));
        newtmp->localvars = nouvelle_liste();
            
        if(!tmp){
            info->nodes = newtmp;
            tmp = newtmp;
        } else {
            tmp->next = newtmp;
        }
            if(!cJSON_IsString(json_id_noeud_courant)){
                retcode = CSC_ERR_FATAL_MISSINGINFO;
                goto end2;
            }
            
            newtmp->id = strdup(json_id_noeud_courant->valuestring);
            tmp = newtmp;
        }
    }
    newtmp->next = NULL;
        
        
    
    
    
end2:
    cJSON_Delete(reponse);
    
end:
    cJSON_Delete(base);
    free(writestruct.ptr);
    free(url_complete);
    free(str);
    

    
    
    return retcode;
}


int allouer_travail(csc_master_info* info, csc_node_info* mon_noeud){
    
    //csc_node_info* mon_noeud = trouver_noeud_par_id(info, id_noeud);
    
    
    if(!mon_noeud || !info)
        return CSC_FATAL_NULL_INFO;

    int retcode = 0;
    char url[] = "/api/v1/fetch-work-for-node";
    
    struct curl_slist *headers = NULL;
    www_writestruct writestruct = { .ptr = NULL, .size = 0};
    
    char* url_complete = strconc(info->server_base_url, url);
    char* str = NULL;
    
    
    
    cJSON* reponse = NULL;
    cJSON* json_code_statut = NULL;
    cJSON* json_payload = NULL;
    
    /* Là on construit la requête */
    cJSON* base = cJSON_CreateObject();
    if(!base){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end;
    }
    cJSON* json_token = cJSON_CreateString(info->authcode);
    if(!json_token){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end;
    }
    cJSON_AddItemToObject(base, "mastertoken", json_token);
    
    cJSON* json_idnoeud = cJSON_CreateString(mon_noeud->id);
    if(!json_idnoeud){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end;
    }
    cJSON_AddItemToObject(base, "nodeid", json_idnoeud);
    
    str = cJSON_Print(base);
    
    
    
    pthread_mutex_lock(&g_net_lock);
    
    curl_easy_setopt(info->handler, CURLOPT_URL, url_complete);
    headers = curl_slist_append(headers, "Expect:");
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(info->handler, CURLOPT_HTTPHEADER, headers);

    
    curl_easy_setopt(info->handler, CURLOPT_POSTFIELDS, str);
    curl_easy_setopt(info->handler, CURLOPT_POSTFIELDSIZE, -1L);
    
    curl_easy_setopt(info->handler, CURLOPT_WRITEFUNCTION, dl2string);
    curl_easy_setopt(info->handler, CURLOPT_WRITEDATA, &writestruct);
    
    curl_easy_perform(info->handler);
    
    pthread_mutex_unlock(&g_net_lock);

    
    reponse = cJSON_Parse(writestruct.ptr);
    
    json_code_statut = cJSON_GetObjectItemCaseSensitive(reponse, "code");
    if(!cJSON_IsNumber(json_code_statut)){
        retcode = CSC_ERR_FATAL_MISSINGINFO;
        goto end2;
    }
    retcode = json_code_statut->valueint;
    if(retcode != 0){
        goto end2;
    }
    
    json_payload = cJSON_GetObjectItemCaseSensitive(reponse, "task-payload");
    if(!cJSON_IsObject(json_payload)){
        retcode = CSC_ERR_FATAL_MISSINGINFO;
        goto end2;
    }
    
    // Lecture + conversion/assignation
    {
        cJSON* var;
        csc_var* local_var;
        cJSON_ArrayForEach(var, json_payload){
            if(!cJSON_IsNumber(var)){
                retcode = CSC_ERR_FATAL_MISSINGINFO;
                goto end2;
            }
            
            local_var = recup_variable(var->string, mon_noeud->localvars);
            if(!local_var){
                // Variable pas trouvée -> erreur critique;
                retcode = CSC_ERR_FATAL_UNREGISTERED_VAR;
                goto end2;
            }
            
            // On convertit la variable...
            switch (local_var->type) {
                case VARTYPE_FLOAT:
                    *((float*)(local_var->value))  = (float)var->valuedouble;
                    break;
                case VARTYPE_DOUBLE:
                    *((double*)(local_var->value))  = (double)var->valuedouble;
                    break;
                case VARTYPE_U8:
                    *((uint8_t*)(local_var->value))  = (uint8_t)var->valueint;
                    break;
                case VARTYPE_U32:
                    *((uint32_t*)(local_var->value)) = (uint32_t)var->valueint;
                    break;
                case VARTYPE_U64:
                    *((uint64_t*)(local_var->value)) = (uint64_t)var->valueint;
                    break;
                case VARTYPE_I32:
                    *((int32_t*)(local_var->value))  = (int32_t)var->valueint;
                    break;
                case VARTYPE_I64:
                    *((int64_t*)(local_var->value))  = (int64_t)var->valueint;
                    break;
                default:
                    // Variable non supportée...
                    retcode = CSC_ERR_FATAL_INVALID_TYPE;
                    break;
            }
        }
    }
    
    
    
    
    
end2:
    cJSON_Delete(reponse);
    
end:
    cJSON_Delete(base);
    free(writestruct.ptr);
    free(url_complete);
    free(str);
    
    
    
    return retcode;
}


int soumettre_travail(csc_master_info* info, csc_node_info* mon_noeud){
    
    //csc_node_info* mon_noeud = trouver_noeud_par_id(info, id_noeud);
    
    if(!mon_noeud || !info)
        return CSC_FATAL_NULL_INFO;
    
    
    int retcode = 0;
    char url[] = "/api/v1/submit-results";
    
    struct curl_slist *headers = NULL;
    www_writestruct writestruct = { .ptr = NULL, .size = 0};
    
    char* url_complete = strconc(info->server_base_url, url);
    char* str = NULL;
    
    
    
    cJSON* reponse = NULL;
    cJSON* json_code_statut = NULL;
    cJSON* json_payload = NULL;
    
    /* Là on construit la requête */
    cJSON* base = cJSON_CreateObject();
    if(!base){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end;
    }
    cJSON* json_token = cJSON_CreateString(info->authcode);
    if(!json_token){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end;
    }
    cJSON_AddItemToObject(base, "mastertoken", json_token);
    
    cJSON* json_idnoeud = cJSON_CreateString(mon_noeud->id);
    if(!json_idnoeud){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end;
    }
    cJSON_AddItemToObject(base, "nodeid", json_idnoeud);
    
    
    json_payload = cJSON_CreateObject();
    if(!json_payload){
        retcode = CSC_ERR_FATAL_JSON_INTERNAL;
        goto end;
    }
    
    // On commence par recopier le schéma d'entrée
    {
        csc_var_list* var_iter_cour = info->sch_in;
        csc_var* var_local     = NULL;
        cJSON*   json_valeur = NULL;
        while(var_iter_cour){
            if(var_iter_cour->local){
                var_local = recup_variable(var_iter_cour->local->name, mon_noeud->localvars);
                // La variable locale exigée n'existe pas...
                if(!var_local){
                    retcode = CSC_ERR_FATAL_UNREGISTERED_VAR;
                    goto end;
                }
                json_valeur = cJSON_CreateNumber(var2double(var_local));
                
                cJSON_AddItemToObject(json_payload, var_local->name, json_valeur);
            }
            var_iter_cour = var_iter_cour->next;
        }
        
        var_iter_cour = info->sch_out;
        while(var_iter_cour){
            if(var_iter_cour->local){
                var_local = recup_variable(var_iter_cour->local->name, mon_noeud->localvars);
                // La variable locale exigée n'existe pas...
                if(!var_local){
                    retcode = CSC_ERR_FATAL_UNREGISTERED_VAR;
                    goto end;
                }
                json_valeur = cJSON_CreateNumber(var2double(var_local));
                cJSON_AddItemToObject(json_payload, var_local->name, json_valeur);
            }
            var_iter_cour = var_iter_cour->next;
        }
    }
    
    cJSON_AddItemToObject(base, "payload", json_payload);
    
    str = cJSON_Print(base);
    
    pthread_mutex_lock(&g_net_lock);
    
    curl_easy_setopt(info->handler, CURLOPT_URL, url_complete);
    headers = curl_slist_append(headers, "Expect:");
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(info->handler, CURLOPT_HTTPHEADER, headers);
    
    curl_easy_setopt(info->handler, CURLOPT_POSTFIELDS, str);
    curl_easy_setopt(info->handler, CURLOPT_POSTFIELDSIZE, -1L);
    
    curl_easy_setopt(info->handler, CURLOPT_WRITEFUNCTION, dl2string);
    curl_easy_setopt(info->handler, CURLOPT_WRITEDATA, &writestruct);
    
    curl_easy_perform(info->handler);
    
    pthread_mutex_unlock(&g_net_lock);

    
    reponse = cJSON_Parse(writestruct.ptr);
    
    json_code_statut = cJSON_GetObjectItemCaseSensitive(reponse, "code");
    if(!cJSON_IsNumber(json_code_statut)){
        retcode = CSC_ERR_NONFATAL_MISSINGINFO;
        goto end2;
    }
    retcode = json_code_statut->valueint;

end2:
    cJSON_Delete(reponse);
    
end:
    cJSON_Delete(base);
    free(writestruct.ptr);
    free(url_complete);
    free(str);
    
    return retcode;
    
}



int connexion(char* adresse){
    CURL* monCurl = NULL;
    monCurl = curl_easy_init();
    
    if(monCurl){
        curl_easy_setopt(monCurl, CURLOPT_URL, "http://localhost:8088/hello");
        curl_easy_perform(monCurl);
    }
    
    curl_easy_cleanup(monCurl);
    
    return 0;
}
