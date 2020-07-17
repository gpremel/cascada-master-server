# Ici on gère la connexion à la base de donnée pour consigner les résultats
import mysql.connector
import json

from vartypes import *


class BDDException(Exception):
    pass

class BDDExceptionTableNonValidee(BDDException):
    """Le nom de projet fourni correspond à une table déjà existente et incompatible avec le 
    schema fourni"""

class BDDExceptionVariableNonValide(BDDException):
    """Un des noms de variable utilisé a été rejeté par le système de stockage. Veuillez en choisir un autre"""


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

        with open(fichier_login, "r") as f:
            self.creds = json.load(f)

        print("Connexion à la BDD \"{}\" avec l'utilisateur {}@{}".format(self.creds["db"], self.creds["user"], self.creds["host"]))
        self.cnx = mysql.connector.connect(
        host=self.creds["host"],
        port=self.creds["port"],
        user=self.creds["user"],
        password=self.creds["pass"],
        database=self.creds["db"])
    

        
        cursor = self.cnx.cursor()

        # On va commencer par voir si une table de donnée avec le nom du projet existe déjà
        r = cursor.execute("""SELECT COUNT(*)
                                FROM information_schema.tables
                                WHERE table_name = %s AND table_schema = %s
                                LIMIT 1""", (nom_projet, self.creds["db"]))
        
        # on est obligé d'itéter sur le résultat de cursor.execute pour faire avancer la requête...
        nb_tables = cursor.fetchone()[0]
    
        schema_sql = [nom + " " + str(vartype.to_SQL_type()) for nom, vartype in schema.items()]
        schema_sql.append("id INT NOT NULL AUTO_INCREMENT, PRIMARY KEY (id)")

        if nb_tables != 0:
            print("Arrrh, la table existe !")    # on suppose que la table est valide (il faut qu'elle soit compatible)
            # TODO: Verifier que la table est compatible
            cursor.execute("DESCRIBE {};".format(nom_projet))
            for r in cursor:
                if r[0] in schema:
                    if str(r[1]).casefold() != str(schema[r[0]].to_SQL_type()).casefold():
                        raise BDDExceptionTableNonValidee
            print("Table validée")
        else:       # la table n'existe pas, donc on la créée
            # TODO: Essayer de trouver une meilleure solution, sinon bonjour les injections SQL !
            print("CREATE TABLE {} ({});".format(nom_projet, ", ".join(schema_sql)))
            cursor.execute("CREATE TABLE {} ({});".format(nom_projet, ", ".join(schema_sql)))
            print("La table n'existait pas, on vient de la créer !")
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
    


if __name__ == '__main__':
    A = controlleurBDD("test2", {"K": csc_float, "n": csc_uint32, "E": csc_float}, "db_cred.json")
    print(A.existe({"K": csc_float(7.4), "n": csc_uint32(14638), "E": csc_float(15.9)}))
    print(A.existe({"K": csc_float(7.3), "n": csc_uint32(14638), "E": csc_float(15.9)}))