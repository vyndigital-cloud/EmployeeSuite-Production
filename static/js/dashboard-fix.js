(function () {
  'use strict';

  // Do not overwrite real implementations if they exist.
  if (typeof window.processOrders !== 'function') {
    window.processOrders = function () {
      console.error('processOrders: implementation missing');
    };
  }
  if (typeof window.updateInventory !== 'function') {
    window.updateInventory = function () {
      console.error('updateInventory: implementation missing');
    };
  }
  if (typeof window.generateReport !== 'function') {
    window.generateReport = function () {
      console.error('generateReport: implementation missing');
    };
  }
  if (typeof window.exportReport !== 'function') {
    window.exportReport = function () {
      console.error('exportReport: implementation missing');
    };
  }

  // Safe helper to call showLoading() if it exists without throwing
  function safeShowLoading() {
    try {
      if (typeof window.showLoading === 'function') window.showLoading();
    } catch (e) {
      console.warn('safeShowLoading error', e);
    }
  }

  function attachFallback(btn, fnName) {
    if (!btn || btn.__es_fallback_attached) return;
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      safeShowLoading();
      try {
        if (typeof window[fnName] === 'function') {
          window[fnName]();
        } else {
          console.error(fnName + ' is not a function');
        }
      } catch (err) {
        console.error(fnName + ' invocation failed', err);
      }
    });
    btn.__es_fallback_attached = true;
  }

  function initButtons() {
    try {
      var buttons = document.querySelectorAll('.card-btn');
      if (!buttons || buttons.length === 0) {
        // no buttons found — nothing to do
        return;
      }
      attachFallback(buttons[0], 'processOrders');
      attachFallback(buttons[1], 'updateInventory');
      attachFallback(buttons[2], 'generateReport');
      console.log('✅ Fallback button listeners initialized, buttons found:', buttons.length);
    } catch (err) {
      console.error('initButtons error', err);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initButtons);
  } else {
    initButtons();
  }
})();
