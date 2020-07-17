from bottle import route, run, response, request, post, static_file

from enum import Enum
import random
import json
import time

from vartypes import *
import db
import projet

sessions_esclaves = {}
sessions_maitres = {}
compteur_utilisation_noms = {}

# Parfois il est possible que l'on décide que la tâche doit être accomplie à nouveau
# (noeud mort par exemple), donc on les consigne dans la pile suivante.
taches_a_redistribuer = []

version = {"version": 1, "vendor": "coffeeXL"}
clef_secrete="ABRACADABRA"
temps_max_keepalive = 1200  # 20 minutes
nom_projet = "GATEAU_SUCRE"


mon_projet = None
maBDD = None #db.controlleurBDD(nom_projet, {"K": csc_uint8, "n": csc_uint64, "E": csc_double}, "db_cred.json")
sequenceur = None

class statutClient(Enum):
    NON_CONNECTE = 0
    CONNECTE = 1
    TIMEOUT = 2

class statutNoeud(Enum):
    INACTIF = 0
    MORT = 2
    PAUSE = 3
    ACTIF = 4

class erreursClient(Enum):
    PAS_ERREUR = 0
    ECHEC_AUTH = 1
    CLEF_MANQUANTE_DANS_TROUSSEAU = 2
    TIMEOUT_RELOGIN = 3
    MANQUE_CHAMP_REQUETE = 4
    MAUVAIS_STATUT_NOEUD = 5
    VALEUR_INVALIDE = 6
    PLUS_DE_TRAVAIL = 7



class tacheCalcul():
    """Une tâche de calcul confiée à un noeud"""
    def __init__(self, valeurs={}):
        """Initialise la tâche de calcul
        Params:
            valeurs (dict): dictionnaire dont les clefs sont les nom des variables et les 
                            valeurs les valeurs desdites variables
        Returns:
            None
        """
        # Les variables qui servent à faire le calcul, générées par le code ccda et transmise au noeud
        self.valeurs = valeurs
        self.demandeur = ""
    
    def __str__(self):
        return ", ".join(["{} = {}".format(var, val) for var, val in self.valeurs.items()])
    



class noeudCalcul():
    def __init__(self, nom="unnamed-node"):
        self.statut = statutNoeud.INACTIF
        self.nom = nom
        self.tache_calcul = None

    def __str__(self):
        return str(self.statut.value) + " [{}]".format(self.tache_calcul) if self.statut != statutNoeud.INACTIF else str(self.statut.value)
    
    def __repr__(self):
        return self.__str__()

class clientMaitre():
    def __init__(self, nom, token, keepalive=0, statut=statutClient.NON_CONNECTE):
        self.nom = nom
        self.token = token
        self.statut = statut
        self.dernier_keepalive = keepalive
        self.noeuds = {}
        self.nb_noeuds_ajoutes = 0

    def deconnecter(self):
        del sessions_maitres[self.token]
    
    def ajouter_noeud(self):
        nom_noeud = self.nom+"#"+str(self.nb_noeuds_ajoutes+1)
        self.noeuds[nom_noeud] = noeudCalcul(nom=nom_noeud)
        self.nb_noeuds_ajoutes += 1
    
    def liste_noeuds(self):
        return [(num, noeud) for num, noeud in self.noeuds.items()]

    def recuperer_noeud(self, idnoeud):
        try:
            return self.noeuds[idnoeud]
        except Exception as e:
            raise e

    

def sanitize(no_timeout=False):
    try:
        data = dict(request.json)
    except:
        raise ValueError

    if data is None:
        raise ValueError

    if int(data["mastertoken"]) not in sessions_maitres.keys():
        return False, json.dumps({"status": "error", "code": erreursClient.CLEF_MANQUANTE_DANS_TROUSSEAU.value, "msg": "No matching masterkey found in keyring"})
    
    client = sessions_maitres[int(data["mastertoken"])]
    if no_timeout:
        if client.dernier_keepalive + temps_max_keepalive < int(time.time()):   # timeout
            return False, json.dumps({"status": "error", "code": erreursClient.TIMEOUT_RELOGIN.value, "msg": "Timed out. Please relogin"})

    client.dernier_keepalive = int(time.time()) # on met à jour la date de dernier contact
    return True, data


@route('/hello')
def hello():
    return "Hello World!"


@route('/api/v1/info')
def api_info():
    """Retournes les infos système"""
    #response.headers['Content-Type'] = 'application/json'
    return version


@post('/api/v1/register-master')
def register_maitre():   # on commence par enregistrer le controlleur
    clef = request.forms.get('key')
    nom  = request.forms.get('name') # nom proposé par le client
    
    nom = "***UNNAMED MASTER***" if nom is None else nom.replace('-', '')
    nom.replace('#', '')

    if clef != clef_secrete :
        return json.dumps({"status": "error", "msg": "Authentification failed", "code": erreursClient.ECHEC_AUTH.value})
    else:
        # on cree un jeton unique pour le maitre
        token_session = random.randint(0, 2**255-1)
        while token_session in sessions_maitres:
            token_session = random.randint(0, 2**255-1)

        # on garantit l'unicité du nom
        if nom not in compteur_utilisation_noms:
            compteur_utilisation_noms[nom] = 0
        else:
            compteur_utilisation_noms[nom] += 1
            nom = nom + "-" + str(compteur_utilisation_noms[nom])
        

        sessions_maitres[token_session] = clientMaitre(nom, token_session, keepalive=int(time.time()), statut=statutClient.CONNECTE)
        return json.dumps({"status": "ok", "msg": "Authentification succeeded", "code": erreursClient.PAS_ERREUR.value, "master_token": token_session, "name": nom})


@post('/api/v1/register-nodes')
def register_nodes():
    """Une fois le maître connecté, on ajoute les noeuds de calcul"""

    s = sanitize()
    if not s[0]:
        return s[1]
    
    data = dict(s[1])
    if "nodenumber" not in data:
        return json.dumps({"status": "error", "msg": "Missing field \'nodenumber\'", "code": erreursClient.MANQUE_CHAMP_REQUETE.value})
    
    client = sessions_maitres[int(data["mastertoken"])]
    nb_noeuds = int(data["nodenumber"])

    for i in range(nb_noeuds):
        client.ajouter_noeud()
    
    return json.dumps({"status": "ok", "msg": "Successfully initialized {} nodes".format(nb_noeuds), "code": erreursClient.PAS_ERREUR.value})
   

@post('/api/v1/fetch-nodes')
def disp_nodes():
    s = sanitize()
    if not s[0]:
        return s[1]
    
    data = dict(s[1])
    client = sessions_maitres[int(data["mastertoken"])]
    liste_noeuds = client.liste_noeuds()
    out = {}
    for z in liste_noeuds:
        out[int(z[0])] = str(z[1])
    return json.dumps(out, default=str)
    

@post('/api/v1/fetch-work-for-node')
def work4node():
    s = sanitize()
    if not s[0]:
        return s[1]
    
    data = dict(s[1])
    client = sessions_maitres[int(data["mastertoken"])]

    if "nodeid" not in data:
        return {"status": "error", "msg": "Missing field \'nodeid\'", "code": erreursClient.MANQUE_CHAMP_REQUETE.value}

    #if nodeid not in data:
    #    return {"status": "error", "msg": "Innvalid value for parameter \'nodeid\'", "code": erreursClient.VALEUR_INVALIDE.value}

    nodeid = data["nodeid"]
    try: 
        mon_noeud = client.recuperer_noeud(nodeid)
    except Exception as e:
        return {"status": "error", "msg": "Innvalid value for parameter \'nodeid\'", "code": erreursClient.VALEUR_INVALIDE.value}

    if mon_noeud.statut != statutNoeud.INACTIF:
        return json.dumps({"status": "error", "msg": "Node is not idle ! (status {})".format(mon_noeud.statut), "code": erreursClient.MAUVAIS_STATUT_NOEUD.value})
    
    # TODO:
    # Récupérer la tâche à effectuer... Et oui...

    # On commence à regarder si l'on n'a pas des des tâches à redistribuer qui traînent...
    if len(taches_a_redistribuer) > 0:
        work = taches_a_redistribuer.pop()
    else:
        work = sequenceur.suivant() #{"k": csc_float(3), "Tdebut": csc_float(10), "Tfin": csc_float(0.002)}
    
    if work:
        mon_noeud.statut = statutNoeud.ACTIF
        mon_noeud.tache_calcul = tacheCalcul(work)

        # TODO:
        # Consigner le travail donné

        # On est obligé de faire comme ça pour pouvoir spécifier l'encodeur par défaut
        response.headers['Content-Type'] = 'application/json'
        return json.dumps({"status": "ok", "msg": "Successfully allocated work", "code": erreursClient.PAS_ERREUR.value, "task-payload": work}, default=str)
    else:
        return json.dumps({"status": "error", "msg": "No mork work to allocate", "code": erreursClient.PLUS_DE_TRAVAIL.value}, default=str)





@post('/api/v1/submit-results')
def submit_results():
    s = sanitize()
    if not s[0]:
        return s[1]
    
    data = dict(s[1])
    client = sessions_maitres[int(data["mastertoken"])]

    if "nodeid" not in data:
        return {"status": "error", "msg": "Missing field \'nodeid\'", "code": erreursClient.MANQUE_CHAMP_REQUETE.value}
    if "payload" not in data:
        return {"status": "error", "msg": "Missing field \'payload\'", "code": erreursClient.MANQUE_CHAMP_REQUETE.value}

    nodeid = data["nodeid"]
    
    mon_noeud = client.recuperer_noeud(nodeid)
    if mon_noeud.statut != statutNoeud.ACTIF:
        return {"status": "error", "msg": "Node is not active ! (status {})".format(mon_noeud.statut), "code": erreursClient.MAUVAIS_STATUT_NOEUD.value}

    resultats = data["payload"]
    print("Résultats du noeud {}#{}: {}".format(client.nom, nodeid, resultats))


    #TODO: Valider les résultats obtenus puis les consigner dans la base de donnée

    maBDD.enregistrer(resultats)
    mon_noeud.statut = statutNoeud.INACTIF
    mon_noeud.tache_calcul = None
    
    return {"status": "ok", "msg": "Work successfully submitted", "code": erreursClient.PAS_ERREUR.value}


@route('/api/v1/sysinfo')
def ret_sysinfo():
    r = {}
    for c in sessions_maitres.values():
        tmp = {}
        for idnoeud, noeud in c.liste_noeuds():
            tmp[idnoeud] = {"nom": noeud.nom, "statut": noeud.statut.value, "tache": "" if noeud.tache_calcul is None else str(noeud.tache_calcul)}
        r[c.nom] = tmp
    return {"nomprojet": nom_projet, "unites": r}
        

@post('/api/v1/unregister-master')
def unregister_master():
    s = sanitize()
    if not s[0]:
        return s[1]
    
    data = dict(s[1])

    client = sessions_maitres[int(data["mastertoken"])]
    client.deconnecter()
    return json.dumps({"status": "ok", "msg": "Successfully disconnected", "code": erreursClient.PAS_ERREUR.value})


@route('/webui/<fichier:path>')
def serve_webui(fichier):
    return static_file(fichier, root='webui/')



def init(projet: projet.projetCascada):
    global nom_projet
    global maBDD
    global sequenceur
    global mon_projet

    mon_projet = projet
    nom_projet = mon_projet.nom
    maBDD = db.controlleurBDD(nom_projet, mon_projet.schema_total(), "db_cred.json")
    sequenceur = mon_projet.sequenceur

def launch():
    run(host='localhost', port=8088, debug=True)
