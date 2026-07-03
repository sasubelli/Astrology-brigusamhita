const form = document.querySelector("#birthForm");
const statusEl = document.querySelector("#status");
const reportEl = document.querySelector("#report");
const emptyState = document.querySelector("#emptyState");
const placesList = document.querySelector("#places");

const chartSlots = [
  [12, 1, 1],
  [1, 1, 2],
  [2, 1, 3],
  [3, 1, 4],
  [11, 2, 1],
  [4, 2, 4],
  [10, 3, 1],
  [5, 3, 4],
  [9, 4, 1],
  [8, 4, 2],
  [7, 4, 3],
  [6, 4, 4],
];

async function loadPlaces(query = "") {
  const response = await fetch(`/api/places?q=${encodeURIComponent(query)}`);
  const places = await response.json();
  placesList.innerHTML = places.map((place) => `<option value="${escapeHtml(place.name)}"></option>`).join("");
}

form.place.addEventListener("input", () => {
  loadPlaces(form.place.value).catch(() => {});
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("Calculating");
  const button = form.querySelector("button");
  button.disabled = true;

  const payload = Object.fromEntries(new FormData(form).entries());
  for (const key of ["latitude", "longitude"]) {
    payload[key] = payload[key] ? Number(payload[key]) : null;
  }
  payload.name = payload.name?.trim() || "Native";
  for (const key of ["place", "timezone"]) {
    payload[key] = payload[key]?.trim() || null;
  }

  try {
    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Unable to calculate chart.");
    }
    renderReport(data);
    setStatus("Complete");
  } catch (error) {
    renderError(error.message);
    setStatus("Check input");
  } finally {
    button.disabled = false;
  }
});

function renderReport(data) {
  emptyState.classList.add("hidden");
  reportEl.classList.remove("hidden");
  reportEl.classList.remove("error");

  reportEl.innerHTML = `
    <section class="section summary-band">
      ${renderChart(data)}
      <div>
        <h2>${escapeHtml(data.birth.name)}</h2>
        <div class="meta-grid">
          ${meta("Birth", formatDateTime(data.birth.local_datetime))}
          ${meta("Place", data.birth.place)}
          ${meta("Timezone", data.birth.timezone)}
          ${meta("Lagna", `${data.ascendant.sign} ${data.ascendant.degree_in_sign.toFixed(2)}°`)}
          ${meta("Moon", `${data.planets.Moon.sign}, ${data.planets.Moon.nakshatra} pada ${data.planets.Moon.pada}`)}
          ${meta("Panchanga", `${data.panchanga.vara}, ${data.panchanga.paksha} ${data.panchanga.tithi_name}`)}
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Core Reading</h2>
      <div class="area-grid">
        ${Object.entries(data.core_reading).map(([title, text]) => miniCard(titleLabel(title), text)).join("")}
      </div>
    </section>

    <section class="section">
      <h2>Sutra Trace</h2>
      <div>${data.sutra_trace.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("")}</div>
    </section>

    <section class="section">
      <h2>Planetary Positions</h2>
      ${renderPlanetTable(data.planets)}
    </section>

    <section class="section">
      <h2>Yogas</h2>
      <div class="yoga-grid">${data.yogas
        .map((yoga) => miniCard(yoga.name, yoga.reading, `Strength: ${yoga.strength}`))
        .join("")}</div>
    </section>

    <section class="section">
      <h2>Life Areas</h2>
      <div class="area-grid">${Object.entries(data.life_areas)
        .map(([name, area]) =>
          miniCard(titleLabel(name), `${area.reading}<br><br>${area.karaka_check}`, area.timing_key),
        )
        .join("")}</div>
    </section>

    <section class="section">
      <h2>Future Timeline</h2>
      <div class="timeline-grid">${data.future_timeline.map(renderTimeline).join("")}</div>
    </section>

    <section class="section">
      <h2>Remedies</h2>
      <div class="remedy-grid">${data.remedies
        .map((item) => miniCard(item.focus, item.practice))
        .join("")}</div>
    </section>
  `;
}

function renderChart(data) {
  const byHouse = {};
  for (const [name, planet] of Object.entries(data.planets)) {
    byHouse[planet.house] ||= [];
    byHouse[planet.house].push(name);
  }
  const houses = Object.fromEntries(data.house_signs.map((item) => [item.house, item]));
  const cells = chartSlots
    .map(([house, row, col]) => {
      const info = houses[house];
      const planets = byHouse[house] || [];
      return `<div class="chart-cell" style="grid-row:${row};grid-column:${col}">
        <div class="house-num">H${house}</div>
        <div class="sign-name">${escapeHtml(info.sign)}</div>
        <div class="planet-list">${planets.map(escapeHtml).join(", ")}</div>
      </div>`;
    })
    .join("");
  return `<div class="chart-grid" aria-label="Whole sign birth chart">
    ${cells}
    <div class="chart-center">Whole Sign<br>Rasi Chart</div>
  </div>`;
}

function renderPlanetTable(planets) {
  const rows = Object.values(planets)
    .map(
      (planet) => `<tr>
        <td>${escapeHtml(planet.name)}</td>
        <td>${escapeHtml(planet.sign)}</td>
        <td>${planet.degree_in_sign.toFixed(2)}°</td>
        <td>${escapeHtml(planet.nakshatra)} ${planet.pada}</td>
        <td>${planet.house}</td>
        <td>${escapeHtml(planet.dignity)}</td>
        <td>${planet.retrograde ? "Yes" : "No"}</td>
      </tr>`,
    )
    .join("");
  return `<div class="table-wrap"><table>
    <thead><tr><th>Planet</th><th>Sign</th><th>Degree</th><th>Nakshatra</th><th>House</th><th>Dignity</th><th>Retro</th></tr></thead>
    <tbody>${rows}</tbody>
  </table></div>`;
}

function renderTimeline(period) {
  return miniCard(
    period.period,
    `<strong>${period.start} to ${period.end}</strong><br>Age ${period.age_range}<br><br>${period.opportunity}`,
    `${period.watch}<br><br>${period.practice}`,
  );
}

function miniCard(title, body, extra = "") {
  return `<article class="mini-card">
    <h3>${escapeHtml(title)}</h3>
    <p>${body}</p>
    ${extra ? `<p>${extra}</p>` : ""}
  </article>`;
}

function meta(label, value) {
  return `<div class="mini-card"><h3>${escapeHtml(label)}</h3><p>${escapeHtml(value)}</p></div>`;
}

function renderError(message) {
  emptyState.classList.add("hidden");
  reportEl.classList.remove("hidden");
  reportEl.classList.add("error");
  reportEl.innerHTML = `<section class="section"><h2>Input needs attention</h2><p>${escapeHtml(message)}</p></section>`;
}

function setStatus(text) {
  statusEl.textContent = text;
}

function titleLabel(value) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDateTime(value) {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

loadPlaces().catch(() => {});
