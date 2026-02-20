# 🚗 Sistema ALPR UNIPIAGET

### Projeto de Conclusão de Curso

Tema: **Sistema de Reconhecimento Automático de Placas Veiculares**

Universidade Jean Piaget de Moçambique
Curso: Engenharia Electrónica e de Telecomunicações
Ano: 2026

Estudante: **Salvador Eduardo Tomoecene**


---

## 📋 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Características](#-características)
- [Arquitetura](#%EF%B8%8F-arquitetura)
- [Tecnologias](#%EF%B8%8F-tecnologias)
- [Instalação](#-instalação)
- [Configuração](#%EF%B8%8F-configuração)
- [Uso](#-uso)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [API Endpoints](#-api-endpoints)
- [Formato de Placas](#-formato-de-placas-moçambicanas)
- [Testes](#-testes)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 Sobre o Projeto

O Sistema ALPR (Automatic License Plate Recognition) é uma solução completa para controle de acesso veicular no campus da UNIPIAGET. O sistema detecta automaticamente placas de veículos, registra entradas e saídas, e gera relatórios de permanência.

### Objetivos

- ✅ Monitorar presença real de docentes no campus
- ✅ Automatizar controle de acesso veicular
- ✅ Evitar fraude em assinatura de presença
- ✅ Gerar relatórios gerenciais

### Problema

Docentes assinam presença, saem com seus carros para fazer outras atividades, e voltam. Isso prejudica o aproveitamento dos estudantes e a qualidade do ensino.

### Solução

Sistema híbrido (Desktop + Web) que detecta, reconhece, registra e gera relatórios automáticos de permanência.

---

## ✨ Características

### Detecção
- ✅ Detecção em tempo real via webcam/vídeo
- ✅ Modelo YOLO v8 treinado especificamente para placas moçambicanas
- ✅ Detecção directa de placas (modo optimizado)
- ✅ Processamento CPU/GPU
- ✅ Suporte a múltiplas fontes (webcam, arquivo, IP camera)

### Reconhecimento (OCR)
- ✅ OCR duplo: EasyOCR + Tesseract (modo híbrido)
- ✅ **Correção automática inteligente** de erros comuns:
  - 0 ↔ O, 1 ↔ I/L, 5 ↔ S, 8 ↔ B, 6 ↔ G, 2 ↔ Z, 7 ↔ T
- ✅ Validação rigorosa do formato XXX000XX
- ✅ Confiança ajustável
- ✅ Pré-processamento avançado de imagens

### Gestão Web
- ✅ API REST completa (FastAPI)
- ✅ Dashboard moderno (TailwindCSS v4)
- ✅ Dark mode com tema burgundy
- ✅ CRUD completo de veículos e proprietários
- ✅ Histórico de acessos com filtros
- ✅ Estatísticas em tempo real
- ✅ Relatórios exportáveis
- ✅ Autenticação JWT com níveis de acesso

### Desktop Module
- ✅ Interface gráfica Tkinter
- ✅ Visualização em tempo real
- ✅ Controles de entrada/saída
- ✅ Sistema de logs
- ✅ Configurações via .env
- ✅ Salvamento automático de imagens

---

## 🏗️ Arquitetura

```
┌─────────────────────┐         ┌─────────────────────┐
│  DESKTOP MODULE     │         │    WEB MODULE       │
│  (Detecção)         │  HTTP   │    (Gerenciamento)  │
│                     │◄───────►│                     │
│  • Câmera/Vídeo     │         │  • API REST         │
│  • YOLO v8          │         │  • Dashboard        │
│  • EasyOCR          │         │  • Relatórios       │
│  • Tesseract        │         │  • Autenticação     │
│  • Interface Tkinter│         │  • FastAPI          │
└─────────────────────┘         └─────────────────────┘
                                         │
                                         ▼
                                ┌─────────────────┐
                                │  SQLite ou      │
                                │  PostgreSQL     │
                                └─────────────────┘
```

### Fluxo de Detecção

```
1. Câmera captura frame
2. YOLO v8 detecta região da placa
3. Pré-processamento da imagem
4. OCR duplo (EasyOCR + Tesseract)
5. Correção inteligente baseada no formato XXX000XX
6. Validação formato moçambicano
7. Envia para API via HTTP POST
8. API verifica duplicata temporal (cooldown)
9. Busca veículo no banco de dados
10. Registra acesso (entrada/saída)
11. Retorna status ao Desktop Module
```

---

## 🛠️ Tecnologias

### Backend (Web Module)
- **FastAPI 0.128.5** - Framework web moderno
- **SQLAlchemy 2.0.46** - ORM para banco de dados
- **Pydantic 2.12.5** - Validação de dados
- **Python-Jose 3.5.0** - JWT para autenticação
- **Uvicorn 0.40.0** - Servidor ASGI
- **Bcrypt 5.0.0** - Hash de senhas

### Frontend (Web Module)
- **TailwindCSS v4** - Framework CSS utility-first
- **Jinja2 3.1.6** - Templates
- **Bootstrap Icons 1.11.3** - Ícones
- **JavaScript Vanilla** - Interatividade

### Computer Vision (Desktop Module)
- **Ultralytics YOLOv8 8.4.13** - Detecção de placas
- **OpenCV 4.13.0** - Processamento de imagens
- **EasyOCR 1.7.2** - OCR com deep learning
- **Tesseract OCR 0.3.13** - OCR tradicional
- **PyTorch 2.10.0+cpu** - Framework deep learning
- **torchvision 0.25.0+cpu** - Visão computacional

### Interface Desktop
- **Tkinter** - Interface gráfica nativa
- **Pillow 12.1.0** - Manipulação de imagens

### Outras
- **Requests 2.32.5** - Cliente HTTP
- **python-dotenv 1.2.1** - Variáveis de ambiente
- **Loguru 0.7.3** - Sistema de logs

---

## 📦 Instalação

### Pré-requisitos

- **Python 3.8+** (recomendado: **3.13**)
- **Tesseract OCR** instalado no sistema
- **Webcam** ou arquivo de vídeo para testes
- **4GB RAM** mínimo (8GB recomendado)
- **(Opcional) GPU NVIDIA com CUDA** para melhor performance

### Passo 1: Clonar Repositório

```bash
git clone https://github.com/seu-usuario/alpr_ujpm.git
cd alpr_ujpm
```

### Passo 2: Criar Ambiente Virtual

```bash
python -m venv venv
```

**Ativar:**
- Windows (CMD): `venv\Scripts\activate`
- Windows (PowerShell): `venv\Scripts\Activate.ps1`
- Linux/Mac: `source venv/bin/activate`

### Passo 3: Instalar Dependências

```bash
pip install -r requirements.txt
```

> ⏱️ Tempo estimado: 5-10 minutos (depende da conexão)

### Passo 4: Instalar Tesseract OCR

#### Windows
1. Baixe: https://github.com/UB-Mannheim/tesseract/wiki
2. Instale em `C:\Program Files\Tesseract-OCR\`
3. O caminho será configurado automaticamente no `.env`

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

#### macOS
```bash
brew install tesseract
```

### Passo 5: Modelo YOLO

O modelo treinado já deve estar em:
```
desktop_module/models/license_plate_detector.pt
```

Se não estiver, verifique a pasta `docs/` para instruções de download.

---

## ⚙️ Configuração

### 1. Arquivo de Configuração

O arquivo `.env` já está configurado. Principais configurações:

```env
# YOLO
YOLO_MODEL_PATH=desktop_module/models/license_plate_detector.pt
YOLO_CONFIDENCE=0.5              # 0.3 a 0.7 (quanto maior, mais rigoroso)
YOLO_DEVICE=cpu                  # ou 'cuda' para GPU

# OCR
OCR_METHOD=hibrido               # easyocr, tesseract, ou hibrido
OCR_MIN_CONFIDENCE=0.3           # 0.0 a 1.0
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# API
API_HOST=http://localhost:8000
API_TIMEOUT=30

# Banco de Dados
DATABASE_URL=sqlite:///./alpr_unipiaget.db

# Segurança
SECRET_KEY=sua-chave-secreta-super-segura-mude-em-producao-12345
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Vídeo/Câmera
VIDEO_SOURCE=0                   # 0=webcam, 1=segunda webcam, ou caminho
PROCESS_EVERY_N_FRAMES=5         # Processa 1 a cada N frames
FRAME_RESIZE_WIDTH=640
FRAME_RESIZE_HEIGHT=480

# Debug
ALPR_DEBUG_MODE=true             # true=aceita qualquer texto, false=validação rigorosa
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
```

### 2. Inicializar Banco de Dados

```bash
python init_database.py
```

Isso cria:
- ✅ Tabelas do banco de dados
- ✅ Usuário admin (`admin` / `admin123`)
- ✅ Estrutura inicial

---

## 🚀 Uso

### Iniciar Web Module (API + Dashboard)

**Terminal 1:**
```bash
# Ativar ambiente virtual
venv\Scripts\activate

# Iniciar servidor
uvicorn web_module.main:app --reload --port 8000
```

Acesse:
- **Dashboard**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Login**: `admin` / `admin123`

### Iniciar Desktop Module (Detecção)

**Terminal 2:**
```bash
# Ativar ambiente virtual
venv\Scripts\activate

# Iniciar aplicação desktop
python desktop_module/main.py
```

### Workflow Recomendado

1. **Cadastrar Proprietários** via Dashboard Web
2. **Cadastrar Veículos** com placas no formato XXX000XX
3. **Iniciar Desktop Module** e começar detecção
4. **Apontar placa para câmera**
5. **Verificar registros** no Dashboard Web

---

## 📁 Estrutura do Projeto

```
alpr_ujpm/
├── desktop_module/              # Aplicação Desktop
│   ├── main.py                 # Ponto de entrada
│   ├── core/
│   │   ├── detector.py         # YOLO + OCR (521 linhas)
│   │   ├── api_client.py       # Cliente HTTP (214 linhas)
│   │   └── camera.py           # Gerenciador câmera (210 linhas)
│   ├── ui/
│   │   └── main_window.py      # Interface Tkinter (520 linhas)
│   ├── config/
│   │   └── settings.py         # Configurações
│   └── models/
│       └── license_plate_detector.pt  # Modelo YOLO (5.2 MB)
│
├── web_module/                  # API e Dashboard Web
│   ├── main.py                 # FastAPI app
│   ├── routes/                 # Endpoints da API
│   │   ├── auth.py
│   │   ├── veiculos.py
│   │   ├── proprietarios.py
│   │   ├── registros.py
│   │   ├── dashboard.py
│   │   └── relatorios.py
│   ├── templates/              # Templates Jinja2
│   │   ├── base.html           # Template base
│   │   ├── login.html          # Login moderno
│   │   ├── dashboard.html      # Dashboard
│   │   ├── veiculos.html       # Gestão veículos
│   │   └── proprietarios.html  # Gestão proprietários
│   └── services/               # Lógica de negócio
│       ├── auth_service.py
│       └── deteccao_service.py
│
├── shared/                      # Código compartilhado
│   ├── utils.py                # Validação XXX000XX + correção OCR
│   └── schemas.py              # Modelos Pydantic
│
├── storage/                     # Armazenamento
│   ├── images/                 # Imagens de detecções
│   ├── debug/                  # Imagens de debug
│   └── test_images/            # Imagens de teste
│
├── tests/                       # Scripts de teste
│   ├── verificar_modelo.py     # Verifica modelo YOLO
│   ├── testar_modelo.py        # Testa detecção
│   └── testar_correcao_ocr_simples.py  # Testa correção OCR
│
├── docs/                        # Documentação
│   ├── SISTEMA_COMPLETO.md     # Documentação completa
│   ├── INSTALACAO_MODELO_YOLO.md
│   └── INSTALACAO_TESSERACT.md
│
├── scripts_antigos/             # Scripts auxiliares antigos
│
├── venv/                        # Ambiente virtual (119 dependências)
│
├── .env                         # Configurações (NÃO commitar!)
├── .gitignore                   # Arquivos ignorados
├── requirements.txt             # Dependências Python
├── init_database.py             # Inicializa banco
└── README.md                    # Este arquivo
```

---

## 🔌 API Endpoints

### Autenticação
```
POST   /api/v1/auth/login       # Login (retorna JWT)
GET    /api/v1/auth/me          # Dados do usuário atual
```

### Veículos
```
GET    /api/v1/veiculos                  # Listar veículos
POST   /api/v1/veiculos                  # Criar veículo
GET    /api/v1/veiculos/{id}             # Obter veículo
GET    /api/v1/veiculos/placa/{placa}    # Buscar por placa
PUT    /api/v1/veiculos/{id}             # Atualizar veículo
DELETE /api/v1/veiculos/{id}             # Deletar veículo
GET    /api/v1/veiculos/count/total      # Contar veículos
```

### Proprietários
```
GET    /api/v1/proprietarios             # Listar proprietários
POST   /api/v1/proprietarios             # Criar proprietário
GET    /api/v1/proprietarios/{id}        # Obter proprietário
PUT    /api/v1/proprietarios/{id}        # Atualizar proprietário
DELETE /api/v1/proprietarios/{id}        # Deletar proprietário
GET    /api/v1/proprietarios/count/total # Contar proprietários
```

### Registros de Acesso
```
GET    /api/v1/registros                 # Listar registros
POST   /api/v1/registros/deteccao        # Registrar detecção (Desktop)
GET    /api/v1/registros/{id}            # Obter registro
GET    /api/v1/registros/hoje            # Registros de hoje
GET    /api/v1/registros/count/hoje      # Contagem de hoje
```

### Dashboard
```
GET    /api/v1/dashboard/estatisticas         # Estatísticas gerais
GET    /api/v1/dashboard/veiculos-no-campus   # Veículos no campus
GET    /api/v1/dashboard/atividade-recente    # Últimas detecções
```

**Documentação interativa:** http://localhost:8000/docs

---

## 🚦 Formato de Placas Moçambicanas

### Formato Válido: `XXX000XX`

- **XXX**: 3 letras (província/categoria)
- **000**: 3 números (série)
- **XX**: 2 letras (final)

### Exemplos Válidos
```
MPM123AB  ✅  (Maputo)
AAA456CD  ✅  (Série AAA)
LMX789BC  ✅  (Série LMX)
GAZ012EF  ✅  (Gaza)
INB345GH  ✅  (Inhambane)
```

### Exemplos Inválidos
```
MP1234AB  ❌  (Apenas 2 letras iniciais)
MPM12AB   ❌  (Apenas 2 números)
MPM123A   ❌  (Apenas 1 letra final)
MPM123ABC ❌  (3 letras finais)
```

### Correção Automática de OCR

O sistema corrige automaticamente confusões comuns baseadas na posição:

| Confusão | Posição | Correção |
|----------|---------|----------|
| 0 ↔ O | 0-2, 6-7 | 0 → O |
| 0 ↔ O | 3-5 | O → 0 |
| 1 ↔ I/L | 0-2, 6-7 | 1 → I |
| 1 ↔ I/L | 3-5 | I/L → 1 |
| 5 ↔ S | 0-2, 6-7 | 5 → S |
| 5 ↔ S | 3-5 | S → 5 |
| 8 ↔ B | 0-2, 6-7 | 8 → B |
| 8 ↔ B | 3-5 | B → 8 |
| 6 ↔ G | Todas | Inteligente |
| 2 ↔ Z | Todas | Inteligente |
| 7 ↔ T | Todas | Inteligente |

**Exemplo:**
```
OCR Lê:      MPM1O3AB  (O em vez de 0)
Sistema Corrige: MPM103AB  (O→0 na posição numérica)
```

---

## 🧪 Testes

### Verificar Modelo YOLO
```bash
python tests/verificar_modelo.py
```

Saída esperada:
```
✓ Modelo carregado com sucesso!
  Classes detectadas: 1
  Nomes das classes: {0: 'licenses'}
  [INFO] Tipo: MODELO DE PLACAS
```

### Testar Detecção com Webcam
```bash
# Com GUI (se disponível)
python tests/testar_modelo.py --webcam

# Sem GUI (salva frames em arquivo)
python tests/testar_modelo.py --webcam --no-gui --frames=5
```

### Testar Correção OCR
```bash
python tests/testar_correcao_ocr_simples.py
```

Saída esperada:
```
Resultados: 7 sucessos, 0 falhas
```

### Testar com Imagem
```bash
python tests/testar_modelo.py storage/test_images/carro1.jpg
```

---

## 🐛 Troubleshooting

### Desktop Module não abre

**Problema:** Erro ao importar cv2, ultralytics, etc.

**Solução:**
```bash
# Verifique se está no ambiente virtual
venv\Scripts\activate

# Reinstale dependências
pip install -r requirements.txt
```

### Webcam não funciona

**Problema:** Câmera não abre ou tela preta

**Soluções:**
```env
# Tente outro índice no .env
VIDEO_SOURCE=1  # ou 2, 3...

# Ou use vídeo de arquivo
VIDEO_SOURCE=caminho/para/video.mp4
```

### YOLO não detecta placas

**Problema:** Bounding box não aparece

**Soluções:**
```env
# Reduza confiança no .env
YOLO_CONFIDENCE=0.25  # ou até 0.2

# Verifique se modelo existe
ls desktop_module/models/license_plate_detector.pt
```

### OCR retorna texto errado

**Problema:** Placa não é reconhecida corretamente

**Soluções:**
```env
# Use modo debug temporariamente
ALPR_DEBUG_MODE=true

# Ajuste confiança mínima
OCR_MIN_CONFIDENCE=0.2

# Use método híbrido
OCR_METHOD=hibrido
```

### Desktop não conecta à API

**Problema:** Detecção não aparece no dashboard

**Soluções:**
```bash
# Verifique se web module está rodando
curl http://localhost:8000/health

# Verifique configuração
grep API_HOST .env

# Deve ser: API_HOST=http://localhost:8000
```

### Erro: "Tesseract not found"

**Solução:**
```env
# Configure caminho correto no .env
# Windows:
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Linux/Mac:
TESSERACT_CMD=tesseract
```

---

## 📄 Licença

Este projeto é desenvolvido como trabalho académico para a Universidade Jean Piaget de Moçambique.

---

## 👥 Autores

**Sistema ALPR UNIPIAGET**
Engenharia Electrónica e de Telecomunicações
Universidade Jean Piaget de Moçambique
2026

---

## 🙏 Agradecimentos

- Universidade Jean Piaget de Moçambique
- Docentes orientadores
- Comunidade open source (Ultralytics, FastAPI, OpenCV, EasyOCR, Tesseract)

---

## 📞 Suporte

Para questões e sugestões:
- **Issues**: https://github.com/seu-usuario/alpr_ujpm/issues
- **Email**: suporte@unipiaget.ac.mz

---

**⭐ Sistema ALPR UNIPIAGET - Reconhecimento Automático de Placas para Moçambique 🇲🇿**
