# Instalação de Modelo YOLO para Placas

## Problema Atual

O modelo **YOLOv8n** genérico detecta:
- ✅ Carros, motos, caminhões
- ❌ **NÃO** detecta placas de veículos

**Solução**: Usar modelo YOLO treinado especificamente para placas.

---

## Opção 1: Modelo do Roboflow Universe (RECOMENDADO)

### Passo 1: Criar Conta no Roboflow

1. Acesse: https://roboflow.com/
2. Crie uma conta gratuita
3. Acesse: https://universe.roboflow.com/

### Passo 2: Procurar Modelo de Placas

1. Na busca, digite: **"license plate detector"**
2. Escolha um dos modelos populares:
   - **"license-plate-detector"** (mais usado)
   - **"vehicle-registration-plates"**
   - **"car-license-plate-detection"**

### Passo 3: Baixar Modelo

1. Clique no modelo escolhido
2. Clique em **"Download Dataset"**
3. Selecione formato: **"YOLOv8"**
4. Clique em **"Show Download Code"**
5. Copie o código Python

**Exemplo do código:**

```python
from roboflow import Roboflow
rf = Roboflow(api_key="SUA_API_KEY_AQUI")
project = rf.workspace().project("license-plate-detector")
dataset = project.version(1).download("yolov8")
```

### Passo 4: Instalar Roboflow e Baixar

No terminal do projeto:

```bash
pip install roboflow
```

Crie um arquivo `baixar_modelo_roboflow.py`:

```python
from roboflow import Roboflow
import shutil
from pathlib import Path

# Substitua pela sua API key do Roboflow
rf = Roboflow(api_key="SUA_API_KEY_AQUI")

# Baixa o dataset
project = rf.workspace().project("license-plate-detector")
dataset = project.version(1).download("yolov8")

print(f"Dataset baixado em: {dataset.location}")
print("\nProcurando arquivo .pt do modelo...")

# Procura o arquivo .pt
dataset_path = Path(dataset.location)
pt_files = list(dataset_path.rglob("*.pt"))

if pt_files:
    model_file = pt_files[0]
    print(f"Modelo encontrado: {model_file}")

    # Copia para pasta de modelos
    dest = Path("desktop_module/models/license_plate_detector.pt")
    shutil.copy(model_file, dest)
    print(f"\nModelo copiado para: {dest}")
    print("\nAtualize o .env:")
    print("YOLO_MODEL_PATH=desktop_module/models/license_plate_detector.pt")
else:
    print("Nenhum arquivo .pt encontrado. Você precisará treinar o modelo.")
```

Execute:

```bash
python baixar_modelo_roboflow.py
```

### Passo 5: Configurar no Sistema

Edite o `.env`:

```env
YOLO_MODEL_PATH=desktop_module/models/license_plate_detector.pt
```

---

## Opção 2: Modelo Pré-treinado do GitHub

Alguns modelos disponíveis:

1. **Ultralytics YOLOv8 License Plate**
   ```bash
   # Baixa modelo pré-treinado
   wget https://github.com/username/yolo-license-plate/releases/download/v1.0/best.pt
   mv best.pt desktop_module/models/license_plate.pt
   ```

2. **Procure no GitHub**: "yolov8 license plate detection"

---

## Opção 3: Treinar Modelo Customizado (AVANÇADO)

Para placas **moçambicanas** específicas:

### Passo 1: Coletar Dataset

- Mínimo: 500 imagens de veículos com placas moçambicanas
- Recomendado: 1000-2000 imagens
- Variações: dia/noite, diferentes ângulos, clima

### Passo 2: Anotar Imagens

Use Roboflow ou LabelImg:

1. Upload imagens no Roboflow
2. Desenhe caixas ao redor das placas
3. Label: "license_plate"
4. Export em formato YOLOv8

### Passo 3: Treinar Modelo

```python
from ultralytics import YOLO

# Carrega modelo base
model = YOLO('yolov8n.pt')

# Treina com seu dataset
results = model.train(
    data='path/to/data.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    name='mozambique_plates'
)

# Salva melhor modelo
# Será salvo em: runs/detect/mozambique_plates/weights/best.pt
```

Copie o modelo treinado:

```bash
cp runs/detect/mozambique_plates/weights/best.pt desktop_module/models/mozambique_plates.pt
```

---

## Testar Novo Modelo

Depois de configurar o modelo:

```bash
# 1. Teste básico
python teste_desktop_basic.py

# 2. Processe imagens
python processar_testes.py --tipo imagem

# 3. Verifique detecções
python diagnostico_yolo.py
```

---

## Comparação de Opções

| Opção | Dificuldade | Precisão | Custo | Tempo |
|-------|-------------|----------|-------|-------|
| Roboflow | Fácil | Boa | Gratuito* | 10 min |
| GitHub | Média | Variável | Gratuito | 5 min |
| Treinar Custom | Difícil | Excelente | Tempo | Dias/Semanas |

*Roboflow tem limite gratuito

---

## Recomendação

**Para começar agora**:
1. Use modelo do Roboflow Universe
2. Escolha "license-plate-detector" popular
3. Baixe e configure conforme Passo 3-5

**Para produção (futuro)**:
1. Colete dataset de placas moçambicanas
2. Treine modelo customizado
3. Vai ter melhor precisão com placas locais

---

## Próximos Passos

Após instalar o modelo:

1. ✅ Tesseract instalado
2. ✅ Modelo YOLO de placas instalado
3. ⬜ Testar sistema completo
4. ⬜ Desativar modo debug
5. ⬜ Configurar validação para formato moçambicano
