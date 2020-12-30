#ifndef varstructs_h
#define varstructs_h

#include <stdint.h>

#define VARTYPE_U8 0     /* uint8_t  */
#define VARTYPE_U32 1    /* uint32_t */
#define VARTYPE_U64 2    /* uint64_t */
#define VARTYPE_FLOAT 3  /* float    */
#define VARTYPE_DOUBLE 4 /* double   */
#define VARTYPE_I32 5    /* int32_t  */
#define VARTYPE_I64 6    /* int64_t  */

typedef uint8_t csc_var_type;

struct csc_var {
    csc_var_type type;
    char* name;
    void* value;
};

struct csc_var_list {
    struct csc_var* local;
    struct csc_var_list* next;
};


typedef struct csc_var csc_var;
typedef struct csc_var_list csc_var_list;

#endif