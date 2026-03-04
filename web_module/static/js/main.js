/**
 * Sistema ALPR UNIPIAGET - JavaScript Principal
 * Funções compartilhadas entre todas as páginas
 */

const API_URL = 'http://localhost:8000/api/v1';

// Papel do utilizador atual (preenchido por loadUserInfo)
let currentUserRole = 'visualizador';

// Previne múltiplos redirects simultâneos para /login
let _redirecionandoParaLogin = false;

function _redirecionarLogin() {
    if (_redirecionandoParaLogin) return;
    _redirecionandoParaLogin = true;
    window.location.href = '/login';
}

/**
 * Faz requisição autenticada à API
 * @param {string} endpoint - Endpoint da API (ex: '/veiculos')
 * @param {string} method - Método HTTP (GET, POST, PUT, DELETE)
 * @param {object} data - Dados para enviar (opcional)
 * @returns {Promise<object>} - Resposta da API
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
    const token = localStorage.getItem('token');

    const headers = {
        'Content-Type': 'application/json'
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        method: method,
        headers: headers
    };

    if (data && (method === 'POST' || method === 'PUT')) {
        config.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(`${API_URL}${endpoint}`, config);

        // Se 401, token inválido -> redireciona para login (uma única vez)
        if (response.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('usuario');
            _redirecionarLogin();
            return null;
        }

        const result = await response.json();

        if (!response.ok) {
            // Pydantic pode retornar detail como array de objetos de validação
            let detail = result.detail;
            if (Array.isArray(detail)) {
                detail = detail.map(e => e.msg || e.message || JSON.stringify(e)).join(' | ');
            } else if (typeof detail === 'object' && detail !== null) {
                detail = JSON.stringify(detail);
            }
            throw new Error(detail || 'Erro na requisição');
        }

        return result;

    } catch (error) {
        if (_redirecionandoParaLogin) return null; // ignora erros durante redirect
        console.error('Erro na requisição:', error);
        showToast('Erro ao comunicar com servidor', 'danger');
        throw error;
    }
}

/**
 * Verifica se usuário está autenticado
 */
function checkAuth() {
    const token = localStorage.getItem('token');
    const currentPath = window.location.pathname;

    if (!token && currentPath !== '/login') {
        _redirecionarLogin();
    } else if (token && currentPath === '/login') {
        window.location.href = '/';
    }
}

/**
 * Carrega informações do usuário na navbar e controla visibilidade por role
 */
function loadUserInfo() {
    const usuarioStr = localStorage.getItem('usuario');
    if (!usuarioStr) return;

    try {
        const usuario = JSON.parse(usuarioStr);

        // Nome do usuário
        const userNameEl = document.getElementById('userName');
        if (userNameEl) userNameEl.textContent = usuario.nome_completo || usuario.username;

        // Inicial do avatar
        const userInitialEl = document.getElementById('userInitial');
        if (userInitialEl) {
            const name = usuario.nome_completo || usuario.username || '?';
            userInitialEl.textContent = name.charAt(0).toUpperCase();
        }

        // Papel do usuário (display name)
        const roleMap = {
            admin: 'Admin',
            operador: 'Gestor de Sistema',
            visualizador: 'Visualizador'
        };
        const userRoleEl = document.getElementById('userRole');
        if (userRoleEl) userRoleEl.textContent = roleMap[usuario.nivel_acesso] || usuario.nivel_acesso;

        // Mostra menu "Usuários" apenas para admin e operador (Gestor de Sistema)
        if (usuario.nivel_acesso === 'admin' || usuario.nivel_acesso === 'operador') {
            const navUsuarios = document.getElementById('nav-usuarios');
            if (navUsuarios) navUsuarios.classList.remove('hidden');
        }

        // Guarda role numa variável global para uso nas páginas
        currentUserRole = usuario.nivel_acesso;

    } catch (error) {
        console.error('Erro ao carregar dados do usuário:', error);
    }
}

/**
 * Retorna o nível de acesso do usuário logado
 * @returns {string} - 'admin', 'operador' ou 'visualizador'
 */
function getUserRole() {
    try {
        const usuario = JSON.parse(localStorage.getItem('usuario') || '{}');
        return usuario.nivel_acesso || 'visualizador';
    } catch {
        return 'visualizador';
    }
}

/**
 * Faz logout do sistema
 */
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
    // Notifica API de forma não-bloqueante (fire-and-forget)
    fetch(`${API_URL}/auth/logout`, { method: 'POST' }).catch(() => {});
    window.location.href = '/login';
}

/**
 * Exibe toast de notificação (Tailwind)
 * @param {string} message - Mensagem a exibir
 * @param {string} type - Tipo do alerta (success, danger, warning, info)
 */
function showToast(message, type = 'info') {
    const alertsContainer = document.getElementById('alertsContainer');
    if (!alertsContainer) {
        console.warn('Container de alertas não encontrado');
        return;
    }

    const colorMap = {
        success: 'bg-green-50 border-green-400 text-green-800 dark:bg-green-900/30 dark:text-green-300',
        danger:  'bg-red-50 border-red-400 text-red-800 dark:bg-red-900/30 dark:text-red-300',
        warning: 'bg-yellow-50 border-yellow-400 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
        info:    'bg-blue-50 border-blue-400 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    };
    const iconMap = {
        success: 'bi-check-circle-fill',
        danger:  'bi-x-circle-fill',
        warning: 'bi-exclamation-triangle-fill',
        info:    'bi-info-circle-fill',
    };

    const alertId = `alert-${Date.now()}`;
    const cls = colorMap[type] || colorMap.info;
    const icon = iconMap[type] || iconMap.info;

    alertsContainer.insertAdjacentHTML('beforeend', `
        <div id="${alertId}" class="flex items-center gap-3 p-4 mb-3 border-l-4 rounded-lg shadow-subtle ${cls}">
            <i class="bi ${icon} text-lg flex-shrink-0"></i>
            <span class="flex-1 text-sm font-medium">${message}</span>
            <button onclick="document.getElementById('${alertId}').remove()" class="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity">
                <i class="bi bi-x-lg text-sm"></i>
            </button>
        </div>
    `);

    setTimeout(() => {
        const el = document.getElementById(alertId);
        if (el) el.remove();
    }, 5000);
}

/**
 * Formata data/hora para exibição
 * @param {string} datetime - Data/hora em ISO format
 * @returns {string} - Data formatada
 */
function formatDateTime(datetime) {
    if (!datetime) return '-';

    const date = new Date(datetime);
    return date.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Formata data para exibição
 * @param {string} date - Data em ISO format
 * @returns {string} - Data formatada
 */
function formatDate(date) {
    if (!date) return '-';

    const d = new Date(date);
    return d.toLocaleDateString('pt-BR');
}

/**
 * Formata placa para exibição (AA-00-00-XX)
 * @param {string} placa - Placa sem formatação
 * @returns {string} - Placa formatada
 */
function formatPlaca(placa) {
    if (!placa || placa.length !== 8) return placa;

    // AA0000XX -> AA-00-00-XX
    return `${placa.slice(0, 2)}-${placa.slice(2, 4)}-${placa.slice(4, 6)}-${placa.slice(6, 8)}`;
}

/**
 * Cria badge de categoria
 * @param {string} categoria - Categoria (docente, tecnico, etc)
 * @returns {string} - HTML do badge
 */
function getBadgeCategoria(categoria) {
    const badges = {
        'docente': 'primary',
        'tecnico': 'success',
        'visitante': 'warning',
        'aluno': 'info'
    };

    const color = badges[categoria] || 'secondary';
    return `<span class="badge bg-${color}">${categoria}</span>`;
}

/**
 * Cria badge de tipo de movimento
 * @param {string} tipo - entrada ou saida
 * @returns {string} - HTML do badge
 */
function getBadgeMovimento(tipo) {
    if (tipo === 'entrada') {
        return '<span class="badge bg-success"><i class="bi bi-arrow-right"></i> Entrada</span>';
    } else {
        return '<span class="badge bg-danger"><i class="bi bi-arrow-left"></i> Saída</span>';
    }
}

/**
 * Confirma ação destrutiva
 * @param {string} message - Mensagem de confirmação
 * @returns {boolean} - true se confirmado
 */
function confirmarAcao(message) {
    return confirm(message);
}

/**
 * Valida formato de placa moçambicana
 * @param {string} placa - Placa a validar
 * @returns {boolean} - true se válida
 */
function validarPlaca(placa) {
    if (!placa) return false;

    // Remove hífens e espaços
    const placaLimpa = placa.replace(/[-\s]/g, '').toUpperCase();

    // Valida formato: 2 letras + 4 números + 2 alfanuméricos
    const regex = /^[A-Z]{2}\d{4}[A-Z0-9]{2}$/;

    return regex.test(placaLimpa);
}

/**
 * Valida email
 * @param {string} email - Email a validar
 * @returns {boolean} - true se válido
 */
function validarEmail(email) {
    if (!email) return false;

    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

/**
 * Valida telefone moçambicano
 * @param {string} telefone - Telefone a validar
 * @returns {boolean} - true se válido
 */
function validarTelefone(telefone) {
    if (!telefone) return false;

    // Remove caracteres não numéricos
    const telefoneLimpo = telefone.replace(/\D/g, '');

    // Valida formato: +258XXXXXXXXX ou 8XXXXXXXX
    return /^(\+?258)?[28]\d{8}$/.test(telefoneLimpo);
}

/**
 * Debounce para funções de busca
 * @param {function} func - Função a executar
 * @param {number} delay - Delay em ms
 * @returns {function} - Função com debounce
 */
function debounce(func, delay = 300) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

/**
 * Exporta tabela para CSV
 * @param {string} tableId - ID da tabela HTML
 * @param {string} filename - Nome do arquivo
 */
function exportarTabelaCSV(tableId, filename = 'dados.csv') {
    const table = document.getElementById(tableId);
    if (!table) return;

    let csv = [];

    // Headers
    const headers = [];
    table.querySelectorAll('thead th').forEach(th => {
        headers.push(th.textContent.trim());
    });
    csv.push(headers.join(','));

    // Rows
    table.querySelectorAll('tbody tr').forEach(tr => {
        const row = [];
        tr.querySelectorAll('td').forEach(td => {
            row.push(`"${td.textContent.trim()}"`);
        });
        csv.push(row.join(','));
    });

    // Download
    const csvContent = '\uFEFF' + csv.join('\n'); // BOM para Excel
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Atualiza contador de tempo real (ex: "há 2 minutos")
 * @param {string} datetime - Data/hora em ISO format
 * @returns {string} - Tempo relativo
 */
function tempoRelativo(datetime) {
    if (!datetime) return '-';

    const agora = new Date();
    const data = new Date(datetime);
    const diff = Math.floor((agora - data) / 1000); // segundos

    if (diff < 60) return 'agora há pouco';
    if (diff < 3600) return `há ${Math.floor(diff / 60)} min`;
    if (diff < 86400) return `há ${Math.floor(diff / 3600)}h`;
    return `há ${Math.floor(diff / 86400)} dias`;
}

/**
 * Loading spinner
 */
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Carregando...</span></div></div>';
    }
}

/**
 * Remove loading spinner
 */
function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '';
    }
}

// ============================================================================
// EVENT LISTENERS GLOBAIS
// ============================================================================

// Marca link ativo na sidebar (Tailwind)
document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('aside nav a[href]').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
});
