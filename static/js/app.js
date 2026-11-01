/**
 * Automated CO-PO and CO-PSO Mapping System
 * Multi-Department & Multi-Course OBE Management System
 */

const state = {
    departments: [],
    currentDeptId: null,
    currentDept: null,
    courses: [],
    currentCourseId: null,
    currentCourse: null,
    pos: [],
    psos: [],
    wks: [],
    peos: [],
    cos: [],
    suggestions: {},
    matrix: {}, // { "CO1": { "PO 1": "3", "PO 2": "2", ... } }
    modalCell: { co: null, col: null },
    catalogVisible: false,
    selectedUploadFile: null
};

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    try {
        showToast("Initializing OBE Curriculum Engine...", "info");
        const res = await fetch("/api/departments");
        const json = await res.json();

        if (json.status !== "success") {
            showToast("Failed to load departments: " + json.message, "danger");
            return;
        }

        state.departments = json.departments || [];
        populateDepartmentSelect();

        // Default to 'aids' or the first department available
        const defaultDept = state.departments.find(d => d.id === "aids") || state.departments[0];
        if (defaultDept) {
            state.currentDeptId = defaultDept.id;
            document.getElementById("department-select").value = defaultDept.id;
            await loadDepartment(defaultDept.id);
        } else {
            showToast("No departments configured. Please add a department.", "warning");
        }
    } catch (err) {
        console.error("Initialization error:", err);
        showToast("Error connecting to backend: " + err.message, "danger");
    }
}

function populateDepartmentSelect() {
    const sel = document.getElementById("department-select");
    if (!sel) return;
    sel.innerHTML = "";

    state.departments.forEach(dept => {
        const opt = document.createElement("option");
        opt.value = dept.id;
        opt.textContent = `${dept.name} (${dept.short_name})`;
        sel.appendChild(opt);
    });
}

async function onDepartmentChange(deptId) {
    if (!deptId || deptId === state.currentDeptId) return;
    state.currentDeptId = deptId;
    await loadDepartment(deptId);
}

async function loadDepartment(deptId, selectCourseId = null) {
    try {
        const res = await fetch(`/api/departments/${deptId}`);
        const json = await res.json();

        if (json.status !== "success") {
            showToast("Failed to load department details: " + json.message, "danger");
            return;
        }

        state.currentDept = json.department;
        state.courses = state.currentDept.courses || [];

        // Update header & catalog labels
        const hdrDept = document.getElementById("header-dept-name");
        if (hdrDept) hdrDept.textContent = `${state.currentDept.name} (${state.currentDept.short_name})`;

        const catalogTitle = document.getElementById("catalog-dept-title");
        if (catalogTitle) catalogTitle.textContent = `${state.currentDept.name} — Courses (${state.courses.length})`;

        const toggleBtnText = document.getElementById("btn-toggle-catalog-text");
        if (toggleBtnText) toggleBtnText.textContent = `Department Courses (${state.courses.length})`;

        // Populate course dropdown
        populateCourseSelect();

        // Render catalog cards
        renderCourseCatalog();

        // Select course
        if (state.courses.length > 0) {
            let targetCourseId = selectCourseId;
            if (!targetCourseId || !state.courses.some(c => c.id === targetCourseId)) {
                targetCourseId = state.courses[0].id;
            }
            document.getElementById("course-select").value = targetCourseId;
            await loadCourse(deptId, targetCourseId);
        } else {
            // No courses in this department yet
            state.currentCourseId = null;
            state.currentCourse = null;
            renderEmptyCourseWorkspace();
            showToast("No courses found in this department. Click '+ Add Course' to create one.", "warning");
        }
    } catch (err) {
        console.error("Load department error:", err);
        showToast("Error loading department: " + err.message, "danger");
    }
}

function populateCourseSelect() {
    const sel = document.getElementById("course-select");
    if (!sel) return;
    sel.innerHTML = "";

    if (state.courses.length === 0) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "No courses available";
        sel.appendChild(opt);
        return;
    }

    state.courses.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = `${c.course_name} (${c.course_code})`;
        sel.appendChild(opt);
    });
}

function renderCourseCatalog() {
    const grid = document.getElementById("course-cards-grid");
    if (!grid) return;
    grid.innerHTML = "";

    if (state.courses.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 32px; color: var(--slate-500);">
                <p style="font-size: 15px; margin-bottom: 12px;">No courses defined yet for this department.</p>
                <button class="btn btn-primary-sm" onclick="openAddCourseModal()">+ Add First Course</button>
            </div>
        `;
        return;
    }

    state.courses.forEach(c => {
        const card = document.createElement("div");
        card.className = `course-card-item ${c.id === state.currentCourseId ? "active" : ""}`;
        card.onclick = () => selectCourseFromCatalog(c.id);

        card.innerHTML = `
            <div class="course-card-top">
                <span class="badge-code">${escapeHtml(c.course_code)}</span>
                <span class="badge-pill" style="background:#e0f2fe; color:#0369a1; font-size:11px;">${escapeHtml(c.class_name || "UG")}</span>
            </div>
            <div class="course-card-title">${escapeHtml(c.course_name)}</div>
            <div class="course-card-meta">
                <span>👤 Coordinator: <strong>${escapeHtml(c.coordinator || "Faculty In-Charge")}</strong></span>
                <span>📅 Sem: ${escapeHtml(c.semester || "Odd")} &bull; AY: ${escapeHtml(c.academic_year || "2026-2027")}</span>
                <span>🎯 Outcomes: <strong>${(c.cos || []).length} Course Outcomes</strong></span>
            </div>
            <button class="course-card-btn" type="button">Open Mapping ➔</button>
        `;
        grid.appendChild(card);
    });
}

function selectCourseFromCatalog(courseId) {
    document.getElementById("course-select").value = courseId;
    loadCourse(state.currentDeptId, courseId);
    // Optionally close catalog to show workspace
    if (state.catalogVisible) {
        toggleCourseCatalog();
    }
}

async function onCourseChange(courseId) {
    if (!courseId || courseId === state.currentCourseId) return;
    await loadCourse(state.currentDeptId, courseId);
}

async function loadCourse(deptId, courseId) {
    try {
        showToast("Loading course mapping and outcomes...", "info");
        const res = await fetch(`/api/departments/${deptId}/courses/${courseId}`);
        const json = await res.json();

        if (json.status !== "success") {
            showToast("Failed to load course: " + json.message, "danger");
            return;
        }

        state.currentCourseId = courseId;
        state.currentCourse = json.course;
        state.pos = json.po_statements || [];
        state.psos = json.pso_statements || [];
        state.wks = json.wk_statements || [];
        state.peos = json.peo_statements || [];
        state.cos = json.course.cos || [];
        state.suggestions = json.suggestions || {};
        state.matrix = json.matrix || {};

        // Update Course Meta Card
        updateCourseMetaBanner();

        // Render Articulation Matrix
        renderMatrixTable();

        // Render Reference Tabs
        renderJustificationsTable();
        renderStatementTabs();

        // Update active class on catalog cards
        renderCourseCatalog();

        showToast(`Loaded: ${state.currentCourse.course_name} (${state.currentCourse.course_code})`, "success");
    } catch (err) {
        console.error("Load course error:", err);
        showToast("Error loading course: " + err.message, "danger");
    }
}

function updateCourseMetaBanner() {
    const c = state.currentCourse;
    if (!c) return;

    const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    setEl("meta-course-name", c.course_name);
    setEl("meta-course-code", c.course_code);
    setEl("meta-class-sem", `${c.class_name || "SY B Tech"} • Sem ${c.semester || "Odd"}`);
    setEl("meta-academic-year", c.academic_year || "2026-2027");
    setEl("meta-coordinator", c.coordinator || "Faculty In-Charge");
    setEl("meta-dept-name", state.currentDept ? state.currentDept.name : "Department");

    const cosSubtitle = document.getElementById("cos-panel-subtitle");
    if (cosSubtitle) cosSubtitle.textContent = `Course: ${c.course_name} (${c.course_code})`;
}

function renderEmptyCourseWorkspace() {
    const tbody = document.getElementById("matrix-tbody");
    if (tbody) {
        tbody.innerHTML = `<tr><td colspan="15" style="text-align:center; padding:32px; color:var(--slate-500);">No courses in this department yet. Click "+ Add Course" above to create a course.</td></tr>`;
    }
}

/**
 * Returns column header keys: ['PO 1', 'PO 2', ... 'PSO 1', 'PSO 2']
 */
function getTargetColumns() {
    const cols = [];
    state.pos.forEach(p => {
        const num = p.code.replace(/\D/g, "");
        cols.push(`PO ${num}`);
    });
    state.psos.forEach(p => {
        const num = p.code.replace(/\D/g, "");
        cols.push(`PSO ${num}`);
    });
    return cols;
}

/**
 * Renders the Articulation Matrix table (thead, tbody, tfoot)
 */
function renderMatrixTable() {
    const thead = document.getElementById("matrix-thead");
    const tbody = document.getElementById("matrix-tbody");
    if (!thead || !tbody) return;

    thead.innerHTML = "";
    tbody.innerHTML = "";

    const allCols = getTargetColumns();

    // 1. Build THEAD
    const trHead = document.createElement("tr");
    trHead.innerHTML = `
        <th class="th-co">CO #</th>
        <th class="th-statement">Course Outcome Statement & Bloom Level</th>
    `;
    state.pos.forEach(po => {
        const th = document.createElement("th");
        th.className = "th-po";
        th.title = `${po.title || po.code}: ${po.desc || ""}`;
        th.textContent = po.code;
        trHead.appendChild(th);
    });
    state.psos.forEach(pso => {
        const th = document.createElement("th");
        th.className = "th-pso";
        th.title = pso.desc || "";
        th.textContent = pso.code;
        trHead.appendChild(th);
    });
    const thAvg = document.createElement("th");
    thAvg.className = "th-avg";
    thAvg.textContent = "CO Avg";
    trHead.appendChild(thAvg);
    thead.appendChild(trHead);

    // 2. Build TBODY
    state.cos.forEach(co => {
        const coKey = co.num;
        const tr = document.createElement("tr");

        // CO #
        const tdCo = document.createElement("td");
        tdCo.className = "td-co";
        tdCo.textContent = coKey;
        tr.appendChild(tdCo);

        // CO Statement & BL tag
        const tdStmt = document.createElement("td");
        tdStmt.className = "td-statement";
        tdStmt.innerHTML = `
            <div class="stmt-content">${escapeHtml(co.statement)}</div>
            <span class="bl-tag">${escapeHtml(co.bl || "Level 2 (Understand)")}</span>
        `;
        tr.appendChild(tdStmt);

        // Matrix Columns
        allCols.forEach(col => {
            const td = document.createElement("td");
            td.className = "matrix-cell";

            const currentVal = state.matrix[coKey]?.[col] ?? "-";
            const sugg = state.suggestions[coKey]?.[col] || {};

            const wrapper = document.createElement("div");
            wrapper.className = "cell-wrapper";

            const select = document.createElement("select");
            select.className = "matrix-select";
            select.setAttribute("data-val", currentVal);
            select.setAttribute("data-co", coKey);
            select.setAttribute("data-col", col);

            const options = ["-", "1", "2", "3"];
            options.forEach(opt => {
                const optEl = document.createElement("option");
                optEl.value = opt;
                optEl.textContent = opt;
                if (String(currentVal) === opt) {
                    optEl.selected = true;
                }
                select.appendChild(optEl);
            });

            select.addEventListener("change", (e) => {
                handleCellChange(coKey, col, e.target.value);
            });

            const infoBtn = document.createElement("button");
            infoBtn.className = "info-btn";
            infoBtn.type = "button";
            infoBtn.title = "View Justification, Match % & Bloom Breakdown";
            infoBtn.innerHTML = "&#9432;";
            infoBtn.addEventListener("click", () => openModal(coKey, col));

            const ctrlRow = document.createElement("div");
            ctrlRow.className = "cell-control-row";
            ctrlRow.appendChild(select);
            ctrlRow.appendChild(infoBtn);
            wrapper.appendChild(ctrlRow);

            // Match percentage badge and review indicator
            const pctVal = sugg.match_percentage;
            const pctRow = document.createElement("div");
            pctRow.style.display = "flex";
            pctRow.style.alignItems = "center";
            pctRow.style.justifyContent = "center";
            pctRow.style.gap = "2px";

            const pctSpan = document.createElement("span");
            pctSpan.className = "cell-pct";
            pctSpan.textContent = (pctVal !== undefined && pctVal > 0) ? `${pctVal}%` : "-";
            pctSpan.title = "Calculated Semantic & Bloom Competency Match Percentage";
            pctSpan.addEventListener("click", () => openModal(coKey, col));
            pctRow.appendChild(pctSpan);

            if (sugg.is_uncertain) {
                const warnTag = document.createElement("span");
                warnTag.className = "cell-review-flag";
                warnTag.textContent = "⚠️";
                warnTag.title = sugg.review_note || "Borderline match score. Recommended for Teacher Review.";
                pctRow.appendChild(warnTag);
            }

            wrapper.appendChild(pctRow);
            td.appendChild(wrapper);
            tr.appendChild(td);
        });

        // Row Average Column
        const tdRowAvg = document.createElement("td");
        tdRowAvg.className = "row-avg-val";
        tdRowAvg.id = `row-avg-${coKey}`;
        tdRowAvg.textContent = calculateRowAverage(coKey);
        tr.appendChild(tdRowAvg);

        tbody.appendChild(tr);
    });

    // 3. Build TFOOT
    renderFooterAverages();
    updateOverallAverage();
}

function handleCellChange(coKey, col, newValue) {
    if (!state.matrix[coKey]) state.matrix[coKey] = {};
    state.matrix[coKey][col] = newValue;

    const sel = document.querySelector(`select[data-co="${coKey}"][data-col="${col}"]`);
    if (sel) {
        sel.setAttribute("data-val", newValue);
    }

    const rowAvgEl = document.getElementById(`row-avg-${coKey}`);
    if (rowAvgEl) {
        rowAvgEl.textContent = calculateRowAverage(coKey);
    }

    renderFooterAverages();
    updateOverallAverage();
}

function calculateRowAverage(coKey) {
    const rowVals = state.matrix[coKey] || {};
    let sum = 0;
    let count = 0;

    for (let col in rowVals) {
        const v = rowVals[col];
        if (v !== "-" && v !== "0" && v !== 0 && !isNaN(v)) {
            sum += Number(v);
            count++;
        }
    }
    if (count === 0) return "-";
    return (sum / count).toFixed(2);
}

function renderFooterAverages() {
    const tfootRow = document.getElementById("matrix-tfoot");
    if (!tfootRow) return;
    tfootRow.innerHTML = "";

    const tdLabel = document.createElement("td");
    tdLabel.colSpan = 2;
    tdLabel.className = "tfoot-label";
    tdLabel.textContent = "Average (NBA Formula):";
    tfootRow.appendChild(tdLabel);

    const allCols = getTargetColumns();

    allCols.forEach(col => {
        const td = document.createElement("td");
        td.className = "col-avg-val";
        td.textContent = calculateColAverage(col);
        tfootRow.appendChild(td);
    });

    const tdCorner = document.createElement("td");
    tdCorner.className = "col-avg-val";
    tdCorner.textContent = calculateOverallMatrixAverage();
    tfootRow.appendChild(tdCorner);
}

function calculateColAverage(col) {
    let sum = 0;
    let count = 0;

    state.cos.forEach(co => {
        const v = state.matrix[co.num]?.[col];
        if (v !== "-" && v !== "0" && v !== 0 && !isNaN(v)) {
            sum += Number(v);
            count++;
        }
    });

    if (count === 0) return "-";
    return (sum / count).toFixed(2);
}

function calculateOverallMatrixAverage() {
    let sum = 0;
    let count = 0;

    state.cos.forEach(co => {
        const row = state.matrix[co.num] || {};
        for (let col in row) {
            const v = row[col];
            if (v !== "-" && v !== "0" && v !== 0 && !isNaN(v)) {
                sum += Number(v);
                count++;
            }
        }
    });

    if (count === 0) return "-";
    return (sum / count).toFixed(2);
}

function updateOverallAverage() {
    const badge = document.getElementById("overall-matrix-avg");
    if (badge) {
        badge.textContent = calculateOverallMatrixAverage();
    }
}

/**
 * Re-applies AI suggested values to the matrix
 */
function applySuggestions() {
    if (!state.currentCourse) return;
    state.matrix = {};
    const allCols = getTargetColumns();

    state.cos.forEach(co => {
        const coKey = co.num;
        state.matrix[coKey] = {};
        allCols.forEach(col => {
            const sugg = state.suggestions[coKey]?.[col];
            const val = sugg ? sugg.value : 0;
            state.matrix[coKey][col] = val === 0 ? "-" : String(val);
        });
    });

    renderMatrixTable();
    renderJustificationsTable();
    showToast("Explainable AI Suggestions applied to matrix!", "success");
}

/**
 * Saves teacher's edited matrix to backend persistently
 */
async function saveTeacherMatrix() {
    if (!state.currentDeptId || !state.currentCourseId) {
        showToast("No active course selected to save.", "warning");
        return;
    }

    const btn = document.getElementById("btn-save-matrix");
    const origHtml = btn.innerHTML;
    try {
        btn.disabled = true;
        btn.innerHTML = `<span>⏳</span> Saving...`;

        const res = await fetch(`/api/departments/${state.currentDeptId}/courses/${state.currentCourseId}/save`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ matrix: state.matrix })
        });
        const json = await res.json();

        if (json.status !== "success") {
            throw new Error(json.message || "Failed to save matrix");
        }

        showToast("Teacher mapping successfully saved to persistent database!", "success");
    } catch (err) {
        console.error("Save error:", err);
        showToast("Error saving mappings: " + err.message, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = origHtml;
    }
}

function clearMatrix() {
    state.cos.forEach(co => {
        const coKey = co.num;
        for (let col in state.matrix[coKey]) {
            state.matrix[coKey][col] = "-";
        }
    });
    renderMatrixTable();
    showToast("Matrix cleared. All correlations set to '-' (No Mapping).", "warning");
}

/**
 * Exports currently selected course to Excel
 */
async function exportCourseExcel() {
    if (!state.currentDeptId || !state.currentCourseId) {
        showToast("No active course selected to export.", "warning");
        return;
    }

    const btn = document.getElementById("btn-export-excel");
    const originalText = btn.innerHTML;
    try {
        btn.disabled = true;
        btn.innerHTML = `<span class="btn-icon">⏳</span> Generating Excel...`;
        showToast(`Generating Excel export for ${state.currentCourse.course_name}...`, "info");

        const payload = {
            matrix: state.matrix,
            justifications: state.suggestions
        };

        const res = await fetch(`/api/departments/${state.currentDeptId}/courses/${state.currentCourseId}/export`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errJson = await res.json().catch(() => ({}));
            throw new Error(errJson.message || "Export failed on server");
        }

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        const cleanCode = (state.currentCourse.course_code || "Course").replace(/[^a-zA-Z0-9]/g, "_");
        a.download = `CO_PO_Mapping_${cleanCode}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        showToast("Excel workbook downloaded successfully! (4 sheets with NBA matrices & justifications)", "success");
    } catch (err) {
        console.error("Export error:", err);
        showToast("Export failed: " + err.message, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

/**
 * Renders Tab 1: Justifications Table
 */
function renderJustificationsTable() {
    const tbody = document.getElementById("justifications-tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    const allCols = getTargetColumns();

    state.cos.forEach(co => {
        const coKey = co.num;
        allCols.forEach(col => {
            const sugg = state.suggestions[coKey]?.[col] || {};
            const val = state.matrix[coKey]?.[col] ?? sugg.value ?? 0;
            const strVal = (val === 0 || val === "0" || val === "-") ? "-" : String(val);
            const strength = strVal === "-" ? "No Mapping" : (strVal === "1" ? "Low" : (strVal === "2" ? "Moderate" : "High"));
            const reason = sugg.reason || "Correlation aligned with syllabus course outcomes.";
            const matchPct = sugg.match_percentage !== undefined ? `${sugg.match_percentage}%` : "-";
            const topic = sugg.co_topic || "Curriculum Outcome";
            const isUnc = sugg.is_uncertain;
            const reviewStatus = isUnc ? `<span class="badge-mini-review">⚠️ Review Suggested</span>` : `<span style="color:#16a34a; font-weight:600; font-size:12px;">✓ Verified</span>`;

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${coKey}</strong></td>
                <td><span class="badge-code">${col}</span></td>
                <td><span class="matrix-select" data-val="${strVal}" style="display:inline-block; line-height:28px; width:34px; height:28px; text-align:center;">${strVal}</span></td>
                <td><strong style="color:var(--primary); font-family:var(--font-heading);">${matchPct}</strong></td>
                <td><span class="badge-pill ${strength.toLowerCase().replace(/\s+/g, '-')}">${strength}</span></td>
                <td><strong>${escapeHtml(topic)}</strong></td>
                <td>${escapeHtml(reason)}</td>
                <td>${reviewStatus}</td>
            `;
            tbody.appendChild(tr);
        });
    });
}

/**
 * Renders statement tabs (COs, POs, PSOs, WKs, PEOs)
 */
function renderStatementTabs() {
    // COs
    const cosContainer = document.getElementById("cos-cards-container");
    if (cosContainer) {
        cosContainer.innerHTML = "";
        state.cos.forEach(co => {
            const card = document.createElement("div");
            card.className = "info-card";
            card.innerHTML = `
                <div class="info-card-top">
                    <span class="badge-pill co-pill">${co.num}</span>
                    <span class="badge-pill bl-pill">${co.bl || "Level 2 (Understand)"}</span>
                    <span class="code-sub">Code: ${co.code || ""}</span>
                </div>
                <p class="statement-body">${escapeHtml(co.statement)}</p>
            `;
            cosContainer.appendChild(card);
        });
    }

    // POs
    const posContainer = document.getElementById("pos-cards-container");
    if (posContainer) {
        posContainer.innerHTML = "";
        state.pos.forEach(po => {
            const card = document.createElement("div");
            card.className = "info-card";
            card.innerHTML = `
                <div class="info-card-top">
                    <span class="badge-pill po-pill">${po.code}</span>
                    <span class="card-title-text">${escapeHtml(po.title || po.code)}</span>
                </div>
                <p class="statement-body">${escapeHtml(po.desc || "")}</p>
            `;
            posContainer.appendChild(card);
        });
    }

    // PSOs
    const psosContainer = document.getElementById("psos-cards-container");
    if (psosContainer) {
        psosContainer.innerHTML = "";
        state.psos.forEach(pso => {
            const card = document.createElement("div");
            card.className = "info-card pso-card";
            card.innerHTML = `
                <div class="info-card-top">
                    <span class="badge-pill pso-pill">${pso.code}</span>
                </div>
                <p class="statement-body">${escapeHtml(pso.desc || "")}</p>
            `;
            psosContainer.appendChild(card);
        });
    }

    // WKs
    const wksContainer = document.getElementById("wks-cards-container");
    if (wksContainer) {
        wksContainer.innerHTML = "";
        state.wks.forEach(wk => {
            const card = document.createElement("div");
            card.className = "info-card";
            card.innerHTML = `
                <div class="info-card-top">
                    <span class="badge-pill wk-pill">${wk.code}</span>
                </div>
                <p class="statement-body">${escapeHtml(wk.desc || "")}</p>
            `;
            wksContainer.appendChild(card);
        });
    }

    // PEOs
    const peosContainer = document.getElementById("peos-cards-container");
    if (peosContainer) {
        peosContainer.innerHTML = "";
        state.peos.forEach(peo => {
            const card = document.createElement("div");
            card.className = "info-card";
            card.innerHTML = `
                <div class="info-card-top">
                    <span class="badge-pill peo-pill">${peo.code}</span>
                </div>
                <p class="statement-body">${escapeHtml(peo.desc || "")}</p>
            `;
            peosContainer.appendChild(card);
        });
    }
}

/**
 * MODAL HANDLERS
 */
function openModal(coKey, colKey) {
    state.modalCell = { co: coKey, col: colKey };

    const coObj = state.cos.find(c => c.num === coKey) || { statement: "", bl: "" };
    const sugg = state.suggestions[coKey]?.[colKey] || {};
    const currentVal = state.matrix[coKey]?.[colKey] || "-";

    document.getElementById("modal-co-po-title").textContent = `${coKey} ➔ ${colKey} Mapping & Evaluation Details`;
    document.getElementById("modal-subtitle").textContent = `Course: ${state.currentCourse?.course_name || ""} (${state.currentCourse?.course_code || ""})`;

    document.getElementById("modal-co-desc").innerHTML = `
        <strong>[${escapeHtml(coObj.bl || "BL")}]</strong> ${escapeHtml(coObj.statement)}
        <div style="margin-top:4px; font-size:12px; color:var(--primary); font-weight:600;">Main Skill / Focus: ${escapeHtml(sugg.co_topic || "Course Concept")}</div>
    `;

    let targetText = colKey;
    if (colKey.startsWith("PO")) {
        const num = colKey.replace(/\D/g, "");
        const poObj = state.pos.find(p => p.code.includes(num));
        if (poObj) targetText = `<strong>${poObj.title}:</strong> ${poObj.desc}`;
    } else if (colKey.startsWith("PSO")) {
        const num = colKey.replace(/\D/g, "");
        const psoObj = state.psos.find(p => p.code.includes(num));
        if (psoObj) targetText = psoObj.desc;
    }
    document.getElementById("modal-target-desc").innerHTML = targetText;

    const pct = sugg.match_percentage !== undefined ? sugg.match_percentage : 0.0;
    const pctBadge = document.getElementById("modal-pct-badge");
    if (pctBadge) pctBadge.textContent = `${pct}% Match`;

    const reviewTag = document.getElementById("modal-review-tag");
    if (reviewTag) {
        reviewTag.style.display = sugg.is_uncertain ? "inline-block" : "none";
    }

    const ruleEl = document.getElementById("modal-threshold-rule");
    if (ruleEl) {
        if (pct > 80.0) {
            ruleEl.innerHTML = `Calculated Match: <strong>${pct}%</strong> &bull; Rule: <strong>&gt; 80.0%</strong> &rarr; <strong>High Correlation (3)</strong>`;
            ruleEl.style.borderLeftColor = "var(--success)";
        } else if (pct >= 50.0) {
            ruleEl.innerHTML = `Calculated Match: <strong>${pct}%</strong> &bull; Rule: <strong>50.0%–80.0%</strong> &rarr; <strong>Moderate Correlation (2)</strong>`;
            ruleEl.style.borderLeftColor = "var(--secondary)";
        } else if (pct > 0.0) {
            ruleEl.innerHTML = `Calculated Match: <strong>${pct}%</strong> &bull; Rule: <strong>&lt; 50.0%</strong> &rarr; <strong>Low Correlation (1)</strong>`;
            ruleEl.style.borderLeftColor = "var(--warning)";
        } else {
            ruleEl.innerHTML = `No Meaningful Relationship: <strong>0.0%</strong> &bull; Rule: <strong>Dash (-)</strong>`;
            ruleEl.style.borderLeftColor = "var(--slate-400)";
        }
    }

    const fb = sugg.factor_breakdown || {};
    const setVal = (id, v) => {
        const el = document.getElementById(id);
        if (el) el.textContent = `${v ?? 0}%`;
    };
    setVal("modal-f-domain", fb.domain_relevance);
    setVal("modal-f-verb", fb.verb_alignment);
    setVal("modal-f-phrase", fb.phrase_match);
    setVal("modal-f-semantic", fb.semantic_similarity);

    document.getElementById("modal-rationale-desc").innerHTML = `
        <div>${escapeHtml(sugg.reason || "Explainable correlation calculated from curricular and cognitive alignment.")}</div>
        <div style="margin-top:6px; font-size:12px; color:#15803d;"><strong>Matching Elements:</strong> ${escapeHtml(sugg.matching_elements || "Alignment confirmed")}</div>
    `;

    updateModalScoreBadge(currentVal);
    const select = document.getElementById("modal-quick-select");
    if (select) select.value = currentVal;

    document.getElementById("modal-backdrop").classList.add("active");
}

function updateModalScoreBadge(val) {
    const badge = document.getElementById("modal-score-badge");
    if (!badge) return;
    if (val === "3") {
        badge.textContent = "High Correlation (3)";
        badge.style.background = "var(--success-bg)";
        badge.style.color = "#065f46";
    } else if (val === "2") {
        badge.textContent = "Moderate Correlation (2)";
        badge.style.background = "var(--info-bg)";
        badge.style.color = "#1e40af";
    } else if (val === "1") {
        badge.textContent = "Low Correlation (1)";
        badge.style.background = "var(--warning-bg)";
        badge.style.color = "#92400e";
    } else {
        badge.textContent = "No Correlation (-)";
        badge.style.background = "var(--slate-100)";
        badge.style.color = "var(--slate-500)";
    }
}

function modalQuickChange(newVal) {
    const { co, col } = state.modalCell;
    if (co && col) {
        handleCellChange(co, col, newVal);
        updateModalScoreBadge(newVal);
    }
}

function closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.remove("active");
}

function closeModalOnBackdrop(e, modalId) {
    if (e.target === e.currentTarget) {
        closeModal(modalId);
    }
}

/* ================= ADD NEW COURSE MODAL LOGIC ================= */
function openAddCourseModal() {
    const sub = document.getElementById("modal-add-course-subtitle");
    if (sub && state.currentDept) {
        sub.textContent = `Adding course to ${state.currentDept.name} (${state.currentDept.short_name})`;
    }

    const coContainer = document.getElementById("co-rows-container");
    if (coContainer && coContainer.children.length === 0) {
        coContainer.innerHTML = "";
        addCoRow("CO1", "", "", "Level 2 (Understand)");
        addCoRow("CO2", "", "", "Level 3 (Apply)");
        addCoRow("CO3", "", "", "Level 3 (Apply)");
        addCoRow("CO4", "", "", "Level 4 (Analyze)");
    }

    document.getElementById("modal-add-course").classList.add("active");
}

function switchAddCourseTab(tab) {
    const pManual = document.getElementById("add-course-panel-manual");
    const pUpload = document.getElementById("add-course-panel-upload");
    const btnM = document.getElementById("btn-tab-manual-course");
    const btnU = document.getElementById("btn-tab-upload-course");

    if (tab === "manual") {
        pManual.style.display = "block";
        pUpload.style.display = "none";
        btnM.classList.add("active");
        btnU.classList.remove("active");
    } else {
        pManual.style.display = "none";
        pUpload.style.display = "block";
        btnM.classList.remove("active");
        btnU.classList.add("active");
    }
}

function addCoRow(defaultNum = "", defaultCode = "", defaultStmt = "", defaultBl = "Level 2 (Understand)") {
    const container = document.getElementById("co-rows-container");
    if (!container) return;

    const count = container.children.length + 1;
    const coNum = defaultNum || `CO${count}`;

    const row = document.createElement("div");
    row.className = "co-row-item";
    row.innerHTML = `
        <span class="co-row-num">${coNum}</span>
        <div class="co-row-inputs">
            <div class="co-row-top">
                <input type="text" class="form-input co-input-code" placeholder="Code (e.g. 2ADPC301_${count})" value="${escapeHtml(defaultCode)}">
                <select class="form-select co-input-bl">
                    <option value="Level 1 (Remember)" ${defaultBl.includes("1") ? "selected" : ""}>Level 1 (Remember)</option>
                    <option value="Level 2 (Understand)" ${defaultBl.includes("2") ? "selected" : ""}>Level 2 (Understand)</option>
                    <option value="Level 3 (Apply)" ${defaultBl.includes("3") ? "selected" : ""}>Level 3 (Apply)</option>
                    <option value="Level 4 (Analyze)" ${defaultBl.includes("4") ? "selected" : ""}>Level 4 (Analyze)</option>
                    <option value="Level 5 (Evaluate)" ${defaultBl.includes("5") ? "selected" : ""}>Level 5 (Evaluate)</option>
                    <option value="Level 6 (Create)" ${defaultBl.includes("6") ? "selected" : ""}>Level 6 (Create)</option>
                </select>
            </div>
            <textarea class="form-textarea co-input-stmt" rows="2" placeholder="Course Outcome Statement..." required>${escapeHtml(defaultStmt)}</textarea>
        </div>
        <button type="button" class="btn-del-co" onclick="removeCoRow(this)" title="Remove CO">&times;</button>
    `;
    container.appendChild(row);
}

function removeCoRow(btn) {
    const row = btn.closest(".co-row-item");
    if (row) {
        row.remove();
        // renumber
        const container = document.getElementById("co-rows-container");
        Array.from(container.children).forEach((r, idx) => {
            const numEl = r.querySelector(".co-row-num");
            if (numEl) numEl.textContent = `CO${idx + 1}`;
        });
    }
}

async function submitAddCourse(e) {
    e.preventDefault();
    if (!state.currentDeptId) {
        showToast("No active department selected.", "danger");
        return;
    }

    const name = document.getElementById("input-course-name").value.trim();
    const code = document.getElementById("input-course-code").value.trim();
    const coord = document.getElementById("input-coordinator").value.trim();
    const cls = document.getElementById("input-class-name").value.trim();
    const sem = document.getElementById("input-semester").value;

    const coRows = document.querySelectorAll("#co-rows-container .co-row-item");
    const cos = [];
    coRows.forEach((r, idx) => {
        const stmt = r.querySelector(".co-input-stmt").value.trim();
        const bl = r.querySelector(".co-input-bl").value;
        const cCode = r.querySelector(".co-input-code").value.trim() || `${code.replace(/\s+/g, '')}_${idx + 1}`;
        if (stmt) {
            cos.push({
                num: `CO${idx + 1}`,
                code: cCode,
                statement: stmt,
                bl: bl
            });
        }
    });

    if (cos.length === 0) {
        showToast("Please enter at least one Course Outcome (CO) statement.", "warning");
        return;
    }

    const payload = {
        course_name: name,
        course_code: code,
        coordinator: coord,
        class_name: cls,
        semester: sem,
        cos: cos
    };

    const btn = document.getElementById("btn-submit-course");
    btn.disabled = true;
    btn.textContent = "Saving...";

    try {
        const res = await fetch(`/api/departments/${state.currentDeptId}/courses`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const json = await res.json();

        if (json.status !== "success") {
            throw new Error(json.message || "Failed to add course");
        }

        showToast(`Course "${name}" created successfully!`, "success");
        closeModal("modal-add-course");

        // Reload department and select the new course
        await loadDepartment(state.currentDeptId, json.course.id);
    } catch (err) {
        console.error("Add course error:", err);
        showToast("Error adding course: " + err.message, "danger");
    } finally {
        btn.disabled = false;
        btn.textContent = "Save Course & Generate Mapping";
    }
}

async function handleExcelFileSelected(e) {
    const file = e.target.files[0];
    if (!file) return;

    state.selectedUploadFile = file;
    document.getElementById("file-chosen-name").textContent = `Selected: ${file.name} (${Math.round(file.size / 1024)} KB)`;

    // Preview
    try {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch("/api/parse-course-excel", {
            method: "POST",
            body: formData
        });
        const json = await res.json();

        if (json.status === "success") {
            const d = json.data;
            const previewCard = document.getElementById("upload-preview-card");
            const previewBox = document.getElementById("upload-preview-details");
            previewCard.style.display = "block";
            previewBox.innerHTML = `
                <div><strong>Course Name:</strong> ${escapeHtml(d.course_name || "Detected from filename")}</div>
                <div><strong>Course Code:</strong> ${escapeHtml(d.course_code || "Auto-assigned")}</div>
                <div><strong>Coordinator:</strong> ${escapeHtml(d.coordinator || "Faculty In-Charge")}</div>
                <div><strong>Detected COs:</strong> ${d.cos.length} statements found</div>
            `;
            document.getElementById("btn-confirm-upload").disabled = false;
        } else {
            showToast("Could not preview file: " + json.message, "warning");
        }
    } catch (err) {
        console.error("Preview error:", err);
    }
}

async function submitUploadCourse() {
    if (!state.selectedUploadFile || !state.currentDeptId) return;

    const btn = document.getElementById("btn-confirm-upload");
    btn.disabled = true;
    btn.textContent = "Uploading & Processing...";

    try {
        const formData = new FormData();
        formData.append("file", state.selectedUploadFile);

        const res = await fetch(`/api/departments/${state.currentDeptId}/courses/upload`, {
            method: "POST",
            body: formData
        });
        const json = await res.json();

        if (json.status !== "success") {
            throw new Error(json.message || "Failed to upload course file");
        }

        showToast(`Course "${json.course.course_name}" uploaded and created!`, "success");
        closeModal("modal-add-course");

        await loadDepartment(state.currentDeptId, json.course.id);
    } catch (err) {
        console.error("Upload error:", err);
        showToast("Upload failed: " + err.message, "danger");
    } finally {
        btn.disabled = false;
        btn.textContent = "Upload & Create Course";
    }
}

/* ================= ADD NEW DEPARTMENT MODAL LOGIC ================= */
function openAddDepartmentModal() {
    document.getElementById("modal-add-dept").classList.add("active");
}

async function submitAddDepartment(e) {
    e.preventDefault();

    const name = document.getElementById("input-dept-name").value.trim();
    const shortName = document.getElementById("input-dept-short").value.trim().toUpperCase();
    const prog = document.getElementById("input-dept-program").value.trim();
    const pso1 = document.getElementById("input-dept-pso1").value.trim();
    const pso2 = document.getElementById("input-dept-pso2").value.trim();

    const payload = {
        name: name,
        short_name: shortName,
        program: prog,
        pso_statements: [
            { code: "PSO1", desc: pso1 },
            { code: "PSO2", desc: pso2 }
        ]
    };

    try {
        const res = await fetch("/api/departments", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const json = await res.json();

        if (json.status !== "success") {
            throw new Error(json.message || "Failed to create department");
        }

        showToast(`Department "${name}" created successfully!`, "success");
        closeModal("modal-add-dept");

        // Refresh departments list
        const resDepts = await fetch("/api/departments");
        const jsonDepts = await resDepts.json();
        state.departments = jsonDepts.departments || [];
        populateDepartmentSelect();

        // Switch to the newly created department
        state.currentDeptId = json.department.id;
        document.getElementById("department-select").value = json.department.id;
        await loadDepartment(json.department.id);
    } catch (err) {
        console.error("Create department error:", err);
        showToast("Error creating department: " + err.message, "danger");
    }
}

/* ================= VIEW TOGGLE & TABS ================= */
function toggleCourseCatalog() {
    const sec = document.getElementById("catalog-section");
    if (!sec) return;
    state.catalogVisible = !state.catalogVisible;
    sec.style.display = state.catalogVisible ? "block" : "none";
}

function switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));

    const targetPanel = document.getElementById(tabId);
    if (targetPanel) {
        targetPanel.classList.add("active");
    }

    const clickedBtn = Array.from(document.querySelectorAll(".tab-btn")).find(b => b.getAttribute("onclick")?.includes(tabId));
    if (clickedBtn) {
        clickedBtn.classList.add("active");
    }
}

function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    let icon = "ℹ️";
    if (type === "success") icon = "✅";
    if (type === "warning") icon = "⚠️";
    if (type === "danger") icon = "❌";

    toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(10px)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
