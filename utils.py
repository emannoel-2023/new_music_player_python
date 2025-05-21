def formatar_tempo(segundos):
    minutos = int(segundos) // 60
    segundos_restantes = int(segundos) % 60
    return f"{minutos:02d}:{segundos_restantes:02d}"
