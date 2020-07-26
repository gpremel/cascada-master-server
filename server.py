from bottle import route, run, response, request, post, static_file

from enum import Enum
import copy
import random
import json
import time
import logging

import db
import projet
from vartypes import *


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
    MANQUE_VARIABLE_RESULTATS = 8
    ECHEC_VALIDATION = 9
    NOEUD_INEXISTANT = 10



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
        self.date_creation = int(time.time())
        self.date_derniere_allocation = self.date_creation

    def versdict(self):
        return self.valeurs
    
    def __str__(self):
        return ", ".join(["{} = {}".format(var, val) for var, val in self.valeurs.items()])
    
    def realloc(self):
        self.date_derniere_allocation = int(time.time())


class noeudCalcul():
    def __init__(self, nom="unnamed-node"):
        self.statut = statutNoeud.INACTIF
        self.nom = nom
        self.tache_calcul = None

    def __str__(self):
        return str(self.statut.value) + " [{}]".format(self.tache_calcul) if self.statut != statutNoeud.INACTIF else str(self.statut.value)
    
    def __repr__(self):
        return self.__str__()

    def abandonner_tache(self):
        if self.statut == statutNoeud.ACTIF:
            self.statut = statutNoeud.INACTIF
            # normalement ça ne devrait pas arriver d'avor une tâche None en statut
            # actif mais bon on ne sait jamais
            if self.tache_calcul is not None:
                taches_a_redistribuer.append(self.tache_calcul)
                self.tache_calcul = None

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
        logging.info("Le client maître {} [{}] s'est connecté".format(nom, request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR')))
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
    
    logging.info("Le client maître {} a initialisé {} noeuds".format(client.nom, nb_noeuds))
    return json.dumps({"status": "ok", "msg": "Successfully initialized {} nodes".format(nb_noeuds), "code": erreursClient.PAS_ERREUR.value})
   

@post('/api/v1/fetch-nodes')
def disp_nodes():
    s = sanitize()
    if not s[0]:
        return s[1]
    
    data = dict(s[1])
    client = sessions_maitres[int(data["mastertoken"])]
    liste_noeuds = client.liste_noeuds()
    out = []
    for z in liste_noeuds:
        out.append(z[0])
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
        return {"status": "error", "msg": "Invalid value for parameter \'nodeid\'", "code": erreursClient.VALEUR_INVALIDE.value}

    if mon_noeud.statut != statutNoeud.INACTIF:
        return {"status": "error", "msg": "Node is not idle ! (status {})".format(mon_noeud.statut), "code": erreursClient.MAUVAIS_STATUT_NOEUD.value}
    

    # On commence à regarder si l'on n'a pas des des tâches à redistribuer qui traînent...
    # Si ce n'est pas le cas on générère une nouvelle tâche: si elle est déjà dans la bdd, on la saute
    # Pas de panique, la boucle infinie n'est pas vraiment infinie car taches_a_redistribuer est forcément plus courte que
    # l'ensemble fini des valeurs générées par le séquenceur et on fini également par arriver au bout du séquenceur
    while True:
        if len(taches_a_redistribuer) > 0:
            work = taches_a_redistribuer.pop()
            print("Travail {} réucupéré de la pile des rejections".format(work))
            break
        else:
            work = sequenceur.suivant() #{"k": csc_float(3), "Tdebut": csc_float(10), "Tfin": csc_float(0.002)}
            if not work or not maBDD.existe(work):
                if work is not None:
                    work = tacheCalcul(work)
                break
            else:
                print("Travail {} sauté car déjà existant ou None".format(work))
                

    if work:
        mon_noeud.statut = statutNoeud.ACTIF
        mon_noeud.tache_calcul = work

        # On est obligé de faire comme ça pour pouvoir spécifier l'encodeur par défaut
        response.headers['Content-Type'] = 'application/json'
        return json.dumps({"status": "ok", "msg": "Successfully allocated work", "code": erreursClient.PAS_ERREUR.value, "task-payload": work.versdict()}, default=str)
    else:
        # Là on n'a plus de tâches rejetées à refaire et la séquence est épuisée :/
        # On commence à "cannibaliser" les tâches en donnant les tâches les plus anciennes$ aux nouveaux arrivants

        tache_ancienne = None
        for client in sessions_maitres.values():
            for noeud in client.liste_noeuds():
                if tache_ancienne is None:
                    tache_ancienne = noeud[1].tache_calcul
                elif noeud[1].tache_calcul is not None and noeud[1].tache_calcul.date_derniere_allocation < tache_ancienne.date_derniere_allocation:
                    tache_ancienne = noeud[1].tache_calcul
        

        if tache_ancienne is None:
            # Tout le monde a fini, ça commence à devenir compliqué
            # On densifie si c'est possible
            if not maBDD.densification_en_cours():
                if mon_projet.nb_densifications_effectuees < mon_projet.nb_densifications:
                    maBDD.densifier(mon_projet.facteur_selection, mon_projet.var_densification)
                    # on garde l'ancien séquenceur car on va en avoir besoin pour connaître le nombre d'itération pour
                    # chaque variable (comme le séquenceur est rechargé après chaque changement de schéma, si par exemple
                    # on a 2 schéma pour le niveau 2, le 2e schéma utiliserait les données du premier schéma de niveau 2
                    # si on ne faisait pas de sauvegarde)
                    mon_projet.ancien_sequenceur = copy.deepcopy(mon_projet.sequenceur)
                    mon_projet.nb_densifications_effectuees += 1  

            # il se peut (s'il y a une erreur...) que la densification ne se fasse pas
            # dans ce cas on renvoit le message d'erreur
            # sinon...
            if maBDD.densification_en_cours():   # si on a déjà entamé une séquence de densification, on recharge un nouveau schéma
                # la BDD nous renvoit un dico de la forme:
                # {'<nom var>': (valeur centrale, début, fin), ...}
                # on n'a pas d'utilité pour la valeur centrale, par contre on a besoin du nombre d'itérations
                # on l'obtient en regardans dans le schéma
                nouv_sch = {}
                resultat_dens = maBDD.schema_suivant(mon_projet.schema_densification)
                if resultat_dens:  # Attention au cas None !
                    nombre_valeurs_differentes = 0

                    # On commence par compter le nombres de variables telles que leurs bornes soient différentes
                    # On peut voir ce nombre comme le nombre de dimensions de l'espace de densification
                    # Ensuite connaissant le volume du pavé d'optimisation (il est multiplié par un facteur mon_projet.facteur_amplification)
                    # on en déduit la longueur des arrètes (le nombre d'itération)
                    for xn, xv in resultat_dens.items():
                        if xv[1] != xv[2]:
                            nombre_valeurs_differentes += 1

                    # Si nombre_valeurs_differentes vaut 0, problème pour le calcul
                    nombre_valeurs_differentes = max(1, nombre_valeurs_differentes)        
                    for xn, xv in resultat_dens.items():
                        if xv[1] != xv[2]:
                            nouv_sch[xn] = (xv[1], xv[2], int(
                                mon_projet.facteur_amplification**(1/nombre_valeurs_differentes)*mon_projet.ancien_sequenceur.nb_iters_pour_variable(xn)))
                        else:
                            # Si <debut> = <fin>, ça ne sert à rien d'itérer plein de fois
                            # Rq: on ne retraite que le schéma de densification, donc si des variables
                            # sont faites exprès pour répéter plusieurs fois le même calcul,
                            # il suffit de ne pas les mettre dans le schéma de densification
                            nouv_sch[xn] = (xv[1], xv[2], 1)
                    logging.info("\tRechargement d'un nouveau schéma {}".format(nouv_sch))
                    mon_projet.sequenceur.recharger_bornes_pas(nouv_sch)


                # On a tout réenclenché, on relance la requête
                return work4node()

            if not mon_projet.execution_terminee:
                logging.warning("Travail terminé, plus de tâche à allouer !")
                mon_projet.execution_terminee = True

            return {"status": "error", "msg": "No mork work to allocate", "code": erreursClient.PLUS_DE_TRAVAIL.value}
        else:
            # Met à jour la date de dernière allocation
            print("Cannibalisation de {}".format(tache_ancienne))
            tache_ancienne.realloc()
            response.headers['Content-Type'] = 'application/json'
            return json.dumps({"status": "ok", "msg": "Successfully allocated work", "code": erreursClient.PAS_ERREUR.value, "task-payload": tache_ancienne.versdict()}, default=str)





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

    try:
        mon_noeud = client.recuperer_noeud(nodeid)
    except Exception:
        return {"status": "error", "msg": "No matching node found", "code": erreursClient.NOEUD_INEXISTANT.value}


    if mon_noeud.statut != statutNoeud.ACTIF:
        return {"status": "error", "msg": "Node is not active ! (status {})".format(mon_noeud.statut), "code": erreursClient.MAUVAIS_STATUT_NOEUD.value}

    resultats = data["payload"]
    print("Résultats du noeud {}: {}".format(nodeid, resultats))

    # Quoi qu'il arrive, on retire la tâche au noeud: 
    #   -> si c'est OK, tant mieux
    #   -> sinon on le redonnera après
    # Rq: TODO: il faudrait peut-être faire en sorte que ce ne soit pas ce noeud qui récupère la tâche...

    resultats_purifies = {}
    schema_complet = mon_projet.schema_total()
    for l in schema_complet:
        # Coup dur, il manque un morceau de la réponse...
        if not l in resultats:
            mon_noeud.abandonner_tache()
            return {"status": "error", "msg": "Missing variable '{}' in payload".format(l), "code": erreursClient.MANQUE_VARIABLE_RESULTATS.value}
        else:
            resultats_purifies[l] = schema_complet[l](resultats[l])

    # On demande au noeud de renvoyer les données d'entrée pour être sûr que c'est les mêmes
    # Si c'est pas la cas, on refuse la réponse
    for l in mon_projet.schema_entree:
        if resultats_purifies[l] != mon_noeud.tache_calcul.valeurs[l]:
            mon_noeud.abandonner_tache()
            return {"status": "error", "msg": "Incorrect value for '{}'".format(l), "code": erreursClient.ECHEC_VALIDATION.value}

    if not mon_projet.valider(resultats_purifies):
        mon_noeud.abandonner_tache()
        return {"status": "error", "msg": "Submition validation failed", "code": erreursClient.ECHEC_VALIDATION.value}

    resultats = {**mon_noeud.tache_calcul.valeurs, **resultats_purifies}
    
    mon_noeud.statut = statutNoeud.INACTIF
    mon_noeud.tache_calcul = None

    maBDD.enregistrer(resultats)
    
    return {"status": "ok", "msg": "Work successfully submitted", "code": erreursClient.PAS_ERREUR.value}

@post('/api/v1/drop-task')
def drop_task():
    s = sanitize()
    if not s[0]:
        return s[1]
    
    data = dict(s[1])
    client = sessions_maitres[int(data["mastertoken"])]

    if "nodeid" not in data:
        return {"status": "error", "msg": "Missing field \'nodeid\'", "code": erreursClient.MANQUE_CHAMP_REQUETE.value}

    nodeid = data["nodeid"]

    try:
        mon_noeud = client.recuperer_noeud(nodeid)
    except Exception:
        return {"status": "error", "msg": "No matching node found", "code": erreursClient.NOEUD_INEXISTANT.value}

    if mon_noeud.statut != statutNoeud.ACTIF:
        return {"status": "error", "msg": "Node is not active ! (status {})".format(mon_noeud.statut), "code": erreursClient.MAUVAIS_STATUT_NOEUD.value}

    mon_noeud.abandonner_tache()

    return {"status": "ok", "msg": "Task successfully drop for node '{}'".format(mon_noeud), "code": erreursClient.PAS_ERREUR}


@route('/api/v1/sysinfo')
def ret_sysinfo():
    r = {}
    for c in sessions_maitres.values():
        tmp = {}
        for idnoeud, noeud in c.liste_noeuds():
            tmp[idnoeud] = {"nom": noeud.nom, "statut": noeud.statut.value, "tache": "" if noeud.tache_calcul is None else str(noeud.tache_calcul)}
        r[c.nom] = tmp

    # on chercher maintenant le poucentrage de complétation de l'étape de densification en cours
    avancement = 0

    if mon_projet.sequenceur.nb_iters_total == 0:
        avancement = 1.0
    else:
        if mon_projet.nb_densifications_effectuees == 0:
            avancement = mon_projet.sequenceur.nb_iters_realisees / mon_projet.sequenceur.nb_iters_total
        else:
            if maBDD.limite_select == 0:
                avancement = 1.0
            else:
                avancement = (mon_projet.sequenceur.nb_iters_realisees + 
                                    mon_projet.sequenceur.nb_iters_total*(maBDD.offset_cour_densification-1)) / \
                                    (maBDD.limite_select*mon_projet.sequenceur.nb_iters_total)

    
    return {"nomprojet": nom_projet, "unites": r, "nb_densifications_totales": mon_projet.nb_densifications, "nb_densifcations_effectuees": mon_projet.nb_densifications_effectuees, "avancement": avancement}
        

@post('/api/v1/unregister-master')
def unregister_master():
    s = sanitize()
    if not s[0]:
        return s[1]
    
    data = dict(s[1])

    client = sessions_maitres[int(data["mastertoken"])]
    nom = client.nom
    for noeud in client.noeuds.values():
        noeud.abandonner_tache()
    client.deconnecter()
    logging.info("Le client maître {} [{}] s'est connecté".format(nom, request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR')))
    return json.dumps({"status": "ok", "msg": "Successfully disconnected", "code": erreursClient.PAS_ERREUR.value})


@route('/webui/<fichier:path>')
def serve_webui(fichier):
    return static_file(fichier, root='webui/')



def init(projet: projet.projetCascada):
    global nom_projet
    global maBDD
    global sequenceur
    global mon_projet
    
    logging.info("\n\n\n")
    logging.info("**** INITIALISATION SERVEUR ****")
    logging.info("Résumé du projet")
    logging.info("\tNom: {}".format(projet.nom))
    logging.info("\tSchéma entré:  {}".format(projet.schema_entree))
    logging.info("\tSchéma sortie: {}".format(projet.schema_sortie))
    logging.info("\tSchéma densification: {}".format(projet.schema_densification))

    mon_projet = projet
    nom_projet = mon_projet.nom
    maBDD = db.controlleurBDD(nom_projet, mon_projet.schema_total(), "db_cred.json")
    sequenceur = mon_projet.sequenceur

def launch():
    logging.info("**** DÉMARRAGE SERVEUR ****")
    run(host='0.0.0.0', port=8088, debug=True)
