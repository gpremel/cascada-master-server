"""Ici on définit l'objet représentant un projet Cascada"""

import seq

class projetCascada():
    def __init__(self, nom_projet: str, sequenceur: seq.sequenceur, schema_sortie: dict, schema_densification: dict):
        self.sequenceur = sequenceur
        self.nom = nom_projet
        self.schema_sortie = schema_sortie
        self.schema_entree = sequenceur.schema
        self.schema_densification = schema_densification
        self.var_densification = 'd'
        self.nb_densifications = 10
        self.facteur_selection = 0.01
        self.facteur_amplification = 1
        self.nb_densifications_effectuees = 0
        self.ancien_sequenceur = None
        self.execution_terminee = False

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

    def valider(self, resultat):
        """Valide le résultat renvoyé par les noeuds.
        Params:
            resultat (dict): clef: le nom de la variable, valeur: la valeur comme instance du type
        Returns:
            bool: True si c'est bon, False sinon (données rejetées)    
        """
        return True

    def changer_sequenceur(self, nouv_seq):
        self.sequenceur = nouv_seq
        self.schema_entree = self.sequenceur.schema
