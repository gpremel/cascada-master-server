#!/usr/bin/env python3

import re
from enum import Enum

import shvars
import compteur


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
                     (self.valeur is None or autre_token.valeur is None or self.valeur == autre_token.valeur)) or \
                         (self.type == TokenEnum.TXT and autre_token.type == TokenEnum.VAR or \
                             self.type == TokenEnum.VAR and autre_token.type == TokenEnum.TXT):
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

class ListeLiee():
    
    def __init__(self, liste):
        # dernier_noeud = None
        # for l in liste:
        #     if dernier_noeud is None:  # on n'a pas encore alloué de noeud
        #         self.debut = [l, None]
        #         dernier_noeud = debut
        #     else:
        #         courant = [l, None]
        #         dernier_noeud[1] = courant
        #         dernier_noeud = courant
        
        
        self.pl = None  # pointeur de lecture
        self.debut = None  # debut de la chaîne

        self.inserer(liste)  # on insère la liste qui nous permet d'initialiser le tout...
        self.debut = self.pl
    

    def lire(self):
        # Sécurité pour pas planter
        return None if self.pl is None else self.pl[0]
    
    def inserer(self, nliste): # mode='avant'):
        """Permet d'insérer le contenu de nliste immediatement après pl
                        pl                      pl
                [l-1] - [l] - [l+1] -> [l-1] - [l] - [nliste1] - ... - [nlistep] - [pl+1]"""
        deb_nliste = None
        dernier_noeud = None
        
        for l in nliste:
            if dernier_noeud is None:  # on n'a pas encore alloué de noeud
                deb_nliste = [l, None]
                dernier_noeud = deb_nliste
            else:
                courant = [l, None]
                dernier_noeud[1] = courant
                dernier_noeud = courant

        if self.pl is not None:
            ancien_suivant = self.pl[1]
        else:
            ancien_suivant = None

        if self.pl is None:   # survient lors de l'initialisation par exemple
            self.pl = deb_nliste
        else:
            self.pl[1] = deb_nliste


        if len(nliste) > 0:
            dernier_noeud[1] = ancien_suivant

    def suivant(self, pas_inc=False):
        """Permet d'accéder à l'élément suivant dans la liste
        Si pas_inc est a vrai, pl n'est pas incrémenté
        Renvoie un tuple:
            [0]: le contenu de la liste
            [1]: True si on est à la fin de la liste, False sinon"""
        if self.pl is None:
            return None, True
        elif pas_inc:
            return self.pl[1][0], False
        else:
            self.pl = self.pl[1]
            if self.pl is None:
                return None, True
            else:
                return self.pl[0], False

    
    def goto(self, nouveau_pl):
        """Permet de changer pl à une valeur arbitraire (potentiellement dangereux)"""
        self.pl = nouveau_pl
    
    def rembobiner(self):
        """Permet de ramener la liste liée à son état initial"""
        self.goto(self.debut)

    # def __iter__(self):
    #     return self

    # def __next__(self):
    #     a = self.suivant()
    #     if a[1]:
    #         raise StopIteration
    #     else:
    #         return a[0]

    def __str__(self):
        ancien_pl = self.pl
        self.rembobiner()
        l = self.lire()
        continuer = True
        est_debut = True
        s = ""
        while continuer is True:
            s += "{}{}".format("" if est_debut else " -> ", l)
            if est_debut:
                est_debut = False
            l, continuer = self.suivant()
            continuer = not continuer  # la fonction self.suivant() renvoie True si est arrivé à la fin de la chaîne
        self.goto(ancien_pl)
        return s
    
    # def __repr__(self):
    #     return self.__str__()


    


class FlowRunner():
    def __init__(self, *args, **kwargs):
        self.recuperer_ligne_suivante = None
        self.labels = {}   # les labels pour les gotos
        self.mode = None
        self.fin_prog_atteinte = False

        if not "src" in kwargs:
            print("Pas de source founie. Lecture de stdin")
            self.recuperer_ligne_suivante = self._recup_stdin
            self.src = ListeLiee([])
            self.mode = 'stdin'
        else:
            liste_src_compilee = []
            for i in range(len(kwargs["src"])):
                liste_src_compilee.append(tokeniserLigne(parser_ligne(kwargs["src"][i], i+1)))
            self.src = ListeLiee(liste_src_compilee)
            self.recuperer_ligne_suivante = self._recup_src
            self.mode = 'src'

    def _recup_stdin(self):
        s =  input("> ")
        a = tokeniserLigne(parser_ligne(s, "-"))
        self.src.inserer(a)
        return a, False

    
    def _recup_src(self):
        res = self.src.lire()
        self.src.suivant()
        return res, res is None


    def enregistrer_label(self, nom):
        if nom in self.labels and self.labels[nom] is not self.src.pl:
            raise ValueError("Un label est déjà présent !")
        else:
            self.labels[nom] = self.src.pl
    
    def goto_label(self, nom):
        if nom not in self.labels:
            raise ValueError("Clef pour le goto non renseignée !")
        else:
            jp = self.labels[nom]
            self.src.goto(jp)       # là on est sur la ligne où l'on définit le label
            self.src.suivant()      # on va à la ligne suivante

    def end(self):
        """Permet à une commande tierce d'indiquer que le programme doit s'arrêter de tourner au flowrunner
            Args:
                self
            Returns:
                None
        """
        
        self.fin_prog_atteinte = True

    def run_step(self):
        """Permet de récupérer et d'executer une unique instruction
            Args:
                self
            Returns:
                bool: True s'il reste des intructions à executer, False sinon
        """

        if self.fin_prog_atteinte:    # utilisé si une commande tiere veut mettre fin à l'execution
            return False

        l, self.fin_prog_atteinte = self.recuperer_ligne_suivante()

        if self.fin_prog_atteinte:   # utilisé quand on est à la fin de la source
            return False
        try:
            exec_ligne(l)
        except Exception as ve:
            print("E] {}".format(ve))
        return True

    def run(self):
        """Fait tourner le programme
            Args:
                self
            Returns
                None
        """

        while self.run_step():
            pass



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


def inc(*args):
    """Incremente la variable donnée en entrée"""
    var = contexte_variables.acceder_variable(args[1].valeur)
    var.valeur = var.valeur + var.type(1)

def add(*args):
    """Ajoute deux valeurs"""
    return args

def exec_end(*args):
    """Termine l'execution"""
    #flow_exec.

ScriptCommand("echo", echo, [[]])
ScriptCommand("dir", dir, [[]])
ScriptCommand("let", let, [[Token(TokenEnum.VTY), Token(TokenEnum.TXT), Token(TokenEnum.OPR, '='), Token(TokenEnum.ANY)]])
ScriptCommand("examine", examine, [[Token(TokenEnum.VAR)]])
ScriptCommand("bind", bind, [[Token(TokenEnum.VAR), Token(TokenEnum.VAR)]])
ScriptCommand("lscmd", lscmd, [[]])
ScriptCommand("ldi", ldi, [[[Token(TokenEnum.VAR), Token(TokenEnum.TXT)], Token(TokenEnum.ANY)], 
                            [[Token(TokenEnum.VAR), Token(TokenEnum.TXT)], Token(TokenEnum.OPR, '='), Token(TokenEnum.ANY)]])
ScriptCommand("ge", ge, [[Token(TokenEnum.NUM), Token(TokenEnum.NUM)]])
ScriptCommand("inc", inc, [[Token(TokenEnum.VAR)]])
#ScriptCommand("add", add, [[[Token(TokenEnum.NUM), Token(TokenEnum.VAR)], ])

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




    
    
contexte_variables = shvars.VarJar()
#flow_exec          = FlowRunner()






if __name__ == '__main__':

    continuer = True



    # A = ListeLiee(["pomme", "poire", "banane", "pastèque"])
    # print(A)
    # A.suivant()
    # A.inserer(["tomate", "choux", "carrote"])
    # print(A)
    # print(A.suivant(pas_inc=True)[0])
    # print(A.suivant()[0])
    # print(A.suivant()[0])
    # exit(0)

    lignes = ["int64 a = 17051999", "inc a", "examine a"]
    flow_exec          = FlowRunner(src=lignes)
    flow_exec.run()

    a = compteur.CompteurLogRange(1, 100, 2)
    while continuer:
        s, continuer = a.incremente()
        if continuer: print(s)

    exit(0)

    #while continuer:
    for l in lignes: 
        s = l#input("> ")
        try:
            a = parser_ligne(s, num_ligne="-") #"dir \"test2\" 3 3.141592  -4   \"a#\"   abc")
            #print(a)
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

