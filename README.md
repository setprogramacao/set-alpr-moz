# Sistema ALPR UNIPIAGET

**Reconhecimento Automático de Placas Veiculares com Controlo de Cancela via PLC**

Universidade Jean Piaget de Moçambique — Engenharia Electrónica e de Telecomunicações

Estudante: **Salvador Eduardo Tomoecene** · Ano: **2026**

---

## Índice

- [Sobre o Projeto](#sobre-o-projeto)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Fluxo de Detecção](#fluxo-de-detecção)
- [Base de Dados](#base-de-dados)
- [Integração PLC / Cancela](#integração-plc--cancela)
- [Tecnologias](#tecnologias)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [API Endpoints](#api-endpoints)
- [Formato de Placas](#formato-de-placas-moçambicanas)
- [Troubleshooting](#troubleshooting)

---

## Sobre o Projeto

O Sistema ALPR é uma solução completa para controlo de acesso veicular no campus da UNIPIAGET.
Detecta automaticamente placas de veículos via câmara, regista entradas e saídas, aciona a cancela
eletrônica via PLC (Modbus TCP) e disponibiliza um dashboard web com relatórios.

### Problema

Docentes podiam assinar presença e abandonar o campus antes de cumprir a carga horária.
Não existia correlação automática entre a presença física (veículo no campus) e o registo de presença.

### Solução

Sistema híbrido (Desktop + Web + PLC) que detecta, reconhece e regista automaticamente
a passagem de veículos, controlando a cancela eletrônica e gerando relatórios de permanência.

---

## Arquitetura do Sistema

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         SISTEMA ALPR UNIPIAGET                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

  ┌─────────────────────────────────┐          ┌──────────────────────────────┐
  │        MÓDULO DESKTOP           │          │        MÓDULO WEB            │
  │        Python · Tkinter         │          │      Python · FastAPI        │
  │                                 │          │                              │
  │  ┌──────────┐  ┌─────────────┐  │          │  ┌────────────────────────┐  │
  │  │  Câmara  │  │   YOLO v8   │  │          │  │    REST API (50+       │  │
  │  │  OpenCV  ├─►│  Detecção   │  │          │  │    endpoints)          │  │
  │  └──────────┘  └──────┬──────┘  │          │  │  /auth /veiculos       │  │
  │                        │         │          │  │  /proprietarios        │  │
  │               ┌────────▼──────┐  │  HTTP    │  │  /registros            │  │
  │               │  OCR Duplo    │  │◄────────►│  │  /dashboard            │  │
  │               │  EasyOCR +    ├──┼─ POST ──►│  │  /relatorios           │  │
  │               │  Tesseract    │  │ /deteccao│  └──────────┬─────────────┘  │
  │               └──────┬────────┘  │          │             │                │
  │                       │          │          │  ┌──────────▼─────────────┐  │
  │               ┌───────▼───────┐  │          │  │    SQLAlchemy ORM      │  │
  │               │  Correção OCR │  │          │  │    Deteccao Service    │  │
  │               │  0↔O 1↔I 5↔S │  │          │  │    Auth Service        │  │
  │               └──────┬────────┘  │          │  └──────────┬─────────────┘  │
  │                       │          │          │             │                │
  │               ┌───────▼───────┐  │          │  ┌──────────▼─────────────┐  │
  │               │  API Client   │  │          │  │  Templates Jinja2      │  │
  │               │  (HTTP)       │  │          │  │  Tailwind CSS v4       │  │
  │               └──────┬────────┘  │          │  │  Vanilla JS            │  │
  │                       │          │          │  └────────────────────────┘  │
  │               ┌───────▼───────┐  │          └──────────────┬───────────────┘
  │               │ PLC Controller│  │                          │ SQL
  │               │ Modbus TCP    │  │          ┌──────────────▼───────────────┐
  │               └──────┬────────┘  │          │         BASE DE DADOS        │
  └──────────────────────┼───────────┘          │    SQLite (dev)              │
                         │                       │    PostgreSQL (prod)         │
                         │ Modbus TCP             │                              │
                         │ porta 5020             │    proprietarios             │
  ┌──────────────────────▼────────────┐          │    veiculos                  │
  │         PLC / CANCELA             │          │    registros_acesso          │
  │                                   │          │    usuarios                  │
  │  [Coil 0]  Cancela ─────────────► │ Abre /   └──────────────────────────────┘
  │                          Fecha    │
  │  [DI 0]    Sensor Laço ◄───────── │ Veículo                    Browser
  │                          Presente │                               │
  └───────────────────────────────────┘          ┌──────────────────▼──────────┐
                                                 │     Dashboard Web            │
                                                 │   http://localhost:8000      │
                                                 └──────────────────────────────┘
```

### Descrição dos Módulos

| Módulo | Tecnologia | Função |
|--------|-----------|--------|
| Desktop | Python · Tkinter · OpenCV | Captura vídeo, detecta e reconhece placas |
| Web API | FastAPI · SQLAlchemy · JWT | Armazena registros, autentica, serve dashboard |
| PLC | Modbus TCP · pymodbus | Controla abertura/fecho da cancela |
| Base de Dados | SQLite / PostgreSQL | Persiste proprietários, veículos, acessos |

---

## Fluxo de Detecção

### Diagrama Completo

```
  CÂMARA             MÓDULO DESKTOP                   API                 PLC
     │                      │                           │                    │
     │──── Frame ───────────►                           │                    │
     │                      │                           │                    │
     │               ┌──────▼──────┐                    │                    │
     │               │  YOLO v8    │                    │                    │
     │               │  Localiza   │                    │                    │
     │               │  BBox placa │                    │                    │
     │               └──────┬──────┘                    │                    │
     │                      │                           │                    │
     │               ┌──────▼──────┐                    │                    │
     │               │  Recorta    │                    │                    │
     │               │  + CLAHE    │                    │                    │
     │               │  + Margem   │                    │                    │
     │               └──────┬──────┘                    │                    │
     │                      │                           │                    │
     │               ┌──────▼──────┐                    │                    │
     │               │  EasyOCR   │                    │                    │
     │               │     +       │                    │                    │
     │               │  Tesseract │                    │                    │
     │               └──────┬──────┘                    │                    │
     │                      │                           │                    │
     │               ┌──────▼──────┐                    │                    │
     │               │  Correção   │                    │                    │
     │               │  Inteligente│                    │                    │
     │               │  0↔O,1↔I.. │                    │                    │
     │               └──────┬──────┘                    │                    │
     │                      │                           │                    │
     │               ┌──────▼──────┐                    │                    │
     │               │  Validação  │                    │                    │
     │               │  XXX000XX   │                    │                    │
     │               └──────┬──────┘                    │                    │
     │                      │                           │                    │
     │                      │─── POST /registros ──────►│                    │
     │                      │       /deteccao           │                    │
     │                      │                    ┌──────▼──────┐             │
     │                      │                    │  Verifica    │             │
     │                      │                    │  Duplicata   │             │
     │                      │                    │  (cooldown)  │             │
     │                      │                    └──────┬───────┘             │
     │                      │                    ┌──────▼──────┐             │
     │                      │                    │  Toggle      │             │
     │                      │                    │  Entrada/    │             │
     │                      │                    │  Saída       │             │
     │                      │                    └──────┬───────┘             │
     │                      │                    ┌──────▼──────┐             │
     │                      │                    │  Salva na   │             │
     │                      │                    │  Base de    │             │
     │                      │                    │  Dados      │             │
     │                      │                    └──────┬───────┘             │
     │                      │◄─── Resposta ─────────────│                    │
     │                      │   {cadastrado, tipo,      │                    │
     │                      │    mensagem, duplicata}   │                    │
     │                      │                           │                    │
     │               ┌──────▼──────────────────────┐    │                    │
     │               │  SE OCR leu placa            │    │                    │
     │               │    (cadastrada ou não):      │    │                    │
     │               └──────┬──────────────────────-┘    │                    │
     │                      │── Write Coil 0 = True ─────────────────────────►│
     │                      │                           │   ┌─────────────┐   │
     │                      │                           │   │ Cancela     │   │
     │                      │                           │   │ ABRE ↑      │   │
     │                      │                           │   └─────────────┘   │
     │                      │                           │                    │
     │                      │                           │◄── DI 0 = True ────│
     │                      │                           │  (veículo no laço) │
     │                      │                           │                    │
     │                      │                           │◄── DI 0 = False ───│
     │                      │                           │  (veículo passou)  │
     │                      │── Write Coil 0 = False ──────────────────────► │
     │                      │                           │   ┌─────────────┐   │
     │                      │                           │   │ Cancela     │   │
     │                      │                           │   │ FECHA ↓     │   │
     │                      │                           │   └─────────────┘   │
```

### Lógica de Toggle Entrada/Saída

```
  Detecção da placa AHK641MP
         │
         ▼
  ┌─────────────────────────┐
  │  Consulta último        │
  │  registo desta placa    │
  │  na Base de Dados       │
  └─────────┬───────────────┘
            │
   ┌─────── ▼ ───────┐
   │ Existe registo? │
   └─────── ┬ ───────┘
            │
      Não ──┼── Sim
      │     │    │
      │     │    ▼
      │     │  ┌─────────────────┐
      │     │  │ Qual foi o      │
      │     │  │ último tipo?    │
      │     │  └────────┬────────┘
      │     │           │
      │     │    entrada─┼─saida
      │     │           │    │
      ▼     │           ▼    ▼
  ENTRADA   │       SAÍDA  ENTRADA
      │     │           │    │
      └─────┴───────────┴────┘
                    │
              Regista na BD
              com tipo determinado
```

### Seleção do Resultado OCR

```
         Imagem recortada da placa
                    │
          ┌─────────┴──────────┐
          │                    │
          ▼                    ▼
    ┌───────────┐        ┌───────────┐
    │  EasyOCR  │        │ Tesseract │
    │ (deep     │        │ (clássico)│
    │ learning) │        │ PSM 7/8/6 │
    └─────┬─────┘        └─────┬─────┘
          │                    │
          └─────────┬──────────┘
                    │
           ┌────────▼────────┐
           │  Concordam?     │
           │ (mesmo texto)   │
           └────────┬────────┘
                    │
           Sim ─────┴───── Não
            │                │
            ▼                ▼
      Confiança alta    Valida formato
      usa resultado     moçambicano XXX000XX
                        escolhe o melhor
                            │
                            ▼
                   corrigir_placa_ocr()
                   (correção por posição)
                            │
                            ▼
                    Placa final validada
```

---

## Base de Dados

### Diagrama Entidade-Relacionamento

```
┌───────────────────────────────┐          ┌───────────────────────────────────┐
│          PROPRIETARIOS        │          │              VEICULOS             │
├───────────────────────────────┤          ├───────────────────────────────────┤
│ PK  id           INTEGER      │◄──1───N──│ FK  proprietario_id  INTEGER      │
│     nome         VARCHAR      │          │ PK  id               INTEGER      │
│     categoria    ENUM         │          │     placa            VARCHAR(8)   │
│     departamento VARCHAR?     │          │     modelo           VARCHAR?     │
│     telefone     VARCHAR?     │          │     marca            VARCHAR?     │
│     email        VARCHAR?     │          │     cor              VARCHAR?     │
│     ativo        BOOLEAN      │          │     ano              INTEGER?     │
│     criado_em    DATETIME     │          │     ativo            BOOLEAN      │
└───────────────────────────────┘          └──────────────┬────────────────────┘
                                                          │
         categoria:                              1        │
         docente | tecnico                               │
         aluno | visitante                              N │
                                           ┌─────────────▼──────────────────────┐
                                           │          REGISTROS_ACESSO          │
                                           ├────────────────────────────────────┤
                                           │ PK  id               INTEGER       │
                                           │ FK  veiculo_id       INTEGER?      │
                                           │     placa_detectada  VARCHAR       │
                                           │     tipo_movimento   ENUM          │
                                           │     data_hora        DATETIME      │
                                           │     confianca_ocr    FLOAT         │
                                           │     metodo_ocr       VARCHAR       │
                                           │     imagem_path      VARCHAR?      │
                                           └────────────────────────────────────┘
                                                veiculo_id nullable:
                                                aceita placas não cadastradas

┌───────────────────────────────┐
│            USUARIOS           │
├───────────────────────────────┤
│ PK  id           INTEGER      │
│     username     VARCHAR      │   nivel_acesso:
│     senha_hash   VARCHAR      │   admin | operador | visualizador
│     nivel_acesso ENUM         │
│     ativo        BOOLEAN      │
│     criado_em    DATETIME     │
└───────────────────────────────┘
  (independente — sem FK para as outras tabelas)
```

### Tabelas Detalhadas

#### `proprietarios`

| Coluna | Tipo | Restrição | Descrição |
|--------|------|-----------|-----------|
| id | INTEGER | PK, Auto | Identificador único |
| nome | VARCHAR | NOT NULL | Nome completo |
| categoria | ENUM | NOT NULL | `docente` / `tecnico` / `aluno` / `visitante` |
| departamento | VARCHAR | NULL | Faculdade ou departamento |
| telefone | VARCHAR | NULL | Formato `+258XXXXXXXXX` |
| email | VARCHAR | NULL | Endereço de e-mail |
| ativo | BOOLEAN | DEFAULT True | Registo ativo |
| criado_em | DATETIME | DEFAULT now() | Data de criação |

#### `veiculos`

| Coluna | Tipo | Restrição | Descrição |
|--------|------|-----------|-----------|
| id | INTEGER | PK, Auto | Identificador único |
| proprietario_id | INTEGER | FK, NOT NULL | Referência ao proprietário |
| placa | VARCHAR(8) | UNIQUE, NOT NULL | Formato `XXX000XX` |
| modelo | VARCHAR | NULL | Modelo do veículo |
| marca | VARCHAR | NULL | Marca (Toyota, etc.) |
| cor | VARCHAR | NULL | Cor do veículo |
| ano | INTEGER | NULL | Ano de fabrico |
| ativo | BOOLEAN | DEFAULT True | Registo ativo |

#### `registros_acesso`

| Coluna | Tipo | Restrição | Descrição |
|--------|------|-----------|-----------|
| id | INTEGER | PK, Auto | Identificador único |
| veiculo_id | INTEGER | FK, NULL | Veículo cadastrado (nullable) |
| placa_detectada | VARCHAR | NOT NULL | Placa lida pelo OCR |
| tipo_movimento | ENUM | NOT NULL | `entrada` / `saida` |
| data_hora | DATETIME | NOT NULL | Timestamp da detecção |
| confianca_ocr | FLOAT | 0.0–1.0 | Qualidade do reconhecimento |
| metodo_ocr | VARCHAR | NOT NULL | `easyocr` / `tesseract` / `hibrido` |
| imagem_path | VARCHAR | NULL | Caminho relativo da imagem salva |

#### `usuarios`

| Coluna | Tipo | Restrição | Descrição |
|--------|------|-----------|-----------|
| id | INTEGER | PK, Auto | Identificador único |
| username | VARCHAR | UNIQUE, NOT NULL | Nome de utilizador |
| senha_hash | VARCHAR | NOT NULL | Hash bcrypt da senha |
| nivel_acesso | ENUM | NOT NULL | `admin` / `operador` / `visualizador` |
| ativo | BOOLEAN | DEFAULT True | Conta ativa |
| criado_em | DATETIME | DEFAULT now() | Data de criação |

---

## Integração PLC / Cancela

### Protocolo Modbus TCP

```
  MÓDULO DESKTOP                        PLC / CANCELA ELETRÔNICA
  PLCController                         Porta Modbus TCP: 5020
       │
       │── connect() ──────────────────────────────────► TCP:5020
       │
       │── write_coil(0, True) ─────────────────────────► Coil 0 = 1
       │                                                   ┌──────────┐
       │                                                   │ CANCELA  │
       │                                                   │  ABRE ↑  │
       │                                                   └──────────┘
       │── read_discrete_inputs(0) ◄──────────── DI 0 ────► Sensor Laço
       │   (polling a cada 300ms)                          Indutivo
       │
       │   DI 0 = True  → veículo entrou no laço
       │   DI 0 = False → veículo saiu do laço
       │
       │── write_coil(0, False) ────────────────────────── Coil 0 = 0
       │                                                   ┌──────────┐
       │                                                   │ CANCELA  │
       │                                                   │ FECHA ↓  │
       │                                                   └──────────┘
       │
       │   FALLBACK: se DI 0 não responder em 8s
       │── write_coil(0, False) ─────────────────────────► Fecha por segurança
```

### Mapa de Registos Modbus

| Tipo | Endereço | Função Modbus | Direcção | Descrição |
|------|----------|--------------|----------|-----------|
| Coil | 0 | FC01 (read) / FC05 (write) | Escrita pelo Desktop | Comando cancela: `True`=abrir, `False`=fechar |
| Discrete Input | 0 | FC02 (read) | Leitura pelo Desktop | Sensor de laço: `True`=veículo presente |

### Regras de Acesso e Abertura da Cancela

Toda a viatura que entra no campus deve ser registada. A cancela é controlada
pelo sensor de laço indutivo e pelo resultado do OCR — não pelo cadastro da placa.

```
  Sensor de laço deteta veículo (DI 0 = True)
           │
           ▼
    Câmara captura frame e processa OCR
           │
    ┌──────▼──────┐
    │  OCR leu a  │── Não ──► Cancela NÃO abre
    │    placa?   │           Agente de segurança regista manualmente
    └──────┬──────┘           e abre cancela pelo botão físico
           │ Sim (qualquer placa, cadastrada ou não)
           ▼
    Movimento registado na BD (entrada ou saída)
           │
    ┌──────▼──────┐
    │  PLC        │── Não ──► Registo feito, sem controlo PLC
    │  conectado? │
    └──────┬──────┘
           │ Sim
           ▼
    abrir_cancela()  →  Coil 0 = True
           │
    Sensor OFF (veículo passou)  →  fechar_cancela()  →  Coil 0 = False
```

> **Nota:** O cadastro da placa não é condição de acesso.
> Veículos não cadastrados entram e são registados como "desconhecido".
> O relatório permite depois identificar padrões e presenças no campus.

### Simulador PLC Virtual

Para testes sem hardware, o projeto inclui um servidor Modbus TCP virtual:

```bash
# Iniciar simulador (terminal separado)
python -m desktop_module.simulador_plc

# Saída esperada:
#   Servidor Modbus TCP aguardando em 127.0.0.1:5020
#   Cancela: fechada ↓  |  Laço: livre ○
#   [SIM] Veículo chegará ao laço em 1.5s
#   [SIM] Veículo NO laço indutivo (sensor=ON)
#   [SIM] Veículo SAIU do laço (sensor=OFF)
#   Cancela: fechada ↓  |  Laço: livre ○
```

---

## Tecnologias

### Backend (Web Module)

| Pacote | Versão | Função |
|--------|--------|--------|
| FastAPI | 0.128.5 | Framework web REST |
| SQLAlchemy | 2.0.46 | ORM base de dados |
| Pydantic | 2.12.5 | Validação de schemas |
| Uvicorn | 0.40.0 | Servidor ASGI |
| python-jose | 3.5.0 | JWT (autenticação) |
| bcrypt | 5.0.0 | Hash de senhas |
| Jinja2 | 3.1.x | Templates HTML |

### Frontend (Web Module)

| Tecnologia | Versão | Função |
|-----------|--------|--------|
| Tailwind CSS | v4 (CDN) | Estilo utility-first |
| Bootstrap Icons | 1.11.3 | Ícones |
| Chart.js | 4.4.0 | Gráficos do dashboard |
| Vanilla JS | ES2020 | Interatividade |

### Computer Vision (Desktop Module)

| Pacote | Versão | Função |
|--------|--------|--------|
| Ultralytics (YOLO) | 8.4.13 | Detecção de placas |
| OpenCV | 4.13.0 | Processamento de imagens |
| EasyOCR | 1.7.2 | OCR com deep learning |
| pytesseract | 0.3.13 | Interface Tesseract |
| PyTorch (CPU) | 2.10.0 | Framework neural |
| Pillow | 12.1.0 | Manipulação de imagens |

### Integração Industrial

| Pacote | Versão | Função |
|--------|--------|--------|
| pymodbus | 3.9.2 | Cliente/servidor Modbus TCP |

---

## Instalação

### Pré-requisitos

- Python 3.8+ (recomendado: **3.13**)
- Tesseract OCR instalado no sistema
- Webcam ou arquivo de vídeo
- 4 GB RAM mínimo (8 GB recomendado)

### Passo 1: Clonar o Repositório

```bash
git clone https://github.com/setprogramacao/set-alpr-moz.git
cd set-alpr-moz
```

### Passo 2: Criar Ambiente Virtual

```bash
python -m venv venv

# Ativar (Windows CMD)
venv\Scripts\activate

# Ativar (Linux/macOS)
source venv/bin/activate
```

### Passo 3: Instalar Dependências

```bash
pip install -r requirements.txt
```

### Passo 4: Instalar Tesseract OCR

**Windows:** Descarregar de https://github.com/UB-Mannheim/tesseract/wiki e instalar em `C:\Program Files\Tesseract-OCR\`

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

### Passo 5: Inicializar Base de Dados

```bash
python init_database.py
```

Cria as tabelas e o utilizador `admin` / `admin123`.

---

## Configuração

O ficheiro `.env` controla todas as configurações do sistema:

```env
# === YOLO ===
YOLO_MODEL_PATH=desktop_module/models/license_plate_detector.pt
YOLO_CONFIDENCE=0.5

# === OCR ===
OCR_METHOD=hibrido               # easyocr | tesseract | hibrido
OCR_MIN_CONFIDENCE=0.3
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# === API ===
API_HOST=http://localhost:8000
API_TIMEOUT=30

# === BASE DE DADOS ===
DATABASE_URL=sqlite:///./alpr_unipiaget.db

# === SEGURANÇA ===
SECRET_KEY=mude-esta-chave-em-producao
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# === CÂMARA ===
VIDEO_SOURCE=0                   # 0=webcam, ou caminho para ficheiro
PROCESS_EVERY_N_FRAMES=5

# === PLC / CANCELA ===
PLC_HABILITADO=True
PLC_HOST=127.0.0.1
PLC_PORT=5020
BARREIRA_CONFIANCA_MINIMA=0.70   # Confiança mínima para abrir cancela
BARREIRA_TIMEOUT_SEGUNDOS=8      # Fecha automaticamente após N segundos
```

---

## Uso

### 1. Iniciar o Servidor Web

```bash
# Terminal 1
uvicorn web_module.main:app --reload --port 8000
```

Aceder em: http://localhost:8000 — Login: `admin` / `admin123`

### 2. Iniciar o Simulador PLC (para testes)

```bash
# Terminal 2
python -m desktop_module.simulador_plc
```

### 3. Iniciar o Módulo Desktop

```bash
# Terminal 3
python -m desktop_module.main
```

### Workflow Recomendado

1. Cadastrar **Proprietários** (Pessoas) via Dashboard Web
2. Cadastrar **Veículos** com placa no formato `XXX000XX`
3. Iniciar **Módulo Desktop** e clicar em "Iniciar Captura"
4. Apontar placa para câmara
5. Verificar **Registros** e **Dashboard** no browser

---

## Estrutura do Projeto

```
alpr_ujpm/
├── desktop_module/                 # Aplicação Desktop (Tkinter)
│   ├── main.py                    # Ponto de entrada
│   ├── simulador_plc.py           # Servidor Modbus TCP virtual
│   ├── config/
│   │   └── settings.py            # Todas as configurações (.env)
│   ├── core/
│   │   ├── detector.py            # YOLO v8 + OCR duplo
│   │   ├── camera.py              # Gestão de câmara/vídeo
│   │   ├── api_client.py          # Cliente HTTP para a API
│   │   └── plc_controller.py      # Cliente Modbus TCP
│   ├── ui/
│   │   └── main_window.py         # Interface Tkinter principal
│   └── models/
│       └── license_plate_detector.pt   # Modelo YOLO (5.2 MB)
│
├── web_module/                     # API REST + Dashboard Web
│   ├── main.py                    # Aplicação FastAPI
│   ├── routes/
│   │   ├── auth.py                # Login, JWT, gestão de utilizadores
│   │   ├── veiculos.py            # CRUD de veículos
│   │   ├── proprietarios.py       # CRUD de proprietários
│   │   ├── registros.py           # Registos de acesso + detecção
│   │   ├── dashboard.py           # Estatísticas e KPIs
│   │   └── relatorios.py          # Relatórios e exportação CSV
│   ├── services/
│   │   ├── auth_service.py        # Lógica JWT + bcrypt
│   │   └── deteccao_service.py    # Toggle entrada/saída, duplicatas
│   ├── templates/                 # HTML Jinja2
│   │   ├── base.html              # Layout com sidebar
│   │   ├── login.html
│   │   ├── index.html             # Dashboard
│   │   ├── veiculos.html
│   │   ├── proprietarios.html
│   │   ├── registros.html
│   │   ├── relatorios.html
│   │   └── usuarios.html
│   └── static/
│       └── js/main.js             # JS partilhado (auth, apiRequest)
│
├── shared/                         # Código partilhado
│   ├── schemas.py                 # Modelos Pydantic (request/response)
│   └── utils.py                   # Validação placa, correção OCR, imagens
│
├── docs_apresentacao/              # Landing page para apresentação TCC
│   └── index.html
│
├── storage/
│   ├── images/                    # Imagens de detecções salvas
│   └── test_images/               # Imagens para testes
│
├── .env                            # Configurações (não commitar)
├── requirements.txt
├── init_database.py
└── README.md
```

---

## API Endpoints

Base URL: `http://localhost:8000/api/v1`
Autenticação: `Authorization: Bearer <jwt_token>`
Documentação interativa: http://localhost:8000/api/docs

### Autenticação e Utilizadores

```
POST   /auth/login                  Login — devolve JWT token
GET    /auth/me                     Perfil do utilizador atual
POST   /usuarios                    Criar utilizador (admin)
GET    /usuarios                    Listar utilizadores
PUT    /usuarios/{id}               Atualizar utilizador
DELETE /usuarios/{id}               Desativar utilizador (admin)
```

### Detecção (Desktop → API)

```
POST   /registros/deteccao          Registar detecção (sem autenticação)
                                    Body: { placa, tipo_movimento, confianca_ocr,
                                            metodo_ocr, imagem_base64, timestamp }
```

### Veículos e Proprietários

```
GET    /veiculos                    Listar (filtros: proprietario_id, placa)
POST   /veiculos                    Criar
GET    /veiculos/placa/{placa}      Buscar por placa
PUT    /veiculos/{id}               Atualizar
DELETE /veiculos/{id}               Eliminar (admin)

GET    /proprietarios               Listar (filtros: categoria, nome, ativo)
POST   /proprietarios               Criar
PUT    /proprietarios/{id}          Atualizar
DELETE /proprietarios/{id}          Eliminar (admin, em cascata)
```

### Registros e Dashboard

```
GET    /registros                   Listar com filtros (placa, tipo, datas)
GET    /registros/count/hoje        Contagem de hoje (total, entradas, saídas)
GET    /registros/ultimos/por-hora  Gráfico horário (últimas N horas)
DELETE /registros/{id}              Eliminar registo (admin)

GET    /dashboard/estatisticas      KPIs completos
GET    /dashboard/veiculos-no-campus Veículos presentes agora
GET    /dashboard/alertas           Alertas (ausência > 3 dias, etc.)
GET    /dashboard/atividade-recente Últimas detecções

POST   /relatorios/veiculos         Análise por veículo (período)
POST   /relatorios/proprietarios    Análise por proprietário
GET    /relatorios/exportar/registros  Exportar CSV
GET    /relatorios/resumo           Resumo do período
```

### Exemplo de Request/Response

**POST /registros/deteccao** (Desktop → API):
```json
{
  "placa_detectada": "AHK641MP",
  "tipo_movimento": "entrada",
  "confianca_ocr": 0.87,
  "metodo_ocr": "hibrido",
  "timestamp": "2026-03-04T14:32:00"
}
```

**Resposta:**
```json
{
  "sucesso": true,
  "mensagem": "Detecção registrada [ENTRADA] — José Silva (docente)",
  "registro_id": 142,
  "veiculo_cadastrado": true,
  "duplicata": false,
  "tipo_movimento": "entrada"
}
```

---

## Formato de Placas Moçambicanas

### Padrão: `XXX 000 XX`

```
  ┌─────────────────────────────────────────┐
  │  ┌─────┐  ┌─────┐  ┌─────┐             │
  │  │ M Z │  │ 1 2 │  │ M C │  MOÇAMBIQUE │
  │  │ B   │  │ 3   │  │    │             │
  │  └─────┘  └─────┘  └─────┘             │
  │    3 Letras  3 Números  2 Letras        │
  └─────────────────────────────────────────┘

  Regex: ^[A-Z]{3}[0-9]{3}[A-Z]{2}$
```

### Correção Automática de Erros OCR

O sistema corrige confusões visuais com base na posição do caractere:

| Leu | Posição | Esperado | Substitui por |
|-----|---------|----------|--------------|
| `0` | Letra (0-2, 6-7) | Letra | `O` |
| `O` | Número (3-5) | Número | `0` |
| `1` | Letra (0-2, 6-7) | Letra | `I` |
| `I` ou `L` | Número (3-5) | Número | `1` |
| `5` | Letra (0-2, 6-7) | Letra | `S` |
| `S` | Número (3-5) | Número | `5` |
| `8` | Letra (0-2, 6-7) | Letra | `B` |
| `6` | Letra (0-2, 6-7) | Letra | `G` |
| `2` | Letra (0-2, 6-7) | Letra | `Z` |

**Exemplo:**
```
OCR leu:       MZB1O3MC   (O em posição numérica)
Após correção: MZB103MC   (O → 0)
```

---

## Troubleshooting

### Desktop não abre

```bash
# Verificar ambiente virtual
venv\Scripts\activate
pip install -r requirements.txt
```

### Webcam não funciona

```env
# .env — tentar outro índice
VIDEO_SOURCE=1
# ou usar ficheiro de vídeo:
VIDEO_SOURCE=storage/test_images/video.mp4
```

### PLC não conecta

```bash
# Verificar se simulador está a correr
python -m desktop_module.simulador_plc

# Verificar .env
PLC_HOST=127.0.0.1
PLC_PORT=5020
```

### Desktop não conecta à API

```bash
# Verificar se servidor web está a correr
curl http://localhost:8000/health

# .env deve ter:
API_HOST=http://localhost:8000
```

### Tesseract não encontrado

```env
# Windows:
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Linux/macOS:
TESSERACT_CMD=tesseract
```

---

## Papéis de Utilizador

| Papel | Criar/Editar | Eliminar | Relatórios | Gerir Utilizadores |
|-------|-------------|----------|------------|-------------------|
| `admin` | Sim | Sim | Sim | Sim |
| `operador` | Sim | Não | Sim | Não |
| `visualizador` | Não | Não | Leitura | Não |

---

## Licença

Projeto académico desenvolvido para a Universidade Jean Piaget de Moçambique.
Proibida a reprodução comercial sem autorização.

---

**Sistema ALPR UNIPIAGET — Reconhecimento Automático de Placas para Moçambique**
