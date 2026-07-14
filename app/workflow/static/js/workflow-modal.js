(function () {

    const style = document.createElement("style");

    style.textContent = `
    .wf-alert-overlay{
        display:none;
        position:fixed;
        inset:0;
        background:rgba(15,23,42,.45);
        justify-content:center;
        align-items:center;
        z-index:99999;
    }
    .wf-alert-box{
        width:400px;
        max-width:90%;
        background:#fff;
        border-radius:14px;
        padding:28px;
        box-shadow:0 20px 60px rgba(0,0,0,.18);
        animation:wfAlertOpen .22s ease;
        text-align:center;
    }
    @keyframes wfAlertOpen{
        from{ opacity:0; transform:translateY(16px); }
        to{ opacity:1; transform:none; }
    }
    .wf-alert-icon{
        width:52px;
        height:52px;
        border-radius:50%;
        background:#fef3c7;
        color:#ca8a04;
        font-size:26px;
        font-weight:700;
        display:flex;
        align-items:center;
        justify-content:center;
        margin:0 auto 16px;
    }
    .wf-alert-title{
        font-size:18px;
        font-weight:700;
        color:#1e293b;
        margin-bottom:10px;
    }
    .wf-alert-message{
        font-size:14px;
        color:#475569;
        line-height:1.6;
        white-space:pre-line;
        margin-bottom:22px;
    }
    .wf-alert-btn{
        border:none;
        cursor:pointer;
        background:#2563eb;
        color:white;
        padding:10px 34px;
        border-radius:9px;
        font-size:14px;
        font-weight:600;
        transition:.2s;
    }
    .wf-alert-btn:hover{
        background:#1d4ed8;
    }
    .wf-confirm-overlay{
        display:none;
        position:fixed;
        inset:0;
        background:rgba(15,23,42,.45);
        justify-content:center;
        align-items:center;
        z-index:99999;
    }
    .wf-confirm-box{
        width:400px;
        max-width:90%;
        background:#fff;
        border-radius:14px;
        padding:28px;
        box-shadow:0 20px 60px rgba(0,0,0,.18);
        animation:wfAlertOpen .22s ease;
        text-align:center;
    }
    .wf-confirm-icon{
        width:52px;
        height:52px;
        border-radius:50%;
        background:#fee2e2;
        color:#dc2626;
        font-size:24px;
        font-weight:700;
        display:flex;
        align-items:center;
        justify-content:center;
        margin:0 auto 16px;
    }
    .wf-confirm-title{
        font-size:18px;
        font-weight:700;
        color:#1e293b;
        margin-bottom:10px;
    }
    .wf-confirm-message{
        font-size:14px;
        color:#475569;
        line-height:1.6;
        white-space:pre-line;
        margin-bottom:22px;
    }
    .wf-confirm-actions{
        display:flex;
        gap:10px;
        justify-content:center;
    }
    .wf-confirm-btn{
        border:none;
        cursor:pointer;
        padding:10px 28px;
        border-radius:9px;
        font-size:14px;
        font-weight:600;
        transition:.2s;
    }
    .wf-confirm-cancel{
        background:#f1f5f9;
        color:#334155;
    }
    .wf-confirm-cancel:hover{
        background:#e2e8f0;
    }
    .wf-confirm-ok{
        background:#dc2626;
        color:#fff;
    }
    .wf-confirm-ok:hover{
        background:#b91c1c;
    }
    `;

    document.head.appendChild(style);

    const overlay = document.createElement("div");
    overlay.className = "wf-alert-overlay";

    overlay.innerHTML = `
        <div class="wf-alert-box">
            <div class="wf-alert-icon">!</div>
            <div class="wf-alert-title"></div>
            <div class="wf-alert-message"></div>
            <button type="button" class="wf-alert-btn">확인</button>
        </div>
    `;

    function mount() {
        document.body.appendChild(overlay);
    }

    if (document.body) {
        mount();
    } else {
        document.addEventListener("DOMContentLoaded", mount);
    }

    const titleEl = overlay.querySelector(".wf-alert-title");
    const messageEl = overlay.querySelector(".wf-alert-message");
    const buttonEl = overlay.querySelector(".wf-alert-btn");

    let resolver = null;

    function close() {
        overlay.style.display = "none";
        if (resolver) {
            resolver();
            resolver = null;
        }
    }

    buttonEl.addEventListener("click", close);

    overlay.addEventListener("click", function (e) {
        if (e.target === overlay) close();
    });

    window.addEventListener("keydown", function (e) {
        if (
            (e.key === "Escape" || e.key === "Enter")
            && overlay.style.display === "flex"
        ) {
            e.preventDefault();
            close();
        }
    });

    window.wfAlert = function (message, title) {
        titleEl.innerText = title || "알림";
        messageEl.innerText = message || "";
        overlay.style.display = "flex";
        buttonEl.focus();

        return new Promise(function (resolve) {
            resolver = resolve;
        });
    };

    const confirmOverlay = document.createElement("div");
    confirmOverlay.className = "wf-confirm-overlay";

    confirmOverlay.innerHTML = `
        <div class="wf-confirm-box">
            <div class="wf-confirm-icon">!</div>
            <div class="wf-confirm-title"></div>
            <div class="wf-confirm-message"></div>
            <div class="wf-confirm-actions">
                <button type="button" class="wf-confirm-btn wf-confirm-cancel">취소</button>
                <button type="button" class="wf-confirm-btn wf-confirm-ok">삭제</button>
            </div>
        </div>
    `;

    function mountConfirm() {
        document.body.appendChild(confirmOverlay);
    }

    if (document.body) {
        mountConfirm();
    } else {
        document.addEventListener("DOMContentLoaded", mountConfirm);
    }

    const confirmTitleEl = confirmOverlay.querySelector(".wf-confirm-title");
    const confirmMessageEl = confirmOverlay.querySelector(".wf-confirm-message");
    const confirmCancelEl = confirmOverlay.querySelector(".wf-confirm-cancel");
    const confirmOkEl = confirmOverlay.querySelector(".wf-confirm-ok");

    let confirmResolver = null;

    function closeConfirm(result) {
        confirmOverlay.style.display = "none";
        if (confirmResolver) {
            confirmResolver(result);
            confirmResolver = null;
        }
    }

    confirmCancelEl.addEventListener("click", function () { closeConfirm(false); });
    confirmOkEl.addEventListener("click", function () { closeConfirm(true); });

    confirmOverlay.addEventListener("click", function (e) {
        if (e.target === confirmOverlay) closeConfirm(false);
    });

    window.addEventListener("keydown", function (e) {
        if (confirmOverlay.style.display !== "flex") return;

        if (e.key === "Escape") {
            e.preventDefault();
            closeConfirm(false);
        } else if (e.key === "Enter") {
            e.preventDefault();
            closeConfirm(true);
        }
    });

    window.wfConfirm = function (message, title, okLabel) {
        confirmTitleEl.innerText = title || "확인";
        confirmMessageEl.innerText = message || "";
        confirmOkEl.innerText = okLabel || "삭제";
        confirmOverlay.style.display = "flex";
        confirmOkEl.focus();

        return new Promise(function (resolve) {
            confirmResolver = resolve;
        });
    };

    window.updateFilePicker = function (input) {
        const picker = input.closest(".file-picker");

        if (!picker) return;

        const nameEl = picker.querySelector(".file-picker-name");

        if (!nameEl) return;

        if (input.files && input.files.length > 0) {
            nameEl.innerText = input.files[0].name;
            nameEl.classList.add("has-file");
        } else {
            nameEl.innerText = nameEl.dataset.empty || "선택된 파일 없음";
            nameEl.classList.remove("has-file");
        }
    };
})();