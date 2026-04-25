const lookupForm = document.getElementById("lookupForm");
const reportForm = document.getElementById("reportForm");
const apiKeyInput = document.getElementById("apiKeyInput");
const phoneInput = document.getElementById("phoneInput");
const retentionTierInput = document.getElementById("retentionTierInput");
const lookupError = document.getElementById("lookupError");
const riskBadge = document.getElementById("riskBadge");
const resultGrid = document.getElementById("resultGrid");
const sourceSummary = document.getElementById("sourceSummary");
const complianceFlags = document.getElementById("complianceFlags");
const reportStatus = document.getElementById("reportStatus");
const historyBody = document.getElementById("historyBody");
const refreshHistoryBtn = document.getElementById("refreshHistory");

let latestPhone = "";

async function apiRequest(path, options = {}) {
  const apiKey = apiKeyInput?.value?.trim() || "";
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (apiKey) {
    headers["x-api-key"] = apiKey;
    localStorage.setItem("phoneIntelApiKey", apiKey);
  }

  const response = await fetch(path, {
    headers,
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

function makeCard(key, value) {
  return `<article class="kv"><div class="k">${key}</div><div class="v">${value}</div></article>`;
}

function updateRiskBadge(score) {
  riskBadge.classList.remove("safe", "warn", "danger");
  riskBadge.textContent = `Risk: ${score}`;
  if (score < 25) riskBadge.classList.add("safe");
  else if (score < 60) riskBadge.classList.add("warn");
  else riskBadge.classList.add("danger");
}

function renderLookup(data) {
  const cards = [
    makeCard("Phone", data.normalized_phone),
    makeCard("Country", `${data.country.name} (${data.country.code})`),
    makeCard("Line Type", data.line_type_guess),
    makeCard("Spam Reports", data.report_counts.spam),
    makeCard("Scam Reports", data.report_counts.scam),
    makeCard("Safe Reports", data.report_counts.safe),
    makeCard("Lookup ID", data.lookup_id),
    makeCard("Retention Tier", data.compliance_flags?.retention_tier || "standard"),
    makeCard("Time", new Date(data.created_at).toLocaleString()),
  ];

  resultGrid.classList.remove("muted");
  resultGrid.innerHTML = cards.join("");
  updateRiskBadge(data.risk_score);

  sourceSummary.classList.remove("muted");
  complianceFlags.classList.remove("muted");
  sourceSummary.textContent = JSON.stringify(data.source_summary || {}, null, 2);
  complianceFlags.textContent = JSON.stringify(data.compliance_flags || {}, null, 2);
}

function renderHistory(items) {
  if (!items.length) {
    historyBody.innerHTML = `<tr><td colspan="5" class="muted">No records yet.</td></tr>`;
    return;
  }

  historyBody.innerHTML = items
    .map((item) => `
      <tr>
        <td>${new Date(item.created_at).toLocaleString()}</td>
        <td>${item.normalized_phone}</td>
        <td>${item.country_name} (${item.country_code})</td>
        <td>${item.line_type_guess}</td>
        <td>${item.risk_score}</td>
      </tr>
    `)
    .join("");
}

async function loadHistory() {
  const query = latestPhone ? `?phone=${encodeURIComponent(latestPhone)}` : "";
  try {
    const data = await apiRequest(`/api/history${query}`);
    renderHistory(data.items || []);
  } catch (error) {
    historyBody.innerHTML = `<tr><td colspan="5" class="muted">Failed to load history.</td></tr>`;
  }
}

lookupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  lookupError.textContent = "";
  reportStatus.textContent = "";
  const phone = phoneInput.value.trim();
  const retention_tier = retentionTierInput.value;

  try {
    const data = await apiRequest("/api/lookup", {
      method: "POST",
      body: JSON.stringify({ phone, retention_tier }),
    });
    latestPhone = data.normalized_phone;
    renderLookup(data);
    await loadHistory();
  } catch (error) {
    lookupError.textContent = error.message;
  }
});

reportForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  reportStatus.textContent = "";
  const phone = phoneInput.value.trim();
  if (!phone) {
    reportStatus.textContent = "Enter a phone number first.";
    return;
  }

  const category = document.getElementById("categoryInput").value;
  const note = document.getElementById("noteInput").value.trim();

  try {
    const data = await apiRequest("/api/report", {
      method: "POST",
      body: JSON.stringify({ phone, category, note }),
    });
    reportStatus.textContent = `Report stored. Spam ${data.report_counts.spam}, Scam ${data.report_counts.scam}, Safe ${data.report_counts.safe}`;
    await loadHistory();
  } catch (error) {
    reportStatus.textContent = error.message;
  }
});

refreshHistoryBtn.addEventListener("click", loadHistory);

loadHistory();

const savedApiKey = localStorage.getItem("phoneIntelApiKey");
if (savedApiKey && apiKeyInput) {
  apiKeyInput.value = savedApiKey;
}
