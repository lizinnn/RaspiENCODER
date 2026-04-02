#!/usr/bin/env python3

import time
import os
import signal
import sys
import VL53L0X
import RPi.GPIO as GPIO
from omxplayer.player import OMXPlayer

# =========================
# VIDEOS
# =========================
VIDEO_IDLE = "/home/pi/Video/Idle.mp4"
VIDEO_TRIG = "/home/pi/Video/Eugenia.mp4"

# =========================
# ARQUIVO DE CONFIG
# =========================
ARQUIVO_CONFIG = "/home/pi/Video/config_disparo.txt"

# =========================
# PINOS DO ENCODER
# =========================
PIN_CLK = 17
PIN_DT = 27
PIN_SW = 22

# =========================
# CONFIGURACOES
# =========================
LIMITE_PADRAO_CM = 80.0
LIMITE_MIN_CM = 10.0
LIMITE_MAX_CM = 200.0
PASSO_CM = 5.0

LEITURAS_PARA_DISPARO = 3
LEITURAS_PARA_RESET = 3

# =========================
# ESTADO GLOBAL
# =========================
limite_cm = LIMITE_PADRAO_CM
triggered = False
contador_disparo = 0
contador_saida = 0
mensagem_status = ""
ultimo_clk = 1

# =========================
# GPIO
# =========================
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_CLK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_DT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_SW, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# =========================
# FUNCOES AUXILIARES
# =========================
def carregar_limite():
    if os.path.exists(ARQUIVO_CONFIG):
        try:
            arquivo = open(ARQUIVO_CONFIG, "r")
            valor = float(arquivo.read().strip())
            arquivo.close()

            if valor >= LIMITE_MIN_CM and valor <= LIMITE_MAX_CM:
                return valor
        except:
            pass

    return LIMITE_PADRAO_CM

def salvar_limite(valor):
    arquivo = open(ARQUIVO_CONFIG, "w")
    arquivo.write("%.1f" % valor)
    arquivo.close()

def limpar_tela():
    os.system("clear")

def barra_visual(cm):
    max_cm = 200.0
    largura = 50

    if cm < 0:
        cm = 0
    if cm > max_cm:
        cm = max_cm

    preenchido = int((cm / max_cm) * largura)

    return "[" + ("#" * preenchido) + ("-" * (largura - preenchido)) + "]"

def set_status(msg):
    global mensagem_status
    mensagem_status = msg

def ajustar_encoder():
    global limite_cm
    global ultimo_clk

    clk_estado = GPIO.input(PIN_CLK)
    dt_estado = GPIO.input(PIN_DT)

    if clk_estado != ultimo_clk:
        if clk_estado == 0:
            if dt_estado != clk_estado:
                limite_cm = limite_cm + PASSO_CM
            else:
                limite_cm = limite_cm - PASSO_CM

            if limite_cm < LIMITE_MIN_CM:
                limite_cm = LIMITE_MIN_CM

            if limite_cm > LIMITE_MAX_CM:
                limite_cm = LIMITE_MAX_CM

        ultimo_clk = clk_estado

def botao_pressionado():
    return GPIO.input(PIN_SW) == GPIO.LOW

# =========================
# ENCERRAMENTO
# =========================
idle = None
tof = None

def encerrar(sig=None, frame=None):
    global idle
    global tof

    try:
        if tof is not None:
            tof.stop_ranging()
    except:
        pass

    try:
        if idle is not None:
            idle.quit()
    except:
        pass

    GPIO.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, encerrar)
signal.signal(signal.SIGTERM, encerrar)

# =========================
# INICIALIZACAO
# =========================
limite_cm = carregar_limite()
set_status("[CONFIG] Limite carregado: %.1f cm" % limite_cm)

tof = VL53L0X.VL53L0X()
tof.start_ranging(VL53L0X.VL53L0X_LONG_RANGE_MODE)

idle = OMXPlayer(VIDEO_IDLE, args=['--no-osd', '--loop'])

ultimo_clk = GPIO.input(PIN_CLK)
ultimo_tempo_print = 0
ultimo_tempo_botao = 0

# =========================
# LOOP PRINCIPAL
# =========================
try:
    while True:
        ajustar_encoder()

        distancia = tof.get_distance()

        if distancia > 0 and distancia < 8190:
            cm = distancia / 10.0

            if cm <= limite_cm:
                contador_disparo = contador_disparo + 1
                contador_saida = 0
            else:
                contador_saida = contador_saida + 1
                contador_disparo = 0

            if contador_disparo >= LEITURAS_PARA_DISPARO and triggered == False:
                triggered = True
                set_status("[TRIGGER] Disparo em %.1f cm (limite %.1f cm)" % (cm, limite_cm))
                idle.pause()
                os.system("/usr/bin/omxplayer -o local --layer 15 '%s'" % VIDEO_TRIG)
                idle.play()

            elif contador_saida >= LEITURAS_PARA_RESET and triggered == True:
                triggered = False
                set_status("[RESET] Sistema pronto para novo disparo")

        else:
            cm = None
            set_status("[SENSOR] Leitura invalida")

        # SALVAR NO BOTAO SW
        if botao_pressionado():
            agora = time.time()

            if agora - ultimo_tempo_botao > 0.4:
                salvar_limite(limite_cm)
                set_status("[SALVO] Novo limite gravado: %.1f cm" % limite_cm)
                ultimo_tempo_botao = agora

        agora_print = time.time()
        if agora_print - ultimo_tempo_print > 0.1:
            limpar_tela()
            print("=== SISTEMA SENSOR + VIDEO + ENCODER ===")
            print("")

            if cm is not None:
                print("Distancia atual : %.1f cm" % cm)
                print(barra_visual(cm))
            else:
                print("Distancia atual : leitura invalida")
                print(barra_visual(0))

            print("Limite disparo  : %.1f cm" % limite_cm)
            print("Arquivo config  : %s" % ARQUIVO_CONFIG)
            print("")

            if cm is not None:
                if cm <= limite_cm:
                    print("STATUS SENSOR   : DENTRO DA ZONA DE DISPARO")
                else:
                    print("STATUS SENSOR   : FORA DA ZONA DE DISPARO")
            else:
                print("STATUS SENSOR   : LEITURA INVALIDA")

            if triggered == True:
                print("TRIGGER ATIVO   : SIM")
            else:
                print("TRIGGER ATIVO   : NAO")

            print("")
            print("CONTROLES:")
            print("- Gire o encoder para ajustar a distancia")
            print("- Aperte o botao SW para SALVAR")
            print("- O valor salvo permanece ate nova calibracao")
            print("- Ctrl+C para sair")
            print("")
            print("MENSAGEM:")
            print(mensagem_status)

            ultimo_tempo_print = agora_print

        time.sleep(0.02)

finally:
    encerrar()
