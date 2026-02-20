"""
Script Simples para Verificar Modelo YOLO
Carrega o modelo e mostra informações básicas
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent  # raiz do projeto
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv()

import os

def verificar_modelo():
    """Verifica se o modelo YOLO está OK"""
    try:
        from ultralytics import YOLO

        model_path = os.getenv("YOLO_MODEL_PATH", "desktop_module/models/yolov8n.pt")
        full_path = ROOT_DIR / model_path

        print()
        print("=" * 70)
        print("  VERIFICAÇÃO DO MODELO YOLO - ALPR UNIPIAGET")
        print("=" * 70)
        print()
        print(f"  Caminho: {full_path}")

        if not full_path.exists():
            print(f"  [ERRO] Ficheiro não encontrado!")
            return False

        size_mb = full_path.stat().st_size / 1024 / 1024
        print(f"  Tamanho: {size_mb:.1f} MB")
        print()
        print("  Carregando modelo...")

        model = YOLO(str(full_path))

        print("  [OK] Modelo carregado com sucesso!")
        print()

        # Informações do modelo
        names = model.names
        print(f"  Classes detectadas: {len(names)}")
        print(f"  Nomes das classes: {names}")
        print()

        # Tipo de modelo
        if len(names) <= 5:
            print("  [INFO] Tipo: MODELO DE PLACAS")
            print("  → Detecção directa de placas (modo optimizado)")
        else:
            print("  [INFO] Tipo: MODELO GENÉRICO")
            print("  → Detecção via veículos + OpenCV (modo híbrido)")

        print()
        print("=" * 70)
        print("  ✓ Modelo pronto para uso!")
        print("=" * 70)
        print()

        # Instruções
        print("  Próximos passos:")
        print("  1. Instale dependências: pip install -r requirements.txt")
        print("  2. Teste com imagem: python testar_modelo.py imagem.jpg")
        print("  3. Teste com webcam: python testar_modelo.py --webcam")
        print("  4. Inicie o sistema desktop: python main_desktop.py")
        print()

        return True

    except ImportError as e:
        print(f"  [ERRO] Dependência não instalada: {e}")
        print()
        print("  Execute: pip install ultralytics python-dotenv")
        return False
    except Exception as e:
        print(f"  [ERRO] Falha ao carregar modelo: {e}")
        return False

if __name__ == "__main__":
    verificar_modelo()
