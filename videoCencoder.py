#!/usr/bin/env python3

import time
import VL53L0X
import os
from omxplayer.player import OMXPlayer

ARQUIVO_TXT = "/home/pi/distancia_salva.txt"

videoIdle = "/home/pi/Video/Idle.mp4"
videoTrig = "/home/pi/Video/Eugenia.mp4"

def carregar_limite_cm():
    try:
        arquivo = open(ARQUIVO_TXT, "r")
        valor = float(arquivo.read().strip())
        arquivo.close()
        return valor
    except:
        return 80.0

limite_cm = carregar_limite_cm()

print("Limite carregado: %.1f cm" % limite_cm)

tof = VL53L0X.VL53L0X()
idle = OMXPlayer(videoIdle, args=['--no-osd', '--loop'])

tof.start_ranging(VL53L0X.VL53L0X_BETTER_ACCURACY_MODE)

timing = tof.get_timing()
print("Timing %d ms" % (timing / 1000))

triggered = False
zona_livre = False
margem_reset_cm = 10.0

try:
    while True:
        distance = tof.get_distance()

        if distance > 0 and distance < 8190:
            cm = distance / 10.0

            print("Leitura: %.1f cm | Limite: %.1f cm | Armado: %s | Triggered: %s" % (
                cm,
                limite_cm,
                str(zona_livre),
                str(triggered)
            ))

            if cm > (limite_cm + margem_reset_cm):
                if zona_livre == False:
                    print("SISTEMA ARMADO")
                zona_livre = True

            if zona_livre == True and cm <= limite_cm and triggered == False:
                triggered = True
                print("DISPARO!")
                idle.pause()
                os.system("/usr/bin/omxplayer -o local --layer 15 /home/pi/Video/Eugenia.mp4")
                idle.play()

            if cm > (limite_cm + margem_reset_cm):
                if triggered == True:
                    print("RESET DO TRIGGER")
                triggered = False

        else:
            print("Leitura invalida")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("Parando...")

finally:
    tof.stop_ranging()
    try:
        idle.quit()
    except:
        pass
