import unittest
import os
from biblioteca import Biblioteca

class TestBiblioteca(unittest.TestCase):
    def setUp(self):
        self.bib = Biblioteca()

    def test_carregar_diretorio_valido(self):
        caminho = os.getcwd()  # Diretório atual deve existir
        musicas = self.bib.carregar_diretorio(caminho)
        self.assertIsInstance(musicas, list)

    def test_carregar_diretorio_invalido(self):
        musicas = self.bib.carregar_diretorio("diretorio_inexistente")
        self.assertEqual(musicas, [])

if __name__ == '__main__':
    unittest.main()
