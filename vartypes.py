"""In this file, we define wrappers around classes defined in ctypes"""

from typing import Dict, Type, Any

import ctypes


class csc_var():
    """Class that guarantees the existence of an instance variable
    that contains the "pythonic" value for the variable"""
    pass


class csc_arithm_expanded():
    """Class that defines an aritmetic extension to ctypes variable
    NOT TO BE DIRECTELY INSTANCIATED"""

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
        return type(self)(self.value * other.value)

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


class csc_printing_expanded():
    """Class that defines a printing extension to ctypes variable
    NOT TO BE DIRECTELY INSTANCIATED"""

    typecode = 0

    # pylint: disable=no-member
    def __str__(self):
        return str(self.value)  # "{}({})".format(self.__class__.__name__, self.value)

    def __repr__(self):
        return self.__str__()

    @classmethod
    def get_typecode(cls) -> int:
        """Returns the type's typecode"""
        return cls.typecode


class csc_SQL_expanded():
    """Class that binds the type to an SQL type
    NOT TO BE DIRECTELY INSTANCIATED"""
    @staticmethod
    def to_SQL_type():
        return "BLOB"


class csc_uint64(
        csc_printing_expanded,
        ctypes.c_uint64,
        csc_arithm_expanded,
        csc_SQL_expanded,
        csc_var):

    typecode = 2

    @staticmethod
    def to_SQL_type():
        return "BIGINT(20) UNSIGNED"

    # For unsigned intergers, we don't directely cast to int but instead use value.value
    # ("pythonic value" of the variable)
    def __init__(self, value):
        if isinstance(value, csc_var):
            ctypes.c_uint64.__init__(self, int(value.value))
        elif isinstance(value, int):
            ctypes.c_uint64.__init__(self, value)
        else:
            ctypes.c_uint64.__init__(self, int(value))


class csc_int64(
        csc_printing_expanded,
        ctypes.c_int64,
        csc_arithm_expanded,
        csc_SQL_expanded,
        csc_var):

    typecode = 6

    @staticmethod
    def to_SQL_type():
        return "BIGINT(20)"

    def __init__(self, value):
        if not isinstance(value, int):
            ctypes.c_int64.__init__(self, int(value))
        else:
            ctypes.c_int64.__init__(self, value)


class csc_uint32(
        csc_printing_expanded,
        ctypes.c_uint32,
        csc_arithm_expanded,
        csc_SQL_expanded,
        csc_var):

    typecode = 1

    @staticmethod
    def to_SQL_type():
        return "INT(10) UNSIGNED"

    def __init__(self, value):
        if isinstance(value, csc_var):
            ctypes.c_uint32.__init__(self, int(value.value))
        elif isinstance(value, int):
            ctypes.c_uint32.__init__(self, value)
        else:
            ctypes.c_uint32.__init__(self, int(value))


class csc_int32(
        csc_printing_expanded,
        ctypes.c_uint32,
        csc_arithm_expanded,
        csc_SQL_expanded,
        csc_var):

    typecode = 5

    @staticmethod
    def to_SQL_type():
        return "INT(10)"

    def __init__(self, value):
        if not isinstance(value, int):
            ctypes.c_int32.__init__(self, int(value))
        else:
            ctypes.c_int32.__init__(self, value)


class csc_uint8(
        csc_printing_expanded,
        ctypes.c_uint8,
        csc_arithm_expanded,
        csc_SQL_expanded,
        csc_var):
    @staticmethod
    def to_SQL_type():
        return "TINYINT(3) UNSIGNED"

    def __init__(self, value):
        if isinstance(value, csc_var):
            ctypes.c_uint8.__init__(self, int(value.value))
        elif isinstance(value, int):
            ctypes.c_uint8.__init__(self, value)
        else:
            ctypes.c_uint8.__init__(self, int(value))


class csc_float(
        csc_printing_expanded,
        ctypes.c_float,
        csc_arithm_expanded,
        csc_SQL_expanded,
        csc_var):

    typecode = 3

    @staticmethod
    def to_SQL_type():
        return "DOUBLE"  # "FLOAT" -> we have to use DOUBLE or else MariaDB is going to have issues

    def __init__(self, value):
        if isinstance(value, float):
            ctypes.c_float.__init__(self, value)
        elif isinstance(value, csc_float):
            ctypes.c_float.__init__(self, value.value)
        else:
            ctypes.c_float.__init__(self, float(value))


class csc_double(
        csc_printing_expanded,
        ctypes.c_double,
        csc_arithm_expanded,
        csc_SQL_expanded,
        csc_var):

    typecode = 4

    @staticmethod
    def to_SQL_type():
        return "DOUBLE"  # "DOUBLE"

    def __init__(self, value):
        if isinstance(value, float):
            ctypes.c_double.__init__(self, value)
        elif isinstance(value, csc_double):
            ctypes.c_double.__init__(self, value.value)
        else:
            ctypes.c_double.__init__(self, float(value))


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


def caster_depuis_schema(schema: Dict[str, Type[csc_var]],
                         valeurs: Dict[str, Any]) -> Dict[str, csc_var]:
    """Takes a scheme defined in schema and cast the values in valeurs accordingly

    Params:
        schema: a dictionnary, its keys being the name of the variables and its values their
                expected type
        valeurs: a dictionnary, its keys being the name of the variables and its values their
                expected value

    Returns:
        dict: a dictionnary, its keys being the name of the variables and its values instances of
                the type defined in schema, having their respective values matching those found in
                valeurs
    """

    res = {}
    for var, typ in schema.items():
        if var in valeurs:
            res[var] = typ(valeurs[var])
    return res


def schema_vers_sch_typecode(schema):
    """Transforms class to their typecode to send it to the client

    Params:
        schema: the scheme

    Returns:
        dict: the scheme with classes replaces by their respective typecode
    """

    sch_typecode = {}
    for n, c in schema.items():
        sch_typecode[n] = c.typecode

    return sch_typecode
