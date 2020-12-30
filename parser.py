#!/usr/bin/env python3
from typing import List, Any, Tuple

import re
from enum import Enum

import shvars


TESTMODE = False  # used for unit tests


def set_testing_mode(test_mode):
    global TESTMODE
    TESTMODE = test_mode


class LangError(Exception):
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
                    nchar = kwargs["nchar"]
                    if len(strligne) > 0:
                        if nchar >= len(strligne):
                            nchar = len(strligne) - 1
                        cartouche = cartouche + "[contexte: {}[{}]{}] ".format(
                            strligne[max(nchar - 5, 0):nchar],
                            strligne[nchar],
                            "" if nchar + 1 == len(
                                strligne)
                            else strligne[nchar + 1:min(nchar + 6, len(strligne))])
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
    CMD = 0   # command (function)
    FLOAT = 1
    INT = 2
    QSTR = 3
    OPR = 4   # OPeratoR
    UKWN = 5
    ANY = 6   # "magic" type matching any other (used for syntax checking)
    NUM = 7   # "magic" type matching numbers
    VAR = 8   # variable
    KW = 9   # language KeyWord
    VTY = 10  # Variable TYpe
    TXT = 11  # raw TeXT (which true nature has not yet been decided by the program)


class Token():
    def __init__(self, type, valeur=None):
        self.type = type  # from TokeEnum
        self.valeur = valeur

    def est_nombre(self) -> bool:
        """Checks whether the token represents a number

            Returns:
                bool: True if so, False if not
        """
        return self.type in [TokenEnum.INT, TokenEnum.FLOAT, TokenEnum.NUM, TokenEnum.ANY]

    def match(self, autre_token: 'Token') -> bool:
        """Quite lenient comparison

        Params:
            autre_token: other token

        Returns:
            True if the tokens matches; False if not
        """

        if self.type == TokenEnum.ANY or autre_token.type == TokenEnum.ANY or \
            (self.est_nombre() and autre_token.type == TokenEnum.NUM) or \
            (self.type == TokenEnum.NUM and autre_token.est_nombre()) or \
                (self.type == autre_token.type and
                 (self.valeur is None or autre_token.valeur is None or
                     self.valeur == autre_token.valeur)) or \
            (self.type == TokenEnum.TXT and autre_token.type == TokenEnum.VAR or
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
            return "Generic tokenizing error"

    def __repr__(self):
        return self.__str__()


class ScriptCommand():
    """A script command"""

    liste_commandes = {}

    def __init__(self, nom, func, motif_syntaxe=None):
        self.nom = nom
        self.func = func

        self.motif_syntaxe = motif_syntaxe

        ScriptCommand.liste_commandes[nom] = self

    @staticmethod
    def cmd_existe(nom_cmd: str) -> bool:
        """Checks whether a command exists

        Params:
            nom_cmd: the name of the command

        Returns:
            True if the command exists, False if it doesn't
        """

        return nom_cmd in ScriptCommand.liste_commandes

    def run(self, *tokenliste: List[Token]) -> Any:
        """Runs the command

        Params:
            tokenliste: the list of tokens

        Returns:
            Any: the return value of the command
        """

        self.func(*tokenliste)

    def valider_syntaxe(self, *tokenliste: List[Token]) -> bool:
        """Checks whether the input is valid (only applicable if the command
        has defined a type schemes, see below).

        Params:
            tokenliste: the list of tokens

        Returns:
            bool: True if the syntax has been validated, False if not

        Note:
            The idea is to give ScriptCommand the motif_syntaxe variable. It's a list of lists,
            containing syntax schemes. A syntax scheme is a list of tokens [t1, t2, t3, ..., tn].
            Using Token's match function, we check that the user-submitted tokens match the scheme.
            If it's not the case, we keep looking through motif_syntaxe. To avoid repetitions, using
            a list of tokens instead of a mere token is allowed: if one of the list's tokens
            matches, the list is considered to have been validated.
        """

        if self.motif_syntaxe is None:
            return True
        else:
            ok = True  # if motify_synatxe is empty we match everything
            for s in self.motif_syntaxe:   # testing each syntax scheme...
                # s does not contain the first argument (the name of the command) but
                # tokenliste does
                if len(s) + 1 == len(tokenliste):
                    # we only test the scheme of same length; if they are of a different
                    # length, we're sure they won't match
                    # if tokenliste is 1 token long (the name of the command) and s is empty,
                    # we automatically validate the command
                    ok = True
                    for i in range(1, len(tokenliste)):
                        ok = False
                        if isinstance(s[i - 1], list):
                            for sub_s in s[i - 1]:
                                if tokenliste[i].match(sub_s):
                                    ok = True
                                    break
                        else:
                            ok = tokenliste[i].match(s[i - 1])

                        if not ok:  # we reject this scheme because it differs
                            break

                    if ok:  # Hourray, we've found a matching scheme
                        break
                else:
                    ok = False
            return ok


class CmdError(Exception):
    """Generic command execution error"""


class ListeLiee():

    def __init__(self, liste: List):
        """Initializes the list

            Params:
                liste: the list to be used to fill the newly created linked list
        """

        self.pl = None  # reading pointer
        self.debut = None  # start of the list

        self.inserer(liste)  # we insert the provided list
        self.debut = self.pl

    def lire(self) -> Any:
        """Peeks the content of the list at the position indicated by self.pl

        Returns:
            Any: the content of the list at pl
        """
        return None if self.pl is None else self.pl[0]

    def inserer(self, nliste: List) -> None:  # mode='avant'):
        """Inserts the content of nliste immediately after pl

        Params:
            nliste: a linked list (ListeLiee)

        Note:
                        pl                      pl
                [l-1] - [l] - [l+1] -> [l-1] - [l] - [nliste1] - ... - [nlistep] - [pl+1]
        """

        deb_nliste = None
        dernier_noeud = None

        for l in nliste:
            if dernier_noeud is None:  # we haven't allocated a node yet
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

        if self.pl is None:   # happens oftentimes (during initialization)
            self.pl = deb_nliste
        else:
            self.pl[1] = deb_nliste

        if len(nliste) > 0:
            dernier_noeud[1] = ancien_suivant

    def suivant(self, pas_inc: bool = False) -> Any:
        """Accesses the next element in the list.

        Params:
            pas_inc: If pas_inc is set to true, pl is not incremented

        Returns:
            Tuple:
                [0]: the content of the list
                [1]: True if we are at the end of the list; False if not
        """

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

    def goto(self, nouveau_pl: List[Tuple[Any, List]]) -> None:
        """Sets pl to an abritrary value; use with caution

        Params:
            nouveau_pl: the new value of pl
        """
        self.pl = nouveau_pl

    def rembobiner(self) -> None:
        """Resets the internal state of the list"""
        self.goto(self.debut)

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
            continuer = not continuer  # the self.suivant() function returns True
            # if we're at the end of the list
        self.goto(ancien_pl)
        return s


class FlowRunner():
    """Used to control the execution flow of the program; still WIP"""

    def __init__(self, *args, **kwargs):
        self.recuperer_ligne_suivante = None
        self.labels = {}   # les labels pour les gotos
        self.mode = None
        self.fin_prog_atteinte = False

        if "src" not in kwargs:
            print("No source was given; reading stdin")
            self.recuperer_ligne_suivante = self._recup_stdin
            self.src = ListeLiee([])
            self.mode = 'stdin'
        else:
            liste_src_compilee = []
            for i in range(len(kwargs["src"])):
                liste_src_compilee.append(lexer_ligne(tokeniser_ligne(kwargs["src"][i], i + 1)))
            self.src = ListeLiee(liste_src_compilee)
            self.recuperer_ligne_suivante = self._recup_src
            self.mode = 'src'

    def _recup_stdin(self):
        s = input("> ")
        a = lexer_ligne(tokeniser_ligne(s, "-"))
        self.src.inserer(a)
        return a, False

    def _recup_src(self):
        res = self.src.lire()
        self.src.suivant()
        return res, res is None

    def enregistrer_label(self, nom: str) -> None:
        """Registers a label to use with goto_label; the label points to the current instruction

        Params:
            nom: the name of the label
        """

        if nom in self.labels and self.labels[nom] is not self.src.pl:
            raise ValueError("A label has already been defined !")
        else:
            self.labels[nom] = self.src.pl

    def goto_label(self, nom: str) -> None:
        """Jumps to label nom

        Params:
            nom: the name of the label
        """

        if nom not in self.labels:
            raise ValueError("Goto key not given !")
        else:
            jp = self.labels[nom]
            self.src.goto(jp)       # we're on the line defined by the label
            self.src.suivant()      # we jump to the next line

    def end(self) -> None:
        """Enables an external command to stop the program"""

        self.fin_prog_atteinte = True

    def run_step(self) -> bool:
        """Fetches and executes a single instruction

            Returns:
                bool: True if there still are instructions to be exectued; False if not
        """

        # used if a third-party command (eg exit) wants to stop the execution
        if self.fin_prog_atteinte:
            return False

        l, self.fin_prog_atteinte = self.recuperer_ligne_suivante()

        if self.fin_prog_atteinte:   # reached the end of the source
            return False
        try:
            exec_ligne(l)
        except Exception as ve:
            print("E] {}".format(ve))
        return True

    def run(self) -> None:
        """Runs the program"""

        while self.run_step():
            pass


def tokeniser_ligne(strligne: str, num_ligne: int = None) -> List[str]:
    """Tokenizes a line of code

    Params:
        strligne: the line of code
        num_ligne: the line number (used for error reporting)

    Returns:
        List[str]: a list of words that should then be lexed
        """

    separateurs = [' ', "\t"]
    marqueurs_commentaires = ["#"]
    mots = []

    f_EOL = False   # the character that was read is the last one on the line
    f_dans_quote = False
    f_sep_attendu = False   # exepcting the next char to be a delimiter
    f_mot_non_vide = False   # we've not read a char in the word, only a delimiter
    f_char_est_sep = False   # we've read a delimiter
    f_mode_com = False   # reading a comment
    f_arret = False   # stop parsing the line

    indice_debut_mot_lu = 0  # a "word" might be several actual words if we're read a quote
    indice_dernier_quote_lu = 0  # last quote read ? (used to display an error...)
    for i in range(len(strligne)):

        if i + 1 == len(strligne):
            f_EOL = True

        f_char_est_sep = (strligne[i] in separateurs)

        if strligne[i] in marqueurs_commentaires and not f_dans_quote:
            f_mode_com = True
            f_arret = True

        if not f_char_est_sep and not f_mode_com:
            f_mot_non_vide = True
            if f_sep_attendu:
                raise LangError(
                    message="Delimiter expected but missing !",
                    nchar=i + 1,
                    nligne=num_ligne,
                    strligne=strligne)

        if strligne[i] == '"':
            indice_dernier_quote_lu = i
            if indice_debut_mot_lu != i:
                # we've found a quote in the middle of a word !
                # either we're reading a quoted string (and we're at the
                # end of it -> exepcting a delimiter) or it's not the
                # case and we raise an error

                if not f_dans_quote:
                    raise LangError(
                        message="Undue quote !",
                        nchar=indice_dernier_quote_lu,
                        nligne=num_ligne,
                        strligne=strligne)
                f_sep_attendu = True
            f_dans_quote ^= True  # flip the quote status

        if ((f_char_est_sep or f_EOL) and not f_dans_quote) or f_arret:
            # We're done reading our word !
            if f_mot_non_vide:
                # If we've not read a delimiter, we have to add the character we've just read
                # (it's part of the word)
                # If the last char is a delimiter, we don't
                mots.append(strligne[indice_debut_mot_lu:i + int(f_EOL and not (f_char_est_sep))])
                f_sep_attendu = False
                f_mot_non_vide = False
            indice_debut_mot_lu = i + 1
            if f_arret:
                break

            # f_chr_prec_sep = f_char_est_sep

    if f_dans_quote:
        raise LangError(
            message="Unended quote !",
            nchar=indice_dernier_quote_lu,
            strligne=strligne,
            nligne=num_ligne)

    return mots


def lexer_ligne(strtokenisee: List[str]) -> List[Token]:
    """Lexes a list of words (should be called with the result of tokeniser_ligne)

    Params:
        strtokenisee: the list of words

    Returns:
        List[Token]: a list of lexed tokens
    """

    c = []

    re_qstr = re.compile(r"\".*\"$")
    re_flt = re.compile(r"[-|+]?[0-9]*\.+[0-9]*$")
    re_int = re.compile(r"[-|+]?[0-9]+$")
    re_identifier = re.compile(r"[a-zA-Z_].*$")
    re_opr = re.compile(r"=$")

    f_ukwn = False  # is the parsed token unknown ?

    for mot in strtokenisee:
        if re_qstr.match(mot):
            c.append(Token(TokenEnum.QSTR, mot))
        elif re_flt.match(mot):
            c.append(Token(TokenEnum.FLOAT, mot))
        elif re_int.match(mot):
            c.append(Token(TokenEnum.INT, mot))
        elif re_identifier.match(mot):
            # gotta find precisely what we're dealing with
            if ScriptCommand.cmd_existe(mot):
                c.append(Token(TokenEnum.CMD, mot))
            elif contexte_variables.existance_type(mot):
                c.append(Token(TokenEnum.VTY, mot))
            elif contexte_variables.existance_variable(mot):
                c.append(Token(TokenEnum.VAR, mot))
            else:
                # it's text, but we can't say much more about it...
                c.append(Token(TokenEnum.TXT, mot))

        elif re_opr.match(mot):
            c.append(Token(TokenEnum.OPR, mot))
        else:
            c.append(Token(TokenEnum.UKWN, mot))
            f_ukwn = True

        if f_ukwn:
            raise TokenError("Tokenization of {} failed!".format(mot))

    return c


# *************************************************************************************************
# The following are commands that ought to be called as script commands but are of relatively low
# interest if they were to be used in Python code: they are therefore not extensively documented
# *************************************************************************************************

def echo(*args):
    """Prints the passed arguments"""

    for a in args:
        print(a.valeur, end='')
        print(" ", end='', flush=True)
    print("")


def let(*args):
    """Declares a variable"""
    # Syntax: let <type> <name> [=] <value>

    vtype = args[1].valeur
    vnom = args[2].valeur
    vval = (args[4].valeur if args[3].valeur == "=" else args[3].valeur)
    otype = shvars.VarJar.recuperer_type(vtype)
    contexte_variables.ajouter_variable(vnom, shvars.CscVar(otype, otype.constructeur(vval)))


def examine(*args):
    """Reads a variable and displays its content"""
    # Syntaxe: examine <name>

    vnom = args[1].valeur
    print(contexte_variables.acceder_variable(vnom))


def bind(*args):
    """Binds two variables together (akin to have them point on the same
    underlaying object)"""
    # Syntax bind <rvar> <lvar>

    rvnom = args[1].valeur
    lvnom = args[2].valeur
    contexte_variables.lier_variables(lvnom, rvnom)


def ldi(*args):
    """Loads an immediate (ie constant) value in a variable"""
    if len(args) == 3:
        vtoken = args[1]
        nouvelle_valeur_token = args[2]
    elif len(args) == 4:
        vtoken = args[1]
        nouvelle_valeur_token = args[3]

    if not contexte_variables.existance_variable(
            vtoken.valeur):  # the variable we received does not exist !
        raise CmdError()
    try:
        contexte_variables.changer_valeur_variable(vtoken.valeur, nouvelle_valeur_token.valeur)
    except Exception as e:
        raise e


def lscmd(*args):
    """Lists avaible commands"""
    for ncmd, cmd in ScriptCommand.liste_commandes.items():
        print("{}: {}".format(ncmd, cmd.func.__doc__))


def ge(*args):
    """Displays True if the first argument is bigger than the second,
    False if not"""
    print(args[1].valeur >= args[2].valeur)


def inc(*args):
    """Increments the variables passed"""
    var = contexte_variables.acceder_variable(args[1].valeur)
    var.valeur = var.valeur + var.type(1)


ScriptCommand("echo", echo, [[]])
ScriptCommand("let", let, [[Token(TokenEnum.VTY), Token(TokenEnum.TXT),
                            Token(TokenEnum.OPR, '='), Token(TokenEnum.ANY)]])
ScriptCommand("examine", examine, [[Token(TokenEnum.VAR)]])
ScriptCommand("bind", bind, [[Token(TokenEnum.VAR), Token(TokenEnum.VAR)]])
ScriptCommand("lscmd", lscmd, [[]])
ScriptCommand("ldi", ldi, [[[Token(TokenEnum.VAR), Token(TokenEnum.TXT)], Token(TokenEnum.ANY)], [
              [Token(TokenEnum.VAR), Token(TokenEnum.TXT)], Token(TokenEnum.OPR, '='),
              Token(TokenEnum.ANY)]])
ScriptCommand("ge", ge, [[Token(TokenEnum.NUM), Token(TokenEnum.NUM)]])
ScriptCommand("inc", inc, [[Token(TokenEnum.VAR)]])

liste_cmds = ScriptCommand.liste_commandes


def exec_ligne(tokenliste: List[Token]) -> None:
    """Executes the list of tokens provided in tokenliste.

    Params:
        tokenliste: a list of tokens

    Note:
        For a more "natural" feel, lines starting by a variable name
        (ie intended variable declarations)
        are expansed to be treated as such.
    """

    if tokenliste[0].type == TokenEnum.VTY:
        tokenliste = [Token(TokenEnum.CMD, "let")] + tokenliste
    elif tokenliste[0].type == TokenEnum.VAR:
        tokenliste = [Token(TokenEnum.CMD, "ldi")] + tokenliste

    if tokenliste[0].type == TokenEnum.CMD:
        if tokenliste[0].valeur not in liste_cmds:
            raise ValueError("Command not found. Use lscmd to list available commands.")
        else:
            cmd = liste_cmds[tokenliste[0].valeur]
            if cmd.valider_syntaxe(*tokenliste):
                cmd.run(*tokenliste)
            else:
                raise ValueError("Failed to validate scheme !")

    else:
        raise TokenError("Incorrect syntax")


contexte_variables = shvars.VarJar()


if __name__ == '__main__':

    lignes = ["int64 a = ", "inc a", "examine a"]

    while True:
        s = input("> ")
        try:
            a = tokeniser_ligne(s, num_ligne="-")  # "dir \"test2\" 3 3.141592  -4   \"a#\"   abc")
            # print(a)
        except LangError as pe:
            print(pe)
            continue

        try:
            b = lexer_ligne(a)
        except TokenError as te:
            print(te)
            continue

        if len(a) > 0:
            if a[0] == "exit":
                continuer = False
            else:
                try:
                    exec_ligne(b)
                except Exception as ve:
                    print("E] {}".format(ve))
