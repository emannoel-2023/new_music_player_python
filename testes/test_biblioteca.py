import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import unittest
from biblioteca import Biblioteca

class TestBiblioteca(unittest.TestCase):
    def setUp(self):
        self.bib = Biblioteca()

    def test_carregar_diretorio_valido(self):
        caminho = os.getcwd()
        musicas = self.bib.carregar_diretorio(caminho)
        self.assertIsInstance(musicas, list)

    def test_carregar_diretorio_invalido(self):
        musicas = self.bib.carregar_diretorio("diretorio_inexistente")
        self.assertEqual(musicas, [])

if __name__ == '__main__':
    unittest.main()
