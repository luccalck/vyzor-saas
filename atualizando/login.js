/**
 * VYZOR Analytics Platform - Login Script
 * Handles authentication with Supabase via Flask backend
 */

document.addEventListener('DOMContentLoaded', () => {
    // Inicialização
    initializeLogin();
    
    // Verificar se já existe uma sessão ativa
    checkSession();
});

function initializeLogin() {
    console.log('🔐 Inicializando página de login...');
    
    // Aplicar tema inicial
    applyTheme(getStoredTheme());
    
    // Configurar listeners de eventos
    setupEventListeners();
    
    // Esconder tela de carregamento
    setTimeout(() => {
        hideLoadingScreen();
    }, 1000);
}

function setupEventListeners() {
    // Formulário de login
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Alternador de tema
    const themeToggle = document.getElementById('theme-toggle-login');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
}

async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const errorMessage = document.getElementById('error-message');
    
    if (!email || !password) {
        showError(errorMessage, 'Por favor, preencha todos os campos.');
        return;
    }
    
    try {
        // Mostrar indicador de carregamento
        const loginButton = document.querySelector('.login-button');
        loginButton.textContent = 'Entrando...';
        loginButton.disabled = true;
        
        // Fazer requisição para o backend Python
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Login bem-sucedido
            console.log('✅ Login realizado com sucesso!');
            
            // Salvar informações da sessão
            sessionStorage.setItem('vyzor-auth', 'true');
            sessionStorage.setItem('vyzor-user-email', email);
            if (data.token) {
                sessionStorage.setItem('vyzor-token', data.token);
            }
            
            // Redirecionar para a página principal
            window.location.href = 'index.html';
        } else {
            // Login falhou
            showError(errorMessage, data.message || 'Email ou senha incorretos. Tente novamente.');
            loginButton.textContent = 'Entrar';
            loginButton.disabled = false;
        }
    } catch (error) {
        console.error('❌ Erro ao fazer login:', error);
        showError(errorMessage, 'Erro ao conectar com o servidor. Tente novamente mais tarde.');
        
        const loginButton = document.querySelector('.login-button');
        loginButton.textContent = 'Entrar';
        loginButton.disabled = false;
    }
}

function showError(element, message) {
    element.textContent = message;
    element.classList.add('visible');
    
    // Esconder a mensagem após 5 segundos
    setTimeout(() => {
        element.classList.remove('visible');
    }, 5000);
}

function hideLoadingScreen() {
    const loadingScreen = document.getElementById('loading');
    const loginContainer = document.getElementById('login-container');
    
    if (loadingScreen && loginContainer) {
        loadingScreen.style.opacity = '0';
        setTimeout(() => {
            loadingScreen.classList.add('hidden');
            loginContainer.classList.remove('hidden');
        }, 500);
    }
}

function getStoredTheme() {
    // Padrão: modo escuro quando não houver preferência salva
    const stored = localStorage.getItem('vyzor-theme');
    return stored ? stored : 'dark';
}

function applyTheme(theme) {
    if (theme === 'dark') {
        document.body.classList.add('dark');
        document.getElementById('theme-icon-light-login')?.classList.add('hidden');
        document.getElementById('theme-icon-dark-login')?.classList.remove('hidden');
    } else {
        document.body.classList.remove('dark');
        document.getElementById('theme-icon-light-login')?.classList.remove('hidden');
        document.getElementById('theme-icon-dark-login')?.classList.add('hidden');
    }
}

function toggleTheme() {
    const currentTheme = getStoredTheme();
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    localStorage.setItem('vyzor-theme', newTheme);
    applyTheme(newTheme);
}

// Verificar se já existe uma sessão ativa
function checkSession() {
    const isAuthenticated = sessionStorage.getItem('vyzor-auth');
    
    if (isAuthenticated === 'true') {
        // Se já estiver autenticado, redirecionar para a página principal
        window.location.href = 'index.html';
    }
}

// Função para fazer logout
function logout() {
    // Limpar dados da sessão
    sessionStorage.removeItem('vyzor-auth');
    sessionStorage.removeItem('vyzor-user-email');
    
    // Redirecionar para a página de login
    window.location.href = 'login.html';
}