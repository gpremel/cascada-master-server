#!/usr/bin/env python3


class ParseError(Exception):
    def __init__(self, **kwargs):
        self.message = ""

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
                cartouche = cartouche + "[contexte: {}[{}]{}] ".format(strligne[max(nchar-5,0):nchar], strligne[nchar], "" if nchar+1 == len(strligne) else strligne[nchar+1:min(nchar+6, len(strligne))])
            self.message = cartouche + "  " + self.message


    
    def __str__(self):
        if self.message:
            return "{}".format(self.message)
        else:
            return "Erreur générique"
        
    def __repr__(self):
        return self.__str__()

def parser_ligne(strligne):
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

    indice_debut_mot_lu = 0  # garder à l'esprit qu'un "mot" peut consister en plusieurs mots si c'est en quote par ex
    indice_dernier_quote_lu = 0 # le dernier quote qu'on a lu ? (utile pour afficher une erreur si le quote ne fini pas...)
    for i in range(len(strligne)):
        
        if i+1 == len(strligne):
            f_EOL = True

        f_char_est_sep = (strligne[i] in separateurs)

        if not f_char_est_sep:
            f_mot_non_vide = True
            if f_sep_attendu:
                raise ParseError(message="Séparateur attendu mais absent !", nchar=i, nligne=1, strligne=strligne)
        
        if strligne[i] in marqueurs_commentaires and not f_dans_quote:
            f_mode_com = True
            f_arret = True



        if strligne[i] == '"':
            indice_dernier_quote_lu = i
            if indice_debut_mot_lu != i:
                # On a trouvé un quote en plein milieu d'un mot !
                # soit on lit une chaîne quotée (dans ce cas-là la chaîne est
                # finie et on s'attend à trouver un séparateur au caractère
                # d'après) soit ce n'est pas le cas -> erreur
                if not f_dans_quote:
                    raise ParseError(message="Quote indue !", nchar=i, nligne=1, strligne=strligne)
                f_sep_attendu = True
            f_dans_quote ^= True  # on inverse la valeur de quote

                

        if (f_char_est_sep or f_EOL and not f_dans_quote) or f_arret:
            # On a terminé notre mot !
            if f_mot_non_vide:
                # si on n'a pas lu de séparateur, on doit rajouter le caractère qu'on vient
                # de lire (il fait partie du mot, ie quote_char par exemple)
                mots.append(strligne[indice_debut_mot_lu:i+int(f_EOL)])
                f_sep_attendu = False
                f_mot_non_vide = False
            indice_debut_mot_lu = i+1
            if f_arret:
                break
                
    if f_dans_quote:
        raise ParseError(message="Quote non terminée !", nchar=indice_dernier_quote_lu, strligne=strligne, nligne=1)
    
    return mots





if __name__ == '__main__':
    print(parser_ligne("test1 \"test2\"     \"a#\"   abc"))
