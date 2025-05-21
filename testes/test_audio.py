import unittest
from audio import AudioPlayer

class TestAudioPlayer(unittest.TestCase):
    def setUp(self):
        self.player = AudioPlayer()

    def test_volume(self):
        self.player.setar_volume(0.7)
        self.assertAlmostEqual(self.player.get_volume(), 0.7, places=1)

    def test_carregar_musica_invalida(self):
        resultado = self.player.carregar_musica("arquivo_inexistente.mp3")
        self.assertFalse(resultado)

if __name__ == '__main__':
    unittest.main()
