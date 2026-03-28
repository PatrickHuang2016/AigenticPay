/**
 * Temporal Pay Frontend Logic
 * 处理认证、数据加载、规则管理与网关模拟。
 */

document.addEventListener('DOMContentLoaded', () => {
    // 状态管理
    const state = {
        token: localStorage.getItem('token') || null,
        user: null,
        whitelist: [],
        transactions: [],
        filters: {}
    };

    // DOM 元素
    const authPage = document.getElementById('auth-page');
    const dashboardPage = document.getElementById('dashboard-page');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const tabBtns = document.querySelectorAll('.tab-btn');
    const logoutBtn = document.getElementById('logout-btn');

    const userBalanceText = document.getElementById('user-balance');
    const userEmailText = document.getElementById('user-display-email');
    const dailyLimitInput = document.getElementById('daily-limit-input');
    const saveLimitBtn = document.getElementById('save-limit-btn');
    const whitelistTags = document.getElementById('whitelist-tags');
    const newMerchantInput = document.getElementById('new-merchant-input');
    const addMerchantBtn = document.getElementById('add-merchant-btn');
    const transactionTable = document.getElementById('transaction-table').querySelector('tbody');

    const depositModal = document.getElementById('deposit-modal');
    const openDepositBtn = document.getElementById('open-deposit-modal');
    const confirmDepositBtn = document.getElementById('confirm-deposit');
    const cancelDepositBtn = document.getElementById('cancel-deposit');

    const simToggle = document.getElementById('gateway-sim-btn');
    const simPanel = document.getElementById('gateway-simulator');
    const closeSimBtn = document.getElementById('close-sim');
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const chatMessages = document.getElementById('chat-messages');

    // UI Utilities
    function showConfirm(msg, okText = "Yes, Update", cancelText = "No, Cancel") {
        return new Promise((resolve) => {
            const modal = document.getElementById('confirm-modal');
            const msgEl = document.getElementById('confirm-message');
            const okBtn = document.getElementById('confirm-ok-btn');
            const cancelBtn = document.getElementById('confirm-cancel-btn');

            msgEl.textContent = msg;
            okBtn.textContent = okText;
            cancelBtn.textContent = cancelText;

            modal.classList.add('active');

            const cleanup = () => {
                okBtn.onclick = null;
                cancelBtn.onclick = null;
                modal.classList.remove('active');
            };

            okBtn.onclick = () => { cleanup(); resolve(true); };
            cancelBtn.onclick = () => { cleanup(); resolve(false); };
        });
    }

    // --- 初始化 ---
    if (state.token) {
        showPage('dashboard');
        initDashboard();
    }

    // --- 页面切换逻辑 ---
    function showPage(pageId) {
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`${pageId}-page`).classList.add('active');
        window.scrollTo(0, 0); // 切换页面时滚动到顶部
    }

    // --- 认证逻辑 ---
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const target = btn.dataset.tab;
            loginForm.classList.toggle('active', target === 'login');
            registerForm.classList.toggle('active', target === 'register');
        });
    });

    async function handleAuth(action) {
        const email = document.getElementById(`${action}-email`).value;
        const password = document.getElementById(`${action}-password`).value;

        if (!email || !password) return alert('Please fill in all fields');

        const bodyData = { email, password };
        if (action === 'register') {
            const address = document.getElementById('register-address').value;
            if (!address) return alert('Please enter your billing address');
            bodyData.address = address;
        }

        try {
            const endpoint = action === 'login' ? '/api/token' : '/api/register';
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bodyData)
            });

            const data = await response.json();
            if (response.ok) {
                if (action === 'login') {
                    state.token = data.access_token;
                    localStorage.setItem('token', state.token);
                    showPage('dashboard');
                    initDashboard();
                } else {
                    alert('Registration successful! Please login.');
                    // Switch to login tab
                    const loginTab = document.querySelector('.tab-btn[data-tab="login"]');
                    if (loginTab) loginTab.click();
                }
            } else {
                alert(data.detail || 'Authentication failed');
            }
        } catch (err) {
            console.error(err);
            alert('Network connection failed');
        }
    }

    document.getElementById('login-submit').addEventListener('click', () => handleAuth('login'));
    document.getElementById('register-submit').addEventListener('click', () => handleAuth('register'));

    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('token');
        location.reload();
    });

    // --- Dashboard 数据加载 ---
    async function apiFetch(url, options = {}) {
        const headers = {
            'Authorization': `Bearer ${state.token}`,
            'Content-Type': 'application/json',
            ...options.headers
        };
        const response = await fetch(url, { ...options, headers });
        if (response.status === 401) {
            localStorage.removeItem('token');
            location.reload();
        }
        return response;
    }

    async function initDashboard() {
        await loadUserData();
        loadWhitelist();
        loadTransactions();
    }

    async function loadUserData() {
        const res = await apiFetch('/api/me');
        const data = await res.json();
        state.user = data;
        userBalanceText.textContent = data.balance.toFixed(2);
        userEmailText.textContent = data.email;
        dailyLimitInput.value = data.daily_limit;

        const vcardToggle = document.getElementById('vcard-toggle');
        if (vcardToggle) {
            vcardToggle.checked = data.virtual_card_enabled;
            vcardToggle.onchange = async (e) => {
                const res = await apiFetch('/api/rules', {
                    method: 'PUT',
                    body: JSON.stringify({ virtual_card_enabled: e.target.checked })
                });
                if (!res.ok) alert('Failed to update virtual card settings');
            };
        }
    }

    async function loadWhitelist() {
        const res = await apiFetch('/api/whitelist');
        const data = await res.json();
        state.whitelist = data;
        renderWhitelist();
    }

    function renderWhitelist() {
        whitelistTags.innerHTML = '';
        state.whitelist.forEach(item => {
            const tag = document.createElement('div');
            tag.className = 'tag';
            tag.innerHTML = `
                <span>${item.merchant_name} (Max: $${item.max_per_transaction})</span>
                <i class="fas fa-times" data-id="${item.id}"></i>
            `;
            tag.querySelector('i').onclick = () => removeMerchant(item.id);
            whitelistTags.appendChild(tag);
        });
    }

    async function addMerchant(forceUpdate = false, skipFuzzy = false) {
        const name = newMerchantInput.value.trim();
        const limit = parseFloat(document.getElementById('new-merchant-limit').value);
        if (!name || isNaN(limit)) return alert('Please enter both name and limit');

        const res = await apiFetch('/api/whitelist', {
            method: 'POST',
            body: JSON.stringify({
                merchant_name: name,
                max_per_transaction: limit,
                force_update: forceUpdate,
                skip_fuzzy: skipFuzzy
            })
        });

        if (res.ok) {
            newMerchantInput.value = '';
            document.getElementById('new-merchant-limit').value = '500.00';
            loadWhitelist();
        } else if (res.status === 409) {
            const err = await res.json();
            if (await showConfirm(err.detail, "Yes, Update", "No, Cancel")) {
                addMerchant(true, false);
            } else {
                alert('Addition cancelled.');
            }
        } else if (res.status === 403) {
            const err = await res.json();
            if (await showConfirm(err.detail, "Yes, it's the same", "No, it's a new merchant")) {
                if (await showConfirm(`Do you want to update the limit to $${limit}?`, "Yes, Update Limit", "Cancel")) {
                    addMerchant(true, false);
                } else {
                    alert('Addition cancelled.');
                }
            } else {
                // Not the same merchant, add as new unique one
                addMerchant(false, true);
            }
        } else {
            const err = await res.json();
            alert(`Error: ${err.detail || 'Internal error'}`);
        }
    }

    async function removeMerchant(id) {
        const res = await apiFetch(`/api/whitelist/${id}`, { method: 'DELETE' });
        if (res.ok) loadWhitelist();
    }

    async function saveLimit() {
        const limit = parseFloat(dailyLimitInput.value);
        const res = await apiFetch('/api/rules', {
            method: 'PUT',
            body: JSON.stringify({ daily_limit: limit })
        });
        if (res.ok) alert('Daily limit saved successfully');
    }

    async function loadTransactions() {
        const res = await apiFetch('/api/transactions');
        const data = await res.json();
        state.transactions = data;
        renderTransactions();
    }

    function renderTransactions() {
        transactionTable.innerHTML = '';

        const filtered = state.transactions.filter(t => {
            return Object.keys(state.filters).every(key => {
                const val = state.filters[key].toLowerCase();
                if (!val) return true;

                let cellVal = "";
                if (key === 'timestamp') cellVal = new Date(t.timestamp).toLocaleString().toLowerCase();
                else if (key === 'amount') cellVal = t.amount.toString();
                else if (key === 'type') {
                    const typeText = t.type === 'payment' ? 'Payment' : 'Deposit';
                    const statusTxt = t.status === 'failed' ? ' (Failed)' : '';
                    cellVal = (typeText + statusTxt).toLowerCase();
                }
                else cellVal = (t[key] || "-").toString().toLowerCase();

                return cellVal.includes(val);
            });
        });

        filtered.forEach(t => {
            const row = document.createElement('tr');
            const dateStr = new Date(t.timestamp).toLocaleString();
            const typeText = t.type === 'payment' ? 'Payment' : 'Deposit';
            const color = t.type === 'payment' ? (t.status === 'success' ? 'var(--danger)' : '#666') : 'var(--secondary)';
            const statusTxt = t.status === 'failed' ? ' (Failed)' : '';

            row.innerHTML = `
                <td>${dateStr}</td>
                <td><span style="color:${color}">${typeText}${statusTxt}</span></td>
                <td>${t.merchant_name || '-'}</td>
                <td style="font-weight:600">$ ${t.amount.toFixed(2)}</td>
                <td style="font-size:0.8rem; font-family:monospace">${t.request_id || '-'}</td>
                <td style="font-size:0.8rem; font-family:monospace">${t.id || '-'}</td>
                <td style="font-size:0.8rem; font-family:monospace">${t.order_id || '-'}</td>
                <td style="font-size:0.85rem; color:var(--text-dim)">${t.failed_reason || '-'}</td>
                <td style="font-size:0.8rem; font-family:monospace; font-weight:600; color:var(--primary)">${t.virtual_card_number ? '**** ' + t.virtual_card_number.slice(-4) : '<span style="color:var(--text-dim)">-</span>'}</td>
                <td style="font-size:0.8rem; font-family:monospace">${t.onchain_hash 
                    ? `<a href="https://juicy-low-small-testnet.explorer.testnet.skalenodes.com/tx/${t.onchain_hash}" target="_blank" style="color:var(--primary); text-decoration:none;">${t.onchain_hash.substring(0, 10)}...</a>` 
                    : '<span style="color:var(--text-dim)"> - </span>'}</td>
            `;
            transactionTable.appendChild(row);
        });
    }

    // --- 充值逻辑 ---
    openDepositBtn.onclick = () => depositModal.classList.add('active');
    cancelDepositBtn.onclick = () => depositModal.classList.remove('active');
    confirmDepositBtn.onclick = async () => {
        const amount = parseFloat(document.getElementById('deposit-amount').value);
        if (isNaN(amount) || amount <= 0) return alert('Please enter a valid amount');

        const res = await apiFetch('/api/deposit', {
            method: 'POST',
            body: JSON.stringify({ amount })
        });
        if (res.ok) {
            depositModal.classList.remove('active');
            initDashboard();
        }
    };

    // --- Agent Simulator Chat Logic ---
    simToggle.onclick = () => simPanel.classList.toggle('active');
    closeSimBtn.onclick = (e) => {
        e.stopPropagation();
        simPanel.classList.remove('active');
    };

    function addMessage(text, type = 'bot') {
        const msg = document.createElement('div');
        msg.className = `message ${type}`;
        msg.textContent = text;
        chatMessages.appendChild(msg);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function handleChat() {
        const input = chatInput.value.toLowerCase().trim();
        if (!input) return;

        addMessage(chatInput.value.trim(), 'user');
        chatInput.value = '';

        // Product Registry
        const products = [
            { keywords: ["air force", "nike"], name: "Nike Air Force 1", price: 200, merchant: "Amazon" },
            { keywords: ["iphone", "17 pro"], name: "iPhone 17 Pro", price: 2000, merchant: "Telus" },
            { keywords: ["macbook", "mcbook"], name: "MacBook Pro", price: 1000, merchant: "Amazon" }
        ];

        const product = products.find(p => p.keywords.some(k => input.includes(k)));

        setTimeout(() => {
            addMessage("Analyzing your request and searching global markets...", "bot");

            setTimeout(async () => {
                if (product) {
                    addMessage(`Found: ${product.name}.`, "bot");
                    addMessage(`Store: ${product.merchant} | Price: $${product.price.toFixed(2)}`, "bot");
                    addMessage(`Checking your autonomous payment rules for ${product.merchant}...`, "bot");

                    setTimeout(async () => {
                        try {
                            const res = await fetch('/api/pay', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    identity: state.user ? state.user.email : "",
                                    merchant_name: product.merchant,
                                    amount: product.price
                                })
                            });
                            const data = await res.json();

                            if (data.status === 'success') {
                                addMessage(`✅ Payment approved! The transaction has been recorded in your Audit Logs.`, "bot");
                                initDashboard();
                            } else {
                                addMessage(`❌ Payment blocked: ${data.message}`, "bot");
                                initDashboard(); // Refresh to show the failed attempt in logs
                            }
                        } catch (err) {
                            addMessage("Error connecting to the payment gateway.", "bot");
                        }
                    }, 1500);
                } else {
                    addMessage("I couldn't identify a specific product. Try 'Buy iPhone 17 Pro' or 'Get Nike Air Force'.", "bot");
                }
            }, 1800);
        }, 600);
    }

    chatSendBtn.onclick = handleChat;
    chatInput.onkeypress = (e) => {
        if (e.key === 'Enter') handleChat();
    };

    addMerchantBtn.onclick = () => addMerchant();
    newMerchantInput.onkeypress = (e) => {
        if (e.key === 'Enter') addMerchant();
    };
    saveLimitBtn.onclick = saveLimit;

    // Filter event listeners
    document.querySelectorAll('.table-filter').forEach(input => {
        input.addEventListener('input', (e) => {
            state.filters[e.target.dataset.col] = e.target.value;
            renderTransactions();
        });
    });
});
