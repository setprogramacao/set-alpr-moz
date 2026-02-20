"""
Cliente API - Desktop Module ALPR UNIPIAGET
Comunicação HTTP com o Web Module
"""

import requests
from typing import Optional, Dict
import logging
from datetime import datetime
import base64
import cv2
import numpy as np

from ..config import API_DETECCAO_ENDPOINT, API_TIMEOUT
from shared.utils import imagem_para_base64

logger = logging.getLogger(__name__)


class APIClient:
    """
    Cliente para comunicação com API do Web Module
    """

    def __init__(self, api_url: Optional[str] = None, timeout: int = API_TIMEOUT):
        """
        Inicializa cliente API

        Args:
            api_url: URL base da API (None = usar config)
            timeout: Timeout em segundos
        """
        self.api_url = api_url if api_url else API_DETECCAO_ENDPOINT
        self.timeout = timeout
        self.conectado = False
        self.ultima_resposta = None

        logger.info(f"APIClient inicializado - URL: {self.api_url}")

    def testar_conexao(self) -> bool:
        """
        Testa conexão com a API

        Returns:
            True se conectado
        """
        try:
            # Tenta fazer request para health endpoint
            # Extrai host da URL (ex: http://localhost:8000/api/v1/registros/deteccao -> http://localhost:8000)
            parts = self.api_url.split("/")
            base_url = f"{parts[0]}//{parts[2]}"  # http://localhost:8000
            health_url = f"{base_url}/health"

            response = requests.get(health_url, timeout=5)

            self.conectado = response.status_code == 200
            logger.info(f"Teste de conexão: {'✓ Conectado' if self.conectado else '✗ Falhou'}")

            return self.conectado

        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            self.conectado = False
            return False

    def enviar_deteccao(
        self,
        placa: str,
        tipo_movimento: str,
        confianca_ocr: float,
        metodo_ocr: str,
        imagem: Optional[np.ndarray] = None,
        resultados_ocr: Optional[list] = None
    ) -> Optional[Dict]:
        """
        Envia detecção de placa para a API

        Args:
            placa: Placa detectada
            tipo_movimento: "entrada" ou "saida"
            confianca_ocr: Confiança do OCR (0.0 a 1.0)
            metodo_ocr: Método usado ("easyocr", "tesseract", "hibrido")
            imagem: Imagem da detecção (opcional)
            resultados_ocr: Lista de resultados OCR detalhados (opcional)

        Returns:
            Resposta da API ou None em caso de erro
        """
        try:
            # Prepara dados
            dados = {
                "placa_detectada": placa,
                "tipo_movimento": tipo_movimento,
                "confianca_ocr": confianca_ocr,
                "metodo_ocr": metodo_ocr,
                "timestamp": datetime.now().isoformat()
            }

            # Converte imagem para base64 se fornecida
            if imagem is not None:
                imagem_base64 = imagem_para_base64(imagem)
                if imagem_base64:
                    dados["imagem_base64"] = imagem_base64

            # Adiciona resultados OCR detalhados se fornecidos
            if resultados_ocr:
                dados["resultados_ocr"] = [
                    {
                        "texto": r["texto"],
                        "confianca": r["confianca"],
                        "metodo": r["metodo"]
                    }
                    for r in resultados_ocr
                ]

            # Envia para API
            logger.info(f"Enviando detecção: {placa} - {tipo_movimento}")

            response = requests.post(
                self.api_url,
                json=dados,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )

            # Processa resposta
            if response.status_code == 200:
                resultado = response.json()
                self.ultima_resposta = resultado
                logger.info(f"✓ Detecção enviada com sucesso: {resultado.get('mensagem')}")
                return resultado
            else:
                erro = response.json() if response.content else {}
                logger.error(f"Erro na API ({response.status_code}): {erro.get('detail', 'Erro desconhecido')}")
                return None

        except requests.exceptions.Timeout:
            logger.error("Timeout ao conectar à API")
            self.conectado = False
            return None

        except requests.exceptions.ConnectionError:
            logger.error("Erro de conexão com a API")
            self.conectado = False
            return None

        except Exception as e:
            logger.error(f"Erro ao enviar detecção: {e}")
            return None

    def obter_veiculo_por_placa(self, placa: str) -> Optional[Dict]:
        """
        Busca informações de veículo por placa

        Args:
            placa: Placa do veículo

        Returns:
            Dados do veículo ou None
        """
        try:
            base_url = "/".join(self.api_url.split("/")[:-2])
            url = f"{base_url}/veiculos/placa/{placa}"

            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                return None

        except Exception as e:
            logger.error(f"Erro ao buscar veículo: {e}")
            return None

    def obter_estatisticas_hoje(self) -> Optional[Dict]:
        """
        Obtém estatísticas de hoje

        Returns:
            Estatísticas ou None
        """
        try:
            base_url = "/".join(self.api_url.split("/")[:-2])
            url = f"{base_url}/registros/count/hoje"

            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                return None

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return None

    def esta_conectado(self) -> bool:
        """Verifica se está conectado"""
        return self.conectado

    def obter_status(self) -> Dict:
        """
        Obtém status da conexão

        Returns:
            Dict com status
        """
        return {
            "api_url": self.api_url,
            "conectado": self.conectado,
            "timeout": self.timeout,
            "ultima_resposta": self.ultima_resposta
        }
