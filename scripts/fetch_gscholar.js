const puppeteer = require('puppeteer');
const fs = require('fs');

async function fetchMetrics(profileUrl) {
  const browser = await puppeteer.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  await page.setUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117 Safari/537.36');

  try {
    await page.goto(profileUrl, { waitUntil: 'networkidle2', timeout: 60000 });
    await page.waitForSelector('#gsc_rsb_st', { timeout: 15000 });

    const data = await page.evaluate(() => {
      const rows = Array.from(document.querySelectorAll('#gsc_rsb_st tbody tr'));
      const result = {};
      rows.forEach(tr => {
        const label = tr.querySelector('td.gsc_rsb_sth')?.innerText?.trim();
        const vals = Array.from(tr.querySelectorAll('td.gsc_rsb_std')).map(td => td.innerText.trim());
        if (label) {
          result[label] = { all: vals[0] || null, since: vals[1] || null };
        }
      });
      const nameEl = document.querySelector('#gsc_prf_in');
      const name = nameEl ? nameEl.innerText.trim() : null;
      return { name, stats: result };
    });

    const citationAll = data.stats['Citations'] ? parseInt(data.stats['Citations'].all.replace(/,/g,'') ) : null;
    const hindexAll   = data.stats['h-index'] ? parseInt(data.stats['h-index'].all.replace(/,/g,'') ) : null;
    const i10All      = data.stats['i10-index'] ? parseInt(data.stats['i10-index'].all.replace(/,/g,'') ) : null;

    const out = {
      name: data.name,
      citation_all: citationAll,
      h_index_all: hindexAll,
      i10_index_all: i10All,
      fetched_at: (new Date()).toISOString(),
      source: profileUrl
    };

    await browser.close();

    // ensure data directory exists
    try { fs.mkdirSync('data', { recursive: true }); } catch(e){}
    fs.writeFileSync('data/citation.json', JSON.stringify(out, null, 2));
    console.log('Wrote data/citation.json');
    return out;
  } catch (err) {
    await browser.close();
    console.error('Error in fetchMetrics:', err.message);
    throw err;
  }
}

if (require.main === module) {
  (async () => {
    const profileUrl = process.env.PROFILE_URL || process.argv[2];
    if (!profileUrl) {
      console.error('Usage: PROFILE_URL="<url>" node fetch_gscholar.js OR node fetch_gscholar.js <url>');
      process.exit(2);
    }
    try {
      await fetchMetrics(profileUrl);
    } catch (e) {
      console.error('Fetch failed:', e);
      process.exit(1);
    }
  })();
}
