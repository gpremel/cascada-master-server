"""An example main module, which starts the server"""

import logging

import numpy as np

import server
from vartypes import csc_float
from seq import Sequenceur
from projet import ProjetCascada


server_scheme = {"X": csc_float, "Y": csc_float, "Z": csc_float}
client_scheme = {"mE": csc_float}

range_scheme = {
    "X": (-9, 9, 10, np.linspace),
    "Y": (-9, 9, 10, np.linspace),
    "Z": (-9, 9, 10, np.linspace)
}

logging.basicConfig(filename='cascada.log',
                    level=logging.INFO,
                    format='%(levelname)s %(asctime)s %(message)s')


sequencer = Sequenceur(server_scheme, range_scheme)

my_project = ProjetCascada("Demo",
                           sequencer,
                           client_scheme,
                           server_scheme,
                           "mE",
                           3, 0.04, 1,
                           "mdp",
                           "aVeryEfficientAlgorithm")

server.init(my_project)
server.launch()
