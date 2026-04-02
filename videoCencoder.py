#!/usr/bin/env python3

import time
import VL53L0X
import os
from omxplayer.player import OMXPlayer

ARQUIVO_TXT = "/home/pi/distancia_salva.txt"

videoIdle = "/home/pi/Video/Idle.mp4"
videoTrig = "/home/pi/Video/Eugenia.mp4"

def carregar_limite_mm():
    try:
        arquivo = open(ARQUIVO_TXT, "r")
        valor = float(arquivo.read().strip())
        arquivo.close()
        return valor
    except:
        return 800.0   # padrao = 800 mm = 80 cm

# carrega limite salvo
limite_mm = carregar_limite_mm()

print("Limite carregado: %.1f mm (%.1f cm)" % (limite_mm, limite_mm / 10.0))

tof = VL53L0X.VL53L0X()

idle = OMXPlayer(videoIdle, args=['--no-osd', '--loop'])

tof.start_ranging(VL53L0X.VL53L0X_BETTER_ACCURACY_MODE)

timing = tof.get_timing()
print("Timing %d ms" % (timing / 1000))

triggered = False
zona_livre = False
margem_reset_mm = 100   # 10 cm de margem para rearmar

try:
    while True:
        distance = tof.get_distance()

        if distance > 0 and distance < 8190:
            print("Leitura: %.1f mm (%.1f cm) | Limite: %.1f mm (%.1f cm)" % (
                distance,
                distance / 10.0,
                limite_mm,
                limite_mm / 10.0
            ))

            # primeiro ele precisa enxergar que esta FORA da zona
            # para armar o sistema e evitar disparo instantaneo na partida
            if distance > (limite_mm + margem_reset_mm):
                zona_livre = True

            # dispara somente se ja esteve fora da zona antes
            if zona_livre == True and distance <= limite_mm and triggered == False:
                triggered = True
                print("DISPARO!")
                idle.pause()
                os.system("/usr/bin/omxplayer -o local --layer 15 /home/pi/Video/Eugenia.mp4")
                idle.play()

            # rearma quando sair da zona com margem
            if distance > (limite_mm + margem_reset_mm):
                triggered = False

        else:
            print("Leitura invalida")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("Parando...")

finally:
    tof.stop_ranging()
