document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    const mccContainer = document.getElementById("mcc-container");

    async function loadMccs() {
        try {
            const res = await fetch("/api/mcc", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            
            if (res.status === 401) {
                localStorage.removeItem("token");
                window.location.href = "index.html";
                return;
            }

            const mccs = await res.json();
            renderMccs(mccs);
        } catch (e) {
            console.error("Failed to load MCCs:", e);
            mccContainer.innerHTML = '<p style="color:red;">Failed to load data. Please refresh.</p>';
        }
    }

    function renderMccs(mccs) {
        if (!mccs || mccs.length === 0) {
            mccContainer.innerHTML = '<p class="hint">No category limits found for this user.</p>';
            return;
        }

        mccContainer.innerHTML = "";
        mccs.forEach(mcc => {
            const card = document.createElement("div");
            card.className = "mcc-card";
            
            card.innerHTML = `
                <div class="mcc-header">
                    <span class="mcc-title">${mcc.description}</span>
                    <span class="mcc-code">MCC: ${mcc.mcc_code}</span>
                </div>
                <div class="input-group">
                    <label>Limit per Transaction (${mcc.currency || 'USD'})</label>
                    <div class="input-with-btn">
                        <input type="number" id="mcc-input-${mcc.mcc_code}" value="${mcc.limit.toFixed(2)}" step="0.01">
                        <button class="mini-btn save-mcc-btn" data-code="${mcc.mcc_code}">Save</button>
                    </div>
                </div>
            `;
            
            mccContainer.appendChild(card);
        });

        // Add event listeners for new save buttons
        document.querySelectorAll(".save-mcc-btn").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                const code = e.target.getAttribute("data-code");
                const input = document.getElementById(`mcc-input-${code}`);
                const limit = parseFloat(input.value);
                
                if (isNaN(limit) || limit < 0) {
                    alert("Please enter a valid amount.");
                    return;
                }

                const originalText = btn.textContent;
                btn.textContent = "Saving...";
                btn.disabled = true;

                try {
                    const res = await fetch(`/api/mcc/${code}`, {
                        method: "PUT",
                        headers: {
                            "Content-Type": "application/json",
                            "Authorization": `Bearer ${token}`
                        },
                        body: JSON.stringify({ limit })
                    });
                    
                    if (res.ok) {
                        btn.textContent = "Saved";
                        btn.style.background = "var(--success)";
                        setTimeout(() => {
                            btn.textContent = originalText;
                            btn.style.background = "";
                            btn.disabled = false;
                        }, 2000);
                        
                        // Refresh logs on successful save
                        loadMccLogs();
                    } else {
                        const err = await res.json();
                        alert("Error: " + (err.detail || "Update failed"));
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }
                } catch (e) {
                    console.error("Save error:", e);
                    alert("Failed to save limit.");
                    btn.textContent = originalText;
                    btn.disabled = false;
                }
            });
        });
    }

    async function loadMccLogs() {
        try {
            const res = await fetch("/api/mcc/logs", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const logs = await res.json();
                renderMccLogs(logs);
            }
        } catch (e) {
            console.error("Failed to load MCC logs:", e);
        }
    }

    function renderMccLogs(logs) {
        const tbody = document.querySelector("#mcc-logs-table tbody");
        if (!logs || logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color: var(--text-dim);">No limit changes recorded yet.</td></tr>';
            return;
        }

        tbody.innerHTML = "";
        logs.forEach(log => {
            const tr = document.createElement("tr");
            const date = new Date(log.changed_at).toLocaleString();
            tr.innerHTML = `
                <td>${date}</td>
                <td><span class="mcc-code">${log.mcc_code}</span></td>
                <td>${log.old_limit.toFixed(2)} ${log.currency}</td>
                <td style="color: var(--success); font-weight: 600;">${log.new_limit.toFixed(2)} ${log.currency}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Init
    loadMccs();
    loadMccLogs();
});
