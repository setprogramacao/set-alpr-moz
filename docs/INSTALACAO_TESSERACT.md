# Instalação do Tesseract OCR - Windows

## Passo 1: Download

**Link de download**: https://github.com/UB-Mannheim/tesseract/wiki

1. Acesse o link acima
2. Clique em **"tesseract-ocr-w64-setup-5.x.x.exe"** (versão mais recente)
3. Baixe o instalador (aproximadamente 60 MB)

## Passo 2: Instalação

1. Execute o instalador baixado
2. **IMPORTANTE**: Durante a instalação, anote o caminho de instalação
   - Padrão: `C:\Program Files\Tesseract-OCR`
3. Na tela "Select Components":
   - ✅ Marque "English" (obrigatório)
   - ✅ Marque "Portuguese" (opcional, para melhor suporte)
4. Complete a instalação

## Passo 3: Verificar Instalação

Abra o PowerShell/CMD e execute:

```bash
"C:\Program Files\Tesseract-OCR\tesseract.exe" --version
```

Deve mostrar algo como:
```
tesseract 5.x.x
```

## Passo 4: Configurar no Sistema ALPR

### Opção 1: Configurar no .env (RECOMENDADO)

Edite o arquivo `.env` e atualize a linha:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### Opção 2: Adicionar ao PATH do Windows

1. Abra "Variáveis de Ambiente" do Windows
2. Em "Variáveis do Sistema", encontre "Path"
3. Clique em "Editar"
4. Adicione: `C:\Program Files\Tesseract-OCR`
5. Clique OK
6. Reinicie o terminal

Então no `.env`:
```env
TESSERACT_CMD=tesseract
```

## Passo 5: Testar

Execute:

```bash
python teste_desktop_basic.py
```

**Antes** (com erro):
```
Erro ao configurar Tesseract: tesseract is not installed...
```

**Depois** (funcionando):
```
✓ Tesseract configurado
```

## Solução de Problemas

### Erro: "tesseract is not installed"

**Solução**: Verifique o caminho no `.env`:
1. Abra o Explorador de Arquivos
2. Navegue até `C:\Program Files\Tesseract-OCR`
3. Verifique se `tesseract.exe` existe
4. Copie o caminho completo para o `.env`

### Erro: "Failed to load language 'eng'"

**Solução**: Reinstale o Tesseract e marque "English" durante a instalação

## Próximo Passo

Após instalar o Tesseract, execute:

```bash
python processar_testes.py --tipo imagem
```

Os erros de Tesseract devem desaparecer e o OCR híbrido vai funcionar melhor!
