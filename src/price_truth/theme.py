"""Shared visual layer: design tokens, CSS, motion, chart styling and small display components. No business logic."""
from html import escape

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# Pastel palette carried over from the design prototype (lavender → butter → peach on cream). Text colours are
# darker than the pastels so every label meets WCAG AA contrast.
PURPLE, LAVENDER, CORAL, MINT, INK, MUTED = "#6B8DBF", "#E0D4F7", "#F08A7A", "#3E9E77", "#3B3a48", "#62606F"
PEACH, BUTTER, VIOLET, AMBER, GRID = "#FFB5A7", "#FFE8A3", "#7B68C8", "#E2A93B", "#EFEAE2"
TONES = {  # tone: (accent, background, icon). Icons and titles repeat the meaning conveyed by colour.
    "good": ("#3E9E77", "#E7F6EE", "✓"),
    "neutral": ("#7B68C8", "#F1ECFC", "≈"),
    "bad": ("#E06B58", "#FFEDE8", "!"),
    "muted": ("#8A8797", "#F4F2EF", "i"),
}
SOURCE_BADGES = {  # Where a number came from, shown next to the result (colours meet WCAG AA contrast).
    "historical": ("Historical catalogue", "#5A46B0", "#F1ECFC"),
    "live": ("Live response", "#1F7550", "#E7F6EE"),
    "cached": ("Saved response", "#7A5410", "#FFF4D6"),
    "user": ("Your entry", "#3A5F94", "#EAF1FA"),
    "reported": ("Published report", "#4A4757", "#F2F0EC"),
}

CSS = """
<style>
:root { --pt-ink:#3B3A48; --pt-muted:#62606F; --pt-line:#ECE6DD; --pt-bg:#FFFBF5; --pt-card:#FFFFFF;
  --pt-blue:#6B8DBF; --pt-violet:#7B68C8; --pt-peach:#FFB5A7; --pt-peach-deep:#FF9A8B; --pt-mint:#B4E7CE;
  --pt-butter:#FFE8A3; --pt-lav:#E0D4F7;
  --pt-hero: linear-gradient(135deg,#E0D4F7 0%,#FFE8A3 50%,#FFB5A7 100%);
  --pt-button: linear-gradient(135deg,#FFB5A7 0%,#FF9A8B 100%);
  --pt-shadow: 0 8px 32px rgba(107,80,60,.07); --pt-lift: 0 18px 44px rgba(107,80,60,.14);
  --pt-radius: 22px; --pt-ease: cubic-bezier(.16,1,.3,1); }
html { scroll-behavior: smooth; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--pt-bg); }
[data-testid="stAppViewContainer"]::before { content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
  background: radial-gradient(900px 500px at 8% -10%, rgba(224,212,247,.55), transparent 60%),
              radial-gradient(800px 480px at 100% 0%, rgba(255,232,163,.35), transparent 60%),
              radial-gradient(900px 600px at 90% 110%, rgba(255,181,167,.28), transparent 60%); }
[data-testid="stHeader"] { background: rgba(255,251,245,.72); backdrop-filter: blur(14px) saturate(140%);
  border-bottom: 1px solid rgba(236,230,221,.8); }
[data-testid="stHeader"] a, [data-testid="stHeader"] button { border-radius: 999px !important; }
.block-container { padding: 4.8rem clamp(1rem, 2.6vw, 2.6rem) 3rem; max-width: 1680px; position: relative; z-index: 1; }
h1, h2, h3 { letter-spacing: -0.02em; color: var(--pt-ink); }
[id] { scroll-margin-top: 7.5rem; }

/* Cards: keyed containers (st-key-card_*) become rounded white panels that lift on hover. */
[class*="st-key-card_"], .st-key-dash_selector { background: rgba(255,255,255,.86); border: 1px solid var(--pt-line) !important;
  border-radius: var(--pt-radius) !important; box-shadow: var(--pt-shadow); padding: 1.05rem 1.15rem 1rem !important;
  transition: box-shadow .35s var(--pt-ease), transform .35s var(--pt-ease); }
[class*="st-key-card_"]:hover { box-shadow: var(--pt-lift); transform: translateY(-2px); }
[class*="st-key-card_"] [data-testid="stPlotlyChart"] { background: transparent !important; border: none !important;
  padding: 0 !important; }

/* Buttons: primary actions use the peach gradient with dark text (contrast > 7:1). */
button[kind="primary"], button[kind="primaryFormSubmit"], button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--pt-button) !important; color: #3A1F1A !important; border: none !important; border-radius: 999px !important;
  font-weight: 650 !important; box-shadow: 0 8px 22px rgba(255,154,139,.35); transition: transform .25s var(--pt-ease), box-shadow .25s; }
button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover { transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(255,154,139,.5); }
button[kind="secondary"], button[data-testid="stBaseButton-secondary"], [data-testid="stLinkButton"] a {
  border-radius: 999px !important; transition: transform .25s var(--pt-ease); }
button[kind="secondary"]:hover, [data-testid="stLinkButton"] a:hover { transform: translateY(-2px); }
[data-baseweb="select"] > div, [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {
  border-radius: 14px !important; }
[data-testid="stNumberInputStepUp"], [data-testid="stNumberInputStepDown"] { display:none; }

.pt-eyebrow { text-transform:uppercase; letter-spacing:.12em; font-size:.7rem; font-weight:600;
  color: #6450B5; font-family: "IBM Plex Mono", ui-monospace, monospace; margin-bottom:.15rem; }
.pt-intro { display:flex; justify-content:space-between; align-items:flex-end; gap:1.5rem; flex-wrap:wrap; margin:.1rem 0 .9rem; }
.pt-intro h1 { font-size: clamp(1.5rem, 2.4vw, 2rem); margin:0; padding:0; line-height:1.15; }
.pt-intro p { margin:.3rem 0 0; color: var(--pt-muted); max-width: 46rem; }
.pt-grad { background: linear-gradient(120deg,#7B68C8 0%,#FF9A8B 60%,#E2A93B 100%); -webkit-background-clip:text;
  background-clip:text; color: transparent; }
.pt-chips { display:flex; gap:.5rem; flex-wrap:wrap; }
.pt-chip { background: rgba(255,255,255,.8); border:1px solid var(--pt-line); border-radius: 999px; padding:.35rem .85rem;
  font-size:.84rem; color: var(--pt-muted); white-space:nowrap; }
.pt-chip b { color: var(--pt-ink); font-weight:650; }
.pt-card-head { display:flex; justify-content:space-between; align-items:baseline; gap:.2rem .6rem; flex-wrap:wrap; margin:-.1rem 0 .5rem; }
.pt-card-head h3 { font-size:1.08rem; margin:0; padding:0; }
.pt-card-head span { font-size:.8rem; color: var(--pt-muted); }
.pt-section { margin: 1.6rem 0 .6rem; }
.pt-section h2 { font-size: 1.3rem; margin: 0; padding: 0; }
.pt-section p { margin: .25rem 0 0; color: var(--pt-muted); max-width: 56rem; }
[data-testid="stElementContainer"]:has(.pt-nav) { position: sticky; top: 3.75rem; z-index: 50; }
.pt-nav { display:flex; gap:.3rem; flex-wrap:wrap; width:fit-content; margin:.5rem 0 .3rem; padding:.35rem;
  background: rgba(255,255,255,.78); backdrop-filter: blur(12px); border:1px solid var(--pt-line); border-radius:999px;
  box-shadow: var(--pt-shadow); }
.pt-nav a { text-decoration:none; color: var(--pt-muted); font-size:.85rem; font-weight:560; padding:.35rem .9rem;
  border-radius: 999px; transition: all .2s var(--pt-ease); }
.pt-nav a:hover, .pt-nav a:focus-visible { color: #3A1F1A; background: var(--pt-button); }

/* Headline cards with hover explanations. */
[data-testid="stElementContainer"]:has(.pt-kpis) { position: relative; z-index: 60; }
.pt-kpis { display:grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap:.85rem; margin:.3rem 0 .2rem; }
.pt-kpi { position:relative; background: rgba(255,255,255,.9); border:1px solid var(--pt-line); border-radius: 20px;
  padding: .9rem 1.05rem .85rem; box-shadow: var(--pt-shadow); outline:none; overflow: visible;
  transition: transform .35s var(--pt-ease), box-shadow .35s var(--pt-ease); }
.pt-kpi::before { content:""; position:absolute; left:1rem; right:1rem; top:0; height:3px; border-radius:0 0 4px 4px;
  background: var(--accent, var(--pt-line)); }
.pt-kpi:hover, .pt-kpi:focus-visible { transform: translateY(-4px); box-shadow: var(--pt-lift); }
.pt-kpi-label { font-size:.72rem; text-transform:uppercase; letter-spacing:.07em; color: var(--pt-muted);
  font-weight:600; display:flex; gap:.35rem; align-items:center; }
.pt-kpi-label span { font-size:.68rem; border:1px solid var(--pt-line); border-radius:50%; width:1rem; height:1rem;
  display:inline-flex; align-items:center; justify-content:center; text-transform:none; }
.pt-kpi-value { font-size:1.32rem; font-weight:700; color: var(--pt-ink); margin:.3rem 0 .1rem; line-height:1.15; }
.pt-kpi-note { font-size:.8rem; color: var(--pt-muted); }
.pt-kpi-tip { visibility:hidden; opacity:0; position:absolute; left:.4rem; min-width: 240px; top: calc(100% + .5rem);
  background: rgba(59,58,72,.96); color:#fff; font-size:.8rem; line-height:1.45; padding:.65rem .8rem; border-radius:14px;
  z-index:40; transform: translateY(-4px); transition: opacity .2s, transform .25s var(--pt-ease);
  box-shadow: 0 14px 34px rgba(59,58,72,.3); pointer-events:none; }
.pt-kpi:hover .pt-kpi-tip, .pt-kpi:focus-visible .pt-kpi-tip { visibility:visible; opacity:1; transform:none; }

.pt-product { display:flex; gap:1rem; align-items:center; justify-content:space-between; flex-wrap:wrap; margin:.1rem 0; }
.pt-product h3 { font-size:1.05rem; margin:0; padding:0; line-height:1.35; font-weight:650; }
.pt-tags { display:flex; gap:.4rem; flex-wrap:wrap; margin-top:.35rem; }
.pt-tag { font-size:.75rem; color: var(--pt-muted); background: #FBF8F3; border:1px solid var(--pt-line);
  padding:.15rem .6rem; border-radius: 999px; }
.pt-tag.real { color:#1F7550; background:#E7F6EE; border-color:#C9EBD9; }
.pt-tag.sim { color:#7A5410; background:#FFF4D6; border-color:#F6E2A8; }
.pt-verdict { border-radius: 18px; padding: .85rem 1.05rem; display:flex; gap: .85rem; align-items:flex-start;
  border:1px solid var(--line); background: var(--bg); margin: .15rem 0 .6rem; }
.pt-verdict .pt-icon { flex: 0 0 2rem; height:2rem; border-radius:50%; background: var(--accent); color:#fff;
  font-weight:700; display:flex; align-items:center; justify-content:center; font-size:1rem;
  box-shadow: 0 6px 14px var(--line); }
.pt-verdict h3 { margin:0 0 .15rem; font-size:1.02rem; color: var(--pt-ink); padding:0; }
.pt-verdict p { margin:0; color: var(--pt-ink); font-size:.92rem; }
.pt-badge { display:inline-block; font-size:.8rem; font-weight:600; padding:.15rem .7rem; border-radius:999px; }
.pt-card-title { font-weight:600; font-size:1.05rem; color:var(--pt-ink); margin:0 0 .2rem; line-height:1.35; }
.pt-meta { color: var(--pt-muted); font-size:.88rem; margin:0; }
.pt-empty { border:1.5px dashed #E4DCCF; border-radius:18px; padding:1rem 1.15rem; background:#FFFDF9; }
.pt-empty h4 { margin:0 0 .25rem; font-size:.98rem; color:var(--pt-ink); padding:0; }
.pt-empty p { margin:0; color: var(--pt-muted); }
.pt-stat { font-size:1.6rem; font-weight:700; color:var(--pt-ink); line-height:1.1; }
.pt-stat-label { color:var(--pt-muted); font-size:.85rem; }
.pt-footer { margin-top: 2rem; padding-top: 1rem; border-top:1px solid var(--pt-line); color: var(--pt-muted); font-size:.84rem; }
[data-testid="stMetric"] { background: rgba(255,255,255,.9); border:1px solid var(--pt-line); border-radius: 16px; padding: .65rem .9rem; }
[data-testid="stMetricValue"] { font-weight:700; font-size: 1.3rem; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #5F5D6B !important; opacity: 1 !important; }
[data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]) { overflow: visible !important; }
[data-testid="stPlotlyChart"] { background: rgba(255,255,255,.92); border:1px solid var(--pt-line); border-radius: 18px;
  padding: .3rem .45rem; }
a:focus-visible, button:focus-visible, [role="tab"]:focus-visible, .pt-kpi:focus-visible { outline: 3px solid #A795E8 !important;
  outline-offset: 2px; }

/* Custom cursor: only switched on by the script, only for a fine pointer, never with reduced motion. */
.pt-cursor-dot, .pt-cursor-ring { position: fixed; top: 0; left: 0; pointer-events: none; z-index: 2147483000;
  border-radius: 50%; transform: translate(-50%, -50%); opacity: 0; transition: opacity .2s; }
.pt-cursor-dot { width: 8px; height: 8px; background: #FF8E7F; }
.pt-cursor-ring { width: 34px; height: 34px; border: 1.6px solid rgba(123,104,200,.55); background: rgba(224,212,247,.12);
  transition: width .25s var(--pt-ease), height .25s var(--pt-ease), background .25s, border-color .25s, opacity .2s; }
html.pt-cursor-on .pt-cursor-dot, html.pt-cursor-on .pt-cursor-ring { opacity: 1; }
html.pt-cursor-on.pt-cursor-hover .pt-cursor-ring { width: 54px; height: 54px; background: rgba(255,181,167,.18);
  border-color: rgba(255,154,139,.7); }
html.pt-cursor-on.pt-cursor-down .pt-cursor-ring { width: 24px; height: 24px; }
.pt-progress { position: fixed; top: 0; left: 0; height: 3px; width: 0; z-index: 1000002;
  background: linear-gradient(90deg,#7B68C8,#FF9A8B,#FFD36E); border-radius: 0 3px 3px 0; pointer-events:none; }
.pt-reveal { opacity: 0; transform: translateY(18px); transition: opacity .7s var(--pt-ease), transform .7s var(--pt-ease); }
.pt-reveal.pt-in { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; }
  *, *::before, *::after { animation: none !important; transition: none !important; }
  .pt-reveal { opacity: 1; transform: none; } .pt-cursor-dot, .pt-cursor-ring { display: none; } }
@media (max-width: 640px) { .block-container { padding-top: 4rem; }
  [data-testid="stElementContainer"]:has(.pt-nav) { top: 3.4rem; }
  .pt-kpis { grid-template-columns: 1fr 1fr; } .pt-kpi-value { font-size: 1.15rem; } }
</style>
"""

# Motion layer. Runs in the page itself (Streamlit's `unsafe_allow_javascript`); guarded so reruns never stack
# listeners. Elements Streamlit adds later are picked up by a MutationObserver.
FX = """
<script>
(() => {
  if (window.__ptfx) return; window.__ptfx = true;
  const doc = document, root = doc.documentElement;
  const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fine = matchMedia('(pointer: fine)').matches;
  const bar = doc.createElement('div'); bar.className = 'pt-progress'; doc.body.appendChild(bar);
  const scroller = () => doc.querySelector('[data-testid="stMain"]') || doc.scrollingElement;
  const onScroll = (e) => { const s = e && e.target && e.target.scrollHeight ? e.target : scroller();
    const max = s.scrollHeight - s.clientHeight; bar.style.width = (max > 0 ? 100 * s.scrollTop / max : 0) + '%'; };
  doc.addEventListener('scroll', onScroll, true);
  if (fine && !calm) {
    const dot = doc.createElement('div'), ring = doc.createElement('div');
    dot.className = 'pt-cursor-dot'; ring.className = 'pt-cursor-ring'; doc.body.append(dot, ring);
    let x = innerWidth / 2, y = innerHeight / 2, rx = x, ry = y;
    addEventListener('mousemove', (e) => { x = e.clientX; y = e.clientY; root.classList.add('pt-cursor-on');
      dot.style.transform = `translate(${x - 4}px, ${y - 4}px)`; }, {passive: true});
    addEventListener('mouseout', (e) => { if (!e.relatedTarget) root.classList.remove('pt-cursor-on'); });
    addEventListener('mousedown', () => root.classList.add('pt-cursor-down'));
    addEventListener('mouseup', () => root.classList.remove('pt-cursor-down'));
    const hot = 'a, button, [role="button"], [role="option"], [data-baseweb="select"], .pt-kpi, .pt-feature, summary';
    doc.addEventListener('mouseover', (e) => root.classList.toggle('pt-cursor-hover', !!e.target.closest(hot)));
    const loop = () => { rx += (x - rx) * .18; ry += (y - ry) * .18;
      ring.style.transform = `translate(${rx}px, ${ry}px) translate(-50%, -50%)`; requestAnimationFrame(loop); };
    dot.style.transform = 'translate(-50%,-50%)'; ring.style.left = '0'; ring.style.top = '0'; loop();
  }
  const seen = new WeakSet();
  const io = 'IntersectionObserver' in window ? new IntersectionObserver((items) => items.forEach((it) => {
    if (it.isIntersecting) { it.target.classList.add('pt-in'); io.unobserve(it.target); } }), {threshold: .12}) : null;
  const count = (el) => { const end = parseFloat(el.dataset.count), dec = +(el.dataset.decimals || 0);
    const fmt = (v) => v.toLocaleString('en-IN', {minimumFractionDigits: dec, maximumFractionDigits: dec});
    if (calm) { el.textContent = fmt(end) + (el.dataset.suffix || ''); return; }
    const t0 = performance.now(), dur = 1400;
    const step = (t) => { const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      el.textContent = fmt(end * e) + (el.dataset.suffix || ''); if (k < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step); };
  const scan = () => {
    doc.querySelectorAll('.pt-reveal').forEach((el) => { if (!seen.has(el)) { seen.add(el);
      if (io && !calm) io.observe(el); else el.classList.add('pt-in'); } });
    doc.querySelectorAll('[data-count]').forEach((el) => { if (!seen.has(el)) { seen.add(el); count(el); } });
  };
  new MutationObserver(scan).observe(doc.body, {childList: true, subtree: true}); scan();
})();
</script>
"""


def apply() -> None:
    """Inject the stylesheet and the motion layer once per run."""
    st.html(CSS)
    st.html(FX, unsafe_allow_javascript=True)


def intro(title: str, text: str, chips: list[tuple[str, str]]) -> None:
    """Page heading with a one-line purpose and real coverage figures as chips."""
    chip_html = "".join(f'<span class="pt-chip"><b>{escape(v)}</b> {escape(k)}</span>' for v, k in chips)
    st.html(f'<div class="pt-intro"><div><h1>{escape(title)}</h1><p>{escape(text)}</p></div>'
            f'<div class="pt-chips">{chip_html}</div></div>')


def hero(eyebrow: str, title: str, text: str) -> None:
    """Render a page heading with an eyebrow label."""
    page_header(eyebrow, title, text)


def page_header(eyebrow: str, title: str, text: str) -> None:
    """Render a compact page heading with a one-line purpose statement."""
    st.html(f'<div class="pt-section" style="margin-top:.2rem"><div class="pt-eyebrow">{escape(eyebrow)}</div>'
            f'<h2 style="font-size:1.75rem">{escape(title)}</h2><p>{escape(text)}</p></div>')


def section(anchor: str, eyebrow: str, title: str, text: str) -> None:
    """A section heading that the sticky section menu scrolls to."""
    st.html(f'<div class="pt-section" id="{escape(anchor)}"><div class="pt-eyebrow">{escape(eyebrow)}</div>'
            f'<h2>{escape(title)}</h2><p>{escape(text)}</p></div>')


def card_head(anchor: str, eyebrow: str, title: str, note: str = "") -> None:
    """Heading inside a dashboard card; the anchor lets the section menu scroll to it."""
    st.html(f'<div id="{escape(anchor)}"><div class="pt-eyebrow">{escape(eyebrow)}</div><div class="pt-card-head">'
            f'<h3>{escape(title)}</h3><span>{escape(note)}</span></div></div>')


def section_nav(items: list[tuple[str, str]]) -> None:
    """Sticky in-page menu: each link scrolls smoothly to its section."""
    links = "".join(f'<a href="#{escape(anchor)}">{escape(label)}</a>' for anchor, label in items)
    st.html(f'<nav class="pt-nav" aria-label="Sections">{links}</nav>')


def kpis(cards: list[dict]) -> None:
    """Headline figures; hovering or focusing a card reveals how the figure was produced."""
    html = []
    for card in cards:
        accent = TONES.get(card.get("tone", ""), (None,))[0] or "var(--pt-line)"
        html.append(
            f'<div class="pt-kpi" tabindex="0" style="--accent:{accent}" aria-label="{escape(card["label"])}: '
            f'{escape(card["value"])}. {escape(card["tip"])}">'
            f'<div class="pt-kpi-label">{escape(card["label"])}<span aria-hidden="true">?</span></div>'
            f'<div class="pt-kpi-value">{escape(card["value"])}</div>'
            f'<div class="pt-kpi-note">{escape(card.get("note", ""))}</div>'
            f'<div class="pt-kpi-tip" role="tooltip">{escape(card["tip"])}</div></div>')
    st.html(f'<div class="pt-kpis">{"".join(html)}</div>')


def product_header(title: str, tags: list[str], provenance: list[tuple[str, str]]) -> None:
    """Selected product name with its facts and where each part of the analysis comes from."""
    tag_html = "".join(f'<span class="pt-tag">{escape(t)}</span>' for t in tags if t)
    source_html = "".join(f'<span class="pt-tag {escape(kind)}">{escape(text)}</span>' for kind, text in provenance)
    st.html(f'<div class="pt-product"><div><div class="pt-eyebrow">Selected product</div><h3>{escape(title)}</h3>'
            f'<div class="pt-tags">{tag_html}</div></div><div class="pt-tags">{source_html}</div></div>')


def footer(text: str) -> None:
    """Closing note about data scope."""
    st.html(f'<div class="pt-footer">{escape(text)}</div>')


def verdict(title: str, text: str, tone: str) -> None:
    """A result banner whose icon and title carry meaning without relying on colour."""
    accent, background, icon = TONES.get(tone, TONES["neutral"])
    st.html(f'<div class="pt-verdict" role="status" style="--accent:{accent};--bg:{background};--line:{accent}33">'
            f'<div class="pt-icon" aria-hidden="true">{icon}</div>'
            f'<div><h3>{escape(title)}</h3><p>{escape(text)}</p></div></div>')


def empty_state(title: str, text: str) -> None:
    """Explain why nothing is shown and what the user can do next."""
    st.html(f'<div class="pt-empty"><h4>{escape(title)}</h4><p>{escape(text)}</p></div>')


def source_badge(kind: str, detail: str = "") -> None:
    """Show where a result came from beside the result itself."""
    label, color, background = SOURCE_BADGES[kind]
    st.html(f'<span class="pt-badge" style="color:{color};background:{background}">'
            f'{escape(label + (f" · {detail}" if detail else ""))}</span>')


def product_card(title: str, facts: list[tuple[str, str]], source: str, source_detail: str = "") -> None:
    """Identity card shown above an analysis; unknown fields are labelled, never hidden."""
    with st.container(border=True):
        source_badge(source, source_detail)
        st.html(f'<p class="pt-card-title">{escape(title)}</p>')
        text = " · ".join(f"<b>{escape(k)}:</b> {escape(v if v not in (None, '') else 'Unknown')}"
                          for k, v in facts)
        st.html(f'<p class="pt-meta">{text}</p>')


def stat(column, value: str, label: str) -> None:
    """A large number with a short label."""
    column.html(f'<div class="pt-stat">{escape(value)}</div><div class="pt-stat-label">{escape(label)}</div>')


def chart_template() -> go.layout.Template:
    """The brand chart style, built once. As Plotly's default it costs ~1 ms per chart instead of ~20 ms."""
    template = go.layout.Template(pio.templates["plotly_white"])
    template.layout.update(margin=dict(l=16, r=16, t=46, b=10), font=dict(family="Inter, sans-serif", color=INK, size=13),
                           colorway=[PURPLE, CORAL, MINT, AMBER, VIOLET], paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)", title=dict(font=dict(size=15), x=.01),
                           hoverlabel=dict(font_family="Inter, sans-serif", bgcolor="#3B3A48", font_color="#fff",
                                           bordercolor="#3B3A48"),
                           xaxis=dict(gridcolor=GRID, linecolor=GRID), yaxis=dict(gridcolor=GRID, linecolor=GRID))
    return template


pio.templates["price_truth"] = chart_template()
pio.templates.default = "price_truth"


def style_figure(figure: go.Figure, height: int = 320) -> go.Figure:
    """Set the chart height; colours, fonts and grid come from the default brand template. Backgrounds are set on
    the figure itself because Streamlit's front end otherwise paints the plot area in the theme's panel colour."""
    figure.update_layout(height=height, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    if not figure.layout.margin.l:
        figure.update_layout(margin=dict(l=24, r=18, t=46, b=10))
    return figure


def label_margin(figure: go.Figure, labels: list[str]) -> go.Figure:
    """Reserve room for the longest category label (Plotly's automatic margin can clip a few pixels)."""
    width = max((len(str(label)) for label in labels), default=0)
    figure.update_layout(margin=dict(l=min(260, 12 + int(7.4 * width)), r=18, t=46, b=10))
    figure.update_yaxes(automargin=False)
    return figure


def range_chart(lower: float, estimate: float, upper: float, quote: float, prefix: str = "₹") -> go.Figure:
    """Show the quote against the model's expected range on one horizontal scale."""
    low, high = min(lower, quote), max(upper, quote)
    pad = (high - low) * .12 or high * .1
    figure = go.Figure()
    figure.add_trace(go.Bar(x=[upper - lower], base=[lower], y=["range"], orientation="h",
                            marker_color="rgba(224,212,247,.75)", marker_line_color=VIOLET, marker_line_width=1.5,
                            hovertemplate=f"Expected range {prefix}%{{base:,.0f}}–{prefix}{upper:,.0f}<extra></extra>",
                            name="Expected range"))
    figure.add_trace(go.Scatter(x=[estimate], y=["range"], mode="markers", name="Model estimate",
                                marker=dict(symbol="line-ns", size=26, line=dict(width=3, color=VIOLET)),
                                hovertemplate=f"Estimate {prefix}%{{x:,.0f}}<extra></extra>"))
    figure.add_trace(go.Scatter(x=[quote], y=["range"], mode="markers", name="Your price",
                                marker=dict(symbol="diamond", size=17, color=CORAL, line=dict(width=1.5, color="#fff")),
                                hovertemplate=f"Your price {prefix}%{{x:,.0f}}<extra></extra>"))
    figure.update_yaxes(visible=False)
    figure.update_xaxes(range=[max(0, low - pad), high + pad], tickprefix=prefix, tickformat=",.0f")
    figure.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.35), bargap=.45,
                         title="Your price against the expected range")
    return style_figure(figure, height=210)


def effects_chart(effects: list[dict], height: int | None = None) -> go.Figure:
    """Horizontal bars of percentage effects; increases and decreases use colour and sign."""
    ordered = list(reversed(effects))
    figure = go.Figure(go.Bar(
        x=[e["effect_pct"] for e in ordered], y=[f"{e['label']}  {e['effect_pct']:+.0f}%" for e in ordered],
        orientation="h", marker_color=[PURPLE if e["effect_pct"] >= 0 else CORAL for e in ordered],
        marker_line_width=0, hovertemplate="%{y}: %{x:+.1f}% on the estimate<extra></extra>"))
    figure.update_xaxes(ticksuffix="%", zeroline=True, zerolinecolor="#CFC8BC")
    figure.update_yaxes(automargin=True)
    figure.update_layout(title="What moved the estimate", bargap=.35)
    label_margin(figure, [f"{e['label']}  {e['effect_pct']:+.0f}%" for e in effects])
    return style_figure(figure, height=height or max(260, 46 * len(effects) + 70))


def contribution_chart(effects: list[dict], title: str, height: int | None = None) -> go.Figure:
    """Signed contributions: coral raises the risk, blue lowers it; labels state direction in words."""
    ordered = list(reversed(effects))
    figure = go.Figure(go.Bar(
        x=[e["value"] for e in ordered], y=[e["label"] for e in ordered], orientation="h",
        marker_color=[CORAL if e["value"] >= 0 else PURPLE for e in ordered],
        customdata=["raises risk" if e["value"] >= 0 else "lowers risk" for e in ordered],
        hovertemplate="%{y}: %{customdata}<extra></extra>"))
    figure.update_xaxes(zeroline=True, zerolinecolor="#CFC8BC", showticklabels=False,
                        title_text="← lowers risk          raises risk →")
    figure.update_yaxes(automargin=True)
    figure.update_layout(title=title, bargap=.35)
    label_margin(figure, [e["label"] for e in effects])
    return style_figure(figure, height=height or max(240, 46 * len(effects) + 70))


def gauge(probability: float, threshold: float) -> go.Figure:
    """Risk dial for the discount model, with the flag threshold marked."""
    figure = go.Figure(go.Indicator(
        mode="gauge+number", value=100 * probability, number=dict(suffix="%", valueformat=".0f", font=dict(size=30)),
        gauge=dict(axis=dict(range=[0, 100], ticksuffix="%"), bar=dict(color=CORAL if probability >= threshold
                                                                       else PURPLE, thickness=.32),
                   steps=[dict(range=[0, 100 * threshold], color="#EEE7FB"),
                          dict(range=[100 * threshold, 100], color="#FFE6DF")],
                   threshold=dict(line=dict(color=INK, width=3), thickness=.8, value=100 * threshold)),
        title=dict(text="Model: risk the discount is inflated", font=dict(size=14))))
    style_figure(figure, height=190)
    figure.update_layout(margin=dict(l=30, r=30, t=50, b=6))
    return figure
