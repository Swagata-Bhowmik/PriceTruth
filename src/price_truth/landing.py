"""Landing page: what Price Truth does, with real coverage figures, and the way into the dashboard."""
import base64
from html import escape

import streamlit as st

DASHBOARD = "views/dashboard.py"

CSS = """
<style>
.block-container { max-width: 1240px; padding-top: 4.4rem; }
[data-testid="stMain"] { background:
  linear-gradient(180deg, rgba(255,251,245,0) 0, rgba(255,251,245,0) 70vh, #FFFBF5 112vh) local,
  linear-gradient(135deg,#E0D4F7 0%,#FFE8A3 50%,#FFB5A7 100%) local; }
[data-testid="stAppViewContainer"]::before { display:none; }
.lp-hero { position: relative; text-align: center; padding: 3.2rem 1rem 1.2rem; }
.lp-blob { position:fixed; border-radius:50%; filter: blur(52px); opacity:.5; pointer-events:none; z-index:-1; }
.lp-blob.a { width:440px; height:440px; background:#FFB5A7; top:8vh; left:-140px; animation: lpfloat1 16s ease-in-out infinite; }
.lp-blob.b { width:380px; height:380px; background:#E0D4F7; top:14vh; right:-120px; animation: lpfloat2 19s ease-in-out infinite; }
.lp-blob.c { width:320px; height:320px; background:#B4E7CE; bottom:-120px; left:40%; animation: lpfloat1 22s ease-in-out infinite reverse; }
@keyframes lpfloat1 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(40px,30px) scale(1.08); } }
@keyframes lpfloat2 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(-36px,24px) scale(.94); } }
.lp-badge { display:inline-flex; gap:.5rem; align-items:center; padding:.42rem 1rem; border-radius:999px;
  background: rgba(255,255,255,.55); border:1px solid rgba(255,255,255,.75); backdrop-filter: blur(10px);
  font-family:"IBM Plex Mono",monospace; font-size:.74rem; letter-spacing:.12em; text-transform:uppercase; color:#5D5A6B; }
.lp-badge i { width:8px; height:8px; border-radius:50%; background:#3E9E77; box-shadow:0 0 0 0 rgba(62,158,119,.6);
  animation: lppulse 2.2s infinite; }
@keyframes lppulse { 0% { box-shadow:0 0 0 0 rgba(62,158,119,.55); } 70% { box-shadow:0 0 0 10px rgba(62,158,119,0); } 100% { box-shadow:0 0 0 0 rgba(62,158,119,0); } }
.lp-hero h1 { font-size: clamp(2.6rem, 6.2vw, 4.9rem); line-height:1.02; letter-spacing:-.035em; margin:1.2rem auto .9rem;
  color:#3B3A48; max-width: 15ch; font-weight:800; }
.lp-hero h1 em { font-style:normal; background: linear-gradient(110deg,#7B68C8 0%,#FF8E7F 55%,#E2A93B 100%);
  -webkit-background-clip:text; background-clip:text; color:transparent; }
.lp-hero p { font-size: clamp(1.02rem, 1.6vw, 1.22rem); color:#55535F; max-width: 40rem; margin: 0 auto; line-height:1.6; }
.st-key-lp_search { max-width: 720px; margin: 1.6rem auto .2rem; background: rgba(255,255,255,.82); padding: .45rem .5rem .45rem 1.1rem;
  border-radius: 999px; border:1px solid rgba(255,255,255,.9); box-shadow: 0 18px 50px rgba(107,80,60,.16); backdrop-filter: blur(12px); }
.st-key-lp_search [data-testid="stTextInput"] input { background: transparent !important; border:none !important; font-size:1rem; }
.st-key-lp_search [data-baseweb="input"], .st-key-lp_search [data-baseweb="base-input"] { background: transparent !important; border:none !important; }
.st-key-lp_search button { animation: lpglow 2.8s ease-in-out infinite; }
@keyframes lpglow { 0%,100% { box-shadow: 0 8px 22px rgba(255,154,139,.35); } 50% { box-shadow: 0 8px 34px rgba(255,154,139,.7); } }
.lp-trust { display:flex; justify-content:center; gap:1.4rem; flex-wrap:wrap; margin-top:.9rem; color:#55535F; font-size:.9rem; }
.lp-trust span { display:inline-flex; gap:.4rem; align-items:center; }
.lp-trust img { display:inline-block; }
.lp-cue { text-align:center; margin-top:2.2rem; color:#77737F; font-size:.8rem; letter-spacing:.06em; }
.lp-cue img { display:block; margin:.35rem auto 0; animation: lpbob 1.8s ease-in-out infinite; }
@keyframes lpbob { 0%,100% { transform: translateY(0); } 50% { transform: translateY(7px); } }
.lp-stats { display:grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 2.4rem 0 1rem; }
.lp-stat { background: rgba(255,255,255,.66); border:1px solid rgba(255,255,255,.85); backdrop-filter: blur(12px);
  border-radius: 22px; padding: 1.2rem 1.3rem; box-shadow: 0 8px 32px rgba(107,80,60,.08); text-align:left;
  transition: transform .4s cubic-bezier(.16,1,.3,1), box-shadow .4s; }
.lp-stat:hover { transform: translateY(-5px); box-shadow: 0 20px 48px rgba(107,80,60,.15); }
.lp-stat b { display:block; font-size: clamp(1.7rem, 3vw, 2.3rem); color:#3B3A48; letter-spacing:-.02em; }
.lp-stat span { color:#5F5D6B; font-size:.88rem; }
.lp-sec { text-align:center; margin: 4.2rem auto 1.6rem; max-width: 46rem; }
.lp-sec .k { font-family:"IBM Plex Mono",monospace; font-size:.74rem; letter-spacing:.14em; text-transform:uppercase; color:#6450B5; }
.lp-sec h2 { font-size: clamp(1.8rem, 3.4vw, 2.6rem); margin:.4rem 0 .5rem; letter-spacing:-.03em; }
.lp-sec p { color:#5F5D6B; margin:0; font-size:1.04rem; }
.lp-two { display:grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; }
.lp-card { background:#fff; border:1px solid #ECE6DD; border-radius: 26px; padding: 1.6rem 1.7rem; position:relative; overflow:hidden;
  box-shadow: 0 8px 32px rgba(107,80,60,.07); transition: transform .45s cubic-bezier(.16,1,.3,1), box-shadow .45s; }
.lp-card:hover { transform: translateY(-6px) rotate(-.3deg); box-shadow: 0 24px 56px rgba(107,80,60,.15); }
.lp-card h3 { font-size:1.3rem; margin:.7rem 0 .4rem; }
.lp-card p { color:#5F5D6B; margin:0; line-height:1.6; }
.lp-icon { width:48px; height:48px; border-radius:16px; display:grid; place-items:center; }

.lp-price { display:flex; align-items:center; gap:.9rem; margin: 1.2rem 0 .3rem; font-weight:700; font-size:1.4rem; }
.lp-price s { color:#A09CAB; font-weight:600; }
.lp-price .arrow { color:#C8C2B6; }
.lp-price .off { font-size:.8rem; background:#FFEDE8; color:#B34A39; padding:.25rem .6rem; border-radius:999px; }
.lp-shrink { display:flex; align-items:flex-end; gap: 1rem; height: 120px; margin: 1.2rem 0 .3rem; }
.lp-shrink div { flex:1; border-radius: 14px 14px 6px 6px; display:flex; align-items:flex-end; justify-content:center;
  padding-bottom:.45rem; font-weight:700; color:#3B3A48; font-size:.9rem; transform-origin: bottom;
  animation: lpgrow 1.4s cubic-bezier(.16,1,.3,1) both; }
.lp-shrink div:nth-child(1) { height:100%; background: linear-gradient(180deg,#E0D4F7,#CBBBF0); }
.lp-shrink div:nth-child(2) { height:87%; background: linear-gradient(180deg,#FFE8A3,#F8D774); animation-delay:.15s; }
@keyframes lpgrow { from { transform: scaleY(.1); opacity:.2; } to { transform: scaleY(1); opacity:1; } }
.lp-src { font-size:.78rem; color:#77737F; margin-top:.6rem !important; }
.lp-grid { display:grid; grid-template-columns: repeat(3, 1fr); gap: 1.1rem; }
a.pt-feature { display:block; text-decoration:none; color:inherit; background: rgba(255,255,255,.92); border:1px solid #ECE6DD;
  border-radius: 24px; padding: 1.35rem 1.4rem 1.25rem; box-shadow: 0 8px 28px rgba(107,80,60,.06);
  transition: transform .45s cubic-bezier(.16,1,.3,1), box-shadow .45s, border-color .3s; }
a.pt-feature:hover, a.pt-feature:focus-visible { transform: translateY(-7px); box-shadow: 0 26px 56px rgba(107,80,60,.15);
  border-color:#E0D4F7; }
a.pt-feature:hover .lp-icon { transform: rotate(-8deg) scale(1.08); }
.lp-icon { transition: transform .45s cubic-bezier(.16,1,.3,1); }
a.pt-feature h4 { margin:.9rem 0 .3rem; font-size:1.08rem; color:#3B3A48; }
a.pt-feature p { margin:0; color:#5F5D6B; font-size:.93rem; line-height:1.55; }
a.pt-feature .go { display:inline-block; margin-top:.8rem; font-size:.84rem; font-weight:600; color:#6450B5; }
a.pt-feature:hover .go { color:#E06B58; }
.lp-tag { display:inline-block; font-family:"IBM Plex Mono",monospace; font-size:.66rem; letter-spacing:.1em; padding:.2rem .55rem;
  border-radius: 6px; margin-left:.5rem; vertical-align: middle; }
.lp-steps { display:grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; position:relative; }
.lp-steps::before { content:""; position:absolute; top: 34px; left: 12%; right: 12%; height: 2px;
  background: linear-gradient(90deg,#E0D4F7,#FFB5A7,#FFE8A3); z-index:0; }
.lp-step { text-align:center; position:relative; z-index:1; padding: 0 .4rem; }
.lp-step .n { width:68px; height:68px; margin:0 auto .9rem; border-radius:50%; background:#fff; display:grid; place-items:center;
  font-weight:800; font-size:1.3rem; color:#7B68C8; border:1px solid #ECE6DD; box-shadow: 0 10px 26px rgba(107,80,60,.1);
  transition: transform .4s cubic-bezier(.16,1,.3,1); }
.lp-step:hover .n { transform: scale(1.1) rotate(8deg); }
.lp-step h4 { margin:0 0 .3rem; font-size:1.02rem; }
.lp-step p { margin:0; color:#5F5D6B; font-size:.9rem; line-height:1.5; }
.lp-proof { display:grid; grid-template-columns: repeat(3, 1fr); gap: 1.1rem; }
.lp-proof .lp-card b { display:block; font-size:1.55rem; line-height:1.2; letter-spacing:-.02em; margin:.8rem 0 .35rem; color:#3B3A48; }
.lp-cta { margin: 4.4rem 0 1rem; border-radius: 32px; padding: 2.8rem 2rem 1.4rem; text-align:center; position:relative; overflow:hidden;
  background: linear-gradient(135deg,#E0D4F7 0%,#FFE8A3 55%,#FFB5A7 100%); box-shadow: 0 24px 60px rgba(107,80,60,.16); }
.lp-cta h2 { font-size: clamp(1.7rem, 3.2vw, 2.4rem); margin:0 0 .5rem; letter-spacing:-.03em; }
.lp-cta p { margin:0 auto; max-width: 36rem; color:#4F4D5A; }
.st-key-lp_cta { max-width: 540px; margin: -4.6rem auto 0; position: relative; z-index: 2; padding-bottom: 1.6rem; }
.lp-foot { display:flex; justify-content:space-between; flex-wrap:wrap; gap:1rem; margin: 2.6rem 0 0; padding: 1.2rem 0 0;
  border-top:1px solid #ECE6DD; color:#6A6775; font-size:.85rem; }
.lp-foot b { color:#3B3A48; }
@media (max-width: 900px) { .lp-stats, .lp-grid, .lp-proof { grid-template-columns: 1fr 1fr; }
  .lp-two { grid-template-columns: 1fr; } .lp-steps { grid-template-columns: 1fr 1fr; } .lp-steps::before { display:none; } }
@media (max-width: 560px) { .lp-stats, .lp-grid, .lp-proof { grid-template-columns: 1fr; } }
</style>
"""

ICONS = {  # Stroke icons (24 px grid).
    "verdict": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/>',
    "shield": '<path d="M12 3l7 3v6c0 4.5-3 7.6-7 9-4-1.4-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "chart": '<path d="M4 19h16"/><path d="M5 15l4-5 4 3 6-7"/>',
    "store": '<path d="M4 9l1.5-5h13L20 9"/><path d="M4 9h16v11H4z"/><path d="M9 20v-6h6v6"/>',
    "scale": '<path d="M12 4v16M7 20h10M5 8h14"/><path d="M5 8l-3 6h6zM19 8l-3 6h6z"/>',
    "shrink": '<path d="M4 6h10v10H4z"/><path d="M14 12h6M17 9l3 3-3 3"/>',
    "tag": '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.4"/>',
    "check": '<path d="M5 12l4 4 10-10"/>',
    "down": '<path d="M6 9l6 6 6-6"/>',
}
FEATURES = [  # (icon, tint, ink, title, tag, text, section anchor)
    ("verdict", "#EEE7FB", "#7B68C8", "Fair price verdict", "CORE",
     "A model trained on 21k real listings estimates what the product should cost and SHAP shows why.", "verdict"),
    ("shield", "#FFEDE8", "#E06B58", "Discount check", "RULE + ML",
     "The EU 30-day reference-price rule and a classifier tell you if the discount is real.", "discount"),
    ("chart", "#FFF4D6", "#B8860B", "Price history & timing", "180 DAYS",
     "See how the price moved around sale events and whether to buy now or wait.", "history"),
    ("store", "#E7F6EE", "#3E9E77", "Where to buy", "8 PLATFORMS",
     "Total cost on Amazon, Flipkart, Croma, Myntra and more, delivery fees included.", "buy"),
    ("scale", "#EAF1FA", "#6B8DBF", "Pack value", "UNIT PRICE",
     "Compare pack sizes per 100 g, 100 ml or item to find the real best value.", "packs"),
    ("shrink", "#FBEFF7", "#B4568F", "Shrinkflation", "CITED",
     "Documented Indian cases where the pack shrank but the price did not.", "shrink"),
]
STEPS = [("1", "Pick a product", "Choose platform, category and product from the dropdowns."),
         ("2", "Enter the price", "Type the MRP and the price you see. Everything updates live."),
         ("3", "Read the evidence", "Verdict, discount check, history and cheapest platform, each explained."),
         ("4", "Decide", "Buy, wait for a sale, or pick another pack. Save the report as a PDF.")]


def svg(name: str, ink: str = "#7B68C8", size: int = 16) -> str:
    """A stroke icon as an inline image (st.html sanitises raw <svg> elements away)."""
    markup = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{ink}" stroke-width="1.9" '
              f'stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')
    data = base64.b64encode(markup.encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{data}" width="{size}" height="{size}" alt="" aria-hidden="true">'


def icon(name: str, ink: str, tint: str) -> str:
    """A rounded tile holding one stroke icon."""
    return f'<div class="lp-icon" style="background:{tint}">{svg(name, ink, 24)}</div>'


def stat_html(value: float, label: str, decimals: int = 0, suffix: str = "") -> str:
    """A counter that animates up to a real figure (the final value is in the markup for no-script readers)."""
    shown = f"{value:,.{decimals}f}{suffix}"
    return (f'<div class="lp-stat pt-reveal"><b data-count="{value}" data-decimals="{decimals}" data-suffix="{suffix}">'
            f'{shown}</b><span>{escape(label)}</span></div>')


def hero() -> None:
    """Headline, a product search that opens the dashboard, and the trust line."""
    st.html('<section class="lp-hero"><div class="lp-blob a"></div><div class="lp-blob b"></div><div class="lp-blob c"></div>'
            '<span class="lp-badge"><i></i>Explainable price checks for Indian shoppers</span>'
            '<h1>Is your discount actually <em>real?</em></h1>'
            '<p>Price Truth checks an online price against what similar products really sold for, tests the discount '
            'against its own price history, and finds where it is cheapest. Every answer shows its evidence.</p></section>')
    with st.container(key="lp_search"), st.form("lp_search_form", border=False):
        columns = st.columns([5, 1.6], vertical_alignment="center")
        query = columns[0].text_input("Search a product", placeholder="Try “HDMI cable”, “earphones” or “kurta”…",
                                      label_visibility="collapsed")
        if columns[1].form_submit_button("Check price", type="primary", width="stretch"):
            open_dashboard(query)
    st.html(f'<div class="lp-trust"><span>{svg("check")}Real Amazon & Flipkart listings</span>'
            f'<span>{svg("check")}Explained with SHAP</span><span>{svg("check")}Honest about its limits</span></div>'
            f'<div class="lp-cue">Scroll to explore{svg("down", "#77737F", 22)}</div>')


def open_dashboard(query: str = "") -> None:
    """Carry the search into the dashboard's dropdown filter and switch page."""
    if query.strip():
        st.session_state.update(dash_platform="All", dash_category="All", dash_subcategory="All",
                                dash_filter=query.strip())
        st.session_state.pop("dash_product", None)
    st.switch_page(DASHBOARD)


def stats(listings: int, r2: float | None, cited: int) -> None:
    """Real coverage and accuracy figures, counted up on arrival."""
    cards = [stat_html(listings, "real Amazon & Flipkart listings"), stat_html(8, "Indian platforms compared")]
    if r2 is not None:
        cards.append(stat_html(r2, "R² on 4,269 unseen listings", 2))
    cards.append(stat_html(cited, "cited shrinkflation cases"))
    st.html(f'<div class="lp-stats">{"".join(cards)}</div>')


def problem() -> None:
    """The two tricks the product exposes, with a real cited shrinkflation case."""
    st.html(f'''<div class="lp-sec pt-reveal"><div class="k">The problem</div><h2>Two quiet tricks cost shoppers money</h2>
<p>One is loud and sits on every sale banner. The other hides in the pack.</p></div>
<div class="lp-two">
 <div class="lp-card pt-reveal">{icon("tag", "#E06B58", "#FFEDE8")}<h3>Inflated “MRP” discounts</h3>
  <p>A discount is only as honest as the price it is measured from. Raise the MRP and a normal price looks like a bargain.</p>
  <div class="lp-price"><s>₹1,999</s><span class="arrow">→</span><span>₹299</span><span class="off">“85% off”</span></div>
  <p class="lp-src">Illustration. Price Truth compares the price with its own 30-day low instead.</p></div>
 <div class="lp-card pt-reveal">{icon("shrink", "#B4568F", "#FBEFF7")}<h3>Silent shrinkflation</h3>
  <p>The price stays the same while the pack gets smaller, so you pay more per gram without noticing.</p>
  <div class="lp-shrink"><div>155 g · ₹10</div><div>135 g · ₹10</div></div>
  <p class="lp-src">Vim bar, reported by Bloomberg / Financial Express, May 2022: 13% less soap, a 15% hidden price rise.</p></div>
</div>''')


def features() -> None:
    """Every dashboard section as a card that links straight to it."""
    cards = "".join(
        f'<a class="pt-feature pt-reveal" href="dashboard#{anchor}" target="_self">{icon(name, ink, tint)}'
        f'<h4>{escape(title)}<span class="lp-tag" style="background:{tint};color:{ink}">{escape(tag)}</span></h4>'
        f'<p>{escape(text)}</p><span class="go">Open in dashboard →</span></a>'
        for name, tint, ink, title, tag, text, anchor in FEATURES)
    st.html('<div class="lp-sec pt-reveal"><div class="k">One dashboard</div><h2>Six answers on one screen</h2>'
            '<p>Choose a product once. Everything below is computed for it, and every number explains itself.</p></div>'
            f'<div class="lp-grid">{cards}</div>')


def how_it_works() -> None:
    """Four steps from product to decision."""
    steps = "".join(f'<div class="lp-step pt-reveal"><div class="n">{n}</div><h4>{escape(t)}</h4><p>{escape(d)}</p></div>'
                    for n, t, d in STEPS)
    st.html('<div class="lp-sec pt-reveal"><div class="k">How it works</div><h2>From a price tag to a decision</h2></div>'
            f'<div class="lp-steps">{steps}</div>')


def proof(audit: dict | None) -> None:
    """Why the numbers can be trusted, from the saved evaluation reports."""
    overall = (audit or {}).get("overall", {})
    error = f"{overall['median_absolute_percentage_error']:.0f}%" if overall else "—"
    st.html(f'''<div class="lp-sec pt-reveal"><div class="k">Built on evidence</div><h2>Transparent by design</h2>
<p>Measured on products the model never saw, with real and simulated data kept apart.</p></div>
<div class="lp-proof">
 <div class="lp-card pt-reveal">{icon("verdict", "#7B68C8", "#EEE7FB")}<b>{error}</b><p>typical error on held-out
  listings. Categories where the model is weak are flagged on the dashboard.</p></div>
 <div class="lp-card pt-reveal">{icon("shield", "#3E9E77", "#E7F6EE")}<b>Real vs simulated</b><p>Listings are real. Daily
  histories, offers and discount labels are simulated from published research, and every row says which.</p></div>
 <div class="lp-card pt-reveal">{icon("check", "#E06B58", "#FFEDE8")}<b>No guessing</b><p>When the data cannot support an
  answer, such as a forecast, the app says so instead of inventing one.</p></div>
</div>''')


def cta() -> None:
    """Closing call to action and footer."""
    st.html('<div class="lp-cta pt-reveal"><h2>Ready to check a price?</h2><p>Open the dashboard, pick a product and '
            'see the verdict, the discount check and the cheapest platform in one view.</p>'
            '<div style="height:4.4rem"></div></div>')
    with st.container(key="lp_cta"):
        columns = st.columns(2)
        if columns[0].button("Open the dashboard", type="primary", width="stretch"):
            open_dashboard()
        if columns[1].button("Read the user guide", icon=":material/menu_book:", width="stretch"):
            st.switch_page("views/user-guide.py")
    st.html('<div class="lp-foot"><span><b>Price Truth</b> · NMIMS M.Sc. Data Science, Group 11 · Academic project</span>'
            '<span>Data: Amazon (CC BY-NC-SA 4.0), Flipkart (CC BY-SA 4.0), Open Food Facts & Open Prices (ODbL)</span></div>')


def landing_page(listings: int, audit: dict | None, cited: int) -> None:
    """The full landing page."""
    st.html(CSS)
    hero()
    r2 = audit["overall"]["r2"] if audit else None
    stats(listings, r2, cited)
    problem()
    features()
    how_it_works()
    proof(audit)
    cta()
