"""
Configurações - Desktop Module ALPR UNIPIAGET
Carrega configurações do arquivo .env e define constantes
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# ============================================================================
# DIRETÓRIOS
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "images"
LOGS_DIR = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR / "desktop_module" / "models"

# Cria diretórios se não existirem
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# API CONFIGURATION
# ============================================================================

API_HOST = os.getenv("API_HOST", "http://localhost:8000")
API_BASE_URL = f"{API_HOST}/api/v1"
API_DETECCAO_ENDPOINT = f"{API_BASE_URL}/registros/deteccao"
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))  # segundos


# ============================================================================
# YOLO CONFIGURATION
# ============================================================================

YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", str(MODELS_DIR / "yolov8n.pt"))
YOLO_CONFIDENCE_THRESHOLD = float(os.getenv("YOLO_CONFIDENCE", "0.5"))
YOLO_IOU_THRESHOLD = float(os.getenv("YOLO_IOU", "0.45"))
YOLO_DEVICE = os.getenv("YOLO_DEVICE", "cpu")  # "cpu" ou "cuda"


# ============================================================================
# OCR CONFIGURATION
# ============================================================================

OCR_METHOD = os.getenv("OCR_METHOD", "hibrido")  # "easyocr", "tesseract", "hibrido"
OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "en").split(",")  # ["en"]
OCR_MIN_CONFIDENCE = float(os.getenv("OCR_MIN_CONFIDENCE", "0.6"))

# EasyOCR
EASYOCR_GPU = os.getenv("EASYOCR_GPU", "False").lower() == "true"

# Tesseract
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "tesseract")  # Caminho do executável
TESSERACT_CONFIG = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


# ============================================================================
# CAMERA/VIDEO CONFIGURATION
# ============================================================================

VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", "0")  # "0" = webcam, ou caminho de arquivo
PROCESS_EVERY_N_FRAMES = int(os.getenv("PROCESS_EVERY_N_FRAMES", "5"))
FRAME_RESIZE_WIDTH = int(os.getenv("FRAME_RESIZE_WIDTH", "640"))
FRAME_RESIZE_HEIGHT = int(os.getenv("FRAME_RESIZE_HEIGHT", "480"))
FPS_LIMIT = int(os.getenv("FPS_LIMIT", "30"))


# ============================================================================
# DETECTION CONFIGURATION
# ============================================================================

# Cooldown entre detecções da mesma placa (segundos)
DETECTION_COOLDOWN = int(os.getenv("DETECTION_COOLDOWN", "300"))  # 5 minutos

# Salvar imagens das detecções
SAVE_DETECTION_IMAGES = os.getenv("SAVE_DETECTION_IMAGES", "True").lower() == "true"

# Tipo de movimento padrão
DEFAULT_MOVEMENT_TYPE = os.getenv("DEFAULT_MOVEMENT_TYPE", "entrada")  # "entrada" ou "saida"

# Auto alternar tipo de movimento
AUTO_TOGGLE_MOVEMENT = os.getenv("AUTO_TOGGLE_MOVEMENT", "True").lower() == "true"


# ============================================================================
# UI CONFIGURATION
# ============================================================================

WINDOW_TITLE = "Sistema ALPR UNIPIAGET - Módulo Desktop"
WINDOW_WIDTH = int(os.getenv("WINDOW_WIDTH", "1200"))
WINDOW_HEIGHT = int(os.getenv("WINDOW_HEIGHT", "800"))
PREVIEW_WIDTH = 640
PREVIEW_HEIGHT = 480


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = LOGS_DIR / "desktop_module.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5


# ============================================================================
# DETECTION PARAMETERS
# ============================================================================

# Pré-processamento de imagem
PREPROCESSING_ENABLED = True
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID_SIZE = (8, 8)

# Filtros de detecção
MIN_PLATE_WIDTH = 80  # pixels
MIN_PLATE_HEIGHT = 20  # pixels
MAX_PLATE_WIDTH = 400  # pixels
MAX_PLATE_HEIGHT = 200  # pixels


# ============================================================================
# VALIDATION
# ============================================================================

def validar_configuracoes():
    """
    Valida configurações essenciais

    Raises:
        ValueError: Se alguma configuração crítica estiver inválida
    """
    erros = []

    # Valida modelo YOLO
    if not Path(YOLO_MODEL_PATH).exists():
        erros.append(f"Modelo YOLO não encontrado: {YOLO_MODEL_PATH}")

    # Valida OCR method
    if OCR_METHOD not in ["easyocr", "tesseract", "hibrido"]:
        erros.append(f"Método OCR inválido: {OCR_METHOD}. Use 'easyocr', 'tesseract' ou 'hibrido'")

    # Valida API URL
    if not API_HOST.startswith("http"):
        erros.append(f"API_HOST inválido: {API_HOST}. Deve começar com http:// ou https://")

    # Valida video source
    if VIDEO_SOURCE != "0" and not Path(VIDEO_SOURCE).exists():
        print(f"AVISO: Video source não encontrado: {VIDEO_SOURCE}. Tentando usar webcam...")

    if erros:
        raise ValueError(f"Erros de configuração:\n" + "\n".join(f"- {erro}" for erro in erros))

    print("[OK] Configuracoes validadas com sucesso")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def obter_config_display():
    """
    Retorna configurações em formato legível para display

    Returns:
        dict: Dicionário com configurações principais
    """
    return {
        "API": {
            "Host": API_HOST,
            "Timeout": f"{API_TIMEOUT}s"
        },
        "YOLO": {
            "Modelo": Path(YOLO_MODEL_PATH).name,
            "Confiança": f"{YOLO_CONFIDENCE_THRESHOLD:.1%}",
            "Dispositivo": YOLO_DEVICE
        },
        "OCR": {
            "Método": OCR_METHOD.upper(),
            "Confiança Mínima": f"{OCR_MIN_CONFIDENCE:.1%}",
            "Idiomas": ", ".join(OCR_LANGUAGES)
        },
        "Vídeo": {
            "Source": VIDEO_SOURCE if VIDEO_SOURCE != "0" else "Webcam",
            "Processar Frames": f"1 a cada {PROCESS_EVERY_N_FRAMES}",
            "Resolução": f"{FRAME_RESIZE_WIDTH}x{FRAME_RESIZE_HEIGHT}"
        },
        "Detecção": {
            "Cooldown": f"{DETECTION_COOLDOWN}s",
            "Salvar Imagens": "Sim" if SAVE_DETECTION_IMAGES else "Não",
            "Tipo Movimento": DEFAULT_MOVEMENT_TYPE.capitalize()
        }
    }


# Valida configurações ao importar
if __name__ != "__main__":
    try:
        validar_configuracoes()
    except ValueError as e:
        print(f"ERRO: {e}")
        print("Corriga as configurações no arquivo .env e tente novamente.")
