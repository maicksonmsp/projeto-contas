// ========== GERENCIAMENTO DE TEMA ==========
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    const toggle = document.getElementById('themeToggle');
    if (toggle) {
        toggle.checked = savedTheme === 'dark';
    }
    
    console.log('Tema inicializado:', savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    console.log('Tema alterado para:', newTheme);
}

// ========== FUNÇÕES GERAIS ==========
function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor);
}

function formatarData(dataString) {
    if (!dataString) return '';
    try {
        const data = new Date(dataString);
        return data.toLocaleDateString('pt-BR');
    } catch (e) {
        return dataString;
    }
}

function calcularDiasRestantes(dataTermino) {
    if (!dataTermino) return 0;
    try {
        const hoje = new Date();
        const termino = new Date(dataTermino);
        const diffTime = termino - hoje;
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    } catch (e) {
        return 0;
    }
}

// ========== GERENCIAMENTO DE LINHAS ==========
function filtrarTabela() {
    const input = document.getElementById('searchInput');
    if (!input) return;
    
    const filter = input.value.toLowerCase();
    const table = document.getElementById('linhasTable');
    if (!table) return;
    
    const rows = table.getElementsByTagName('tr');
    
    for (let i = 1; i < rows.length; i++) {
        const cells = rows[i].getElementsByTagName('td');
        let found = false;
        
        for (let j = 0; j < cells.length; j++) {
            if (cells[j].textContent.toLowerCase().includes(filter)) {
                found = true;
                break;
            }
        }
        
        rows[i].style.display = found ? '' : 'none';
    }
}

function confirmarExclusao(id, tipo) {
    if (confirm(`Tem certeza que deseja excluir este ${tipo === 'linhas' ? 'linha' : 'usuário'}?`)) {
        fetch(`/${tipo}/excluir/${id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Erro: ' + (data.error || 'Não foi possível excluir'));
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao conectar com o servidor');
        });
    }
}

// ========== VALIDAÇÃO DE FORMULÁRIOS ==========
function validarFormulario(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let valido = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            valido = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return valido;
}

// ========== NOTIFICAÇÕES ==========
function mostrarNotificacao(mensagem, tipo = 'info') {
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[tipo] || 'alert-info';
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${alertClass} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('main .container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 300);
        }, 5000);
    }
}

// ========== INICIALIZAÇÃO ==========
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar tema
    initTheme();
    
    // Configurar tooltips do Bootstrap
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });
    
    // Configurar popovers
    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    popovers.forEach(popover => {
        new bootstrap.Popover(popover);
    });
    
    // Auto-dismiss alerts após 5 segundos
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            setTimeout(() => bsAlert.close(), 5000);
        });
    }, 5000);
    
    // Adicionar máscara para telefone
    const telefoneInputs = document.querySelectorAll('input[type="tel"], input[name*="linha"]');
    telefoneInputs.forEach(input => {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            
            if (value.length > 11) {
                value = value.substring(0, 11);
            }
            
            if (value.length > 10) {
                // Formato: (00) 00000-0000
                value = value.replace(/^(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
            } else if (value.length > 6) {
                // Formato: (00) 0000-0000
                value = value.replace(/^(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
            } else if (value.length > 2) {
                value = value.replace(/^(\d{2})(\d+)/, '($1) $2');
            } else if (value.length > 0) {
                value = value.replace(/^(\d*)/, '($1');
            }
            
            e.target.value = value;
        });
    });
    
    // Formatar valores monetários
    const moneyInputs = document.querySelectorAll('input[type="number"][step="0.01"]');
    moneyInputs.forEach(input => {
        input.addEventListener('blur', function(e) {
            let value = parseFloat(e.target.value);
            if (!isNaN(value)) {
                e.target.value = value.toFixed(2);
            }
        });
    });
    
    console.log('Sistema PEIXOTO inicializado com sucesso!');
});

// ========== EXPORTAÇÃO DE DADOS ==========
function exportarParaCSV() {
    window.location.href = '/exportar/linhas';
}

// ========== ATALHOS DE TECLADO ==========
document.addEventListener('keydown', function(e) {
    // Ctrl + E = Exportar
    if (e.ctrlKey && e.key === 'e') {
        e.preventDefault();
        exportarParaCSV();
    }
    
    // Ctrl + N = Nova Linha
    if (e.ctrlKey && e.key === 'n') {
        e.preventDefault();
        const novoBtn = document.querySelector('a[href*="adicionar"]');
        if (novoBtn) novoBtn.click();
    }
    
    // Ctrl + F = Focar na busca
    if (e.ctrlKey && e.key === 'f') {
        e.preventDefault();
        const searchInput = document.querySelector('input[name="search"], #searchInput');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }
});

// ========== CARREGAMENTO DINÂMICO ==========
function carregarDadosDashboard() {
    fetch('/api/dashboard')
        .then(response => response.json())
        .then(data => {
            console.log('Dados do dashboard carregados:', data);
        })
        .catch(error => {
            console.error('Erro ao carregar dados do dashboard:', error);
        });
}