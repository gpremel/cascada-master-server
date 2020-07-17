"""Ici on définit l'objet représentant un projet Cascada"""


class projetCascada():
    def __init__(self, nom_projet, sequenceur, schema_sortie: dict):
        self.sequenceur = sequenceur
        self.nom = nom_projet
        self.schema_sortie = schema_sortie
    
    def __str__(self):
        return self.nom
    
    def __repr__(self):
        return self.__str__()

    def schema_total(self):
        schema_entree = self.sequenceur.schema
        for a in schema_entree.keys():
            if a in self.schema_sortie:
                raise KeyError  # on n'a pas le droit d'avoir en entrée et en sortie des variables de même nom!
        return {**schema_entree, **self.schema_sortie}

