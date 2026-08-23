/**
 * script.js - Frontend Controller for E-Commerce AI Data Assistant
 * 
 * Handles:
 * - Natural language chat interactions and API communication (POST /ask)
 * - Dynamic markdown formatting, SQL accordion rendering, and data table generation
 * - Quick question chip handlers and starter suggestions
 * - Database schema explorer modal and live status polling
 * - Mobile responsive drawer controls and toast alerts
 */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const chatViewport = document.getElementById("chatViewport");
    const chatContainer = document.getElementById("chatContainer");
    const welcomeScreen = document.getElementById("welcomeScreen");
    const messagesStream = document.getElementById("messagesStream");
    const promptInput = document.getElementById("promptInput");
    const sendBtn = document.getElementById("sendBtn");
    const newChatBtn = document.getElementById("newChatBtn");
    const clearChatNavBtn = document.getElementById("clearChatNavBtn");
    const sidebar = document.getElementById("sidebar");
    const mobileMenuBtn = document.getElementById("mobileMenuBtn");
    const mobileCloseBtn = document.getElementById("mobileCloseBtn");
    const schemaModal = document.getElementById("schemaModal");
    const openSchemaBtn = document.getElementById("openSchemaBtn");
    const viewSchemaNavBtn = document.getElementById("viewSchemaNavBtn");
    const closeSchemaModalBtn = document.getElementById("closeSchemaModalBtn");
    const schemaModalBody = document.getElementById("schemaModalBody");
    const toastContainer = document.getElementById("toastContainer");

    // Initialize Lucide icons
    if (window.lucide) {
        window.lucide.createIcons();
    }

    // Auto-resize input textarea
    promptInput.addEventListener("input", () => {
        promptInput.style.height = "auto";
        promptInput.style.height = Math.min(promptInput.scrollHeight, 120) + "px";
    });

    // Handle Enter key for submission (Shift+Enter for new line)
    promptInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submitUserQuestion();
        }
    });

    // Send Button click
    sendBtn.addEventListener("click", () => {
        submitUserQuestion();
    });

    // Mobile Sidebar Toggles
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener("click", () => {
            sidebar.classList.add("open");
        });
    }

    if (mobileCloseBtn) {
        mobileCloseBtn.addEventListener("click", () => {
            sidebar.classList.remove("open");
        });
    }

    // New Analysis / Clear Chat
    if (newChatBtn) {
        newChatBtn.addEventListener("click", resetAnalysisView);
    }
    if (clearChatNavBtn) {
        clearChatNavBtn.addEventListener("click", resetAnalysisView);
    }

    function resetAnalysisView() {
        messagesStream.innerHTML = "";
        welcomeScreen.style.display = "flex";
        promptInput.value = "";
        promptInput.style.height = "auto";
        promptInput.focus();
        showToast("Started new analysis session", "success");
    }

    // Quick Question Chips & Starter Prompts Click Handlers
    document.addEventListener("click", (e) => {
        const chip = e.target.closest(".query-chip") || e.target.closest(".starter-chip");
        if (chip && chip.dataset.question) {
            const question = chip.dataset.question;
            promptInput.value = question;
            promptInput.focus();
            if (sidebar.classList.contains("open")) {
                sidebar.classList.remove("open");
            }
            submitUserQuestion();
        }
    });

    // Schema Explorer Modal Controls
    if (openSchemaBtn) openSchemaBtn.addEventListener("click", openSchemaExplorer);
    if (viewSchemaNavBtn) viewSchemaNavBtn.addEventListener("click", openSchemaExplorer);
    if (closeSchemaModalBtn) closeSchemaModalBtn.addEventListener("click", closeSchemaExplorer);

    schemaModal.addEventListener("click", (e) => {
        if (e.target === schemaModal) {
            closeSchemaExplorer();
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && schemaModal.classList.contains("active")) {
            closeSchemaExplorer();
        }
    });

    async function openSchemaExplorer() {
        schemaModal.classList.add("active");
        schemaModalBody.innerHTML = `
            <div class="schema-loading" style="text-align: center; padding: 40px; color: var(--text-muted);">
                <i data-lucide="loader" class="spin"></i> Loading schema columns...
            </div>
        `;
        if (window.lucide) window.lucide.createIcons();

        try {
            const response = await fetch("/api/schema");
            const data = await response.json();
            renderSchemaDetails(data);
        } catch (err) {
            schemaModalBody.innerHTML = `<p style="color: var(--accent-rose); padding: 20px;">Failed to load database schema: ${err.message}</p>`;
        }
    }

    function closeSchemaExplorer() {
        schemaModal.classList.remove("active");
    }

    function renderSchemaDetails(schemaData) {
        if (!schemaData || !schemaData.columns || schemaData.columns.length === 0) {
            schemaModalBody.innerHTML = `<p style="padding: 20px; color: var(--text-muted);">No schema details available.</p>`;
            return;
        }

        const columns = schemaData.columns;
        const totalRows = schemaData.row_count || 0;
        const engine = schemaData.engine || "Database";

        let html = `
            <div style="margin-bottom: 16px; font-size: 0.86rem; color: var(--text-secondary); display: flex; justify-content: space-between;">
                <span>Active Table: <strong style="color: var(--accent-cyan);">orders</strong> (${columns.length} columns)</span>
                <span>Total Records: <strong style="color: var(--accent-emerald);">${totalRows.toLocaleString()} rows</strong></span>
            </div>
            <div class="schema-columns-grid">
        `;

        columns.forEach(col => {
            const samples = col.sample_values && col.sample_values.length > 0
                ? col.sample_values.join(", ")
                : "None";

            html += `
                <div class="schema-column-card">
                    <div class="schema-col-top">
                        <span class="schema-col-name">${escapeHtml(col.name)}</span>
                        <span class="schema-col-type">${escapeHtml(col.type)}</span>
                    </div>
                    <div class="schema-col-samples" title="Sample values: ${escapeHtml(samples)}">
                        Sample: ${escapeHtml(samples)}
                    </div>
                </div>
            `;
        });

        html += `</div>`;
        schemaModalBody.innerHTML = html;
        if (window.lucide) window.lucide.createIcons();
    }

    // ===================================================================
    // CHAT & QUERY EXECUTION ENGINE
    // ===================================================================

    async function submitUserQuestion() {
        const question = promptInput.value.trim();
        if (!question) return;

        // Hide welcome screen
        welcomeScreen.style.display = "none";

        // Append User Message
        appendUserMessage(question);

        // Clear input
        promptInput.value = "";
        promptInput.style.height = "auto";
        sendBtn.disabled = true;

        // Append Loading Skeleton
        const loadingId = appendLoadingSkeleton();
        scrollToBottom();

        try {
            const response = await fetch("/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: question })
            });

            const data = await response.json();

            // Remove loading skeleton
            removeElement(loadingId);

            // Render AI Response Card
            appendAIResponse(data);

        } catch (error) {
            removeElement(loadingId);
            appendAIResponse({
                status: "error",
                answer: `⚠️ Connection Error: Failed to communicate with the server. (${error.message})`,
                sql: "",
                data: [],
                columns: [],
                rowCount: 0,
                executionTimeMs: 0
            });
        } finally {
            sendBtn.disabled = false;
            scrollToBottom();
            promptInput.focus();
        }
    }

    function appendUserMessage(text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message-wrapper user-message";
        msgDiv.innerHTML = `
            <div class="user-bubble">
                <span>${escapeHtml(text)}</span>
                <div class="user-icon">
                    <i data-lucide="user"></i>
                </div>
            </div>
        `;
        messagesStream.appendChild(msgDiv);
        if (window.lucide) window.lucide.createIcons();
    }

    function appendLoadingSkeleton() {
        const id = "loading-" + Date.now();
        const skeletonDiv = document.createElement("div");
        skeletonDiv.id = id;
        skeletonDiv.className = "message-wrapper ai-message";
        skeletonDiv.innerHTML = `
            <div class="loading-card">
                <div class="ai-avatar">
                    <i data-lucide="sparkles"></i>
                </div>
                <div class="loading-dots">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
                <span class="loading-text">Analyzing database schema & generating SQL query...</span>
            </div>
        `;
        messagesStream.appendChild(skeletonDiv);
        if (window.lucide) window.lucide.createIcons();
        return id;
    }

    function appendAIResponse(payload) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message-wrapper ai-message";

        const isSuccess = payload.status === "success";
        const answerFormatted = formatMarkdown(payload.answer || "No response received.");
        const sql = payload.sql || "";
        const dataRows = payload.data || [];
        const columns = payload.columns || [];
        const rowCount = payload.rowCount !== undefined ? payload.rowCount : dataRows.length;
        const execTime = payload.executionTimeMs || 0;
        const engine = payload.engine || "Database";
        const source = payload.source || "AI Assistant";

        let sqlSection = "";
        if (sql) {
            sqlSection = `
                <div class="sql-accordion" id="sql-acc-${Date.now()}">
                    <div class="sql-header">
                        <div class="sql-title-wrap">
                            <i data-lucide="terminal"></i>
                            <span>Generated SQL Query</span>
                        </div>
                        <div class="sql-controls">
                            <button class="copy-sql-btn" data-sql="${escapeAttribute(sql)}">
                                <i data-lucide="copy"></i>
                                <span>Copy SQL</span>
                            </button>
                            <span class="sql-chevron">
                                <i data-lucide="chevron-down"></i>
                            </span>
                        </div>
                    </div>
                    <pre class="sql-code-block"><code>${escapeHtml(sql)}</code></pre>
                </div>
            `;
        }

        let tableSection = "";
        if (dataRows && dataRows.length > 0 && columns && columns.length > 0) {
            tableSection = renderDataTable(columns, dataRows);
        }

        const cardHtml = `
            <div class="ai-card">
                <div class="ai-header">
                    <div class="ai-brand">
                        <div class="ai-avatar">
                            <i data-lucide="sparkles"></i>
                        </div>
                        <span class="ai-name">Data Analyst AI</span>
                        <span class="ai-source-badge">${escapeHtml(source)}</span>
                    </div>
                    <div class="ai-actions">
                        <button class="icon-btn copy-answer-btn" title="Copy answer">
                            <i data-lucide="copy"></i>
                        </button>
                    </div>
                </div>

                <div class="ai-body">
                    ${answerFormatted}
                </div>

                ${sqlSection}

                ${tableSection}

                <div class="ai-footer">
                    <div class="metric-tags">
                        <span class="metric-tag" title="Execution Time">
                            <i data-lucide="clock"></i> ${execTime} ms
                        </span>
                        <span class="metric-tag" title="Rows Retrieved">
                            <i data-lucide="database"></i> ${rowCount} ${rowCount === 1 ? 'row' : 'rows'}
                        </span>
                    </div>
                    <span class="engine-badge">${escapeHtml(engine)}</span>
                </div>
            </div>
        `;

        msgDiv.innerHTML = cardHtml;
        messagesStream.appendChild(msgDiv);

        if (window.lucide) window.lucide.createIcons();

        // Bind interactive features inside this card
        bindCardEvents(msgDiv, payload.answer || "", sql);

        // Auto-scroll so entire response card is visible above input prompt
        scrollToBottom();
    }

    function renderDataTable(columns, rows) {
        // Limit initial display to 15 rows for clean presentation
        const displayRows = rows.slice(0, 15);
        
        // Find numeric columns for visual progress bars (e.g. sales, revenue, profit, orders)
        let maxMetricValue = 0;
        let metricColumn = null;

        const metricCandidates = ["total_sales", "Total_Sales", "Sales", "Total_Revenue", "total_profit", "Profit", "Net_Amount", "order_count", "total_orders", "orders"];
        for (const cand of metricCandidates) {
            if (columns.includes(cand)) {
                metricColumn = cand;
                break;
            }
        }

        if (metricColumn) {
            displayRows.forEach(r => {
                const val = parseFloat(r[metricColumn]) || 0;
                if (val > maxMetricValue) maxMetricValue = val;
            });
        }

        let tableHtml = `
            <div class="data-table-container">
                <table class="analytics-table">
                    <thead>
                        <tr>
                            <th style="width: 50px; text-align: center;">#</th>
                            ${columns.map(c => `<th>${escapeHtml(formatColumnHeader(c))}</th>`).join("")}
                        </tr>
                    </thead>
                    <tbody>
                        ${displayRows.map((row, idx) => {
                            const rank = idx + 1;
                            let rankBadgeClass = "rank-other";
                            let rankIcon = rank;
                            if (rank === 1) { rankBadgeClass = "rank-1"; rankIcon = "🥇 1"; }
                            else if (rank === 2) { rankBadgeClass = "rank-2"; rankIcon = "🥈 2"; }
                            else if (rank === 3) { rankBadgeClass = "rank-3"; rankIcon = "🥉 3"; }
                            else if (rank === 4) { rankBadgeClass = "rank-4"; rankIcon = "4"; }
                            else if (rank === 5) { rankBadgeClass = "rank-5"; rankIcon = "5"; }

                            return `
                                <tr>
                                    <td style="text-align: center;">
                                        <span class="rank-badge ${rankBadgeClass}" style="width: 26px; height: 26px; font-size: 0.76rem; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%;">
                                            ${rankIcon}
                                        </span>
                                    </td>
                                    ${columns.map(c => {
                                        let val = row[c];
                                        let cellContent = "";

                                        if (val === null || val === undefined) {
                                            cellContent = `<span style="color: var(--text-muted);">-</span>`;
                                        } else if (c.toLowerCase() === "category") {
                                            const catClass = getCategoryClass(String(val));
                                            cellContent = `<span class="category-pill ${catClass}">${escapeHtml(String(val))}</span>`;
                                        } else if (c === metricColumn && maxMetricValue > 0) {
                                            const numVal = parseFloat(val) || 0;
                                            const pct = Math.min(Math.round((numVal / maxMetricValue) * 100), 100);
                                            const formattedNum = formatMetricValue(c, numVal);
                                            cellContent = `
                                                <div class="table-bar-cell">
                                                    <span style="font-weight: 700; color: var(--accent-emerald-light); font-family: var(--font-mono); min-width: 80px;">${formattedNum}</span>
                                                    <div class="progress-track">
                                                        <div class="progress-fill" style="width: ${pct}%;"></div>
                                                    </div>
                                                </div>
                                            `;
                                        } else if (typeof val === "number" && !Number.isInteger(val)) {
                                            cellContent = `<span style="font-family: var(--font-mono); font-weight: 600;">₹${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>`;
                                        } else if (typeof val === "number") {
                                            cellContent = `<span style="font-family: var(--font-mono); font-weight: 600;">${val.toLocaleString()}</span>`;
                                        } else {
                                            cellContent = `<span style="font-weight: 600; color: var(--text-white);">${escapeHtml(String(val))}</span>`;
                                        }

                                        return `<td>${cellContent}</td>`;
                                    }).join("")}
                                </tr>
                            `;
                        }).join("")}
                    </tbody>
                </table>
            </div>
        `;
        return tableHtml;
    }

    function formatColumnHeader(col) {
        return col.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
    }

    function getCategoryClass(catName) {
        const c = catName.toLowerCase().trim();
        if (c.includes("elect")) return "cat-electronics";
        if (c.includes("fash")) return "cat-fashion";
        if (c.includes("furn")) return "cat-furniture";
        if (c.includes("home")) return "cat-home";
        return "cat-electronics";
    }

    function formatMetricValue(colName, num) {
        const colLower = colName.toLowerCase();
        if (colLower.includes("sale") || colLower.includes("revenue") || colLower.includes("profit") || colLower.includes("amount") || colLower.includes("price")) {
            if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
            if (num >= 1000) return `₹${(num / 1000).toFixed(1)}k`;
            return `₹${num.toFixed(2)}`;
        }
        return num.toLocaleString();
    }

    function bindCardEvents(cardElement, rawAnswer, rawSql) {
        // Toggle SQL Accordion
        const accordion = cardElement.querySelector(".sql-accordion");
        if (accordion) {
            const header = accordion.querySelector(".sql-header");
            header.addEventListener("click", (e) => {
                if (e.target.closest(".copy-sql-btn")) return;
                accordion.classList.toggle("collapsed");
            });
        }

        // Copy SQL Button
        const copySqlBtn = cardElement.querySelector(".copy-sql-btn");
        if (copySqlBtn) {
            copySqlBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                copyToClipboard(rawSql, "SQL query copied to clipboard!");
            });
        }

        // Copy Answer Button
        const copyAnswerBtn = cardElement.querySelector(".copy-answer-btn");
        if (copyAnswerBtn) {
            copyAnswerBtn.addEventListener("click", () => {
                const plainText = rawAnswer.replace(/[*#_`]/g, "");
                copyToClipboard(plainText, "Answer copied to clipboard!");
            });
        }
    }

    // ===================================================================
    // UTILITIES & VIBRANT FORMATTING
    // ===================================================================

    function formatMarkdown(text) {
        if (!text) return "";
        let formatted = escapeHtml(text);

        // Headings: ### Title or ## Title
        formatted = formatted.replace(/(?:^|\n)###?\s+(.+)/g, '<h3>$1</h3>');

        // Bold: **text** -> <strong>text</strong>
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

        // Highlight Currency: ₹39.07 Lakh, ₹7.85 Lakh, ₹4,999
        formatted = formatted.replace(/(₹[\d,]+(?:\.\d+)?(?:\s*(?:Lakh|Cr|k|Crore))?)/g, '<span class="money-highlight">$1</span>');

        // Numbered lists: 1. Item
        formatted = formatted.replace(/(?:^|\n)(\d+)\.\s+(.+)/g, "<br><strong style='color: var(--accent-cyan-light);'>$1.</strong> $2");

        // Bullet lists: - Item or * Item or • Item
        formatted = formatted.replace(/(?:^|\n)[-*•]\s+(.+)/g, "<br><span style='color: var(--accent-indigo-light);'>•</span> $1");

        // Paragraph line breaks
        formatted = formatted.replace(/\n\n/g, "<br><br>");
        formatted = formatted.replace(/\n/g, "<br>");

        return formatted;
    }

    function escapeHtml(string) {
        if (!string) return "";
        return String(string)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function escapeAttribute(string) {
        if (!string) return "";
        return String(string)
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function removeElement(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        setTimeout(() => {
            chatViewport.scrollTo({
                top: chatViewport.scrollHeight + 500,
                behavior: "smooth"
            });
        }, 100);
    }

    function copyToClipboard(text, successMsg) {
        if (!navigator.clipboard) {
            fallbackCopyText(text);
            showToast(successMsg, "success");
            return;
        }
        navigator.clipboard.writeText(text).then(() => {
            showToast(successMsg, "success");
        }).catch(() => {
            fallbackCopyText(text);
            showToast(successMsg, "success");
        });
    }

    function fallbackCopyText(text) {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand("copy");
        } catch (err) {}
        document.body.removeChild(textArea);
    }

    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        
        let iconName = "info";
        if (type === "success") iconName = "check-circle";
        if (type === "error") iconName = "alert-triangle";

        toast.innerHTML = `
            <i data-lucide="${iconName}"></i>
            <span>${escapeHtml(message)}</span>
        `;
        toastContainer.appendChild(toast);
        if (window.lucide) window.lucide.createIcons();

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(100%)";
            toast.style.transition = "all 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }
});
