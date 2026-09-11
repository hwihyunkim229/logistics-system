(() => {
    const table = document.getElementById('planTable');
    const header = table.tHead.rows[0];
    const days = [...header.querySelectorAll('[data-plan-date]')];
    const weeks = [];
    days.forEach((day, index) => {
        const key = day.dataset.planWeek;
        if (!weeks.length || weeks[weeks.length - 1].key !== key) {
            weeks.push({key, indexes: []});
            day.classList.add('plan-week-boundary');
        }
        weeks[weeks.length - 1].indexes.push(index);
    });
    const totalHead = document.createElement('th');
    totalHead.className = 'plan-total';
    totalHead.textContent = '기간 합계';
    header.insertBefore(totalHead, days[0] || null);
    const weekTitle = week => {
        const first = days[week.indexes[0]].dataset.planDate.slice(5).replace('-', '/');
        const last = days[week.indexes[week.indexes.length - 1]].dataset.planDate.slice(5).replace('-', '/');
        return `${weeks.indexOf(week) + 1}주 · ${first}~${last}`;
    };
    const band = table.tHead.insertRow(0);
    const blank = document.createElement('th');
    blank.colSpan = 2;
    blank.textContent = '조회 기간';
    band.append(blank);
    weeks.forEach(week => {
        const cell = document.createElement('th');
        cell.colSpan = week.indexes.length;
        cell.className = 'plan-week-group';
        cell.textContent = weekTitle(week);
        band.append(cell);
        const weekly = document.createElement('th');
        weekly.className = 'plan-week-cell';
        weekly.textContent = weekTitle(week);
        header.append(weekly);
    });
    table.querySelectorAll('.child-row').forEach(row => {
        const cells = [...row.querySelectorAll('[data-plan-qty]')];
        const total = document.createElement('td');
        total.className = 'plan-total';
        total.textContent = Number(row.dataset.total || 0).toLocaleString('ko-KR');
        row.insertBefore(total, cells[0] || null);
        weeks.forEach(week => {
            cells[week.indexes[0]]?.classList.add('plan-week-boundary');
            const sum = week.indexes.reduce((value, index) => value + Number(cells[index]?.dataset.planQty || 0), 0);
            const cell = document.createElement('td');
            cell.className = 'plan-week-cell';
            cell.textContent = sum ? sum.toLocaleString('ko-KR') : '–';
            row.append(cell);
        });
    });
    function setView(mode) {
        const weekly = mode === 'week';
        table.querySelectorAll('[data-plan-date],[data-plan-qty]').forEach(cell => cell.hidden = weekly);
        table.querySelectorAll('.plan-week-cell').forEach(cell => cell.hidden = !weekly);
        band.hidden = weekly;
        [...header.cells].forEach(cell => cell.style.setProperty('top', weekly ? '0px' : `${band.getBoundingClientRect().height}px`, 'important'));
        table.querySelectorAll('.group-row > td').forEach(cell => cell.colSpan = 2 + (weekly ? weeks.length : days.length));
        document.querySelectorAll('[data-plan-view]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.planView === mode)));
    }
    document.querySelectorAll('[data-plan-view]').forEach(button => button.addEventListener('click', () => setView(button.dataset.planView)));
    const today = new Intl.DateTimeFormat('sv-SE', {timeZone: 'Asia/Seoul'}).format(new Date());
    const todayHeader = days.find(day => day.dataset.planDate === today);
    todayHeader?.classList.add('plan-today');
    const todayButton = document.getElementById('planToday');
    todayButton.disabled = !todayHeader;
    todayButton.addEventListener('click', () => {
        setView('day');
        if (todayHeader) {
            const wrap = table.closest('.table-wrap');
            wrap.scrollLeft += todayHeader.getBoundingClientRect().left - wrap.getBoundingClientRect().left - 440;
        }
    });
    setView('day');
})();
