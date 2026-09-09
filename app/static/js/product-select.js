(function () {
    "use strict";

    let active = null;
    let menu = null;

    function closeMenu() {
        if (!active) return;
        active.wrapper.closest("td")?.classList.remove("editing", "product-select-editing");
        active.wrapper.classList.remove("is-open");
        active.button.setAttribute("aria-expanded", "false");
        if (menu) menu.remove();
        menu = null;
        active = null;
    }

    function positionMenu(wrapper) {
        if (!menu) return;
        const rect = wrapper.getBoundingClientRect();
        const below = window.innerHeight - rect.bottom;
        const openUp = below < 240 && rect.top > below;
        menu.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - rect.width - 8)) + "px";
        menu.style.width = rect.width + "px";
        menu.style.maxHeight = Math.max(140, Math.min(280, openUp ? rect.top - 12 : below - 12)) + "px";
        menu.style.top = openUp ? "auto" : rect.bottom + 5 + "px";
        menu.style.bottom = openUp ? (window.innerHeight - rect.top + 5) + "px" : "auto";
    }

    function selectOption(select, index) {
        if (select.disabled || select.options[index]?.disabled) return;
        select.selectedIndex = index;
        select.dispatchEvent(new Event("change", { bubbles: true }));
        const display = select.closest("td")?.querySelector(".display, .grade-text, .product-select-cell-value");
        if (display) display.textContent = select.options[index]?.textContent || "-";
        sync(select);
        closeMenu();
    }

    function openMenu(select, wrapper, button) {
        if (active?.select === select) return closeMenu();
        closeMenu();
        active = { select, wrapper, button };
        wrapper.classList.add("is-open");
        button.setAttribute("aria-expanded", "true");
        menu = document.createElement("div");
        menu.className = "product-select-menu";
        menu.setAttribute("role", "listbox");

        Array.from(select.options).forEach((option, index) => {
            const item = document.createElement("button");
            item.type = "button";
            item.className = "product-select-option";
            item.textContent = option.textContent;
            item.disabled = option.disabled;
            item.setAttribute("role", "option");
            item.setAttribute("aria-selected", String(index === select.selectedIndex));
            if (index === select.selectedIndex) item.classList.add("is-selected");
            item.addEventListener("click", () => selectOption(select, index));
            menu.appendChild(item);
        });

        document.body.appendChild(menu);
        menu.addEventListener("wheel", event => {
            event.preventDefault();
            event.stopPropagation();
            const multiplier = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? menu.clientHeight : 1;
            menu.scrollTop += event.deltaY * multiplier;
        }, { passive: false });
        positionMenu(wrapper);
        menu.querySelector(".is-selected")?.scrollIntoView({ block: "nearest" });
    }

    function sync(select) {
        const wrapper = select.closest(".product-select");
        if (!wrapper) return;
        const button = wrapper.querySelector(".product-select-trigger");
        const option = select.options[select.selectedIndex];
        button.querySelector(".product-select-value").textContent = option?.textContent || "선택";
        button.disabled = select.disabled;
        wrapper.classList.toggle("is-disabled", select.disabled);
    }

    function enhance(select) {
        if (select.dataset.productSelect === "true" || select.multiple || select.size > 1) return;
        select.dataset.productSelect = "true";
        const wrapper = document.createElement("span");
        wrapper.className = "product-select";
        if (select.classList.contains("editor")) wrapper.classList.add("product-select-editor");
        const cell = select.closest("td");
        if (cell) wrapper.classList.add("product-select-cell-editor");
        select.parentNode.insertBefore(wrapper, select);
        wrapper.appendChild(select);

        const button = document.createElement("button");
        button.type = "button";
        button.className = "product-select-trigger";
        button.setAttribute("aria-haspopup", "listbox");
        button.setAttribute("aria-expanded", "false");
        button.innerHTML = '<span class="product-select-value"></span><i class="fa-solid fa-chevron-down"></i>';
        wrapper.appendChild(button);
        button.addEventListener("click", () => openMenu(select, wrapper, button));
        button.addEventListener("keydown", event => {
            if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
                event.preventDefault();
                openMenu(select, wrapper, button);
            }
        });
        select.addEventListener("change", () => sync(select));
        new MutationObserver(() => sync(select)).observe(select, { childList: true, subtree: true, attributes: true });
        sync(select);

        if (cell && cell.dataset.productSelectCell !== "true") {
            cell.dataset.productSelectCell = "true";
            let display = cell.querySelector(".display, .grade-text, .product-select-cell-value");
            if (!display) {
                display = document.createElement("span");
                display.className = "product-select-cell-value";
                display.textContent = select.options[select.selectedIndex]?.textContent || "-";
                cell.insertBefore(display, wrapper);
            }
            cell.classList.add("product-select-cell");
            cell.addEventListener("click", event => {
                if (event.target.closest("a, input, button, .product-select-menu")) return;
                cell.classList.add("product-select-editing");
                if (active?.select !== select) wrapper.querySelector(".product-select-trigger").click();
            });
        }
    }

    function enhanceAll(root) {
        if (root.matches?.("select")) enhance(root);
        root.querySelectorAll?.("select").forEach(enhance);
    }

    document.addEventListener("DOMContentLoaded", () => {
        enhanceAll(document);
        new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(node => {
            if (node.nodeType === 1) enhanceAll(node);
        }))).observe(document.body, { childList: true, subtree: true });
    });
    document.addEventListener("click", event => {
        const activeCell = active?.wrapper.closest("td");
        if (active && !active.wrapper.contains(event.target) && !menu?.contains(event.target) && !activeCell?.contains(event.target)) closeMenu();
    });
    window.addEventListener("resize", closeMenu);
    document.addEventListener("scroll", event => {
        if (menu && (event.target === menu || menu.contains(event.target))) return;
        closeMenu();
    }, true);
    document.addEventListener("keydown", event => { if (event.key === "Escape") closeMenu(); });
})();
