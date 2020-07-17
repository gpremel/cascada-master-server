import numpy as np

import server
import vartypes
import seq
import projet


schema = {"K": vartypes.csc_float, "Tdeb": vartypes.csc_float, "Tfin": vartypes.csc_float, "lambda": vartypes.csc_float}
schema_range = {"K": (0, 10, 100, np.linspace), "Tdeb": (8, 10, 3, np.linspace), "Tfin": (0.01, 1, 10, np.linspace), "lambda": (1, 1, 1, np.linspace)}

mon_super_sequenceur = seq.sequenceur(schema, schema_range)
mon_genial_projet = projet.projetCascada("Glissade_rapide", mon_super_sequenceur, {"E": vartypes.csc_float})

server.init(mon_genial_projet)
server.launch()
