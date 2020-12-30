"""Defines the main logic of the server"""

from typing import Dict, List, Tuple
from enum import Enum
import copy
import random
import json
import time
import logging

from bottle import route, run, response, request, post, static_file

import db
from projet import ProjetCascada
from vartypes import schema_vers_sch_typecode, csc_var


sessions_esclaves = {}
sessions_maitres = {}
compteur_utilisation_noms = {}


# Sometimes it might be possible that we decide the taks has to bo accomplished again,
# so we keep track of them in the following stack
taches_a_redistribuer = []

version = {"version": 1, "vendor": "coffeeXL"}
clef_secrete = "ABRACADABRA"
temps_max_keepalive = 1200  # 20 minutes; TODO: Implement support for keepalive
nom_projet = "EMPTY"


mon_projet = None
maBDD = None
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
    ECHEC_VERIFICATION = 11


class tacheCalcul():
    """A computation task, assigned to a node"""

    def __init__(self, valeurs: Dict[str, csc_var] = {}):
        """Initializes the task

        Params:
            valeurs: dictionnary with keys being the variables' name and value their value
        """

        # The variables used to make the computation, generatd by the code and sent to the node
        self.valeurs = valeurs
        self.demandeur = ""
        self.date_creation = int(time.time())
        self.date_derniere_allocation = self.date_creation
        self.norealloc = False   # used to cannibalize (ie protect from deadlocks)
        # if A -> task T1
        #    B -> task T2
        #    C -> task T1
        # A ends and is given T2
        # B ends and is given T1
        # C ends and is given T2
        #  ->> Deadlock

    def versdict(self) -> Dict[str, csc_var]:
        """Returns a dictionary which structure is akin to the one from the dictionnary supplied in init

        Returns:
            dict: dictionnary with keys being the variables' name and value their value
        """
        return self.valeurs

    def __str__(self):
        return ", ".join(["{} = {}".format(var, val) for var, val in self.valeurs.items()])

    def realloc(self) -> None:
        """Updates the last allocation date of the task"""
        self.date_derniere_allocation = int(time.time())


class NoeudCalcul():
    """A computation unit running on the slave server (ie master client)"""

    def __init__(self, nom="unnamed-node"):
        self.statut = statutNoeud.INACTIF
        self.nom = nom
        self.tache_calcul = None

    def __str__(self):
        return str(
            self.statut.value) + " [{}]".format(
            self.tache_calcul) if self.statut != statutNoeud.INACTIF else str(
            self.statut.value)

    def __repr__(self):
        return self.__str__()

    def abandonner_tache(self) -> None:
        if self.statut == statutNoeud.ACTIF:
            self.statut = statutNoeud.INACTIF
            # normally it shouldn't happen to have a None task as a status
            # buuut we never know
            if self.tache_calcul is not None:
                taches_a_redistribuer.append(self.tache_calcul)
                self.tache_calcul = None

    def charger_tache(self, tache) -> None:
        self.tache_calcul = tache
        self.statut = statutNoeud.ACTIF


class clientMaitre():
    """A slave server that manages several computation units"""

    def __init__(self, nom: str, token: str, keepalive: int = 0,
                 statut: statutClient = statutClient.NON_CONNECTE):
        """Initializes a slave server

        Params:
            nom: the name of the server
            token: an authentification token for the slave server
            keepalive: the last epoch an action related to the slave server was performed
            statut: the status of the slave server
        """

        self.nom = nom
        self.token = token
        self.statut = statut
        self.dernier_keepalive = keepalive
        self.noeuds = {}
        self.nb_noeuds_ajoutes = 0

    def deconnecter(self) -> None:
        """Disconnects the slave server (ie closes its session)"""
        del sessions_maitres[self.token]

    def ajouter_noeud(self) -> None:
        """Allocates a new computation node on the slave server"""
        nom_noeud = self.nom + "#" + str(self.nb_noeuds_ajoutes + 1)
        self.noeuds[nom_noeud] = NoeudCalcul(nom=nom_noeud)
        self.nb_noeuds_ajoutes += 1
        return nom_noeud

    def liste_noeuds(self) -> List[Tuple[str, NoeudCalcul]]:
        """Lists the avaible nodes for the slave slave"""
        return [(num, noeud) for num, noeud in self.noeuds.items()]

    def recuperer_noeud(self, idnoeud: str) -> NoeudCalcul:
        """Returns the computation node matching the id idnoeud

        Params:
            idnoeud: the id of the node
        """

        try:
            return self.noeuds[idnoeud]
        except Exception as e:
            raise e


def sanitize(no_timeout: bool = False) -> Dict[str, str]:
    """Performs various tasks on the client's request: validating its authentifcation namely

    Params:
        no_timeout: Disables client desauthentification based on timeout

    Returns
        bool: True if the slave server was successfully authentificated, False if not
        dict: if the client was not authentificated, returns a dict containing the message that
            should be transmitted to the client. If the client was authentificated, returns
            the POST data the client sent.
    """

    try:
        data = dict(request.json)
    except BaseException:
        raise ValueError

    if data is None:
        raise ValueError

    if data["mastertoken"] not in sessions_maitres.keys():
        return False, {"status": "error",
                       "code": erreursClient.CLEF_MANQUANTE_DANS_TROUSSEAU.value,
                       "msg": "No matching masterkey found in keyring"}

    client = sessions_maitres[data["mastertoken"]]
    if no_timeout:
        if client.dernier_keepalive + temps_max_keepalive < int(time.time()):   # timeout
            return False, {"status": "error", "code": erreursClient.TIMEOUT_RELOGIN.value,
                           "msg": "Timed out. Please relogin"}

    client.dernier_keepalive = int(time.time())  # updates the last contact date
    return True, data


@route('/hello')
def hello():
    """Used for tests"""
    return "Hello World!"


@route('/api/v1/info')
def api_info():
    """Returns system info"""
    return version


@post('/api/v1/register-master')
def register_maitre():   # we start be registering the slave server
    """Registers a slave server"""

    res = dict(request.json)

    # pylint: disable=no-member
    if res is None:
        clef = request.forms.get('key')
        nom = request.forms.get('name')  # name suggested by the client, that may or may not be used
    else:
        clef = res["key"] if "key" in res else None
        nom = res["name"] if "name" in res else None

    nom = "***UNNAMED MASTER***" if nom is None else nom.replace('-', '')
    nom.replace('#', '')

    if clef != clef_secrete:
        return {
            "status": "error",
            "msg": "Authentification failed",
            "code": erreursClient.ECHEC_AUTH.value}
    else:
        # we create a master auth token for the client
        token_session = str(random.randint(0, 2**255 - 1))
        while token_session in sessions_maitres:
            token_session = str(random.randint(0, 2**255 - 1))

        # guarantees the name's unicity
        if nom not in compteur_utilisation_noms:
            compteur_utilisation_noms[nom] = 0
        else:
            compteur_utilisation_noms[nom] += 1
            nom = nom + "-" + str(compteur_utilisation_noms[nom])

        sessions_maitres[token_session] = clientMaitre(
            nom, token_session, keepalive=int(
                time.time()), statut=statutClient.CONNECTE)
        logging.info("The slave server {} [{}] has connected".format(
            nom, request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR')))
        return {
            "status": "ok",
            "msg": "Authentification succeeded",
            "code": erreursClient.PAS_ERREUR.value,
            "master_token": token_session,
            "name": nom,
            "project": {
                "algo": mon_projet.algo,
                "name": mon_projet.nom,
                "scheme_in": schema_vers_sch_typecode(
                    mon_projet.schema_entree),
                "scheme_out": schema_vers_sch_typecode(
                    mon_projet.schema_sortie)}}


@post('/api/v1/register-nodes')
def register_nodes():
    """Once that the slave server is connected, we can allocate nodes for it"""

    s = sanitize()
    if not s[0]:
        return s[1]

    data = s[1]
    if "nodenumber" not in data:
        return json.dumps({"status": "error",
                           "msg": "Missing field \'nodenumber\'",
                           "code": erreursClient.MANQUE_CHAMP_REQUETE.value})

    client = sessions_maitres[data["mastertoken"]]
    nb_noeuds = int(data["nodenumber"])
    noms_noeuds = []
    for i in range(nb_noeuds):
        noms_noeuds.append(client.ajouter_noeud())

    logging.info("The slave server {} has initialized {} nodes".format(client.nom, nb_noeuds))
    return json.dumps({"status": "ok", "msg": "Successfully initialized {} nodes".format(
        nb_noeuds), "code": erreursClient.PAS_ERREUR.value, "nodenames": noms_noeuds})


@post('/api/v1/fetch-nodes')
def disp_nodes():
    """Returns a list of available nodes for the slave server"""

    s = sanitize()
    if not s[0]:
        return s[1]

    data = dict(s[1])
    client = sessions_maitres[data["mastertoken"]]
    liste_noeuds = client.liste_noeuds()
    out = []
    for z in liste_noeuds:
        out.append(z[0])
    return json.dumps(out, default=str)


@post('/api/v1/fetch-work-for-node')
def work4node():
    """Very important function, that allocates work to a node
    The code might seem long, but it's heavily commented"""

    s = sanitize()
    if not s[0]:
        return s[1]

    data = dict(s[1])
    client = sessions_maitres[data["mastertoken"]]

    if "nodeid" not in data:
        return {"status": "error", "msg": "Missing field \'nodeid\'",
                "code": erreursClient.MANQUE_CHAMP_REQUETE.value}

    # if nodeid not in data:
    # return {"status": "error", "msg": "Innvalid value for parameter
    # \'nodeid\'", "code": erreursClient.VALEUR_INVALIDE.value}

    nodeid = data["nodeid"]
    try:
        mon_noeud = client.recuperer_noeud(nodeid)
    except Exception:  # as e:
        return {
            "status": "error",
            "msg": "Invalid value for parameter \'nodeid\'",
            "code": erreursClient.VALEUR_INVALIDE.value}

    if mon_noeud.statut != statutNoeud.INACTIF:
        return {"status": "error", "msg": "Node is not idle ! (status {})".format(
            mon_noeud.statut), "code": erreursClient.MAUVAIS_STATUT_NOEUD.value}

    # First off, we have to check whether we have rejected tasks that could be allocated
    # If that's not the case, we have to generate it: if it is already in the databse, we skip it
    # The "while True" is not a real infinite loop, because taches_a_redistribuer is necessarily
    # smaller than the finite set of generated values by the sequencer, we do iterate
    # through said sequencer's values and when we're done we break the loop
    while True:
        if len(taches_a_redistribuer) > 0:
            work = taches_a_redistribuer.pop()
            print("Work {} fetched from rejections stack".format(work))
            break
        else:
            # {"k": csc_float(3), "Tdebut": csc_float(10), "Tfin": csc_float(0.002)}
            work = sequenceur.suivant()
            while work and not mon_projet.valider(work):
                # if the submitted work is deemed invalid
                # (for instance, a sqrt that was computed to be
                # negative), it could mean there was a transimission
                # issue or a bug in the client (and not necessarily that
                # the algorithm itself is flawed): the task is rejected
                # to be reallocated later
                work = sequenceur.suivant()

            if not work or not maBDD.existe(work):
                if work is not None:
                    work = tacheCalcul(work)
                break
            else:
                pass

    if work:
        mon_noeud.charger_tache(work)

        # Not very elegant, be we HAVE to do this to be able the specify the default serializer
        response.headers['Content-Type'] = 'application/json'
        return json.dumps({"status": "ok",
                           "msg": "Successfully allocated work",
                           "code": erreursClient.PAS_ERREUR.value,
                           "task-payload": work.versdict()},
                          default=lambda x: x.value)
    else:
        # There's no rejected task to distribute and the sequence is exhausted :/
        # We start "cannibalizing" the task by reallocated the oldest task
        # (which client might have stalled) to work-hungry newcomers

        tache_ancienne = None
        for client in sessions_maitres.values():
            for noeud in client.liste_noeuds():
                if noeud[1].tache_calcul and not noeud[1].tache_calcul.norealloc:
                    if tache_ancienne is None:
                        tache_ancienne = noeud[1].tache_calcul

                    elif noeud[1].tache_calcul is not None \
                        and noeud[1].tache_calcul.date_derniere_allocation \
                            < tache_ancienne.date_derniere_allocation:

                        tache_ancienne = noeud[1].tache_calcul

        if tache_ancienne is None:
            # Everybody's done, it's getting complicated to allocate new tasks
            # We try to densify if it is possible
            if not maBDD.densification_en_cours():
                if mon_projet.nb_densifications_effectuees < mon_projet.nb_densifications:
                    maBDD.densifier(mon_projet.facteur_selection, mon_projet.var_densification)
                    # We keep the old sequencer as we will need it to know the number of iterations
                    # for each variable (the sequencer is reloaded after each scheme change, if we
                    # have 2 level 2 schemes, the 2nd scheme whould use the data from the first
                    # level 2 scheme if we did not save the father (here, it's the level 1 scheme))
                    mon_projet.ancien_sequenceur = copy.deepcopy(mon_projet.sequenceur)
                    mon_projet.nb_densifications_effectuees += 1

            # what if the densification doesn't happen (because of an error for instance) ?
            # in that special case, an error mesage is returned.
            # else...
            if maBDD.densification_en_cours():

                # if we've already started a densification sequence, we reload the new scheme
                # the DB returns a dictionnary which shape is:
                # {'<var name>': (central value, start, end), ...}
                # we don't really need the central value, but we do need the number of iterations
                # (which is not supplied)
                # we get it by looking throught the scheme
                nouv_sch = {}
                resultat_dens = maBDD.schema_suivant(mon_projet.schema_densification)
                if resultat_dens:  # Watch out for the None case !
                    nombre_valeurs_differentes = 0

                    # We start by counting the number of variables having differents limits
                    # This number can be interpreted as the number of dimensions in the
                    # densification space
                    # Then, knowing the volume of the densification hyperrectangle
                    # (it is multiplied by mon_projet.facteur_amplification) we can guess
                    # the length of the edges (ie the number of iterations)
                    for xn, xv in resultat_dens.items():
                        if xv[1] != xv[2]:
                            nombre_valeurs_differentes += 1

                    # If nombre_valeurs_differentes is 0, we have an issue for the computation
                    nombre_valeurs_differentes = max(1, nombre_valeurs_differentes)
                    for xn, xv in resultat_dens.items():
                        if xv[1] != xv[2]:
                            nouv_sch[xn] = (
                                xv[1], xv[2], int(
                                    mon_projet.facteur_amplification**(
                                        1 / nombre_valeurs_differentes)
                                    * mon_projet.ancien_sequenceur.nb_iters_pour_variable(xn)))
                        else:
                            # If <start> = <end>, there is no use in iterating
                            # Note: we reload only the values specified in the densification scheme,
                            # so if there are variables that were made not to be densified
                            # (for instance dummy variables made to repeat the same computation
                            # several times), an easy solution is not to include them in the
                            # densification scheme
                            nouv_sch[xn] = (xv[1], xv[2], 1)
                    logging.info("\tReloading a new scheme {}".format(nouv_sch))
                    mon_projet.sequenceur.recharger_bornes_pas(nouv_sch)

                # We've reloaded everything that we had to
                # -> we re-run the request
                return work4node()

            if not mon_projet.execution_terminee:
                logging.warning("Done, no more tasks to allocate !")
                mon_projet.execution_terminee = True

            return {
                "status": "error",
                "msg": "No mork work to allocate",
                "code": erreursClient.PLUS_DE_TRAVAIL.value}
        else:
            # Met à jour la date de dernière allocation
            print("Cannibalizing {}".format(tache_ancienne))
            tache_ancienne.realloc()
            mon_noeud.charger_tache(tache_ancienne)

            response.headers['Content-Type'] = 'application/json'
            return json.dumps({"status": "ok",
                               "msg": "Successfully allocated work",
                               "code": erreursClient.PAS_ERREUR.value,
                               "task-payload": tache_ancienne.versdict()},
                              default=lambda x: x.value)


@post('/api/v1/submit-results')
def submit_results():
    """Used by the slave server to submit its computation results"""

    s = sanitize()
    if not s[0]:
        return s[1]

    data = dict(s[1])
    client = sessions_maitres[data["mastertoken"]]

    if "nodeid" not in data:
        return {"status": "error", "msg": "Missing field \'nodeid\'",
                "code": erreursClient.MANQUE_CHAMP_REQUETE.value}
    if "payload" not in data:
        return {"status": "error", "msg": "Missing field \'payload\'",
                "code": erreursClient.MANQUE_CHAMP_REQUETE.value}

    nodeid = data["nodeid"]

    try:
        mon_noeud = client.recuperer_noeud(nodeid)
    except Exception:
        return {
            "status": "error",
            "msg": "No matching node found",
            "code": erreursClient.NOEUD_INEXISTANT.value}

    if mon_noeud.statut != statutNoeud.ACTIF:
        return {"status": "error", "msg": "Node is not active ! (status {})".format(
            mon_noeud.statut), "code": erreursClient.MAUVAIS_STATUT_NOEUD.value}

    resultats = data["payload"]

    # Whatever happens, the task is taken away from the node:
    #   -> if everything is OK: great !
    #   -> if not: we will hand it out again at a later time
    # Note: TODO: maybe we should make it so that the same node isn't
    # reallocated the same task it failed to compute...

    resultats_purifies = {}
    schema_complet = mon_projet.schema_total()
    for l in schema_complet:
        # Part of the answer is missing -> we reject it
        if l not in resultats:
            mon_noeud.abandonner_tache()
            return {"status": "error", "msg": "Missing variable '{}' in payload".format(
                l), "code": erreursClient.MANQUE_VARIABLE_RESULTATS.value}
        else:
            resultats_purifies[l] = schema_complet[l](resultats[l])

    # Task was rejected
    if not mon_projet.valider(resultats_purifies):
        mon_noeud.abandonner_tache()
        return {
            "status": "error",
            "msg": "Submition validation failed",
            "code": erreursClient.ECHEC_VALIDATION.value}

    resultats = {**mon_noeud.tache_calcul.valeurs, **resultats_purifies}

    mon_noeud.statut = statutNoeud.INACTIF
    mon_noeud.tache_calcul.norealloc = True
    mon_noeud.tache_calcul = None

    maBDD.enregistrer(resultats)

    return {
        "status": "ok",
        "msg": "Work successfully submitted",
        "code": erreursClient.PAS_ERREUR.value}


@post('/api/v1/drop-task')
def drop_task():
    """Used by the slave server to drop a task"""

    s = sanitize()
    if not s[0]:
        return s[1]

    data = dict(s[1])
    client = sessions_maitres[data["mastertoken"]]

    if "nodeid" not in data:
        return {"status": "error", "msg": "Missing field \'nodeid\'",
                "code": erreursClient.MANQUE_CHAMP_REQUETE.value}

    nodeid = data["nodeid"]

    try:
        mon_noeud = client.recuperer_noeud(nodeid)
    except Exception:
        return {
            "status": "error",
            "msg": "No matching node found",
            "code": erreursClient.NOEUD_INEXISTANT.value}

    if mon_noeud.statut != statutNoeud.ACTIF:
        return {"status": "error", "msg": "Node is not active ! (status {})".format(
            mon_noeud.statut), "code": erreursClient.MAUVAIS_STATUT_NOEUD.value}

    mon_noeud.abandonner_tache()

    return {
        "status": "ok",
        "msg": "Task successfully drop for node '{}'".format(mon_noeud),
        "code": erreursClient.PAS_ERREUR}


@route('/api/v1/sysinfo')
def ret_sysinfo():
    """This is used by the webui to fetch infos about the current state of the system
    TODO: add a caching system for the data sent to the webui (useful if there are many webuis
    running on different computers)"""

    r = {}
    for c in sessions_maitres.values():
        tmp = {}
        for idnoeud, noeud in c.liste_noeuds():
            tmp[idnoeud] = {
                "nom": noeud.nom,
                "statut": noeud.statut.value,
                "tache": "" if noeud.tache_calcul is None else str(
                    noeud.tache_calcul)}
        r[c.nom] = tmp

    # computes the % of completation of the current densification level
    #
    avancement = 0

    if mon_projet.sequenceur.nb_iters_total == 0:
        avancement = 1.0
    else:
        if mon_projet.nb_densifications_effectuees == 0:
            avancement = mon_projet.sequenceur.nb_iters_realisees \
                / mon_projet.sequenceur.nb_iters_total
        else:
            if maBDD.limite_select == 0:
                avancement = 1.0
            else:
                avancement = (mon_projet.sequenceur.nb_iters_realisees
                              + mon_projet.sequenceur.nb_iters_total
                              * (maBDD.offset_cour_densification - 1)) / \
                    (maBDD.limite_select * mon_projet.sequenceur.nb_iters_total)

    return {
        "nomprojet": nom_projet,
        "unites": r,
        "nb_densifications_totales": mon_projet.nb_densifications,
        "nb_densifcations_effectuees": mon_projet.nb_densifications_effectuees,
        "avancement": avancement}


@post('/api/v1/unregister-master')
def unregister_master():
    """Used by the slave server to disconnect in a clean fashion"""

    s = sanitize()
    if not s[0]:
        return s[1]

    data = dict(s[1])

    client = sessions_maitres[data["mastertoken"]]
    nom = client.nom
    for noeud in client.noeuds.values():
        noeud.abandonner_tache()
    client.deconnecter()
    logging.info("Slave server {} [{}] has disconnected".format(
        nom, request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR')))
    return json.dumps({"status": "ok",
                       "msg": "Successfully disconnected",
                       "code": erreursClient.PAS_ERREUR.value})


@route('/webui/<fichier:path>')
def serve_webui(fichier):
    """Used to serve the static webui files"""

    return static_file(fichier, root='webui/')


def init(projet: ProjetCascada) -> None:
    """Initializes the server.

    Params:
        projet: the cascada project object
    """

    global nom_projet
    global maBDD
    global sequenceur
    global mon_projet

    logging.info("\n\n\n")
    logging.info("**** SERVER INITIALIZATION ****")
    logging.info("Project summary")
    logging.info("\tName: {}".format(projet.nom))
    logging.info("\tInput scheme:  {}".format(projet.schema_entree))
    logging.info("\tOut scheme: {}".format(projet.schema_sortie))
    logging.info("\tDensification scheme: {}".format(projet.schema_densification))

    mon_projet = projet
    nom_projet = mon_projet.nom
    maBDD = db.controlleurBDD(nom_projet, mon_projet.schema_total(), "db_cred.json")
    sequenceur = mon_projet.sequenceur


def launch(port: int = 8088, host: str = '0.0.0.0') -> None:
    """Launches the server.

    Params:
        port: the port the server should listen on
        host: the adress the server should bind to

    Returns:
        None

    Note:
        To be called after init()
    """

    logging.info("**** SERVER IS STARTING ****")
    run(host=host, port=port, debug=False)
