/**
 * VYZOR Analytics Platform - Complete JavaScript Application
 * Main application logic, theme management, and UI interactions
 */

class VyzorApp {
    constructor() {
        this.currentPage = 'overview';
        this.theme = this.getStoredTheme();
        this.data = new Map();
        this.charts = new Map();
        this.chatHistory = [];
        
        // Verificar autenticação antes de inicializar
        this.checkAuthentication();
    }

    // Verificar se o usuário está autenticado
    checkAuthentication() {
        const isAuthenticated = sessionStorage.getItem('vyzor-auth');
        
        if (isAuthenticated !== 'true') {
            // Se não estiver autenticado, redirecionar para a página de login
            console.log('🔒 Usuário não autenticado. Redirecionando para login...');
            window.location.href = 'login.html';
            return;
        }
        
        // Se estiver autenticado, inicializar a aplicação
        this.init();
    }
    
    async init() {
        console.log('🚀 Initializing VYZOR Analytics Platform...');
        
        try {
            // Apply initial theme
            this.applyTheme(this.theme);
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Apply stored company name to the sidebar brand
            this.applyCompanyName(this.getStoredCompanyName());
            
            // Carregar estatísticas reais do backend ANTES dos mocks
            await this.loadDashboardStats();

            // Load mock data (permanece para dados não críticos)
            this.loadMockData();
            
            // Initialize current page
            this.showPage(this.currentPage);
            
            // Hide loading screen
            setTimeout(() => {
                this.hideLoadingScreen();
            }, 2000);
            
            // Initialize charts
            setTimeout(() => {
                this.initializeCharts();
            }, 2500);
            
            // Atualizar informações do usuário
            this.updateUserInfo();
            
            console.log('✅ VYZOR Analytics Platform initialized successfully');
            
        } catch (error) {
            console.error('❌ Error initializing application:', error);
            this.showNotification('Erro ao inicializar aplicação', 'error');
        }
    }

    setupEventListeners() {
        // Navigation
        document.addEventListener('click', (e) => {
            const navItem = e.target.closest('[data-page]');
            if (navItem) {
                e.preventDefault();
                const page = navItem.dataset.page;
                this.navigateToPage(page);
            }
        });

        // Settings navigation
        document.addEventListener('click', (e) => {
            const settingsNavItem = e.target.closest('[data-section]');
            if (settingsNavItem) {
                e.preventDefault();
                const section = settingsNavItem.dataset.section;
                this.showSettingsSection(section);
            }
        });

        // Mobile menu toggle (only for mobile)
        const mobileMenu = document.getElementById('mobile-menu');
        if (mobileMenu) {
            mobileMenu.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }

        // Mobile overlay
        const mobileOverlay = document.getElementById('mobile-overlay');
        if (mobileOverlay) {
            mobileOverlay.addEventListener('click', () => {
                this.closeSidebar();
            });
        }

        // Theme toggle
        // Removido: alternador no header. Agora o tema é controlado pela seção Aparência.
        // Controle via quadrados de tema na página de Configurações
        document.querySelectorAll('.theme-option').forEach(option => {
            option.addEventListener('click', () => {
                const selected = option.dataset.theme; // 'light' | 'dark' | 'auto'
                this.setThemeFromSelector(selected);
            });
        });
        
        // Logout (abre modal de confirmação)
        const userProfile = document.querySelector('.user-profile');
        if (userProfile) {
            userProfile.addEventListener('click', () => {
                this.showLogoutConfirm();
            });
        }

        // Chat functionality
        const sendMessage = document.getElementById('send-message');
        const chatInput = document.getElementById('chat-input');
        const clearChat = document.getElementById('clear-chat');
        
        // Adicionar mais métodos para a aplicação
    }
    
    // Atualizar informações do usuário
    updateUserInfo() {
        const userEmail = sessionStorage.getItem('vyzor-user-email');
        const userName = document.querySelector('.user-name');
        
        if (userEmail && userName) {
            // Exibir o email do usuário ou nome se disponível
            if (userEmail === 'adm@vyzor.com') {
                userName.textContent = 'Administrador';
            } else {
                userName.textContent = userEmail.split('@')[0];
            }
        }
    }
    
    // Função para fazer logout (sem prompt nativo)
    logout() {
        // Limpar dados da sessão e redirecionar
        sessionStorage.removeItem('vyzor-auth');
        sessionStorage.removeItem('vyzor-user-email');
        window.location.href = 'login.html';
    }

    // Modal de confirmação de logout
    showLogoutConfirm() {
        let backdrop = document.getElementById('logout-confirm');
        if (!backdrop) {
            // Cria estrutura se não existir (fallback)
            backdrop = document.createElement('div');
            backdrop.id = 'logout-confirm';
            backdrop.className = 'confirm-backdrop';
            backdrop.innerHTML = `
                <div class="confirm-modal" role="dialog" aria-modal="true">
                    <h3>Deseja realmente sair?</h3>
                    <div class="confirm-actions">
                        <button id="logout-yes" class="btn-primary">Sim</button>
                        <button id="logout-no" class="btn-secondary">Não</button>
                    </div>
                </div>`;
            document.body.appendChild(backdrop);
        }

        backdrop.classList.add('active');

        const onClose = () => {
            backdrop.classList.remove('active');
        };

        const yesBtn = backdrop.querySelector('#logout-yes');
        const noBtn = backdrop.querySelector('#logout-no');

        const handleYes = () => {
            yesBtn.removeEventListener('click', handleYes);
            noBtn.removeEventListener('click', handleNo);
            backdrop.removeEventListener('click', handleBackdrop);
            this.logout();
        };
        const handleNo = () => {
            yesBtn.removeEventListener('click', handleYes);
            noBtn.removeEventListener('click', handleNo);
            backdrop.removeEventListener('click', handleBackdrop);
            onClose();
        };
        const handleBackdrop = (e) => {
            if (e.target === backdrop) {
                handleNo();
            }
        };

        yesBtn.addEventListener('click', handleYes);
        noBtn.addEventListener('click', handleNo);
        backdrop.addEventListener('click', handleBackdrop);
    }

    // ==========================================
    // NAVIGATION AND PAGE MANAGEMENT
    // ==========================================

    navigateToPage(page) {
        if (this.currentPage === page) return;
        
        this.currentPage = page;
        this.showPage(page);
        this.updateNavigation(page);
        this.updatePageTitle(page);
        this.closeSidebar();
        
        // Initialize page-specific functionality
        setTimeout(() => {
            this.initializePage(page);
        }, 100);
    }

    showPage(page) {
        // Hide all pages
        document.querySelectorAll('.page').forEach(p => {
            p.classList.remove('active');
        });
        
        // Show current page
        const pageElement = document.getElementById(`${page}-page`);
        if (pageElement) {
            pageElement.classList.add('active');
        }
    }

    updateNavigation(page) {
        // Remove active class from all nav items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Add active class to current page
        const activeNavItem = document.querySelector(`[data-page="${page}"]`);
        if (activeNavItem) {
            activeNavItem.classList.add('active');
        }
    }

    updatePageTitle(page) {
        const pageTitles = {
            'overview': 'Dashboard',
            'sales-dashboard': 'Vendas',
            'marketing-dashboard': 'Marketing',
            'operations-dashboard': 'Operações',
            'cs-dashboard': 'Customer Success',
            'finance-dashboard': 'Financeiro',
            'data-import': 'Importar Dados',
            'goals': 'Metas',
            'reports': 'Relatórios',
            'assistant': 'Assistente',
            'admin': 'Usuários',
            'settings': 'Configurações'
        };
        
        const pageTitle = document.getElementById('page-title');
        if (pageTitle) {
            pageTitle.textContent = pageTitles[page] || 'VYZOR';
        }
    }

    initializePage(page) {
        switch (page) {
            case 'overview':
                this.initializeDashboard();
                break;
            case 'sales-dashboard':
                this.initializeSales();
                break;
            case 'marketing-dashboard':
                this.initializeMarketing();
                break;
            case 'operations-dashboard':
                this.initializeOperations();
                break;
            case 'cs-dashboard':
                this.initializeCustomerSuccess();
                break;
            case 'finance-dashboard':
                this.initializeFinance();
                break;
            case 'assistant':
                this.initializeAssistant();
                break;
            case 'admin':
                this.initializeUsers();
                break;
            case 'settings':
                this.initializeSettings();
                break;
        }
    }

    // ==========================================
    // SIDEBAR MANAGEMENT
    // ==========================================

    toggleSidebar() {
        // Only for mobile
        if (window.innerWidth <= 768) {
            const sidebar = document.getElementById('sidebar');
            const mobileOverlay = document.getElementById('mobile-overlay');
            
            if (sidebar) {
                const isOpen = sidebar.classList.contains('open');
                
                if (isOpen) {
                    this.closeSidebar();
                } else {
                    this.openSidebar();
                }
            }
        }
    }

    openSidebar() {
        const sidebar = document.getElementById('sidebar');
        const mobileOverlay = document.getElementById('mobile-overlay');
        
        if (sidebar && window.innerWidth <= 768) {
            sidebar.classList.add('open');
            
            if (mobileOverlay) {
                mobileOverlay.classList.remove('hidden');
                mobileOverlay.classList.add('show');
                document.body.style.overflow = 'hidden';
            }
        }
    }

    closeSidebar() {
        const sidebar = document.getElementById('sidebar');
        const mobileOverlay = document.getElementById('mobile-overlay');
        
        if (sidebar && window.innerWidth <= 768) {
            sidebar.classList.remove('open');
            
            if (mobileOverlay) {
                mobileOverlay.classList.add('hidden');
                mobileOverlay.classList.remove('show');
                document.body.style.overflow = '';
            }
        }
    }

    handleResize() {
        // Auto-close sidebar on resize to desktop
        if (window.innerWidth > 768) {
            this.closeSidebar();
        }
    }

    // ==========================================
    // THEME MANAGEMENT
    // ==========================================

    getStoredTheme() {
        try {
            const stored = localStorage.getItem('vyzor-theme');
            if (stored) return stored;
            // Padrão: iniciar em modo escuro quando não houver preferência salva
            return 'dark';
        } catch (error) {
            return 'dark';
        }
    }

    applyTheme(theme) {
        const html = document.documentElement;
        const effective = theme === 'system'
            ? (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
            : theme;
        const lightIcon = document.getElementById('theme-icon-light');
        const darkIcon = document.getElementById('theme-icon-dark');
        
        // Remove existing theme classes
        html.classList.remove('light', 'dark');
        
        // Apply new theme
        html.classList.add(effective);
        html.classList.add('theme-transition');
        
        // Update theme icons
        if (lightIcon && darkIcon) {
            if (effective === 'dark') {
                lightIcon.classList.add('hidden');
                darkIcon.classList.remove('hidden');
            } else {
                lightIcon.classList.remove('hidden');
                darkIcon.classList.add('hidden');
            }
        }
        
        // Remove transition class after animation
        setTimeout(() => {
            html.classList.remove('theme-transition');
        }, 300);
        
        this.updateThemeSelectorActive(this.theme);
        console.log(`🎨 Theme applied: ${effective} (mode: ${this.theme})`);
    }

    toggleTheme() {
        const newTheme = this.theme === 'light' ? 'dark' : 'light';
        this.theme = newTheme;
        this.applyTheme(newTheme);
        this.saveTheme(newTheme);
    }

    saveTheme(theme) {
        try {
            localStorage.setItem('vyzor-theme', theme);
        } catch (error) {
            console.warn('Could not save theme preference:', error);
        }
    }

    setThemeFromSelector(selected) {
        // Map 'auto' to 'system' preference
        const pref = selected === 'auto' ? 'system' : selected;
        this.theme = pref;
        const apply = pref === 'system'
            ? (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
            : pref;
        this.applyTheme(apply);
        this.saveTheme(pref);
        this.updateThemeSelectorActive(pref);
    }

    updateThemeSelectorActive(pref) {
        const activeKey = pref === 'system' ? 'auto' : pref; // Reflect UI choice
        document.querySelectorAll('.theme-option').forEach(opt => {
            opt.classList.toggle('active', opt.dataset.theme === activeKey);
        });
    }

    // ==========================================
    // COMPANY NAME MANAGEMENT
    // ==========================================
    getStoredCompanyName() {
        try {
            return localStorage.getItem('vyzor-company-name') || 'VYZOR';
        } catch (error) {
            return 'VYZOR';
        }
    }
    
    applyCompanyName(name) {
        const brandEl = document.getElementById('company-name-display') || document.querySelector('.logo-text h1');
        if (brandEl) {
            brandEl.textContent = name;
        }
    }
    
    saveCompanyName(name) {
        try {
            localStorage.setItem('vyzor-company-name', name);
        } catch (error) {
            console.warn('Could not save company name:', error);
        }
    }

    // ==========================================
    // DATA MANAGEMENT
    // ==========================================
    async loadDashboardStats() {
        try {
            // 1) Receita Total via API dedicada
            try {
                const total = await this.fetchReceitaTotal();
                this.updateReceitaTotalKPI(total);
            } catch (e) {
                console.warn('Falha ao carregar Receita Total:', e);
            }

            // 2) Indicadores filtrados pelos labels presentes no DOM
            const labelEls = Array.from(document.querySelectorAll('#overview-page .kpi-card .kpi-label'));
            const nomes = labelEls.map(el => (el.textContent || '').trim()).filter(Boolean);
            const qs = nomes.length ? ('?nomes=' + nomes.map(n => encodeURIComponent(n)).join(',')) : '';

            try {
                const resp = await fetch('/api/indicadores/filtrados' + qs);
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const json = await resp.json();
                if (!json.success) throw new Error(json.message || 'Resposta sem sucesso');
                const indicadores = Array.isArray(json.data) ? json.data : [];

                // Atualiza cada card do dashboard com o indicador correspondente
                const cards = document.querySelectorAll('#overview-page .kpi-card');
                cards.forEach(card => {
                    const labelEl = card.querySelector('.kpi-label');
                    const valueEl = card.querySelector('.kpi-value');
                    if (!labelEl || !valueEl) return;

                    const nomeLabel = (labelEl.textContent || '').trim().toLowerCase();
                    const ind = indicadores.find(i => {
                        const n = (i.nome || i.title || '').trim().toLowerCase();
                        return n === nomeLabel;
                    });
                    valueEl.textContent = ind ? this.formatIndicadorValue(ind) : '—';
                });
            } catch (e) {
                console.warn('Falha ao carregar indicadores filtrados:', e);
            }
        } catch (error) {
            console.error('Erro em loadDashboardStats:', error);
        }
    }

    formatIndicadorValue(indicador) {
        const nome = indicador.nome || indicador.title || '';
        const prefixo = indicador.prefixo || '';
        const valor = indicador.valor ?? indicador.valor_atual ?? indicador.total ?? indicador.value;
        if (valor == null) return '—';

        const nomeLower = String(nome).toLowerCase();
        if (prefixo === 'R$' || nomeLower.includes('receita') || nomeLower.includes('ticket')) {
            return this.formatCurrencyBRL(valor);
        }
        if (nomeLower.includes('taxa') || String(valor).toString().endsWith('%')) {
            const n = Number(String(valor).replace('%','').replace(',','.'));
            return Number.isNaN(n) ? String(valor) : `${n.toFixed(1)}%`;
        }
        const n = Number(valor);
        return Number.isNaN(n) ? String(valor) : n.toLocaleString('pt-BR');
    }

    loadMockData() {
        // Dashboard data
        this.data.set('dashboard', {
            kpis: [
                { title: 'Receita Total', value: 'R$ 2.847.293', change: 12.5, icon: '💰' },
                { title: 'Novos Clientes', value: '1.247', change: 8.7, icon: '👥' },
                { title: 'Taxa Conversão', value: '23.4%', change: -2.1, icon: '🎯' },
                { title: 'Ticket Médio', value: 'R$ 2.605', change: 5.2, icon: '🛒' }
            ],
            recentOrders: this.generateRecentOrders()
        });

        // Sales data
        this.data.set('sales', {
            kpis: [
                { title: 'Receita Total', value: 'R$ 3.248.750', change: 15.3, icon: '💰' },
                { title: 'Pedidos', value: '1.247', change: 8.7, icon: '🛒' },
                { title: 'Ticket Médio', value: 'R$ 2.605', change: 5.2, icon: '📊' },
                { title: 'Taxa Conversão', value: '23.4%', change: -2.1, icon: '🎯' }
            ]
        });

        // Marketing data
        this.data.set('marketing', {
            kpis: [
                { title: 'CAC Médio', value: 'R$ 127', change: -8.3, icon: '🎯' },
                { title: 'ROAS Médio', value: '4.2x', change: 15.7, icon: '📈' },
                { title: 'Leads Gerados', value: '3.847', change: 23.4, icon: '👥' },
                { title: 'Conversões', value: '892', change: 18.2, icon: '🎯' }
            ]
        });

        console.log('📊 Mock data loaded successfully');
    }

    generateRecentOrders() {
        const customers = ['TechCorp', 'Innovate Sol.', 'Digital Dyn.', 'Future Sys.', 'Global Tech'];
        const statuses = ['Pago', 'Pendente', 'Processando', 'Cancelado'];
        
        const orders = [];
        for (let i = 0; i < 10; i++) {
            orders.push({
                id: `#PED-${String(1250 - i).padStart(6, '0')}`,
                cliente: customers[Math.floor(Math.random() * customers.length)],
                valor: `R$ ${(Math.random() * 50000 + 5000).toLocaleString('pt-BR')}`,
                status: statuses[Math.floor(Math.random() * statuses.length)],
                data: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toLocaleDateString('pt-BR')
            });
        }
        
        return orders;
    }

    // ==========================================
    // PAGE INITIALIZATION
    // ==========================================

    initializeDashboard() {
        // Update recent orders table
        const tableBody = document.querySelector('#recent-orders-table tbody');
        if (tableBody) {
            const orders = this.data.get('dashboard').recentOrders;
            tableBody.innerHTML = orders.map(order => `
                <tr>
                    <td>${order.id}</td>
                    <td>${order.cliente}</td>
                    <td>${order.valor}</td>
                    <td><span class="status-badge ${this.getStatusClass(order.status)}">${order.status}</span></td>
                    <td>${order.data}</td>
                </tr>
            `).join('');
        }

        // Buscar receita total real do backend e atualizar o KPI
        this.fetchReceitaTotal()
            .then(total => {
                this.updateReceitaTotalKPI(total);
            })
            .catch(err => {
                console.warn('Falha ao obter receita total:', err);
            });
    }

    initializeSales() {
        console.log('📊 Sales page initialized');
    }

    initializeMarketing() {
        console.log('📢 Marketing page initialized');
    }

    initializeOperations() {
        console.log('⚙️ Operations page initialized');
    }

    initializeCustomerSuccess() {
        console.log('🤝 Customer Success page initialized');
    }

    initializeFinance() {
        console.log('💼 Finance page initialized');
    }

    // ==========================================
    // RECEITA TOTAL (Supabase via Flask)
    // ==========================================
    async fetchReceitaTotal() {
        try {
            const token = sessionStorage.getItem('vyzor-token') || '';
            const resp = await fetch('/api/receita-total', {
                headers: token ? { 'X-Auth-Token': token } : {}
            });
            if (!resp.ok) return null;
            const data = await resp.json();
            // Se o backend sinalizar falha ou total inválido, retorna null para UI mostrar "Não deu"
            if (!data || data.success === false) return null;
            const n = Number(data.total);
            // Permite zero; só invalida NaN ou infinito
            if (!isFinite(n)) return null;
            return n;
        } catch (e) {
            console.warn('Erro ao buscar receita total:', e);
            return null;
        }
    }

    updateReceitaTotalKPI(total) {
        // Determina texto a exibir: número formatado ou "Não deu"
        const formatted = (total == null) ? 'Não deu' : this.formatCurrencyBRL(total);

        // Localizar o card com label "Receita Total" no Dashboard principal
        const cards = document.querySelectorAll('#overview-page .kpi-card');
        cards.forEach(card => {
            const labelEl = card.querySelector('.kpi-label');
            if (labelEl && labelEl.textContent.trim() === 'Receita Total') {
                const valueEl = card.querySelector('.kpi-value');
                if (valueEl) valueEl.textContent = formatted;
            }
        });
    }

    formatCurrencyBRL(value) {
        try {
            return 'R$ ' + Number(value).toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        } catch (e) {
            return `R$ ${value}`;
        }
    }

    initializeUsers() {
        // Initialize users table
        const tableBody = document.querySelector('#users-table tbody');
        if (tableBody) {
            const users = [
                { name: 'João Silva', email: 'joao.silva@empresa.com', role: 'Admin', status: 'Online', lastAccess: '14:35' },
                { name: 'Maria Santos', email: 'maria.santos@empresa.com', role: 'Analista', status: 'Online', lastAccess: '14:20' },
                { name: 'Pedro Costa', email: 'pedro.costa@empresa.com', role: 'Vendedor', status: 'Ausente', lastAccess: '13:45' },
                { name: 'Ana Oliveira', email: 'ana.oliveira@empresa.com', role: 'Marketing', status: 'Online', lastAccess: '14:32' },
                { name: 'Carlos Ferreira', email: 'carlos.ferreira@empresa.com', role: 'Financeiro', status: 'Offline', lastAccess: '12:15' }
            ];
            
            tableBody.innerHTML = users.map(user => `
                <tr>
                    <td>${user.name}</td>
                    <td>${user.email}</td>
                    <td>${user.role}</td>
                    <td><span class="status-badge ${this.getStatusClass(user.status)}">${user.status}</span></td>
                    <td>${user.lastAccess}</td>
                    <td>
                        <button class="btn-secondary">Editar</button>
                        <button class="btn-secondary">Desativar</button>
                    </td>
                </tr>
            `).join('');
        }
        console.log('👥 Users page initialized');
    }

    initializeSettings() {
        console.log('⚙️ Settings page initialized');
        // Wire up company name input and save button
        const input = document.getElementById('company-name-input');
        const saveBtn = document.getElementById('save-company');
        
        if (input) {
            const storedName = this.getStoredCompanyName();
            if (storedName) input.value = storedName;
        }
        
        if (input && saveBtn) {
            saveBtn.addEventListener('click', () => {
                const newName = (input.value || '').trim();
                if (!newName) {
                    this.showNotification('Informe um nome válido para a empresa', 'warning');
                    return;
                }
                this.applyCompanyName(newName);
                this.saveCompanyName(newName);
                this.showNotification('Nome da empresa atualizado com sucesso', 'success');
            });
        }
    }

    showSettingsSection(section) {
        // Hide all settings sections
        document.querySelectorAll('.settings-section').forEach(s => {
            s.classList.remove('active');
        });
        
        // Remove active class from all nav items
        document.querySelectorAll('.settings-nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Show selected section
        const sectionElement = document.getElementById(`${section}-settings`);
        if (sectionElement) {
            sectionElement.classList.add('active');
        }
        
        // Add active class to selected nav item
        const activeNavItem = document.querySelector(`[data-section="${section}"]`);
        if (activeNavItem) {
            activeNavItem.classList.add('active');
        }
    }

    initializeAssistant() {
        // Initialize chat history
        this.chatHistory = [
            {
                type: 'assistant',
                message: 'Olá! Sou seu assistente VYZOR. Posso ajudá-lo com análises de dados, relatórios e insights sobre seu negócio. Como posso ajudar hoje?',
                time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
            }
        ];
        
        this.updateChatDisplay();
        console.log('🤖 Assistant initialized');
    }

    // ==========================================
    // CHAT FUNCTIONALITY
    // ==========================================

    sendChatMessage(message = null) {
        const chatInput = document.getElementById('chat-input');
        const messageText = message || (chatInput ? chatInput.value.trim() : '');
        
        if (!messageText) return;
        
        // Add user message
        this.chatHistory.push({
            type: 'user',
            message: messageText,
            time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
        });
        
        // Clear input
        if (chatInput && !message) {
            chatInput.value = '';
        }
        
        // Update display
        this.updateChatDisplay();
        
        // Generate AI response
        setTimeout(() => {
            const response = this.generateAIResponse(messageText);
            this.chatHistory.push({
                type: 'assistant',
                message: response,
                time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
            });
            
            this.updateChatDisplay();
        }, 1000);
    }

    generateAIResponse(userMessage) {
        const message = userMessage.toLowerCase();
        
        if (message.includes('receita') || message.includes('faturamento')) {
            return '📈 Com base nos dados atuais, a receita total é R$ 2.847.293 (+12.5% vs mês anterior). O crescimento está sólido, com destaque para o aumento no ticket médio de +5.2%. Recomendo focar na conversão, que está em -2.1%.';
        }
        
        if (message.includes('cliente') || message.includes('clientes')) {
            return '👥 Temos 1.247 novos clientes este mês (+8.7%). Os top 5 clientes por receita são: TechCorp (R$ 485K), Innovate Solutions (R$ 423K), Digital Dynamics (R$ 387K), Future Systems (R$ 356K) e Global Tech (R$ 298K). A taxa de churn está em 2.1%.';
        }
        
        if (message.includes('venda') || message.includes('vendas')) {
            return '💰 Performance de vendas excelente! 1.247 pedidos este mês (+8.7%), receita de R$ 3.248.750 (+15.3%), ticket médio de R$ 2.605 (+5.2%). A taxa de conversão está em 23.4%, ligeiramente abaixo do esperado (-2.1%).';
        }
        
        if (message.includes('marketing') || message.includes('campanha')) {
            return '📢 Marketing performando muito bem! ROAS médio de 4.2x (+15.7%), CAC de R$ 127 (-8.3%), 3.847 leads gerados (+23.4%) e 892 conversões (+18.2%). As campanhas de Black Friday estão sendo destaque.';
        }
        
        if (message.includes('meta') || message.includes('objetivo')) {
            return '🎯 Progresso das metas mensais: Receita 94.9% (R$ 2.847.293/R$ 3M), Novos Clientes 83.1% (1.247/1.500), Leads 96.2% (3.847/4K), Conversão 93.6% (23.4%/25%). Estamos no caminho certo para superar os objetivos!';
        }
        
        if (message.includes('projeção') || message.includes('previsão')) {
            return '🔮 Baseado na tendência atual, a projeção para o próximo trimestre é: R$ 9.8M de receita (+12% vs atual), ~3.900 novos clientes (+8%), melhor mês projetado é dezembro. Recomendo preparar campanhas intensivas para Q4.';
        }
        
        // Default response
        return '💡 Interessante pergunta! Baseado nos dados disponíveis, posso ajudar com análises específicas sobre vendas, marketing, clientes, metas, projeções e muito mais. Que área gostaria de explorar primeiro?';
    }

    updateChatDisplay() {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;
        
        chatMessages.innerHTML = this.chatHistory.map(msg => `
            <div class="chat-message ${msg.type}">
                <div class="message-avatar">
                    ${msg.type === 'user' ? '👤' : '🤖'}
                </div>
                <div class="message-content">
                    <strong>${msg.type === 'user' ? 'Você' : 'Assistente VYZOR'}:</strong><br>
                    ${msg.message}
                    <div class="message-time">${msg.time}</div>
                </div>
            </div>
        `).join('');
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    clearChat() {
        this.chatHistory = [
            {
                type: 'assistant',
                message: 'Chat limpo! Como posso ajudá-lo agora?',
                time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
            }
        ];
        
        this.updateChatDisplay();
    }

    // ==========================================
    // CHARTS INITIALIZATION
    // ==========================================

    initializeCharts() {
        try {
            this.createRevenueChart();
            this.createPipelineChart();
            this.createCustomersChart();
            this.createSalesPipelineChart();
            this.createCampaignsChart();
            this.createChannelsChart();
            this.createOperationsChart();
            this.createTimeChart();
            this.createHealthChart();
            this.createNpsChart();
            this.createDreChart();
            this.createCashflowChart();
            
            console.log('📊 Charts initialized successfully');
        } catch (error) {
            console.warn('⚠️ Charts initialization failed:', error);
        }
    }

    createRevenueChart() {
        const canvas = document.getElementById('revenue-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.charts.has('revenue')) {
            this.charts.get('revenue').destroy();
        }

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
                datasets: [
                    {
                        label: 'Receita Bruta',
                        data: [2800000, 2950000, 3100000, 2950000, 3200000, 3350000, 3450000, 3300000, 3500000, 3650000, 3750000, 3600000],
                        borderColor: '#cbb26a',
                        backgroundColor: 'rgba(203, 178, 106, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Receita Líquida',
                        data: [2520000, 2655000, 2790000, 2655000, 2880000, 3015000, 3105000, 2970000, 3150000, 3285000, 3375000, 3240000],
                        borderColor: '#eee293',
                        backgroundColor: 'rgba(238, 226, 147, 0.1)',
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return 'R$ ' + (value / 1000000).toFixed(1) + 'M';
                            }
                        }
                    }
                }
            }
        });

        this.charts.set('revenue', chart);
    }

    createPipelineChart() {
        const canvas = document.getElementById('pipeline-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.charts.has('pipeline')) {
            this.charts.get('pipeline').destroy();
        }

        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Leads', 'Qualificados', 'Oportunidades', 'Propostas', 'Negociação', 'Fechados'],
                datasets: [{
                    data: [8420, 6240, 4180, 2850, 1680, 1247],
                    backgroundColor: [
                        '#cbb26a',
                        '#eee293',
                        '#28a745',
                        '#2196f3',
                        '#ff9800',
                        '#e53935'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                    }
                }
            }
        });

        this.charts.set('pipeline', chart);
    }

    createCustomersChart() {
        const canvas = document.getElementById('customers-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.charts.has('customers')) {
            this.charts.get('customers').destroy();
        }

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['TechCorp', 'Innovate Sol.', 'Digital Dyn.', 'Future Sys.', 'Global Tech', 'Smart Ind.'],
                datasets: [{
                    label: 'Receita (R$)',
                    data: [485750, 423600, 387200, 356800, 298500, 234700],
                    backgroundColor: '#cbb26a',
                    borderColor: '#cbb26a',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return 'R$ ' + (value / 1000).toFixed(0) + 'K';
                            }
                        }
                    }
                }
            }
        });

        this.charts.set('customers', chart);
    }

    createSalesPipelineChart() {
        const canvas = document.getElementById('sales-pipeline-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.charts.has('salesPipeline')) {
            this.charts.get('salesPipeline').destroy();
        }

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Leads', 'Qualificados', 'Oportunidades', 'Propostas', 'Negociação', 'Fechados'],
                datasets: [{
                    label: 'Quantidade',
                    data: [8420, 6240, 4180, 2850, 1680, 1247],
                    backgroundColor: '#cbb26a',
                    borderColor: '#cbb26a',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        this.charts.set('salesPipeline', chart);
    }

    createCampaignsChart() {
        const canvas = document.getElementById('campaigns-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.charts.has('campaigns')) {
            this.charts.get('campaigns').destroy();
        }

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Black Friday', 'Verão Collection', 'Back to School', 'Natal Premium', 'Liquidação Jan'],
                datasets: [
                    {
                        label: 'Investimento',
                        data: [45000, 32000, 28000, 38000, 25000],
                        backgroundColor: '#cbb26a',
                        borderColor: '#cbb26a',
                        borderWidth: 1
                    },
                    {
                        label: 'Retorno',
                        data: [189000, 128000, 84000, 152000, 75000],
                        backgroundColor: '#eee293',
                        borderColor: '#eee293',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return 'R$ ' + (value / 1000).toFixed(0) + 'K';
                            }
                        }
                    }
                }
            }
        });

        this.charts.set('campaigns', chart);
    }

    createChannelsChart() {
        const canvas = document.getElementById('channels-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.charts.has('channels')) {
            this.charts.get('channels').destroy();
        }

        const chart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Google Ads', 'Facebook Ads', 'Instagram Ads', 'LinkedIn Ads', 'E-mail Marketing', 'SEO Orgânico'],
                datasets: [{
                    data: [35, 28, 18, 12, 5, 2],
                    backgroundColor: [
                        '#cbb26a',
                        '#eee293',
                        '#28a745',
                        '#2196f3',
                        '#ff9800',
                        '#e53935'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });

        this.charts.set('channels', chart);
    }

    createOperationsChart() {
        const canvas = document.getElementById('operations-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        if (this.charts.has('operations')) {
            this.charts.get('operations').destroy();
        }

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Atendimento', 'Produção', 'Logística', 'Qualidade', 'Vendas'],
                datasets: [{
                    label: 'Eficiência (%)',
                    data: [94.2, 87.9, 91.5, 98.7, 92.3],
                    backgroundColor: '#cbb26a',
                    borderColor: '#cbb26a',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });

        this.charts.set('operations', chart);
    }

    createTimeChart() {
        const canvas = document.getElementById('time-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        if (this.charts.has('time')) {
            this.charts.get('time').destroy();
        }

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
                datasets: [{
                    label: 'Tempo Médio (horas)',
                    data: [2.4, 2.1, 2.3, 2.0, 2.2, 1.8, 1.9],
                    borderColor: '#eee293',
                    backgroundColor: 'rgba(238, 226, 147, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        this.charts.set('time', chart);
    }

    createHealthChart() {
        const canvas = document.getElementById('health-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        if (this.charts.has('health')) {
            this.charts.get('health').destroy();
        }

        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Excelente (9-10)', 'Bom (7-8)', 'Regular (5-6)', 'Ruim (1-4)'],
                datasets: [{
                    data: [45, 35, 15, 5],
                    backgroundColor: [
                        '#28a745',
                        '#cbb26a',
                        '#ff9800',
                        '#e53935'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        this.charts.set('health', chart);
    }

    createNpsChart() {
        const canvas = document.getElementById('nps-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        if (this.charts.has('nps')) {
            this.charts.get('nps').destroy();
        }

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                datasets: [{
                    label: 'NPS Score',
                    data: [58, 62, 65, 68, 70, 72],
                    borderColor: '#cbb26a',
                    backgroundColor: 'rgba(203, 178, 106, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });

        this.charts.set('nps', chart);
    }

    createDreChart() {
        const canvas = document.getElementById('dre-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        if (this.charts.has('dre')) {
            this.charts.get('dre').destroy();
        }

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                datasets: [
                    {
                        label: 'Receita',
                        data: [2800000, 2920000, 2750000, 3100000, 2980000, 2923000],
                        backgroundColor: '#28a745',
                        borderColor: '#28a745',
                        borderWidth: 1
                    },
                    {
                        label: 'Custos',
                        data: [-1680000, -1752000, -1650000, -1860000, -1788000, -1754000],
                        backgroundColor: '#e53935',
                        borderColor: '#e53935',
                        borderWidth: 1
                    },
                    {
                        label: 'EBITDA',
                        data: [840000, 876000, 825000, 930000, 894000, 892400],
                        backgroundColor: '#cbb26a',
                        borderColor: '#cbb26a',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false
                    }
                }
            }
        });

        this.charts.set('dre', chart);
    }

    createCashflowChart() {
        const canvas = document.getElementById('cashflow-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        if (this.charts.has('cashflow')) {
            this.charts.get('cashflow').destroy();
        }

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                datasets: [
                    {
                        label: 'Entrada',
                        data: [2800000, 2920000, 2750000, 3100000, 2980000, 2923000],
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        fill: false,
                        tension: 0.4
                    },
                    {
                        label: 'Saída',
                        data: [2200000, 2350000, 2180000, 2450000, 2320000, 2268800],
                        borderColor: '#e53935',
                        backgroundColor: 'rgba(229, 57, 53, 0.1)',
                        fill: false,
                        tension: 0.4
                    },
                    {
                        label: 'Saldo',
                        data: [600000, 570000, 570000, 650000, 660000, 654200],
                        borderColor: '#cbb26a',
                        backgroundColor: 'rgba(203, 178, 106, 0.1)',
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        this.charts.set('cashflow', chart);
    }

    // ==========================================
    // UTILITY FUNCTIONS
    // ==========================================



    hideLoadingScreen() {
        const loadingScreen = document.getElementById('loading');
        const app = document.getElementById('app');
        
        if (loadingScreen && app) {
            loadingScreen.style.opacity = '0';
            setTimeout(() => {
                loadingScreen.style.display = 'none';
                app.classList.remove('hidden');
            }, 500);
        }
    }

    showNotification(message, type = 'info', duration = 5000) {
        const container = document.getElementById('notifications');
        if (!container) return;

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>${message}</div>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; font-size: 1.2rem; cursor: pointer; opacity: 0.7;">×</button>
            </div>
        `;

        container.appendChild(notification);

        // Auto-remove after duration
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.opacity = '0';
                setTimeout(() => {
                    notification.remove();
                }, 300);
            }
        }, duration);
    }

    // ==========================================
    // API SIMULATION
    // ==========================================

    async fetchData(endpoint) {
        // Simulate API call delay
        await new Promise(resolve => setTimeout(resolve, 500 + Math.random() * 1000));
        
        // Return mock data based on endpoint
        switch (endpoint) {
            case '/api/dashboard':
                return this.data.get('dashboard');
            case '/api/sales':
                return this.data.get('sales');
            case '/api/marketing':
                return this.data.get('marketing');
            default:
                throw new Error(`Unknown endpoint: ${endpoint}`);
        }
    }

    // ==========================================
    // KEYBOARD SHORTCUTS HELP
    // ==========================================

    showKeyboardShortcuts() {
        const shortcuts = [
            'Alt + 1: Dashboard',
            'Alt + 2: Vendas',
            'Alt + 3: Marketing',
            'Alt + T: Alternar tema'
        ];
        
        this.showNotification(
            `Atalhos do teclado:<br>${shortcuts.join('<br>')}`,
            'info',
            8000
        );
    }

    getStatusClass(status) {
        const statusClasses = {
            'Online': 'success',
            'Ausente': 'warning',
            'Offline': 'danger',
            'Pago': 'success',
            'Pendente': 'warning',
            'Processando': 'info',
            'Cancelado': 'danger'
        };
        return statusClasses[status] || 'secondary';
    }
}

// ===============================
// Preencher KPIs com indicadores reais (Supabase via Flask)
// ===============================
(function() {
  function normalizarLabel(label) {
    const t = (label || '').trim().toLowerCase();
    // Mapeia textos da UI para nomes de indicador na base
    const map = {
      'receita total': 'Receita Total',
      'taxa conversão': 'Taxa de Conversão',
      'taxa de conversão': 'Taxa de Conversão',
      'receita geral': 'Receita Geral',
      'ticket médio': 'Ticket Médio',
      'novos clientes': 'Novos Clientes',
      'pedidos': 'Pedidos'
    };
    return map[t] || null;
  }

  function formatarValor(indicador) {
    const nome = indicador.nome || indicador.title || '';
    const prefixo = indicador.prefixo || '';
    const valor = indicador.valor ?? indicador.valor_atual ?? indicador.total ?? indicador.value;
    if (valor == null) return '—';

    // Heurísticas simples de formatação
    const nomeLower = String(nome).toLowerCase();
    if (prefixo === 'R$' || nomeLower.includes('receita') || nomeLower.includes('ticket')) {
      try {
        return 'R$ ' + Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      } catch {
        return `R$ ${valor}`;
      }
    }
    if (nomeLower.includes('taxa') || String(valor).toString().endsWith('%')) {
      const n = Number(String(valor).replace('%','').replace(',','.'));
      if (!Number.isNaN(n)) return `${n.toFixed(1)}%`;
      return String(valor);
    }
    // default número puro
    const n = Number(valor);
    return Number.isNaN(n) ? String(valor) : n.toLocaleString('pt-BR');
  }

  async function buscarIndicadores() {
    try {
      // Coleta labels da UI e normaliza para nomes de indicadores
      const labelEls = Array.from(document.querySelectorAll('#overview-page .kpi-card .kpi-label'));
      const nomes = labelEls
        .map(el => normalizarLabel(el.textContent))
        .filter(n => !!n);
      const qs = nomes.length ? ('?nomes=' + nomes.map(n => encodeURIComponent(n)).join(',')) : '';

      const resp = await fetch('/api/indicadores/filtrados' + qs);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json = await resp.json();
      if (!json.success) throw new Error(json.message || 'Resposta sem sucesso');
      return Array.isArray(json.data) ? json.data : [];
    } catch (e) {
      console.warn('Falha ao buscar indicadores filtrados:', e);
      return [];
    }
  }

  function preencherKpis(indicadores) {
    const cards = document.querySelectorAll('#overview-page .kpi-card');
    cards.forEach(card => {
      const labelEl = card.querySelector('.kpi-label');
      const valueEl = card.querySelector('.kpi-value');
      if (!labelEl || !valueEl) return;

      const nomeIndicador = normalizarLabel(labelEl.textContent);
      if (!nomeIndicador) return;

      // Procura indicador correspondente
      const ind = indicadores.find(i => {
        const n = (i.nome || i.title || '').trim().toLowerCase();
        return n === nomeIndicador.trim().toLowerCase();
      });

      // Sempre substituir o valor estático: se não houver indicador, usa marcador neutro
      valueEl.textContent = ind ? formatarValor(ind) : '—';
    });
  }

  document.addEventListener('DOMContentLoaded', async () => {
    try {
      const indicadores = await buscarIndicadores();
      preencherKpis(indicadores);
    } catch (e) {
      console.warn('Preenchimento de KPIs falhou:', e);
    }
  });
})();

// ==========================================
// INITIALIZE APPLICATION
// ==========================================

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.vyzorApp = new VyzorApp();
});

// Handle browser back/forward buttons
window.addEventListener('popstate', (e) => {
    if (e.state && e.state.page && window.vyzorApp) {
        window.vyzorApp.navigateToPage(e.state.page);
    }
});

// Listen for system theme changes
if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (window.vyzorApp && window.vyzorApp.theme === 'system') {
            window.vyzorApp.applyTheme(e.matches ? 'dark' : 'light');
        }
    });
}

// Global error handler
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
    if (window.vyzorApp) {
        window.vyzorApp.showNotification('Ocorreu um erro inesperado', 'error');
    }
});

// Global unhandled promise rejection handler
window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
    if (window.vyzorApp) {
        window.vyzorApp.showNotification('Erro ao processar dados', 'error');
    }
});

// Add CSS for status badges
const style = document.createElement('style');
style.textContent = `
    .status-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .status-badge.success {
        background-color: rgba(40, 167, 69, 0.1);
        color: var(--success);
        border: 1px solid rgba(40, 167, 69, 0.2);
    }
    
    .status-badge.warning {
        background-color: rgba(255, 152, 0, 0.1);
        color: var(--warning);
        border: 1px solid rgba(255, 152, 0, 0.2);
    }
    
    .status-badge.info {
        background-color: rgba(33, 150, 243, 0.1);
        color: var(--info);
        border: 1px solid rgba(33, 150, 243, 0.2);
    }
    
    .status-badge.danger {
        background-color: rgba(229, 57, 53, 0.1);
        color: var(--danger);
        border: 1px solid rgba(229, 57, 53, 0.2);
    }
`;
document.head.appendChild(style);

console.log('🚀 VYZOR JavaScript loaded successfully');

// Export for debugging
window.VyzorApp = VyzorApp;