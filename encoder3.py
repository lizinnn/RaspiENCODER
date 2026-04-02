#!/usr/bin/env python3

import time
import os
import sys
import signal
import threading
import VL53L0X
from omxplayer.player import OMXPlayer
from gpiozero import RotaryEncoder, Button

# =========================
# ARQUIVOS
# =========================
VIDEO_IDLE = "/home/pi/Video/Idle.mp4"
VIDEO_TRIG = "/home/pi/Video/Eugenia.mp4"
ARQUIVO_CONFIG = "/home/pi/Video/config_disparo.txt"

# =========================
# GPIO DO ENCODER
# =========================
PIN_CLK = 17
PIN_DT = 27
PIN_SW = 22

# =========================
# LIMITES DE AJUSTE
# =========================
LIMITE_PADRAO_CM = 80.0
LIMITE_MIN_CM = 20.0
LIMITE_MAX_CM = 200.0
PASSO_CM = 1.0

# =========================
# FILTRO DE DISPARO
# =========================
LEITURAS_PARA_DISPARO = 3
LEITURAS_PARA_RESET = 3

# =========================
# ESTADO GLOBAL
# =========================
limite_cm = LIMITE_PADRAO_CM
triggered = False
contador_disparo = 0
contador_saida = 0
ultimo_print = 0
mensagem_status = ""
lock = threading.Lock()

# controle do encoder
ultimo_steps = 0

# =========================
# FUNCOES DE CONFIG
# =========================
def carregar_limite():
    if os.path.exists(ARQUIVO_CONFIG):
        try:
            with open(ARQUIVO_CONFIG, "r") as f:
                valor = float(f.read().strip())
                if LIMITE_MIN_CM <= valor <= LIMITE_MAX_CM:
                    return valor
        except Exception:
            pass
    return LIMITE_PADRAO_CM

def salvar_limite(valor):
    with open(ARQUIVO_CONFIG, "w") as f:
        f.write(f"{valor:.1f}")

# =========================
# FUNCOES VISUAIS
# =========================
def limpar_tela():
    os.system("clear")

def barra_visual(cm, max_cm=200, largura=50):
    if cm < 0:
        cm = 0
    if cm > max_cm:
        cm = max_cm
    preenchido = int((cm / max_cm) * largura)
    return "[" + "#" * preenchido + "-" * (largura - preenchido) + "]"

def set_status(msg):
    global mensagem_status
    with lock:
        mensagem_status = msg

def get_status():
    with lock:
        return mensagem_status

# =========================
# INICIALIZA ENCODER
# =========================
encoder = RotaryEncoder(a=PIN_CLK, b=PIN_DT, max_steps=0)
botao = Button(PIN_SW, pull_up=True, bounce_time=0.15)

# =========================
# CALLBACKS
# =========================
def ajustar_limite():
    global limite_cm, ultimo_steps

    steps_atual = encoder.steps
    delta = steps_atual - ultimo_steps

    if delta != 0:
        with lock:
            limite_cm += delta * PASSO_CM

            if limite_cm < LIMITE_MIN_CM:
                limite_cm = LIMITE_MIN_CM
            elif limite_cm > LIMITE_MAX_CM:
                limite_cm = LIMITE_MAX_CM

        ultimo_steps = steps_atual

def salvar_configuracao():
    with lock:
        valor = limite_cm
    try:
        salvar_limite(valor)
        set_status(f"[SALVO] Novo limite gravado: {valor:.1f} cm")
    except Exception as e:
        set_status(f"[ERRO] Falha ao salvar: {e}")

botao.when_pressed = salvar_configuracao

# =========================
# ENCERRAMENTO LIMPO
# =========================
idle = None
tof = None

def encerrar(*args):
    global idle, tof
    try:
        if tof is not None:
            tof.stop_ranging()
    except Exception:
        pass

    try:
        if idle is not None:
            idle.quit()
    except Exception:
        pass

    sys.exit(0)

signal.signal(signal.SIGINT, encerrar)
signal.signal(signal.SIGTERM, encerrar)

# =========================
# INICIALIZACAO
# =========================
limite_cm = carregar_limite()
set_status(f"[CONFIG] Limite carregado: {limite_cm:.1f} cm")

tof = VL53L0X.VL53L0X()
tof.start_ranging(VL53L0X.VL53L0X_BETTER_ACCURACY_MODE)

idle = OMXPlayer(VIDEO_IDLE, args=['--no-osd', '--loop'])

# =========================
# LOOP PRINCIPAL
# =========================
try:
    while True:
        ajustar_limite()

        distance = tof.get_distance()

        if distance > 0:
            cm = distance / 10.0

            with lock:
                limite_atual = limite_cm

            # filtro anti-oscilacao
            if cm <= limite_atual:
                contador_disparo += 1
                contador_saida = 0
            else:
                contador_saida += 1
                contador_disparo = 0

            # dispara video
            if contador_disparo >= LEITURAS_PARA_DISPARO and not triggered:
                triggered = True
                set_status(f"[TRIGGER] Disparo em {cm:.1f} cm (limite {limite_atual:.1f} cm)")
                idle.pause()
                os.system(f"/usr/bin/omxplayer -o local --layer 15 '{VIDEO_TRIG}'")
                idle.play()

            # libera novo disparo
            elif contador_saida >= LEITURAS_PARA_RESET and triggered:
                triggered = False
                set_status("[RESET] Sistema pronto para novo disparo")

            agora = time.time()
            if agora - ultimo_print > 0.10:
                limpar_tela()
                print("=== SISTEMA SENSOR + VIDEO + ENCODER ===\n")
                print(f"Distancia atual : {cm:6.1f} cm")
                print(f"Limite disparo  : {limite_atual:6.1f} cm")
                print(f"Arquivo config  : {ARQUIVO_CONFIG}")
                print()
                print(barra_visual(cm))
                print()

                if cm <= limite_atual:
                    print("STATUS SENSOR   : DENTRO DA ZONA DE DISPARO")
                else:
                    print("STATUS SENSOR   : FORA DA ZONA DE DISPARO")

                print(f"TRIGGER ATIVO   : {'SIM' if triggered else 'NAO'}")
                print()
                print("CONTROLES:")
                print("- Gire o encoder para ajustar a distancia")
                print("- Aperte o botao para SALVAR o valor")
                print("- O valor salvo permanece ate nova calibracao")
                print("- Ctrl+C para sair")
                print()
                print("MENSAGEM:")
                print(get_status())

                ultimo_print = agora

        else:
            set_status("[SENSOR] Leitura invalida")

        time.sleep(0.05)

finally:
    encerrar()
