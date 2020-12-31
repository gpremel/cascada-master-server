"""Defines the object representing a Cascada project"""

from typing import Dict, Callable, Type
from seq import Sequenceur
from vartypes import csc_var


class ProjetCascada():
    """A cascada project, ie where all details pertaining to the tasks should be centralized"""

    def __init__(self, nom_projet: str, sequenceur: Sequenceur,
                 schema_sortie: Dict[str, Type[csc_var]],
                 schema_densification: Dict[str, Type[csc_var]],
                 var_densification: str, nb_densifications: int,
                 facteur_selection: float, facteur_amplification: float,
                 password: str,
                 alogrithm: str = "UNKNOWN",
                 validateur_entree: Callable[[Dict[str, csc_var]], bool] = lambda x: True):
        """Initializes the cascada project

            Params:
                nom_projet: the name of the project
                sequenceur: the sequencer that is going to be used to generate the sequence of
                            values sent to the slave servers
                schema_sortie: the outgoing scheme that is going to be sent to the slave servers
                schema_densification: the scheme that lists the variables thats are going
                                        to be densified
                var_densification: the name of the variable that is going to be
                                    used to find the best, most promising records
                nb_densifications: the number of densifications to be made
                facteur_selection: the proportion of records to be kept during the densification
                facteur_amplification: describe the "zoom" factor, ie by how the program is going
                                    to increase the scale around the most promising records
                password: the password the client will have to give to connect to the server
                algorithm: (optionnal) a simple string describing the algorithm used; will be sent
                                    to the client during the handshake process;
                                    defaults to "UNKNOWN"
                validateur_entree: (optionnal) a function that is going to be called to check
                                    the validity of the result returned by the client if applicable;
                                    defaults to a function that accepts anything
        """

        self.sequenceur = sequenceur
        self.nom = nom_projet
        self.schema_sortie = schema_sortie
        self.schema_entree = sequenceur.schema
        self.schema_densification = schema_densification
        self.var_densification = var_densification
        self.nb_densifications = nb_densifications  # 10
        self.facteur_selection = facteur_selection  # 0.01
        self.facteur_amplification = facteur_amplification  # 1
        self.nb_densifications_effectuees = 0
        self.ancien_sequenceur = None  # used during densification,
        # to know how many iterations we made
        # for each variable
        self.execution_terminee = False
        self.password = password
        self.algo = alogrithm
        self.valider = validateur_entree

    def __str__(self):
        return self.nom

    def __repr__(self):
        return self.__str__()

    def schema_total(self) -> Dict[str, csc_var]:
        """Computes the complete scheme (with both the in and out schemes)

        Returns:
            dict: the complete scheme
        """

        schema_entree = self.sequenceur.schema
        for a in schema_entree.keys():
            if a in self.schema_sortie:
                raise KeyError  # we can't have the same variable both
                # in the sent scheme (computed by the server)
                # and the received scheme (computed by the client)
        return {**schema_entree, **self.schema_sortie}

    def changer_sequenceur(self, nouv_seq: Sequenceur) -> None:
        """Changes the sequencer to the sequencer provided by nouv_seq

        Params:
            nouv_seq: the new sequencer
        """

        self.sequenceur = nouv_seq
        self.schema_entree = self.sequenceur.schema
