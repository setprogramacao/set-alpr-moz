"""
Interface Principal - Desktop Module ALPR UNIPIAGET
Interface gráfica Tkinter para captura e detecção de placas
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from PIL import Image, ImageTk
import threading
import time
from datetime import datetime
from typing import Optional
import logging

from ..core import PlateDetector, CameraManager, APIClient
from ..config import (
    WINDOW_TITLE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    PREVIEW_WIDTH,
    PREVIEW_HEIGHT,
    PROCESS_EVERY_N_FRAMES,
    DEFAULT_MOVEMENT_TYPE,
    AUTO_TOGGLE_MOVEMENT,
    SAVE_DETECTION_IMAGES,
)
from ..utils import converter_cv_para_pil, preprocessar_para_display
from shared.utils import salvar_imagem_deteccao, formatar_log_deteccao

logger = logging.getLogger(__name__)


class MainWindow:
    """
    Janela principal da aplicação Desktop
    """

    def __init__(self, root: tk.Tk):
        """Inicializa interface"""
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # Componentes
        self.detector = None
        self.camera = None
        self.api_client = None

        # Estado
        self.capturando = False
        self.tipo_movimento = DEFAULT_MOVEMENT_TYPE
        self.frame_count = 0
        self.deteccoes_count = 0
        self.thread_captura = None
        self.testando_imagens = False

        # UI Components
        self.preview_label = None
        self.log_text = None
        self.status_label = None
        self.btn_iniciar = None
        self.btn_pausar = None
        self.btn_parar_teste = None
        self.lbl_progresso_teste = None

        # Inicializa UI
        self.criar_interface()

        # Inicializa componentes
        self.inicializar_componentes()

        # Configura evento de fechamento
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        logger.info("MainWindow inicializada")

    def criar_interface(self):
        """Cria elementos da interface"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configura grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # ===== COLUNA ESQUERDA =====
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        # Preview de vídeo
        preview_frame = ttk.LabelFrame(left_frame, text="Preview", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.preview_label = ttk.Label(preview_frame, text="Aguardando inicialização...")
        self.preview_label.pack()

        # Informações da detecção
        info_frame = ttk.LabelFrame(left_frame, text="Última Detecção", padding="5")
        info_frame.pack(fill=tk.X, pady=(10, 0))

        self.lbl_placa = ttk.Label(info_frame, text="Placa: -", font=("Arial", 14, "bold"))
        self.lbl_placa.pack()

        self.lbl_confianca = ttk.Label(info_frame, text="Confiança: -")
        self.lbl_confianca.pack()

        self.lbl_status_veiculo = ttk.Label(info_frame, text="Status: -")
        self.lbl_status_veiculo.pack()

        # ===== COLUNA DIREITA =====
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.rowconfigure(2, weight=1)

        # Controles
        control_frame = ttk.LabelFrame(right_frame, text="Controles", padding="5")
        control_frame.pack(fill=tk.X)

        # Botões de controle
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.btn_iniciar = ttk.Button(
            btn_frame,
            text="▶ Iniciar Captura",
            command=self.iniciar_captura,
            width=20
        )
        self.btn_iniciar.pack(side=tk.LEFT, padx=5)

        self.btn_pausar = ttk.Button(
            btn_frame,
            text="⏸ Pausar",
            command=self.pausar_captura,
            state=tk.DISABLED,
            width=20
        )
        self.btn_pausar.pack(side=tk.LEFT, padx=5)

        # Tipo de movimento
        movimento_frame = ttk.Frame(control_frame)
        movimento_frame.pack(fill=tk.X, pady=5)

        ttk.Label(movimento_frame, text="Tipo de Movimento:").pack(side=tk.LEFT, padx=5)

        self.tipo_movimento_var = tk.StringVar(value=self.tipo_movimento)
        ttk.Radiobutton(
            movimento_frame,
            text="Entrada",
            variable=self.tipo_movimento_var,
            value="entrada",
            command=self.on_tipo_movimento_changed
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            movimento_frame,
            text="Saída",
            variable=self.tipo_movimento_var,
            value="saida",
            command=self.on_tipo_movimento_changed
        ).pack(side=tk.LEFT, padx=5)

        # Configurações
        config_frame = ttk.LabelFrame(right_frame, text="Configurações", padding="5")
        config_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            config_frame,
            text="Selecionar Fonte de Vídeo",
            command=self.selecionar_fonte
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            config_frame,
            text="Configurar API",
            command=self.configurar_api
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            config_frame,
            text="Ver Configurações",
            command=self.ver_configuracoes
        ).pack(fill=tk.X, pady=2)

        # Separador e botões de teste com imagens
        ttk.Separator(config_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(8, 4))

        ttk.Label(config_frame, text="Teste com Imagens:", font=("Arial", 9, "bold")).pack(anchor=tk.W)

        ttk.Button(
            config_frame,
            text="Testar Imagem Unica",
            command=self.testar_imagem_unica
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            config_frame,
            text="Testar Banco de Imagens",
            command=self.testar_banco_imagens
        ).pack(fill=tk.X, pady=2)

        self.btn_parar_teste = ttk.Button(
            config_frame,
            text="Parar Teste",
            command=self.parar_teste_imagens,
            state=tk.DISABLED
        )
        self.btn_parar_teste.pack(fill=tk.X, pady=2)

        # Estatísticas
        stats_frame = ttk.LabelFrame(right_frame, text="Estatísticas", padding="5")
        stats_frame.pack(fill=tk.X, pady=(10, 0))

        self.lbl_frames = ttk.Label(stats_frame, text="Frames processados: 0")
        self.lbl_frames.pack(anchor=tk.W)

        self.lbl_deteccoes = ttk.Label(stats_frame, text="Detecções: 0")
        self.lbl_deteccoes.pack(anchor=tk.W)

        self.lbl_api_status = ttk.Label(stats_frame, text="API: Desconectado", foreground="red")
        self.lbl_api_status.pack(anchor=tk.W)

        self.lbl_progresso_teste = ttk.Label(stats_frame, text="", foreground="blue")
        self.lbl_progresso_teste.pack(anchor=tk.W)

        # Log
        log_frame = ttk.LabelFrame(right_frame, text="Log de Atividades", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            width=50,
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Barra de status
        self.status_label = ttk.Label(
            self.root,
            text="Sistema pronto",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.grid(row=1, column=0, sticky=(tk.W, tk.E))

    def inicializar_componentes(self):
        """Inicializa detector, câmera e API"""
        self.adicionar_log("🔧 Inicializando componentes...")

        try:
            # Inicializa detector
            self.adicionar_log("📷 Carregando detector YOLO + OCR...")
            self.detector = PlateDetector()
            self.adicionar_log("✓ Detector carregado com sucesso")

            # Inicializa câmera
            self.adicionar_log("🎥 Inicializando câmera...")
            self.camera = CameraManager()
            if self.camera.abrir():
                self.adicionar_log("✓ Câmera inicializada")
            else:
                self.adicionar_log("✗ Erro ao abrir câmera", nivel="ERROR")

            # Inicializa API client
            self.adicionar_log("🌐 Conectando à API...")
            self.api_client = APIClient()
            if self.api_client.testar_conexao():
                self.adicionar_log("✓ API conectada")
                self.atualizar_status_api(True)
            else:
                self.adicionar_log("⚠ API não disponível (modo offline)", nivel="WARNING")
                self.atualizar_status_api(False)

            self.atualizar_status("Sistema pronto para captura")

        except Exception as e:
            self.adicionar_log(f"✗ Erro na inicialização: {e}", nivel="ERROR")
            messagebox.showerror("Erro", f"Erro ao inicializar componentes:\n{e}")

    def iniciar_captura(self):
        """Inicia captura e detecção"""
        if self.capturando:
            return

        self.capturando = True
        self.btn_iniciar.config(state=tk.DISABLED)
        self.btn_pausar.config(state=tk.NORMAL)

        self.adicionar_log("▶ Captura iniciada")
        self.atualizar_status("Capturando...")

        # Inicia thread de captura
        self.thread_captura = threading.Thread(target=self.loop_captura, daemon=True)
        self.thread_captura.start()

    def pausar_captura(self):
        """Pausa captura"""
        self.capturando = False
        self.btn_iniciar.config(state=tk.NORMAL)
        self.btn_pausar.config(state=tk.DISABLED)

        self.adicionar_log("⏸ Captura pausada")
        self.atualizar_status("Captura pausada")

    def loop_captura(self):
        """Loop principal de captura (roda em thread separada)"""
        frame_skip_count = 0

        while self.capturando:
            try:
                # Lê frame
                ret, frame = self.camera.ler_frame()

                if not ret or frame is None:
                    self.adicionar_log("✗ Erro ao ler frame", nivel="ERROR")
                    break

                self.frame_count += 1
                frame_skip_count += 1

                # Atualiza preview
                self.atualizar_preview(frame)

                # Processa apenas a cada N frames
                if frame_skip_count >= PROCESS_EVERY_N_FRAMES:
                    frame_skip_count = 0

                    # Detecta placas
                    deteccoes = self.detector.processar_frame(frame)

                    if deteccoes:
                        # Processa cada detecção
                        for det in deteccoes:
                            self.processar_deteccao(det, frame)

                    # Atualiza estatísticas
                    self.atualizar_estatisticas()

                time.sleep(0.01)  # Pequena pausa para não sobrecarregar

            except Exception as e:
                self.adicionar_log(f"✗ Erro no loop de captura: {e}", nivel="ERROR")
                break

        self.capturando = False

    def processar_deteccao(self, deteccao: dict, frame):
        """Processa uma detecção"""
        placa = deteccao["placa"]
        confianca = deteccao["confianca_ocr"]
        metodo = deteccao["metodo_ocr"]
        imagem_placa = deteccao.get("imagem_placa")

        self.deteccoes_count += 1

        # Atualiza display
        self.atualizar_info_deteccao(placa, confianca)

        # Salva imagem se habilitado
        if SAVE_DETECTION_IMAGES and imagem_placa is not None:
            salvar_imagem_deteccao(frame, placa)

        # Envia para API
        if self.api_client and self.api_client.esta_conectado():
            resposta = self.api_client.enviar_deteccao(
                placa=placa,
                tipo_movimento=self.tipo_movimento,
                confianca_ocr=confianca,
                metodo_ocr=metodo,
                imagem=imagem_placa,
                resultados_ocr=deteccao.get("resultados_ocr_detalhados")
            )

            if resposta:
                cadastrado = resposta.get("veiculo_cadastrado", False)
                mensagem = resposta.get("mensagem", "")

                # Log formatado
                log_msg = formatar_log_deteccao(placa, self.tipo_movimento, confianca, metodo, cadastrado)
                self.adicionar_log(log_msg)

                # Atualiza status veículo
                if cadastrado:
                    veiculo = resposta.get("veiculo")
                    if veiculo:
                        proprietario = veiculo.get("proprietario", {})
                        self.atualizar_status_veiculo(True, proprietario.get("nome", ""))
                else:
                    self.atualizar_status_veiculo(False)

                # Auto toggle movimento
                if AUTO_TOGGLE_MOVEMENT and not resposta.get("duplicata", False):
                    self.alternar_tipo_movimento()
            else:
                self.adicionar_log(f"⚠ Detecção não enviada: {placa}", nivel="WARNING")
        else:
            self.adicionar_log(f"🚗 {placa} | {confianca:.0%} | MODO OFFLINE")

    def atualizar_preview(self, frame):
        """Atualiza preview de vídeo"""
        try:
            # Redimensiona para preview
            frame_display = preprocessar_para_display(frame, PREVIEW_WIDTH, PREVIEW_HEIGHT)

            # Converte para PhotoImage
            photo = converter_cv_para_pil(frame_display)

            # Atualiza label (deve ser feito na main thread)
            self.root.after(0, self._atualizar_preview_ui, photo)

        except Exception as e:
            logger.error(f"Erro ao atualizar preview: {e}")

    def _atualizar_preview_ui(self, photo):
        """Atualiza UI do preview (main thread)"""
        self.preview_label.config(image=photo)
        self.preview_label.image = photo  # Mantém referência

    def atualizar_info_deteccao(self, placa: str, confianca: float):
        """Atualiza informações da última detecção"""
        self.root.after(0, lambda: self.lbl_placa.config(text=f"Placa: {placa}"))
        self.root.after(0, lambda: self.lbl_confianca.config(text=f"Confiança: {confianca:.0%}"))

    def atualizar_status_veiculo(self, cadastrado: bool, proprietario: str = ""):
        """Atualiza status do veículo"""
        if cadastrado:
            texto = f"✓ Cadastrado - {proprietario}"
            cor = "green"
        else:
            texto = "✗ Não Cadastrado"
            cor = "red"

        self.root.after(0, lambda: self.lbl_status_veiculo.config(text=texto, foreground=cor))

    def atualizar_estatisticas(self):
        """Atualiza estatísticas"""
        self.root.after(0, lambda: self.lbl_frames.config(text=f"Frames processados: {self.frame_count}"))
        self.root.after(0, lambda: self.lbl_deteccoes.config(text=f"Detecções: {self.deteccoes_count}"))

    def atualizar_status_api(self, conectado: bool):
        """Atualiza status da API"""
        if conectado:
            texto = "API: ✓ Conectado"
            cor = "green"
        else:
            texto = "API: ✗ Desconectado"
            cor = "red"

        self.root.after(0, lambda: self.lbl_api_status.config(text=texto, foreground=cor))

    def adicionar_log(self, mensagem: str, nivel: str = "INFO"):
        """Adiciona mensagem ao log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_linha = f"[{timestamp}] {mensagem}\n"

        def _add():
            self.log_text.insert(tk.END, log_linha)
            self.log_text.see(tk.END)  # Auto-scroll

        self.root.after(0, _add)

        # Também loga no logger
        if nivel == "ERROR":
            logger.error(mensagem)
        elif nivel == "WARNING":
            logger.warning(mensagem)
        else:
            logger.info(mensagem)

    def atualizar_status(self, mensagem: str):
        """Atualiza barra de status"""
        self.root.after(0, lambda: self.status_label.config(text=mensagem))

    def on_tipo_movimento_changed(self):
        """Callback quando tipo de movimento muda"""
        self.tipo_movimento = self.tipo_movimento_var.get()
        self.adicionar_log(f"📝 Tipo de movimento alterado: {self.tipo_movimento.upper()}")

    def alternar_tipo_movimento(self):
        """Alterna automaticamente tipo de movimento"""
        novo_tipo = "saida" if self.tipo_movimento == "entrada" else "entrada"
        self.tipo_movimento = novo_tipo
        self.root.after(0, lambda: self.tipo_movimento_var.set(novo_tipo))

    def selecionar_fonte(self):
        """Abre diálogo para selecionar fonte de vídeo"""
        filepath = filedialog.askopenfilename(
            title="Selecionar Vídeo",
            filetypes=[
                ("Vídeos", "*.mp4 *.avi *.mov"),
                ("Imagens", "*.jpg *.jpeg *.png"),
                ("Todos", "*.*")
            ]
        )

        if filepath:
            # Reinicializa câmera com nova fonte
            if self.camera:
                self.camera.fechar()

            self.camera = CameraManager(filepath)
            if self.camera.abrir():
                self.adicionar_log(f"✓ Nova fonte selecionada: {filepath}")
            else:
                self.adicionar_log(f"✗ Erro ao abrir: {filepath}", nivel="ERROR")

    def configurar_api(self):
        """Abre diálogo para configurar API"""
        # TODO: Implementar diálogo de configuração
        messagebox.showinfo("Configurar API", "Funcionalidade em desenvolvimento")

    def ver_configuracoes(self):
        """Exibe configurações atuais"""
        from ..config import obter_config_display

        config = obter_config_display()

        # Formata para exibição
        texto = "=== CONFIGURAÇÕES ATUAIS ===\n\n"
        for secao, valores in config.items():
            texto += f"{secao}:\n"
            for chave, valor in valores.items():
                texto += f"  • {chave}: {valor}\n"
            texto += "\n"

        messagebox.showinfo("Configurações", texto)

    # =========================================================================
    # TESTES COM IMAGENS
    # =========================================================================

    def testar_imagem_unica(self):
        """Testa deteccao em uma imagem selecionada pelo utilizador"""
        if not self.detector:
            messagebox.showerror("Erro", "Detector nao inicializado")
            return

        filepath = filedialog.askopenfilename(
            title="Selecionar Imagem para Teste",
            filetypes=[
                ("Imagens", "*.jpg *.jpeg *.png *.bmp"),
                ("Todos os arquivos", "*.*")
            ]
        )

        if filepath:
            from pathlib import Path as _Path
            self.adicionar_log(f"Testando imagem: {_Path(filepath).name}")
            self._processar_imagem_arquivo(filepath)

    def testar_banco_imagens(self):
        """Testa deteccao em uma pasta ou conjunto de imagens"""
        if not self.detector:
            messagebox.showerror("Erro", "Detector nao inicializado")
            return

        if self.testando_imagens:
            messagebox.showwarning("Aviso", "Ja existe um teste em andamento. Clique em 'Parar Teste' primeiro.")
            return

        # Pergunta se quer selecionar pasta ou arquivos individuais
        resposta = messagebox.askyesnocancel(
            "Selecionar Imagens",
            "Como deseja selecionar as imagens?\n\n"
            "SIM = Selecionar uma PASTA inteira\n"
            "NAO = Selecionar imagens individualmente\n"
            "CANCELAR = Abortar"
        )

        if resposta is None:
            return

        image_files = []

        if resposta:  # Pasta inteira
            from pathlib import Path as _Path
            pasta = filedialog.askdirectory(title="Selecionar Pasta com Imagens")
            if pasta:
                extensoes = {'.jpg', '.jpeg', '.png', '.bmp'}
                image_files = sorted([
                    str(p) for p in _Path(pasta).iterdir()
                    if p.suffix.lower() in extensoes
                ])
        else:  # Arquivos individuais
            files = filedialog.askopenfilenames(
                title="Selecionar Imagens",
                filetypes=[
                    ("Imagens", "*.jpg *.jpeg *.png *.bmp"),
                    ("Todos os arquivos", "*.*")
                ]
            )
            image_files = list(files)

        if not image_files:
            self.adicionar_log("Nenhuma imagem selecionada", nivel="WARNING")
            return

        self.adicionar_log(f"Iniciando teste com {len(image_files)} imagem(ns)...")
        self.testando_imagens = True
        self.btn_parar_teste.config(state=tk.NORMAL)

        thread = threading.Thread(
            target=self._executar_banco_imagens,
            args=(image_files,),
            daemon=True
        )
        thread.start()

    def parar_teste_imagens(self):
        """Para o teste de banco de imagens em andamento"""
        self.testando_imagens = False
        self.adicionar_log("Teste de imagens interrompido pelo utilizador")
        self.btn_parar_teste.config(state=tk.DISABLED)
        self.root.after(0, lambda: self.lbl_progresso_teste.config(text=""))

    def _processar_imagem_arquivo(self, filepath: str):
        """Carrega e processa uma unica imagem para deteccao"""
        import cv2 as _cv2
        from pathlib import Path as _Path

        frame = _cv2.imread(filepath)
        if frame is None:
            self.adicionar_log(f"Erro ao carregar imagem: {filepath}", nivel="ERROR")
            return

        # Mostra a imagem no preview
        self.atualizar_preview(frame)

        # Roda o detector
        deteccoes = self.detector.processar_frame(frame)

        nome = _Path(filepath).name
        if deteccoes:
            for det in deteccoes:
                self.processar_deteccao(det, frame)
            self.atualizar_estatisticas()
        else:
            self.adicionar_log(f"Nenhuma placa detectada em: {nome}", nivel="WARNING")

    def _executar_banco_imagens(self, image_files: list):
        """Processa lista de imagens em sequencia (roda em thread separada)"""
        import cv2 as _cv2
        from pathlib import Path as _Path

        total = len(image_files)
        processadas = 0
        total_deteccoes = 0

        for i, filepath in enumerate(image_files):
            if not self.testando_imagens:
                break

            nome = _Path(filepath).name

            # Atualiza progresso na UI
            progresso_txt = f"Teste: {i + 1}/{total} - {nome}"
            self.root.after(0, lambda t=progresso_txt: self.lbl_progresso_teste.config(text=t))
            self.atualizar_status(f"Processando imagem {i + 1} de {total}...")

            frame = _cv2.imread(filepath)
            if frame is None:
                self.adicionar_log(f"Erro ao carregar: {nome}", nivel="ERROR")
                continue

            # Atualiza preview
            self.atualizar_preview(frame)

            # Detecta placas
            deteccoes = self.detector.processar_frame(frame)
            processadas += 1

            if deteccoes:
                total_deteccoes += len(deteccoes)
                for det in deteccoes:
                    self.processar_deteccao(det, frame)
            else:
                self.adicionar_log(f"  Sem placa: {nome}")

            self.atualizar_estatisticas()

            # Pausa breve para a interface respirar e o utilizador ver o resultado
            time.sleep(0.5)

        # Finaliza
        self.testando_imagens = False
        self.root.after(0, lambda: self.btn_parar_teste.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.lbl_progresso_teste.config(text=""))

        resumo = f"Teste concluido: {processadas}/{total} imagens | {total_deteccoes} deteccao(oes)"
        self.adicionar_log(f"{resumo}")
        self.atualizar_status(resumo)

    def on_closing(self):
        """Callback ao fechar janela"""
        if self.capturando or self.testando_imagens:
            if messagebox.askokcancel("Sair", "Operacao em andamento. Deseja realmente sair?"):
                self.capturando = False
                self.testando_imagens = False
                time.sleep(0.5)  # Aguarda threads finalizarem
                self.fechar()
        else:
            self.fechar()

    def fechar(self):
        """Fecha aplicação e libera recursos"""
        self.adicionar_log("🛑 Encerrando aplicação...")

        if self.camera:
            self.camera.fechar()

        self.root.quit()
        self.root.destroy()
