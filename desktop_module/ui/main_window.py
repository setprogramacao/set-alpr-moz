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

from ..core import PlateDetector, CameraManager, APIClient, PLCController
from ..config import (
    WINDOW_TITLE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    PREVIEW_WIDTH,
    PREVIEW_HEIGHT,
    PROCESS_EVERY_N_FRAMES,
    SAVE_DETECTION_IMAGES,
    API_HOST,
    API_TIMEOUT,
    PLC_HABILITADO,
    PLC_HOST,
    PLC_PORT,
)
from ..utils import converter_cv_para_pil, preprocessar_para_display
from shared.utils import salvar_imagem_deteccao

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
        self.plc_controller = None

        # Estado
        self.capturando = False
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
        self.btn_recarregar = None
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
            width=18
        )
        self.btn_iniciar.pack(side=tk.LEFT, padx=5)

        self.btn_pausar = ttk.Button(
            btn_frame,
            text="⏸ Pausar",
            command=self.pausar_captura,
            state=tk.DISABLED,
            width=12
        )
        self.btn_pausar.pack(side=tk.LEFT, padx=5)

        self.btn_recarregar = ttk.Button(
            btn_frame,
            text="↺ Recarregar",
            command=self.recarregar_sistema,
            width=14
        )
        self.btn_recarregar.pack(side=tk.LEFT, padx=5)

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

        ttk.Button(
            config_frame,
            text="Configurar PLC / Cancela",
            command=self.configurar_plc
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

        self.lbl_plc_status = ttk.Label(stats_frame, text="Cancela: ○ Desconectado", foreground="gray")
        self.lbl_plc_status.pack(anchor=tk.W)

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

            # Inicializa PLC controller
            if PLC_HABILITADO:
                self.adicionar_log("🔌 Conectando ao PLC...")
                self.plc_controller = PLCController(
                    callback_status=self._on_plc_status,
                    callback_veiculo_detectado=self._on_veiculo_no_sensor
                )
                if self.plc_controller.conectar():
                    self.adicionar_log("✓ PLC conectado — cancela pronta")
                    self.atualizar_status_plc("fechada")
                else:
                    self.adicionar_log("⚠ PLC não conectado (inicie o simulador)", nivel="WARNING")
                    self.atualizar_status_plc("erro")
            else:
                self.adicionar_log("○ Integração PLC desativada (PLC_HABILITADO=False)")

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

        # Envia para API (tipo_movimento é determinado automaticamente pelo servidor)
        if self.api_client and self.api_client.esta_conectado():
            resposta = self.api_client.enviar_deteccao(
                placa=placa,
                tipo_movimento="entrada",  # valor ignorado pelo servidor; a API decide
                confianca_ocr=confianca,
                metodo_ocr=metodo,
                imagem=imagem_placa,
                resultados_ocr=deteccao.get("resultados_ocr_detalhados")
            )

            if resposta:
                cadastrado = resposta.get("veiculo_cadastrado", False)
                eh_duplicata = resposta.get("duplicata", False)
                mensagem_servidor = resposta.get("mensagem", "")

                # Log com mensagem real do servidor (contém [ENTRADA]/[SAÍDA] e nome)
                icone = "⚠" if eh_duplicata else ("✓" if cadastrado else "🚗")
                self.adicionar_log(f"{icone} {placa} | {confianca:.0%} | {metodo} | {mensagem_servidor}")

                # Atualiza status veículo
                if cadastrado:
                    veiculo = resposta.get("veiculo")
                    if veiculo:
                        proprietario = veiculo.get("proprietario", {})
                        self.atualizar_status_veiculo(True, proprietario.get("nome", ""))
                else:
                    self.atualizar_status_veiculo(False)

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

    def recarregar_sistema(self):
        """Para a captura atual e reinicializa todos os componentes"""
        # Para captura se estiver rodando
        if self.capturando:
            self.capturando = False
            self.btn_iniciar.config(state=tk.NORMAL)
            self.btn_pausar.config(state=tk.DISABLED)

        if self.testando_imagens:
            self.testando_imagens = False
            self.btn_parar_teste.config(state=tk.DISABLED)
            self.root.after(0, lambda: self.lbl_progresso_teste.config(text=""))

        # Fecha câmera atual
        if self.camera:
            try:
                self.camera.fechar()
            except Exception:
                pass

        # Desconecta PLC (será reconectado na reinicialização)
        if self.plc_controller:
            try:
                self.plc_controller.desconectar()
            except Exception:
                pass

        self.adicionar_log("↺ Recarregando sistema...")
        self.atualizar_status("Recarregando...")

        # Reinicializa em thread para não travar a UI durante o carregamento do YOLO/OCR
        def _recarregar():
            self.inicializar_componentes()

        threading.Thread(target=_recarregar, daemon=True).start()

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
        """Abre diálogo para configurar a URL e timeout da API"""
        from ..config import BASE_DIR

        dialog = tk.Toplevel(self.root)
        dialog.title("Configurar API")
        dialog.geometry("420x230")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Valores actuais
        url_atual = self.api_client.api_url if self.api_client else ""
        # Extrai o host (remove o endpoint /api/v1/registros/deteccao)
        try:
            parts = url_atual.split("/")
            host_atual = f"{parts[0]}//{parts[2]}"
        except Exception:
            host_atual = f"http://{API_HOST}" if not API_HOST.startswith("http") else API_HOST

        timeout_atual = str(self.api_client.timeout if self.api_client else API_TIMEOUT)

        frame = ttk.Frame(dialog, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)

        # Host
        ttk.Label(frame, text="URL da API (host):").grid(row=0, column=0, sticky=tk.W, pady=4)
        entry_host = ttk.Entry(frame, width=36)
        entry_host.insert(0, host_atual)
        entry_host.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(8, 0), pady=4)

        # Timeout
        ttk.Label(frame, text="Timeout (segundos):").grid(row=1, column=0, sticky=tk.W, pady=4)
        entry_timeout = ttk.Entry(frame, width=10)
        entry_timeout.insert(0, timeout_atual)
        entry_timeout.grid(row=1, column=1, sticky=tk.W, padx=(8, 0), pady=4)

        # Status de conexão
        lbl_status = ttk.Label(frame, text="", foreground="gray")
        lbl_status.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=4)

        def testar_conexao():
            host = entry_host.get().strip().rstrip("/")
            if not host.startswith("http"):
                lbl_status.config(text="✗ URL deve começar com http:// ou https://", foreground="red")
                return
            lbl_status.config(text="Testando conexão...", foreground="gray")
            dialog.update()
            try:
                import requests as _req
                resp = _req.get(f"{host}/health", timeout=5)
                if resp.status_code == 200:
                    lbl_status.config(text="✓ Conexão bem-sucedida!", foreground="green")
                else:
                    lbl_status.config(text=f"✗ Servidor respondeu: {resp.status_code}", foreground="orange")
            except Exception as e:
                lbl_status.config(text=f"✗ Falha: {type(e).__name__}", foreground="red")

        def salvar():
            host = entry_host.get().strip().rstrip("/")
            if not host.startswith("http"):
                lbl_status.config(text="✗ URL inválida. Use http:// ou https://", foreground="red")
                return
            try:
                timeout = int(entry_timeout.get().strip())
            except ValueError:
                lbl_status.config(text="✗ Timeout deve ser um número inteiro", foreground="red")
                return

            novo_endpoint = f"{host}/api/v1/registros/deteccao"

            # Actualiza o cliente API em memória
            if self.api_client:
                self.api_client.api_url = novo_endpoint
                self.api_client.timeout = timeout

            # Persiste no .env
            env_path = BASE_DIR / ".env"
            try:
                linhas = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
                novas = []
                keys_written = set()
                for linha in linhas:
                    if linha.startswith("API_HOST="):
                        novas.append(f"API_HOST={host}")
                        keys_written.add("API_HOST")
                    elif linha.startswith("API_TIMEOUT="):
                        novas.append(f"API_TIMEOUT={timeout}")
                        keys_written.add("API_TIMEOUT")
                    else:
                        novas.append(linha)
                if "API_HOST" not in keys_written:
                    novas.append(f"API_HOST={host}")
                if "API_TIMEOUT" not in keys_written:
                    novas.append(f"API_TIMEOUT={timeout}")
                env_path.write_text("\n".join(novas) + "\n", encoding="utf-8")
            except Exception as e:
                self.adicionar_log(f"⚠ Não foi possível salvar .env: {e}", nivel="WARNING")

            self.adicionar_log(f"✓ API configurada: {host} | timeout={timeout}s")
            dialog.destroy()

        # Botões
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(8, 0))

        ttk.Button(btn_frame, text="Testar Conexão", command=testar_conexao, width=16).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Salvar", command=salvar, width=10).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=4)

        frame.columnconfigure(1, weight=1)

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

    def atualizar_status_plc(self, status: str):
        """Atualiza label de status da cancela na UI."""
        mapa = {
            "aberta": ("Cancela: ↑ ABERTA", "green"),
            "fechada": ("Cancela: ↓ Fechada", "gray"),
            "erro": ("Cancela: ✗ Erro PLC", "red"),
        }
        texto, cor = mapa.get(status, ("Cancela: ○ Desconectado", "gray"))
        self.root.after(0, lambda: self.lbl_plc_status.config(text=texto, foreground=cor))

    def _on_plc_status(self, status: str):
        """Callback chamado pelo PLCController (thread secundária) quando o status muda."""
        self.atualizar_status_plc(status)

    def _on_veiculo_no_sensor(self):
        """
        Callback chamado pelo PLCController quando o sensor de laço deteta um veículo.
        Captura o frame atual da câmara e processa para registo de placa.
        """
        if not self.camera or not self.detector:
            return

        try:
            ret, frame = self.camera.ler_frame()
            if not ret or frame is None:
                self.adicionar_log("⚠ Sensor ativo mas câmara não disponível", nivel="WARNING")
                return

            self.atualizar_preview(frame)
            deteccoes = self.detector.processar_frame(frame)

            if deteccoes:
                for det in deteccoes:
                    self.processar_deteccao(det, frame)
                self.atualizar_estatisticas()
            else:
                self.adicionar_log("Sensor: veículo detectado — placa não lida neste frame", nivel="WARNING")

        except Exception as e:
            logger.error(f"Erro no callback de sensor: {e}")

    def configurar_plc(self):
        """Abre diálogo para configurar e testar a ligação ao PLC."""
        from ..config import BASE_DIR

        dialog = tk.Toplevel(self.root)
        dialog.title("Configurar PLC / Cancela")
        dialog.geometry("440x280")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)

        # IP
        ttk.Label(frame, text="IP do PLC:").grid(row=0, column=0, sticky=tk.W, pady=4)
        entry_host = ttk.Entry(frame, width=26)
        entry_host.insert(0, self.plc_controller.host if self.plc_controller else PLC_HOST)
        entry_host.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(8, 0), pady=4)

        # Porta
        ttk.Label(frame, text="Porta Modbus TCP:").grid(row=1, column=0, sticky=tk.W, pady=4)
        entry_port = ttk.Entry(frame, width=10)
        entry_port.insert(0, str(self.plc_controller.port if self.plc_controller else PLC_PORT))
        entry_port.grid(row=1, column=1, sticky=tk.W, padx=(8, 0), pady=4)

        # Mensagem de status
        lbl_status = ttk.Label(frame, text="", foreground="gray")
        lbl_status.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=4)

        def testar_conexao():
            host = entry_host.get().strip()
            try:
                port = int(entry_port.get().strip())
            except ValueError:
                lbl_status.config(text="✗ Porta inválida", foreground="red")
                return
            lbl_status.config(text="Conectando...", foreground="gray")
            dialog.update()
            tmp = PLCController(host=host, port=port)
            if tmp.conectar():
                tmp.desconectar()
                lbl_status.config(text="✓ PLC acessível!", foreground="green")
            else:
                lbl_status.config(text="✗ Não foi possível conectar", foreground="red")

        def abrir_manual():
            if self.plc_controller and self.plc_controller.esta_conectado():
                threading.Thread(target=self.plc_controller.abrir_cancela, daemon=True).start()
                lbl_status.config(text="↑ Comando enviado: abrir cancela", foreground="blue")
            else:
                lbl_status.config(text="✗ PLC não conectado", foreground="red")

        def fechar_manual():
            if self.plc_controller and self.plc_controller.esta_conectado():
                threading.Thread(target=self.plc_controller.fechar_cancela, daemon=True).start()
                lbl_status.config(text="↓ Comando enviado: fechar cancela", foreground="gray")
            else:
                lbl_status.config(text="✗ PLC não conectado", foreground="red")

        def salvar():
            host = entry_host.get().strip()
            try:
                port = int(entry_port.get().strip())
            except ValueError:
                lbl_status.config(text="✗ Porta inválida", foreground="red")
                return

            # Reconecta com novos parâmetros
            if self.plc_controller:
                self.plc_controller.desconectar()

            self.plc_controller = PLCController(
                host=host, port=port,
                callback_status=self._on_plc_status,
                callback_veiculo_detectado=self._on_veiculo_no_sensor
            )
            if self.plc_controller.conectar():
                self.adicionar_log(f"✓ PLC reconfigurado: {host}:{port}")
                self.atualizar_status_plc("fechada")
            else:
                self.adicionar_log(f"⚠ PLC configurado mas não conectado: {host}:{port}", nivel="WARNING")
                self.atualizar_status_plc("erro")

            # Persiste no .env
            env_path = BASE_DIR / ".env"
            try:
                linhas = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
                novas = []
                keys_written = set()
                for linha in linhas:
                    if linha.startswith("PLC_HOST="):
                        novas.append(f"PLC_HOST={host}")
                        keys_written.add("PLC_HOST")
                    elif linha.startswith("PLC_PORT="):
                        novas.append(f"PLC_PORT={port}")
                        keys_written.add("PLC_PORT")
                    else:
                        novas.append(linha)
                if "PLC_HOST" not in keys_written:
                    novas.append(f"PLC_HOST={host}")
                if "PLC_PORT" not in keys_written:
                    novas.append(f"PLC_PORT={port}")
                env_path.write_text("\n".join(novas) + "\n", encoding="utf-8")
            except Exception as e:
                self.adicionar_log(f"⚠ Não foi possível salvar .env: {e}", nivel="WARNING")

            dialog.destroy()

        # Linha de botões 1 — testes manuais
        btn_frame1 = ttk.Frame(frame)
        btn_frame1.grid(row=3, column=0, columnspan=2, pady=(4, 0))
        ttk.Button(btn_frame1, text="Testar Conexão", command=testar_conexao, width=16).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame1, text="↑ Abrir", command=abrir_manual, width=10).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame1, text="↓ Fechar", command=fechar_manual, width=10).pack(side=tk.LEFT, padx=3)

        # Linha de botões 2 — salvar/cancelar
        btn_frame2 = ttk.Frame(frame)
        btn_frame2.grid(row=4, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(btn_frame2, text="Salvar e Reconectar", command=salvar, width=20).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame2, text="Cancelar", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=3)

        frame.columnconfigure(1, weight=1)

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

        if self.plc_controller:
            self.plc_controller.desconectar()

        self.root.quit()
        self.root.destroy()
