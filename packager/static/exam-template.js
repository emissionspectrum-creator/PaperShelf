// 考卷 HTML 產生邏輯（DESIGN.md 第 6、7 節）。
// 預覽與最終存檔輸出都呼叫這個函式，避免預覽與正式產物走兩套邏輯。
(function (root) {
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // questions: [{ dataUrl: "data:image/...;base64,...", scale: 100 }]
  function buildExamHtml({ grade, subject, questions }) {
    const title = escapeHtml(`${grade} ${subject}`);
    const items = questions
      .map(
        (q) => `    <div class="frame">
      <img src="${q.dataUrl}" style="width:${q.scale}%" alt="">
    </div>`
      )
      .join("\n");

    return `<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<style>
  html, body {
    margin: 0;
    padding: 0;
    background: #f5f4f0;
  }
  .frame {
    box-sizing: border-box;
    width: min(900px, 96vw);
    margin: 0 auto 3rem auto;
  }
  .frame:first-child {
    margin-top: 2rem;
  }
  .frame img {
    display: block;
    margin: 0 auto;
    max-width: 100%;
    height: auto;
  }
</style>
</head>
<body>
${items}
</body>
</html>
`;
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { buildExamHtml };
  } else {
    root.buildExamHtml = buildExamHtml;
  }
})(typeof window !== "undefined" ? window : globalThis);
