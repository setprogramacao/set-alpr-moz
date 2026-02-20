/**
 * Sistema ALPR UNIPIAGET - JavaScript Principal
 * Funções compartilhadas entre todas as páginas
 */

const API_URL = 'http://localhost:8000/api/v1';

/**
 * Faz requisição autenticada à API
 * @param {string} endpoint - Endpoint da API (ex: '/veiculos')
 * @param {string} method - Método HTTP (GET, POST, PUT, DELETE)
 * @param {object} data - Dados para enviar (opcional)
 * @returns {Promise<object>} - Resposta da API
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
    const token = localStorage.getItem('token');

    if (!token && !endpoint.includes('/auth/login')) {
        window.location.href = '/login';
        return null;
    }

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

        // Se 401, token inválido -> redireciona para login
        if (response.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('usuario');
            window.location.href = '/login';
            return null;
        }

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Erro na requisição');
        }

        return result;

    } catch (error) {
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
        window.location.href = '/login';
    } else if (token && currentPath === '/login') {
        window.location.href = '/';
    }
}

/**
 * Carrega informações do usuário na navbar
 */
function loadUserInfo() {
    const usuarioStr = localStorage.getItem('usuario');

    if (!usuarioStr) return;

    try {
        const usuario = JSON.parse(usuarioStr);
        const userNameElement = document.getElementById('userName');

        if (userNameElement) {
            userNameElement.textContent = usuario.nome_completo;
        }
    } catch (error) {
        console.error('Erro ao carregar dados do usuário:', error);
    }
}

/**
 * Faz logout do sistema
 */
async function logout() {
    try {
        await apiRequest('/auth/logout', 'POST');
    } catch (error) {
        console.error('Erro no logout:', error);
    } finally {
        localStorage.removeItem('token');
        localStorage.removeItem('usuario');
        window.location.href = '/login';
    }
}

/**
 * Exibe toast de notificação
 * @param {string} message - Mensagem a exibir
 * @param {string} type - Tipo do alerta (success, danger, warning, info)
 */
function showToast(message, type = 'info') {
    const alertsContainer = document.getElementById('alertsContainer');

    if (!alertsContainer) {
        console.warn('Container de alertas não encontrado');
        return;
    }

    const alertId = `alert-${Date.now()}`;
    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    alertsContainer.insertAdjacentHTML('beforeend', alertHTML);

    // Auto remove após 5 segundos
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            alertElement.remove();
        }
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

// Ativa tooltips do Bootstrap
document.addEventListener('DOMContentLoaded', function() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Marca link ativo na navbar
document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');

    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
});
