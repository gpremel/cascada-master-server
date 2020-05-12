#!/usr/bin/env python3

import vartypes as vt

"""Dans ce fichier on définit le système de traitement des variables de cascada"""

class CscType():
    """Un type générique de variable cascada"""
    def __init__(self, nom, constructeur):
        self.nom            = nom
        self.constructeur   = constructeur 

class CscVar():
    """Une variable générique de cascada"""
    def __init__(self, type, valeur):
        self.type = type
        self.valeur = valeur
        
    def __str__(self):
        return "{} {}".format(self.type, self.valeur)

    def __repr__(self):
        return self.__str__()

class VarMgmtError(Exception):
    """Erreur dans la gestion des variables"""
    pass

class VarJar():
    """Le "pot" qui contient les variables (abstraction grossière)"""

    vartypes = { "int64": CscType("int64", vt.mk_int64), "uint64": CscType("uint64", vt.mk_uint64), 
    "int32": CscType("int32", vt.mk_int32), "uint32": CscType("uint32", vt.mk_uint32),
    "uint8": CscType("uint8", vt.mk_uint8), "string": CscType("string", str),
    "float": CscType("float", vt.mk_cfloat), "double": CscType("double", vt.mk_cdouble) }

    def __init__(self):
        self.bocal = {}
    
    def ajouter_variable(self, nom: str, var: CscVar):
        """On ajoute une variable au bocal"""
        try:
            self.bocal[nom] = var
        except:
            raise VarMgmtError()

    def lier_variables(self, lnom: str, rnom: str):
        """On lit deux variables du bocal: en gros rnom pointe désormais sur la variables connue sous le
           nom de lnom"""
        try:
            rv = self.bocal[rnom]
            lv = self.bocal[lnom]
        except:
            raise VarMgmtError()
        
        if rv.type.nom != lv.type.nom:
            raise VarMgmtError

        self.bocal[rnom] = self.bocal[lnom]


    def acceder_variable(self, nom):
        try:
            a = self.bocal[nom]
        except:
            raise VarMgmtError()
        return a
    
    def existance_variable(self, nom_variable):
        return nom_variable in self.bocal

    def changer_valeur_variable(self, nom_variable, nouvelle_valeur):
        a = self.acceder_variable(nom_variable)
        a.valeur = a.type.constructeur(nouvelle_valeur)
            

    @staticmethod
    def existance_type(nom_type):
        return nom_type in VarJar.vartypes

    @staticmethod
    def recuperer_type(nom_type):
        if VarJar.existance_type(nom_type):
            return VarJar.vartypes[nom_type]
        else:
            return None