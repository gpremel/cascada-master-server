import ctypes

"""Dans ce fichier on définit des wrappers autour des classes fournies par ctypes"""

def mk_uint64(v):
    return ctypes.c_uint64(int(v))

def mk_int64(v):
    return ctypes.c_int64(int(v))

def mk_uint32(v):
    return ctypes.c_uint32(int(v))

def mk_int32(v):
    return ctypes.c_int32(int(v))

def mk_uint8(v):
    return ctypes.c_uint8(int(v))

def mk_cfloat(v):
    return ctypes.c_float(float(v))

def mk_cdouble(v):
    return ctypes.c_double(float(v))

