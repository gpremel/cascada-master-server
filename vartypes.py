import ctypes

"""Dans ce fichier on définit des wrappers autour des classes fournies par ctypes"""


class csc_arithm_expanded(object):
    """Classe qui vise à fournir une extension
    des propriétés arithmétiques à d'autres types
    NE DOIT PAS ÊTRE INSTANCIÉE DIRECTEMENT"""

    def __new__(cls, *args, **kwargs):
        if cls is csc_arithm_expanded:
            raise TypeError("base class may not be instantiated")
        pass 

    def __init__(self, *args, **kwargs):
        self.value = None
        pass

    def __add__(self, other):
        return type(self)(self.value + other.value)
    
    def __sub__(self, other):
        return type(self)(self.value - other.value)
    
    def __mul__(self, other):
        return type(self)(self.value*other.value)
    
    def __div__(self, other):
        return type(self)(self.value / other.value)

    def __eq__(self, other):
        return self.value == other.value
    
    def __lt__(self, other):
        return self.value < other.value

    def __le__(self, other):
        return self.value <= other.value

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)


class csc_printing_expanded(object):
    """Classe qui vise à fournir une extension
    des propriétés d'affichage à d'autres types
    NE DOIT PAS ÊTRE INSTANCIÉE DIRECTEMENT"""

    typecode = 0

    def __str__(self):
        return str(self.value) #"{}({})".format(self.__class__.__name__, self.value)
    
    def __repr__(self):
        return self.__str__()

    @staticmethod
    def get_typecode():
        return typecode

class csc_SQL_expanded(object):
    """Classe qui n'implémente qu'une unique fonction, qui vise à offrir une
    interopérabilité entre cascada et SQL"""
    @staticmethod
    def to_SQL_type():
        return "BLOB"


    
class csc_uint64(csc_printing_expanded, ctypes.c_uint64, csc_arithm_expanded, csc_SQL_expanded):
    
    typecode = 2
    
    @staticmethod
    def to_SQL_type():
        return "BIGINT(20) UNSIGNED"
    
    def __init__(self, value):
        if not isinstance(value, int):
            ctypes.c_uint64.__init__(self, int(value))
        else:
            ctypes.c_uint64.__init__(self, value)

    
    

class csc_int64(csc_printing_expanded, ctypes.c_int64, csc_arithm_expanded, csc_SQL_expanded):
    
    typecode = 6

    @staticmethod
    def to_SQL_type():
        return "BIGINT(20)"
    
    def __init__(self, value):
        if not isinstance(value, int):
            ctypes.c_int64.__init__(self, int(value))
        else:
            ctypes.c_int64.__init__(self, value)



class csc_uint32(csc_printing_expanded, ctypes.c_uint32, csc_arithm_expanded, csc_SQL_expanded):
    
    typecode = 1
    
    @staticmethod
    def to_SQL_type():
        return "INT(10) UNSIGNED"
    
    def __init__(self, value):
        if not isinstance(value, int):
            ctypes.c_uint32.__init__(self, int(value))
        else:
            ctypes.c_uint32.__init__(self, value)



class csc_int32(csc_printing_expanded, ctypes.c_uint32, csc_arithm_expanded, csc_SQL_expanded):

    typecode = 5

    @staticmethod
    def to_SQL_type():
        return "INT(10)"

    def __init__(self, value):
        if not isinstance(value, int):
            ctypes.c_int32.__init__(self, int(value))
        else:
            ctypes.c_int32.__init__(self, value)




class csc_uint8(csc_printing_expanded, ctypes.c_uint8,  csc_arithm_expanded, csc_SQL_expanded):
    @staticmethod
    def to_SQL_type():
        return "TINYINT(3) UNSIGNED"
    
    def __init__(self, value):
        if not isinstance(value, int):
            ctypes.c_uint8.__init__(self, int(value))
        else:
            ctypes.c_uint8.__init__(self, value)




class csc_float(csc_printing_expanded, ctypes.c_float, csc_arithm_expanded, csc_SQL_expanded):

    typecode = 3

    @staticmethod
    def to_SQL_type():
        return "DOUBLE" # "FLOAT" -> pas le choix sinon MariaDB déconne et ne renvoit pas les bonnes valeurs
    
    def __init__(self, value):
        if isinstance(value, float):
            ctypes.c_float.__init__(self, value)
        elif isinstance(value, csc_float):
            ctypes.c_float.__init__(self, value.value)
        else:
            ctypes.c_float.__init__(self, float(value))


class csc_double(csc_printing_expanded, ctypes.c_double, csc_arithm_expanded, csc_SQL_expanded):

    typecode = 4

    @staticmethod
    def to_SQL_type():
        return "DOUBLE" # "DOUBLE"
   
    def __init__(self, value):
        if isinstance(value, value):
            ctypes.c_double.__init__(self, value)
        elif isinstance(value, csc_double):
            ctypes.c_float.__init__(self, value.value)
        else:
            ctypes.c_double.__init__(self, float(value))



# def mk_uint64(v):
#     return ctypes.c_uint64(int(v))

# def mk_int64(v):
#     return ctypes.c_int64(int(v))

# def mk_uint32(v):
#     return ctypes.c_uint32(int(v))

# def mk_int32(v):
#     return ctypes.c_int32(int(v))

# def mk_uint8(v):
#     return ctypes.c_uint8(int(v))

# def mk_cfloat(v):
#     return ctypes.c_float(float(v))

# def mk_cdouble(v):
#     return ctypes.c_double(float(v))


def mk_uint64(v):
    return csc_uint64(int(v))

def mk_int64(v):
    return csc_int64(int(v))

def mk_uint32(v):
    return csc_uint32(int(v))

def mk_int32(v):
    return csc_int32(int(v))

def mk_uint8(v):
    return csc_uint8(int(v))

def mk_cfloat(v):
    return csc_float(float(v))

def mk_cdouble(v):
    return csc_double(float(v))


def caster_depuis_schema(schema, valeurs):
    res = {}
    for var, typ in schema.items():
        if var in valeurs:
            res[var] = typ(valeurs[var])
    return res

def schema_vers_sch_typecode(schema):
    """Permet de transformer les classes en leur typecode pour l'envoyer au client

    Params:
        schema (dict): le schéma

    Returns:
        dict: le schéma avec les classes remplacées par leur typecode

    """

    sch_typecode = {}
    for n, c in schema.items():
        sch_typecode[n] = c.typecode
    
    return sch_typecode