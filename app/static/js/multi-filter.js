(() => {
    const widgets = new Map();
    const values = select => Array.from(select.selectedOptions, o => o.value).filter(Boolean);
    const writeValues = (params, name, selected) => {
        params.delete(name);
        selected.forEach(value => params.append(name, value));
    };
    window.MultiFilter = {
        values,
        refresh(select) { widgets.get(select)?.refresh(); },
        reset(select) {
            Array.from(select.options).forEach(o => o.selected = false);
            widgets.get(select)?.refresh();
        }
    };
    function enhance(select) {
        const param = select.dataset.filterParam || select.name;
        const local = select.hasAttribute('data-filter-local');
        const auto = !!select.getAttribute('onchange');
        select.removeAttribute('onchange');
        select.multiple = true;
        const params = new URLSearchParams(location.search);
        if (!local && params.has(param)) {
            const selected = params.getAll(param);
            Array.from(select.options).forEach(o => o.selected = !!o.value && selected.includes(o.value));
        } else {
            Array.from(select.options).filter(o => !o.value).forEach(o => o.selected = false);
        }
        const label = select.dataset.filterLabel || select.getAttribute('aria-label') ||
            select.closest('label')?.textContent.trim() || select.previousElementSibling?.textContent.trim() || '필터';
        const emptyLabel = Array.from(select.options).find(o => !o.value)?.textContent.trim() || '전체';
        const wrap = document.createElement('span');
        wrap.className = 'multi-filter';
        const trigger = document.createElement('button');
        trigger.type = 'button';
        trigger.className = 'multi-filter-trigger';
        trigger.setAttribute('aria-expanded', 'false');
        select.before(wrap);
        wrap.append(trigger, select);
        select.hidden = true;
        select.classList.add('multi-filter-native');
        const panel = document.createElement('div');
        panel.className = 'multi-filter-panel';
        panel.hidden = true;
        panel.id = 'multi-filter-' + widgets.size;
        panel.setAttribute('role', 'group');
        panel.setAttribute('aria-label', label + ' 다중 선택');
        trigger.setAttribute('aria-controls', panel.id);
        const search = document.createElement('input');
        search.type = 'search';
        search.placeholder = '항목 검색';
        search.setAttribute('aria-label', label + ' 항목 검색');
        const list = document.createElement('div');
        list.className = 'multi-filter-options';
        const footer = document.createElement('div');
        footer.className = 'multi-filter-actions';
        const clear = document.createElement('button');
        clear.type = 'button'; clear.textContent = '선택 해제';
        const apply = document.createElement('button');
        apply.type = 'button'; apply.textContent = '적용'; apply.className = 'multi-filter-apply';
        footer.append(clear, apply);
        panel.append(search, list, footer);
        document.body.append(panel);
        let draft = new Set();
        const refresh = () => {
            const labels = Array.from(select.selectedOptions).filter(o => o.value).map(o => o.textContent.trim());
            trigger.textContent = labels.length > 1 ? labels[0] + ' 외 ' + (labels.length - 1) + '개 ▾' : (labels[0] || emptyLabel) + ' ▾';
            trigger.title = labels.join(', ') || emptyLabel;
            trigger.setAttribute('aria-label', label + ': ' + (labels.join(', ') || emptyLabel));
            trigger.disabled = select.disabled;
            trigger.classList.toggle('has-selection', labels.length > 0);
        };
        const close = (focus = false) => {
            panel.hidden = true; trigger.setAttribute('aria-expanded', 'false');
            if (focus) trigger.focus();
        };
        const render = () => {
            list.replaceChildren();
            Array.from(select.options).filter(o => o.value && o.textContent.toLowerCase().includes(search.value.toLowerCase())).forEach(o => {
                const row = document.createElement('label');
                const check = document.createElement('input');
                check.type = 'checkbox'; check.checked = draft.has(o.value); check.disabled = o.disabled;
                check.addEventListener('change', () => check.checked ? draft.add(o.value) : draft.delete(o.value));
                const text = document.createElement('span'); text.textContent = o.textContent.trim();
                row.append(check, text); list.append(row);
            });
            if (!list.childElementCount) list.textContent = '일치하는 항목이 없습니다.';
        };
        trigger.addEventListener('click', () => {
            if (!panel.hidden) { close(); return; }
            widgets.forEach(w => w.close());
            draft = new Set(values(select)); search.value = ''; render(); panel.hidden = false;
            trigger.setAttribute('aria-expanded', 'true');
            const rect = trigger.getBoundingClientRect();
            const width = Math.min(Math.max(rect.width, 260), window.innerWidth - 24);
            panel.style.width = width + 'px';
            panel.style.left = Math.max(12, Math.min(rect.left, window.innerWidth - width - 12)) + 'px';
            const height = Math.min(340, window.innerHeight - 24);
            panel.style.maxHeight = height + 'px';
            panel.style.top = Math.max(12, Math.min(rect.bottom + 6, window.innerHeight - height - 12)) + 'px';
            search.focus();
        });
        search.addEventListener('input', render);
        clear.addEventListener('click', () => { draft.clear(); render(); });
        apply.addEventListener('click', () => {
            Array.from(select.options).forEach(o => o.selected = draft.has(o.value));
            refresh(); close(true);
            select.dispatchEvent(new Event('change', {bubbles: true}));
            if (select.dataset.filterParam) {
                const url = new URL(location.href);
                writeValues(url.searchParams, param, values(select));
                url.searchParams.set('page', '1');
                location.assign(url.pathname + '?' + url.searchParams);
            } else if (auto && select.form) {
                select.form.requestSubmit();
            }
        });
        panel.addEventListener('keydown', event => {
            if (event.key === 'Escape') { event.preventDefault(); close(true); }
        });
        document.addEventListener('pointerdown', event => {
            if (!wrap.contains(event.target) && !panel.contains(event.target)) close();
        });
        panel.addEventListener('focusout', event => {
            if (event.relatedTarget && !panel.contains(event.relatedTarget) && event.relatedTarget !== trigger) close();
        });
        window.addEventListener('resize', () => close());

        select.addEventListener('change', refresh);
        new MutationObserver(refresh).observe(select, {childList:true, subtree:true, attributes:true, attributeFilter:['disabled']});
        widgets.set(select, {refresh, close}); refresh();
    }
    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('select[data-multi-filter]').forEach(enhance);
        // Search forms outside table-header filters carry every selected value.
        document.querySelectorAll('form').forEach(form => {
            if ((form.getAttribute('method') || 'get').toLowerCase() !== 'get') return;
            form.addEventListener('submit', () => {
                widgets.forEach((widget, select) => {
                    const name = select.dataset.filterParam;
                    if (!name) return;
                    const hidden = Array.from(form.querySelectorAll('input[type=hidden]')).filter(i => i.name === name);
                    if (!hidden.length) return;
                    hidden.forEach(i => i.remove());
                    const selected = values(select);
                    (selected.length ? selected : ['']).forEach(value => {
                        const input = document.createElement('input');
                        input.type = 'hidden'; input.name = name; input.value = value; form.append(input);
                    });
                });
                form.querySelectorAll('input[name=page]').forEach(input => input.value = '1');
            });
        });
    });
    document.addEventListener('click', event => {
        const link = event.target.closest('a[href]');
        if (!link) return;
        const url = new URL(link.href, location.href);
        if (url.origin !== location.origin) return;
        const pagination = url.pathname === location.pathname && url.searchParams.has('page');
        const mrpDownload = location.pathname === '/mrp/result' && url.pathname.startsWith('/mrp/result/download');
        if (!pagination && !mrpDownload) return;
        const current = new URLSearchParams(location.search);
        widgets.forEach((widget, select) => {
            if (select.hasAttribute('data-filter-local')) return;
            const name = select.dataset.filterParam || select.name;
            if (current.has(name)) writeValues(url.searchParams, name, current.getAll(name));
        });
        link.href = url.pathname + '?' + url.searchParams;
    });
})();
