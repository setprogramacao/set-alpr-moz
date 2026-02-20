"""
Processamento de Imagens - Desktop Module
Funções auxiliares para manipulação de imagens
"""

import cv2
import numpy as np
from PIL import Image, ImageTk
from typing import Tuple


def preprocessar_para_display(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    """
    Redimensiona frame para exibição mantendo aspect ratio

    Args:
        frame: Frame original
        width: Largura desejada
        height: Altura desejada

    Returns:
        Frame redimensionado
    """
    if frame is None or frame.size == 0:
        return frame

    h, w = frame.shape[:2]
    aspect = w / h

    # Calcula nova dimensão mantendo aspect ratio
    if w > h:
        nova_largura = width
        nova_altura = int(width / aspect)
    else:
        nova_altura = height
        nova_largura = int(height * aspect)

    # Redimensiona
    frame_resized = cv2.resize(frame, (nova_largura, nova_altura), interpolation=cv2.INTER_AREA)

    return frame_resized


def converter_cv_para_pil(frame: np.ndarray) -> ImageTk.PhotoImage:
    """
    Converte frame OpenCV para formato Tkinter PhotoImage

    Args:
        frame: Frame OpenCV (BGR)

    Returns:
        ImageTk.PhotoImage para Tkinter
    """
    if frame is None or frame.size == 0:
        # Retorna imagem vazia
        return ImageTk.PhotoImage(Image.new('RGB', (320, 240), color='black'))

    # Converte BGR para RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Converte para PIL Image
    pil_image = Image.fromarray(frame_rgb)

    # Converte para PhotoImage
    photo = ImageTk.PhotoImage(image=pil_image)

    return photo


def adicionar_texto_overlay(
    frame: np.ndarray,
    texto: str,
    posicao: Tuple[int, int],
    cor: Tuple[int, int, int] = (0, 255, 0),
    tamanho: float = 0.6,
    espessura: int = 2
) -> np.ndarray:
    """
    Adiciona texto overlay no frame

    Args:
        frame: Frame original
        texto: Texto a adicionar
        posicao: Posição (x, y)
        cor: Cor BGR
        tamanho: Tamanho da fonte
        espessura: Espessura do texto

    Returns:
        Frame com texto
    """
    frame_copy = frame.copy()

    cv2.putText(
        frame_copy,
        texto,
        posicao,
        cv2.FONT_HERSHEY_SIMPLEX,
        tamanho,
        cor,
        espessura
    )

    return frame_copy


def desenhar_bounding_box(
    frame: np.ndarray,
    bbox: Tuple[int, int, int, int],
    cor: Tuple[int, int, int] = (0, 255, 0),
    espessura: int = 2,
    label: str = None
) -> np.ndarray:
    """
    Desenha bounding box no frame

    Args:
        frame: Frame original
        bbox: (x1, y1, x2, y2)
        cor: Cor BGR
        espessura: Espessura da linha
        label: Label opcional

    Returns:
        Frame com bounding box
    """
    frame_copy = frame.copy()
    x1, y1, x2, y2 = bbox

    # Desenha retângulo
    cv2.rectangle(frame_copy, (x1, y1), (x2, y2), cor, espessura)

    # Adiciona label se fornecido
    if label:
        (texto_w, texto_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame_copy, (x1, y1 - texto_h - 10), (x1 + texto_w, y1), cor, -1)
        cv2.putText(frame_copy, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    return frame_copy
