#!/usr/bin/env python3

import time
import VL53L0X
import RPi.GPIO as GPIO

BOTAO = 17
ARQUIVO_TXT = "/home/pi/distancia_salva.txt"

GPIO.setmode(GPIO.BCM)
GPIO.setup(BOTAO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

tof = VL53L0X.VL53L0X()
tof.start_ranging(VL53L0X.VL53L0X_LONG_RANGE_MODE)

ultima_distancia = None

try:
    while True:
        distancia = tof.get_distance()   # mm

        if distancia > 0 and distancia < 8190:
            cm = distancia / 10.0
            ultima_distancia = distancia
            print("Objeto a %.1f mm (%.1f cm)" % (distancia, cm))
        else:
            print("Sem leitura")

        if GPIO.input(BOTAO) == GPIO.LOW:
            print("")
            print("Botao pressionado. Salvando...")

            time.sleep(0.3)

            if ultima_distancia is not None:
                arquivo = open(ARQUIVO_TXT, "w")
                arquivo.write(str(ultima_distancia))
                arquivo.close()

                print("Salvo: %.1f mm" % ultima_distancia)
                print("Arquivo: %s" % ARQUIVO_TXT)
            else:
                print("Nenhuma leitura valida para salvar")

            break

        time.sleep(0.1)

except KeyboardInterrupt:
    print("Parando...")

finally:
    tof.stop_ranging()
    GPIO.cleanup()
