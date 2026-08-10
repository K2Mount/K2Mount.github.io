(function () {
  function targetHeight(width) {
    if (width < 560) return 180;
    if (width < 980) return 225;
    return 300;
  }

  function aspectFor(figure) {
    const image = figure.querySelector("img");
    const natural = image?.naturalWidth && image?.naturalHeight
      ? image.naturalWidth / image.naturalHeight
      : 4 / 3;
    return Math.max(0.25, Math.min(natural, 5.2));
  }

  function buildRows(figures, width, gap, target) {
    const rows = [];
    let row = [];
    let aspectSum = 0;

    figures.forEach((figure) => {
      const aspect = aspectFor(figure);
      if (figure.classList.contains("is-featured")) {
        if (row.length) {
          rows.push({ items: row, aspectSum, complete: false });
          row = [];
          aspectSum = 0;
        }
        rows.push({ items: [{ figure, aspect }], aspectSum: aspect, featured: true });
        return;
      }

      if (width < 560) {
        rows.push({ items: [{ figure, aspect }], aspectSum: aspect, complete: false });
        return;
      }

      row.push({ figure, aspect });
      aspectSum += aspect;
      const filledWidth = aspectSum * target + gap * Math.max(0, row.length - 1);
      if (filledWidth >= width && row.length > 1) {
        rows.push({ items: row, aspectSum, complete: true });
        row = [];
        aspectSum = 0;
      }
    });

    if (row.length) {
      rows.push({ items: row, aspectSum, complete: false });
    }

    return rows;
  }

  function layout(container) {
    const figures = container.__galleryFigures || Array.from(container.querySelectorAll(":scope > figure, :scope > .gallery-row > figure"));
    container.__galleryFigures = figures;
    if (!figures.length) return;

    const width = container.clientWidth;
    if (!width) return;

    const gap = Number(getComputedStyle(container).getPropertyValue("--gallery-gap").replace("px", "")) || 1;
    const target = targetHeight(width);
    const rows = buildRows(figures, width, gap, target);
    const rowNodes = rows.map((row) => {
      const rowNode = document.createElement("div");
      rowNode.className = row.complete ? "gallery-row" : "gallery-row is-last";
      const rowHeight = row.featured
        ? Math.max(target, Math.min(width < 760 ? 460 : 620, width / row.aspectSum))
        : row.complete
        ? Math.min(340, (width - gap * (row.items.length - 1)) / row.aspectSum)
        : Math.min(target, width / row.aspectSum);

      row.items.forEach(({ figure, aspect }) => {
        const figureWidth = row.featured ? width : Math.round(rowHeight * aspect);
        figure.style.width = `${figureWidth}px`;
        figure.style.height = `${Math.round(rowHeight)}px`;
        figure.style.flexBasis = `${figureWidth}px`;
        rowNode.append(figure);
      });

      return rowNode;
    });

    container.replaceChildren(...rowNodes);
  }

  function layoutGallery(container) {
    if (!container) return;
    const figures = Array.from(container.querySelectorAll(":scope > figure, :scope > .gallery-row > figure"));
    container.__galleryFigures = figures;
    layout(container);
    figures.forEach((figure) => {
      const image = figure.querySelector("img");
      if (!image || image.complete) return;
      image.addEventListener("load", () => layout(container), { once: true });
      image.addEventListener("error", () => layout(container), { once: true });
    });
  }

  function layoutAll(root = document) {
    root.querySelectorAll("[data-justified-gallery]").forEach((container) => layoutGallery(container));
  }

  let resizeTimer = 0;
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => {
      document.querySelectorAll("[data-justified-gallery]").forEach((container) => layout(container));
    }, 120);
  });

  window.K2Gallery = { layoutAll, layoutGallery };
})();
