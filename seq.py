"""Ici on définit l'objet séquenceur qui va nous permettre de générer des séries de données à fournir aux noeuds"""

import numpy as np


from vartypes import *
import server

class sequenceur():
    def __init__(self, schema={}, schema_compteurs={}):
        """Initialise le sequenceur
            Params:
                schema           (dict): le classique dictionnaire avec comme clef les noms des variables 
                                            et comme valeur la classe de type
                schema_compteurs (dict): plus subtile, dictionnaire avec comme clef le nom des variables
                                            et comme valeur un quadruplet (debut, fin, nombre itérations, fct)
                                            avec fct une fonction qui à (debut, fin, nombre itération) associe
                                            le (a)range correspondant (c'est typiquement numpy.linspace)
            Returns:
                dict: le schéma de sortie, avec comme clef les noms des variables et comme valeurs des instances
                        de type
            """

        self.nb_iters_realisees = 0
        self.schema = schema
        self.schema_compteurs = schema_compteurs
        self.a_deborde = False

        self.nb_iters_total = 0


        if len(schema_compteurs) > 0:
            self.nb_iters_total = 1
            for r in schema_compteurs.values():
                self.nb_iters_total *= r[2]

        self.indices_courants = [0 for i in range(len(schema_compteurs))]

        # espace_variable nous permet de "compacter" schema et schema_compteurs en un seul bloc.
        # c'est un tableau contenant des sous-listes de taille 5
        # Chaque sous-liste a cette structure
        #   -> le nom de la variables
        #   -> la classe décrivant son type
        #   -> le quadruplet (debut, fin, nombre, fonction générant le range)
        #   -> le range genéré
        #   -> la valeur actuelle de la variable comme instance de son type

        self.espace_variables = []
        for nom, vartype in self.schema.items():
            self.espace_variables.append([nom, vartype])
        for i in range(len(self.espace_variables)):
            # on recast en liste car on va le modifier par la suite
            self.espace_variables[i].append(list(self.schema_compteurs[self.espace_variables[i][0]]))
            
            fct = self.espace_variables[i][2][3]
            deb = self.espace_variables[i][2][0]
            fin = self.espace_variables[i][2][1]
            nb  = self.espace_variables[i][2][2]

            # la première variable
            self.espace_variables[i].append(fct(deb, fin, nb))

            # expression un peu compliquée qui permet d'initialiser la valeur de la variable
            # comme instance de son type
            self.espace_variables[i].append(self.espace_variables[i][1](deb))

    def suivant(self):
        """Permet de générer le nombre suivant dans la séquence"""
        if len(self.indices_courants) == 0 or self.a_deborde:
            return None
        
        # on propage la retenue
        i = 0
        while i < len(self.indices_courants) and self.indices_courants[i] >= self.espace_variables[i][2][2]:
            self.indices_courants[i] = 0
            i += 1
            if i < len(self.indices_courants): self.indices_courants[i] += 1
        
        # on a fini d'itérer (on est à bloc) et tous les indices ont été rebasculés à 0
        if i >= len(self.indices_courants):
            self.a_deborde = True
            return None

        # on a propagé la retenue du rang 0 au rang i exclu, par ailleurs on sait qu'on n'est pas dans une
        # situation de rebouclage: ainsi la variable la plus à droite n'a pas débordé, elle a simplement
        # été incrémentée.
        # on doit ainsi recalculer les variables de 0 à i INCLUS (comme i < dernier indice c'est bon)
        for j in range(i+1):
            caster = self.espace_variables[j][1]    # le type de la variable   
            # la variable comme instance de son type vaut désormais la valeur prise par le range au nouvel indice
            self.espace_variables[j][4] = caster(self.espace_variables[j][3][self.indices_courants[j]])
        

        # il ne reste plus qu'à générer le schéma de sortie
        # pour ce faire on lit simplement l'espace de variables
        sch_sortie = {}
        for j in range(len(self.espace_variables)):
            sch_sortie[self.espace_variables[j][0]] = self.espace_variables[j][4]
        
        # enfin, on incrémente pour le tour suivant
        self.indices_courants[0] += 1

        return sch_sortie

if __name__ == '__main__':
    schema = {"K": csc_float, "E": csc_uint8}
    schema_compteurs = {"K": (0, 1, 10, np.linspace), "E": (0, 5, 6, np.linspace)} #{"K": range(0, 10), "E": range(0, 5, 1)}
    S = sequenceur(schema, schema_compteurs)
    print(S.nb_iters_total)
    print(S.indices_courants)

    server.sequenceur = S
    server.launch()
