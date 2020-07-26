"""Ici on définit le gestionnaire de session qui permet de partager les infos de session entre plusieurs instances/processus/threads
    de cascada (sinon on risque d'avoir des désynchronisations entre les instances, ce qui serait dramatique)"""

from multiprocessing import Lock
from multiprocessing.managers import BaseManager

corbeille_taches = []
sessions_maitre = {}




