/* =========================================================
   MPLADS SENTINEL - script.js
   Complete working frontend script
   ========================================================= */

"use strict";

/* =========================================================
   1. API CONFIGURATION
   ========================================================= */

const API_PORT = "8000";
const API_PATH = "/api/v1";

function getApiBase() {
    if (
        window.location.port === API_PORT ||
        window.location.port === ""
    ) {
        return API_PATH;
    }

    return `http://127.0.0.1:${API_PORT}${API_PATH}`;
}

const API_BASE = getApiBase();

console.log("MPLADS Sentinel starting...");
console.log("API Base:", API_BASE);


/* =========================================================
   2. GLOBAL STATE
   ========================================================= */

let projectPage = 1;

const PROJECTS_PER_PAGE = 25;

let projectLoading = false;
let anomalyLoading = false;


/* =========================================================
   3. HELPER FUNCTIONS
   ========================================================= */

function $(id) {
    return document.getElementById(id);
}


function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function firstValue(obj, keys, fallback = "") {

    if (!obj || typeof obj !== "object") {
        return fallback;
    }

    for (const key of keys) {

        if (
            obj[key] !== undefined &&
            obj[key] !== null &&
            obj[key] !== ""
        ) {
            return obj[key];
        }
    }

    return fallback;
}


function formatNumber(value) {

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "0";
    }

    return number.toLocaleString("en-IN", {
        maximumFractionDigits: 2
    });
}


function formatCurrency(value) {

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "₹0";
    }

    return "₹" + number.toLocaleString("en-IN", {
        maximumFractionDigits: 2
    });
}


function getArrayFromResponse(data, possibleKeys = []) {

    if (Array.isArray(data)) {
        return data;
    }

    if (!data || typeof data !== "object") {
        return [];
    }

    for (const key of possibleKeys) {

        if (Array.isArray(data[key])) {
            return data[key];
        }
    }

    const commonKeys = [
        "items",
        "data",
        "results",
        "works",
        "projects",
        "anomalies"
    ];

    for (const key of commonKeys) {

        if (Array.isArray(data[key])) {
            return data[key];
        }
    }

    return [];
}


/* =========================================================
   4. API REQUEST
   ========================================================= */

async function apiFetch(endpoint, options = {}) {

    const url = `${API_BASE}${endpoint}`;

    console.log("API REQUEST:", endpoint);

    const response = await fetch(url, {
        ...options,

        headers: {
            "Accept": "application/json",
            ...(options.headers || {})
        }
    });

    console.log(
        "API RESPONSE:",
        response.status,
        response.statusText
    );

    if (!response.ok) {

        let errorText = "";

        try {
            errorText = await response.text();
        } catch (error) {
            errorText = "";
        }

        throw new Error(
            `API ${response.status} ${response.statusText}: ${errorText}`
        );
    }

    return await response.json();
}


/* =========================================================
   5. PAGE NAVIGATION
   ========================================================= */

function showPage(pageName, clickedButton) {

    console.log("Opening page:", pageName);

    /* Hide all pages */

    document.querySelectorAll(".page").forEach(page => {
        page.classList.remove("active-page");
    });


    /* Show requested page */

    const targetPage = $(`${pageName}-page`);

    if (!targetPage) {

        console.error(
            `Page not found: ${pageName}-page`
        );

        return;
    }

    targetPage.classList.add("active-page");


    /* Update sidebar active button */

    document
        .querySelectorAll(".nav-btn, .nav-item")
        .forEach(button => {
            button.classList.remove("active");
        });


    if (clickedButton) {
        clickedButton.classList.add("active");
    }


    /* Page title */

    const title = $("page-title");
    const subtitle = $("page-subtitle");


    /* Dashboard */

    if (pageName === "dashboard") {

        if (title) {
            title.textContent = "Dashboard";
        }

        if (subtitle) {
            subtitle.textContent =
                "MPLADS monitoring and early-warning system";
        }

        loadDashboard();
    }


    /* Projects */

    if (pageName === "projects") {

        if (title) {
            title.textContent = "Projects";
        }

        if (subtitle) {
            subtitle.textContent =
                "Browse and investigate MPLADS projects";
        }

        projectPage = 1;

        loadProjectFilters();
        loadProjects();
    }


    /* Anomalies */

    if (pageName === "anomalies") {

        if (title) {
            title.textContent = "Anomaly Detection";
        }

        if (subtitle) {
            subtitle.textContent =
                "Statistical irregularities requiring verification";
        }

        loadAnomalySummary();
        loadAnomalies();
    }
}


/* =========================================================
   6. DASHBOARD
   ========================================================= */

async function loadDashboard() {

    console.log("Loading dashboard...");

    try {

        const data = await apiFetch("/dashboard");

        console.log("Dashboard data:", data);

        updateDashboardStats(data);

        renderDashboardOverview(data);


        /* Load anomaly information */

        try {

            const anomalyData =
                await apiFetch("/anomalies/summary");

            console.log(
                "Dashboard anomaly summary:",
                anomalyData
            );

            renderAnomalyDashboardOverview(
                anomalyData
            );

        } catch (error) {

            console.error(
                "Dashboard anomaly summary error:",
                error
            );

            const container =
                $("anomaly-overview");

            if (container) {

                container.innerHTML = `
                    <div class="loading">
                        Unable to load anomaly information.
                    </div>
                `;
            }
        }

    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );

        showDashboardError(error);
    }
}


/* =========================================================
   7. DASHBOARD STATISTICS
   ========================================================= */

function updateDashboardStats(data) {

    const totalProjects = firstValue(
        data,
        [
            "total_projects",
            "project_count",
            "total_works",
            "count"
        ],
        0
    );


    const totalAllocation = firstValue(
        data,
        [
            "total_allocation",
            "total_allocation_amount",
            "allocation_total",
            "total_amount"
        ],
        0
    );


    const totalAnomalies = firstValue(
        data,
        [
            "total_anomalies",
            "anomaly_count",
            "anomalies"
        ],
        0
    );


    const detectionTypes = firstValue(
        data,
        [
            "detection_types",
            "anomaly_types",
            "types_count"
        ],
        2
    );


    if ($("total-projects")) {

        $("total-projects").textContent =
            formatNumber(totalProjects);
    }


    if ($("total-allocation")) {

        $("total-allocation").textContent =
            formatCurrency(totalAllocation);
    }


    if ($("total-anomalies")) {

        $("total-anomalies").textContent =
            formatNumber(totalAnomalies);
    }


    if ($("detection-types")) {

        if (Array.isArray(detectionTypes)) {

            $("detection-types").textContent =
                formatNumber(
                    detectionTypes.length
                );

        } else {

            $("detection-types").textContent =
                formatNumber(detectionTypes);
        }
    }
}


/* =========================================================
   8. DATASET OVERVIEW
   ========================================================= */

function renderDashboardOverview(data) {

    const container =
        $("overview-content");

    if (!container) {
        return;
    }


    const totalProjects = firstValue(
        data,
        [
            "total_projects",
            "project_count",
            "total_works",
            "count"
        ],
        0
    );


    const totalAllocation = firstValue(
        data,
        [
            "total_allocation",
            "total_allocation_amount",
            "allocation_total",
            "total_amount"
        ],
        0
    );


    const states = firstValue(
        data,
        [
            "states",
            "state_count",
            "total_states"
        ],
        null
    );


    const categories = firstValue(
        data,
        [
            "categories",
            "category_count",
            "total_categories"
        ],
        null
    );


    let html = "";


    html += `
        <div class="overview-row">
            <span>Total Projects</span>
            <strong>
                ${escapeHtml(
                    formatNumber(totalProjects)
                )}
            </strong>
        </div>
    `;


    html += `
        <div class="overview-row">
            <span>Total Allocation</span>
            <strong>
                ${escapeHtml(
                    formatCurrency(totalAllocation)
                )}
            </strong>
        </div>
    `;


    if (states !== null) {

        const stateCount =
            Array.isArray(states)
                ? states.length
                : states;

        html += `
            <div class="overview-row">
                <span>States</span>
                <strong>
                    ${escapeHtml(
                        formatNumber(stateCount)
                    )}
                </strong>
            </div>
        `;
    }


    if (categories !== null) {

        const categoryCount =
            Array.isArray(categories)
                ? categories.length
                : categories;

        html += `
            <div class="overview-row">
                <span>Categories</span>
                <strong>
                    ${escapeHtml(
                        formatNumber(categoryCount)
                    )}
                </strong>
            </div>
        `;
    }


    container.innerHTML = html;
}


/* =========================================================
   9. DASHBOARD ANOMALY OVERVIEW
   ========================================================= */

function renderAnomalyDashboardOverview(data) {

    const container =
        $("anomaly-overview");

    if (!container) {
        return;
    }


    const total = firstValue(
        data,
        [
            "total_anomalies",
            "total",
            "count"
        ],
        0
    );


    const repeated = firstValue(
        data,
        [
            "repeated_amount_pattern",
            "repeated_patterns",
            "repeated_count"
        ],
        0
    );


    const extreme = firstValue(
        data,
        [
            "extreme_allocation",
            "extreme_allocations",
            "extreme_count"
        ],
        0
    );


    const maxScore = firstValue(
        data,
        [
            "max_pattern_score",
            "maximum_pattern_score",
            "max_score"
        ],
        0
    );


    container.innerHTML = `

        <div class="overview-row">
            <span>Total Anomalies</span>
            <strong>
                ${escapeHtml(
                    formatNumber(total)
                )}
            </strong>
        </div>

        <div class="overview-row">
            <span>Repeated Patterns</span>
            <strong>
                ${escapeHtml(
                    formatNumber(repeated)
                )}
            </strong>
        </div>

        <div class="overview-row">
            <span>Extreme Allocations</span>
            <strong>
                ${escapeHtml(
                    formatNumber(extreme)
                )}
            </strong>
        </div>

        <div class="overview-row">
            <span>Maximum Pattern Score</span>
            <strong>
                ${escapeHtml(
                    formatNumber(maxScore)
                )}
            </strong>
        </div>

    `;
}


/* =========================================================
   10. DASHBOARD ERROR
   ========================================================= */

function showDashboardError(error) {

    const container =
        $("overview-content");

    if (!container) {
        return;
    }


    container.innerHTML = `
        <div style="padding:12px;">
            <strong>
                Unable to load dashboard data.
            </strong>

            <br>

            <small>
                ${escapeHtml(
                    error.message
                )}
            </small>
        </div>
    `;
}


/* =========================================================
   11. PROJECT FILTERS
   ========================================================= */

async function loadProjectFilters() {

    console.log(
        "Loading project filters..."
    );

    try {

        /*
         * Correct endpoint:
         *
         * /api/v1/filters
         *
         * NOT /api/v1/works/filters
         */

        const data =
            await apiFetch("/filters");

        console.log(
            "Project filter data:",
            data
        );


        const states =
            getArrayFromResponse(
                data,
                ["states"]
            );


        const categories =
            getArrayFromResponse(
                data,
                ["categories"]
            );


        const statuses =
            getArrayFromResponse(
                data,
                ["statuses"]
            );


        populateSelect(
            "state-filter",
            states,
            "All States"
        );


        populateSelect(
            "category-filter",
            categories,
            "All Categories"
        );


        populateSelect(
            "status-filter",
            statuses,
            "All Statuses"
        );

    } catch (error) {

        console.error(
            "Project filters error:",
            error
        );
    }
}


/* =========================================================
   12. POPULATE SELECT
   ========================================================= */

function populateSelect(
    id,
    values,
    firstLabel
) {

    const select = $(id);

    if (
        !select ||
        !Array.isArray(values)
    ) {
        return;
    }


    const currentValue =
        select.value;


    const uniqueValues =
        [
            ...new Set(
                values
                    .map(
                        value =>
                            String(
                                value ?? ""
                            ).trim()
                    )
                    .filter(Boolean)
            )
        ]
        .sort(
            (a, b) =>
                a.localeCompare(
                    b
                )
        );


    select.innerHTML =
        `<option value="">
            ${escapeHtml(firstLabel)}
        </option>`;


    uniqueValues.forEach(
        value => {

            const option =
                document.createElement(
                    "option"
                );

            option.value = value;

            option.textContent =
                value;

            select.appendChild(
                option
            );
        }
    );


    if (
        uniqueValues.includes(
            currentValue
        )
    ) {
        select.value =
            currentValue;
    }
}


/* =========================================================
   13. PROJECTS
   ========================================================= */

async function loadProjects() {

    if (projectLoading) {
        return;
    }


    projectLoading = true;


    const table =
        $("projects-table");


    if (table) {

        table.innerHTML = `
            <tr>
                <td
                    colspan="7"
                    class="loading"
                >
                    Loading projects...
                </td>
            </tr>
        `;
    }


    try {

        const search =
            $("project-search")
                ? $("project-search")
                    .value
                    .trim()
                : "";


        const state =
            $("state-filter")
                ? $("state-filter")
                    .value
                : "";


        const category =
            $("category-filter")
                ? $("category-filter")
                    .value
                : "";


        const status =
            $("status-filter")
                ? $("status-filter")
                    .value
                : "";


        const params =
            new URLSearchParams();


        params.set(
            "limit",
            String(
                PROJECTS_PER_PAGE
            )
        );


        params.set(
            "offset",
            String(
                (projectPage - 1) *
                PROJECTS_PER_PAGE
            )
        );


        if (search) {
            params.set(
                "search",
                search
            );
        }


        if (state) {
            params.set(
                "state",
                state
            );
        }


        if (category) {
            params.set(
                "category",
                category
            );
        }


        if (status) {
            params.set(
                "status",
                status
            );
        }


        const data =
            await apiFetch(
                `/works?${params.toString()}`
            );


        console.log(
            "Projects data:",
            data
        );


        const projects =
            getArrayFromResponse(
                data,
                [
                    "works",
                    "projects",
                    "items",
                    "data",
                    "results"
                ]
            );


        renderProjects(
            projects
        );


        updateProjectPagination(
            data,
            projects.length
        );

    } catch (error) {

        console.error(
            "Projects error:",
            error
        );


        if (table) {

            table.innerHTML = `
                <tr>
                    <td
                        colspan="7"
                        style="padding:20px;"
                    >
                        <strong>
                            Unable to load projects.
                        </strong>

                        <br>

                        <small>
                            ${escapeHtml(
                                error.message
                            )}
                        </small>
                    </td>
                </tr>
            `;
        }

    } finally {

        projectLoading = false;
    }
}


/* =========================================================
   14. RENDER PROJECTS
   ========================================================= */

function renderProjects(projects) {

    const table =
        $("projects-table");


    if (!table) {

        console.error(
            "projects-table not found"
        );

        return;
    }


    if (
        !Array.isArray(projects) ||
        projects.length === 0
    ) {

        table.innerHTML = `
            <tr>
                <td
                    colspan="7"
                    style="padding:20px;"
                >
                    No projects found.
                </td>
            </tr>
        `;

        return;
    }


    table.innerHTML =
        projects
            .map(project => {

                const projectId =
                    firstValue(
                        project,
                        [
                            "PROJECT_ID",
                            "project_id",
                            "id",
                            "IDA"
                        ],
                        "-"
                    );


                /*
                 * MP name will be fixed next.
                 */

                const mpName =
                    firstValue(
                        project,
                        [
                            "MP NAME",
                            "MP_NAME",
                            "mp_name",
                            "mp"
                        ],
                        "Unknown"
                    );


                const state =
                    firstValue(
                        project,
                        [
                            "STATE",
                            "state"
                        ],
                        "-"
                    );


                const constituency =
                    firstValue(
                        project,
                        [
                            "CONSTITUENCY",
                            "constituency"
                        ],
                        "-"
                    );


                const category =
                    firstValue(
                        project,
                        [
                            "CATEGORY",
                            "category"
                        ],
                        "-"
                    );


                const amount =
                    firstValue(
                        project,
                        [
                            "ALLOCATION_AMOUNT_NUM",
                            "ALLOCATION AMOUNT",
                            "allocation_amount",
                            "allocation_amount_num",
                            "amount"
                        ],
                        0
                    );


                const status =
                    firstValue(
                        project,
                        [
                            "STATUS",
                            "status"
                        ],
                        "-"
                    );


                return `
                    <tr>

                        <td>
                            ${escapeHtml(
                                projectId
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                mpName
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                state
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                constituency
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                category
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                formatCurrency(
                                    amount
                                )
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                status
                            )}
                        </td>

                    </tr>
                `;
            })
            .join("");
}


/* =========================================================
   15. PROJECT PAGINATION
   ========================================================= */

function updateProjectPagination(
    data,
    count
) {

    const pageLabel =
        $("project-page-number");


    if (pageLabel) {

        pageLabel.textContent =
            `Page ${projectPage}`;
    }


    const buttons =
        document.querySelectorAll(
            ".pagination button"
        );


    if (buttons.length >= 2) {

        buttons[0].disabled =
            projectPage <= 1;


        buttons[1].disabled =
            count <
            PROJECTS_PER_PAGE;
    }
}


function previousProjects() {

    if (projectPage <= 1) {
        return;
    }


    projectPage--;

    loadProjects();
}


function nextProjects() {

    const nextButton =
        document.querySelector(
            ".pagination button:last-child"
        );


    if (
        nextButton &&
        nextButton.disabled
    ) {
        return;
    }


    projectPage++;

    loadProjects();
}


/* =========================================================
   16. ANOMALY SUMMARY
   ========================================================= */

async function loadAnomalySummary() {

    console.log(
        "Loading anomaly summary..."
    );


    try {

        const data =
            await apiFetch(
                "/anomalies/summary"
            );


        console.log(
            "Anomaly summary:",
            data
        );


        const total =
            firstValue(
                data,
                [
                    "total_anomalies",
                    "total",
                    "count"
                ],
                0
            );


        const repeated =
            firstValue(
                data,
                [
                    "repeated_amount_pattern",
                    "repeated_patterns",
                    "repeated_count"
                ],
                0
            );


        const extreme =
            firstValue(
                data,
                [
                    "extreme_allocation",
                    "extreme_allocations",
                    "extreme_count"
                ],
                0
            );


        const maxScore =
            firstValue(
                data,
                [
                    "max_pattern_score",
                    "maximum_pattern_score",
                    "max_score"
                ],
                0
            );


        if ($("anomaly-total")) {

            $("anomaly-total")
                .textContent =
                formatNumber(total);
        }


        if ($("repeated-count")) {

            $("repeated-count")
                .textContent =
                formatNumber(repeated);
        }


        if ($("extreme-count")) {

            $("extreme-count")
                .textContent =
                formatNumber(extreme);
        }


        if ($("max-pattern-score")) {

            $("max-pattern-score")
                .textContent =
                formatNumber(maxScore);
        }

    } catch (error) {

        console.error(
            "Anomaly summary error:",
            error
        );
    }
}


/* =========================================================
   17. ANOMALIES
   ========================================================= */

async function loadAnomalies() {

    if (anomalyLoading) {
        return;
    }


    anomalyLoading = true;


    const table =
        $("anomalies-table");


    if (table) {

        table.innerHTML = `
            <tr>
                <td
                    colspan="6"
                    class="loading"
                >
                    Loading anomalies...
                </td>
            </tr>
        `;
    }


    try {

        const selectedType =
            $("anomaly-type-filter")
                ? $("anomaly-type-filter")
                    .value
                : "";


        const params =
            new URLSearchParams();


        params.set(
            "limit",
            "50"
        );


        params.set(
            "offset",
            "0"
        );


        if (selectedType) {

            params.set(
                "anomaly_type",
                selectedType
            );
        }


        const data =
            await apiFetch(
                `/anomalies?${params.toString()}`
            );


        console.log(
            "Anomalies data:",
            data
        );


        const anomalies =
            getArrayFromResponse(
                data,
                [
                    "anomalies",
                    "items",
                    "data",
                    "results"
                ]
            );


        renderAnomalies(
            anomalies
        );

    } catch (error) {

        console.error(
            "Anomalies error:",
            error
        );


        if (table) {

            table.innerHTML = `
                <tr>
                    <td
                        colspan="6"
                        style="padding:20px;"
                    >
                        <strong>
                            Unable to load anomalies.
                        </strong>

                        <br>

                        <small>
                            ${escapeHtml(
                                error.message
                            )}
                        </small>
                    </td>
                </tr>
            `;
        }

    } finally {

        anomalyLoading = false;
    }
}


/* =========================================================
   18. RENDER ANOMALIES
   ========================================================= */

function renderAnomalies(
    anomalies
) {

    const table =
        $("anomalies-table");


    if (!table) {

        console.error(
            "anomalies-table not found"
        );

        return;
    }


    if (
        !Array.isArray(anomalies) ||
        anomalies.length === 0
    ) {

        table.innerHTML = `
            <tr>
                <td
                    colspan="6"
                    style="padding:20px;"
                >
                    No anomalies found.
                </td>
            </tr>
        `;

        return;
    }


    table.innerHTML =
        anomalies
            .map(anomaly => {

                const projectId =
                    firstValue(
                        anomaly,
                        [
                            "project_id",
                            "PROJECT_ID",
                            "id"
                        ],
                        "-"
                    );


                const mp =
                    firstValue(
                        anomaly,
                        [
                            "mp",
                            "MP NAME",
                            "mp_name",
                            "MP_NAME"
                        ],
                        "Unknown"
                    );


                const type =
                    firstValue(
                        anomaly,
                        [
                            "anomaly_type",
                            "type"
                        ],
                        "-"
                    );


                const severity =
                    firstValue(
                        anomaly,
                        [
                            "severity"
                        ],
                        "-"
                    );


                const patternScore =
                    firstValue(
                        anomaly,
                        [
                            "pattern_score",
                            "score"
                        ],
                        "-"
                    );


                let evidence =
                    firstValue(
                        anomaly,
                        [
                            "message"
                        ],
                        ""
                    );


                /*
                 * Extreme allocation evidence
                 */

                if (!evidence) {

                    if (
                        type ===
                        "extreme_allocation"
                    ) {

                        const ratio =
                            firstValue(
                                anomaly,
                                [
                                    "peer_median_ratio",
                                    "ratio"
                                ],
                                null
                            );


                        const percentile =
                            firstValue(
                                anomaly,
                                [
                                    "percentile"
                                ],
                                null
                            );


                        evidence =
                            `Ratio: ${
                                ratio ?? "-"
                            }x, Percentile: ${
                                percentile ?? "-"
                            }%`;

                    } else {

                        /*
                         * Repeated pattern evidence
                         */

                        const matches =
                            firstValue(
                                anomaly,
                                [
                                    "matching_projects",
                                    "match_count"
                                ],
                                null
                            );


                        const locations =
                            firstValue(
                                anomaly,
                                [
                                    "different_locations",
                                    "location_count"
                                ],
                                null
                            );


                        evidence =
                            `Matching projects: ${
                                matches ?? "-"
                            }, Locations: ${
                                locations ?? "-"
                            }`;
                    }
                }


                return `
                    <tr>

                        <td>
                            ${escapeHtml(
                                projectId
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                mp
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                formatAnomalyType(
                                    type
                                )
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                severity
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                patternScore
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                evidence
                            )}
                        </td>

                    </tr>
                `;
            })
            .join("");
}


/* =========================================================
   19. FORMAT ANOMALY TYPE
   ========================================================= */

function formatAnomalyType(type) {

    if (
        type ===
        "repeated_amount_pattern"
    ) {
        return "Repeated Amount Pattern";
    }


    if (
        type ===
        "extreme_allocation"
    ) {
        return "Extreme Allocation";
    }


    return type || "-";
}


/* =========================================================
   20. REFRESH DATA
   ========================================================= */

async function refreshData() {

    console.log(
        "Refreshing MPLADS data..."
    );


    const button =
        document.querySelector(
            ".refresh-btn"
        );


    if (button) {

        button.disabled = true;

        button.textContent =
            "↻ Refreshing...";
    }


    try {

        /*
         * Ask backend to clear its cached
         * dataset/anomaly results.
         */

        try {

            await apiFetch(
                "/refresh",
                {
                    method: "POST"
                }
            );


            console.log(
                "Backend refresh completed."
            );

        } catch (error) {

            console.warn(
                "Backend refresh failed:",
                error
            );
        }


        /*
         * Reload dashboard
         */

        await loadDashboard();


        /*
         * Reload anomaly summary
         */

        await loadAnomalySummary();


        /*
         * Reload Projects if currently open
         */

        if (
            $("projects-page") &&
            $("projects-page")
                .classList
                .contains(
                    "active-page"
                )
        ) {

            await loadProjects();
        }


        /*
         * Reload Anomalies if currently open
         */

        if (
            $("anomalies-page") &&
            $("anomalies-page")
                .classList
                .contains(
                    "active-page"
                )
        ) {

            await loadAnomalies();
        }

    } catch (error) {

        console.error(
            "Refresh error:",
            error
        );

    } finally {

        if (button) {

            button.disabled = false;

            button.textContent =
                "↻ Refresh Data";
        }
    }
}


/* =========================================================
   21. STARTUP
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        console.log(
            "DOM loaded."
        );


        /*
         * Load dashboard immediately.
         */

        loadDashboard();


        /*
         * Load project filters.
         */

        loadProjectFilters();


        /*
         * Set Dashboard as active.
         */

        const dashboardButton =
            document.querySelector(
                ".nav-btn, .nav-item"
            );


        if (dashboardButton) {

            document
                .querySelectorAll(
                    ".nav-btn, .nav-item"
                )
                .forEach(button => {
                    button.classList.remove(
                        "active"
                    );
                });


            dashboardButton.classList.add(
                "active"
            );
        }
    }
);


/* =========================================================
   22. EXPOSE FUNCTIONS TO HTML
   ========================================================= */

window.showPage =
    showPage;

window.refreshData =
    refreshData;

window.loadProjects =
    loadProjects;

window.previousProjects =
    previousProjects;

window.nextProjects =
    nextProjects;

window.loadAnomalies =
    loadAnomalies;