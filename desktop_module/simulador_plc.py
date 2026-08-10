"""
Simulador PLC - Desktop Module ALPR UNIPIAGET
Servidor Modbus TCP virtual para testes sem hardware real.

Uso:
    python -m desktop_module.simulador_plc
    python desktop_module/simulador_plc.py

O simulador expõe:
    - Coil 0: cancela (escrita pelo PLCController → abre/fecha cancela)
    - Discrete Input 0: sensor de laço indutivo (disparado automaticamente pelo simulador)

Fluxo simulado (novo):
    1. A cada INTERVALO_VEICULO_S segundos, o simulador dispara o sensor (DI 0 = True)
    2. O PLCController deteta sensor ON → abre a cancela + aciona câmara
    3. Após DURACAO_SENSOR_S segundos o sensor desliga (DI 0 = False)
    4. O PLCController deteta sensor OFF → fecha a cancela
"""

import sys
import time
import threading
import logging


def configurar_saida_console():
    """Permite imprimir acentos e simbolos no console Windows sem encerrar."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


configurar_saida_console()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("SimuladorPLC")

try:
    from pymodbus.server import StartTcpServer
    from pymodbus.datastore import (
        ModbusSlaveContext,
        ModbusServerContext,
        ModbusSequentialDataBlock,
    )
    from pymodbus.device import ModbusDeviceIdentification
    PYMODBUS_DISPONIVEL = True
except ImportError:
    PYMODBUS_DISPONIVEL = False
    logger.error("pymodbus não instalado. Execute: pip install pymodbus==3.9.2")
    sys.exit(1)


# ============================================================================
# CONFIGURAÇÕES DO SIMULADOR
# ============================================================================

HOST = "127.0.0.1"
PORT = 5020

# Endereços Modbus
COIL_CANCELA = 0       # Saída: desktop escreve True para abrir
INPUT_LACO = 0         # Entrada: True = veículo no laço indutivo

# Parâmetros de simulação automática
INTERVALO_VEICULO_S = 12.0  # Segundos entre veículos simulados
DURACAO_SENSOR_S = 3.0      # Segundos com veículo no laço (sensor ativo)


# ============================================================================
# DATASTORE COMPARTILHADO
# ============================================================================

def criar_contexto() -> ModbusServerContext:
    """Cria contexto Modbus com blocos de dados para coils e discrete inputs."""

    # Coils (leitura/escrita) — índice Modbus começa em 1 internamente no pymodbus
    coils = ModbusSequentialDataBlock(0, [False] * 10)

    # Discrete inputs (leitura) — sensor de laço
    discrete_inputs = ModbusSequentialDataBlock(0, [False] * 10)

    # Holding registers e input registers (não utilizados, mas necessários)
    holding = ModbusSequentialDataBlock(0, [0] * 10)
    inputs = ModbusSequentialDataBlock(0, [0] * 10)

    store = ModbusSlaveContext(
        di=discrete_inputs,   # discrete inputs (fc=2)
        co=coils,             # coils (fc=1)
        hr=holding,           # holding registers (fc=3)
        ir=inputs,            # input registers (fc=4)
    )

    return ModbusServerContext(slaves=store, single=True)


# Contexto global compartilhado entre servidor e thread de monitoramento
contexto: ModbusServerContext = criar_contexto()


# ============================================================================
# THREAD DE MONITORAMENTO / SIMULAÇÃO AUTO
# ============================================================================

def ler_coil(ctx: ModbusServerContext, address: int) -> bool:
    """Lê valor de uma coil pelo contexto do servidor."""
    # slave_id=0x00 no modo single
    valores = ctx[0x00].getValues(1, address, count=1)  # fc=1 → coils
    return bool(valores[0])


def escrever_discrete_input(ctx: ModbusServerContext, address: int, valor: bool):
    """Escreve no bloco de discrete inputs (simula sensor externo)."""
    ctx[0x00].setValues(2, address, [valor])  # fc=2 → discrete inputs


def simular_veiculos(ctx: ModbusServerContext):
    """
    Thread que simula chegada de veículos ao sensor de laço indutivo.

    Novo fluxo (sensor é a origem do evento):
      1. A cada INTERVALO_VEICULO_S segundos, liga o sensor (DI 0 = True)
      2. O PLCController deteta sensor ON e abre a cancela automaticamente
      3. Após DURACAO_SENSOR_S segundos, desliga o sensor (DI 0 = False)
      4. O PLCController deteta sensor OFF e fecha a cancela
    """
    time.sleep(3.0)  # aguarda PLCController conectar antes do primeiro evento
    logger.info(f"Thread de simulação iniciada — veículo a cada {INTERVALO_VEICULO_S}s")

    while True:
        try:
            logger.info("  [SIM] Veículo chegando à cancela — sensor ON")
            escrever_discrete_input(ctx, INPUT_LACO, True)

            time.sleep(DURACAO_SENSOR_S)

            logger.info("  [SIM] Veículo passou — sensor OFF")
            escrever_discrete_input(ctx, INPUT_LACO, False)

            time.sleep(INTERVALO_VEICULO_S)

        except Exception as e:
            logger.error(f"Erro na thread de simulação: {e}")
            time.sleep(1)


# ============================================================================
# PAINEL DE STATUS (CONSOLE)
# ============================================================================

def painel_status(ctx: ModbusServerContext):
    """Thread que imprime o estado atual no console a cada 2 segundos."""
    while True:
        try:
            cancela = ler_coil(ctx, COIL_CANCELA)
            laco = ctx[0x00].getValues(2, INPUT_LACO, count=1)[0]  # fc=2

            cancela_str = "ABERTA  ↑" if cancela else "fechada ↓"
            laco_str = "VEÍCULO NO LAÇO ●" if laco else "livre         ○"

            print(f"\r  Cancela: {cancela_str}   |   Laço: {laco_str}   ", end="", flush=True)
            time.sleep(2)
        except Exception:
            time.sleep(2)


# ============================================================================
# IDENTIDADE DO DISPOSITIVO MODBUS
# ============================================================================

def criar_identidade() -> ModbusDeviceIdentification:
    identity = ModbusDeviceIdentification()
    identity.VendorName = "ALPR UNIPIAGET"
    identity.ProductCode = "SIM-PLC"
    identity.VendorUrl = "https://github.com/setprogramacao"
    identity.ProductName = "Simulador PLC Cancela"
    identity.ModelName = "Virtual Modbus TCP Server"
    identity.MajorMinorRevision = "1.0"
    return identity


# ============================================================================
# PONTO DE ENTRADA
# ============================================================================

def main():
    print("=" * 60)
    print("  SIMULADOR PLC — ALPR UNIPIAGET")
    print(f"  Endereço   : {HOST}:{PORT} (Modbus TCP)")
    print(f"  DI 0       : Sensor laço (True=veículo presente) ← origem do evento")
    print(f"  Coil 0     : Cancela (True=aberta) ← controlada pelo PLCController")
    print(f"  Intervalo  : veículo a cada {INTERVALO_VEICULO_S}s | sensor ativo {DURACAO_SENSOR_S}s")
    print("=" * 60)
    print("  Pressione Ctrl+C para encerrar")
    print()

    global contexto

    # Inicia thread de simulação automática
    threading.Thread(
        target=simular_veiculos,
        args=(contexto,),
        daemon=True,
        name="SimAuto"
    ).start()

    # Inicia thread de painel de status
    threading.Thread(
        target=painel_status,
        args=(contexto,),
        daemon=True,
        name="PainelStatus"
    ).start()

    # Inicia servidor Modbus TCP (bloqueante)
    logger.info(f"Servidor Modbus TCP aguardando conexões em {HOST}:{PORT}")
    try:
        StartTcpServer(
            context=contexto,
            identity=criar_identidade(),
            address=(HOST, PORT),
        )
    except KeyboardInterrupt:
        print("\n\n  Simulador encerrado.")
    except OSError as e:
        logger.error(f"Erro ao iniciar servidor: {e}")
        logger.error(f"Verifique se a porta {PORT} está livre.")
        sys.exit(1)


if __name__ == "__main__":
    main()
