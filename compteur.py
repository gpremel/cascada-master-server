import math


class Compteur():
    """Définit les compteurs utilisés pour balayer les domaines de recherches
        Un compteur doit implémter deux fonctions:
            -> incrémente: qui retourne la valeur de lecture du compteur puis l'incrémente
            -> setup: qui met en place le compteur"""

    def __init__(self, debut, fin, nb, **kwargs):
        self.debut = debut
        self.fin = fin
        self.nb = nb
        self.args = kwargs
        self.setup()
    
    def incremente(self):
        """La fonction incrémente revoit la valeur de lecture du compteur puis l'incrémente
            Args:
                self
            Returns:
                object: la valeur avant incrémentation
                bool:   True s'il reste des valeurs à lire, False sinon
        """
        return None, True

    def setup(self):
        pass


class CompteurError(Exception):
    """Erreur de compteur"""
    pass

class CompteurRange(Compteur):
    def setup(self):
        self.i = self.debut     # valeur lue du compteur

        if self.debut == self.fin:  # cas spécial où le pas est nul; on se débrouille pour afficher nb fois la valeur
            self.mode_repet = True
            self.nb_repet = 0
        else:       # sinon on calcule un pas
            self.mode_repet = False    
            if self.nb is not None and self.nb != 0:
                self.pas = (self.fin - self.debut)/self.nb
            else:
                raise CompteurError

    def incremente(self):
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
    def setup(self):
        self.i = math.log(self.debut)     # valeur lue du compteur
        self.borne_sup = math.log(self.fin)
        if self.debut == self.fin:  # cas spécial où le pas est nul; on se débrouille pour afficher nb fois la valeur
            self.mode_repet = True
            self.nb_repet = 0
        else:       # sinon on calcule un pas
            self.mode_repet = False    
            if self.nb is not None and self.nb != 0:
                self.pas = (math.log(self.fin) - math.log(self.debut))/self.nb
            else:
                raise CompteurError

    def incremente(self):
        if self.mode_repet:
            self.nb_repet += 1
            return self.debut, self.nb_repet < self.nb
        else:
            if self.i <= self.borne_sup:
                res = self.i
                self.i += self.pas
                return min(self.fin, math.exp(res)), True # erreurs d'arrondi, mais si on élimine
                                                        # le problème on perd énormément en distance couverte
            else:
                return self.fin, False
