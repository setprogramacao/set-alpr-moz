"""
Sistema ALPR UNIPIAGET - Desktop Module
Ponto de entrada da aplicação desktop

Autor: Sistema ALPR
Instituição: Universidade Jean Piaget de Moçambique
Curso: Engenharia Electrónica e de Telecomunicações
"""

import tkinter as tk
from tkinter import messagebox
import logging
import logging.handlers
import sys
from pathlib import Path

# Adiciona diretório raiz ao path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from desktop_module.config import (
    validar_configuracoes,
    LOG_FILE,
    LOG_LEVEL,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
)
from desktop_module.ui import MainWindow


def configurar_logging():
    """Configura sistema de logging"""
    # Cria formato de log
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configura handlers
    handlers = [
        logging.StreamHandler(),  # Console
        logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
    ]

    # Configura logging
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )

    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("Sistema ALPR UNIPIAGET - Desktop Module")
    logger.info("=" * 80)

    return logger


def verificar_dependencias():
    """Verifica se todas as dependências estão instaladas"""
    dependencias = {
        "cv2": "opencv-python",
        "ultralytics": "ultralytics",
        "easyocr": "easyocr",
        "pytesseract": "pytesseract",
        "requests": "requests",
        "PIL": "Pillow",
        "dotenv": "python-dotenv"
    }

    faltando = []

    for modulo, pacote in dependencias.items():
        try:
            __import__(modulo)
        except ImportError:
            faltando.append(pacote)

    if faltando:
        mensagem = (
            "Dependências faltando:\n\n" +
            "\n".join(f"  • {pkg}" for pkg in faltando) +
            "\n\nInstale com:\n" +
            f"pip install {' '.join(faltando)}"
        )
        messagebox.showerror("Dependências Faltando", mensagem)
        return False

    return True


def main():
    """Função principal"""
    # Configura logging
    logger = configurar_logging()

    # Verifica dependências
    logger.info("Verificando dependências...")
    if not verificar_dependencias():
        logger.error("Dependências faltando. Encerrando.")
        sys.exit(1)
    logger.info("✓ Todas as dependências instaladas")

    # Valida configurações
    logger.info("Validando configurações...")
    try:
        validar_configuracoes()
        logger.info("✓ Configurações válidas")
    except ValueError as e:
        logger.error(f"Erro nas configurações: {e}")
        messagebox.showerror("Erro de Configuração", str(e))
        sys.exit(1)

    # Cria janela principal
    logger.info("Inicializando interface gráfica...")
    try:
        root = tk.Tk()

        # Configura ícone (se existir)
        # icon_path = Path(__file__).parent / "assets" / "icon.ico"
        # if icon_path.exists():
        #     root.iconbitmap(icon_path)

        # Cria aplicação
        app = MainWindow(root)

        logger.info("Interface inicializada")
        logger.info("Sistema pronto para uso!")

        # Inicia loop principal
        root.mainloop()

    except Exception as e:
        logger.exception(f"Erro fatal: {e}")
        messagebox.showerror("Erro Fatal", f"Erro ao iniciar aplicação:\n\n{e}")
        sys.exit(1)

    logger.info("Aplicação encerrada")


if __name__ == "__main__":
    main()
