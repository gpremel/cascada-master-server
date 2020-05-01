#!/usr/bin/env python3

import numpy as np

n = 1000 	# on génère n lignes pour tester le parser

p_char_special = 3
p_espace = 5
p_mot_dico = 5

char_speciaux = ['"', '#']

p_tot = p_char_special+p_espace+p_mot_dico

f_dernier_type_insere_est_mot = False

with open("wordlist.txt") as f:
	lines = f.read().splitlines()
l = []

for i in range(n):
	nmots_ligne = int(np.abs(np.random.normal(6, 2)))
	j = 0
	cur_l = []
	while j <= nmots_ligne:
		x = np.random.randint(1, p_tot+1)
		if x <= p_char_special:
			cur_l.append(char_speciaux[int(np.random.randint(1,5) > 3)])
			f_dernier_type_insere_est_mot = False
		elif p_char_special < x <= p_espace+p_char_special:
			cur_l.append(" ")
			f_dernier_type_insere_est_mot = False
		else:
			if j == nmots_ligne:
				break
			else:
				if f_dernier_type_insere_est_mot:   # on évite d'avoir des mots collés
					cur_l.append(" ")
				cur_l.append(np.random.choice(lines))
				f_dernier_type_insere_est_mot = True

			j += 1
	l.append("".join(cur_l))

with open("out.txt", 'w') as f:
	for ligne in l:
		f.write(ligne+"\n")
		
