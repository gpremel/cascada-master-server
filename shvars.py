"""In this file, we define cascada's variable management system"""

from typing import Any, Union

import vartypes as vt


class CscType():
    """A generic cascada type"""

    def __init__(self, nom, constructeur):
        self.nom = nom
        self.constructeur = constructeur

    def __call__(self, *args, **kwargs):
        return self.constructeur(*args, **kwargs)

    def __str__(self):
        return self.nom

    def __repr__(self):
        return self.__str__()


class CscVar():
    """A generic cascada variable"""

    def __init__(self, type, valeur):
        self.type = type
        self.valeur = valeur

    def __str__(self):
        return "{} {}".format(self.type, self.valeur)

    def __repr__(self):
        return self.__str__()


class VarMgmtError(Exception):
    """An execption was encountered while managing the variables"""
    pass


class VarJar():
    """The "jar" that cointains the variables"""

    vartypes = {"int64": CscType("int64", vt.mk_int64), "uint64": CscType("uint64", vt.mk_uint64),
                "int32": CscType("int32", vt.mk_int32), "uint32": CscType("uint32", vt.mk_uint32),
                "uint8": CscType("uint8", vt.mk_uint8), "string": CscType("string", str),
                "float": CscType("float", vt.mk_cfloat), "double": CscType("double", vt.mk_cdouble)}

    def __init__(self):
        self.bocal = {}

    def ajouter_variable(self, nom: str, var: CscVar) -> None:
        """Adds a variable to the jar

        Params:
            nom: the name of the variable to add
            var: its value
        """
        try:
            self.bocal[nom] = var
        except BaseException:
            raise VarMgmtError()

    def lier_variables(self, lnom: str, rnom: str) -> None:
        """Binds two variables: rnom now points to the variable pointed to by lnom

        Params:
            lnom: the name of the variable that will be pointed to by both lnom and rnom
            rnom: the reference that is going to be changed

        Note:
            Both the variable name lnom and rnom have to exist beforehand and have to be of the
            type"""
        try:
            rv = self.bocal[rnom]
            lv = self.bocal[lnom]
        except BaseException:
            raise VarMgmtError()

        if rv.type.nom != lv.type.nom:
            raise VarMgmtError

        self.bocal[rnom] = self.bocal[lnom]

    def acceder_variable(self, nom: str) -> CscVar:
        """Returns the variable named nom

        Params:
            nom: the name of the variable that should be returned
        """
        try:
            a = self.bocal[nom]
        except BaseException:
            raise VarMgmtError()
        return a

    def existance_variable(self, nom_variable: str) -> bool:
        """Checks whether the variable named nom_variable is defined

        Params:
            nom_variable: the name of the variable

        Returns:
            True if the variable is defined, False if not
        """
        return nom_variable in self.bocal

    def changer_valeur_variable(self, nom_variable: str, nouvelle_valeur: Any) -> None:
        """Changes the value of the variable named nom_variable, sets it to nouvelle_valeur

        Params:
            nom_variable: the name of the variable
            nouvelle_valeur: its new value
        """

        a = self.acceder_variable(nom_variable)
        a.valeur = a.type.constructeur(nouvelle_valeur)

    @staticmethod
    def existance_type(nom_type: str) -> bool:
        """Checks whether the variable type nom_type is defined

        Params:
            nom_type: the name of the type
        """
        return nom_type in VarJar.vartypes

    @staticmethod
    def recuperer_type(nom_type: str) -> Union[CscType, None]:
        """Returns the CscType object matching the type name nom_type

        Params:
            nom_type: the name of the variable type

        Returns:
            CscType|None: the CscType matching nom_type or None if it does not exist
        """
        if VarJar.existance_type(nom_type):
            return VarJar.vartypes[nom_type]
        else:
            return None
