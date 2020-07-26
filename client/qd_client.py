#!/usr/bin/env python3

import time
import requests
import sys
import signal

SERVER = "http://localhost:8088/api/v1/"
CLEF = "ABRACADABRA"
NOM = "QD_PYTHON" if len(sys.argv) < 2 else sys.argv[1]
N_NODES = 20
TOKEN = None


def deconnexion():                                                                  
    # *** Déconnexion ***                                                           
    r = requests.post(SERVER+"unregister-master", json={"mastertoken": TOKEN})      
    res = r.json()                                                                  
    if res["code"] == 0:                                                            
        print("Déconnexion OK")                                                     
    else:                                                                           
        print(res["msg"])                                                           
    exit(0)

# *** Login ***
print("Authentification... ", end='', flush=True)
r = requests.post(SERVER+"register-master", data={"key": CLEF, "name": NOM})
res = r.json()
TOKEN = res["master_token"]
NOM = res["name"]
print("OK")
print("Connecté sous le nom {}".format(NOM))


# *** Noeuds ***

# Création 
r = requests.post(SERVER+"register-nodes", json={"mastertoken": TOKEN, "nodenumber": N_NODES})
# Liste
r = requests.post(SERVER+"fetch-nodes", json={"mastertoken": TOKEN})
res = r.json()

mon_noeud = res[0]

signal.signal(signal.SIGINT, lambda s, f: deconnexion())

# *** Recherche d'un travail ***
#print("Bonjour, je suis le noeud {}, je cherche un travail".format(mon_noeud))
while True:

    r = requests.post(SERVER+"fetch-work-for-node", json={"mastertoken": TOKEN, "nodeid": mon_noeud})
    res = r.json()

    if res["code"] != 0:
        print("FATAL: {} (errcode {})".format(res["msg"], res["code"]))
        deconnexion()

    travail = r.json()["task-payload"]

    #print("Voilà mon travail: {}".format(travail))

    d = 0
    for coordonnee in travail.values():
        d += float(coordonnee)**2

    travail["d"] = -(d**0.5)  # pour maximiser en 0
    r = requests.post(SERVER+"submit-results", json={"mastertoken": TOKEN, "nodeid": mon_noeud, "payload": travail})


deconnexion()


