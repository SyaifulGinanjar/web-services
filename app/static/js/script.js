/**
 * Navigasi tanpa reload penuh: link & form internal di-fetch, lalu hanya
 * <main id="app-content"> yang diganti. Navbar & sidebar tetap (tidak ikut reload).
 * Tanpa JavaScript, semua link & form tetap berfungsi normal (progressive enhancement).
 */
(() => {
  'use strict';

  const CONTENT_SELECTOR = '#app-content';
  const SIDEBAR_KEY = 'sidebar-collapsed';
  const MOBILE_QUERY = window.matchMedia('(max-width: 991.98px)');

  let controller = null;
  let pageCleanup = null;

  // ---------------------------------------------------------------- Helpers
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const storage = {
    get(key) { try { return localStorage.getItem(key); } catch { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch { /* diabaikan */ } },
  };

  function debounce(fn, wait) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), wait);
    };
  }

  function isInternalUrl(url) {
    return url.origin === window.location.origin && !url.pathname.startsWith('/api/')
      && !url.pathname.startsWith('/static/');
  }

  // ---------------------------------------------------------- Progress bar
  const progress = {
    el: null,
    timer: null,
    start() {
      this.el = this.el || $('#nav-progress');
      if (!this.el) return;
      clearTimeout(this.timer);
      this.el.classList.remove('done');
      this.el.classList.add('active');
    },
    done() {
      if (!this.el) return;
      this.el.classList.add('done');
      this.timer = setTimeout(() => this.el.classList.remove('active', 'done'), 300);
    },
  };

  // ---------------------------------------------------------------- Modals
  function closeOpenModals() {
    $$('.modal.show').forEach((el) => bootstrap.Modal.getInstance(el)?.hide());
    $$('.modal-backdrop').forEach((el) => el.remove());
    document.body.classList.remove('modal-open');
    document.body.style.removeProperty('overflow');
    document.body.style.removeProperty('padding-right');
  }

  // --------------------------------------------------------------- Sidebar
  function updateSidebar(section) {
    $$('#sidebar .sidebar-link').forEach((link) => {
      const active = link.dataset.section === section;
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
  }

  function initSidebar() {
    const button = $('#sidebar-button');
    if (!button) return;

    if (!MOBILE_QUERY.matches && storage.get(SIDEBAR_KEY) === '1') {
      document.body.classList.add('sidebar-collapsed');
    }

    button.addEventListener('click', () => {
      if (MOBILE_QUERY.matches) {
        document.body.classList.toggle('sidebar-open');
      } else {
        const collapsed = document.body.classList.toggle('sidebar-collapsed');
        storage.set(SIDEBAR_KEY, collapsed ? '1' : '0');
      }
    });

    document.addEventListener('click', (event) => {
      if (event.target.closest('[data-sidebar-close]')) document.body.classList.remove('sidebar-open');
    });
  }

  // ------------------------------------------------------------ Navigation
  async function navigate(url, { method = 'GET', body = null, push = true } = {}) {
    controller?.abort();
    controller = new AbortController();
    progress.start();

    try {
      const response = await fetch(url, {
        method,
        body,
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'fetch' },
        signal: controller.signal,
      });

      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('text/html')) {
        window.location.assign(response.url);
        return;
      }

      const html = await response.text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const next = $(CONTENT_SELECTOR, doc);
      const current = $(CONTENT_SELECTOR);

      // Halaman tanpa layout (login, error) -> muat penuh
      if (!next || !current) {
        if (method === 'GET') {
          window.location.assign(response.url);
        } else {
          document.open();
          document.write(html);
          document.close();
        }
        return;
      }

      const focusedId = document.activeElement?.id;
      const selection = focusedId && document.activeElement.selectionStart;

      closeOpenModals();
      runPageCleanup();
      current.replaceWith(next);
      document.title = doc.title;

      // POST tanpa redirect (mis. validasi gagal) -> URL tetap
      const finalUrl = method === 'GET' || response.redirected ? response.url : window.location.href;
      if (push && finalUrl !== window.location.href) {
        history.pushState({ spa: true }, '', finalUrl);
      } else {
        history.replaceState({ spa: true }, '', finalUrl);
      }

      updateSidebar(next.dataset.section);
      document.body.classList.remove('sidebar-open');
      initPage(next);

      // Pertahankan fokus input (mis. live search) atau scroll ke atas
      const refocus = focusedId && document.getElementById(focusedId);
      if (refocus && next.contains(refocus) && refocus.matches('input, select, textarea')) {
        refocus.focus();
        if (typeof selection === 'number' && refocus.setSelectionRange) {
          try { refocus.setSelectionRange(selection, selection); } catch { /* tipe input tidak mendukung */ }
        }
      } else if (push) {
        window.scrollTo({ top: 0 });
        next.focus({ preventScroll: true });
      }
    } catch (error) {
      if (error.name === 'AbortError') return;
      console.error(error);
      // Fallback aman: navigasi biasa
      if (method === 'GET') window.location.assign(url);
    } finally {
      progress.done();
    }
  }

  function onLinkClick(event) {
    if (event.defaultPrevented || event.button !== 0
      || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

    const link = event.target.closest('a[href]');
    if (!link || link.target || link.hasAttribute('download') || link.closest('[data-no-nav]')) return;

    const href = link.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('javascript:')) {
      if (href === '#') event.preventDefault();
      return;
    }

    const url = new URL(link.href);
    if (!isInternalUrl(url)) return;

    event.preventDefault();
    navigate(url.href);
  }

  function submitForm(form, submitter) {
    const method = (submitter?.getAttribute('formmethod') || form.getAttribute('method') || 'GET').toUpperCase();
    const action = new URL(submitter?.getAttribute('formaction') || form.getAttribute('action') || window.location.href,
      window.location.href);
    const formData = new FormData(form, submitter || undefined);

    if (method === 'GET') {
      const params = new URLSearchParams();
      formData.forEach((value, key) => {
        if (value !== '') params.append(key, value);
      });
      params.delete('page'); // filter/search baru selalu mulai dari halaman 1
      action.search = params.toString();
      return navigate(action.href);
    }
    return navigate(action.href, { method, body: formData });
  }

  function onSubmit(event) {
    const form = event.target;
    if (event.defaultPrevented || !(form instanceof HTMLFormElement)) return;

    if (form.dataset.confirm && !form.dataset.confirmed) {
      event.preventDefault();
      confirmDialog(form.dataset.confirm).then((ok) => {
        if (!ok) return;
        form.dataset.confirmed = '1';
        form.requestSubmit(event.submitter || undefined);
      });
      return;
    }
    delete form.dataset.confirmed;

    if (form.hasAttribute('data-no-nav') || form.target) return;
    const action = new URL(form.getAttribute('action') || window.location.href, window.location.href);
    if (!isInternalUrl(action)) return;

    event.preventDefault();
    const submitter = event.submitter;
    const pending = submitForm(form, submitter); // FormData dibuat sebelum tombol di-disable
    if (submitter) {
      submitter.disabled = true;
      pending.finally(() => { submitter.disabled = false; });
    }
  }

  // --------------------------------------------------------- Confirm modal
  function confirmDialog(message) {
    const el = $('#confirmModal');
    if (!el || !window.bootstrap) return Promise.resolve(window.confirm(message));

    return new Promise((resolve) => {
      let confirmed = false;
      $('[data-confirm-message]', el).textContent = message;
      const okButton = $('[data-confirm-ok]', el);
      const modal = bootstrap.Modal.getOrCreateInstance(el);

      const onOk = () => { confirmed = true; modal.hide(); };
      okButton.addEventListener('click', onOk, { once: true });
      el.addEventListener('hidden.bs.modal', () => {
        okButton.removeEventListener('click', onOk);
        resolve(confirmed);
      }, { once: true });
      modal.show();
    });
  }

  // --------------------------------------------- Live search & auto submit
  const liveSearch = debounce((input) => input.form?.requestSubmit(), 400);

  function onInput(event) {
    if (event.target.matches('[data-live-search]')) liveSearch(event.target);
  }

  function onChange(event) {
    if (event.target.matches('[data-auto-submit]')) event.target.form?.requestSubmit();
  }

  // ------------------------------------------------------------ Page inits
  const pages = {
    dashboard(root) {
      const dataEl = $('#dashboard-data', root);
      if (!dataEl || !window.Chart) return null;
      const data = JSON.parse(dataEl.textContent);
      const palette = ['#0d6efd', '#dc3545', '#ffc107', '#198754', '#6f42c1', '#20c997', '#fd7e14', '#0dcaf0'];
      const charts = [];

      const pie = (id, labels, values, colors) => {
        const canvas = $(`#${id}`, root);
        if (!canvas) return;
        charts.push(new Chart(canvas, {
          type: 'doughnut',
          data: { labels, datasets: [{ data: values, backgroundColor: colors || palette }] },
          options: { maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
        }));
      };

      const bar = (id, labels, datasets, horizontal = false) => {
        const canvas = $(`#${id}`, root);
        if (!canvas) return;
        charts.push(new Chart(canvas, {
          type: 'bar',
          data: { labels, datasets },
          options: {
            indexAxis: horizontal ? 'y' : 'x',
            maintainAspectRatio: false,
            scales: { x: { beginAtZero: true, ticks: { precision: 0 } }, y: { beginAtZero: true, ticks: { precision: 0 } } },
            plugins: { legend: { display: datasets.length > 1, position: 'bottom' } },
          },
        }));
      };

      const { kpi, kpi2 } = data;
      console.log('KPI Data:', kpi, kpi2); // Debugging output
      pie('chartKunjungan', ['Sesuai target', 'Melewati target'], [kpi.dispatch_ok, kpi.dispatch_gagal], ['#198754', '#dc3545']);
      pie('chartSelesai', ['Sesuai target', 'Melewati target'], [kpi2.completion_ok, kpi2.completion_gagal], ['#198754', '#dc3545']);
      pie('chartGaransi', data.garansi.map((r) => r.label), data.garansi.map((r) => r.total), ['#0d6efd', '#ffc107', '#adb5bd']);
      bar('chartTeknisi', data.teknisi.map((r) => r.label), [
        { label: 'Total pekerjaan', data: data.teknisi.map((r) => r.total), backgroundColor: '#0d6efd' },
        { label: 'Selesai', data: data.teknisi.map((r) => r.selesai), backgroundColor: '#198754' },
      ]);
      bar('chartUnit', data.unit.map((r) => r.label), [
        { label: 'Jumlah unit', data: data.unit.map((r) => r.total), backgroundColor: '#6f42c1' },
      ], true);

      return () => charts.forEach((chart) => chart.destroy());
    },
  };

  function runPageCleanup() {
    if (typeof pageCleanup === 'function') pageCleanup();
    pageCleanup = null;
  }

  function initPage(root) {
    const init = pages[root.dataset.page];
    pageCleanup = init ? init(root) : null;

    // Modal yang harus langsung terbuka (mis. validasi form tambah gagal)
    const modalEl = $('[data-open-on-load]', root);
    if (modalEl && window.bootstrap) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  // ------------------------------------------------------------------ Boot
  document.addEventListener('DOMContentLoaded', () => {
    initSidebar();

    const root = $(CONTENT_SELECTOR);
    if (!root) return; // halaman tanpa layout (login/error)

    history.replaceState({ spa: true }, '', window.location.href);
    initPage(root);

    document.addEventListener('click', onLinkClick);
    document.addEventListener('submit', onSubmit);
    document.addEventListener('input', onInput);
    document.addEventListener('change', onChange);
    window.addEventListener('popstate', (event) => {
      if (event.state?.spa) navigate(window.location.href, { push: false });
    });
  });
})();
