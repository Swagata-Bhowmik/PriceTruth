"""Shared visual layer: CSS, chart styling and small display components. No business logic."""
from html import escape

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

PURPLE, LAVENDER, CORAL, MINT, INK, MUTED = "#5B3FD0", "#F4F1FE", "#D9534A", "#16804B", "#141127", "#5E5A70"
AMBER, GRID = "#B7791F", "#ECEAF3"
TONES = {  # tone: (accent, background, icon). Icons and titles repeat the meaning conveyed by colour.
    "good": (MINT, "#EAF6EF", "✓"),
    "neutral": (PURPLE, "#F1EDFD", "≈"),
    "bad": ("#B93A35", "#FCEDEC", "!"),
    "muted": (MUTED, "#F3F2F6", "i"),
}
SOURCE_BADGES = {  # Where a number came from, shown next to the result (colours meet WCAG AA contrast).
    "historical": ("Historical catalogue", "#4A2FB8", "#F1EDFD"),
    "live": ("Live response", "#0F6B3E", "#EAF6EF"),
    "cached": ("Saved response", "#6B4A08", "#FDF4E3"),
    "user": ("Your entry", "#1F5A99", "#EAF2FB"),
    "reported": ("Published report", "#3F3B52", "#F0EFF4"),
}

CSS = """
<style>
:root { --pt-purple:#5B3FD0; --pt-ink:#141127; --pt-muted:#5E5A70; --pt-line:#E6E3F0; --pt-bg:#F7F6FB;
  --pt-card:#FFFFFF; --pt-shadow:0 1px 2px rgba(20,17,39,.04), 0 4px 16px rgba(20,17,39,.05); }
html { scroll-behavior: smooth; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--pt-bg); }
[data-testid="stHeader"] { background: rgba(247,246,251,.86); backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--pt-line); }
.block-container { padding-top: 4.6rem; padding-bottom: 3rem; max-width: 1320px; }
h1, h2, h3 { letter-spacing: -0.015em; color: var(--pt-ink); }
[id] { scroll-margin-top: 7.5rem; }
/* Cards: bordered Streamlit containers become white dashboard panels. */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) { background: var(--pt-card); }
div[data-testid="stVerticalBlockBorderWrapper"][class*="border"] { box-shadow: var(--pt-shadow); }
.pt-intro { display:flex; justify-content:space-between; align-items:flex-end; gap:1.5rem; flex-wrap:wrap;
  margin: .2rem 0 1rem; }
.pt-intro h1 { font-size: clamp(1.6rem, 3.2vw, 2.15rem); margin:0; padding:0; line-height:1.15; }
.pt-intro p { margin:.35rem 0 0; color: var(--pt-muted); max-width: 44rem; font-size: 1.02rem; }
.pt-chips { display:flex; gap:.5rem; flex-wrap:wrap; }
.pt-chip { background: var(--pt-card); border:1px solid var(--pt-line); border-radius: 999px; padding:.35rem .8rem;
  font-size:.84rem; color: var(--pt-muted); white-space:nowrap; }
.pt-chip b { color: var(--pt-ink); font-weight:650; }
.pt-eyebrow { text-transform:uppercase; letter-spacing:.09em; font-size:.72rem; font-weight:650;
  color: var(--pt-purple); margin-bottom:.15rem; }
.pt-section { margin: 2.2rem 0 .7rem; padding-top: .3rem; }
.pt-section h2 { font-size: 1.35rem; margin: 0; padding: 0; }
.pt-section p { margin: .25rem 0 0; color: var(--pt-muted); max-width: 52rem; }
[data-testid="stElementContainer"]:has(.pt-nav) { position: sticky; top: 3.6rem; z-index: 50; background: var(--pt-bg);
  box-shadow: 0 6px 12px -10px rgba(20,17,39,.25); }
.pt-nav { display:flex; gap:.3rem; flex-wrap:wrap;
  background: var(--pt-bg); padding:.45rem 0; margin: .6rem 0 .2rem;
  border-bottom: 1px solid var(--pt-line); }
.pt-nav a { text-decoration:none; color: var(--pt-muted); font-size:.86rem; font-weight:550; padding:.32rem .75rem;
  border-radius: 999px; border:1px solid transparent; transition: all .15s ease; }
.pt-nav a:hover, .pt-nav a:focus-visible { color: var(--pt-purple); background:#fff; border-color: var(--pt-line); }
[data-testid="stElementContainer"]:has(.pt-kpis) { position: relative; z-index: 60; }
.pt-kpis { display:grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap:.75rem; margin:.4rem 0 .2rem; }
.pt-kpi { position:relative; background: var(--pt-card); border:1px solid var(--pt-line); border-radius: 14px;
  padding: .85rem 1rem .8rem; box-shadow: var(--pt-shadow); border-top: 3px solid var(--accent, var(--pt-line));
  outline:none; transition: transform .15s ease, box-shadow .15s ease; cursor: default; }
.pt-kpi:hover, .pt-kpi:focus-visible { transform: translateY(-2px);
  box-shadow: 0 2px 4px rgba(20,17,39,.05), 0 10px 26px rgba(20,17,39,.09); }
.pt-kpi-label { font-size:.76rem; text-transform:uppercase; letter-spacing:.06em; color: var(--pt-muted);
  font-weight:600; display:flex; gap:.35rem; align-items:center; }
.pt-kpi-label span { font-size:.72rem; border:1px solid var(--pt-line); border-radius:50%; width:1rem; height:1rem;
  display:inline-flex; align-items:center; justify-content:center; text-transform:none; }
.pt-kpi-value { font-size:1.28rem; font-weight:700; color: var(--pt-ink); margin:.25rem 0 .1rem; line-height:1.15; }
.pt-kpi-note { font-size:.82rem; color: var(--pt-muted); }
.pt-kpi-tip { visibility:hidden; opacity:0; position:absolute; left:.4rem; min-width: 230px; top: calc(100% + .45rem);
  background: var(--pt-ink); color:#fff; font-size:.8rem; line-height:1.4; padding:.6rem .7rem; border-radius:10px;
  z-index:40; transition: opacity .15s ease; box-shadow: 0 8px 24px rgba(20,17,39,.25); pointer-events:none; }
.pt-kpi:hover .pt-kpi-tip, .pt-kpi:focus-visible .pt-kpi-tip { visibility:visible; opacity:1; }
.pt-product { display:flex; gap:1rem; align-items:center; justify-content:space-between; flex-wrap:wrap;
  margin:.2rem 0 .1rem; }
.pt-product h3 { font-size:1.08rem; margin:0; padding:0; line-height:1.35; font-weight:650; }
.pt-tags { display:flex; gap:.4rem; flex-wrap:wrap; margin-top:.35rem; }
.pt-tag { font-size:.76rem; color: var(--pt-muted); background: var(--pt-bg); border:1px solid var(--pt-line);
  padding:.15rem .55rem; border-radius: 6px; }
.pt-tag.real { color:#0F6B3E; background:#EAF6EF; border-color:#CBE9D7; }
.pt-tag.sim { color:#7A4E0C; background:#FDF4E3; border-color:#F2DDB3; }
.pt-verdict { border-radius: 12px; padding: .9rem 1.1rem; display:flex; gap: .85rem; align-items:flex-start;
  border:1px solid var(--line); background: var(--bg); margin: .2rem 0 .7rem; }
.pt-verdict .pt-icon { flex: 0 0 2rem; height:2rem; border-radius:50%; background: var(--accent); color:#fff;
  font-weight:700; display:flex; align-items:center; justify-content:center; font-size:1rem; }
.pt-verdict h3 { margin:0 0 .15rem; font-size:1.05rem; color: var(--pt-ink); padding:0; }
.pt-verdict p { margin:0; color: var(--pt-ink); font-size:.94rem; }
.pt-badge { display:inline-block; font-size:.8rem; font-weight:600; padding:.15rem .6rem; border-radius:6px; }
.pt-card-title { font-weight:600; font-size:1.05rem; color:var(--pt-ink); margin:0 0 .2rem; line-height:1.35; }
.pt-meta { color: var(--pt-muted); font-size:.88rem; margin:0; }
.pt-empty { border:1.5px dashed var(--pt-line); border-radius:12px; padding:1.1rem 1.2rem; background:#FCFBFF; }
.pt-empty h4 { margin:0 0 .25rem; font-size:1rem; color:var(--pt-ink); padding:0; }
.pt-empty p { margin:0; color: var(--pt-muted); }
.pt-stat { font-size:1.6rem; font-weight:700; color:var(--pt-ink); line-height:1.1; }
.pt-stat-label { color:var(--pt-muted); font-size:.85rem; }
.pt-footer { margin-top: 2.5rem; padding-top: 1rem; border-top:1px solid var(--pt-line); color: var(--pt-muted);
  font-size:.84rem; }
[data-testid="stNumberInputStepUp"], [data-testid="stNumberInputStepDown"] { display:none; }
[data-testid="stMetricValue"] { font-weight:700; font-size: 1.35rem; }
[data-testid="stMetric"] { background: var(--pt-card); border:1px solid var(--pt-line); border-radius: 12px;
  padding: .7rem .9rem; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #5A566C !important; opacity: 1 !important; }
/* Charts fit their container; no inner scroll region that keyboard users could not reach. */
[data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]) { overflow: visible !important; }
[data-testid="stPlotlyChart"] { background: var(--pt-card); border:1px solid var(--pt-line); border-radius: 14px;
  padding: .35rem .5rem; box-shadow: var(--pt-shadow); }
a:focus-visible, button:focus-visible, [role="tab"]:focus-visible { outline: 3px solid #8E6CF2 !important;
  outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; }
  * { animation: none !important; transition: none !important; } }
@media (max-width: 640px) { .block-container { padding-top: 4rem; }
  [data-testid="stElementContainer"]:has(.pt-nav) { top: 3.4rem; }
  .pt-kpis { grid-template-columns: 1fr 1fr; } .pt-kpi-value { font-size: 1.2rem; } }
</style>
"""


def apply() -> None:
    """Inject the stylesheet once per run."""
    st.html(CSS)


def intro(title: str, text: str, chips: list[tuple[str, str]]) -> None:
    """Dashboard heading with a one-line purpose and real coverage figures as chips."""
    chip_html = "".join(f'<span class="pt-chip"><b>{escape(v)}</b> {escape(k)}</span>' for v, k in chips)
    st.html(f'<div class="pt-intro"><div><h1>{escape(title)}</h1><p>{escape(text)}</p></div>'
            f'<div class="pt-chips">{chip_html}</div></div>')


def hero(eyebrow: str, title: str, text: str) -> None:
    """Render a page heading with an eyebrow label."""
    page_header(eyebrow, title, text)


def page_header(eyebrow: str, title: str, text: str) -> None:
    """Render a compact page heading with a one-line purpose statement."""
    st.html(f'<div class="pt-section" style="margin-top:.4rem"><div class="pt-eyebrow">{escape(eyebrow)}</div>'
            f'<h2 style="font-size:1.7rem">{escape(title)}</h2><p>{escape(text)}</p></div>')


def section(anchor: str, eyebrow: str, title: str, text: str) -> None:
    """A dashboard section heading that the sticky section menu scrolls to."""
    st.html(f'<div class="pt-section" id="{escape(anchor)}"><div class="pt-eyebrow">{escape(eyebrow)}</div>'
            f'<h2>{escape(title)}</h2><p>{escape(text)}</p></div>')


def section_nav(items: list[tuple[str, str]]) -> None:
    """Sticky in-page menu: each link scrolls smoothly to its section."""
    links = "".join(f'<a href="#{escape(anchor)}">{escape(label)}</a>' for anchor, label in items)
    st.html(f'<nav class="pt-nav" aria-label="Dashboard sections">{links}</nav>')


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
                           colorway=[PURPLE, CORAL, MINT, AMBER, "#3A86C8"], paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)", title=dict(font=dict(size=15), x=.01),
                           hoverlabel=dict(font_family="Inter, sans-serif", bgcolor=INK, font_color="#fff",
                                           bordercolor=INK),
                           xaxis=dict(gridcolor=GRID, linecolor=GRID), yaxis=dict(gridcolor=GRID, linecolor=GRID))
    return template


pio.templates["price_truth"] = chart_template()
pio.templates.default = "price_truth"


def style_figure(figure: go.Figure, height: int = 320) -> go.Figure:
    """Set the chart height; colours, fonts, grid and margins come from the default brand template."""
    figure.update_layout(height=height)
    return figure


def range_chart(lower: float, estimate: float, upper: float, quote: float, prefix: str = "₹") -> go.Figure:
    """Show the quote against the model's expected range on one horizontal scale."""
    low, high = min(lower, quote), max(upper, quote)
    pad = (high - low) * .12 or high * .1
    figure = go.Figure()
    figure.add_trace(go.Bar(x=[upper - lower], base=[lower], y=["range"], orientation="h",
                            marker_color="rgba(91,63,208,.16)", marker_line_color=PURPLE, marker_line_width=1.5,
                            hovertemplate=f"Expected range {prefix}%{{base:,.0f}}–{prefix}{upper:,.0f}<extra></extra>",
                            name="Expected range"))
    figure.add_trace(go.Scatter(x=[estimate], y=["range"], mode="markers", name="Model estimate",
                                marker=dict(symbol="line-ns", size=26, line=dict(width=3, color=PURPLE)),
                                hovertemplate=f"Estimate {prefix}%{{x:,.0f}}<extra></extra>"))
    figure.add_trace(go.Scatter(x=[quote], y=["range"], mode="markers", name=f"Your price {prefix}{quote:,.0f}",
                                marker=dict(symbol="diamond", size=16, color=CORAL, line=dict(width=1.5, color="#fff")),
                                hovertemplate=f"Your price {prefix}%{{x:,.0f}}<extra></extra>"))
    figure.update_yaxes(visible=False)
    figure.update_xaxes(range=[max(0, low - pad), high + pad], tickprefix=prefix, tickformat=",.0f")
    figure.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.35), bargap=.45,
                         title="Your price against the expected range")
    return style_figure(figure, height=220)


def effects_chart(effects: list[dict]) -> go.Figure:
    """Horizontal bars of percentage effects; increases and decreases use colour and sign."""
    ordered = list(reversed(effects))
    figure = go.Figure(go.Bar(
        x=[e["effect_pct"] for e in ordered], y=[f"{e['label']}  {e['effect_pct']:+.0f}%" for e in ordered],
        orientation="h", marker_color=[PURPLE if e["effect_pct"] >= 0 else CORAL for e in ordered],
        hovertemplate="%{y}: %{x:+.1f}% on the estimate<extra></extra>"))
    figure.update_xaxes(ticksuffix="%", zeroline=True, zerolinecolor="#B9B3CC")
    figure.update_yaxes(automargin=True)
    figure.update_layout(title="What moved the estimate")
    return style_figure(figure, height=max(260, 46 * len(effects) + 70))


def contribution_chart(effects: list[dict], title: str) -> go.Figure:
    """Signed contributions: coral raises the risk, purple lowers it; labels state direction in words."""
    ordered = list(reversed(effects))
    figure = go.Figure(go.Bar(
        x=[e["value"] for e in ordered], y=[e["label"] for e in ordered], orientation="h",
        marker_color=[CORAL if e["value"] >= 0 else PURPLE for e in ordered],
        customdata=["raises risk" if e["value"] >= 0 else "lowers risk" for e in ordered],
        hovertemplate="%{y}: %{customdata}<extra></extra>"))
    figure.update_xaxes(zeroline=True, zerolinecolor="#B9B3CC", showticklabels=False,
                        title_text="← lowers risk          raises risk →")
    figure.update_yaxes(automargin=True)
    figure.update_layout(title=title)
    return style_figure(figure, height=max(240, 46 * len(effects) + 70))


def gauge(probability: float, threshold: float) -> go.Figure:
    """Risk dial for the discount model, with the flag threshold marked."""
    figure = go.Figure(go.Indicator(
        mode="gauge+number", value=100 * probability, number=dict(suffix="%", valueformat=".0f", font=dict(size=30)),
        gauge=dict(axis=dict(range=[0, 100], ticksuffix="%"), bar=dict(color=CORAL if probability >= threshold
                                                                       else PURPLE, thickness=.32),
                   steps=[dict(range=[0, 100 * threshold], color="#F1EDFD"),
                          dict(range=[100 * threshold, 100], color="#FCEDEC")],
                   threshold=dict(line=dict(color=INK, width=3), thickness=.8, value=100 * threshold)),
        title=dict(text="Model: risk the discount is inflated", font=dict(size=14))))
    style_figure(figure, height=230)
    figure.update_layout(margin=dict(l=28, r=28, t=56, b=12))
    return figure
