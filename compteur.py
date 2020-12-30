"""Defines a counter used to sweep the domain defined in the scheme"""

from typing import Tuple

import math
from Numbers import Number


class Compteur():
    """Defines a counter used to sweep the domain defined in the scheme
    A counter has to implement two functions
            -> incremente: returns the current value then increment
            -> setup: prepares the counter
    """

    def __init__(self, debut: Number, fin: Number, nb: int, **kwargs):
        self.debut = debut
        self.fin = fin
        self.nb = nb
        self.args = kwargs
        self.setup()

    def incremente(self) -> Tuple[Number, bool]:
        """The incremente function reads the counter current value and increments it

        Return:
                Number: the current counter value
                bool:   True if there are remaining values to be read, False if not
        """

        return None, True

    def setup(self):
        """Setups the counter"""
        pass


class CompteurError(Exception):
    """Counter error"""
    pass


class CompteurRange(Compteur):
    """A simple counter that iterates linearly"""

    def setup(self):
        """See the Compteur class"""
        self.i = self.debut     # value read by the counter

        if self.debut == self.fin:  # special case: if the start of the suquence is the same
            self.mode_repet = True  # value as the end, we shall return nb times the same value
            self.nb_repet = 0
        else:       # computing the step
            self.mode_repet = False
            if self.nb is not None and self.nb != 0:
                self.pas = (self.fin - self.debut) / self.nb
            else:
                raise CompteurError

    def incremente(self) -> Tuple[Number, bool]:
        """See the Compteur class"""
        if self.mode_repet:
            self.nb_repet += 1
            return self.debut, self.nb_repet < self.nb
        else:
            if self.i <= self.fin:
                res = self.i
                self.i += self.pas
                return res, True
            else:
                return self.fin, False


class CompteurLogRange(Compteur):
    """A counter that iterates following a geometric progression"""

    def setup(self):
        self.i = math.log(self.debut)     # value read by the counter
        self.borne_sup = math.log(self.fin)
        if self.debut == self.fin:  # special case when the step is null; see CompteurRange
            self.mode_repet = True
            self.nb_repet = 0
        else:     # compute the common ratio
            self.mode_repet = False
            if self.nb is not None and self.nb != 0:
                self.pas = (math.log(self.fin) - math.log(self.debut)) / self.nb
            else:
                raise CompteurError

    def incremente(self) -> Tuple[Number, bool]:
        if self.mode_repet:
            self.nb_repet += 1
            return self.debut, self.nb_repet < self.nb
        else:
            if self.i <= self.borne_sup:
                res = self.i
                self.i += self.pas
                return min(self.fin, math.exp(res)), True  # deal with rounding errors
            else:
                return self.fin, False
