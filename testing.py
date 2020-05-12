import os  
import unittest
import json
import logging
import sys

import parser as p




#p.set_testing_mode(True)

# j = []
# with open(os.path.join(os.path.realpath('.'), "out.txt")) as g:
#     for l in g:
#         l = l.rstrip('\n')
        
#         a = {}
#         a["input"] = l

#         b = None
        
#         try:
#             b = p.parser_ligne(l)
#         except p.ParseError as e:
#             b = e

#         a["output"] = str(b)

#         j.append(a)

# g.close()
#with open(os.path.join(os.path.realpath('.'), "testing/parser_ligne.json"), 'w') as f:
#    json.dump(j, f, indent=4)


class TestParse(unittest.TestCase):


    def setUp(self):
            p.set_testing_mode(True)
            f = open(os.path.join(os.path.realpath('.'), "testing", "parser_ligne.json"))
            self.d = json.load(f)
            f.close()

  

    def test_parser(self):
        #log = logging.getLogger("test_parser")
        for test in self.d:
            try:
                b = p.parser_ligne(test["input"])
            except p.ParseError as e:
                b = e
        
        #logging.getLogger("test_parser").debug(test["input"])
        self.assertEqual(str(b), str(test["output"]), test["input"])

    def tearDown(self):
        pass
        


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)  
    #    logger = logging.getLogger("test_parser")
    #logger.setLevel(logging.DEBUG)

    #stream_handler = logging.StreamHandler(sys.stdout)
    #logger.addHandler(stream_handler)


    #logging.getLogger("test_parser").debug("Lololol")
    unittest.main()
    #pass

