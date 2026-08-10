const contentCache = new Map();

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function authorText(authors = "") {
  return Array.isArray(authors) ? authors.join(", ") : String(authors || "");
}

function highlightName(authors = "") {
  return escapeHtml(authorText(authors)).replaceAll("Zhucheng Yang", "<mark>Zhucheng Yang</mark>");
}

async function loadContent(name) {
  if (contentCache.has(name)) return contentCache.get(name);
  const response = await fetch(`./content/${name}.json`);
  if (!response.ok) throw new Error(`Unable to load ${name}.json`);
  const data = await response.json();
  contentCache.set(name, data);
  return data;
}

function renderHome(site) {
  const profile = site?.profile || {};
  setText("[data-home-eyebrow]", profile.eyebrow);
  setText("[data-home-subtitle]", profile.subtitle);
  setText("[data-home-intro]", profile.intro);

  const title = document.querySelector("[data-home-title]");
  if (title && Array.isArray(profile.heroName)) {
    title.innerHTML = profile.heroName.map((line) => `<span>${escapeHtml(line)}</span>`).join("");
  }

  setText("[data-home-chinese]", profile.chineseName);

  const portrait = document.querySelector("[data-profile-portrait]");
  const portraitImage = portrait?.querySelector("img");
  if (portraitImage && profile.portrait?.src) {
    portraitImage.src = profile.portrait.src;
    portraitImage.alt = profile.portrait.alt || "Portrait of Zhucheng Yang";
  }

  const cards = document.querySelector("[data-home-cards]");
  if (cards && Array.isArray(site.homeCards)) {
    cards.innerHTML = site.homeCards
      .map((card, index) => `
        <a class="entry-card" href="${escapeHtml(card.href)}">
          <span class="number">${String(index + 1).padStart(2, "0")}</span>
          <div>
            <h2>${escapeHtml(card.title)}</h2>
            <p>${escapeHtml(card.text)}</p>
          </div>
        </a>
      `)
      .join("");
  }
}

function renderAcademic(site, publications) {
  const intro = document.querySelector("[data-research-intro]");
  if (intro && site?.academic?.researchIntro) intro.textContent = site.academic.researchIntro;

  const metrics = document.querySelector("[data-academic-metrics]");
  if (metrics) {
    const scholar = site?.academic?.scholarMetrics || {};
    const topicCount = site?.academic?.topics?.length || 0;
    const scholarNote = `Google Scholar · updated ${formatMonthYear(scholar.updated)}`;
    const metricItems = [
      {
        label: "PUBLICATIONS",
        value: publications.length,
        note: "Entries currently listed in publications.json."
      },
      {
        label: "RESEARCH THEMES",
        value: topicCount,
        note: "Synthesis, spectra, structure, and AI."
      },
      {
        label: "CITATIONS",
        value: scholar.citations,
        note: scholarNote,
        href: scholar.url
      },
      {
        label: "H-INDEX",
        value: scholar.hIndex,
        note: scholarNote,
        href: scholar.url
      }
    ].filter((item) => item.value !== undefined && item.value !== null);

    metrics.innerHTML = metricItems
      .map((item) => `
        <div class="stat reveal">
          ${item.href ? `<a href="${escapeHtml(item.href)}" target="_blank" rel="noopener noreferrer">` : ""}
            <strong>${escapeHtml(item.value)}</strong>
            <span>${escapeHtml(item.label)}</span>
            <small>${escapeHtml(item.note)}</small>
          ${item.href ? "</a>" : ""}
        </div>
      `)
      .join("");
  }

  const topics = document.querySelector("[data-research-topics]");
  if (topics && Array.isArray(site?.academic?.topics)) {
    topics.innerHTML = site.academic.topics
      .map((topic) => `
        <article>
          <h3>${escapeHtml(topic.title)}</h3>
          <p>${escapeHtml(topic.text)}</p>
        </article>
      `)
      .join("");
  }

  renderPublications(publications);
}

function renderPublications(publications = []) {
  const target = document.querySelector("[data-publications]");
  if (!target) return;

  target.innerHTML = publications
    .map((pub, index) => `
      <article class="publication-row reveal">
        <a class="publication-cover" href="${escapeHtml(publicationUrl(pub))}" target="_blank" rel="noopener noreferrer" aria-label="Open article: ${escapeHtml(pub.title)}">
          <img src="${escapeHtml(pub.image)}" alt="Cover image for ${escapeHtml(pub.title)}" loading="lazy" decoding="async">
        </a>
        <div class="publication-main">
          <h2 class="pub-title">${publications.length - index}. ${escapeHtml(pub.title)}</h2>
          <p class="pub-meta">${highlightName(pub.authors)}</p>
          <p class="pub-meta">${publicationMeta(pub)}</p>
          ${pub.doi ? `<p class="pub-meta">DOI: <a href="${escapeHtml(publicationUrl(pub))}" target="_blank" rel="noopener noreferrer">${escapeHtml(pub.doi)}</a></p>` : ""}
        </div>
        <a class="publication-year" href="${escapeHtml(publicationUrl(pub))}" target="_blank" rel="noopener noreferrer" aria-label="View article: ${escapeHtml(pub.title)}">
          <span>${escapeHtml(pub.year)}</span>
          <span aria-hidden="true">-&gt;</span>
        </a>
      </article>
    `)
    .join("");
}

function publicationUrl(pub) {
  return pub.link || pub.url || (pub.doi ? `https://doi.org/${pub.doi}` : "#");
}

function publicationMeta(pub) {
  const details = [`<em>${escapeHtml(pub.journal)}</em>`, escapeHtml(pub.year)];
  if (pub.volume && pub.issue) {
    details.push(`${escapeHtml(pub.volume)}(${escapeHtml(pub.issue)})`);
  } else if (pub.volume) {
    details.push(escapeHtml(pub.volume));
  }
  if (pub.articleNumber) details.push(escapeHtml(pub.articleNumber));
  if (pub.note) details.push(escapeHtml(pub.note));
  return details.join(", ");
}

function renderNews(news = [], limit = null) {
  const target = document.querySelector("[data-news]");
  if (!target) return;

  const sorted = [...news].sort((a, b) => newsTimestamp(b) - newsTimestamp(a));
  const items = limit ? sorted.slice(0, limit) : sorted;
  let currentYear = "";
  target.innerHTML = items
    .map((item) => {
      const year = newsYear(item);
      const yearLabel = year !== currentYear ? `<h2 class="news-year">${escapeHtml(year)}</h2>` : "";
      currentYear = year;
      const textZh = item.textZh || item.zh;
      return `
        ${yearLabel}
        <article class="news-item reveal">
          <div class="news-stamp">
            <time class="news-date" datetime="${escapeHtml(item.date || item.fullDate)}">${escapeHtml(item.displayDate || item.date)}</time>
            <span class="news-category">${escapeHtml(item.category)}</span>
          </div>
          <div>
            <h3>${escapeHtml(item.title)}</h3>
            <p>${escapeHtml(item.text)}</p>
            ${textZh ? `<p class="news-zh" lang="zh-Hans">${escapeHtml(textZh)}</p>` : ""}
          </div>
        </article>
      `;
    })
    .join("");
}

function newsTimestamp(item) {
  const raw = item.endDate || item.date || item.fullDate || "";
  if (/^\d{4}-\d{2}$/.test(raw)) return Date.parse(`${raw}-01T00:00:00`);
  const parsed = Date.parse(String(raw).replaceAll("/", "-"));
  return Number.isNaN(parsed) ? 0 : parsed;
}

function newsYear(item) {
  return String(item.year || (item.date ? item.date.slice(0, 4) : ""));
}

function renderTrips(trips = []) {
  const target = document.querySelector("[data-trips]");
  if (!target) return;

  const sorted = [...trips].sort((a, b) => Number(a.order || 999) - Number(b.order || 999));

  target.innerHTML = sorted
    .map((trip, tripIndex) => {
      const title = trip.title || trip.folder || trip.destination || "Journey";
      const photos = normaliseJourneyPhotos(trip);
      const featuredIndex = featuredIndexFor(photos, trip.featured);
      const featured = photos[featuredIndex] || null;
      const supporting = photos.filter((_, index) => index !== featuredIndex);
      const order = Number(trip.order || tripIndex + 1);
      return `
      <article class="trip reveal">
        <header class="trip-header">
          <div class="trip-year">${String(order).padStart(2, "0")}</div>
          <div>
            <h2>${escapeHtml(title)}</h2>
            ${trip.meta ? `<p class="trip-meta">${escapeHtml(trip.meta)}</p>` : ""}
            ${trip.introEn ? `<p class="trip-intro trip-intro-en">${escapeHtml(trip.introEn)}</p>` : ""}
            ${trip.introZh ? `<p class="trip-intro trip-intro-zh" lang="${trip.title === "省港澳" || trip.title === "小小多山的島" ? "zh-Hant" : "zh-Hans"}">${escapeHtml(trip.introZh)}</p>` : ""}
          </div>
        </header>
        ${featured ? `
          <figure class="trip-hero">
            <img src="${escapeHtml(featured.src)}" alt="${escapeHtml(title)} featured photograph" loading="${tripIndex === 0 ? "eager" : "lazy"}" decoding="async">
          </figure>
        ` : ""}
        <div class="image-grid justified-gallery" data-justified-gallery>
          ${supporting.map((image) => `
            <figure>
              <img src="${escapeHtml(image.src)}" alt="${escapeHtml(title)} selected photograph" loading="lazy" decoding="async">
            </figure>
          `).join("")}
        </div>
      </article>
    `;
    })
    .join("");
}

function normaliseJourneyPhotos(trip) {
  const folder = trip.folder || "";
  const rawPhotos = trip.photos || [
    ...(trip.hero ? [trip.hero] : []),
    ...(trip.images || []),
  ];
  return rawPhotos.map((photo) => {
    const filename = typeof photo === "string" ? photo : photo?.src || "";
    return { filename, src: photoPath(folder, filename) };
  }).filter((photo) => photo.filename && photo.src);
}

function featuredIndexFor(photos, featured) {
  if (featured) {
    const index = photos.findIndex((photo) => (
      photo.filename === featured ||
      photo.src === featured ||
      photo.src.endsWith(`/${featured}`)
    ));
    if (index >= 0) return index;
  }
  return photos.length ? 0 : -1;
}

function photoPath(folder, src = "") {
  if (/^(https?:)?\/\//.test(src) || src.startsWith("assets/")) return src;
  return `assets/images/photography/${folder}/${src}`;
}

function renderFlightStats(flightData) {
  const target = document.querySelector("[data-flight-summary]");
  if (!target) return;
  const stats = flightData?.stats || {};
  const highlights = flightData?.highlights || {};
  const totalHours = stats.total_duration_minutes ? Math.round(stats.total_duration_minutes / 60) : null;
  const distance = stats.total_distance_km ? `${Math.round(stats.total_distance_km / 1000)}k` : null;
  const mostRoute = highlights.most_flown_route
    ? `${highlights.most_flown_route.origin}-${highlights.most_flown_route.destination}`
    : null;

  const items = [
    { label: "Flights", value: stats.total_flights, note: "Logged flights in the Flight Log database." },
    { label: "Distance", value: distance, note: "Total recorded distance in kilometers." },
    { label: "Airports", value: stats.total_airports, note: `${stats.total_countries || 0} countries represented by airport data.` },
    { label: "Hours", value: totalHours, note: "Recorded airborne time where duration is available." },
    { label: "Airlines", value: stats.total_airlines, note: highlights.top_airline ? `Most flown: ${highlights.top_airline.name}.` : "" },
    { label: "Most flown route", value: mostRoute, note: highlights.most_flown_route ? `${highlights.most_flown_route.count} logged flights.` : "" },
    { label: "Top aircraft", value: highlights.top_aircraft?.name, note: highlights.top_aircraft ? `${highlights.top_aircraft.count} logged flights.` : "" },
    { label: "Longest flight", value: routeLabel(highlights.longest_flight), note: highlights.longest_flight?.distance_km ? `${formatNumber(highlights.longest_flight.distance_km)} km.` : "" },
  ].filter((item) => item.value);

  target.innerHTML = items
    .map((item) => `
      <div class="stat reveal">
        <strong>${escapeHtml(item.value)}</strong>
        <span>${escapeHtml(item.label)}</span>
        <small>${escapeHtml(item.note)}</small>
      </div>
    `)
    .join("");
}

function renderSpecialLiveries(flightData) {
  const section = document.querySelector("[data-special-liveries-section]");
  const target = document.querySelector("[data-special-liveries]");
  if (!section || !target) return;
  const liveries = Array.isArray(flightData?.specialLiveries) ? flightData.specialLiveries : [];
  if (!liveries.length) {
    section.hidden = true;
    return;
  }
  section.hidden = false;
  target.innerHTML = liveries
    .map((item) => `
      <article class="special-livery-row reveal">
        <h3>${escapeHtml(item.registration || "")}</h3>
        <div>
          ${item.aircraft ? `<p>${escapeHtml(item.aircraft)}</p>` : ""}
          ${item.airline ? `<p>${escapeHtml(item.airline)}</p>` : ""}
        </div>
        <strong>${escapeHtml(item.livery || "")}</strong>
      </article>
    `)
    .join("");
}

function renderPlanespotting(flying) {
  const target = document.querySelector("[data-planespotting]");
  if (!target) return;
  target.innerHTML = (flying?.planespotting || [])
    .map((item) => `
      <article class="spotting-row reveal">
        <strong>${escapeHtml(item.iata)}</strong>
        <span>${escapeHtml(item.airport)}</span>
        <em>${escapeHtml([item.city, item.country].filter(Boolean).join(", "))}</em>
      </article>
    `)
    .join("");
}

function renderContact(site) {
  const target = document.querySelector("[data-contact-links]");
  if (!target || !Array.isArray(site?.contact)) return;
  target.innerHTML = site.contact
    .map((item) => {
      const external = item.href?.startsWith("http");
      return `
        <div class="contact-tile">
          <strong>${escapeHtml(item.label)}</strong>
          <span><a href="${escapeHtml(item.href)}"${external ? ' target="_blank" rel="noopener noreferrer"' : ""}>${escapeHtml(item.text)}</a></span>
        </div>
      `;
    })
    .join("");
}

function renderAviationGallery(flying) {
  const target = document.querySelector("[data-aviation-gallery]");
  if (!target) return;
  const aviation = normaliseAviationPhotos(flying);
  const featuredIndex = featuredIndexFor(aviation.photos, aviation.featured);
  const featured = aviation.photos[featuredIndex] || null;
  const supporting = aviation.photos.filter((_, index) => index !== featuredIndex);
  const ordered = featured ? [featured, ...supporting] : supporting;
  target.setAttribute("data-justified-gallery", "");
  target.innerHTML = ordered
    .map((image, index) => `
      <figure class="${index === 0 && featured ? "is-featured" : ""} reveal">
        <img src="${escapeHtml(image.src)}" alt="Aviation photograph" loading="lazy" decoding="async">
      </figure>
    `)
    .join("");
}

function normaliseAviationPhotos(flying) {
  const aviation = flying?.aviationPhotography || {};
  const rawPhotos = Array.isArray(aviation.photos) ? aviation.photos : (flying?.gallery || []);
  return {
    featured: aviation.featured || legacyFeaturedAviationPhoto(flying),
    photos: rawPhotos.map((photo) => {
      const filename = typeof photo === "string" ? photo : photo?.src || "";
      return { filename: cleanFlyingFilename(filename), src: flyingPhotoPath(filename) };
    }).filter((photo) => photo.filename && photo.src),
  };
}

function legacyFeaturedAviationPhoto(flying) {
  const featured = (flying?.gallery || []).find((photo) => photo?.featured);
  return cleanFlyingFilename(featured?.src || "");
}

function cleanFlyingFilename(src = "") {
  const prefix = "assets/images/flying/";
  return src.startsWith(prefix) ? src.slice(prefix.length) : src;
}

function flyingPhotoPath(src = "") {
  if (/^(https?:)?\/\//.test(src) || src.startsWith("assets/")) return src;
  return `assets/images/flying/${src}`;
}

function drawFlightMap(flightData, flying) {
  const target = document.querySelector("#flight-map");
  if (!target || !flightData) return;

  const airports = flightData.airports || {};
  const spotting = new Set((flying?.planespotting || []).map((item) => item.iata));
  const routes = (flightData.routes || [])
    .filter((route) => hasCoordinates(airports[route.origin]) && hasCoordinates(airports[route.destination]))
    .slice(0, 90);
  const maxCount = routes.reduce((max, route) => Math.max(max, route.count || 1), 1);
  const airportCodes = [...new Set([
    ...routes.flatMap((route) => [route.origin, route.destination]),
    ...[...spotting].filter((code) => hasCoordinates(airports[code])),
  ])];

  target.innerHTML = `
    <svg viewBox="0 0 1000 520" role="img" aria-labelledby="flight-map-title flight-map-desc">
      <title id="flight-map-title">World flight map</title>
      <desc id="flight-map-desc">Flight routes and planespotting airports.</desc>
      <g class="map-graticule"></g>
      <g class="map-land" aria-hidden="true"></g>
      <g class="map-routes"></g>
      <g class="map-airports"></g>
      <g class="map-labels" aria-hidden="true"></g>
    </svg>
    <div class="map-panel" data-map-panel tabindex="-1">Select a route or airport.</div>
    <div class="map-legend" aria-label="Map legend">
      <span><i class="dot"></i> Flight airport</span>
      <span><i class="ring"></i> Planespotting airport</span>
    </div>
  `;

  const svg = target.querySelector("svg");
  const graticule = svg.querySelector(".map-graticule");
  const land = svg.querySelector(".map-land");
  const routeLayer = svg.querySelector(".map-routes");
  const airportLayer = svg.querySelector(".map-airports");
  const labels = svg.querySelector(".map-labels");
  const panel = target.querySelector("[data-map-panel]");

  drawGraticule(graticule);
  drawLand(land);

  routes.forEach((route) => {
    const origin = airports[route.origin];
    const destination = airports[route.destination];
    const [x1, y1] = project(origin.longitude, origin.latitude);
    const [x2, y2] = project(destination.longitude, destination.latitude);
    const curve = curvePath(x1, y1, x2, y2);
    const hit = document.createElementNS("http://www.w3.org/2000/svg", "path");
    hit.setAttribute("d", curve);
    hit.setAttribute("class", "route-hit");
    hit.setAttribute("tabindex", "0");
    hit.setAttribute("role", "button");
    hit.setAttribute("aria-label", `${route.origin} to ${route.destination}, ${route.count} flights`);
    bindMapEvents(hit, () => showRoute(panel, route));

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", curve);
    path.setAttribute("class", "route-line");
    path.setAttribute("stroke-width", String(0.65 + (route.count / maxCount) * 2.6));
    routeLayer.append(hit, path);
  });

  airportCodes.forEach((code) => {
    const airport = airports[code];
    const [x, y] = project(airport.longitude, airport.latitude);
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", String(x));
    circle.setAttribute("cy", String(y));
    circle.setAttribute("r", spotting.has(code) ? "5.2" : "3.2");
    circle.setAttribute("class", spotting.has(code) ? "airport-point is-spotting" : "airport-point");
    circle.setAttribute("tabindex", "0");
    circle.setAttribute("role", "button");
    circle.setAttribute("aria-label", `${code}, ${airport.name || airport.city || "airport"}`);
    bindMapEvents(circle, () => showAirport(panel, airport));
    airportLayer.append(circle);
  });

  [...spotting].forEach((code) => {
    const airport = airports[code];
    if (!hasCoordinates(airport)) return;
    const [x, y] = project(airport.longitude, airport.latitude);
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", String(x + 8));
    text.setAttribute("y", String(y - 8));
    text.textContent = code;
    labels.append(text);
  });
}

function bindMapEvents(element, handler) {
  ["mouseenter", "focus", "click", "pointerdown"].forEach((eventName) => {
    element.addEventListener(eventName, handler);
  });
}

function drawGraticule(group) {
  for (let lon = -150; lon <= 150; lon += 30) {
    const [x] = project(lon, 0);
    appendLine(group, x, 20, x, 500);
  }
  for (let lat = -60; lat <= 60; lat += 30) {
    const [, y] = project(0, lat);
    appendLine(group, 20, y, 980, y);
  }
}

function drawLand(group) {
  [
    [170, 170, 150, 96],
    [300, 286, 92, 152],
    [488, 180, 132, 96],
    [640, 190, 240, 112],
    [802, 350, 96, 66],
  ].forEach(([cx, cy, rx, ry]) => {
    const ellipse = document.createElementNS("http://www.w3.org/2000/svg", "ellipse");
    ellipse.setAttribute("cx", cx);
    ellipse.setAttribute("cy", cy);
    ellipse.setAttribute("rx", rx);
    ellipse.setAttribute("ry", ry);
    group.append(ellipse);
  });
}

function appendLine(group, x1, y1, x2, y2) {
  const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
  line.setAttribute("x1", x1);
  line.setAttribute("y1", y1);
  line.setAttribute("x2", x2);
  line.setAttribute("y2", y2);
  group.append(line);
}

function project(lon, lat) {
  return [((Number(lon) + 180) / 360) * 1000, ((90 - Number(lat)) / 180) * 520];
}

function curvePath(x1, y1, x2, y2) {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const distance = Math.hypot(x2 - x1, y2 - y1);
  const lift = Math.min(120, Math.max(28, distance * 0.18));
  return `M ${x1.toFixed(2)} ${y1.toFixed(2)} Q ${mx.toFixed(2)} ${(my - lift).toFixed(2)} ${x2.toFixed(2)} ${y2.toFixed(2)}`;
}

function showRoute(panel, route) {
  panel.innerHTML = `
    <strong>${escapeHtml(route.origin)} -> ${escapeHtml(route.destination)}</strong>
    <span>${escapeHtml(route.count)} logged flight${route.count === 1 ? "" : "s"}</span>
    <em>${route.distance_km ? `${formatNumber(route.distance_km)} km` : "Distance unavailable"}${route.first_year ? ` / ${route.first_year}-${route.last_year}` : ""}</em>
  `;
}

function showAirport(panel, airport) {
  panel.innerHTML = `
    <strong>${escapeHtml(airport.iata)}</strong>
    <span>${escapeHtml(airport.name || airport.city || "Airport")}</span>
    <em>${escapeHtml([airport.city, airport.country].filter(Boolean).join(", "))}</em>
    <em>${escapeHtml(airport.departures || 0)} departures / ${escapeHtml(airport.arrivals || 0)} arrivals</em>
  `;
}

function hasCoordinates(airport) {
  return airport && airport.latitude !== undefined && airport.longitude !== undefined;
}

function routeLabel(flight) {
  if (!flight?.origin || !flight?.destination) return null;
  return `${flight.origin}-${flight.destination}`;
}

function formatNumber(value) {
  return new Intl.NumberFormat("en").format(value);
}

function formatMonthYear(dateString) {
  if (!dateString) return "manually";
  const date = new Date(`${dateString}T00:00:00`);
  if (Number.isNaN(date.getTime())) return dateString;
  return new Intl.DateTimeFormat("en", { month: "short", year: "numeric" }).format(date);
}

function setText(selector, value) {
  const target = document.querySelector(selector);
  if (target && value) target.textContent = value;
}

function wireMenu() {
  const button = document.querySelector("[data-menu-toggle]");
  const nav = document.querySelector("[data-nav]");
  if (!button || !nav) return;

  button.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("is-open");
    document.body.classList.toggle("menu-open", isOpen);
    button.setAttribute("aria-expanded", String(isOpen));
  });
}

function wireReveal() {
  const items = document.querySelectorAll(".reveal");
  if (!items.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });

  items.forEach((item) => observer.observe(item));
}

async function hydratePage() {
  const page = document.body.dataset.page;
  const loaders = {
    async home() {
      const [site, news] = await Promise.all([loadContent("site"), loadContent("news")]);
      renderHome(site);
      renderNews(news, document.body.dataset.newsLimit ? Number(document.body.dataset.newsLimit) : null);
    },
    async academic() {
      const [site, publications] = await Promise.all([loadContent("site"), loadContent("publications")]);
      renderAcademic(site, publications);
    },
    async photography() {
      renderTrips(await loadContent("travel"));
    },
    async flying() {
      const [flying, flightData] = await Promise.all([loadContent("flying"), loadContent("flight-data")]);
      renderFlightStats(flightData);
      renderSpecialLiveries(flightData);
      drawFlightMap(flightData, flying);
      renderPlanespotting(flying);
      renderAviationGallery(flying);
    },
    async news() {
      renderNews(await loadContent("news"));
    },
    async contact() {
      renderContact(await loadContent("site"));
    },
  };

  if (loaders[page]) {
    await loaders[page]();
  }

  if (window.K2Gallery) {
    window.K2Gallery.layoutAll();
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  wireMenu();
  try {
    await hydratePage();
  } catch (error) {
    const main = document.querySelector("main");
    if (main) {
      main.insertAdjacentHTML(
        "beforeend",
        '<p class="content-error">Content could not be loaded. Preview the site through a local HTTP server so JSON requests are available.</p>',
      );
    }
    console.warn(error);
  }
  wireReveal();
});
