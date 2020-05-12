#!/usr/bin/env python3

import re
from enum import Enum

import shvars



contexte_variables = shvars.VarJar()

TESTMODE = False  # utilisé pour les tests unitaires

def set_testing_mode(test_mode):
    global TESTMODE 
    TESTMODE = test_mode


class ParseError(Exception):
    def __init__(self, **kwargs):
        self.message = ""
        if not TESTMODE:
            if "message" in kwargs:
                self.message = kwargs["message"]
                
            if "nligne" in kwargs or "nchar" in kwargs:
                cartouche = ""
                if "nligne" in kwargs:
                    if "nchar" in kwargs:
                        cartouche = "@[l:{}|c:{}] ".format(kwargs["nligne"], kwargs["nchar"])
                    else:
                        cartouche = "@[l:{}]".format(kwargs["nligne"])
                if "nchar" in kwargs and "strligne" in kwargs:
                    strligne = kwargs["strligne"]
                    nchar    = kwargs["nchar"]
                    if len(strligne) > 0:
                        if nchar >= len(strligne):
                            nchar = len(strligne)-1
                        cartouche = cartouche + "[contexte: {}[{}]{}] ".format(strligne[max(nchar-5,0):nchar], strligne[nchar], "" if nchar+1 == len(strligne) else strligne[nchar+1:min(nchar+6, len(strligne))])
                self.message = cartouche + "  " + self.message
        else:
            self.message = "E"

    
    def __str__(self):
        if self.message:
            return "{}".format(self.message)
        else:
            return "Erreur générique"
        
    def __repr__(self):
        return self.__str__()

class TokenEnum(Enum):
    CMD    = 0   # commande (fonction)
    FLOAT  = 1
    INT    = 2
    QSTR   = 3
    OPR    = 4   # OPeratoR
    UKWN   = 5
    ANY    = 6   # type "magique" qui match avec tous les autres (utilisé pour la vérification syntaxique)
    NUM    = 7   # type "magique" qui match avec les nombres
    VAR    = 8   # variable
    KW     = 9   # mot-clef (KeyWord) du langage
    VTY    = 10  # type de variable
    TXT    = 11  # du texte (pour être honnête, le programme ne sait pas encore trop ce que c'est)



class Token():
    def __init__(self, type, valeur=None):
        self.type = type  # venant de l'enum TokenEnum
        self.valeur = valeur
    
    def est_nombre(self):
        return self.type in [TokenEnum.INT, TokenEnum.FLOAT, TokenEnum.NUM, TokenEnum.ANY]

    def match(self, autre_token):
        """Permet de tester de façon assez souple l'égalité de deux tokens"""
        if self.type == TokenEnum.ANY or autre_token.type == TokenEnum.ANY or \
            (self.est_nombre() and autre_token.type == TokenEnum.NUM) or (self.type == TokenEnum.NUM and autre_token.est_nombre()) or \
                (self.type == autre_token.type and \
                     (self.valeur is None or autre_token.valeur is None or self.valeur == autre_token.valeur)):
            return True
        else:
            return False
    

class TokenError(Exception):
    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        if self.message:
            return "{}".format(self.message)
        else:
            return "Erreur de tokenisation générique"
    
    def __repr__(self):
        return self.__str__()

class ScriptCommand():
    liste_commandes = {}

    def __init__(self, nom, func, motif_syntaxe=None):
        self.nom = nom
        self.func = func
 
        self.motif_syntaxe = motif_syntaxe

        ScriptCommand.liste_commandes[nom] = self

    @staticmethod
    def cmd_existe(nom_cmd):
        """Permet de tester si une commande existe"""
        return nom_cmd in ScriptCommand.liste_commandes

    def run(self, *tokenliste):
        self.func(*tokenliste)

    def valider_syntaxe(self, *tokenliste):
        """
        Permet, si toutefois la commande dispose d'un schéma, de vérifier sans avoir à exécuter
        la commande si l'entrée est acceptable.
        Pour ce faire, on fournit à l'objet ScriptCommand la variable motif_syntaxe. C'est une liste de liste, contenant
        des schémas de syntaxe.
        Un schéma de syntaxe est une liste de tokens comme suit [t1, t2, t3, ..., tn]. On vérifie à l'aide de la méthode 
        match (de la classe Token) que les tokens soumis par l'utilisateur correspondent au schéma. Si ce n'est pas le cas,
        on continue à chercher dans motif_syntaxe. Chaque token du schéma constitue donc un maillon de vérification de ce dernier.
        Pour améliorer la concision du code et éviter les répétition, on permet que cetains token d'un schéma soient remplacés
        par une liste de tokens. Dans ce cas, le schéma est considéré correspondant pour le maillon si l'un des tokens de la liste
        match avec le token correspondant de l'entrée.
        """
        
        if self.motif_syntaxe is None:
            return True
        else:            
            ok = True  # si motif_syntaxe est vide on valide tout
            for s in self.motif_syntaxe:   # on teste tous les motifs proposés...
                if len(s)+1 == len(tokenliste):   # s ne comprend pas le premier argument (le nom de la cmd) mais tokenliste si
                    # on ne teste que les schémas de même longueur, sinon on est sur de ne pas avoir de match...
                    ok = True # si tokenliste fait 1 token de long (le nom de la commande) et que s est vide on valide automatiquement
                    for i in range(1,len(tokenliste)):
                        ok = False
                        if isinstance(s[i-1], list):
                            for sub_s in s[i-1]:
                                if tokenliste[i].match(sub_s):
                                    ok = True
                                    break
                        else:
                            ok = tokenliste[i].match(s[i-1])
                        
                        if not ok:  # on rejette ce schéma syntaxique car au rang i-1 il y a différence
                            break
                    
                    if ok:  # hourra, on a trouvé un schéma syntaxique qui correspond parfaitement !
                        break  # on sort donc de la boucle qui rend ZINZIN
                else:
                    ok = False
            return ok


class CmdError(Exception):
    """Erreur générique d'execution de la commande"""


def parser_ligne(strligne, num_ligne=None):
    """Permet de parser une ligne de code"""
    # On commence par faire du code simple qui distingue les mots en quote des chaînes pas en quote.
    
    separateurs = [' ', "\t"]
    marqueurs_commentaires = ["#"]
    mots = []
    
    f_EOL         = False   # le caractère lu est le dernier de la ligne
    f_dans_quote  = False
    f_sep_attendu = False   # on s'attend à ce que le prochain caractère soit un séparateur (f = flag)
    f_mot_non_vide= False   # on n'a pas encore lu de caractère dans le mot, juste des séparateurs
    f_char_est_sep= False   # on a lu un séparateur
    f_mode_com    = False   # on lit un commentaire
    f_arret       = False   # arrete de parser la ligne
    f_chr_prec_sep= False   # le caractère précédent était-il un séparateur ? (utilisé pour le cas où un commentaire demarre à la fin 
                            #   d'une ligne juste avant un esapce...)

    indice_debut_mot_lu = 0  # garder à l'esprit qu'un "mot" peut consister en plusieurs mots si c'est en quote par ex
    indice_dernier_quote_lu = 0 # le dernier quote qu'on a lu ? (utile pour afficher une erreur si le quote ne fini pas...)
    for i in range(len(strligne)):
        
        if i+1 == len(strligne):
            f_EOL = True

        

        f_char_est_sep = (strligne[i] in separateurs)

        if strligne[i] in marqueurs_commentaires and not f_dans_quote:
            f_mode_com = True
            f_arret = True
        
        if not f_char_est_sep and not f_mode_com:
            f_mot_non_vide = True
            if f_sep_attendu:
                raise ParseError(message="Séparateur attendu mais absent !", nchar=i+1, nligne=num_ligne, strligne=strligne)
        




        if strligne[i] == '"':
            indice_dernier_quote_lu = i
            if indice_debut_mot_lu != i:
                # On a trouvé un quote en plein milieu d'un mot !
                # soit on lit une chaîne quotée (dans ce cas-là la chaîne est
                # finie et on s'attend à trouver un séparateur au caractère
                # d'après) soit ce n'est pas le cas -> erreur
                if not f_dans_quote:
                    raise ParseError(message="Quote indue !", nchar=indice_dernier_quote_lu, nligne=num_ligne, strligne=strligne)
                f_sep_attendu = True
            f_dans_quote ^= True  # on inverse la valeur de quote

                

        if ((f_char_est_sep or f_EOL) and not f_dans_quote) or f_arret:
            # On a terminé notre mot !
            if f_mot_non_vide:
                # si on n'a pas lu de séparateur, on doit rajouter le caractère qu'on vient
                # de lire (il fait partie du mot, ie quote_char par exemple)
                # si le dernier caractère est un séparateur, on ne le rajoute pas par contre. 
                mots.append(strligne[indice_debut_mot_lu:i+int(f_EOL and not (f_char_est_sep))])   #or (f_mode_com and f_chr_prec_sep)
                f_sep_attendu = False
                f_mot_non_vide = False
            indice_debut_mot_lu = i+1
            if f_arret:
                break
        
            f_chr_prec_sep = f_char_est_sep
                
    if f_dans_quote:
        raise ParseError(message="Quote non terminée !", nchar=indice_dernier_quote_lu, strligne=strligne, nligne=num_ligne)
    
    return mots



def tokeniserLigne(strparsee):
    """Ici on tokenise la chaine strparsee donnée en entrée"""
    c = []

    re_qstr         = re.compile(r"\".*\"$")
    re_flt          = re.compile(r"[-|+]?[0-9]*\.+[0-9]*$")
    re_int          = re.compile(r"[-|+]?[0-9]+$")
    re_identifier   = re.compile(r"[a-zA-Z_].*$")
    re_opr          = re.compile(r"=$")

    f_ukwn          = False  # le token parsé est-il inconnu ? 

    for mot in strparsee:
        if re_qstr.match(mot):
            c.append(Token(TokenEnum.QSTR, mot))
        elif re_flt.match(mot):
            c.append(Token(TokenEnum.FLOAT, mot))
        elif re_int.match(mot):
            c.append(Token(TokenEnum.INT, mot))
        elif re_identifier.match(mot):
            # là il faut qu'on trouve précisement à qui on à affaire
            if ScriptCommand.cmd_existe(mot):
                c.append( Token(TokenEnum.CMD, mot) )
            elif contexte_variables.existance_type(mot):
                c.append( Token(TokenEnum.VTY, mot) )
            elif contexte_variables.existance_variable(mot):
                c.append( Token(TokenEnum.VAR, mot) )
            else:
                c.append( Token(TokenEnum.TXT, mot) )   # c'est du texte mais on ne peut pas vraiment en dire plus...

        elif re_opr.match(mot):
            c.append( Token(TokenEnum.OPR, mot) )
        else:
            c.append( Token(TokenEnum.UKWN, mot) )
            f_ukwn = True

        if f_ukwn:
            raise TokenError("Erreur de tokenisation de {} !".format(mot))
 
    return c


def echo(*args):
    for a in args:
        print(a.valeur, end='')
        print(" ", end='', flush=True)
    print("")

def dir(*args):
    print("total {}".format(len(args)))
    for a in args:
        print("-rwxr-xr-x  1 guillaume  staff   5548  3 mai 22:49 {}".format(a.valeur))


def let(*args):
    """Permet de déclarer une variable"""
    # Syntaxe: let <type> <nom> [=] <valeur>
    vtype = args[1].valeur
    vnom =  args[2].valeur
    vval = (args[4].valeur if args[3].valeur == "=" else args[3].valeur)
    otype = shvars.VarJar.recuperer_type(vtype)
    contexte_variables.ajouter_variable(vnom, shvars.CscVar(otype, otype.constructeur(vval)))

def examine(*args):
    """Permet de lire une variable et d'en afficher le contenu"""
    # Syntaxe: examine <nom>
    vnom = args[1].valeur
    print(contexte_variables.acceder_variable(vnom))

def bind(*args):
    """Permet de lier deux variables entre elles"""
    # Syntaxe bind <rvar> <lvar>
    rvnom = args[1].valeur
    lvnom = args[2].valeur
    contexte_variables.lier_variables(lvnom, rvnom)

def ldi(*args):
    """Permet de charger une constante dans une variable"""
    if len(args) == 3:
        vtoken = args[1]
        nouvelle_valeur_token = args[2]
    elif len(args) == 4:
        vtoken = args[1]
        nouvelle_valeur_token = args[3]

    if not contexte_variables.existance_variable(vtoken.valeur):  # la variable que l'on nous a envoyé n'existe pas !!
        raise CmdError()
    #try:
        #        a = contexte_variables.acceder_variable(vtoken.valeur)
    #except Exception as e:
    #    raise e
    try:
        contexte_variables.changer_valeur_variable(vtoken.valeur, nouvelle_valeur_token.valeur)
    except Exception as e:
        raise e
#    a.valeur = nouvelle_valeur_token.valeur


def lscmd(*args):
    """Permet de lister les commandes disponibles"""
    for ncmd, cmd in ScriptCommand.liste_commandes.items():
        print("{}: {}".format(ncmd, cmd.func.__doc__))

def ge(*args):
    """Affiche True si le premier argument est plus grand ou égal au deuxième"""
    print(args[1].valeur >= args[2].valeur)

ScriptCommand("echo", echo, [[]])
ScriptCommand("dir", dir, [[]])
ScriptCommand("let", let, [[Token(TokenEnum.VTY), Token(TokenEnum.TXT), Token(TokenEnum.OPR, '='), Token(TokenEnum.ANY)]])
ScriptCommand("examine", examine, [[Token(TokenEnum.VAR)]])
ScriptCommand("bind", bind, [[Token(TokenEnum.VAR), Token(TokenEnum.VAR)]])
ScriptCommand("lscmd", lscmd, [[]])
ScriptCommand("ldi", ldi, [[[Token(TokenEnum.VAR), Token(TokenEnum.TXT)], Token(TokenEnum.ANY)], 
                            [[Token(TokenEnum.VAR), Token(TokenEnum.TXT)], Token(TokenEnum.OPR, '='), Token(TokenEnum.ANY)]])
ScriptCommand("ge", ge, [[Token(TokenEnum.NUM), Token(TokenEnum.NUM)]])

liste_cmds = ScriptCommand.liste_commandes #{"echo": ScriptCommand("echo", echo), "dir": ScriptCommand("dir", dir), "let": ScriptCommand("let", let),
              #"examine": ScriptCommand("examine", examine), "bind": ScriptCommand("bind", bind)}

#print(liste_cmds)


def exec_ligne(tokenliste):
    #if tokenliste[0].type != TokenEnum.CMD or tokenliste[0].valeur not in liste_cmds:
    # On execute la liste
    # Rq: pour plus de naturel, on "expand" les lignes quand elles commencent par par un type de variable
    # ou par du texte. C'est sale et classe en même temps ! 
    if tokenliste[0].type == TokenEnum.VTY:
        tokenliste = [Token(TokenEnum.CMD, "let")] + tokenliste
    elif tokenliste[0].type == TokenEnum.VAR:
        tokenliste = [Token(TokenEnum.CMD, "ldi")] + tokenliste
  
    if tokenliste[0].type ==  TokenEnum.CMD:
        if tokenliste[0].valeur not in liste_cmds: 
            raise ValueError("Commande non trouvée !")
        else:
            cmd = liste_cmds[tokenliste[0].valeur]
            if cmd.valider_syntaxe(*tokenliste):
                cmd.run(*tokenliste)
            else:
                raise ValueError("Motif syntaxique incorrect !")
    
    else:
        raise TokenError("Syntaxe incorrecte")







if __name__ == '__main__':

    continuer = True

    while continuer:
        s = input("> ")
        try:
            a = parser_ligne(s, num_ligne="-") #"dir \"test2\" 3 3.141592  -4   \"a#\"   abc")
            print(a)
        except ParseError as pe:
            print(pe)
            continue
        
        try:
            b = tokeniserLigne(a)
        except TokenError as te:
            print(te)
            continue
        
        #print(a)
        #print(b)
        
        if len(a)>0:
            if a[0] == "exit":
                continuer = False
            else:
                try:
                    exec_ligne(b)
                except Exception as ve:
                    print("E] {}".format(ve))

