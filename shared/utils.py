"""
Utilitários Compartilhados - Sistema ALPR UNIPIAGET
Funções auxiliares usadas pelos módulos Desktop e Web
"""

import re
import cv2
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path
import base64
import hashlib
import os


# ============================================================================
# VALIDAÇÃO DE PLACAS
# ============================================================================

# Modo Debug: aceita qualquer texto (útil para testes)
DEBUG_MODE = os.getenv("ALPR_DEBUG_MODE", "False").lower() == "true"

def validar_placa_debug(placa: str) -> Tuple[bool, str]:
    """
    Validação relaxada para modo debug
    Aceita qualquer texto alfanumérico com 3+ caracteres

    Args:
        placa: String da placa a validar

    Returns:
        Tupla (válido: bool, placa_limpa: str)
    """
    if not placa:
        return False, ""

    # Remove espaços e converte para maiúscula
    placa_limpa = placa.upper().replace("-", "").replace(" ", "")

    # Remove caracteres não alfanuméricos
    placa_limpa = re.sub(r'[^A-Z0-9]', '', placa_limpa)

    # Aceita qualquer texto com 3 ou mais caracteres
    if len(placa_limpa) >= 3:
        return True, placa_limpa

    return False, placa_limpa

def validar_placa_mocambique(placa: str) -> Tuple[bool, str]:
    """
    Valida formato de placa moçambicana

    Formato: XXX000XX (8 caracteres)
    - 3 letras iniciais (código de província/categoria)
    - 3 dígitos numéricos
    - 2 letras finais (série)

    Exemplos válidos: MPM123AB, AAA000ZZ, LMX456CD

    Args:
        placa: String da placa a validar

    Returns:
        Tupla (válido: bool, placa_limpa: str)
    """
    # Se modo debug ativado, usa validação relaxada
    if DEBUG_MODE:
        return validar_placa_debug(placa)

    if not placa:
        return False, ""

    # Remove espaços, hífens e converte para maiúscula
    placa_limpa = placa.upper().replace("-", "").replace(" ", "")

    # Verifica comprimento
    if len(placa_limpa) != 8:
        return False, placa_limpa

    # Valida formato: 3 letras + 3 números + 2 letras
    # Formato moçambicano: XXX000XX
    padrao = r'^[A-Z]{3}\d{3}[A-Z]{2}$'

    if re.match(padrao, placa_limpa):
        return True, placa_limpa

    return False, placa_limpa


def corrigir_placa_ocr(texto: str) -> str:
    """
    Corrige erros comuns de OCR em placas moçambicanas usando formato conhecido.

    Formato moçambicano: XXX000XX (3 letras + 3 números + 2 letras)

    Aplica correções inteligentes baseadas na posição:
    - Posições 0-2: SOMENTE LETRAS (corrige números que parecem letras)
    - Posições 3-5: SOMENTE NÚMEROS (corrige letras que parecem números)
    - Posições 6-7: SOMENTE LETRAS (corrige números que parecem letras)

    Confusões comuns corrigidas:
    - 0 (zero) ↔ O (letra O)
    - 1 (um) ↔ I (letra I) / L (letra L)
    - 5 (cinco) ↔ S (letra S)
    - 8 (oito) ↔ B (letra B)
    - 6 (seis) ↔ G (letra G)
    - 2 (dois) ↔ Z (letra Z)
    - 0 (zero) ↔ D (letra D) / Q (letra Q)
    - 7 (sete) ↔ T (letra T) / J (letra J)
    - 9 (nove) ↔ g (letra G minúscula)

    Args:
        texto: Texto bruto do OCR

    Returns:
        Placa corrigida segundo formato moçambicano
    """
    if not texto:
        return ""

    # 1. Limpa e normaliza
    texto_limpo = texto.upper()
    texto_limpo = re.sub(r'[\s\-.,;:_/\\|]', '', texto_limpo)
    texto_limpo = re.sub(r'[^A-Z0-9]', '', texto_limpo)

    # Se muito curto ou muito longo, retorna sem correção
    if len(texto_limpo) < 6 or len(texto_limpo) > 10:
        return texto_limpo

    # Ajusta para 8 caracteres (remove extras do início/fim)
    if len(texto_limpo) > 8:
        # Tenta encontrar padrão mais provável
        # Procura por sequência de 3 letras seguidas de números
        match = re.search(r'[A-Z]{3}\d{3}[A-Z]{2}', texto_limpo)
        if match:
            texto_limpo = match.group()
        else:
            # Pega os 8 primeiros ou do meio
            start = (len(texto_limpo) - 8) // 2
            texto_limpo = texto_limpo[start:start+8]

    # Preenche inteligentemente se muito curto
    if len(texto_limpo) < 8:
        # Tenta detectar onde preencher baseado no padrão
        # Se tem formato XXX... preenche a parte numérica com 0s
        if len(texto_limpo) >= 3 and texto_limpo[:3].isalpha():
            # Tem 3 letras no início
            parte_letras_inicial = texto_limpo[:3]
            resto = texto_limpo[3:]

            # Separa números e letras do resto
            parte_numerica = ''
            parte_letras_final = ''

            for char in resto:
                if char.isdigit() and len(parte_numerica) < 3:
                    parte_numerica += char
                elif char.isalpha():
                    parte_letras_final += char

            # Preenche até ter 3 números e 2 letras
            parte_numerica = parte_numerica.ljust(3, '0')
            parte_letras_final = parte_letras_final.ljust(2, 'X')[:2]

            texto_limpo = parte_letras_inicial + parte_numerica + parte_letras_final
        else:
            # Fallback: preenche no final
            texto_limpo = texto_limpo.ljust(8, 'X')[:8]

    # 2. Mapas de correção

    # Números que parecem letras (para partes ALFABÉTICAS)
    NUMEROS_PARA_LETRAS = {
        '0': 'O',  # Zero → Letra O
        '1': 'I',  # Um → Letra I
        '2': 'Z',  # Dois → Letra Z
        '3': 'E',  # Três → Letra E (menos comum)
        '4': 'A',  # Quatro → Letra A (menos comum)
        '5': 'S',  # Cinco → Letra S
        '6': 'G',  # Seis → Letra G
        '7': 'T',  # Sete → Letra T
        '8': 'B',  # Oito → Letra B
        '9': 'G',  # Nove → Letra G
    }

    # Letras que parecem números (para parte NUMÉRICA)
    LETRAS_PARA_NUMEROS = {
        'O': '0',  # Letra O → Zero
        'Q': '0',  # Letra Q → Zero
        'D': '0',  # Letra D → Zero
        'I': '1',  # Letra I → Um
        'L': '1',  # Letra L → Um
        'J': '1',  # Letra J → Um (menos comum)
        'Z': '2',  # Letra Z → Dois
        'E': '3',  # Letra E → Três (menos comum)
        'A': '4',  # Letra A → Quatro (menos comum)
        'S': '5',  # Letra S → Cinco
        'G': '6',  # Letra G → Seis
        'T': '7',  # Letra T → Sete
        'B': '8',  # Letra B → Oito
        'g': '9',  # Letra g minúscula → Nove
    }

    # 3. Aplica correções baseadas em posições

    resultado = []

    for i, char in enumerate(texto_limpo):
        if i < 3:  # Posições 0-2: LETRAS
            if char.isdigit():
                # É um número onde deveria ser letra - converte
                char = NUMEROS_PARA_LETRAS.get(char, char)
            # Garante que é letra
            if not char.isalpha():
                char = 'X'  # Placeholder

        elif i < 6:  # Posições 3-5: NÚMEROS
            if char.isalpha():
                # É uma letra onde deveria ser número - converte
                char = LETRAS_PARA_NUMEROS.get(char, char)
            # Garante que é número
            if not char.isdigit():
                char = '0'  # Placeholder

        else:  # Posições 6-7: LETRAS
            if char.isdigit():
                # É um número onde deveria ser letra - converte
                char = NUMEROS_PARA_LETRAS.get(char, char)
            # Garante que é letra
            if not char.isalpha():
                char = 'X'  # Placeholder

        resultado.append(char)

    return ''.join(resultado)


def limpar_texto_ocr(texto: str) -> str:
    """
    Limpa e normaliza texto detectado por OCR (compatibilidade).

    Esta função mantém compatibilidade com código existente.
    Chama a nova função corrigir_placa_ocr() que é muito mais inteligente.

    Args:
        texto: Texto bruto do OCR

    Returns:
        Texto limpo e corrigido
    """
    return corrigir_placa_ocr(texto)


# ============================================================================
# PROCESSAMENTO DE IMAGENS
# ============================================================================

def preprocessar_imagem_placa(imagem: np.ndarray) -> np.ndarray:
    """
    Pré-processa imagem de placa para melhorar OCR

    Aplica:
    - Conversão para escala de cinza
    - Redimensionamento
    - Filtros de ruído
    - Ajuste de contraste
    - Binarização adaptativa

    Args:
        imagem: Imagem numpy array (BGR)

    Returns:
        Imagem pré-processada
    """
    if imagem is None or imagem.size == 0:
        return imagem

    # Conversão para escala de cinza
    if len(imagem.shape) == 3:
        gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    else:
        gray = imagem.copy()

    # Redimensiona para tamanho padrão (mantém aspect ratio)
    altura_desejada = 100
    proporcao = altura_desejada / gray.shape[0]
    largura_nova = int(gray.shape[1] * proporcao)
    gray = cv2.resize(gray, (largura_nova, altura_desejada), interpolation=cv2.INTER_CUBIC)

    # Remove ruído com filtro bilateral (preserva bordas)
    denoised = cv2.bilateralFilter(gray, 11, 17, 17)

    # Ajusta contraste com CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contraste = clahe.apply(denoised)

    # Binarização adaptativa (melhor para iluminação irregular)
    binario = cv2.adaptiveThreshold(
        contraste,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )

    # Operações morfológicas para limpar ruído
    kernel = np.ones((3, 3), np.uint8)
    limpo = cv2.morphologyEx(binario, cv2.MORPH_CLOSE, kernel)
    limpo = cv2.morphologyEx(limpo, cv2.MORPH_OPEN, kernel)

    return limpo


def preprocessar_imagem_placa_cinza(imagem: np.ndarray) -> np.ndarray:
    """
    Pré-processa imagem de placa para EasyOCR.

    Retorna imagem em escala de cinza com contraste melhorado,
    SEM binarização. EasyOCR foi treinado em imagens naturais e
    performa muito melhor com cinza do que com imagem binária.

    Args:
        imagem: Imagem numpy array (BGR)

    Returns:
        Imagem em cinza com contraste melhorado
    """
    if imagem is None or imagem.size == 0:
        return imagem

    # Conversão para escala de cinza
    if len(imagem.shape) == 3:
        gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    else:
        gray = imagem.copy()

    # Redimensiona para altura mínima de 120px para melhorar OCR
    altura_atual = gray.shape[0]
    largura_atual = gray.shape[1]

    if altura_atual < 120:
        proporcao = 120 / altura_atual
        largura_nova = max(int(largura_atual * proporcao), 200)
        gray = cv2.resize(gray, (largura_nova, 120), interpolation=cv2.INTER_CUBIC)
    elif largura_atual < 200:
        proporcao = 200 / largura_atual
        altura_nova = int(altura_atual * proporcao)
        gray = cv2.resize(gray, (200, altura_nova), interpolation=cv2.INTER_CUBIC)

    # Remove ruído preservando bordas dos caracteres
    denoised = cv2.bilateralFilter(gray, 9, 15, 15)

    # Melhora contraste com CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    contraste = clahe.apply(denoised)

    return contraste


def adicionar_margem_placa(imagem: np.ndarray, margem: int = 15) -> np.ndarray:
    """
    Adiciona margem branca ao redor da placa.

    Muitos motores OCR falham quando os caracteres estão mesmo na borda
    da imagem — não há contexto visual em volta. Uma margem branca garante
    que os caracteres respiram e o OCR os lê melhor.

    Args:
        imagem: Imagem numpy array (BGR ou cinza)
        margem: Margem em pixels a adicionar em cada lado (padrão: 15)

    Returns:
        Imagem com margem branca adicionada
    """
    if imagem is None or imagem.size == 0:
        return imagem

    cor = [255, 255, 255] if len(imagem.shape) == 3 else 255

    return cv2.copyMakeBorder(
        imagem,
        margem, margem, margem, margem,
        cv2.BORDER_CONSTANT,
        value=cor
    )


def mesclar_resultados_ocr(texto1: str, texto2: str) -> str:
    """
    Combina dois resultados OCR usando votação por posição de caractere.

    Em vez de escolher um resultado inteiro por confiança global,
    compara cada posição individualmente:
      - Se ambos concordam → usa esse caractere (alta certeza)
      - Se discordam → aplica a regra posicional para desempatar:
          * Posições 0-2 e 6-7 = devem ser LETRAS
          * Posições 3-5       = devem ser NÚMEROS

    Exemplo:
      EasyOCR:  "MPM1Z3AB"   (confunde Z com 2 na posição numérica)
      Tesseract: "MPM123AB"
      → Posição 4: EasyOCR="Z" (letra em posição numérica), Tesseract="2" (dígito ✓)
      → Resultado: "MPM123AB" ← correctamente escolhe o dígito

    Args:
        texto1: Primeiro resultado OCR (idealmente 8 caracteres)
        texto2: Segundo resultado OCR (idealmente 8 caracteres)

    Returns:
        Texto mesclado de 8 caracteres com a melhor leitura posição a posição
    """
    if len(texto1) != 8 and len(texto2) != 8:
        return texto1 or texto2
    if len(texto1) != 8:
        return texto2
    if len(texto2) != 8:
        return texto1

    resultado = []

    for i, (c1, c2) in enumerate(zip(texto1, texto2)):
        if c1 == c2:
            resultado.append(c1)  # Ambos concordam — alta certeza
            continue

        # Discordam — usa regra posicional para desempatar
        posicao_letra = (i < 3 or i >= 6)  # posições 0,1,2,6,7 devem ser letras

        if posicao_letra:
            if c1.isalpha() and c2.isdigit():
                resultado.append(c1)   # c1 é letra — correcto para esta posição
            elif c2.isalpha() and c1.isdigit():
                resultado.append(c2)   # c2 é letra — correcto
            else:
                resultado.append(c1)   # Ambas letras diferentes → favorece texto1
        else:
            # Posição numérica (3, 4, 5)
            if c1.isdigit() and c2.isalpha():
                resultado.append(c1)   # c1 é dígito — correcto
            elif c2.isdigit() and c1.isalpha():
                resultado.append(c2)   # c2 é dígito — correcto
            else:
                resultado.append(c1)   # Ambos dígitos diferentes → favorece texto1

    return ''.join(resultado)


def redimensionar_imagem_para_salvamento(imagem: np.ndarray, max_largura: int = 800) -> np.ndarray:
    """
    Redimensiona imagem para salvamento (economiza espaço)

    Args:
        imagem: Imagem numpy array
        max_largura: Largura máxima

    Returns:
        Imagem redimensionada
    """
    if imagem is None or imagem.size == 0:
        return imagem

    altura, largura = imagem.shape[:2]

    if largura > max_largura:
        proporcao = max_largura / largura
        nova_largura = max_largura
        nova_altura = int(altura * proporcao)
        imagem = cv2.resize(imagem, (nova_largura, nova_altura), interpolation=cv2.INTER_AREA)

    return imagem


# ============================================================================
# SALVAMENTO DE IMAGENS
# ============================================================================

def gerar_nome_arquivo_imagem(placa: str, timestamp: Optional[datetime] = None) -> str:
    """
    Gera nome único para arquivo de imagem

    Formato: PLACA_YYYYMMDD_HHMMSS_HASH.jpg

    Args:
        placa: Placa detectada
        timestamp: Timestamp da detecção (default: agora)

    Returns:
        Nome do arquivo
    """
    if timestamp is None:
        timestamp = datetime.now()

    # Formata timestamp
    data_hora = timestamp.strftime("%Y%m%d_%H%M%S")

    # Gera hash curto para garantir unicidade
    hash_str = hashlib.md5(f"{placa}{timestamp.isoformat()}".encode()).hexdigest()[:8]

    # Limpa placa para usar no nome do arquivo
    placa_limpa = re.sub(r'[^A-Z0-9]', '', placa.upper())

    return f"{placa_limpa}_{data_hora}_{hash_str}.jpg"


def salvar_imagem_deteccao(
    imagem: np.ndarray,
    placa: str,
    diretorio_base: str = "storage/images",
    timestamp: Optional[datetime] = None
) -> Optional[str]:
    """
    Salva imagem de detecção no sistema de arquivos

    Organiza por data: storage/images/YYYY/MM/DD/arquivo.jpg

    Args:
        imagem: Imagem numpy array
        placa: Placa detectada
        diretorio_base: Diretório base para salvamento
        timestamp: Timestamp da detecção

    Returns:
        Caminho relativo do arquivo salvo ou None em caso de erro
    """
    try:
        if imagem is None or imagem.size == 0:
            return None

        if timestamp is None:
            timestamp = datetime.now()

        # Cria estrutura de diretórios por data
        ano = timestamp.strftime("%Y")
        mes = timestamp.strftime("%m")
        dia = timestamp.strftime("%d")

        diretorio_completo = Path(diretorio_base) / ano / mes / dia
        diretorio_completo.mkdir(parents=True, exist_ok=True)

        # Gera nome do arquivo
        nome_arquivo = gerar_nome_arquivo_imagem(placa, timestamp)
        caminho_completo = diretorio_completo / nome_arquivo

        # Redimensiona para economizar espaço
        imagem_redimensionada = redimensionar_imagem_para_salvamento(imagem)

        # Salva imagem com compressão JPEG
        cv2.imwrite(str(caminho_completo), imagem_redimensionada, [cv2.IMWRITE_JPEG_QUALITY, 85])

        # Retorna caminho relativo
        caminho_relativo = str(Path(ano) / mes / dia / nome_arquivo)
        return caminho_relativo

    except Exception as e:
        print(f"Erro ao salvar imagem: {e}")
        return None


def imagem_para_base64(imagem: np.ndarray, formato: str = '.jpg') -> Optional[str]:
    """
    Converte imagem numpy para string base64

    Args:
        imagem: Imagem numpy array
        formato: Formato de codificação (.jpg ou .png)

    Returns:
        String base64 ou None em caso de erro
    """
    try:
        if imagem is None or imagem.size == 0:
            return None

        # Codifica imagem
        _, buffer = cv2.imencode(formato, imagem)

        # Converte para base64
        imagem_base64 = base64.b64encode(buffer).decode('utf-8')

        return imagem_base64

    except Exception as e:
        print(f"Erro ao converter imagem para base64: {e}")
        return None


def base64_para_imagem(imagem_base64: str) -> Optional[np.ndarray]:
    """
    Converte string base64 para imagem numpy

    Args:
        imagem_base64: String base64

    Returns:
        Imagem numpy array ou None em caso de erro
    """
    try:
        if not imagem_base64:
            return None

        # Decodifica base64
        imagem_bytes = base64.b64decode(imagem_base64)

        # Converte para numpy array
        nparr = np.frombuffer(imagem_bytes, np.uint8)

        # Decodifica imagem
        imagem = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        return imagem

    except Exception as e:
        print(f"Erro ao converter base64 para imagem: {e}")
        return None


# ============================================================================
# CÁLCULOS DE TEMPO
# ============================================================================

def calcular_tempo_permanencia(entrada: datetime, saida: Optional[datetime] = None) -> int:
    """
    Calcula tempo de permanência em minutos

    Args:
        entrada: Data/hora de entrada
        saida: Data/hora de saída (default: agora)

    Returns:
        Tempo em minutos
    """
    if saida is None:
        saida = datetime.now()

    delta = saida - entrada
    minutos = int(delta.total_seconds() / 60)

    return max(0, minutos)  # Garante que não retorna negativo


def formatar_tempo_permanencia(minutos: int) -> str:
    """
    Formata tempo de permanência em string legível

    Args:
        minutos: Tempo em minutos

    Returns:
        String formatada (ex: "2h 30min", "45min", "3d 2h")
    """
    if minutos < 0:
        return "0min"

    dias = minutos // (24 * 60)
    horas = (minutos % (24 * 60)) // 60
    mins = minutos % 60

    partes = []

    if dias > 0:
        partes.append(f"{dias}d")
    if horas > 0:
        partes.append(f"{horas}h")
    if mins > 0 or len(partes) == 0:
        partes.append(f"{mins}min")

    return " ".join(partes)


def verificar_duplicata_temporal(
    ultimo_registro: datetime,
    intervalo_minimo: int = 5
) -> Tuple[bool, int]:
    """
    Verifica se registro é duplicata temporal

    Args:
        ultimo_registro: Data/hora do último registro
        intervalo_minimo: Intervalo mínimo em minutos

    Returns:
        Tupla (é_duplicata: bool, segundos_desde_ultimo: int)
    """
    agora = datetime.now()
    delta = agora - ultimo_registro
    segundos = int(delta.total_seconds())

    eh_duplicata = segundos < (intervalo_minimo * 60)

    return eh_duplicata, segundos


# ============================================================================
# VALIDAÇÕES DIVERSAS
# ============================================================================

def validar_email(email: str) -> bool:
    """
    Valida formato de email

    Args:
        email: String de email

    Returns:
        True se válido, False caso contrário
    """
    if not email:
        return False

    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(padrao, email))


def validar_telefone_mocambique(telefone: str) -> Tuple[bool, str]:
    """
    Valida e formata telefone moçambicano

    Formatos aceitos:
    - +258XXXXXXXXX
    - 258XXXXXXXXX
    - 8XXXXXXXX (adiciona +258)
    - 2XXXXXXXX (adiciona +258)

    Args:
        telefone: String do telefone

    Returns:
        Tupla (válido: bool, telefone_formatado: str)
    """
    if not telefone:
        return False, ""

    # Remove espaços e caracteres especiais
    telefone_limpo = re.sub(r'[^\d+]', '', telefone)

    # Adiciona código do país se necessário
    if telefone_limpo.startswith('+258'):
        pass
    elif telefone_limpo.startswith('258'):
        telefone_limpo = '+' + telefone_limpo
    elif telefone_limpo.startswith('8') or telefone_limpo.startswith('2'):
        if len(telefone_limpo) == 9:
            telefone_limpo = '+258' + telefone_limpo

    # Valida formato final: +258XXXXXXXXX
    padrao = r'^\+258[28]\d{8}$'

    if re.match(padrao, telefone_limpo):
        return True, telefone_limpo

    return False, telefone_limpo


def normalizar_nome(nome: str) -> str:
    """
    Normaliza nome próprio (capitaliza corretamente)

    Args:
        nome: Nome a normalizar

    Returns:
        Nome normalizado
    """
    if not nome:
        return ""

    # Remove espaços extras
    nome = " ".join(nome.split())

    # Capitaliza cada palavra, exceto preposições
    preposicoes = {'de', 'da', 'do', 'das', 'dos', 'e'}

    palavras = nome.split()
    palavras_normalizadas = []

    for i, palavra in enumerate(palavras):
        if i == 0 or palavra.lower() not in preposicoes:
            palavras_normalizadas.append(palavra.capitalize())
        else:
            palavras_normalizadas.append(palavra.lower())

    return " ".join(palavras_normalizadas)


# ============================================================================
# UTILITÁRIOS DE CONFIGURAÇÃO
# ============================================================================

def converter_valor_config(valor: str, tipo: str):
    """
    Converte valor de configuração para tipo apropriado

    Args:
        valor: Valor em string
        tipo: Tipo desejado ('string', 'integer', 'float', 'boolean', 'json')

    Returns:
        Valor convertido
    """
    import json

    if tipo == 'string':
        return valor
    elif tipo == 'integer':
        return int(valor)
    elif tipo == 'float':
        return float(valor)
    elif tipo == 'boolean':
        return valor.lower() in ('true', '1', 'yes', 'sim')
    elif tipo == 'json':
        return json.loads(valor)
    else:
        return valor


# ============================================================================
# UTILITÁRIOS DE LOG
# ============================================================================

def formatar_log_deteccao(
    placa: str,
    tipo_movimento: str,
    confianca: float,
    metodo: str,
    cadastrado: bool
) -> str:
    """
    Formata mensagem de log para detecção

    Args:
        placa: Placa detectada
        tipo_movimento: entrada ou saida
        confianca: Confiança do OCR
        metodo: Método OCR usado
        cadastrado: Se veículo está cadastrado

    Returns:
        String formatada para log
    """
    status = "✓ CADASTRADO" if cadastrado else "✗ DESCONHECIDO"
    emoji = "🚗→" if tipo_movimento == "entrada" else "🚗←"

    return (
        f"{emoji} {placa} | {tipo_movimento.upper()} | "
        f"Confiança: {confianca:.2%} | {metodo.upper()} | {status}"
    )


def gerar_resumo_periodo(
    data_inicio: datetime,
    data_fim: datetime,
    total_registros: int,
    total_veiculos_unicos: int
) -> str:
    """
    Gera resumo textual de período

    Args:
        data_inicio: Data de início
        data_fim: Data de fim
        total_registros: Total de registros
        total_veiculos_unicos: Total de veículos únicos

    Returns:
        String com resumo
    """
    dias = (data_fim - data_inicio).days + 1

    return (
        f"Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')} ({dias} dias) | "
        f"Registros: {total_registros} | Veículos únicos: {total_veiculos_unicos}"
    )
