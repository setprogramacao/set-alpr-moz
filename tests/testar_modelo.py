"""
Script de teste do modelo YOLO para detecção de placas
Sistema ALPR UNIPIAGET

Uso:
    python testar_modelo.py                          # Testa com imagem de exemplo
    python testar_modelo.py caminho/imagem.jpg       # Testa com imagem específica
    python testar_modelo.py --webcam                 # Testa com webcam ao vivo (com GUI)
    python testar_modelo.py --webcam --no-gui        # Testa com webcam (salva frames em arquivo)
    python testar_modelo.py --webcam --no-gui --frames=20  # Captura 20 frames
"""

import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent  # raiz do projeto
sys.path.insert(0, str(ROOT_DIR))

# Carrega .env
from dotenv import load_dotenv
load_dotenv()

import cv2
import numpy as np


def carregar_modelo():
    """Carrega o modelo YOLO configurado no .env"""
    from ultralytics import YOLO

    model_path = os.getenv("YOLO_MODEL_PATH", "desktop_module/models/yolov8n.pt")
    full_path = ROOT_DIR / model_path

    print(f"\n  Modelo: {full_path}")

    if not full_path.exists():
        print(f"  [ERRO] Ficheiro não encontrado: {full_path}")
        print()
        print("  Execute primeiro: python baixar_modelo_roboflow.py")
        return None

    print(f"  Tamanho: {full_path.stat().st_size / 1024 / 1024:.1f} MB")

    model = YOLO(str(full_path))

    # Info do modelo
    names = model.names
    print(f"  Classes: {len(names)} → {names}")
    print()

    if len(names) <= 5:
        print("  [OK] Modelo de PLACAS (detecção directa)")
    else:
        print("  [INFO] Modelo GENÉRICO (detecção via veículos + OpenCV)")

    return model


def testar_com_imagem(model, image_path):
    """Testa detecção numa imagem"""
    print(f"\n  Testando com: {image_path}")

    img = cv2.imread(str(image_path))
    if img is None:
        print(f"  [ERRO] Não foi possível carregar: {image_path}")
        return

    print(f"  Dimensões: {img.shape[1]}x{img.shape[0]}")

    # Detecção
    confidence = float(os.getenv("YOLO_CONFIDENCE", "0.25"))
    results = model(img, conf=confidence, verbose=False)[0]

    print(f"  Confiança mínima: {confidence}")
    print(f"  Detecções: {len(results.boxes)}")
    print()

    if len(results.boxes) == 0:
        print("  [AVISO] Nenhuma detecção encontrada.")
        print("  Tente:")
        print("  - Reduzir YOLO_CONFIDENCE no .env (ex: 0.25)")
        print("  - Usar uma imagem com placa visível")
        return

    # Mostra detecções
    for i, box in enumerate(results.boxes):
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls_name = model.names[cls_id]

        print(f"  [{i+1}] Classe: {cls_name} | Confiança: {conf:.1%} | Box: ({x1},{y1})-({x2},{y2})")

        # Desenha na imagem
        color = (0, 255, 0)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        label = f"{cls_name} {conf:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(img, (x1, y1 - th - 8), (x1 + tw, y1), color, -1)
        cv2.putText(img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    # Salva resultado
    output_dir = ROOT_DIR / "storage" / "debug"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"teste_modelo_{Path(image_path).stem}.jpg"
    cv2.imwrite(str(output_path), img)
    print(f"\n  Resultado salvo: {output_path}")

    # Tenta mostrar
    try:
        cv2.imshow("Teste Modelo YOLO - ALPR UNIPIAGET", img)
        print("  Pressione qualquer tecla para fechar...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except Exception:
        print("  (Sem display disponível - resultado salvo em ficheiro)")


def testar_com_webcam(model, usar_gui=True, num_frames=None):
    """Testa detecção em tempo real com webcam"""
    print("\n  Iniciando webcam...")
    if usar_gui:
        print("  Pressione 'Q' para sair")
    else:
        print(f"  Modo sem GUI - capturando {num_frames or 10} frames")
    print()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("  [ERRO] Não foi possível abrir a webcam")
        return

    confidence = float(os.getenv("YOLO_CONFIDENCE", "0.25"))

    # Modo sem GUI - salva frames
    if not usar_gui:
        output_dir = ROOT_DIR / "storage" / "debug" / "webcam_frames"
        output_dir.mkdir(parents=True, exist_ok=True)
        max_frames = num_frames or 10
        frame_count = 0

        from datetime import datetime

        while frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # Detecção
            results = model(frame, conf=confidence, verbose=False)[0]

            # Desenha detecções
            for box in results.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_name = model.names[cls_id]

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"{cls_name} {conf:.0%}"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Info no frame
            cv2.putText(frame, f"Frame {frame_count}/{max_frames} - Deteccoes: {len(results.boxes)}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            # Salva frame
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"frame_{frame_count:02d}_{timestamp}.jpg"
            cv2.imwrite(str(output_path), frame)

            print(f"  Frame {frame_count:02d}/{max_frames}: {len(results.boxes)} detecção(ões) → {output_path.name}")

            import time
            time.sleep(0.3)

        cap.release()
        print(f"\n  ✓ {frame_count} frames salvos em: {output_dir}")
        print()
        return

    # Modo com GUI (original)
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Detecção
            results = model(frame, conf=confidence, verbose=False)[0]

            # Desenha detecções
            for box in results.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_name = model.names[cls_id]

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"{cls_name} {conf:.0%}"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Info
            cv2.putText(frame, f"Deteccoes: {len(results.boxes)} | Conf: {confidence}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            cv2.imshow("ALPR UNIPIAGET - Teste Modelo (Q=Sair)", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        print("  Webcam encerrada.")
    except Exception as e:
        cap.release()
        print(f"  [ERRO] Problema com display GUI: {e}")
        print("  Use: python testar_modelo.py --webcam --no-gui")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  TESTE DE MODELO YOLO - ALPR UNIPIAGET")
    print("=" * 60)

    # Carrega modelo
    model = carregar_modelo()
    if model is None:
        sys.exit(1)

    # Modo webcam
    if "--webcam" in sys.argv:
        usar_gui = "--no-gui" not in sys.argv
        num_frames = None
        for arg in sys.argv:
            if arg.startswith("--frames="):
                num_frames = int(arg.split("=")[1])
        testar_com_webcam(model, usar_gui=usar_gui, num_frames=num_frames)
        sys.exit(0)

    # Imagem específica via argumento
    image_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if image_args:
        for img_path in image_args:
            testar_com_imagem(model, img_path)
        sys.exit(0)

    # Procura imagens de teste
    test_dirs = [
        ROOT_DIR / "storage" / "test_images",
        ROOT_DIR / "storage" / "images",
        ROOT_DIR / "test_images",
    ]

    test_images = []
    for test_dir in test_dirs:
        if test_dir.exists():
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.bmp"]:
                test_images.extend(test_dir.glob(ext))

    if test_images:
        print(f"\n  Encontradas {len(test_images)} imagens de teste")
        for img_path in test_images[:5]:  # Testa até 5 imagens
            testar_com_imagem(model, img_path)
    else:
        print("\n  [INFO] Nenhuma imagem de teste encontrada")
        print()
        print("  Uso:")
        print("    python testar_modelo.py imagem.jpg              # Testar com imagem")
        print("    python testar_modelo.py --webcam                # Testar com webcam (GUI)")
        print("    python testar_modelo.py --webcam --no-gui       # Testar sem GUI (salva frames)")
        print("    python testar_modelo.py --webcam --no-gui --frames=20  # Capturar 20 frames")
        print()
        print("  Ou coloque imagens em: storage/test_images/")

    print()
