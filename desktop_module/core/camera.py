"""
Gerenciador de Câmera - Desktop Module ALPR UNIPIAGET
Captura de vídeo de webcam, arquivos ou imagens
"""

import cv2
import numpy as np
from typing import Optional, Tuple
import logging
from pathlib import Path

from ..config import VIDEO_SOURCE, FRAME_RESIZE_WIDTH, FRAME_RESIZE_HEIGHT

logger = logging.getLogger(__name__)


class CameraManager:
    """
    Gerenciador de captura de vídeo/imagens
    """

    def __init__(self, source: Optional[str] = None):
        """
        Inicializa gerenciador de câmera

        Args:
            source: Fonte de vídeo (None = usar config, 0 = webcam, caminho = arquivo)
        """
        self.source = source if source is not None else VIDEO_SOURCE
        self.cap = None
        self.is_camera = False
        self.is_image = False
        self.is_video = False
        self.frame_atual = None
        self.fps = 30
        self.total_frames = 0
        self.frame_count = 0

        logger.info(f"CameraManager inicializado com source: {self.source}")

    def abrir(self) -> bool:
        """
        Abre fonte de vídeo

        Returns:
            True se aberto com sucesso
        """
        try:
            # Verifica se é webcam (0, 1, 2, etc.)
            if self.source.isdigit():
                source_int = int(self.source)
                self.cap = cv2.VideoCapture(source_int)
                self.is_camera = True
                logger.info(f"Abrindo webcam: {source_int}")

            # Verifica se é arquivo de imagem
            elif Path(self.source).suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                imagem = cv2.imread(self.source)
                if imagem is not None:
                    self.frame_atual = imagem
                    self.is_image = True
                    logger.info(f"Imagem carregada: {self.source}")
                    return True
                else:
                    logger.error(f"Não foi possível carregar imagem: {self.source}")
                    return False

            # Arquivo de vídeo
            else:
                self.cap = cv2.VideoCapture(self.source)
                self.is_video = True
                logger.info(f"Abrindo arquivo de vídeo: {self.source}")

            # Verifica se abriu com sucesso (para câmera/vídeo)
            if self.cap and not self.cap.isOpened():
                logger.error(f"Erro ao abrir fonte: {self.source}")
                return False

            # Obtém propriedades do vídeo/câmera
            if self.cap:
                self.fps = self.cap.get(cv2.CAP_PROP_FPS)
                if self.fps == 0:
                    self.fps = 30  # Default

                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

                logger.info(f"✓ Fonte aberta - FPS: {self.fps}, Total Frames: {self.total_frames}")

            return True

        except Exception as e:
            logger.error(f"Erro ao abrir fonte: {e}")
            return False

    def ler_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Lê próximo frame

        Returns:
            (sucesso: bool, frame: Optional[np.ndarray])
        """
        # Se for imagem, retorna a mesma sempre
        if self.is_image:
            if self.frame_atual is not None:
                return True, self.frame_atual.copy()
            return False, None

        # Para câmera/vídeo
        if self.cap is None or not self.cap.isOpened():
            return False, None

        try:
            ret, frame = self.cap.read()

            if not ret:
                return False, None

            self.frame_count += 1
            self.frame_atual = frame

            # Redimensiona frame se necessário
            if FRAME_RESIZE_WIDTH > 0 and FRAME_RESIZE_HEIGHT > 0:
                frame = cv2.resize(frame, (FRAME_RESIZE_WIDTH, FRAME_RESIZE_HEIGHT))

            return True, frame

        except Exception as e:
            logger.error(f"Erro ao ler frame: {e}")
            return False, None

    def fechar(self):
        """Fecha fonte de vídeo"""
        if self.cap:
            self.cap.release()
            logger.info("Fonte de vídeo fechada")

        self.cap = None
        self.frame_atual = None

    def reiniciar(self) -> bool:
        """
        Reinicia captura (útil para vídeos)

        Returns:
            True se reiniciado com sucesso
        """
        if self.is_image:
            return True  # Imagens não precisam reiniciar

        if self.cap and self.is_video:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.frame_count = 0
            logger.info("Vídeo reiniciado")
            return True

        return False

    def obter_progresso(self) -> float:
        """
        Obtém progresso da reprodução (para vídeos)

        Returns:
            Progresso de 0.0 a 1.0
        """
        if self.is_video and self.total_frames > 0:
            return self.frame_count / self.total_frames
        return 0.0

    def esta_aberto(self) -> bool:
        """Verifica se fonte está aberta"""
        if self.is_image:
            return self.frame_atual is not None

        return self.cap is not None and self.cap.isOpened()

    def obter_info(self) -> dict:
        """
        Obtém informações sobre a fonte

        Returns:
            Dict com informações
        """
        info = {
            "source": self.source,
            "tipo": "imagem" if self.is_image else ("camera" if self.is_camera else "video"),
            "aberto": self.esta_aberto(),
            "fps": self.fps,
            "frame_atual": self.frame_count,
            "total_frames": self.total_frames,
            "progresso": f"{self.obter_progresso():.1%}"
        }

        if self.cap and self.esta_aberto():
            info["largura"] = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            info["altura"] = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        return info

    def __enter__(self):
        """Context manager entry"""
        self.abrir()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.fechar()

    def __del__(self):
        """Destructor"""
        self.fechar()
