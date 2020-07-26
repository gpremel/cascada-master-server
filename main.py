import numpy as np
import logging

import server
import vartypes
import seq
import projet


#schema = {"K": vartypes.csc_float, "Tdeb": vartypes.csc_float, "Tfin": vartypes.csc_float, "lambda": vartypes.csc_float}
#schema_range = {"K": (0, 10, 10, np.linspace), "Tdeb": (8, 10, 3, np.linspace), "Tfin": (0.01, 1, 10, np.linspace), "lambda": (1, 1, 1, np.linspace)}

schema = {"X": vartypes.csc_float, "Y": vartypes.csc_float, "Z": vartypes.csc_float}
schema_range = {"X": (-10, 10, 10, np.linspace), "Y": (-10, 10, 10, np.linspace), "Z": (-10, 10, 10, np.linspace)}


logging.basicConfig(filename='cascada.log', level=logging.INFO, format='%(levelname)s %(asctime)s %(message)s')

mon_super_sequenceur = seq.sequenceur(schema, schema_range)
print("Longueur séquenceur: {}".format(mon_super_sequenceur.nb_iters_total))
mon_genial_projet = projet.projetCascada("Parcours_pentu", mon_super_sequenceur, {"d": vartypes.csc_float}, schema)

server.init(mon_genial_projet)
server.launch()
