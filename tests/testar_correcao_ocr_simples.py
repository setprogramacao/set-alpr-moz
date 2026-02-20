"""
Script Simples de Teste da Correção OCR
Testa apenas a função de correção sem dependências pesadas
"""
import re
import sys

# Configura encoding UTF-8 no Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def corrigir_placa_ocr(texto: str) -> str:
    """
    Versão simplificada copiada de shared/utils.py para testes
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
        match = re.search(r'[A-Z]{3}\d{3}[A-Z]{2}', texto_limpo)
        if match:
            texto_limpo = match.group()
        else:
            # Pega os 8 primeiros ou do meio
            start = (len(texto_limpo) - 8) // 2
            texto_limpo = texto_limpo[start:start+8]

    # Preenche inteligentemente se muito curto
    if len(texto_limpo) < 8:
        # Se tem formato XXX... preenche a parte numérica com 0s
        if len(texto_limpo) >= 3 and texto_limpo[:3].isalpha():
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
            texto_limpo = texto_limpo.ljust(8, 'X')[:8]

    # 2. Mapas de correção
    NUMEROS_PARA_LETRAS = {
        '0': 'O', '1': 'I', '2': 'Z', '3': 'E', '4': 'A',
        '5': 'S', '6': 'G', '7': 'T', '8': 'B', '9': 'G',
    }

    LETRAS_PARA_NUMEROS = {
        'O': '0', 'Q': '0', 'D': '0', 'I': '1', 'L': '1', 'J': '1',
        'Z': '2', 'E': '3', 'A': '4', 'S': '5', 'G': '6',
        'T': '7', 'B': '8', 'g': '9',
    }

    # 3. Aplica correções baseadas em posições
    resultado = []

    for i, char in enumerate(texto_limpo):
        if i < 3:  # Posições 0-2: LETRAS
            if char.isdigit():
                char = NUMEROS_PARA_LETRAS.get(char, char)
            if not char.isalpha():
                char = 'X'

        elif i < 6:  # Posições 3-5: NÚMEROS
            if char.isalpha():
                char = LETRAS_PARA_NUMEROS.get(char, char)
            if not char.isdigit():
                char = '0'

        else:  # Posições 6-7: LETRAS
            if char.isdigit():
                char = NUMEROS_PARA_LETRAS.get(char, char)
            if not char.isalpha():
                char = 'X'

        resultado.append(char)

    return ''.join(resultado)


def validar_placa_mocambique(placa: str):
    """Validação simplificada"""
    placa_limpa = placa.upper().replace("-", "").replace(" ", "")
    padrao = r'^[A-Z]{3}\d{3}[A-Z]{2}$'
    valido = bool(re.match(padrao, placa_limpa))
    return valido, placa_limpa


print()
print("=" * 80)
print("  TESTE DE CORREÇÃO OCR - FORMATO MOÇAMBICANO XXX000XX")
print("=" * 80)
print()

# Casos de teste críticos
casos = [
    ("MPM123AB", "MPM123AB", "Placa correcta"),
    ("MPM1O3AB", "MPM103AB", "O → 0 na parte numérica"),
    ("MP2123AB", "MPZ123AB", "2 → Z na parte alfabética"),
    ("MPLI23AB", "MPL123AB", "I → 1 na parte numérica"),
    ("0PMO23AB", "OPM023AB", "0→O alfabética, O→0 numérica"),
    ("MPM12AB", "MPM120AB", "Preenche parte numérica"),
    ("8PM1S3A0", "BPM153AO", "Múltiplos erros"),
]

print("Casos de teste:")
print("-" * 80)

sucesso = 0
falhas = 0

for entrada, esperado, descricao in casos:
    resultado = corrigir_placa_ocr(entrada)
    valido, _ = validar_placa_mocambique(resultado)

    if resultado == esperado and valido:
        status = "✓"
        cor = "\033[92m"
        sucesso += 1
    else:
        status = "✗"
        cor = "\033[91m"
        falhas += 1

    cor_reset = "\033[0m"

    print(f"  {status} {cor}{entrada:12s} → {resultado:8s}{cor_reset} | {descricao}")
    if resultado != esperado:
        print(f"     Esperado: {esperado}")

print()
print("=" * 80)
print(f"  Resultados: {sucesso} sucessos, {falhas} falhas")
print("=" * 80)
print()
