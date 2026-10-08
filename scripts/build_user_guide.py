"""Capture the running app with Playwright and build the illustrated docs/USER-GUIDE.html.

Start the app first (`streamlit run app.py`), then run this script. PRICE_TRUTH_URL selects the app
(default http://127.0.0.1:8501). Screenshots are embedded, so the guide is one self-contained file.
"""
import base64
import os
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright

from price_truth.paths import ROOT

GUIDE = ROOT / "docs" / "USER-GUIDE.html"
DASHBOARD = "Is this a fair price?"


def shot(page, selector: str | None = None, *, clip_height: int | None = None) -> str:
    """JPEG screenshot of the viewport, an element, or the top of the page, as a data URI."""
    if selector:
        data = page.locator(selector).first.screenshot(type="jpeg", quality=82)
    elif clip_height:
        data = page.screenshot(type="jpeg", quality=82, clip={"x": 0, "y": 0, "width": 1440, "height": clip_height})
    else:
        data = page.screenshot(type="jpeg", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


def scroll_to(page, anchor: str) -> None:
    """Jump to a dashboard section as the sticky menu does, and let charts settle."""
    page.evaluate(f"document.getElementById('{anchor}').scrollIntoView({{block: 'start'}})")
    page.wait_for_timeout(1200)


def capture(base: str) -> dict[str, str]:
    """Screens used in the guide, in reading order."""
    images = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page.goto(f"{base}/")
        page.get_by_role("heading", name="Is your discount actually real?").wait_for(timeout=90_000)
        page.wait_for_timeout(2500)
        images["landing"] = shot(page)
        page.goto(f"{base}/dashboard")
        page.get_by_role("heading", name=DASHBOARD).wait_for(timeout=90_000)
        page.get_by_text("Fair price estimate").first.wait_for(timeout=90_000)
        page.wait_for_timeout(2500)
        images["overview"] = shot(page)
        page.locator(".pt-kpi").nth(3).hover()
        page.wait_for_timeout(400)
        images["tooltip"] = shot(page, clip_height=760)
        page.mouse.move(5, 5)
        for anchor in ["verdict", "discount", "history", "buy", "shrink"]:
            scroll_to(page, anchor)
            images[anchor] = shot(page)
        scroll_to(page, "packs")
        prices = page.get_by_label("Price (INR)")
        quantities = page.get_by_label("Quantity per pack")
        for index, (price, quantity) in enumerate([("45", "400"), ("105", "1000")]):
            prices.nth(index).fill(price)
            quantities.nth(index).fill(quantity)
        page.get_by_role("button", name="Compare value").click()
        page.get_by_text("is the best value").wait_for(timeout=30_000)
        scroll_to(page, "packs")
        images["packs"] = shot(page)
        for path, heading, key in [("food", "Look up a food pack", "food"),
                                   ("observations", "Track prices you have seen", "observations"),
                                   ("methods", "Methods, data and limits", "methods")]:
            page.goto(f"{base}/{path}")
            page.get_by_role("heading", name=heading).wait_for(timeout=60_000)
            page.wait_for_timeout(2500)
            images[key] = shot(page)
        mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        mobile.goto(f"{base}/dashboard")
        mobile.get_by_text("Fair price estimate").first.wait_for(timeout=90_000)
        mobile.wait_for_timeout(2000)
        images["mobile"] = shot(mobile)
        mobile.evaluate("document.getElementById('verdict').scrollIntoView({block: 'start'})")
        mobile.wait_for_timeout(1200)
        images["mobile_verdict"] = shot(mobile)
        browser.close()
    return images


def figure(src: str, caption: str, phone: bool = False) -> str:
    """One framed screenshot with a caption; click to enlarge."""
    return (f'<figure class="{"phone" if phone else ""}"><img src="{src}" alt="{escape(caption)}" loading="lazy">'
            f"<figcaption>{escape(caption)}</figcaption></figure>")


SECTIONS = [
    ("start", "Getting started", """
<p class="lead">Price Truth answers one question: <b>is the price in front of you fair?</b> The home page explains what
it does; type a product into its search box, or press <b>Open the dashboard</b>.</p>
{landing}
<p>Everything else happens on one dashboard that fills the screen:</p>
<ol class="steps">
<li><b>Choose the product</b> with the dropdowns: Platform → Category → Subcategory → Product. The product list shows
the most-rated listings first; type in <i>Filter by name</i> to narrow it (for example <code>cable</code> or
<code>kurta</code>).</li>
<li><b>Enter the prices you see.</b> <i>Listed MRP</i> is the crossed-out "was" price; <i>Price you see</i> is the
price you would pay. Both start at today's price for that listing. Every figure updates as soon as you change one.</li>
<li><b>Read the six headline cards</b>, then scroll, or use the section menu, for the detail behind each one.</li>
</ol>
{overview}
<div class="callout tip"><b>Hover for the "why"</b>Every headline card explains how its number was produced when you
hover over it (or tab to it with the keyboard).</div>
{tooltip}"""),
    ("cards", "The six headline cards", """
<div class="table-wrap"><table>
<tr><th>Card</th><th>What it tells you</th><th>Good sign</th></tr>
<tr><td>Price verdict</td><td>Whether your price is below, inside or above the range similar listings sold for.</td>
<td><span class="pill good">Below expected</span></td></tr>
<tr><td>Fair price estimate</td><td>What the model expects this product to cost, with the range that holds 90% of
real held-out prices.</td><td>Your price at or below the estimate</td></tr>
<tr><td>Advertised discount</td><td>The discount off MRP, compared with this product's usual discount over 90
days.</td><td>Close to usual is normal; far above usual deserves a second look</td></tr>
<tr><td>Real saving</td><td>How far the price is below its lowest price of the 30 days before the sale (the EU
Omnibus rule).</td><td><span class="pill good">5% or more</span></td></tr>
<tr><td>Inflation risk</td><td>A classifier's estimate that the discount is inflated, judged from the listing alone.
</td><td>Below the flag line</td></tr>
<tr><td>Best place to buy</td><td>The cheapest platform today including delivery and platform fees.</td>
<td>Shows how much you would save</td></tr>
</table></div>"""),
    ("fair", "Fair price", """
<p>The Fair price card places your price (diamond) on the model's expected range (box) with its estimate (line).
Below it, <b>why</b> the estimate is what it is: starting from a typical listing, each factor moved the estimate up
(blue) or down (coral) by the percentage shown. These are SHAP values from the trained model.</p>
{verdict}
<div class="callout warn"><b>Listed MRP matters</b>The model uses the MRP as an input, so an inflated MRP raises the
estimate. That is why the discount check below exists.</div>"""),
    ("discount", "Discount check", """
<p>Two checks in one card. <b>Primary:</b> the price-history rule: a discount is flagged when it is advertised as at
least 5 points bigger than usual while the price is less than 5% below its 30-day low. <b>Secondary:</b> a classifier's
risk dial with the flag threshold marked, and the factors that raised or lowered the risk. The classifier sees only the
listing, so when the two disagree, trust the rule.</p>
{discount}"""),
    ("history", "Price history and timing", """
<p>Daily prices for 180 days with sale events shaded; your price is the dashed line. Hover over the chart to read any
day. Beside it: how your price compares with the last 90 days, whether a sale is on or coming, and tomorrow's price.
The forecast is shown only when it beat "same as today" on held-out days; otherwise the app says so.</p>
{history}"""),
    ("buy", "Where to buy", """
<p>The same product on up to eight Indian platforms that sell its category, ranked by total cost. Delivery fees follow
each platform's free-delivery threshold; your own platform uses the price you typed. Use <i>Open</i> to search the
platform.</p>
{buy}"""),
    ("packs", "Pack value", """
<p>Compare two to four pack sizes. Prices are converted to per 100 g, per 100 ml or per item, so different sizes can be
compared fairly. The example compares 400 g for ₹45 with 1 kg for ₹105.</p>
{packs}"""),
    ("shrink", "Shrinkflation", """
<p>Pick a case to see how a pack shrank while its price stayed the same, and how much the real price per gram rose.
Cited cases link to the original news report; simulated timelines use generic names.</p>
{shrink}"""),
    ("export", "Saving your result", """
<p>The Export bar at the end of the dashboard: <b>Download PDF report</b> (verdict, range, explanation and limits),
<b>Download data (JSON)</b>, <b>Download offers (CSV)</b>, and a link to the original listing.</p>"""),
    ("food", "Food & packs", """
<p>Search a food product by name or barcode. You get its pack details from Open Food Facts, dated shop prices from
Open Prices, and a longer real price history example. <b>Compare this pack's value</b> sends the pack size to the
dashboard's Pack value section. Switch on <i>Saved responses only</i> to work offline.</p>
{food}"""),
    ("observations", "My observations", """
<p>Record prices you see in shops, one at a time or as a CSV. You then get the price history and forecast for one
exact pack, a comparison of your store quotes, and a pack-size change check. Your entries stay in your browser session;
download them to keep them.</p>
{observations}"""),
    ("methods", "Methods & data", """
<p>How accurate the model is by platform and category, which data is real and which is simulated, every source and
licence, and what the app cannot tell you.</p>
{methods}"""),
    ("mobile", "On a phone", """
<p>The dashboard stacks its cards into one column; the top menu moves behind the menu button.</p>
<div class="phones">{mobile}{mobile_verdict}</div>"""),
    ("glossary", "Words used in the app", """
<dl class="gloss">
<dt>MRP</dt><dd>Maximum retail price: the "was" price that discounts are quoted against.</dd>
<dt>Expected range</dt><dd>Prices the model considers normal for this listing; it holds 90% of real held-out
prices.</dd>
<dt>30-day low</dt><dd>The lowest price in the 30 days before the current sale began; the fair reference for a
discount.</dd>
<dt>SHAP</dt><dd>A method that splits a model's estimate into the contribution of each input.</dd>
<dt>Simulated / synthetic</dt><dd>Generated by a seeded simulator calibrated to published Indian e-commerce research,
not observed. Daily histories, offers and discount labels are simulated; listings and cited cases are real.</dd>
</dl>"""),
]


def build(images: dict[str, str]) -> str:
    """Assemble the guide from its sections and captured screens."""
    shots = {
        "landing": figure(images["landing"], "The home page: search a product or open the dashboard"),
        "overview": figure(images["overview"], "The dashboard: dropdowns, prices and the six headline cards"),
        "tooltip": figure(images["tooltip"], "Hovering a card explains how its figure is produced"),
        "verdict": figure(images["verdict"], "Fair price: verdict, expected range and what moved the estimate"),
        "discount": figure(images["discount"], "Discount check: history rule and classifier risk"),
        "history": figure(images["history"], "180-day price history with sale periods and timing signals"),
        "buy": figure(images["buy"], "Total cost by platform, cheapest first"),
        "packs": figure(images["packs"], "Pack value: the 1 kg pack is cheaper per 100 g"),
        "shrink": figure(images["shrink"], "A cited shrinkflation case"),
        "food": figure(images["food"], "Food & packs"),
        "observations": figure(images["observations"], "My observations"),
        "methods": figure(images["methods"], "Methods & data"),
        "mobile": figure(images["mobile"], "Dashboard on a phone", phone=True),
        "mobile_verdict": figure(images["mobile_verdict"], "Fair price section on a phone", phone=True),
    }
    toc = "".join(f'<a href="#{key}">{escape(title)}</a>' for key, title, _ in SECTIONS)
    body = "".join(f'<section id="{key}"><h2><span class="num">{i}</span>{escape(title)}</h2>'
                   f"{text.format(**shots)}</section>" for i, (key, title, text) in enumerate(SECTIONS, 1))
    return TEMPLATE.replace("{toc}", toc).replace("{body}", body)


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Price Truth User Guide</title>
<style>
:root{--purple:#5B3FD0;--ink:#141127;--muted:#5E5A70;--line:#E6E3F0;--bg:#F7F6FB;--card:#fff;--good:#16804B;
--good-bg:#EAF6EF;--tip:#F1EDFD;--warn:#FDF4E3}
*{box-sizing:border-box}html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 Inter,"Segoe UI",system-ui,sans-serif}
a{color:var(--purple)}
.layout{display:grid;grid-template-columns:250px minmax(0,1fr);min-height:100vh}
nav{position:sticky;top:0;height:100vh;overflow:auto;background:#fff;border-right:1px solid var(--line);padding:24px 16px}
nav .brand{font-weight:800;font-size:1.1rem;margin:0 8px 18px}nav .brand span{color:var(--purple)}
nav a{display:block;padding:6px 10px;border-radius:8px;color:var(--ink);text-decoration:none;font-size:.93rem}
nav a:hover,nav a:focus-visible{background:var(--bg);color:var(--purple)}
main{padding:8px clamp(16px,4vw,56px) 80px;max-width:1100px}
header{margin:28px 0 8px}header .eyebrow{text-transform:uppercase;letter-spacing:.09em;font-size:.74rem;font-weight:700;
color:var(--purple)}header h1{font-size:clamp(1.9rem,4vw,2.6rem);margin:.2em 0 .3em;letter-spacing:-.02em}
header p{color:var(--muted);margin:0;max-width:46rem}
section{padding-top:36px;scroll-margin-top:8px}
h2{font-size:1.55rem;margin:0 0 8px;display:flex;gap:12px;align-items:center;letter-spacing:-.01em}
h2 .num{display:inline-grid;place-items:center;width:34px;height:34px;border-radius:10px;background:var(--tip);
color:var(--purple);font-size:1rem;font-weight:800}
.lead{font-size:1.04rem}
.steps{padding-left:22px}.steps li{margin:6px 0}
figure{margin:16px 0 24px;border:1px solid var(--line);border-radius:14px;overflow:hidden;background:#fff;
box-shadow:0 8px 28px rgba(20,17,39,.07)}
figure img{width:100%;display:block;cursor:zoom-in}
figcaption{padding:10px 14px;font-size:.88rem;color:var(--muted);border-top:1px solid var(--line)}
.phones{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px}
figure.phone{max-width:320px;margin-inline:auto;border-radius:26px}
.callout{border-radius:12px;padding:12px 16px;margin:14px 0;font-size:.96rem}
.callout b{display:block}.callout.tip{background:var(--tip)}.callout.warn{background:var(--warn)}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:#fff}
table{border-collapse:collapse;width:100%;min-width:560px;font-size:.94rem}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--bg)}td:first-child{font-weight:600;white-space:nowrap}tr:last-child td{border-bottom:0}
.pill{padding:2px 10px;border-radius:999px;font-size:.84rem;font-weight:600}.pill.good{background:var(--good-bg);
color:var(--good)}
code{background:var(--tip);padding:1px 6px;border-radius:6px;font-size:.9em}
dl.gloss{display:grid;grid-template-columns:minmax(140px,220px) 1fr;border:1px solid var(--line);border-radius:12px;
overflow:hidden;background:#fff}
dl.gloss dt,dl.gloss dd{margin:0;padding:10px 14px;border-bottom:1px solid var(--line)}dl.gloss dt{font-weight:600;
background:var(--bg)}
footer{margin-top:48px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:.88rem}
.lightbox{position:fixed;inset:0;background:rgba(20,17,39,.85);display:none;align-items:center;justify-content:center;
padding:24px;z-index:50;cursor:zoom-out}.lightbox.open{display:flex}.lightbox img{max-height:92vh;max-width:96vw;
border-radius:10px}
@media (max-width:860px){.layout{grid-template-columns:1fr}nav{position:static;height:auto;border-right:0;
border-bottom:1px solid var(--line)}dl.gloss{grid-template-columns:1fr}}
</style></head><body><div class="layout">
<nav aria-label="Contents"><div class="brand">Price <span>Truth</span> guide</div>{toc}</nav>
<main><header><div class="eyebrow">User guide</div><h1>How to use Price Truth</h1>
<p>A step-by-step walkthrough of the dashboard and the detail pages, with what every number means.</p></header>
{body}
<footer>Price Truth · NMIMS M.Sc. Data Science, Group 11 · Academic project. Listings are real historical snapshots;
daily histories, offers and discount labels are simulated (see Methods &amp; data).</footer></main></div>
<div class="lightbox" id="lightbox" role="dialog" aria-label="Enlarged screenshot"><img alt=""></div>
<script>
const box=document.getElementById('lightbox'),big=box.querySelector('img');
document.querySelectorAll('figure img').forEach(i=>i.addEventListener('click',()=>{big.src=i.src;big.alt=i.alt;
box.classList.add('open')}));box.addEventListener('click',()=>box.classList.remove('open'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')box.classList.remove('open')});
document.querySelectorAll('nav a[href^="#"]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();
const t=document.getElementById(a.getAttribute('href').slice(1));window.scrollTo({top:t.getBoundingClientRect().top+window.scrollY-8,behavior:'smooth'})}));
</script></body></html>
"""


def main() -> None:
    """Capture the app and write the guide."""
    base = os.environ.get("PRICE_TRUTH_URL", "http://127.0.0.1:8501").rstrip("/")
    GUIDE.write_text(build(capture(base)), encoding="utf-8")
    print(f"Wrote {GUIDE} ({GUIDE.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    Path(GUIDE.parent).mkdir(parents=True, exist_ok=True)
    main()
