/**
 * Advanced Interactions — Phase 4
 * Command Palette, Parallax Cards, Magnetic Cursor
 */
(function () {
    'use strict';
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // ===== COMMAND PALETTE (Ctrl+K) =====
    const NAV_ITEMS = [
        { label: 'Dashboard', icon: 'fa-chart-line', url: '/' },
        { label: 'Samples', icon: 'fa-box-open', url: '/samples' },
        { label: 'IOCs', icon: 'fa-crosshairs', url: '/iocs' },
        { label: 'MITRE ATT&CK', icon: 'fa-skull-crossbones', url: '/mitre-attack' },
        { label: 'AI Sandbox', icon: 'fa-robot', url: '/ai-sandbox' },
        { label: 'Isolation', icon: 'fa-user-shield', url: '/isolation' },
        { label: 'ML Feedback', icon: 'fa-brain', url: '/ml-feedback' },
        { label: 'Advanced', icon: 'fa-bolt', url: '/advanced' },
        { label: 'Admin Panel', icon: 'fa-gears', url: '/admin' },
    ];

    function createPalette() {
        const overlay = document.createElement('div');
        overlay.className = 'cmd-palette-overlay';
        overlay.id = 'cmdPalette';
        overlay.innerHTML = `
            <div class="cmd-palette">
                <input class="cmd-palette-input" id="cmdInput" placeholder="Search pages, actions..." autocomplete="off">
                <div class="cmd-palette-results" id="cmdResults"></div>
                <div class="cmd-palette-footer">
                    <span><kbd>↑↓</kbd> Navigate</span>
                    <span><kbd>↵</kbd> Open</span>
                    <span><kbd>Esc</kbd> Close</span>
                </div>
            </div>`;
        document.body.appendChild(overlay);

        const input = document.getElementById('cmdInput');
        const results = document.getElementById('cmdResults');
        let selectedIdx = 0;

        function render(filter = '') {
            const q = filter.toLowerCase();
            const filtered = NAV_ITEMS.filter(i => i.label.toLowerCase().includes(q));
            selectedIdx = 0;
            results.innerHTML = filtered.map((item, i) =>
                `<div class="cmd-palette-item ${i === 0 ? 'selected' : ''}" data-url="${item.url}">
                    <i class="fa-solid ${item.icon}"></i><span>${item.label}</span>
                </div>`
            ).join('') || '<div class="cmd-palette-item" style="color:var(--text-muted);cursor:default;">No results found</div>';
        }

        input.addEventListener('input', () => render(input.value));

        input.addEventListener('keydown', e => {
            const items = results.querySelectorAll('.cmd-palette-item[data-url]');
            if (e.key === 'ArrowDown') { e.preventDefault(); selectedIdx = Math.min(selectedIdx + 1, items.length - 1); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); selectedIdx = Math.max(selectedIdx - 1, 0); }
            else if (e.key === 'Enter') { if (items[selectedIdx]) window.location.href = items[selectedIdx].dataset.url; return; }
            else if (e.key === 'Escape') { closePalette(); return; }
            items.forEach((el, i) => el.classList.toggle('selected', i === selectedIdx));
            if (items[selectedIdx]) items[selectedIdx].scrollIntoView({ block: 'nearest' });
        });

        results.addEventListener('click', e => {
            const item = e.target.closest('.cmd-palette-item[data-url]');
            if (item) window.location.href = item.dataset.url;
        });

        overlay.addEventListener('click', e => { if (e.target === overlay) closePalette(); });
        render();
    }

    function openPalette() {
        const p = document.getElementById('cmdPalette');
        if (!p) return;
        p.classList.add('open');
        const input = document.getElementById('cmdInput');
        input.value = '';
        input.dispatchEvent(new Event('input'));
        requestAnimationFrame(() => input.focus());
    }

    function closePalette() {
        const p = document.getElementById('cmdPalette');
        if (p) p.classList.remove('open');
    }

    document.addEventListener('keydown', e => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const p = document.getElementById('cmdPalette');
            if (p && p.classList.contains('open')) closePalette();
            else openPalette();
        }
        if (e.key === 'Escape') closePalette();
    });

    createPalette();

    // ===== PARALLAX TILT CARDS =====
    if (!reducedMotion) {
        document.querySelectorAll('.card').forEach(card => {
            card.addEventListener('mousemove', e => {
                const rect = card.getBoundingClientRect();
                const x = (e.clientX - rect.left) / rect.width - 0.5;
                const y = (e.clientY - rect.top) / rect.height - 0.5;
                card.style.transform = `perspective(800px) rotateY(${x * 4}deg) rotateX(${-y * 4}deg) translateY(-3px)`;
                card.style.transition = 'transform 0.1s ease';
            });
            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
                card.style.transition = 'transform 0.5s cubic-bezier(0.16,1,0.3,1)';
            });
        });
    }

    // ===== MAGNETIC CURSOR ON BUTTONS =====
    if (!reducedMotion) {
        document.querySelectorAll('.btn-primary, .btn-secondary').forEach(btn => {
            btn.addEventListener('mousemove', e => {
                const rect = btn.getBoundingClientRect();
                const dx = e.clientX - (rect.left + rect.width / 2);
                const dy = e.clientY - (rect.top + rect.height / 2);
                btn.style.transform = `translate(${dx * 0.15}px, ${dy * 0.15}px)`;
                btn.style.transition = 'transform 0.15s ease';
            });
            btn.addEventListener('mouseleave', () => {
                btn.style.transform = '';
                btn.style.transition = 'transform 0.3s ease';
            });
        });
    }

    // ===== SMOOTH NUMBER COUNTING =====
    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const end = parseInt(el.textContent) || 0;
                if (end === 0) return;
                let start = 0;
                const duration = 800;
                const startTime = performance.now();
                function step(now) {
                    const progress = Math.min((now - startTime) / duration, 1);
                    const eased = 1 - Math.pow(1 - progress, 3);
                    el.textContent = Math.floor(eased * end);
                    if (progress < 1) requestAnimationFrame(step);
                }
                requestAnimationFrame(step);
                observer.unobserve(el);
            }
        });
    });
    document.querySelectorAll('.stat-value').forEach(el => observer.observe(el));
})();
