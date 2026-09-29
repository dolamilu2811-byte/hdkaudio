// HDK AUDIO - Client Application Logic (Cloud / Direct-Download Mode)

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const urlInput = document.getElementById('urlInput');
  const btnClear = document.getElementById('btnClear');
  const btnPaste = document.getElementById('btnPaste');
  const btnFetchInfo = document.getElementById('btnFetchInfo');
  const notifyBox = document.getElementById('notifyBox');
  const notifyMsg = document.getElementById('notifyMsg');

  // Preview elements
  const previewCard = document.getElementById('previewCard');
  const videoThumb = document.getElementById('videoThumb');
  const videoDuration = document.getElementById('videoDuration');
  const videoTitle = document.getElementById('videoTitle');
  const videoChannel = document.getElementById('videoChannel');
  const videoViews = document.getElementById('videoViews');
  const formatSelect = document.getElementById('formatSelect');
  const qualitySelect = document.getElementById('qualitySelect');
  const chkEmbedThumb = document.getElementById('chkEmbedThumb');
  const btnStartDownload = document.getElementById('btnStartDownload');

  // Progress elements
  const progressCard = document.getElementById('progressCard');
  const progressBar = document.getElementById('progressBar');
  const percentNumber = document.getElementById('percentNumber');
  const progressStatusText = document.getElementById('progressStatusText');
  const progressDetailText = document.getElementById('progressDetailText');
  const progressDownloaded = document.getElementById('progressDownloaded');
  const progressSpeed = document.getElementById('progressSpeed');
  const progressEta = document.getElementById('progressEta');

  // Result & Player elements
  const resultCard = document.getElementById('resultCard');
  const resultFileName = document.getElementById('resultFileName');
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
  const STORAGE_KEY = 'hdk_audio_session_history';

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
      // Remove duplicate if exists
      history = history.filter(h => h.filename !== item.filename);
      history.unshift(item);
      if (history.length > 20) history.pop();
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
  function showNotification(msg, isSuccess = false) {
    notifyMsg.textContent = msg;
    notifyBox.className = 'notify-box ' + (isSuccess ? 'success' : '');
    notifyBox.classList.remove('hidden');
  }

  function hideNotification() {
    notifyBox.classList.add('hidden');
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
        showNotification('Bộ nhớ tạm (Clipboard) đang trống. Hãy copy link YouTube trước rồi dán vào đây.');
      }
    } catch (err) {
      urlInput.focus();
      showNotification('Vui lòng bấm Ctrl + V vào ô dán link (Trình duyệt chưa cấp quyền đọc tự động).');
    }
  });

  // Fetch Video Info with strict timeout
  async function fetchVideoInfo() {
    const rawUrl = urlInput.value.trim();
    if (!rawUrl) {
      showNotification('Vui lòng nhập hoặc dán link video YouTube vào ô trên!');
      urlInput.focus();
      return;
    }

    if (!rawUrl.includes('http://') && !rawUrl.includes('https://') && !rawUrl.includes('youtu')) {
      showNotification('Vui lòng nhập một đường link YouTube hợp lệ (ví dụ: https://www.youtube.com/watch?v=...)');
      urlInput.focus();
      return;
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
    const timeoutId = setTimeout(() => controller.abort(), 25000);

    try {
      const res = await fetch('/api/info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: rawUrl }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Không thể phân tích video này.');
      }

      currentVideoData = data;

      // Populate preview
      videoThumb.src = data.thumbnail || 'https://via.placeholder.com/640x360?text=No+Thumbnail';
      videoDuration.textContent = data.duration_str || '00:00';
      videoTitle.textContent = data.title || 'Không có tiêu đề';
      videoChannel.textContent = data.uploader || 'YouTube';
      videoViews.textContent = data.view_count || '0';

      previewCard.classList.remove('hidden');
      resultCard.classList.add('hidden');
      progressCard.classList.add('hidden');

      previewCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    } catch (err) {
      if (err.name === 'AbortError') {
        showNotification('Quá thời gian kết nối YouTube (25s). Bạn vui lòng bấm "Phân tích" lại một lần nữa!');
      } else {
        showNotification(err.message || 'Lỗi khi kết nối tới máy chủ.');
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
      showNotification('Vui lòng phân tích đường link trước khi xuất nhạc.');
      return;
    }

    const payload = {
      url: currentVideoData.url,
      format: formatSelect.value,
      quality: qualitySelect.value,
      embed_thumbnail: chkEmbedThumb.checked
    };

    btnStartDownload.disabled = true;
    hideNotification();
    resultCard.classList.add('hidden');
    progressCard.classList.remove('hidden');
    progressCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    updateProgressUI({
      percent: 5,
      status_text: 'Đang khởi động tiến trình trích xuất âm thanh...',
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
          showNotification('Lỗi xuất nhạc: ' + (task.error || 'Không xác định'));
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

    resultFileName.textContent = task.filename || 'bai_hat.mp3';
    audioPlayer.src = task.stream_url;
    audioPlayer.load();

    btnDownloadBrowser.href = task.file_url;
    btnDownloadBrowser.setAttribute('download', task.filename);

    // Auto-trigger browser download popup
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
    saveSessionItem({
      filename: task.filename,
      title: task.title || task.filename,
      file_url: task.file_url,
      stream_url: task.stream_url,
      format: (task.filename.split('.').pop() || 'MP3').toUpperCase(),
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
    audioPlayer.pause();
    urlInput.focus();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  // Render session history
  function renderSessionHistory() {
    const items = getSessionHistory();
    historyCountBadge.textContent = `${items.length} bài`;

    if (items.length === 0) {
      historyList.innerHTML = `
        <div class="empty-state">
          <i class="fa-solid fa-music empty-icon"></i>
          <p>Chưa có bài hát nào được tải trong phiên này.</p>
          <span>Dán link phía trên để bắt đầu xuất bài hát đầu tiên!</span>
        </div>
      `;
      return;
    }

    historyList.innerHTML = items.map(item => {
      const cleanName = item.title ? item.title.replace(/\.[^/.]+$/, "") : item.filename;

      return `
        <div class="history-item">
          <div class="history-item-left">
            <div class="audio-icon-pill">
              <i class="fa-solid fa-headphones"></i>
            </div>
            <div class="history-meta">
              <div class="history-title" title="${item.filename}">${cleanName}</div>
              <div class="history-sub">
                <span class="tag-format">${item.format}</span>
                <span>Tải lúc: ${item.time}</span>
              </div>
            </div>
          </div>
          <div class="history-actions">
            <button class="btn-history-play" title="Nghe thử" data-stream="${item.stream_url}" data-name="${encodeURIComponent(item.filename)}">
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
        resultFileName.textContent = fileName;
        audioPlayer.src = streamUrl;
        resultCard.classList.remove('hidden');
        btnDownloadBrowser.href = `/api/download-file/${encodeURIComponent(fileName)}`;
        btnDownloadBrowser.setAttribute('download', fileName);
        audioPlayer.play();
        resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    });
  }

  btnClearHistory.addEventListener('click', () => {
    if (confirm('Bạn có muốn xóa danh sách các bài vừa tải trong phiên này không?')) {
      clearAllSessionHistory();
    }
  });

  // Initial load
  renderSessionHistory();
});
