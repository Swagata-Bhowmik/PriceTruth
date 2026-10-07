"""User guide page: the illustrated guide embedded full-height, plus a download for offline use."""
import streamlit as st

from price_truth.paths import ROOT

GUIDE = ROOT / "docs" / "USER-GUIDE.html"

# Use the full width and let the guide fill the window; it scrolls inside its own frame so its
# contents sidebar and section links keep working.
st.html("""<style>
.block-container { max-width: 100% !important; padding: 4.2rem 1.2rem 0 !important; }
.st-key-user_guide iframe { height: calc(100vh - 11rem) !important; border: 1px solid #E4DEF7; border-radius: 12px; }
</style>""")
if not GUIDE.exists():
    st.error("The user guide file is missing. Rebuild it or restore docs/USER-GUIDE.html.")
    st.stop()
columns = st.columns([4, 1], vertical_alignment="center")
columns[0].caption("Step-by-step help for every page, with screenshots. Use the guide's own contents list to jump "
                   "between sections.")
columns[1].download_button("Download guide", GUIDE.read_bytes(), file_name="Price-Truth-User-Guide.html",
                           mime="text/html", on_click="ignore", width="stretch")
with st.container(key="user_guide"):
    st.iframe(GUIDE, height=900)
