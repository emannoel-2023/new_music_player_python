import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import unittest
from playlist import PlaylistManager

class TestPlaylistManager(unittest.TestCase):
    def setUp(self):
        self.pl = PlaylistManager()

    def test_criar_playlist(self):
        self.assertTrue(self.pl.criar_playlist("Teste"))
        self.assertFalse(self.pl.criar_playlist("Teste"))  # Já existe

    def test_adicionar_e_remover(self):
        self.pl.criar_playlist("Teste")
        self.assertTrue(self.pl.adicionar_na_playlist("Teste", "musica.mp3"))
        self.assertFalse(self.pl.adicionar_na_playlist("Outro", "musica.mp3"))
        self.assertTrue(self.pl.remover_da_playlist("Teste", 0))
        self.assertFalse(self.pl.remover_da_playlist("Teste", 10))

if __name__ == '__main__':
    unittest.main()
