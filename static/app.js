// HDK MEDIA - Client Application Logic (Full HD Video & High Quality Audio)

document.addEventListener('DOMContentLoaded', () => {

  // ==========================================
  // CLIENT LICENSE & MASTER SWITCH MANAGEMENT
  // ==========================================
  const CLIENT_ID_KEY = 'hdk_client_id_v2';
  function getClientId() {
    let cid = localStorage.getItem(CLIENT_ID_KEY);
    if (!cid || cid.length < 8) {
      const rand = Math.random().toString(36).substring(2, 8).toUpperCase() + Math.random().toString(36).substring(2, 6).toUpperCase();
      cid = 'HDK-' + rand;
      localStorage.setItem(CLIENT_ID_KEY, cid);
    }
    return cid;
  }
  const myClientId = getClientId();

  // License DOM Elements
  const btnLicenseBadge = document.getElementById('btnLicenseBadge');
  const licenseBadgeText = document.getElementById('licenseBadgeText');
  const systemLockedBanner = document.getElementById('systemLockedBanner');
  const lockedBannerMsg = document.getElementById('lockedBannerMsg');
  const licenseModal = document.getElementById('licenseModal');
  const btnCloseLicenseModal = document.getElementById('btnCloseLicenseModal');
  const displayMyClientId = document.getElementById('displayMyClientId');
  const displayMyTimeLeft = document.getElementById('displayMyTimeLeft');
  const displayMyExpiresAt = document.getElementById('displayMyExpiresAt');
  const btnCopyMyClientId = document.getElementById('btnCopyMyClientId');
  const inputLicenseKey = document.getElementById('inputLicenseKey');
  const btnSubmitKey = document.getElementById('btnSubmitKey');
  const modalLicenseMsg = document.getElementById('modalLicenseMsg');

  let currentLicenseState = null;

  async function checkLicenseStatus(showAlertIfBlocked = false) {
    try {
      const res = await fetch(`/api/license/check?client_id=${myClientId}`);
      const data = await res.json();
      currentLicenseState = data;

      if (displayMyClientId) displayMyClientId.textContent = myClientId;

      if (!data.allowed) {
        if (data.reason === 'system_locked') {
          // Master Kill-Switch is OFF
          if (systemLockedBanner) {
            systemLockedBanner.classList.remove('hidden');
            if (lockedBannerMsg) lockedBannerMsg.textContent = data.message || 'Hệ thống đang tạm khóa bởi Quản trị viên.';
          }
          if (licenseBadgeText) licenseBadgeText.textContent = 'Hệ thống: TẠM KHÓA';
          if (btnLicenseBadge) btnLicenseBadge.className = 'badge-license-pill locked';
          if (showAlertIfBlocked) {
            showNotification(data.message || 'Hệ thống đang tạm khóa bởi Admin.', false);
          }
        } else {
          // Client Expired or Blocked
          if (systemLockedBanner) systemLockedBanner.classList.add('hidden');
          if (licenseBadgeText) licenseBadgeText.textContent = 'Bản quyền: HẾT HẠN';
          if (btnLicenseBadge) btnLicenseBadge.className = 'badge-license-pill expired';
          if (displayMyTimeLeft) {
            displayMyTimeLeft.textContent = 'Đã hết hạn';
            displayMyTimeLeft.className = 'lic-value expired';
          }
          if (displayMyExpiresAt) {
            displayMyExpiresAt.textContent = data.client ? (data.client.expires_at_str || '—') : '—';
          }
          if (showAlertIfBlocked) {
            showNotification(data.message || 'Bản quyền của bạn đã hết hạn. Bấm vào huy hiệu Bản quyền góc trên để kích hoạt!', false);
            openLicenseModal();
          }
        }
        return false;
      } else {
        // Active
        if (systemLockedBanner) systemLockedBanner.classList.add('hidden');
        const timeLeftStr = data.time_left_str || 'Đang hoạt động';
        if (licenseBadgeText) licenseBadgeText.textContent = `Bản quyền: ${timeLeftStr}`;
        if (btnLicenseBadge) btnLicenseBadge.className = 'badge-license-pill';
        if (displayMyTimeLeft) {
          displayMyTimeLeft.textContent = timeLeftStr;
          displayMyTimeLeft.className = 'lic-value active';
        }
        if (displayMyExpiresAt) {
          displayMyExpiresAt.textContent = data.expires_at_str || 'Vĩnh viễn';
        }
        return true;
      }
    } catch (err) {
      console.warn('License check error:', err);
      return true;
    }
  }

  function openLicenseModal() {
    if (licenseModal) {
      licenseModal.classList.remove('hidden');
      if (modalLicenseMsg) modalLicenseMsg.classList.add('hidden');
      checkLicenseStatus();
    }
  }

  function closeLicenseModal() {
    if (licenseModal) licenseModal.classList.add('hidden');
  }

  if (btnLicenseBadge) btnLicenseBadge.addEventListener('click', openLicenseModal);
  if (btnCloseLicenseModal) btnCloseLicenseModal.addEventListener('click', closeLicenseModal);
  if (licenseModal) {
    licenseModal.addEventListener('click', (e) => {
      if (e.target === licenseModal) closeLicenseModal();
    });
  }

  if (btnCopyMyClientId) {
    btnCopyMyClientId.addEventListener('click', () => {
      navigator.clipboard.writeText(myClientId).then(() => {
        btnCopyMyClientId.innerHTML = '<i class="fa-solid fa-check"></i> Đã chép!';
        setTimeout(() => { btnCopyMyClientId.innerHTML = '<i class="fa-regular fa-copy"></i> Copy'; }, 2000);
      });
    });
  }

  if (btnSubmitKey) {
    btnSubmitKey.addEventListener('click', async () => {
      const keyVal = inputLicenseKey.value.trim();
      if (!keyVal) {
        modalLicenseMsg.textContent = 'Vui lòng nhập Mã Kích Hoạt (ví dụ: HDK-30D-XXXX)!';
        modalLicenseMsg.className = 'modal-msg error';
        modalLicenseMsg.classList.remove('hidden');
        return;
      }

      btnSubmitKey.disabled = true;
      btnSubmitKey.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kích hoạt...';

      try {
        const res = await fetch('/api/license/activate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ client_id: myClientId, key: keyVal })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Mã không hợp lệ!');

        modalLicenseMsg.textContent = data.message || 'Kích hoạt thành công!';
        modalLicenseMsg.className = 'modal-msg success';
        modalLicenseMsg.classList.remove('hidden');
        inputLicenseKey.value = '';

        await checkLicenseStatus();
        setTimeout(() => {
          closeLicenseModal();
        }, 1500);
      } catch (err) {
        modalLicenseMsg.textContent = err.message;
        modalLicenseMsg.className = 'modal-msg error';
        modalLicenseMsg.classList.remove('hidden');
      } finally {
        btnSubmitKey.disabled = false;
        btnSubmitKey.innerHTML = '<i class="fa-solid fa-bolt"></i> KÍCH HOẠT';
      }
    });
  }

  // Initial license check on page load
  checkLicenseStatus();


  // DOM Elements
  const urlInput = document.getElementById('urlInput');
  const btnClear = document.getElementById('btnClear');
  const btnPaste = document.getElementById('btnPaste');
  const btnFetchInfo = document.getElementById('btnFetchInfo');
  const notifyBox = document.getElementById('notifyBox');
  const notifyMsg = document.getElementById('notifyMsg');
  const notifyActionBox = document.getElementById('notifyActionBox');
  const btnOpenCookieModal = document.getElementById('btnOpenCookieModal');
  const btnHeaderCookie = document.getElementById('btnHeaderCookie');

  // Cookie Modal elements
  const cookieModal = document.getElementById('cookieModal');
  const btnCloseCookieModal = document.getElementById('btnCloseCookieModal');
  const inputCUser = document.getElementById('inputCUser');
  const inputXs = document.getElementById('inputXs');
  const inputCookieRaw = document.getElementById('inputCookieRaw');
  const btnSaveCookieModal = document.getElementById('btnSaveCookieModal');
  const modalCookieMsg = document.getElementById('modalCookieMsg');

  // Preview elements
  const previewCard = document.getElementById('previewCard');
  const videoThumb = document.getElementById('videoThumb');
  const videoDuration = document.getElementById('videoDuration');
  const videoTitle = document.getElementById('videoTitle');
  const videoChannel = document.getElementById('videoChannel');
  const videoViews = document.getElementById('videoViews');
  const platformBadgeIcon = document.getElementById('platformBadgeIcon');
  const formatSelect = document.getElementById('formatSelect');
  const qualitySelect = document.getElementById('qualitySelect');
  const qualityLabel = document.getElementById('qualityLabel');
  const chkEmbedThumb = document.getElementById('chkEmbedThumb');
  const btnStartDownload = document.getElementById('btnStartDownload');
  const btnStartDownloadText = document.getElementById('btnStartDownloadText');

  // Progress elements
  const progressCard = document.getElementById('progressCard');
  const progressBar = document.getElementById('progressBar');
  const percentNumber = document.getElementById('percentNumber');
  const progressStatusText = document.getElementById('progressStatusText');
  const progressDetailText = document.getElementById('progressDetailText');
  const progressDownloaded = document.getElementById('progressDownloaded');
  const progressSpeed = document.getElementById('progressSpeed');
  const progressEta = document.getElementById('progressEta');

  // Result & Media Player elements
  const resultCard = document.getElementById('resultCard');
  const resultSuccessTitle = document.getElementById('resultSuccessTitle');
  const resultFileName = document.getElementById('resultFileName');
  const resultMediaIcon = document.getElementById('resultMediaIcon');
  const videoPlayerBox = document.getElementById('videoPlayerBox');
  const videoPlayer = document.getElementById('videoPlayer');
  const audioPlayerBox = document.getElementById('audioPlayerBox');
  const audioPlayer = document.getElementById('audioPlayer');
  const btnDownloadBrowser = document.getElementById('btnDownloadBrowser');
  const btnConvertAnother = document.getElementById('btnConvertAnother');

  // Session History elements
  const historyList = document.getElementById('historyList');
  const historyCountBadge = document.getElementById('historyCountBadge');
  const btnClearHistory = document.getElementById('btnClearHistory');

  let currentVideoData = null;
  let activeTaskId = null;
  let pollInterval = null;
  let timerInterval = null;

  // Session storage key
  const STORAGE_KEY = 'hdk_media_session_history_v2';

  function getSessionHistory() {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  function saveSessionItem(item) {
    try {
      let history = getSessionHistory();
      history = history.filter(h => h.filename !== item.filename);
      history.unshift(item);
      if (history.length > 25) history.pop();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
      renderSessionHistory();
    } catch (e) {
      console.error(e);
    }
  }

  function clearAllSessionHistory() {
    localStorage.removeItem(STORAGE_KEY);
    renderSessionHistory();
  }

  // Notification helper
  function showNotification(msg, isSuccess = false, showCookieBtn = false) {
    notifyMsg.textContent = msg;
    notifyBox.className = 'notify-box ' + (isSuccess ? 'success' : '');
    if (showCookieBtn && notifyActionBox) {
      notifyActionBox.classList.remove('hidden');
    } else if (notifyActionBox) {
      notifyActionBox.classList.add('hidden');
    }
    notifyBox.classList.remove('hidden');
    notifyBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function hideNotification() {
    notifyBox.classList.add('hidden');
  }

  // Cookie Modal Handlers
  function openCookieModal() {
    if (cookieModal) {
      cookieModal.classList.remove('hidden');
      if (modalCookieMsg) modalCookieMsg.classList.add('hidden');
    }
  }

  function closeCookieModal() {
    if (cookieModal) {
      cookieModal.classList.add('hidden');
    }
  }

  if (btnOpenCookieModal) btnOpenCookieModal.addEventListener('click', openCookieModal);
  if (btnHeaderCookie) btnHeaderCookie.addEventListener('click', openCookieModal);
  if (btnCloseCookieModal) btnCloseCookieModal.addEventListener('click', closeCookieModal);

  if (cookieModal) {
    cookieModal.addEventListener('click', (e) => {
      if (e.target === cookieModal) closeCookieModal();
    });
  }

  if (btnSaveCookieModal) {
    btnSaveCookieModal.addEventListener('click', async () => {
      const c_user = inputCUser.value.trim();
      const xs = inputXs.value.trim();
      const cookie_raw = inputCookieRaw.value.trim();

      if (!cookie_raw && (!c_user || !xs)) {
        modalCookieMsg.textContent = 'Vui lòng nhập cả c_user và xs (hoặc dán toàn bộ cookie)!';
        modalCookieMsg.className = 'modal-msg error';
        modalCookieMsg.classList.remove('hidden');
        return;
      }

      btnSaveCookieModal.disabled = true;
      btnSaveCookieModal.innerHTML = '<span class="btn-content"><i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...</span>';

      try {
        const res = await fetch('/api/save-cookie', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ c_user, xs, cookie_raw })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Lỗi lưu cookie');

        modalCookieMsg.textContent = 'Đã lưu Cookie Facebook thành công!';
        modalCookieMsg.className = 'modal-msg success';
        modalCookieMsg.classList.remove('hidden');

        setTimeout(() => {
          closeCookieModal();
          btnSaveCookieModal.disabled = false;
          btnSaveCookieModal.innerHTML = '<span class="btn-content"><i class="fa-solid fa-floppy-disk"></i> LƯU COOKIE FACEBOOK</span>';
          if (urlInput.value.trim()) {
            fetchVideoInfo();
          }
        }, 1000);
      } catch (err) {
        btnSaveCookieModal.disabled = false;
        btnSaveCookieModal.innerHTML = '<span class="btn-content"><i class="fa-solid fa-floppy-disk"></i> LƯU COOKIE FACEBOOK</span>';
        modalCookieMsg.textContent = err.message;
        modalCookieMsg.className = 'modal-msg error';
        modalCookieMsg.classList.remove('hidden');
      }
    });
  }

  // URL input handler
  urlInput.addEventListener('input', () => {
    if (urlInput.value.trim().length > 0) {
      btnClear.classList.remove('hidden');
    } else {
      btnClear.classList.add('hidden');
    }
    hideNotification();
  });

  urlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      fetchVideoInfo();
    }
  });

  btnClear.addEventListener('click', () => {
    urlInput.value = '';
    btnClear.classList.add('hidden');
    previewCard.classList.add('hidden');
    hideNotification();
    urlInput.focus();
  });

  // Paste from clipboard
  btnPaste.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && text.trim().length > 0) {
        urlInput.value = text.trim();
        btnClear.classList.remove('hidden');
        hideNotification();
        fetchVideoInfo();
      } else {
        urlInput.focus();
        showNotification('Bộ nhớ tạm (Clipboard) đang trống. Hãy copy link YouTube hoặc Facebook trước rồi dán vào đây.');
      }
    } catch (err) {
      urlInput.focus();
      showNotification('Vui lòng bấm Ctrl + V vào ô dán link (Trình duyệt chưa cấp quyền đọc tự động).');
    }
  });

  // Format selection change handler
  formatSelect.addEventListener('change', () => {
    const val = formatSelect.value;
    if (val.startsWith('mp4')) {
      qualityLabel.innerHTML = '<i class="fa-solid fa-sliders"></i> Độ phân giải video';
      qualitySelect.innerHTML = `
        <option value="1080" ${val === 'mp4-1080' ? 'selected' : ''}>Full HD 1080p (Nét nhất)</option>
        <option value="720" ${val === 'mp4-720' ? 'selected' : ''}>HD 720p (Nhanh nhẹ)</option>
        <option value="best" ${val === 'mp4-best' ? 'selected' : ''}>Chất lượng gốc cao nhất</option>
      `;
      btnStartDownloadText.textContent = 'BẮT ĐẦU TẢI VIDEO FULL HD';
    } else {
      qualityLabel.innerHTML = '<i class="fa-solid fa-sliders"></i> Chất lượng Bitrate âm thanh';
      qualitySelect.innerHTML = `
        <option value="320" selected>320 kbps (Cực nét - Khuyên dùng)</option>
        <option value="256">256 kbps (Rất cao)</option>
        <option value="192">192 kbps (Chuẩn CD)</option>
        <option value="128">128 kbps (Tiết kiệm bộ nhớ)</option>
      `;
      btnStartDownloadText.textContent = `BẮT ĐẦU XUẤT NHẠC ${val.toUpperCase()}`;
    }
  });

  // Fetch Video Info
  async function fetchVideoInfo() {
    const rawUrl = urlInput.value.trim();
    if (!rawUrl) {
      showNotification('Vui lòng nhập hoặc dán link video Facebook hoặc YouTube vào ô trên!');
      urlInput.focus();
      return;
    }

    const isHttp = rawUrl.includes('http://') || rawUrl.includes('https://');
    const isSupported = rawUrl.includes('youtu') || rawUrl.includes('facebook.com') || rawUrl.includes('fb.watch') || rawUrl.includes('fb.com');

    if (!isHttp && !isSupported) {
      showNotification('Vui lòng nhập link YouTube hoặc Facebook hợp lệ (ví dụ: https://www.facebook.com/reel/... hoặc https://youtube.com/...)');
      urlInput.focus();
      return;
    }

    // Reset and hide old results immediately
    resultCard.classList.add('hidden');
    progressCard.classList.add('hidden');
    if (videoPlayer) {
      videoPlayer.pause();
      videoPlayer.removeAttribute('src');
      videoPlayer.load();
    }
    if (audioPlayer) {
      audioPlayer.pause();
      audioPlayer.removeAttribute('src');
      audioPlayer.load();
    }

    hideNotification();
    btnFetchInfo.disabled = true;

    let seconds = 0;
    btnFetchInfo.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang đọc...';
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      seconds++;
      btnFetchInfo.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang đọc (${seconds}s)...`;
    }, 1000);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);

    try {
      const res = await fetch('/api/info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: rawUrl, client_id: myClientId }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Không thể phân tích video này.');
      }

      currentVideoData = data;

      // Populate preview
      videoThumb.src = data.thumbnail || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=640&q=80';
      videoDuration.textContent = data.duration_str || '00:00';
      videoTitle.textContent = data.title || 'Video Facebook';
      videoViews.textContent = data.view_count || 'N/A';

      if (data.platform === 'facebook') {
        videoChannel.textContent = data.uploader || 'Facebook';
        if (platformBadgeIcon) platformBadgeIcon.className = 'fa-brands fa-facebook icon-fb';
      } else {
        videoChannel.textContent = data.uploader || 'YouTube';
        if (platformBadgeIcon) platformBadgeIcon.className = 'fa-brands fa-youtube icon-yt';
      }

      previewCard.classList.remove('hidden');
      resultCard.classList.add('hidden');
      progressCard.classList.add('hidden');

      previewCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    } catch (err) {
      const errMsg = err.message || 'Lỗi khi kết nối tới máy chủ.';
      const isCookieIssue = errMsg.includes('Cookie') || errMsg.includes('đăng nhập') || errMsg.includes('cannot parse');
      showNotification(errMsg, false, isCookieIssue);
      if (errMsg.includes('khóa') || errMsg.includes('hết hạn') || errMsg.includes('bảo trì') || errMsg.includes('Bản quyền')) {
        checkLicenseStatus(true);
      }
      previewCard.classList.add('hidden');
    } finally {
      if (timerInterval) clearInterval(timerInterval);
      clearTimeout(timeoutId);
      btnFetchInfo.disabled = false;
      btnFetchInfo.innerHTML = '<span class="btn-text">Phân tích</span> <i class="fa-solid fa-arrow-right"></i>';
    }
  }

  btnFetchInfo.addEventListener('click', fetchVideoInfo);

  // Start Extraction / Download
  btnStartDownload.addEventListener('click', async () => {
    if (!currentVideoData || !currentVideoData.url) {
      showNotification('Vui lòng phân tích đường link trước khi tải.');
      return;
    }

    const rawFormat = formatSelect.value;
    let format = 'mp4';
    let quality = '1080';

    if (rawFormat.startsWith('mp4')) {
      format = 'mp4';
      if (rawFormat === 'mp4-1080') quality = '1080';
      else if (rawFormat === 'mp4-720') quality = '720';
      else quality = 'best';
    } else {
      format = rawFormat;
      quality = qualitySelect.value || '320';
    }

    const payload = {
      url: currentVideoData.url, client_id: myClientId, format: format, quality: quality, embed_thumbnail: chkEmbedThumb.checked
    };

    btnStartDownload.disabled = true;
    hideNotification();
    resultCard.classList.add('hidden');
    progressCard.classList.remove('hidden');
    progressCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    updateProgressUI({
      percent: 5,
      status_text: format === 'mp4' ? 'Đang chuẩn bị tải video Full HD 1080p...' : 'Đang khởi động tiến trình trích xuất âm thanh...',
      downloaded_str: '0 KB',
      total_str: 'Đang tính...',
      speed_str: '',
      eta_str: ''
    });

    try {
      const res = await fetch('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Lỗi khi bắt đầu tải');
      }

      activeTaskId = data.task_id;
      startProgressPolling();

    } catch (err) {
      btnStartDownload.disabled = false;
      progressCard.classList.add('hidden');
      showNotification(err.message);
    }
  });

  // Progress Polling
  function startProgressPolling() {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
      if (!activeTaskId) return;

      try {
        const res = await fetch(`/api/progress/${activeTaskId}`);
        if (!res.ok) return;

        const task = await res.json();
        updateProgressUI(task);

        if (task.status === 'completed') {
          clearInterval(pollInterval);
          btnStartDownload.disabled = false;
          handleDownloadCompleted(task);
        } else if (task.status === 'error') {
          clearInterval(pollInterval);
          btnStartDownload.disabled = false;
          progressCard.classList.add('hidden');
          showNotification('Lỗi khi tải: ' + (task.error || 'Không xác định'));
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 450);
  }

  function updateProgressUI(task) {
    const percent = Math.min(Math.max(task.percent || 0, 0), 100);
    progressBar.style.width = `${percent}%`;
    percentNumber.textContent = Math.floor(percent);

    progressStatusText.textContent = task.status_text || 'Đang xử lý...';

    if (task.downloaded_str && task.total_str) {
      progressDownloaded.textContent = `${task.downloaded_str} / ${task.total_str}`;
    }
    if (task.speed_str) {
      progressSpeed.textContent = task.speed_str;
    } else {
      progressSpeed.textContent = '';
    }
    if (task.eta_str) {
      progressEta.textContent = `Còn: ${task.eta_str}`;
    } else {
      progressEta.textContent = '';
    }
  }

  function handleDownloadCompleted(task) {
    progressCard.classList.add('hidden');
    resultCard.classList.remove('hidden');

    const isVideo = task.is_video || (task.filename && task.filename.toLowerCase().endsWith('.mp4'));
    resultFileName.textContent = task.filename || (isVideo ? 'video_fullhd.mp4' : 'bai_hat.mp3');

    if (isVideo) {
      resultSuccessTitle.textContent = 'Đã tải xong video Full HD 1080p!';
      resultMediaIcon.className = 'fa-solid fa-film disc-spinning';
      videoPlayerBox.classList.remove('hidden');
      audioPlayerBox.classList.add('hidden');

      audioPlayer.pause();
      videoPlayer.src = task.stream_url;
      videoPlayer.load();
    } else {
      resultSuccessTitle.textContent = 'Đã tạo file nhạc thành công!';
      resultMediaIcon.className = 'fa-solid fa-compact-disc disc-spinning';
      audioPlayerBox.classList.remove('hidden');
      videoPlayerBox.classList.add('hidden');

      videoPlayer.pause();
      audioPlayer.src = task.stream_url;
      audioPlayer.load();
    }

    btnDownloadBrowser.href = task.file_url;
    btnDownloadBrowser.setAttribute('download', task.filename);

    // Auto trigger browser download
    try {
      const a = document.createElement('a');
      a.href = task.file_url;
      a.download = task.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (e) {
      console.log('Auto download triggered');
    }

    resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Save to session history
    const ext = (task.filename.split('.').pop() || 'MP4').toUpperCase();
    saveSessionItem({
      filename: task.filename,
      title: task.title || task.filename,
      file_url: task.file_url,
      stream_url: task.stream_url,
      is_video: isVideo,
      format: isVideo ? 'MP4 Full HD' : ext,
      time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
    });
  }

  // Convert another
  btnConvertAnother.addEventListener('click', () => {
    urlInput.value = '';
    btnClear.classList.add('hidden');
    previewCard.classList.add('hidden');
    resultCard.classList.add('hidden');
    progressCard.classList.add('hidden');
    if (audioPlayer) audioPlayer.pause();
    if (videoPlayer) videoPlayer.pause();
    urlInput.focus();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  // Clear history
  btnClearHistory.addEventListener('click', () => {
    if (confirm('Bạn có chắc chắn muốn xóa toàn bộ danh sách vừa tải trong phiên này?')) {
      clearAllSessionHistory();
    }
  });

  // Render session history
  function renderSessionHistory() {
    const items = getSessionHistory();
    historyCountBadge.textContent = `${items.length} mục`;

    if (items.length === 0) {
      historyList.innerHTML = `
        <div class="empty-state">
          <i class="fa-solid fa-film empty-icon"></i>
          <p>Chưa có video hoặc bài hát nào được tải trong phiên này.</p>
          <span>Dán link Facebook hoặc YouTube phía trên để bắt đầu tải!</span>
        </div>
      `;
      return;
    }

    historyList.innerHTML = items.map(item => {
      const cleanName = item.title ? item.title.replace(/\.[^/.]+$/, "") : item.filename;
      const isVid = item.is_video || item.format.includes('MP4');

      return `
        <div class="history-item">
          <div class="history-item-left">
            <div class="${isVid ? 'audio-icon-pill video-icon-pill' : 'audio-icon-pill'}">
              <i class="${isVid ? 'fa-solid fa-film' : 'fa-solid fa-headphones'}"></i>
            </div>
            <div class="history-meta">
              <div class="history-title" title="${item.filename}">${cleanName}</div>
              <div class="history-sub">
                <span class="${isVid ? 'tag-video' : 'tag-format'}">${isVid ? '🎬 ' : '🎵 '}${item.format}</span>
                <span>Tải lúc: ${item.time}</span>
              </div>
            </div>
          </div>
          <div class="history-actions">
            <button class="btn-history-play" title="Xem / Nghe thử" data-stream="${item.stream_url}" data-name="${encodeURIComponent(item.filename)}" data-isvideo="${isVid}">
              <i class="fa-solid fa-play"></i>
            </button>
            <a href="${item.file_url}" download="${item.filename}" class="btn-history-dl" title="Tải lại về máy">
              <i class="fa-solid fa-download"></i>
            </a>
          </div>
        </div>
      `;
    }).join('');

    // Attach play listeners
    document.querySelectorAll('.btn-history-play').forEach(btn => {
      btn.addEventListener('click', () => {
        const streamUrl = btn.getAttribute('data-stream');
        const fileName = decodeURIComponent(btn.getAttribute('data-name'));
        const isVid = btn.getAttribute('data-isvideo') === 'true';

        resultFileName.textContent = fileName;
        resultCard.classList.remove('hidden');
        btnDownloadBrowser.href = `/api/download-file/${encodeURIComponent(fileName)}`;
        btnDownloadBrowser.setAttribute('download', fileName);

        if (isVid) {
          resultSuccessTitle.textContent = 'Đang phát video đã tải!';
          resultMediaIcon.className = 'fa-solid fa-film disc-spinning';
          videoPlayerBox.classList.remove('hidden');
          audioPlayerBox.classList.add('hidden');
          audioPlayer.pause();
          videoPlayer.src = streamUrl;
          videoPlayer.play();
        } else {
          resultSuccessTitle.textContent = 'Đang phát nhạc đã tải!';
          resultMediaIcon.className = 'fa-solid fa-compact-disc disc-spinning';
          audioPlayerBox.classList.remove('hidden');
          videoPlayerBox.classList.add('hidden');
          videoPlayer.pause();
          audioPlayer.src = streamUrl;
          audioPlayer.play();
        }

        resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    });
  }

  // Initial render of history
  renderSessionHistory();
});
