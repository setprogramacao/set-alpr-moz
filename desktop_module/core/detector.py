"""
Detector de Placas - Desktop Module ALPR UNIPIAGET
Detecção com YOLO v8 + OCR duplo (EasyOCR + Tesseract)
"""

import cv2
import re
import numpy as np
from ultralytics import YOLO
import easyocr
import pytesseract
from typing import List, Tuple, Optional, Dict
from datetime import datetime
import logging

from ..config import (
    YOLO_MODEL_PATH,
    YOLO_CONFIDENCE_THRESHOLD,
    OCR_METHOD,
    OCR_MIN_CONFIDENCE,
    EASYOCR_GPU,
    TESSERACT_CMD,
    TESSERACT_CONFIG,
    OCR_LANGUAGES,
)
from shared.utils import (
    validar_placa_mocambique,
    corrigir_placa_ocr,
    preprocessar_imagem_placa,
    preprocessar_imagem_placa_cinza,
)

# Configura logger
logger = logging.getLogger(__name__)


class PlateDetector:
    """
    Detector de placas veiculares usando YOLO v8 e OCR duplo
    """

    def __init__(self):
        """Inicializa detector YOLO e engines OCR"""
        logger.info("Inicializando PlateDetector...")

        # Cache para evitar recalcular tipo de modelo a cada frame
        self._is_plate_model_cache = None

        # Carrega modelo YOLO
        try:
            self.yolo_model = YOLO(YOLO_MODEL_PATH)
            logger.info(f"✓ Modelo YOLO carregado: {YOLO_MODEL_PATH}")
        except Exception as e:
            logger.error(f"Erro ao carregar modelo YOLO: {e}")
            raise

        # Inicializa EasyOCR
        self.easyocr_reader = None
        if OCR_METHOD in ["easyocr", "hibrido"]:
            try:
                self.easyocr_reader = easyocr.Reader(
                    OCR_LANGUAGES,
                    gpu=EASYOCR_GPU,
                    verbose=False
                )
                logger.info(f"✓ EasyOCR inicializado (GPU: {EASYOCR_GPU})")
            except Exception as e:
                logger.error(f"Erro ao inicializar EasyOCR: {e}")
                if OCR_METHOD == "easyocr":
                    raise

        # Configura Tesseract
        if OCR_METHOD in ["tesseract", "hibrido"]:
            try:
                pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
                # Testa Tesseract
                pytesseract.get_tesseract_version()
                logger.info("✓ Tesseract configurado")
            except Exception as e:
                logger.error(f"Erro ao configurar Tesseract: {e}")
                if OCR_METHOD == "tesseract":
                    raise

        logger.info(f"PlateDetector pronto! Método OCR: {OCR_METHOD.upper()}")

    def detectar_placas_opencv(self, regiao_veiculo: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detecta placas dentro de uma região usando OpenCV (detecção de contornos)

        Args:
            regiao_veiculo: Imagem da região do veículo

        Returns:
            Lista de bounding boxes de possíveis placas: [(x1,y1,x2,y2), ...]
        """
        placas_encontradas = []

        # Converte para escala de cinza
        gray = cv2.cvtColor(regiao_veiculo, cv2.COLOR_BGR2GRAY)

        # Aplica blur para reduzir ruído
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        # Detecção de bordas
        edges = cv2.Canny(blur, 50, 200)

        # Encontra contornos
        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            # Aproxima o contorno
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

            # Placas geralmente têm 4 lados (retângulos)
            if len(approx) >= 4:
                x, y, w, h = cv2.boundingRect(contour)

                # Filtros para características de placas:
                # 1. Aspect ratio (largura/altura) - placas são geralmente horizontais
                # 2. Tamanho mínimo
                # 3. Área mínima
                aspect_ratio = w / h if h > 0 else 0
                area = cv2.contourArea(contour)

                # Filtros relaxados para melhor detecção
                if (1.5 <= aspect_ratio <= 7.0 and
                    w >= 30 and h >= 10 and
                    area >= 300):

                    placas_encontradas.append((x, y, x + w, y + h))

        return placas_encontradas

    def _is_plate_model(self) -> bool:
        """
        Verifica se o modelo carregado é específico para placas.
        Modelos de placas tipicamente têm 1-2 classes (plate, license_plate, etc.)
        Modelos genéricos (COCO) têm 80 classes.
        Resultado é cacheado para não recalcular a cada frame.
        """
        if self._is_plate_model_cache is not None:
            return self._is_plate_model_cache

        try:
            names = self.yolo_model.names
            num_classes = len(names)

            # Se tem poucas classes, provavelmente é modelo de placas
            if num_classes <= 5:
                logger.info(f"Modelo de PLACAS detectado ({num_classes} classes: {names})")
                self._is_plate_model_cache = True
            else:
                logger.info(f"Modelo GENÉRICO detectado ({num_classes} classes)")
                self._is_plate_model_cache = False

            return self._is_plate_model_cache
        except Exception:
            self._is_plate_model_cache = False
            return False

    def detectar_placas(self, frame: np.ndarray) -> List[Dict]:
        """
        Detecta placas em um frame.

        Suporta dois modos automáticos:
        - Modelo de placas: Detecção directa (YOLO encontra placas)
        - Modelo genérico: Abordagem híbrida (YOLO veículos + OpenCV placas)

        Args:
            frame: Frame de vídeo (numpy array BGR)

        Returns:
            Lista de detecções: [{"bbox": (x1,y1,x2,y2), "confidence": float}, ...]
        """
        if self._is_plate_model():
            return self._detectar_placas_directo(frame)
        else:
            return self._detectar_placas_hibrido(frame)

    def _detectar_placas_directo(self, frame: np.ndarray) -> List[Dict]:
        """
        Detecção DIRECTA de placas - para modelos treinados especificamente
        para detectar license plates (ex: modelo Roboflow).

        O modelo YOLO detecta placas directamente no frame,
        sem etapa intermediária de detecção de veículos.
        """
        try:
            results = self.yolo_model(frame, verbose=False)[0]

            deteccoes = []

            for box in results.boxes:
                confidence = float(box.conf[0])

                # Filtra por confiança mínima
                if confidence < YOLO_CONFIDENCE_THRESHOLD:
                    continue

                # Extrai coordenadas (todas as classes são placas neste modelo)
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                # Margem de segurança
                h, w = frame.shape[:2]
                margin = 5
                x1 = max(0, x1 - margin)
                y1 = max(0, y1 - margin)
                x2 = min(w, x2 + margin)
                y2 = min(h, y2 + margin)

                deteccoes.append({
                    "bbox": (x1, y1, x2, y2),
                    "confidence": confidence
                })

            logger.info(f"[DIRECTO] Detectadas {len(deteccoes)} placa(s)")
            return deteccoes

        except Exception as e:
            logger.error(f"Erro na detecção directa YOLO: {e}")
            return []

    def _detectar_placas_hibrido(self, frame: np.ndarray) -> List[Dict]:
        """
        Detecção HÍBRIDA (fallback para modelo genérico YOLOv8n):
        1. YOLO detecta veículos (car, truck, bus, motorcycle)
        2. OpenCV procura placas dentro da região do veículo
        """
        try:
            results = self.yolo_model(frame, verbose=False)[0]

            deteccoes = []

            # IDs das classes de veículos no COCO dataset
            VEHICLE_CLASSES = [2, 3, 5, 7]  # car, motorcycle, bus, truck

            for box in results.boxes:
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])

                if class_id not in VEHICLE_CLASSES:
                    continue

                if confidence < YOLO_CONFIDENCE_THRESHOLD:
                    continue

                vx1, vy1, vx2, vy2 = map(int, box.xyxy[0])

                # Margem de segurança
                h, w = frame.shape[:2]
                vx1 = max(0, vx1 - 10)
                vy1 = max(0, vy1 - 10)
                vx2 = min(w, vx2 + 10)
                vy2 = min(h, vy2 + 10)

                regiao_veiculo = frame[vy1:vy2, vx1:vx2]

                if regiao_veiculo.size == 0:
                    continue

                # Procura placas dentro do veículo usando OpenCV
                placas_relativas = self.detectar_placas_opencv(regiao_veiculo)

                for (px1, py1, px2, py2) in placas_relativas:
                    deteccoes.append({
                        "bbox": (vx1 + px1, vy1 + py1, vx1 + px2, vy1 + py2),
                        "confidence": confidence * 0.9
                    })

            logger.info(f"[HÍBRIDO] Detectadas {len(deteccoes)} placa(s) em {len([b for b in results.boxes if int(b.cls[0]) in VEHICLE_CLASSES])} veículo(s)")
            return deteccoes

        except Exception as e:
            logger.error(f"Erro na detecção híbrida YOLO: {e}")
            return []

    def extrair_texto_easyocr(self, imagem_placa: np.ndarray) -> Tuple[str, float]:
        """
        Extrai texto usando EasyOCR

        Melhorias em relação à versão anterior:
        - Segmentos ordenados da esquerda para a direita (por x-coordinate)
        - Limpeza básica por segmento (só remove chars especiais)
        - corrigir_placa_ocr() aplicado no texto COMPLETO (não em fragmentos)

        Args:
            imagem_placa: Imagem da placa (cinza com CLAHE, sem binarização)

        Returns:
            (texto_corrigido, confianca_media)
        """
        if self.easyocr_reader is None:
            return "", 0.0

        try:
            resultados = self.easyocr_reader.readtext(
                imagem_placa,
                detail=1,
                paragraph=False,
                allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            )

            if not resultados:
                return "", 0.0

            # Ordena da esquerda para a direita (pelo x mínimo do bbox)
            resultados = sorted(resultados, key=lambda item: min(p[0] for p in item[0]))

            textos, confiancas = [], []
            for (bbox, texto, conf) in resultados:
                texto_limpo = re.sub(r'[^A-Z0-9]', '', texto.upper())
                if texto_limpo:
                    textos.append(texto_limpo)
                    confiancas.append(conf)

            if not textos:
                return "", 0.0

            # Junta TUDO e aplica correção uma vez no texto completo
            texto_bruto = "".join(textos)
            texto_corrigido = corrigir_placa_ocr(texto_bruto)
            confianca_media = sum(confiancas) / len(confiancas)

            logger.debug(f"EasyOCR bruto: '{texto_bruto}' → corrigido: '{texto_corrigido}'")
            return texto_corrigido, confianca_media

        except Exception as e:
            logger.error(f"Erro no EasyOCR: {e}")
            return "", 0.0

    def extrair_texto_tesseract(self, imagem_placa: np.ndarray) -> Tuple[str, float]:
        """
        Extrai texto usando Tesseract OCR

        Melhorias em relação à versão anterior:
        - Tenta múltiplos modos PSM (7, 8, 6) e fica com o melhor resultado
        - Limpeza básica por segmento (não em fragmentos)
        - corrigir_placa_ocr() aplicado no texto COMPLETO

        Args:
            imagem_placa: Imagem da placa (binária ou cinza)

        Returns:
            (texto_corrigido, confianca)
        """
        WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        CONFIGS = [
            f"--psm 7 --oem 3 -c tessedit_char_whitelist={WHITELIST}",  # linha única
            f"--psm 8 --oem 3 -c tessedit_char_whitelist={WHITELIST}",  # palavra única
            f"--psm 6 --oem 3 -c tessedit_char_whitelist={WHITELIST}",  # bloco uniforme
        ]

        melhor_texto = ""
        melhor_confianca = 0.0

        for config in CONFIGS:
            try:
                dados = pytesseract.image_to_data(
                    imagem_placa,
                    config=config,
                    output_type=pytesseract.Output.DICT
                )

                textos = []
                confiancas = []

                for i, texto in enumerate(dados['text']):
                    conf = int(dados['conf'][i])
                    if conf > 0 and texto.strip():
                        # Limpeza mínima por token (não aplica corrigir!)
                        texto_limpo = re.sub(r'[^A-Z0-9]', '', texto.upper())
                        if texto_limpo:
                            textos.append(texto_limpo)
                            confiancas.append(conf / 100.0)

                if textos:
                    texto_bruto = "".join(textos)
                    texto_corrigido = corrigir_placa_ocr(texto_bruto)
                    confianca = sum(confiancas) / len(confiancas)

                    logger.debug(f"Tesseract ({config[:8]}): '{texto_bruto}' → '{texto_corrigido}' ({confianca:.2f})")

                    if confianca > melhor_confianca:
                        melhor_texto = texto_corrigido
                        melhor_confianca = confianca

            except Exception as e:
                logger.debug(f"Tesseract config '{config[:8]}' falhou: {e}")
                continue

        return melhor_texto, melhor_confianca

    def reconhecer_placa(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[Dict]:
        """
        Reconhece texto da placa usando OCR duplo.

        Cada engine OCR recebe o preprocessamento ideal:
        - EasyOCR → imagem em cinza + CLAHE (SEM binarização)
        - Tesseract → imagem binária adaptativa

        Args:
            frame: Frame completo
            bbox: Bounding box (x1, y1, x2, y2)

        Returns:
            Dict com resultado do OCR ou None
        """
        x1, y1, x2, y2 = bbox

        # Recorta região da placa
        imagem_placa = frame[y1:y2, x1:x2]

        if imagem_placa.size == 0:
            return None

        # Preprocessamento optimizado por engine
        imagem_cinza   = preprocessar_imagem_placa_cinza(imagem_placa)  # EasyOCR
        imagem_binaria = preprocessar_imagem_placa(imagem_placa)         # Tesseract

        resultados_ocr = []

        # OCR com EasyOCR (usa imagem cinza com CLAHE)
        if OCR_METHOD in ["easyocr", "hibrido"]:
            texto_easy, conf_easy = self.extrair_texto_easyocr(imagem_cinza)
            if texto_easy:
                resultados_ocr.append({
                    "texto": texto_easy,
                    "confianca": conf_easy,
                    "metodo": "easyocr"
                })

        # OCR com Tesseract (usa imagem binária)
        if OCR_METHOD in ["tesseract", "hibrido"]:
            texto_tess, conf_tess = self.extrair_texto_tesseract(imagem_binaria)
            if texto_tess:
                resultados_ocr.append({
                    "texto": texto_tess,
                    "confianca": conf_tess,
                    "metodo": "tesseract"
                })

        if not resultados_ocr:
            return None

        # Selecção do melhor resultado
        if OCR_METHOD == "hibrido" and len(resultados_ocr) == 2:
            t1 = resultados_ocr[0]["texto"]
            t2 = resultados_ocr[1]["texto"]

            if t1 == t2:
                # Ambos concordam — alta confiança
                melhor = resultados_ocr[0]
            else:
                valido1, _ = validar_placa_mocambique(t1)
                valido2, _ = validar_placa_mocambique(t2)

                if valido1 and not valido2:
                    melhor = resultados_ocr[0]
                elif valido2 and not valido1:
                    melhor = resultados_ocr[1]
                else:
                    # Ambos válidos ou nenhum → confiança decide
                    melhor = max(resultados_ocr, key=lambda r: r["confianca"])
        else:
            melhor = resultados_ocr[0]

        # Salvaguarda final — garante formato correcto
        texto_final = corrigir_placa_ocr(melhor["texto"])
        placa_valida, placa_limpa = validar_placa_mocambique(texto_final)

        if not placa_valida or melhor["confianca"] < OCR_MIN_CONFIDENCE:
            logger.debug(
                f"Placa rejeitada: '{texto_final}' "
                f"(válida={placa_valida}, conf={melhor['confianca']:.2f})"
            )
            return None

        return {
            "placa": placa_limpa,
            "confianca": melhor["confianca"],
            "metodo": melhor["metodo"] if OCR_METHOD != "hibrido" else "hibrido",
            "imagem_placa": imagem_placa,
            "todos_resultados": resultados_ocr
        }

    def processar_frame(self, frame: np.ndarray) -> List[Dict]:
        """
        Processa frame completo: detecta placas e reconhece texto

        Args:
            frame: Frame de vídeo

        Returns:
            Lista de detecções com OCR: [{"placa": str, "confidence": float, "bbox": tuple, ...}, ...]
        """
        resultados_finais = []

        # Detecta placas
        deteccoes = self.detectar_placas(frame)

        # Para cada placa detectada, executa OCR
        for deteccao in deteccoes:
            bbox = deteccao["bbox"]
            yolo_conf = deteccao["confidence"]

            # Reconhece texto
            resultado_ocr = self.reconhecer_placa(frame, bbox)

            if resultado_ocr:
                resultados_finais.append({
                    "placa": resultado_ocr["placa"],
                    "confianca_yolo": yolo_conf,
                    "confianca_ocr": resultado_ocr["confianca"],
                    "confianca_final": (yolo_conf + resultado_ocr["confianca"]) / 2,
                    "metodo_ocr": resultado_ocr["metodo"],
                    "bbox": bbox,
                    "imagem_placa": resultado_ocr["imagem_placa"],
                    "timestamp": datetime.now(),
                    "resultados_ocr_detalhados": resultado_ocr.get("todos_resultados", [])
                })

        return resultados_finais

    def desenhar_deteccoes(self, frame: np.ndarray, deteccoes: List[Dict]) -> np.ndarray:
        """
        Desenha bounding boxes e texto nas detecções

        Args:
            frame: Frame original
            deteccoes: Lista de detecções processadas

        Returns:
            Frame anotado
        """
        frame_anotado = frame.copy()

        for det in deteccoes:
            bbox = det["bbox"]
            placa = det["placa"]
            confianca = det["confianca_ocr"]

            x1, y1, x2, y2 = bbox

            # Desenha retângulo verde
            cv2.rectangle(frame_anotado, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Formata texto
            texto = f"{placa} ({confianca:.0%})"

            # Fundo para texto
            (texto_w, texto_h), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame_anotado, (x1, y1 - texto_h - 10), (x1 + texto_w, y1), (0, 255, 0), -1)

            # Desenha texto
            cv2.putText(
                frame_anotado,
                texto,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2
            )

        return frame_anotado
