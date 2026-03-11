"""
Interface Principal - Desktop Module ALPR UNIPIAGET
UI moderna com CustomTkinter — suporte a tema claro/escuro
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
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

# ── Paleta de cores ───────────────────────────────────────────────────────────
CLR_PRIMARY   = "#667eea"
CLR_PRIMARY_H = "#5a6fd6"
CLR_SUCCESS   = "#10b981"
CLR_SUCCESS_H = "#059669"
CLR_DANGER    = "#ef4444"
CLR_DANGER_H  = "#dc2626"
CLR_WARNING   = "#f59e0b"
CLR_WARNING_H = "#d97706"
CLR_INFO      = "#3b82f6"
CLR_MUTED     = "#6b7280"
CLR_TEAL      = "#0d9488"
CLR_TEAL_H    = "#0f766e"

FONT_SMALL = ("Segoe UI", 11)
FONT_UI    = ("Segoe UI", 12)
FONT_BOLD  = ("Segoe UI", 12, "bold")
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_PLACA = ("Segoe UI", 28, "bold")
FONT_GATE  = ("Segoe UI", 15, "bold")
FONT_MONO  = ("Consolas", 11)


class MainWindow:
    """Janela principal da aplicação Desktop ALPR."""

    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(1000, 680)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self._tema_atual = "dark"

        # Componentes de negócio
        self.detector: Optional[PlateDetector] = None
        self.camera: Optional[CameraManager] = None
        self.api_client: Optional[APIClient] = None
        self.plc_controller: Optional[PLCController] = None

        # Estado
        self.capturando = False
        self.frame_count = 0
        self.deteccoes_count = 0
        self.thread_captura = None
        self.testando_imagens = False

        # Referências de UI
        self.preview_label = None
        self.log_text = None
        self.status_label = None
        self.btn_iniciar = None
        self.btn_pausar = None
        self.btn_recarregar = None
        self.btn_parar_teste = None
        self.lbl_progresso_teste = None

        # Cancela
        self._gate_dot = None
        self.lbl_gate_estado = None
        self.lbl_gate_sub = None
        self.btn_abrir_cancela = None
        self.btn_fechar_cancela = None

        # Pills e stats
        self._pill_api_dot = None
        self._pill_plc_dot = None
        self._lbl_hora = None
        self._btn_tema = None
        self._stat_frames = None
        self._stat_detec = None
        self._stat_api_lbl = None
        self._stat_plc_lbl = None

        # Compat legado (não visível)
        self.lbl_plc_status = None

        self.criar_interface()
        threading.Thread(target=self.inicializar_componentes, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._tick_hora()
        logger.info("MainWindow inicializada")

    # =========================================================================
    # INTERFACE
    # =========================================================================

    def criar_interface(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        self._criar_header()
        self._criar_corpo()
        self._criar_statusbar()

    # ── Header ────────────────────────────────────────────────────────────────

    def _criar_header(self):
        header = ctk.CTkFrame(self.root, fg_color="#1e293b", corner_radius=0, height=50)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkLabel(header, text="ALPR", text_color=CLR_PRIMARY,
                     font=("Segoe UI", 14, "bold")).pack(side="left", padx=(16, 0))
        ctk.CTkLabel(header, text=" UNIPIAGET", text_color="white",
                     font=("Segoe UI", 13)).pack(side="left")
        ctk.CTkLabel(header, text="  ·  Módulo Desktop", text_color="#94a3b8",
                     font=FONT_SMALL).pack(side="left")

        # Relógio
        self._lbl_hora = ctk.CTkLabel(header, text="", text_color="#64748b", font=FONT_SMALL)
        self._lbl_hora.pack(side="right", padx=16)

        # Botão alternar tema
        self._btn_tema = ctk.CTkButton(
            header, text="☀", width=32, height=28,
            fg_color="transparent", hover_color="#334155",
            text_color="#94a3b8", font=("Segoe UI", 14),
            command=self._toggle_tema
        )
        self._btn_tema.pack(side="right", padx=(0, 6))

        # Pills de status
        self._pill_plc_dot, _ = self._criar_pill(header, "PLC")
        self._pill_api_dot, _ = self._criar_pill(header, "API")

    def _criar_pill(self, parent, label: str):
        frame = ctk.CTkFrame(parent, fg_color="#0f172a", corner_radius=6)
        frame.pack(side="right", padx=(0, 6))
        dot = ctk.CTkLabel(frame, text="●", text_color=CLR_MUTED, font=("Segoe UI", 9))
        dot.pack(side="left", padx=(8, 2), pady=4)
        ctk.CTkLabel(frame, text=label, text_color="#94a3b8",
                     font=FONT_SMALL).pack(side="left", padx=(0, 8), pady=4)
        return dot, frame

    def _toggle_tema(self):
        if self._tema_atual == "dark":
            ctk.set_appearance_mode("light")
            self._tema_atual = "light"
            self._btn_tema.configure(text="🌙")
        else:
            ctk.set_appearance_mode("dark")
            self._tema_atual = "dark"
            self._btn_tema.configure(text="☀")

    # ── Corpo ─────────────────────────────────────────────────────────────────

    def _criar_corpo(self):
        body = ctk.CTkFrame(self.root, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._criar_coluna_esquerda(body)
        self._criar_coluna_direita(body)

    def _criar_coluna_esquerda(self, parent):
        col = ctk.CTkFrame(parent, fg_color="transparent")
        col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        col.grid_rowconfigure(0, weight=1)
        col.grid_columnconfigure(0, weight=1)

        # ── Preview de câmara ─────────────────────────────────────────────────
        card_prev = ctk.CTkFrame(col, corner_radius=8)
        card_prev.grid(row=0, column=0, sticky="nsew")
        card_prev.grid_rowconfigure(1, weight=1)
        card_prev.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card_prev, text="Câmara", font=FONT_SMALL,
                     text_color=CLR_MUTED).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 0))

        preview_bg = ctk.CTkFrame(card_prev, fg_color="#0a0a0a", corner_radius=6)
        preview_bg.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 12))
        preview_bg.grid_rowconfigure(0, weight=1)
        preview_bg.grid_columnconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(
            preview_bg, text="A aguardar inicialização...",
            text_color="#4b5563", font=FONT_UI
        )
        self.preview_label.grid(row=0, column=0, sticky="nsew")

        # ── Última deteção ────────────────────────────────────────────────────
        card_det = ctk.CTkFrame(col, corner_radius=8)
        card_det.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        ctk.CTkLabel(card_det, text="Última Deteção", font=FONT_SMALL,
                     text_color=CLR_MUTED).pack(anchor="w", padx=12, pady=(10, 0))

        inner_det = ctk.CTkFrame(card_det, fg_color="transparent")
        inner_det.pack(fill="x", padx=12, pady=(4, 12))

        row1 = ctk.CTkFrame(inner_det, fg_color="transparent")
        row1.pack(fill="x")

        self.lbl_placa = ctk.CTkLabel(row1, text="—", font=FONT_PLACA)
        self.lbl_placa.pack(side="left")

        conf_frame = ctk.CTkFrame(row1, fg_color="transparent")
        conf_frame.pack(side="right", pady=4)
        self.lbl_confianca = ctk.CTkLabel(conf_frame, text="—", font=FONT_SMALL,
                                           text_color=CLR_MUTED)
        self.lbl_confianca.pack(anchor="e")
        self._conf_bar = ctk.CTkProgressBar(conf_frame, width=120, height=6,
                                             progress_color=CLR_SUCCESS)
        self._conf_bar.set(0)
        self._conf_bar.pack(anchor="e", pady=(2, 0))

        self.lbl_status_veiculo = ctk.CTkLabel(inner_det, text="", font=FONT_SMALL,
                                                text_color=CLR_MUTED)
        self.lbl_status_veiculo.pack(anchor="w", pady=(4, 0))

    def _criar_coluna_direita(self, parent):
        col = ctk.CTkFrame(parent, fg_color="transparent")
        col.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        col.grid_columnconfigure(0, weight=1)
        col.grid_rowconfigure(4, weight=1)

        self._criar_painel_cancela(col)
        self._criar_painel_captura(col)
        self._criar_painel_stats(col)
        self._criar_painel_acoes(col)
        self._criar_painel_log(col)

    # ── Painel CANCELA ────────────────────────────────────────────────────────

    def _criar_painel_cancela(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(card, text="Controlo da Cancela", font=FONT_SMALL,
                     text_color=CLR_MUTED).pack(anchor="w", padx=12, pady=(10, 0))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(4, 12))

        # Linha de estado
        status_row = ctk.CTkFrame(inner, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 2))

        self._gate_dot = ctk.CTkLabel(status_row, text="●", font=("Segoe UI", 18),
                                       text_color=CLR_MUTED)
        self._gate_dot.pack(side="left")

        self.lbl_gate_estado = ctk.CTkLabel(status_row, text="DESCONECTADO",
                                             font=FONT_GATE, text_color=CLR_MUTED)
        self.lbl_gate_estado.pack(side="left", padx=8)

        self.lbl_gate_sub = ctk.CTkLabel(inner, text="PLC não conectado",
                                          font=FONT_SMALL, text_color=CLR_MUTED)
        self.lbl_gate_sub.pack(anchor="w", pady=(0, 8))

        # Botões manuais
        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(fill="x")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.btn_abrir_cancela = ctk.CTkButton(
            btn_row, text="↑  ABRIR", command=self._cmd_abrir_cancela,
            fg_color=CLR_TEAL, hover_color=CLR_TEAL_H,
            font=FONT_BOLD, height=40, state="disabled"
        )
        self.btn_abrir_cancela.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.btn_fechar_cancela = ctk.CTkButton(
            btn_row, text="↓  FECHAR", command=self._cmd_fechar_cancela,
            fg_color=CLR_DANGER, hover_color=CLR_DANGER_H,
            font=FONT_BOLD, height=40, state="disabled"
        )
        self.btn_fechar_cancela.grid(row=0, column=1, sticky="ew")

    # ── Painel CAPTURA ────────────────────────────────────────────────────────

    def _criar_painel_captura(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        ctk.CTkLabel(card, text="Captura", font=FONT_SMALL,
                     text_color=CLR_MUTED).pack(anchor="w", padx=12, pady=(10, 0))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(4, 12))

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x")

        self.btn_iniciar = ctk.CTkButton(
            row, text="▶  Iniciar", command=self.iniciar_captura,
            fg_color=CLR_SUCCESS, hover_color=CLR_SUCCESS_H, font=FONT_BOLD, width=90
        )
        self.btn_iniciar.pack(side="left", padx=(0, 4))

        self.btn_pausar = ctk.CTkButton(
            row, text="⏸  Pausar", command=self.pausar_captura,
            fg_color=CLR_WARNING, hover_color=CLR_WARNING_H,
            font=FONT_BOLD, width=90, state="disabled"
        )
        self.btn_pausar.pack(side="left", padx=(0, 4))

        self.btn_recarregar = ctk.CTkButton(
            row, text="↺  Recarregar", command=self.recarregar_sistema,
            fg_color=("#64748b", "#334155"), hover_color=("#475569", "#1e293b"),
            font=FONT_BOLD, width=110
        )
        self.btn_recarregar.pack(side="left", padx=(0, 4))

        self.btn_parar_teste = ctk.CTkButton(
            row, text="■  Parar", command=self.parar_teste_imagens,
            fg_color=(CLR_MUTED, "#374151"), hover_color=("#4b5563", "#4b5563"),
            font=FONT_BOLD, width=80, state="disabled"
        )
        self.btn_parar_teste.pack(side="left")

        self.lbl_progresso_teste = ctk.CTkLabel(inner, text="", font=FONT_SMALL,
                                                 text_color=CLR_INFO)
        self.lbl_progresso_teste.pack(anchor="w", pady=(4, 0))

    # ── Painel ESTATÍSTICAS ───────────────────────────────────────────────────

    def _criar_painel_stats(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)
        inner.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def mini(col, label, init, color=None):
            f = ctk.CTkFrame(inner, corner_radius=6)
            f.grid(row=0, column=col, sticky="ew",
                   padx=(0 if col == 0 else 4, 0))
            val = ctk.CTkLabel(f, text=init, font=FONT_BOLD,
                               text_color=color or CLR_PRIMARY)
            val.pack(pady=(6, 0))
            ctk.CTkLabel(f, text=label, font=FONT_SMALL,
                         text_color=CLR_MUTED).pack(pady=(0, 6))
            return val

        self._stat_frames  = mini(0, "Frames",   "0", None)
        self._stat_detec   = mini(1, "Deteções", "0", CLR_INFO)
        self._stat_api_lbl = mini(2, "API",      "—", CLR_MUTED)
        self._stat_plc_lbl = mini(3, "PLC",      "—", CLR_MUTED)

    # ── Painel AÇÕES ──────────────────────────────────────────────────────────

    def _criar_painel_acoes(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        ctk.CTkLabel(card, text="Configurações & Testes", font=FONT_SMALL,
                     text_color=CLR_MUTED).pack(anchor="w", padx=12, pady=(10, 0))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(4, 12))
        inner.grid_columnconfigure((0, 1), weight=1)

        _sec = ("gray85", "gray25")
        _sec_h = ("gray75", "gray30")
        _sec_fg = ("gray10", "gray90")

        cfgs = [
            ("Fonte de Vídeo", self.selecionar_fonte,  0, 0),
            ("Configurar API", self.configurar_api,    0, 1),
            ("Configurar PLC", self.configurar_plc,    1, 0),
            ("Ver Configs",    self.ver_configuracoes, 1, 1),
        ]
        for txt, cmd, r, c in cfgs:
            ctk.CTkButton(
                inner, text=txt, command=cmd,
                fg_color=_sec, hover_color=_sec_h, text_color=_sec_fg,
                font=FONT_UI, height=32
            ).grid(row=r, column=c, sticky="ew",
                   padx=(0 if c == 0 else 4, 0),
                   pady=(0 if r == 0 else 4, 0))

        # Separador
        ctk.CTkFrame(inner, height=1, fg_color=("gray80", "gray30")).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(8, 4))

        test_row = ctk.CTkFrame(inner, fg_color="transparent")
        test_row.grid(row=3, column=0, columnspan=2, sticky="ew")

        ctk.CTkButton(test_row, text="Testar Imagem",
                      command=self.testar_imagem_unica,
                      fg_color=_sec, hover_color=_sec_h, text_color=_sec_fg,
                      font=FONT_UI, height=32).pack(side="left", padx=(0, 4))
        ctk.CTkButton(test_row, text="Banco de Imagens",
                      command=self.testar_banco_imagens,
                      fg_color=_sec, hover_color=_sec_h, text_color=_sec_fg,
                      font=FONT_UI, height=32).pack(side="left")

    # ── Painel LOG ────────────────────────────────────────────────────────────

    def _criar_painel_log(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.grid(row=4, column=0, sticky="nsew", pady=(8, 0))
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 0))

        ctk.CTkLabel(hdr, text="Log de Atividade", font=FONT_SMALL,
                     text_color=CLR_MUTED).pack(side="left")
        ctk.CTkButton(
            hdr, text="Limpar", command=self._limpar_log,
            width=60, height=24,
            fg_color=("gray85", "gray25"), hover_color=("gray75", "gray30"),
            text_color=("gray10", "gray90"), font=FONT_SMALL
        ).pack(side="right")

        self.log_text = ctk.CTkTextbox(
            card, font=FONT_MONO,
            fg_color=("#1a1a2e", "#0d0d1a"),
            text_color="#c9d1d9",
            state="disabled", wrap="word"
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 12))

        # Tags de cor no widget interno tk.Text
        tb = self.log_text._textbox
        tb.tag_configure("ERROR",   foreground="#f87171")
        tb.tag_configure("WARNING", foreground="#fbbf24")
        tb.tag_configure("SUCCESS", foreground="#34d399")
        tb.tag_configure("INFO",    foreground="#c9d1d9")
        tb.tag_configure("MUTED",   foreground="#6b7280")
        tb.tag_configure("TS",      foreground="#4b5563")

    # ── Barra de status ───────────────────────────────────────────────────────

    def _criar_statusbar(self):
        bar = ctk.CTkFrame(self.root, corner_radius=0, height=26,
                           fg_color=("gray90", "gray15"))
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            bar, text="  Sistema pronto",
            font=FONT_SMALL, text_color=CLR_MUTED, anchor="w"
        )
        self.status_label.pack(side="left", fill="y", padx=4)

    # =========================================================================
    # RELÓGIO
    # =========================================================================

    def _tick_hora(self):
        if self._lbl_hora:
            self._lbl_hora.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self._tick_hora)

    # =========================================================================
    # CANCELA — COMANDOS E ATUALIZAÇÕES
    # =========================================================================

    def _cmd_abrir_cancela(self):
        if self.plc_controller and self.plc_controller.esta_conectado():
            threading.Thread(target=self.plc_controller.abrir_cancela,
                             daemon=True).start()
            self.adicionar_log("↑ Abertura manual solicitada pelo operador", nivel="WARNING")
        else:
            messagebox.showwarning("PLC", "PLC não conectado. Verifique a configuração.")

    def _cmd_fechar_cancela(self):
        if self.plc_controller and self.plc_controller.esta_conectado():
            threading.Thread(target=self.plc_controller.fechar_cancela,
                             daemon=True).start()
            self.adicionar_log("↓ Fecho manual solicitado pelo operador", nivel="MUTED")
        else:
            messagebox.showwarning("PLC", "PLC não conectado. Verifique a configuração.")

    def atualizar_status_plc(self, status: str):
        mapa = {
            "aberta":  (CLR_SUCCESS, "ABERTA",       "Cancela levantada — veículo a passar",  "↑ Aberta",  True),
            "fechada": (CLR_MUTED,   "FECHADA",       "A aguardar próximo veículo",            "↓ Fechada", True),
            "erro":    (CLR_DANGER,  "ERRO PLC",      "Falha de comunicação com o PLC",        "✗ Erro",    False),
        }
        cor, texto, sub, mini, ativo = mapa.get(
            status, (CLR_MUTED, "DESCONECTADO", "PLC não conectado", "—", False)
        )

        def _update():
            if self._gate_dot:
                self._gate_dot.configure(text_color=cor)
            if self.lbl_gate_estado:
                self.lbl_gate_estado.configure(text=texto, text_color=cor)
            if self.lbl_gate_sub:
                self.lbl_gate_sub.configure(text=sub)
            if self._stat_plc_lbl:
                self._stat_plc_lbl.configure(text=mini, text_color=cor)
            state = "normal" if ativo else "disabled"
            if self.btn_abrir_cancela:
                self.btn_abrir_cancela.configure(state=state)
            if self.btn_fechar_cancela:
                self.btn_fechar_cancela.configure(state=state)
            if self._pill_plc_dot:
                pill_clr = (CLR_SUCCESS if status == "fechada"
                            else CLR_WARNING if status == "aberta"
                            else CLR_DANGER)
                self._pill_plc_dot.configure(text_color=pill_clr)

        self.root.after(0, _update)

    # =========================================================================
    # INICIALIZAÇÃO DOS COMPONENTES
    # =========================================================================

    def inicializar_componentes(self):
        self.adicionar_log("Inicializando componentes...", nivel="MUTED")
        try:
            self.adicionar_log("Carregando detector YOLO + OCR...", nivel="MUTED")
            self.detector = PlateDetector()
            self.adicionar_log("Detector carregado", nivel="SUCCESS")

            self.adicionar_log("Inicializando câmara...", nivel="MUTED")
            self.camera = CameraManager()
            if self.camera.abrir():
                self.adicionar_log("Câmara inicializada", nivel="SUCCESS")
            else:
                self.adicionar_log("Erro ao abrir câmara", nivel="ERROR")

            self.adicionar_log("Conectando à API...", nivel="MUTED")
            self.api_client = APIClient()
            if self.api_client.testar_conexao():
                self.adicionar_log("API conectada", nivel="SUCCESS")
                self.atualizar_status_api(True)
            else:
                self.adicionar_log("API não disponível — modo offline", nivel="WARNING")
                self.atualizar_status_api(False)

            if PLC_HABILITADO:
                self.adicionar_log("Conectando ao PLC...", nivel="MUTED")
                self.plc_controller = PLCController(
                    callback_status=self._on_plc_status,
                    callback_veiculo_detectado=self._on_veiculo_no_sensor
                )
                if self.plc_controller.conectar():
                    self.adicionar_log("PLC conectado — cancela pronta", nivel="SUCCESS")
                    self.atualizar_status_plc("fechada")
                else:
                    self.adicionar_log("PLC não conectado (inicie o simulador)", nivel="WARNING")
                    self.atualizar_status_plc("erro")
            else:
                self.adicionar_log("Integração PLC desativada (PLC_HABILITADO=False)", nivel="MUTED")

            self.atualizar_status("Sistema pronto para captura")

        except Exception as e:
            self.adicionar_log(f"Erro na inicialização: {e}", nivel="ERROR")
            self.root.after(0, lambda: messagebox.showerror("Erro de Inicialização", str(e)))

    # =========================================================================
    # CAPTURA
    # =========================================================================

    def iniciar_captura(self):
        if self.capturando:
            return
        self.capturando = True
        self.btn_iniciar.configure(state="disabled")
        self.btn_pausar.configure(state="normal")
        self.adicionar_log("Captura iniciada", nivel="SUCCESS")
        self.atualizar_status("A capturar...")
        self.thread_captura = threading.Thread(target=self.loop_captura, daemon=True)
        self.thread_captura.start()

    def pausar_captura(self):
        self.capturando = False
        self.btn_iniciar.configure(state="normal")
        self.btn_pausar.configure(state="disabled")
        self.adicionar_log("Captura pausada", nivel="WARNING")
        self.atualizar_status("Captura pausada")

    def loop_captura(self):
        frame_skip_count = 0
        while self.capturando:
            try:
                ret, frame = self.camera.ler_frame()
                if not ret or frame is None:
                    self.adicionar_log("Erro ao ler frame", nivel="ERROR")
                    break

                self.frame_count += 1
                frame_skip_count += 1
                self.atualizar_preview(frame)

                if frame_skip_count >= PROCESS_EVERY_N_FRAMES:
                    frame_skip_count = 0
                    deteccoes = self.detector.processar_frame(frame)
                    if deteccoes:
                        for det in deteccoes:
                            self.processar_deteccao(det, frame)
                    self.atualizar_estatisticas()

                time.sleep(0.01)

            except Exception as e:
                self.adicionar_log(f"Erro no loop: {e}", nivel="ERROR")
                break

        self.capturando = False

    # =========================================================================
    # DETEÇÃO
    # =========================================================================

    def processar_deteccao(self, deteccao: dict, frame):
        placa     = deteccao["placa"]
        confianca = deteccao["confianca_ocr"]
        metodo    = deteccao["metodo_ocr"]
        imagem_placa = deteccao.get("imagem_placa")

        self.deteccoes_count += 1
        self.atualizar_info_deteccao(placa, confianca)

        if SAVE_DETECTION_IMAGES and imagem_placa is not None:
            salvar_imagem_deteccao(frame, placa)

        if self.api_client and self.api_client.esta_conectado():
            resposta = self.api_client.enviar_deteccao(
                placa=placa,
                tipo_movimento="entrada",
                confianca_ocr=confianca,
                metodo_ocr=metodo,
                imagem=imagem_placa,
                resultados_ocr=deteccao.get("resultados_ocr_detalhados")
            )
            if resposta:
                cadastrado       = resposta.get("veiculo_cadastrado", False)
                eh_duplicata     = resposta.get("duplicata", False)
                msg_servidor     = resposta.get("mensagem", "")
                icone = "⚠" if eh_duplicata else ("✓" if cadastrado else "→")
                nivel = "WARNING" if eh_duplicata else "SUCCESS" if cadastrado else "INFO"
                self.adicionar_log(
                    f"{icone} {placa} | {confianca:.0%} | {metodo} | {msg_servidor}",
                    nivel=nivel
                )
                if cadastrado:
                    veiculo = resposta.get("veiculo")
                    if veiculo:
                        proprietario = veiculo.get("proprietario", {})
                        self.atualizar_status_veiculo(True, proprietario.get("nome", ""))
                else:
                    self.atualizar_status_veiculo(False)
            else:
                self.adicionar_log(f"Deteção não enviada: {placa}", nivel="WARNING")
        else:
            self.adicionar_log(f"{placa} | {confianca:.0%} | MODO OFFLINE", nivel="MUTED")

    # =========================================================================
    # ATUALIZAÇÕES DE UI
    # =========================================================================

    def atualizar_preview(self, frame):
        try:
            frame_display = preprocessar_para_display(frame, PREVIEW_WIDTH, PREVIEW_HEIGHT)
            photo = converter_cv_para_pil(frame_display)
            self.root.after(0, self._atualizar_preview_ui, photo)
        except Exception as e:
            logger.error(f"Erro ao atualizar preview: {e}")

    def _atualizar_preview_ui(self, photo):
        self.preview_label.configure(image=photo, text="")
        self.preview_label.image = photo

    def atualizar_info_deteccao(self, placa: str, confianca: float):
        def _upd():
            self.lbl_placa.configure(text=placa)
            self.lbl_confianca.configure(text=f"{confianca:.0%}")
            self._conf_bar.set(confianca)
            cor = (CLR_SUCCESS if confianca >= 0.8
                   else CLR_WARNING if confianca >= 0.6
                   else CLR_DANGER)
            self._conf_bar.configure(progress_color=cor)
        self.root.after(0, _upd)

    def atualizar_status_veiculo(self, cadastrado: bool, proprietario: str = ""):
        texto = f"✓  {proprietario}" if cadastrado else "Veículo não cadastrado"
        cor   = CLR_SUCCESS if cadastrado else CLR_MUTED
        self.root.after(0, lambda: self.lbl_status_veiculo.configure(
            text=texto, text_color=cor))

    def atualizar_estatisticas(self):
        def _upd():
            self._stat_frames.configure(text=str(self.frame_count))
            self._stat_detec.configure(text=str(self.deteccoes_count))
        self.root.after(0, _upd)

    def atualizar_status_api(self, conectado: bool):
        cor = CLR_SUCCESS if conectado else CLR_DANGER
        txt = "Online" if conectado else "Offline"

        def _upd():
            if self._stat_api_lbl:
                self._stat_api_lbl.configure(text=txt, text_color=cor)
            if self._pill_api_dot:
                self._pill_api_dot.configure(text_color=cor)
        self.root.after(0, _upd)

    def adicionar_log(self, mensagem: str, nivel: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        tag = nivel if nivel in ("ERROR", "WARNING", "SUCCESS", "MUTED") else "INFO"

        def _add():
            tb = self.log_text._textbox
            tb.configure(state="normal")
            tb.insert("end", f"[{timestamp}] ", "TS")
            tb.insert("end", f"{mensagem}\n", tag)
            tb.see("end")
            tb.configure(state="disabled")

        self.root.after(0, _add)

        if nivel == "ERROR":
            logger.error(mensagem)
        elif nivel == "WARNING":
            logger.warning(mensagem)
        else:
            logger.info(mensagem)

    def _limpar_log(self):
        tb = self.log_text._textbox
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        tb.configure(state="disabled")

    def atualizar_status(self, mensagem: str):
        self.root.after(0, lambda: self.status_label.configure(text=f"  {mensagem}"))

    # =========================================================================
    # CALLBACKS PLC
    # =========================================================================

    def _on_plc_status(self, status: str):
        self.atualizar_status_plc(status)

    def _on_veiculo_no_sensor(self):
        """
        Sensor de laço detectou veículo.
        OCR lê placa → cancela abre.
        OCR falha → cancela NÃO abre → operador usa o botão manual.
        """
        if not self.camera or not self.detector:
            return
        try:
            ret, frame = self.camera.ler_frame()
            if not ret or frame is None:
                self.adicionar_log("Sensor activo mas câmara não disponível", nivel="WARNING")
                return

            self.atualizar_preview(frame)
            deteccoes = self.detector.processar_frame(frame)

            if deteccoes:
                for det in deteccoes:
                    self.processar_deteccao(det, frame)
                self.atualizar_estatisticas()

                if self.plc_controller and self.plc_controller.esta_conectado():
                    threading.Thread(target=self.plc_controller.abrir_cancela,
                                     daemon=True).start()
                    placa_lida = deteccoes[0]["placa"]
                    self.adicionar_log(f"Cancela aberta — placa lida: {placa_lida}",
                                       nivel="SUCCESS")
            else:
                self.adicionar_log(
                    "Placa não lida — cancela NÃO abre. Use o botão ABRIR se necessário.",
                    nivel="WARNING"
                )
        except Exception as e:
            logger.error(f"Erro no callback de sensor: {e}")

    # =========================================================================
    # AÇÕES: RECARREGAR, FONTE, API, PLC, CONFIGS, TESTES
    # =========================================================================

    def recarregar_sistema(self):
        if self.capturando:
            self.capturando = False
            self.btn_iniciar.configure(state="normal")
            self.btn_pausar.configure(state="disabled")

        if self.testando_imagens:
            self.testando_imagens = False
            self.btn_parar_teste.configure(state="disabled")
            self.root.after(0, lambda: self.lbl_progresso_teste.configure(text=""))

        if self.camera:
            try: self.camera.fechar()
            except Exception: pass

        if self.plc_controller:
            try: self.plc_controller.desconectar()
            except Exception: pass

        self.adicionar_log("Recarregando sistema...", nivel="MUTED")
        self.atualizar_status("Recarregando...")
        threading.Thread(target=self.inicializar_componentes, daemon=True).start()

    def selecionar_fonte(self):
        filepath = filedialog.askopenfilename(
            title="Selecionar Vídeo / Imagem",
            filetypes=[
                ("Vídeos",  "*.mp4 *.avi *.mov"),
                ("Imagens", "*.jpg *.jpeg *.png"),
                ("Todos",   "*.*")
            ]
        )
        if filepath:
            if self.camera:
                self.camera.fechar()
            self.camera = CameraManager(filepath)
            if self.camera.abrir():
                self.adicionar_log(f"Nova fonte: {filepath}", nivel="SUCCESS")
            else:
                self.adicionar_log(f"Erro ao abrir: {filepath}", nivel="ERROR")

    def configurar_api(self):
        from ..config import BASE_DIR

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Configurar API")
        dialog.geometry("460x240")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        url_atual = self.api_client.api_url if self.api_client else ""
        try:
            parts = url_atual.split("/")
            host_atual = f"{parts[0]}//{parts[2]}"
        except Exception:
            host_atual = f"http://{API_HOST}" if not API_HOST.startswith("http") else API_HOST

        timeout_atual = str(self.api_client.timeout if self.api_client else API_TIMEOUT)

        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="URL da API (host):", font=FONT_UI,
                     anchor="w").grid(row=0, column=0, sticky="w", pady=6)
        entry_host = ctk.CTkEntry(frame, width=280, font=FONT_UI)
        entry_host.insert(0, host_atual)
        entry_host.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=6)

        ctk.CTkLabel(frame, text="Timeout (s):", font=FONT_UI,
                     anchor="w").grid(row=1, column=0, sticky="w", pady=6)
        entry_timeout = ctk.CTkEntry(frame, width=80, font=FONT_UI)
        entry_timeout.insert(0, timeout_atual)
        entry_timeout.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=6)

        lbl_status = ctk.CTkLabel(frame, text="", font=FONT_SMALL, text_color=CLR_MUTED)
        lbl_status.grid(row=2, column=0, columnspan=2, sticky="w", pady=4)

        def testar():
            host = entry_host.get().strip().rstrip("/")
            if not host.startswith("http"):
                lbl_status.configure(text="URL deve começar com http://", text_color=CLR_DANGER)
                return
            lbl_status.configure(text="Testando...", text_color=CLR_MUTED)
            dialog.update()
            try:
                import requests as _req
                resp = _req.get(f"{host}/health", timeout=5)
                if resp.status_code == 200:
                    lbl_status.configure(text="Conexão bem-sucedida!", text_color=CLR_SUCCESS)
                else:
                    lbl_status.configure(text=f"HTTP {resp.status_code}", text_color=CLR_WARNING)
            except Exception as e:
                lbl_status.configure(text=f"{type(e).__name__}", text_color=CLR_DANGER)

        def salvar():
            host = entry_host.get().strip().rstrip("/")
            if not host.startswith("http"):
                lbl_status.configure(text="URL inválida", text_color=CLR_DANGER)
                return
            try:
                timeout = int(entry_timeout.get().strip())
            except ValueError:
                lbl_status.configure(text="Timeout deve ser inteiro", text_color=CLR_DANGER)
                return
            if self.api_client:
                self.api_client.api_url = f"{host}/api/v1/registros/deteccao"
                self.api_client.timeout = timeout
            env_path = BASE_DIR / ".env"
            try:
                linhas = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
                novas, written = [], set()
                for l in linhas:
                    if l.startswith("API_HOST="):
                        novas.append(f"API_HOST={host}"); written.add("API_HOST")
                    elif l.startswith("API_TIMEOUT="):
                        novas.append(f"API_TIMEOUT={timeout}"); written.add("API_TIMEOUT")
                    else:
                        novas.append(l)
                if "API_HOST" not in written: novas.append(f"API_HOST={host}")
                if "API_TIMEOUT" not in written: novas.append(f"API_TIMEOUT={timeout}")
                env_path.write_text("\n".join(novas) + "\n", encoding="utf-8")
            except Exception as e:
                self.adicionar_log(f"Não foi possível salvar .env: {e}", nivel="WARNING")
            self.adicionar_log(f"API configurada: {host} | timeout={timeout}s", nivel="SUCCESS")
            dialog.destroy()

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=3, column=0, columnspan=2, pady=(10, 0))

        ctk.CTkButton(btn_row, text="Testar Conexão", command=testar, width=130, font=FONT_UI,
                      fg_color=CLR_INFO, hover_color="#2563eb").pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="Salvar", command=salvar, width=90, font=FONT_UI,
                      fg_color=CLR_SUCCESS, hover_color=CLR_SUCCESS_H).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="Cancelar", command=dialog.destroy, width=90, font=FONT_UI,
                      fg_color=("gray80", "gray30"), hover_color=("gray70", "gray25"),
                      text_color=("gray10", "gray90")).pack(side="left", padx=4)

    def ver_configuracoes(self):
        from ..config import obter_config_display
        config = obter_config_display()
        texto = "=== CONFIGURAÇÕES ATUAIS ===\n\n"
        for secao, valores in config.items():
            texto += f"{secao}:\n"
            for chave, valor in valores.items():
                texto += f"  • {chave}: {valor}\n"
            texto += "\n"
        messagebox.showinfo("Configurações", texto)

    # ── Testes com imagens ────────────────────────────────────────────────────

    def testar_imagem_unica(self):
        if not self.detector:
            messagebox.showerror("Erro", "Detector não inicializado")
            return
        filepath = filedialog.askopenfilename(
            title="Selecionar Imagem",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp"), ("Todos", "*.*")]
        )
        if filepath:
            from pathlib import Path as _Path
            self.adicionar_log(f"Testando: {_Path(filepath).name}", nivel="MUTED")
            self._processar_imagem_arquivo(filepath)

    def testar_banco_imagens(self):
        if not self.detector:
            messagebox.showerror("Erro", "Detector não inicializado")
            return
        if self.testando_imagens:
            messagebox.showwarning("Aviso", "Teste já em andamento. Clique em 'Parar Teste'.")
            return

        resposta = messagebox.askyesnocancel(
            "Selecionar Imagens",
            "SIM = Selecionar uma PASTA\nNÃO = Selecionar ficheiros individuais\nCANCELAR = Abortar"
        )
        if resposta is None:
            return

        image_files = []
        if resposta:
            from pathlib import Path as _Path
            pasta = filedialog.askdirectory(title="Selecionar Pasta")
            if pasta:
                image_files = sorted([
                    str(p) for p in _Path(pasta).iterdir()
                    if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
                ])
        else:
            files = filedialog.askopenfilenames(
                title="Selecionar Imagens",
                filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp"), ("Todos", "*.*")]
            )
            image_files = list(files)

        if not image_files:
            self.adicionar_log("Nenhuma imagem selecionada", nivel="WARNING")
            return

        self.adicionar_log(f"Iniciando teste com {len(image_files)} imagem(ns)...", nivel="MUTED")
        self.testando_imagens = True
        self.btn_parar_teste.configure(state="normal")
        threading.Thread(target=self._executar_banco_imagens,
                         args=(image_files,), daemon=True).start()

    def parar_teste_imagens(self):
        self.testando_imagens = False
        self.adicionar_log("Teste interrompido pelo utilizador", nivel="WARNING")
        self.btn_parar_teste.configure(state="disabled")
        self.root.after(0, lambda: self.lbl_progresso_teste.configure(text=""))

    def _processar_imagem_arquivo(self, filepath: str):
        import cv2 as _cv2
        from pathlib import Path as _Path
        frame = _cv2.imread(filepath)
        if frame is None:
            self.adicionar_log(f"Erro ao carregar imagem: {filepath}", nivel="ERROR")
            return
        self.atualizar_preview(frame)
        deteccoes = self.detector.processar_frame(frame)
        nome = _Path(filepath).name
        if deteccoes:
            for det in deteccoes:
                self.processar_deteccao(det, frame)
            self.atualizar_estatisticas()
        else:
            self.adicionar_log(f"Nenhuma placa detetada em: {nome}", nivel="WARNING")

    def _executar_banco_imagens(self, image_files: list):
        import cv2 as _cv2
        from pathlib import Path as _Path
        total = len(image_files)
        processadas = total_deteccoes = 0

        for i, filepath in enumerate(image_files):
            if not self.testando_imagens:
                break
            nome = _Path(filepath).name
            prog = f"Teste: {i + 1}/{total} — {nome}"
            self.root.after(0, lambda t=prog: self.lbl_progresso_teste.configure(text=t))
            self.atualizar_status(f"Imagem {i + 1} de {total}...")

            frame = _cv2.imread(filepath)
            if frame is None:
                self.adicionar_log(f"Erro ao carregar: {nome}", nivel="ERROR")
                continue

            self.atualizar_preview(frame)
            deteccoes = self.detector.processar_frame(frame)
            processadas += 1

            if deteccoes:
                total_deteccoes += len(deteccoes)
                for det in deteccoes:
                    self.processar_deteccao(det, frame)
            else:
                self.adicionar_log(f"  Sem placa: {nome}", nivel="MUTED")

            self.atualizar_estatisticas()
            time.sleep(0.5)

        self.testando_imagens = False
        self.root.after(0, lambda: self.btn_parar_teste.configure(state="disabled"))
        self.root.after(0, lambda: self.lbl_progresso_teste.configure(text=""))
        resumo = f"Teste concluído: {processadas}/{total} imagens | {total_deteccoes} deteção(ões)"
        self.adicionar_log(resumo, nivel="SUCCESS")
        self.atualizar_status(resumo)

    # ── Configurar PLC ────────────────────────────────────────────────────────

    def configurar_plc(self):
        from ..config import BASE_DIR

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Configurar PLC / Cancela")
        dialog.geometry("460x310")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="IP do PLC:", font=FONT_UI,
                     anchor="w").grid(row=0, column=0, sticky="w", pady=6)
        entry_host = ctk.CTkEntry(frame, width=240, font=FONT_UI)
        entry_host.insert(0, self.plc_controller.host if self.plc_controller else PLC_HOST)
        entry_host.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=6)

        ctk.CTkLabel(frame, text="Porta Modbus TCP:", font=FONT_UI,
                     anchor="w").grid(row=1, column=0, sticky="w", pady=6)
        entry_port = ctk.CTkEntry(frame, width=100, font=FONT_UI)
        entry_port.insert(0, str(self.plc_controller.port if self.plc_controller else PLC_PORT))
        entry_port.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=6)

        lbl_status = ctk.CTkLabel(frame, text="", font=FONT_SMALL, text_color=CLR_MUTED)
        lbl_status.grid(row=2, column=0, columnspan=2, sticky="w", pady=4)

        def testar():
            host = entry_host.get().strip()
            try:
                port = int(entry_port.get().strip())
            except ValueError:
                lbl_status.configure(text="Porta inválida", text_color=CLR_DANGER); return
            lbl_status.configure(text="Conectando...", text_color=CLR_MUTED)
            dialog.update()
            tmp = PLCController(host=host, port=port)
            if tmp.conectar():
                tmp.desconectar()
                lbl_status.configure(text="PLC acessível!", text_color=CLR_SUCCESS)
            else:
                lbl_status.configure(text="Não foi possível conectar", text_color=CLR_DANGER)

        def abrir_manual():
            if self.plc_controller and self.plc_controller.esta_conectado():
                threading.Thread(target=self.plc_controller.abrir_cancela, daemon=True).start()
                lbl_status.configure(text="Comando enviado: abrir", text_color=CLR_TEAL)
            else:
                lbl_status.configure(text="PLC não conectado", text_color=CLR_DANGER)

        def fechar_manual():
            if self.plc_controller and self.plc_controller.esta_conectado():
                threading.Thread(target=self.plc_controller.fechar_cancela, daemon=True).start()
                lbl_status.configure(text="Comando enviado: fechar", text_color=CLR_MUTED)
            else:
                lbl_status.configure(text="PLC não conectado", text_color=CLR_DANGER)

        def salvar():
            host = entry_host.get().strip()
            try:
                port = int(entry_port.get().strip())
            except ValueError:
                lbl_status.configure(text="Porta inválida", text_color=CLR_DANGER); return

            if self.plc_controller:
                self.plc_controller.desconectar()

            self.plc_controller = PLCController(
                host=host, port=port,
                callback_status=self._on_plc_status,
                callback_veiculo_detectado=self._on_veiculo_no_sensor
            )
            if self.plc_controller.conectar():
                self.adicionar_log(f"PLC reconfigurado: {host}:{port}", nivel="SUCCESS")
                self.atualizar_status_plc("fechada")
            else:
                self.adicionar_log(f"PLC configurado mas não conectado: {host}:{port}", nivel="WARNING")
                self.atualizar_status_plc("erro")

            env_path = BASE_DIR / ".env"
            try:
                linhas = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
                novas, written = [], set()
                for l in linhas:
                    if l.startswith("PLC_HOST="):
                        novas.append(f"PLC_HOST={host}"); written.add("PLC_HOST")
                    elif l.startswith("PLC_PORT="):
                        novas.append(f"PLC_PORT={port}"); written.add("PLC_PORT")
                    else:
                        novas.append(l)
                if "PLC_HOST" not in written: novas.append(f"PLC_HOST={host}")
                if "PLC_PORT" not in written: novas.append(f"PLC_PORT={port}")
                env_path.write_text("\n".join(novas) + "\n", encoding="utf-8")
            except Exception as e:
                self.adicionar_log(f"Não foi possível salvar .env: {e}", nivel="WARNING")
            dialog.destroy()

        row1 = ctk.CTkFrame(frame, fg_color="transparent")
        row1.grid(row=3, column=0, columnspan=2, pady=(6, 0))
        ctk.CTkButton(row1, text="Testar Conexão", command=testar, width=130, font=FONT_UI,
                      fg_color=CLR_INFO, hover_color="#2563eb").pack(side="left", padx=3)
        ctk.CTkButton(row1, text="↑ Abrir", command=abrir_manual, width=80, font=FONT_UI,
                      fg_color=CLR_TEAL, hover_color=CLR_TEAL_H).pack(side="left", padx=3)
        ctk.CTkButton(row1, text="↓ Fechar", command=fechar_manual, width=80, font=FONT_UI,
                      fg_color=CLR_DANGER, hover_color=CLR_DANGER_H).pack(side="left", padx=3)

        row2 = ctk.CTkFrame(frame, fg_color="transparent")
        row2.grid(row=4, column=0, columnspan=2, pady=(8, 0))
        ctk.CTkButton(row2, text="Salvar e Reconectar", command=salvar, width=160, font=FONT_UI,
                      fg_color=CLR_SUCCESS, hover_color=CLR_SUCCESS_H).pack(side="left", padx=3)
        ctk.CTkButton(row2, text="Cancelar", command=dialog.destroy, width=90, font=FONT_UI,
                      fg_color=("gray80", "gray30"), hover_color=("gray70", "gray25"),
                      text_color=("gray10", "gray90")).pack(side="left", padx=3)

    # =========================================================================
    # FECHAR
    # =========================================================================

    def on_closing(self):
        if self.capturando or self.testando_imagens:
            if messagebox.askokcancel("Sair", "Operação em curso. Deseja mesmo sair?"):
                self.capturando = False
                self.testando_imagens = False
                time.sleep(0.3)
                self.fechar()
        else:
            self.fechar()

    def fechar(self):
        self.adicionar_log("A encerrar a aplicação...", nivel="MUTED")
        if self.camera:
            self.camera.fechar()
        if self.plc_controller:
            self.plc_controller.desconectar()
        self.root.quit()
        self.root.destroy()
