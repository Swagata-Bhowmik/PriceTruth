"""Shared visual layer: CSS, chart styling and small display components. No business logic."""
from html import escape

import plotly.graph_objects as go
import streamlit as st

PURPLE, LAVENDER, CORAL, MINT, INK, MUTED = "#6C4FD8", "#F5F2FE", "#E8594A", "#1E8A57", "#1F1B2E", "#625E75"
TONES = {  # tone: (accent, background, icon). Icons and titles repeat the meaning conveyed by colour.
    "good": (MINT, "#E9F7EF", "✓"),
    "neutral": (PURPLE, "#F1EDFD", "≈"),
    "bad": ("#C4403F", "#FDEDEB", "!"),
    "muted": (MUTED, "#F3F2F6", "i"),
}
SOURCE_BADGES = {  # Where a number came from, shown next to the result.
    "historical": ("Historical catalogue", "violet"),
    "live": ("Live response", "green"),
    "cached": ("Saved response", "orange"),
    "user": ("Your entry", "blue"),
    "reported": ("Published report", "gray"),
}

CSS = """
<style>
:root { --pt-purple:#6C4FD8; --pt-ink:#1F1B2E; --pt-muted:#625E75; --pt-line:#E4DEF7; }
.block-container { padding-top: 2.2rem; max-width: 1180px; }
h1 { letter-spacing: -0.02em; }
.pt-hero { margin-top:1rem; background: linear-gradient(135deg,#6C4FD8 0%,#8E6CF2 55%,#B79CFF 100%); color:#fff;
  border-radius: 1.1rem; padding: 2rem 2rem 1.6rem; margin-bottom: 1.2rem; }
.pt-hero h1 { color:#fff; margin:0 0 .4rem; font-size: clamp(1.7rem, 4vw, 2.5rem); }
.pt-hero p { color:#F3EEFF; margin:0; font-size:1.05rem; max-width: 46rem; }
.pt-eyebrow { text-transform:uppercase; letter-spacing:.08em; font-size:.75rem; font-weight:600;
  color: var(--pt-purple); margin-bottom:.15rem; }
.pt-hero .pt-eyebrow { color:#FFE3DF; }
.pt-verdict { border-radius: .9rem; padding: 1rem 1.2rem; display:flex; gap: .9rem; align-items:flex-start;
  border-left: 6px solid var(--accent); background: var(--bg); margin: .4rem 0 .8rem; }
.pt-verdict .pt-icon { flex: 0 0 2.1rem; height:2.1rem; border-radius:50%; background: var(--accent); color:#fff;
  font-weight:700; display:flex; align-items:center; justify-content:center; font-size:1.1rem; }
.pt-verdict h3 { margin:0 0 .2rem; font-size:1.15rem; color: var(--pt-ink); padding:0; }
.pt-verdict p { margin:0; color: var(--pt-ink); }
.pt-card-title { font-weight:600; font-size:1.05rem; color:var(--pt-ink); margin:0 0 .2rem; line-height:1.35; }
.pt-meta { color: var(--pt-muted); font-size:.88rem; margin:0; }
.pt-empty { border:1.5px dashed var(--pt-line); border-radius:.9rem; padding:1.2rem 1.3rem; background:#FCFBFF; }
.pt-empty h4 { margin:0 0 .25rem; font-size:1.02rem; color:var(--pt-ink); padding:0; }
.pt-empty p { margin:0; color: var(--pt-muted); }
.pt-stat { font-size:1.6rem; font-weight:700; color:var(--pt-ink); line-height:1.1; }
.pt-stat-label { color:var(--pt-muted); font-size:.85rem; }
[data-testid="stNumberInputStepUp"], [data-testid="stNumberInputStepDown"] { display:none; }
[data-testid="stMetricValue"] { font-weight:700; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #5F5B71 !important; opacity: 1 !important; }
a:focus-visible, button:focus-visible, [role="tab"]:focus-visible { outline: 3px solid #8E6CF2 !important;
  outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
@media (max-width: 640px) { .pt-hero { padding: 1.3rem 1.1rem 1.1rem; } .block-container { padding-top: 3rem; } }
</style>
"""


def apply() -> None:
    """Inject the stylesheet once per run."""
    st.html(CSS)


def hero(eyebrow: str, title: str, text: str) -> None:
    """Render the branded page header."""
    st.html(f'<div class="pt-hero"><div class="pt-eyebrow">{escape(eyebrow)}</div>'
            f'<h1>{escape(title)}</h1><p>{escape(text)}</p></div>')


def page_header(eyebrow: str, title: str, text: str) -> None:
    """Render a compact page heading with a one-line purpose statement."""
    st.html(f'<div class="pt-eyebrow">{escape(eyebrow)}</div>')
    st.title(title)
    st.caption(text)


def verdict(title: str, text: str, tone: str) -> None:
    """A result banner whose icon and title carry meaning without relying on colour."""
    accent, background, icon = TONES.get(tone, TONES["neutral"])
    st.html(f'<div class="pt-verdict" role="status" style="--accent:{accent};--bg:{background}">'
            f'<div class="pt-icon" aria-hidden="true">{icon}</div>'
            f'<div><h3>{escape(title)}</h3><p>{escape(text)}</p></div></div>')


def empty_state(title: str, text: str) -> None:
    """Explain why nothing is shown and what the user can do next."""
    st.html(f'<div class="pt-empty"><h4>{escape(title)}</h4><p>{escape(text)}</p></div>')


def source_badge(kind: str, detail: str = "") -> None:
    """Show where a result came from beside the result itself."""
    label, color = SOURCE_BADGES[kind]
    st.badge(label + (f" · {detail}" if detail else ""), color=color)


def product_card(title: str, facts: list[tuple[str, str]], source: str, source_detail: str = "") -> None:
    """Identity card shown above every analysis; unknown fields are labelled, never hidden."""
    with st.container(border=True):
        source_badge(source, source_detail)
        st.html(f'<p class="pt-card-title">{escape(title)}</p>')
        text = " · ".join(f"<b>{escape(k)}:</b> {escape(v if v not in (None, '') else 'Unknown')}"
                          for k, v in facts)
        st.html(f'<p class="pt-meta">{text}</p>')


def stat(column, value: str, label: str) -> None:
    """A large number with a short label, used on the home page."""
    column.html(f'<div class="pt-stat">{escape(value)}</div><div class="pt-stat-label">{escape(label)}</div>')


def style_figure(figure: go.Figure, height: int = 320) -> go.Figure:
    """Apply consistent chart styling across pages."""
    figure.update_layout(template="plotly_white", height=height, margin=dict(l=8, r=8, t=40, b=8),
                         font=dict(family="Inter, sans-serif", color=INK, size=13),
                         colorway=[PURPLE, CORAL, MINT, "#E0A21B", "#3A86C8"],
                         hoverlabel=dict(font_family="Inter, sans-serif"))
    if figure.layout.title.text:
        figure.update_layout(title_font_size=15)
    return figure


def range_chart(lower: float, estimate: float, upper: float, quote: float, prefix: str = "₹") -> go.Figure:
    """Show the quote against the model's expected range on one horizontal scale."""
    low, high = min(lower, quote), max(upper, quote)
    pad = (high - low) * .12 or high * .1
    figure = go.Figure()
    figure.add_trace(go.Bar(x=[upper - lower], base=[lower], y=["range"], orientation="h",
                            marker_color="rgba(108,79,216,.18)", marker_line_color=PURPLE, marker_line_width=1.5,
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
    return style_figure(figure, height=210)


def effects_chart(effects: list[dict]) -> go.Figure:
    """Horizontal bars of percentage effects; increases and decreases use colour and sign."""
    ordered = list(reversed(effects))
    figure = go.Figure(go.Bar(
        x=[e["effect_pct"] for e in ordered], y=[e["label"] for e in ordered], orientation="h",
        marker_color=[PURPLE if e["effect_pct"] >= 0 else CORAL for e in ordered],
        text=[f"{e['effect_pct']:+.0f}%" for e in ordered], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:+.1f}%<extra></extra>"))
    figure.update_xaxes(ticksuffix="%", zeroline=True, zerolinecolor="#B9B3CC")
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
    figure.update_layout(title=title)
    return style_figure(figure, height=max(240, 46 * len(effects) + 70))
