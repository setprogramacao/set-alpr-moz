"""
PLC Controller - Desktop Module ALPR UNIPIAGET
Controle da cancela eletrônica via Modbus TCP
"""

import threading
import logging
import time
from typing import Optional, Callable

try:
    from pymodbus.client import ModbusTcpClient
    from pymodbus.exceptions import ModbusException
    PYMODBUS_DISPONIVEL = True
except ImportError:
    PYMODBUS_DISPONIVEL = False

from ..config import (
    PLC_HOST,
    PLC_PORT,
    PLC_TIMEOUT,
    PLC_COIL_CANCELA,
    PLC_INPUT_LACO,
    BARREIRA_TIMEOUT_SEGUNDOS,
)

logger = logging.getLogger(__name__)


class PLCController:
    """
    Controlador de cancela eletrônica via Modbus TCP.

    Fluxo de operação:
    1. Sensor de laço indutivo detecta veículo (DI 0 = True)
    2. Callback aciona câmara para capturar e ler a placa via OCR
    3. Se OCR tiver sucesso → cancela abre (Coil 0 = True) + movimento registado
    4. Se OCR falhar → cancela NÃO abre (agente de segurança intervém manualmente)
    5. Sensor indica que veículo passou (DI 0 = False) → cancela fecha
    6. Fallback: fecha após BARREIRA_TIMEOUT_SEGUNDOS se sensor não responder
    """

    def __init__(
        self,
        host: str = PLC_HOST,
        port: int = PLC_PORT,
        coil_cancela: int = PLC_COIL_CANCELA,
        input_laco: int = PLC_INPUT_LACO,
        timeout: float = PLC_TIMEOUT,
        barreira_timeout: int = BARREIRA_TIMEOUT_SEGUNDOS,
        callback_status: Optional[Callable[[str], None]] = None,
        callback_veiculo_detectado: Optional[Callable[[], None]] = None,
    ):
        """
        Inicializa controlador PLC.

        Args:
            host: Endereço IP do PLC
            port: Porta Modbus TCP
            coil_cancela: Endereço da coil que comanda a cancela
            input_laco: Endereço do discrete input do sensor de laço
            timeout: Timeout de conexão em segundos
            barreira_timeout: Segundos máximos com cancela aberta (fallback segurança)
            callback_status: Chamado com "aberta"/"fechada"/"erro" quando estado muda
            callback_veiculo_detectado: Chamado quando sensor deteta veículo (para câmara)
        """
        self.host = host
        self.port = port
        self.coil_cancela = coil_cancela
        self.input_laco = input_laco
        self.timeout = timeout
        self.barreira_timeout = barreira_timeout
        self.callback_status = callback_status
        self.callback_veiculo_detectado = callback_veiculo_detectado

        self._client: Optional[object] = None
        self._conectado = False
        self._cancela_aberta = False
        self._monitorando = False
        self._lock = threading.Lock()

        if not PYMODBUS_DISPONIVEL:
            logger.warning("pymodbus não instalado — PLCController em modo simulação local")

        logger.info(f"PLCController inicializado — {host}:{port}")

    # =========================================================================
    # CONEXÃO
    # =========================================================================

    def conectar(self) -> bool:
        """
        Estabelece conexão Modbus TCP e inicia monitoramento autônomo do sensor.

        Returns:
            True se conectado com sucesso
        """
        if not PYMODBUS_DISPONIVEL:
            logger.warning("pymodbus não disponível — conexão simulada")
            self._conectado = True
            self.iniciar_monitoramento_sensor()
            return True

        try:
            self._client = ModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=self.timeout,
            )
            resultado = self._client.connect()
            self._conectado = resultado

            if resultado:
                logger.info(f"✓ PLC conectado em {self.host}:{self.port}")
                self._escrever_coil(False)  # garante cancela fechada ao conectar
                self.iniciar_monitoramento_sensor()
            else:
                logger.error(f"✗ Falha ao conectar PLC em {self.host}:{self.port}")

            return resultado

        except Exception as e:
            logger.error(f"Erro ao conectar PLC: {e}")
            self._conectado = False
            return False

    def desconectar(self):
        """Fecha a conexão com o PLC e para o monitoramento do sensor."""
        self.parar_monitoramento_sensor()

        if self._client and PYMODBUS_DISPONIVEL:
            try:
                self._escrever_coil(False)  # fecha cancela por segurança
                self._client.close()
            except Exception as e:
                logger.error(f"Erro ao desconectar PLC: {e}")

        self._conectado = False
        self._cancela_aberta = False
        logger.info("PLC desconectado")

    def esta_conectado(self) -> bool:
        """Verifica se está conectado ao PLC."""
        return self._conectado

    # =========================================================================
    # MONITORAMENTO AUTÓNOMO DO SENSOR DE LAÇO
    # =========================================================================

    def iniciar_monitoramento_sensor(self):
        """Inicia loop autónomo que vigia o sensor e controla a cancela."""
        if self._monitorando:
            return
        self._monitorando = True
        threading.Thread(
            target=self._loop_sensor_principal,
            daemon=True,
            name="PLC-SensorMonitor"
        ).start()
        logger.info("Monitoramento do sensor de laço iniciado")

    def parar_monitoramento_sensor(self):
        """Para o loop de monitoramento do sensor."""
        self._monitorando = False

    def _loop_sensor_principal(self):
        """
        Loop principal autónomo do sensor de laço indutivo.

        Lógica:
        - Sensor ON  → aciona câmara para ler placa (a abertura da cancela depende do OCR)
        - Sensor OFF → fecha cancela se estava aberta
        - Fallback   → fecha se cancela ficar aberta além de barreira_timeout segundos
        """
        veiculo_presente = False
        tempo_detecao: Optional[float] = None
        POLL = 0.3  # segundos entre leituras

        logger.debug("Loop de sensor iniciado")

        while self._monitorando:
            if not self._conectado:
                time.sleep(1.0)
                continue

            estado = self.ler_sensor_laco()

            if estado is True and not veiculo_presente:
                # Veículo entrou no laço → aciona câmara (cancela abre só se OCR tiver sucesso)
                veiculo_presente = True
                tempo_detecao = time.time()
                logger.info("Sensor ON — acionando câmara para leitura de placa")
                if self.callback_veiculo_detectado:
                    threading.Thread(
                        target=self.callback_veiculo_detectado,
                        daemon=True
                    ).start()

            elif estado is False and veiculo_presente:
                # Veículo saiu do laço → fecha cancela se estava aberta
                veiculo_presente = False
                tempo_detecao = None
                if self._cancela_aberta:
                    self._fechar_por_sensor()

            elif veiculo_presente and tempo_detecao is not None:
                # Fallback: veículo bloqueado ou cancela aberta demasiado tempo
                if time.time() - tempo_detecao >= self.barreira_timeout:
                    logger.warning(f"Timeout ({self.barreira_timeout}s) — resetando estado")
                    veiculo_presente = False
                    tempo_detecao = None
                    if self._cancela_aberta:
                        self._fechar_por_sensor()

            time.sleep(POLL)

    def _fechar_por_sensor(self):
        """Fecha cancela após veículo passar."""
        sucesso = self._escrever_coil(False)
        if sucesso:
            self._cancela_aberta = False
            self._notificar_status("fechada")
            logger.info("↓ Cancela FECHADA (veículo passou)")

    # =========================================================================
    # CONTROLE MANUAL (para botões no diálogo de configuração)
    # =========================================================================

    def abrir_cancela(self) -> bool:
        """
        Abre cancela manualmente (botão no diálogo de configuração).

        Returns:
            True se comando enviado com sucesso
        """
        with self._lock:
            if self._cancela_aberta:
                return True
            sucesso = self._escrever_coil(True)
            if sucesso:
                self._cancela_aberta = True
                self._notificar_status("aberta")
                logger.info("↑ Cancela ABERTA (manual)")
            return sucesso

    def fechar_cancela(self) -> bool:
        """
        Fecha cancela manualmente.

        Returns:
            True se comando enviado com sucesso
        """
        with self._lock:
            sucesso = self._escrever_coil(False)
            if sucesso:
                self._cancela_aberta = False
                self._notificar_status("fechada")
                logger.info("↓ Cancela FECHADA (manual)")
            return sucesso

    def cancela_esta_aberta(self) -> bool:
        """Retorna True se a cancela está atualmente aberta."""
        return self._cancela_aberta

    # =========================================================================
    # SENSOR DE LAÇO INDUTIVO
    # =========================================================================

    def ler_sensor_laco(self) -> Optional[bool]:
        """
        Lê o estado do sensor de laço indutivo.

        Returns:
            True se veículo presente no laço, False se livre, None em erro
        """
        if not self._conectado:
            return None

        if not PYMODBUS_DISPONIVEL:
            return False  # simulação: laço sempre livre

        try:
            resultado = self._client.read_discrete_inputs(
                address=self.input_laco,
                count=1
            )

            if resultado.isError():
                logger.error(f"Erro ao ler sensor de laço: {resultado}")
                return None

            return resultado.bits[0]

        except Exception as e:
            logger.error(f"Erro ao ler sensor de laço: {e}")
            return None

    # =========================================================================
    # MÉTODOS INTERNOS
    # =========================================================================

    def _escrever_coil(self, valor: bool) -> bool:
        """
        Escreve valor em uma coil Modbus.

        Args:
            valor: True = ativar (abrir cancela), False = desativar (fechar)

        Returns:
            True se sucesso
        """
        if not PYMODBUS_DISPONIVEL:
            logger.debug(f"[SIMULAÇÃO] Coil {self.coil_cancela} = {valor}")
            return True

        if not self._client or not self._conectado:
            logger.error("PLC não conectado — não foi possível escrever coil")
            self._notificar_status("erro")
            return False

        try:
            resultado = self._client.write_coil(
                address=self.coil_cancela,
                value=valor
            )

            if resultado.isError():
                logger.error(f"Erro ao escrever coil {self.coil_cancela}: {resultado}")
                self._notificar_status("erro")
                return False

            return True

        except Exception as e:
            logger.error(f"Erro ao escrever coil: {e}")
            self._conectado = False
            self._notificar_status("erro")
            return False

    def _notificar_status(self, status: str):
        """Notifica callback de status (thread-safe)."""
        if self.callback_status:
            try:
                self.callback_status(status)
            except Exception as e:
                logger.error(f"Erro no callback de status PLC: {e}")

    # =========================================================================
    # STATUS
    # =========================================================================

    def obter_status(self) -> dict:
        """Retorna estado atual do controlador."""
        return {
            "conectado": self._conectado,
            "host": self.host,
            "port": self.port,
            "cancela_aberta": self._cancela_aberta,
            "monitorando": self._monitorando,
            "pymodbus_disponivel": PYMODBUS_DISPONIVEL,
        }
