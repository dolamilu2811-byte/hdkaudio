// HDK MEDIA ADMIN DASHBOARD SCRIPT - NO BROWSER POPUPS (INLINE EDIT & CUSTOM MODAL)
document.addEventListener('DOMContentLoaded', () => {
  const TOKEN_KEY = 'hdk_admin_token_v1';
  let adminToken = sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
  let dashboardCache = null;
  let activeFilter = 'all';

  // DOM Elements
  const loginOverlay = document.getElementById('loginOverlay');
  const loginForm = document.getElementById('loginForm');
  const adminPass = document.getElementById('adminPass');
  const btnTogglePass = document.getElementById('btnTogglePass');
  const loginMsg = document.getElementById('loginMsg');
  const btnLogin = document.getElementById('btnLogin');

  const adminApp = document.getElementById('adminApp');
  const masterSwitchToggle = document.getElementById('masterSwitchToggle');
  const masterStatusText = document.getElementById('masterStatusText');
  const btnRefreshData = document.getElementById('btnRefreshData');
  const btnLogout = document.getElementById('btnLogout');

  // Stats
  const statSystemState = document.getElementById('statSystemState');
  const statTotalClients = document.getElementById('statTotalClients');
  const statActiveClients = document.getElementById('statActiveClients');
  const statExpiredClients = document.getElementById('statExpiredClients');
  const statTotalDownloads = document.getElementById('statTotalDownloads');
  const tabCountClients = document.getElementById('tabCountClients');
  const tabCountKeys = document.getElementById('tabCountKeys');

  // Tabs
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  // Client search & filter
  const clientSearchInput = document.getElementById('clientSearchInput');
  const filterBtns = document.querySelectorAll('.filter-btn');
  const clientsTableBody = document.getElementById('clientsTableBody');

  // Key generator
  const btnCreateKey = document.getElementById('btnCreateKey');
  const keyNote = document.getElementById('keyNote');
  const newKeyResultBox = document.getElementById('newKeyResultBox');
  const displayNewKeyCode = document.getElementById('displayNewKeyCode');
  const btnCopyNewKey = document.getElementById('btnCopyNewKey');
  const keysTableBody = document.getElementById('keysTableBody');
  const keysCountBadge = document.getElementById('keysCountBadge');

  // Settings
  const changePassForm = document.getElementById('changePassForm');
  const newPass = document.getElementById('newPass');
  const confirmPass = document.getElementById('confirmPass');
  const changePassMsg = document.getElementById('changePassMsg');
  const systemConfigForm = document.getElementById('systemConfigForm');
  const cfgTrialDays = document.getElementById('cfgTrialDays');
  const cfgContact = document.getElementById('cfgContact');
  const cfgBroadcast = document.getElementById('cfgBroadcast');
  const configMsg = document.getElementById('configMsg');

  // Toast
  const toastBox = document.getElementById('toastBox');
  const toastMsg = document.getElementById('toastMsg');
  const toastIcon = document.getElementById('toastIcon');

  // Custom Confirm Modal Elements
  const confirmModal = document.getElementById('confirmModal');
  const confirmTitle = document.getElementById('confirmTitle');
  const confirmDesc = document.getElementById('confirmDesc');
  const btnCancelConfirm = document.getElementById('btnCancelConfirm');
  const btnAcceptConfirm = document.getElementById('btnAcceptConfirm');
  let confirmCallback = null;

  function showToast(msg, isSuccess = true) {
    toastMsg.textContent = msg;
    toastIcon.className = isSuccess ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-exclamation';
    toastIcon.style.color = isSuccess ? 'var(--accent-green)' : 'var(--accent-red)';
    toastBox.classList.remove('hidden');
    setTimeout(() => { toastBox.classList.add('hidden'); }, 3500);
  }

  function showCustomConfirm(title, desc, onConfirm, isDanger = true) {
    confirmTitle.textContent = title;
    confirmDesc.textContent = desc;
    confirmCallback = onConfirm;
    btnAcceptConfirm.className = isDanger ? 'btn-danger' : 'btn-submit';
    confirmModal.classList.remove('hidden');
  }

  function closeCustomConfirm() {
    confirmModal.classList.add('hidden');
    confirmCallback = null;
  }

  if (btnCancelConfirm) btnCancelConfirm.addEventListener('click', closeCustomConfirm);
  if (btnAcceptConfirm) {
    btnAcceptConfirm.addEventListener('click', () => {
      if (confirmCallback) confirmCallback();
      closeCustomConfirm();
    });
  }
  if (confirmModal) {
    confirmModal.addEventListener('click', (e) => {
      if (e.target === confirmModal) closeCustomConfirm();
    });
  }

  // Toggle Password Visibility
  btnTogglePass.addEventListener('click', () => {
    const isPass = adminPass.type === 'password';
    adminPass.type = isPass ? 'text' : 'password';
    btnTogglePass.innerHTML = isPass ? '<i class="fa-solid fa-eye-slash"></i>' : '<i class="fa-solid fa-eye"></i>';
  });

  // Login handler
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const pass = adminPass.value.trim();
    if (!pass) return;

    btnLogin.disabled = true;
    btnLogin.innerHTML = '<span><i class="fa-solid fa-spinner fa-spin"></i> Đang xác thực...</span>';
    loginMsg.classList.add('hidden');

    try {
      const res = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pass })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Sai mật khẩu!');

      adminToken = data.token;
      sessionStorage.setItem(TOKEN_KEY, adminToken);
      localStorage.setItem(TOKEN_KEY, adminToken);

      loginOverlay.classList.add('hidden');
      adminApp.classList.remove('hidden');
      loadDashboard();
      showToast('Đăng nhập thành công! Chào mừng Quản trị viên.');
    } catch (err) {
      loginMsg.textContent = err.message;
      loginMsg.className = 'login-msg error';
      loginMsg.classList.remove('hidden');
    } finally {
      btnLogin.disabled = false;
      btnLogin.innerHTML = '<span><i class="fa-solid fa-right-to-bracket"></i> ĐĂNG NHẬP HỆ THỐNG</span>';
    }
  });

  // Logout handler
  btnLogout.addEventListener('click', () => {
    showCustomConfirm(
      'Đăng Xuất Khỏi Quản Trị',
      'Bạn có chắc chắn muốn đăng xuất khỏi Bảng điều khiển Quản trị?',
      () => {
        adminToken = null;
        sessionStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(TOKEN_KEY);
        loginOverlay.classList.remove('hidden');
        adminApp.classList.add('hidden');
        adminPass.value = '';
      },
      false
    );
  });

  // Auth fetch helper
  async function authFetch(url, options = {}) {
    options.headers = options.headers || {};
    options.headers['Authorization'] = `Bearer ${adminToken}`;
    const res = await fetch(url, options);
    if (res.status === 401) {
      sessionStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(TOKEN_KEY);
      loginOverlay.classList.remove('hidden');
      adminApp.classList.add('hidden');
      throw new Error('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
    }
    return res;
  }

  // Load Dashboard Data
  async function loadDashboard() {
    try {
      const res = await authFetch('/api/admin/dashboard-data');
      if (!res.ok) throw new Error('Không thể tải dữ liệu.');
      const data = await res.json();
      dashboardCache = data;

      renderDashboard(data);
    } catch (err) {
      showToast(err.message, false);
    }
  }

  btnRefreshData.addEventListener('click', () => {
    btnRefreshData.innerHTML = '<i class="fa-solid fa-rotate fa-spin"></i>';
    loadDashboard().finally(() => {
      setTimeout(() => { btnRefreshData.innerHTML = '<i class="fa-solid fa-rotate"></i>'; }, 400);
    });
  });

  // Render Dashboard
  function renderDashboard(data) {
    const isMasterOn = data.master_switch;
    masterSwitchToggle.checked = isMasterOn;
    updateMasterSwitchUI(isMasterOn);

    statSystemState.textContent = isMasterOn ? 'BẬT (Online)' : 'TẮT (Đã khóa)';
    statSystemState.style.color = isMasterOn ? 'var(--accent-green)' : 'var(--accent-red)';
    statTotalClients.textContent = data.stats.total_clients || 0;
    statActiveClients.textContent = data.stats.active_clients || 0;
    statExpiredClients.textContent = (data.stats.expired_clients || 0) + (data.stats.blocked_clients || 0);
    statTotalDownloads.textContent = data.total_downloads || 0;
    tabCountClients.textContent = data.stats.total_clients || 0;
    tabCountKeys.textContent = data.stats.total_keys || 0;

    cfgTrialDays.value = data.trial_days || 1;
    cfgContact.value = data.admin_contact || '037.2222.700';
    cfgBroadcast.value = data.broadcast_message || '';

    renderClientsTable();
    renderKeysTable(data.keys || []);
  }

  function updateMasterSwitchUI(isOn) {
    if (isOn) {
      masterStatusText.textContent = 'ĐANG CHO PHÉP TẢI';
      masterStatusText.className = 'switch-state active';
    } else {
      masterStatusText.textContent = 'ĐÃ TẮT TOÀN HỆ THỐNG';
      masterStatusText.className = 'switch-state locked';
    }
  }

  // Master Switch Toggle Event
  masterSwitchToggle.addEventListener('change', async () => {
    const desiredState = masterSwitchToggle.checked;
    updateMasterSwitchUI(desiredState);

    try {
      const res = await authFetch('/api/admin/system-toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ master_switch: desiredState })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Lỗi khi gạt công tắc');

      showToast(desiredState ? 'ĐÃ BẬT HỆ THỐNG! Tất cả khách hàng có thể tải video.' : 'ĐÃ TẮT HỆ THỐNG! Toàn bộ lượt tải trên mọi máy đã bị đóng băng.');
      statSystemState.textContent = desiredState ? 'BẬT (Online)' : 'TẮT (Đã khóa)';
      statSystemState.style.color = desiredState ? 'var(--accent-green)' : 'var(--accent-red)';
    } catch (err) {
      masterSwitchToggle.checked = !desiredState;
      updateMasterSwitchUI(!desiredState);
      showToast(err.message, false);
    }
  });

  // Tab switching
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      const target = document.getElementById(btn.dataset.tab);
      if (target) target.classList.add('active');
    });
  });

  // Client Filter & Search
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.dataset.filter;
      renderClientsTable();
    });
  });

  clientSearchInput.addEventListener('input', () => {
    renderClientsTable();
  });

  // Render Clients Table
  function renderClientsTable() {
    if (!dashboardCache || !dashboardCache.clients) return;

    const query = clientSearchInput.value.trim().toLowerCase();
    let clients = dashboardCache.clients.filter(c => {
      if (activeFilter === 'active' && c.status !== 'active') return false;
      if (activeFilter === 'expired' && c.status !== 'expired') return false;
      if (activeFilter === 'blocked' && c.status !== 'blocked') return false;

      if (query) {
        const matchName = (c.name || '').toLowerCase().includes(query);
        const matchId = (c.client_id || '').toLowerCase().includes(query);
        const matchIp = (c.ip || '').toLowerCase().includes(query);
        return matchName || matchId || matchIp;
      }
      return true;
    });

    if (clients.length === 0) {
      clientsTableBody.innerHTML = `
        <tr>
          <td colspan="6" class="text-center loading-cell">
            <i class="fa-solid fa-users-slash" style="font-size: 24px; margin-bottom: 8px; display: block;"></i>
            Không tìm thấy khách hàng nào phù hợp bộ lọc.
          </td>
        </tr>
      `;
      return;
    }

    clientsTableBody.innerHTML = clients.map(c => {
      let statusBadge = '';
      if (c.status === 'active') {
        statusBadge = `<span class="status-pill active"><span class="dot"></span> ${c.is_lifetime ? 'VIP Vĩnh Viễn' : 'Hoạt Động'}</span>`;
      } else if (c.status === 'blocked') {
        statusBadge = `<span class="status-pill blocked"><span class="dot"></span> Đã Khóa</span>`;
      } else {
        statusBadge = `<span class="status-pill expired"><span class="dot"></span> Hết Hạn</span>`;
      }

      const isBlocked = (c.status === 'blocked');

      return `
        <tr data-client-id="${c.client_id}">
          <td class="client-cell-name">
            <div class="client-name-row" id="nameRow_${c.client_id}">
              <span class="client-name-text" data-action="rename" data-id="${c.client_id}" data-name="${escapeHtml(c.name)}" title="Bấm vào để đổi tên trực tiếp">${escapeHtml(c.name)}</span>
              <button class="btn-edit-name" data-action="rename" data-id="${c.client_id}" data-name="${escapeHtml(c.name)}" title="Đổi tên ghi chú"><i class="fa-solid fa-pen"></i></button>
            </div>
            <span class="client-id-badge">${c.client_id}</span>
            <div class="client-meta-info"><i class="fa-solid fa-desktop"></i> IP: ${c.ip || 'N/A'} • Tạo: ${c.created_at_str}</div>
          </td>
          <td>
            <div class="time-left-text">${c.time_left}</div>
            <span class="expires-date-sub">Hạn: ${c.expires_at_str}</span>
          </td>
          <td>${statusBadge}</td>
          <td><b>${c.download_count}</b> video</td>
          <td>${c.last_active_str}</td>
          <td class="text-right">
            <div class="action-buttons-group">
              <button class="btn-ext btn-ext-week" data-action="extend" data-id="${c.client_id}" data-days="7" title="Thêm 7 ngày sử dụng">+7 Ngày</button>
              <button class="btn-ext btn-ext-month" data-action="extend" data-id="${c.client_id}" data-days="30" title="Thêm 30 ngày sử dụng">+30 Ngày</button>
              <button class="btn-ext btn-ext-year" data-action="extend" data-id="${c.client_id}" data-days="365" title="Thêm 1 năm sử dụng">+1 Năm</button>
              <button class="btn-ext btn-ext-life" data-action="extend" data-id="${c.client_id}" data-days="-1" title="Kích hoạt vĩnh viễn">Vĩnh viễn</button>
              <button class="btn-block-client" data-action="toggle-block" data-id="${c.client_id}" data-status="${isBlocked ? 'active' : 'blocked'}" title="${isBlocked ? 'Mở khóa' : 'Khóa thiết bị'}">
                <i class="fa-solid ${isBlocked ? 'fa-lock-open' : 'fa-ban'}"></i>
              </button>
              <button class="btn-del-client" data-action="delete" data-id="${c.client_id}" title="Xóa"><i class="fa-solid fa-trash-can"></i></button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  // Client Table Action Event Delegation
  clientsTableBody.addEventListener('click', async (e) => {
    // 1. Check if user clicked rename or the name text
    const renameTrigger = e.target.closest('[data-action="rename"]');
    if (renameTrigger) {
      const clientId = renameTrigger.dataset.id;
      const currentName = renameTrigger.dataset.name || '';
      startInlineEdit(clientId, currentName);
      return;
    }

    const btn = e.target.closest('button');
    if (!btn) return;

    const action = btn.dataset.action;
    const clientId = btn.dataset.id;
    if (!action || !clientId) return;

    // 2. Extend license: INSTANT 1-CLICK (No popup!)
    if (action === 'extend') {
      const days = parseInt(btn.dataset.days);
      const isLifetime = (days === -1);
      btn.disabled = true;
      try {
        const res = await authFetch('/api/admin/client/extend', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ client_id: clientId, days: days, lifetime: isLifetime })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        showToast(isLifetime ? 'Đã kích hoạt VĨNH VIỄN!' : `Đã gia hạn thành công +${days} ngày!`);
        loadDashboard();
      } catch (err) {
        showToast(err.message, false);
      } finally {
        btn.disabled = false;
      }
    } 
    // 3. Block/Unblock: INSTANT 1-CLICK
    else if (action === 'toggle-block') {
      const newStatus = btn.dataset.status;
      const isBlock = (newStatus === 'blocked');
      try {
        const res = await authFetch('/api/admin/client/status', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ client_id: clientId, status: newStatus })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);
        showToast(isBlock ? 'Đã khóa thiết bị!' : 'Đã mở khóa thiết bị!');
        loadDashboard();
      } catch (err) {
        showToast(err.message, false);
      }
    } 
    // 4. Delete client: Custom Glassmorphism Confirmation Modal (NO native browser confirm!)
    else if (action === 'delete') {
      showCustomConfirm(
        'Xóa Khách Hàng',
        `Bạn có chắc chắn muốn xóa khách hàng ${clientId} khỏi danh sách?`,
        async () => {
          try {
            const res = await authFetch('/api/admin/client/delete', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ client_id: clientId })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);
            showToast('Đã xóa khách hàng thành công!');
            loadDashboard();
          } catch (err) {
            showToast(err.message, false);
          }
        },
        true
      );
    }
  });

  // ==========================================
  // INLINE NAME EDITING (Directly in table)
  // ==========================================
  function startInlineEdit(clientId, initialName) {
    const rowEl = document.getElementById(`nameRow_${clientId}`);
    if (!rowEl) return;

    rowEl.innerHTML = `
      <div class="inline-edit-wrap">
        <input type="text" class="inline-edit-input" id="inlineInput_${clientId}" value="${escapeHtml(initialName)}" placeholder="Nhập tên khách...">
        <button class="btn-save-inline" id="btnSaveInline_${clientId}" title="Lưu (Enter)"><i class="fa-solid fa-check"></i></button>
        <button class="btn-cancel-inline" id="btnCancelInline_${clientId}" title="Hủy (Esc)"><i class="fa-solid fa-xmark"></i></button>
      </div>
    `;

    const input = document.getElementById(`inlineInput_${clientId}`);
    const btnSave = document.getElementById(`btnSaveInline_${clientId}`);
    const btnCancel = document.getElementById(`btnCancelInline_${clientId}`);

    input.focus();
    input.select();

    let isSubmitting = false;

    async function saveEdit() {
      if (isSubmitting) return;
      const newName = input.value.trim();
      if (!newName || newName === initialName) {
        cancelEdit();
        return;
      }
      isSubmitting = true;
      btnSave.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

      try {
        const res = await authFetch('/api/admin/client/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ client_id: clientId, name: newName })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        showToast(`Đã đổi tên thành: ${newName}`);
        // Update cache locally for immediate responsiveness
        if (dashboardCache && dashboardCache.clients) {
          const target = dashboardCache.clients.find(c => c.client_id === clientId);
          if (target) target.name = newName;
        }
        renderClientsTable();
      } catch (err) {
        showToast(err.message, false);
        cancelEdit();
      }
    }

    function cancelEdit() {
      rowEl.innerHTML = `
        <span class="client-name-text" data-action="rename" data-id="${clientId}" data-name="${escapeHtml(initialName)}" title="Bấm vào để đổi tên trực tiếp">${escapeHtml(initialName)}</span>
        <button class="btn-edit-name" data-action="rename" data-id="${clientId}" data-name="${escapeHtml(initialName)}" title="Đổi tên ghi chú"><i class="fa-solid fa-pen"></i></button>
      `;
    }

    btnSave.addEventListener('click', (e) => {
      e.stopPropagation();
      saveEdit();
    });

    btnCancel.addEventListener('click', (e) => {
      e.stopPropagation();
      cancelEdit();
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        saveEdit();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        cancelEdit();
      }
    });
  }

  // Render Keys Table
  function renderKeysTable(keys) {
    keysCountBadge.textContent = `${keys.length} mã`;
    if (keys.length === 0) {
      keysTableBody.innerHTML = `<tr><td colspan="5" class="text-center loading-cell">Chưa có mã kích hoạt nào được tạo.</td></tr>`;
      return;
    }

    keysTableBody.innerHTML = keys.map(k => {
      const isUsed = k.used;
      const daysText = k.days === -1 ? 'Vĩnh viễn' : `${k.days} Ngày`;
      return `
        <tr>
          <td>
            <b style="font-family: var(--font-mono); letter-spacing: 0.5px; color: ${isUsed ? 'var(--text-muted)' : 'var(--accent-cyan)'};">${k.key}</b>
            <button class="btn-copy-code" data-code="${k.key}" title="Sao chép mã"><i class="fa-regular fa-copy"></i></button>
          </td>
          <td><span class="status-pill active">${daysText}</span></td>
          <td>${escapeHtml(k.note || 'Không có')}</td>
          <td>
            ${isUsed 
              ? `<span class="status-pill expired"><span class="dot"></span> Đã dùng (${k.used_at_str || ''})</span>` 
              : `<span class="status-pill active"><span class="dot"></span> Chưa sử dụng</span>`}
          </td>
          <td>${k.used_by || '—'}</td>
          <td class="text-right">
            <button class="btn-del-client btn-del-key" data-key="${k.key}" title="Xóa mã này"><i class="fa-solid fa-trash-can"></i></button>
          </td>
        </tr>
      `;
    }).join('');
  }

  // Keys table action delegation (Copy & Delete)
  keysTableBody.addEventListener('click', (e) => {
    const copyBtn = e.target.closest('.btn-copy-code');
    if (copyBtn) {
      const code = copyBtn.dataset.code;
      navigator.clipboard.writeText(code).then(() => {
        showToast(`Đã sao chép mã: ${code}`);
      });
      return;
    }

    const delBtn = e.target.closest('.btn-del-key');
    if (delBtn) {
      const keyCode = delBtn.dataset.key;
      showCustomConfirm(
        'Xóa Mã Kích Hoạt',
        `Bạn có chắc chắn muốn xóa mã ${keyCode}?`,
        async () => {
          try {
            const res = await authFetch('/api/admin/keys/delete', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ key: keyCode })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);
            showToast(`Đã xóa mã ${keyCode} thành công!`);
            loadDashboard();
          } catch (err) {
            showToast(err.message, false);
          }
        },
        true
      );
    }
  });

  // Create Key Handler
  btnCreateKey.addEventListener('click', async () => {
    const selectedRadio = document.querySelector('input[name="keyDays"]:checked');
    const days = selectedRadio ? parseInt(selectedRadio.value) : 7;
    const note = keyNote.value.trim();

    btnCreateKey.disabled = true;
    btnCreateKey.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tạo mã...';

    try {
      const res = await authFetch('/api/admin/keys/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days, note })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      displayNewKeyCode.textContent = data.key;
      newKeyResultBox.classList.remove('hidden');
      keyNote.value = '';
      showToast(`Đã tạo mã mới: ${data.key}`);
      loadDashboard();
    } catch (err) {
      showToast(err.message, false);
    } finally {
      btnCreateKey.disabled = false;
      btnCreateKey.innerHTML = '<i class="fa-solid fa-plus-circle"></i> TẠO MÃ KÍCH HOẠT NGAY';
    }
  });

  btnCopyNewKey.addEventListener('click', () => {
    const code = displayNewKeyCode.textContent;
    navigator.clipboard.writeText(code).then(() => {
      showToast(`Đã sao chép mã: ${code}`);
    });
  });

  // Change Password Handler
  changePassForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const p1 = newPass.value;
    const p2 = confirmPass.value;

    if (p1 !== p2) {
      changePassMsg.textContent = 'Hai mật khẩu không khớp nhau!';
      changePassMsg.className = 'login-msg error';
      changePassMsg.classList.remove('hidden');
      return;
    }
    if (p1.length < 4) {
      changePassMsg.textContent = 'Mật khẩu phải từ 4 ký tự trở lên!';
      changePassMsg.className = 'login-msg error';
      changePassMsg.classList.remove('hidden');
      return;
    }

    try {
      const res = await authFetch('/api/admin/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_password: p1 })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      changePassMsg.textContent = 'Đã đổi mật khẩu Admin thành công!';
      changePassMsg.className = 'login-msg success';
      changePassMsg.classList.remove('hidden');
      newPass.value = '';
      confirmPass.value = '';
      showToast('Đã cập nhật mật khẩu mới!');
    } catch (err) {
      changePassMsg.textContent = err.message;
      changePassMsg.className = 'login-msg error';
      changePassMsg.classList.remove('hidden');
    }
  });

  // System Config Handler
  systemConfigForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const trialDays = parseInt(cfgTrialDays.value) || 0;
    const contact = cfgContact.value.trim();
    const broadcast = cfgBroadcast.value.trim();

    try {
      const res = await authFetch('/api/admin/config/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trial_days: trialDays, admin_contact: contact, broadcast_message: broadcast })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      configMsg.textContent = 'Cập nhật cấu hình thành công!';
      configMsg.className = 'login-msg success';
      configMsg.classList.remove('hidden');
      showToast('Đã lưu cấu hình hệ thống!');
      loadDashboard();
    } catch (err) {
      configMsg.textContent = err.message;
      configMsg.className = 'login-msg error';
      configMsg.classList.remove('hidden');
    }
  });

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, (m) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&custom;', "'": '&#39;'
    })[m]);
  }

  // Initial check
  if (adminToken) {
    loginOverlay.classList.add('hidden');
    adminApp.classList.remove('hidden');
    loadDashboard();
  } else {
    loginOverlay.classList.remove('hidden');
    adminApp.classList.add('hidden');
  }
});
