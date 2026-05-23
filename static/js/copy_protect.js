(function () {
  'use strict';

  // トースト通知を表示
  function showToast() {
    var existing = document.getElementById('cp-toast');
    if (existing) existing.remove();

    var toast = document.createElement('div');
    toast.id = 'cp-toast';
    toast.textContent = 'コピーは禁止されています';
    toast.style.cssText = [
      'position:fixed', 'bottom:80px', 'left:50%',
      'transform:translateX(-50%)',
      'background:rgba(30,30,30,0.85)', 'color:#fff',
      'padding:8px 20px', 'border-radius:20px',
      'font-size:.85rem', 'z-index:9999',
      'pointer-events:none',
      'transition:opacity .4s'
    ].join(';');
    document.body.appendChild(toast);
    setTimeout(function () {
      toast.style.opacity = '0';
      setTimeout(function () { toast.remove(); }, 400);
    }, 1800);
  }

  // レビューカード内かどうか判定
  function inReviewCard(el) {
    return !!el.closest('.review-card');
  }

  // 右クリック禁止（レビューカード内のみ）
  document.addEventListener('contextmenu', function (e) {
    if (inReviewCard(e.target)) {
      e.preventDefault();
      showToast();
    }
  });

  // コピーイベント禁止（レビューカード内のみ）
  document.addEventListener('copy', function (e) {
    var sel = window.getSelection();
    if (sel && sel.anchorNode && inReviewCard(sel.anchorNode.parentElement || sel.anchorNode)) {
      e.preventDefault();
      e.clipboardData && e.clipboardData.setData('text/plain', '');
      showToast();
    }
  });

  // キーボードショートカット禁止（レビューカード内フォーカス時）
  document.addEventListener('keydown', function (e) {
    if (!inReviewCard(e.target)) return;
    var key = e.key.toUpperCase();
    // Ctrl+C / Ctrl+X / Ctrl+A / Ctrl+U（ソース表示）
    if (e.ctrlKey && (key === 'C' || key === 'X' || key === 'A' || key === 'U')) {
      e.preventDefault();
      showToast();
    }
  });

  // グローバルキーボード（Ctrl+U はページ全体で防ぐ）
  document.addEventListener('keydown', function (e) {
    if (e.ctrlKey && e.key.toUpperCase() === 'U') {
      e.preventDefault();
    }
  });

  // 印刷禁止（Ctrl+P）
  document.addEventListener('keydown', function (e) {
    if (e.ctrlKey && e.key.toUpperCase() === 'P') {
      e.preventDefault();
      showToast();
    }
  });

  // beforeprint でも阻止
  window.addEventListener('beforeprint', function (e) {
    e.preventDefault();
    showToast();
  });

})();
