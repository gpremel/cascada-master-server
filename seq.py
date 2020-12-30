"""Here is defined the Sequenceur object that will enable us to
    generate the data we'll send to the nodes"""

from typing import Type, Dict, Tuple, Callable, Iterable

import numpy as np

from vartypes import csc_var, csc_float, csc_uint8


class Sequenceur():
    def __init__(self, schema: Dict[str, Type[csc_var]] = {},
                 schema_compteurs: Dict[str,
                                        Tuple[float,
                                              float,
                                              int,
                                              Callable[[float, float, int],
                                                       Iterable[float]]]] = {}):
        """Initializes the sequencer
            Params:
                schema: a dictionnary, which keys are the name of the variables, the values being
                        the matching type's class
                schema_compteurs: a dictionnary, with its keys being the name of the variables,
                                  the associated values being a 4-value tuple:
                                        - start
                                        - end
                                        - number of iterations
                                        - fct
                                    Where fct is a function that takes (start, end, number of
                                    iterations) and returns the corresponding
                                    range (eg numpy.linspace)
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

        # espace_variable "shrinks" schema and schema_compteurs in a single block
        # it's a list containing sublists made of 5 elements
        # Each sublist has the following structure:
        #  -> the name of the variable
        #  -> the class describing its type
        #  -> the 4-value tuple (start, end, count, fct)
        #  -> the generated range
        #  -> the value of the current variable (as an instance of its type)

        self.espace_variables = []
        for nom, vartype in self.schema.items():
            self.espace_variables.append([nom, vartype])
        for i in range(len(self.espace_variables)):
            self.espace_variables[i].append(
                list(self.schema_compteurs[self.espace_variables[i][0]]))

            fct = self.espace_variables[i][2][3]
            deb = self.espace_variables[i][2][0]
            fin = self.espace_variables[i][2][1]
            nb = self.espace_variables[i][2][2]

            # first variable
            self.espace_variables[i].append(fct(deb, fin, nb))

            # initializes the variable as instance of its type
            self.espace_variables[i].append(self.espace_variables[i][1](deb))

    def suivant(self) -> Dict[str, csc_var]:
        """Generates the next number in the sequence

            Returns:
                dict: the outgoing scheme, with its keys being the name of the variables and
                        the values being a matching (value-wise)
                    instances of their type
        """

        if len(self.indices_courants) == 0 or self.a_deborde:
            return None

        # propagates the carry
        i = 0
        while i < len(
            self.indices_courants) and \
                self.indices_courants[i] >= self.espace_variables[i][2][2]:
            self.indices_courants[i] = 0
            i += 1
            if i < len(self.indices_courants):
                self.indices_courants[i] += 1

        # we're done iterating and each index has been reseted to 0
        if i >= len(self.indices_courants):
            self.a_deborde = True
            return None

        # we've propagated the carry from index 0 to index i excluded; we know that we're not in a
        # "loop-like" situation: the rightmost variable hasn't overflowed, it's simply been
        # incremented. We therefore have to compute variables from 0 to i (INCLUDED)
        # (as i < last index we're good)
        for j in range(i + 1):
            caster = self.espace_variables[j][1]    # the variable's type
            # the variable as instance of its type is now equals to the value taken by
            # the range at the same position
            self.espace_variables[j][4] = caster(
                self.espace_variables[j][3][self.indices_courants[j]])

        # we just have to generate the outgoing scheme
        # it's quite easy: we only have to read the variable space
        sch_sortie = {}
        for j in range(len(self.espace_variables)):
            sch_sortie[self.espace_variables[j][0]] = self.espace_variables[j][4]

        # finally, we increment to loop
        self.indices_courants[0] += 1
        self.nb_iters_realisees += 1

        return sch_sortie

    def reset(self) -> None:
        """Resets the counter"""
        self.__init__(self.schema, self.schema_compteurs)

    def recharger_bornes_pas(self, bornes_pas: Dict[str, Tuple[float, float, int]]) -> None:
        """Reloads the limits and steps parameters for the variables specified in bornes_pas;
        useful for densifying !

            Params:
                bornes_pas: Keys are the names of the variables to be reloaded;
                            values are a 3-element tuple:
                    -> start
                    -> end
                    -> number of iterations

            Returns:
                None

            Notes:
                This function RESETS the counter !
        """

        for n, v in bornes_pas.items():
            if n in self.schema_compteurs:
                fct = self.schema_compteurs[n][3]
                self.schema_compteurs[n] = (v[0], v[1], v[2], fct)
        self.reset()

    def nb_iters_pour_variable(self, nom_variable: str) -> int:
        """Returns the number of iterations for the variable name nom_variable

            Params:
                nom_variable: the name of the variable

            Returns:
                int: the number of iterations
        """

        if nom_variable not in self.schema_compteurs:
            return None
        else:
            return self.schema_compteurs[nom_variable][2]


if __name__ == '__main__':
    schema = {"K": csc_float, "E": csc_uint8}
    schema_compteurs = {
        "K": (
            0, 10, 11, np.linspace), "E": (
            0, 5, 6, np.linspace)}  # {"K": range(0, 10), "E": range(0, 5, 1)}
    S = Sequenceur(schema, schema_compteurs)
    print(S.nb_iters_total)
    x = S.suivant()
    while x is not None:
        print(x)
        if x['E'].value == 4 and x['K'].value < 30:
            S.recharger_bornes_pas({'K': (50, 55, 11)})
        x = S.suivant()
