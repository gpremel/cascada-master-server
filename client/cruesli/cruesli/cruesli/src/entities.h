#ifndef entites_h
#define entites_h


typedef struct csc_node_info {
    char* id;
    struct csc_node_info* next;
    struct csc_var_list* localvars;
} csc_node_info;

typedef struct csc_master_info{
    char* authcode;
    struct csc_node_info* nodes;
    void* handler;   // Actually a CURL*
    char* server_base_url;
    char* mdp;
    char* nom;
    
    char* algo;
    char* nom_projet;
    
    struct csc_var_list* sch_in;
    struct csc_var_list* sch_out;
} csc_master_info;

#endif