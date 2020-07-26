# Ici on gère la connexion à la base de donnée pour consigner les résultats
import mysql.connector
import json
import logging
import math

import vartypes


class BDDException(Exception):
    pass

class BDDExceptionTableNonValidee(BDDException):
    """Le nom de projet fourni correspond à une table déjà existente et incompatible avec le 
    schema fourni"""

class BDDExceptionVariableNonValide(BDDException):
    """Un des noms de variable utilisé a été rejeté par le système de stockage. Veuillez en choisir un autre"""

class BDDExceptionResultatsIngerable(BDDException):
    """Le résultat de la requête n'est pas traitable par le programme"""

class controlleurBDD():
    def __init__(self, nom_projet, schema, fichier_login):
        """Initialise le controlleur de base de données
        Params:
            nom_projet     (str): le nom donné au projet, utilisé pour créer/ouvrir une table
            schema        (dict): le schéma de données utilisé. Par exemple pour deux variables
                                  K (float) et n (unit32) qui me renvoient E (float), le schéma
                                  est {"K": csc_float, "n": csc_uint32, "E": csc_float}
            fichier_login (str):  le bom du fichier utilisé pour se connecter à la base de doonnées

        Returns:
            None
        """

        self.nom_projet = nom_projet
        self.schema = schema


        if "id" in schema or "niv_densification" in schema:
            raise BDDExceptionVariableNonValide


        with open(fichier_login, "r") as f:
            self.creds = json.load(f)

        logging.info("Connexion à la BDD \"{}\" avec l'utilisateur {}@{}".format(self.creds["db"], self.creds["user"], self.creds["host"]))
        
        self.cnx = mysql.connector.connect(
        host=self.creds["host"],
        port=self.creds["port"],
        user=self.creds["user"],
        password=self.creds["pass"],
        database=self.creds["db"])
    
        self.seuil_densification         = None
        self.variable_densification      = None
        self.offset_cour_densification   = 0
        self.limite_select = None

        self.densifie = False

        self.a_afficher_erreur_plus_echantillon = False

        # la profondeur de densification
        # on est obligé de l'intégrer à la table sinon dès qu'on passera à un niveau supérieur
        # cela risque de "noyer" les bons candidats du niveau inférieur
        self.niveau_densification = 1

        
        cursor = self.cnx.cursor()

        # On va commencer par voir si une table de donnée avec le nom du projet existe déjà
        r = cursor.execute("""SELECT COUNT(*)
                                FROM information_schema.tables
                                WHERE table_name = %s AND table_schema = %s
                                LIMIT 1""", (nom_projet, self.creds["db"]))
        
        # on est obligé d'itéter sur le résultat de cursor.execute pour faire avancer la requête...
        nb_tables = cursor.fetchone()[0]
    
        schema_sql = [nom + " " + str(vartype.to_SQL_type()) for nom, vartype in schema.items()]
        schema_sql.append("niv_densification INT UNSIGNED ")
        schema_sql.append("id INT NOT NULL AUTO_INCREMENT, PRIMARY KEY (id)")

        if nb_tables != 0:
            logging.info("Arrrh, la table {} existe !".format(nom_projet))    # on suppose que la table est valide (il faut qu'elle soit compatible)
            # TODO: Verifier que la table est compatible -> vérifier niv_densification
            cursor.execute("DESCRIBE {};".format(nom_projet))
            for r in cursor:
                # Le nom...
                if r[0] in schema:
                    # Le type...
                    if str(r[1]).casefold() != str(schema[r[0]].to_SQL_type()).casefold():
                        raise BDDExceptionTableNonValidee
                elif r[0] == "niv_densification":
                    if str(r[1]).casefold() != str(vartypes.csc_uint32.to_SQL_type()).casefold():
                        raise BDDExceptionTableNonValidee

            logging.info("Table validée")
        else:       # la table n'existe pas, donc on la créée
            # TODO: Essayer de trouver une meilleure solution, sinon bonjour les injections SQL !
            cursor.execute("CREATE TABLE {} ({});".format(nom_projet, ", ".join(schema_sql)))
            logging.info("La table {} n'existait pas, on vient de la créer !".format(nom_projet))
        cursor.close()

    def enregistrer(self, resultat):
        """Enregistre le résultat d'un calcule dans la base de données
        Params:
            resultat (dict): le résultat du calcul, sous la forme {"nom variable": valeur variable}.
                            Idéalement, le schéma doit reprendre celui utilisé pour initialiser le controlleur
                            Exemple:
                                {"K": csc_float(7.4), "n": csc_uint32(14638), "E": csc_float(15.9)}
        Returns:
            None
        """
        cursor = self.cnx.cursor()
        # Par sécurité, on force un recast
        r2 = {}
        for nom, type_var in self.schema.items():
            r2[nom] = type_var(resultat[nom])
        resultat = r2
        resultat["niv_densification"] = vartypes.csc_int32(self.niveau_densification)
        cursor.execute("""INSERT INTO {} ({}) VALUES ({})""".format(self.nom_projet, 
                                                                    ", ".join(resultat.keys()),
                                                                    ", ".join([r'%s' for x in resultat.keys()])),
                                                    tuple([str(x) for x in resultat.values()]))
        self.cnx.commit()
        cursor.close()
    
    def existe(self, valeurs):
        """Vérifie s'il existe un enregistrement contenant valeurs
        
        Params:
            valeurs (dict): les valeurs prises par les variables, par exemple
                            {"K": csc_float(7.4), "n": csc_uint32(14638), "E": csc_float(15.9)}
        Returns:
            None
        """
        cursor = self.cnx.cursor(dictionary=True)
        cursor.execute("""SELECT COUNT(*) AS C FROM {} WHERE {}""".format(self.nom_projet,
                                                                        " AND ".join([ "{} = {}".format(var, str(val)) 
                                                                                            for var, val in valeurs.items()])) )
        res = cursor.fetchone()["C"]
        cursor.close()
        return res != 0
    
    def densifier(self, seuil: float, variable: str, offset: int = 0):
        # On extrait que les meilleurs enregistrement au sens de variable (ceux qui MAXIMISENT <variable>)

        
        
        if not 0<seuil<=1:
            raise ValueError 

        if variable not in self.schema:
            raise KeyError

        
        self.densifie = True


        # On garde en mémoire les paramètres que l'on nous a donné en entré car on
        # pourra en avoir besoin par la suite si le curseur périme.
        self.seuil_densification = seuil
        self.offset_cour_densification = offset
        self.variable_densification = variable

        # On commence par regarder le nombre d'enregistrements
        cursor = self.cnx.cursor(dictionary=True)
        cursor.execute("""SELECT COUNT(*) AS C FROM {} WHERE niv_densification={}""".format(self.nom_projet, self.niveau_densification))
        count = int(cursor.fetchone()["C"])
        cursor.close()

        logging.info("Procédure de densification sur {} initiée. Le niveau de densification actuel est {}; ce niveau a engendré {} échantillons".format(
                                                                                                self.variable_densification,
                                                                                                self.niveau_densification,
                                                                                                count
        ))

        


        # De là on déduit le nombre d'enregistrements qu'on va garder
        if self.niveau_densification == 1:
            limite = int(math.ceil(seuil*count))
        else:
            # On sait qu'au coup précédent on a tiré limite_select configurations,
            # donc chaque configuration aura eu count/limite_select itérations
            # On met un max pour éviter que ça plante
            limite = int(math.ceil(seuil*count/max(self.limite_select,1)))
        
        if limite == 0 and not self.a_afficher_erreur_plus_echantillon:
            logging.warning("Aucun échantillon trouvé. " \
            "Cause probable: les échantillons de cet étape ont tous été déjà calculés précédement. " \
            "Solution: Ajuster les paramètres numériques de densification" \
            "Le problème va se répéter pour les autres densifications mais cet avertissement ne s'affichera qu'une fois")
            self.a_afficher_erreur_plus_echantillon = True

        self.limite_select = limite


        logging.info("\tPour cette séquence de densification, {} schémas seront tirés".format(limite))

        self.niveau_densification += 1
        
    
    def schema_suivant(self, schema_entree):
        """Permet de réaliser le gros de l'opération de densification
        Cela consiste à repérer les meilleurs configuration d'entrée pour "zoomer"
        dessus et augmenter la résolution au voisinage de ces points
        
        Params:
            schema_entree (dict): un schéma de la même forme que celui utiliser pour initialiser le controlleur de base de donnée
                                    à ceci près qu'il ne contient que les données en entrée: en effet, cela n'a pas de sens d'optimiser
                                    ce qu'on va donner aux noeuds en se basant sur la sortie desdits noeuds (sauf bien sûr pour la
                                    variable qu'on utilise pour tri les schémas, mais ça c'est pour la fonction  densifier)
        
        Returns:
            dict: un dictionnaire, qui a comme clef les variables de schema_entree et comme valeurs un triplet (<valeur intéressante>,
            <voisin immédiatement en dessous>, <voisin immédiatement au dessus>). Quand il n'y a pas de tel voisin, la fonction les
            remplace par <valeur intéressante>. Si on est la fin de l'itération, la fonction renvoit None; dans ce cas, il faut faire
            un nouvel appel à densifier.

        Notes:
            Attention, cette fonction doit être appelée après l'appel à  densifier . Bien vérifier avant de l'appeler qu'une
            densification est en cours (qu'on a pas épuisé toutes les valeurs pour ce niveau de densification)
        
        """

        if not self.densifie:
            return None
        


        cursor = self.cnx.cursor(dictionary=True)

        # On commence par extraire l'enregistrement avec les coordonnées bonnes
        cursor.execute("""SELECT * FROM {} WHERE niv_densification = {}-1 ORDER BY {} DESC LIMIT 1 OFFSET {}""".format(self.nom_projet,
                                                                                        self.niveau_densification,
                                                                                        self.variable_densification,
                                                                                        self.offset_cour_densification))
        
        sch = cursor.fetchone()
        if sch is None:
            self.densifie = False
            return None
        

        self.offset_cour_densification += 1


        cursor.close()

        cursor = self.cnx.cursor()
        sch_vrai = {}
        # On reacast (ULTRA IMPORTANT POUR LES FLOAT, à cause de la précision
        # en gros MySQL n'affiche que la partie significante des floats mais 
        # attend la valeur "longue" bien qu'absudre, qu'on obtient en recastant)
        for n in schema_entree:
            sch_vrai[n] = schema_entree[n](sch[n])

        # on reprend le niveau de densification précédent
        sch_vrai["niv_densification"] = vartypes.csc_int32(self.niveau_densification - 1)

        # Ensuite on va chercher pour chaque coordonnée ses plus proches voisins en fixant les autres coordonnées
        xs = {xn: "{} = {}".format(xn, xv) for xn, xv in sch_vrai.items()}

        bornes = {}

        for n, v in sch_vrai.items():
            # On ne prend pas en compte la variable de densification car c'est elle qu'on cherche à maximiser
            if n != self.variable_densification and n != "niv_densification":
                val_python = sch[n]
                s = " AND ".join(filter(None, [xs[xn] if (xn != n and xn != self.variable_densification) else None for xn in sch_vrai]))

                # cf https://ask.sqlservercentral.com/questions/103011/retrieve-closest-upper-and-lower-values.html
                # on récupère les plus proches voisins
                
                cursor.execute("""SELECT
                                        CASE SIGN({}-{})
                                            WHEN 1 THEN MIN({})
                                            ELSE        MAX({})
                                        END 
                                AS  {}
                                FROM {} AS xV
                                WHERE {} 
                                GROUP BY SIGN({}-{}) 
                                HAVING SIGN({}-{}) != 0
                                """.format(n, v, n, n, n, self.nom_projet,
                                                                s, n, v, n, v))

                res = cursor.fetchall()

                # Problème: les données sont renvoyées par le connecteurs sous la forme d'un tuple
                r = []
                for x in res:
                    if isinstance(x, tuple):
                        r.append(*x)
                    else:
                        r.append(x)
                res = r
                res.sort()

                if len(res) == 2:
                    bornes[n] = tuple([val_python, *res])
                elif len(res) == 1:
                    if res[0] < val_python:
                        bornes[n] = (val_python, res[0], val_python)
                    else:
                        bornes[n] = (val_python, val_python, res[0])
                elif len(res) == 0:
                    bornes[n] = (val_python, val_python, val_python)
                else:
                    raise BDDExceptionResultatsIngerable
            
        if self.offset_cour_densification >= self.limite_select:
            self.densifie = False

        # offset_cour_densification-1 car on vient de l'incrémenter
        logging.info("\tNouveau schéma tiré: {}, offset {}".format(bornes, self.offset_cour_densification-1))

        return bornes


    def densification_en_cours(self):
        return self.densifie
    

if __name__ == '__main__':
    #A = controlleurBDD("test2", {"K": csc_float, "n": csc_uint32, "E": csc_float}, "db_cred.json")
    schema = {"K": vartypes.csc_float, "Tdeb": vartypes.csc_float, "Tfin": vartypes.csc_float, "lambda": vartypes.csc_float, "E": vartypes.csc_float}
    A = controlleurBDD("Glissade_rapide", schema, "db_cred.json")
    #print(A.existe({"K": csc_float(7.4), "n": csc_uint32(14638), "E": csc_float(15.9)}))
    #print(A.existe({"K": csc_float(7.3), "n": csc_uint32(14638), "E": csc_float(15.9)}))
    A.densifier(0.01, "E")
    for i in range(35):
        print(A.schema_suivant({"K": vartypes.csc_float, "Tdeb": vartypes.csc_float, "Tfin": vartypes.csc_float, "lambda": vartypes.csc_float}))