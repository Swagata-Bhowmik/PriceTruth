"""End-to-end widget interactions using Streamlit's official AppTest harness."""
import pytest
from streamlit.testing.v1 import AppTest

from price_truth.paths import ROOT

PAGES = ["views/home.py", "views/product.py", "views/compare.py", "views/food.py", "views/shrink.py",
         "views/observations.py", "views/catalogue.py", "views/methods.py", "views/user-guide.py"]


def application(page="views/home.py"):
    """Load a page through the same entrypoint and navigation users run."""
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=45)
    app.session_state["food_offline"] = True  # tests never call live APIs or rewrite saved responses
    app.run()
    if page != "views/home.py":
        app.switch_page(page).run()
    return app


def button(app, label):
    """Find a button by its visible label."""
    return next(b for b in app.button if b.label == label)


@pytest.mark.parametrize("page", PAGES)
def test_pages_render(page):
    """Every navigation destination loads without a Python exception."""
    app = application(page)
    assert not app.exception


def test_home_shows_real_coverage():
    """Home statistics come from the catalogue, not hard-coded marketing numbers."""
    app = application()
    html = " ".join(str(h.proto.body) for h in app.get("html"))
    assert "21,267" in html and "Amazon &amp; Flipkart listings" in html


def test_price_check_runs_real_model():
    """Submitting a quote displays a verdict, three metrics and two computed charts."""
    app = application("views/product.py")
    button(app, "Check this price").click().run()
    assert not app.exception
    assert [m.label for m in app.metric][:3] == ["Advertised discount", "Model estimate", "Expected range"]
    assert len(app.get("plotly_chart")) >= 2
    assert [t.label for t in app.tabs] == ["Discount check", "Price history & timing", "Where to buy"]
    html = " ".join(str(h.proto.body) for h in app.get("html"))
    assert "pt-verdict" in html


def test_price_check_search_with_no_match_shows_empty_state():
    """An impossible query explains what to do instead of failing."""
    app = application("views/product.py")
    app.text_input(key="product_query").set_value("zzzzqqqxxx").run()
    assert not app.exception
    assert "No listings match" in " ".join(str(h.proto.body) for h in app.get("html"))


def test_unit_comparison_flow():
    """Comparable packs produce a best-value verdict and ranked table."""
    app = application("views/compare.py")
    app.number_input(key="price1").set_value(10)
    app.number_input(key="quantity1").set_value(100)
    app.number_input(key="price2").set_value(15)
    app.number_input(key="quantity2").set_value(200)
    button(app, "Compare value").click().run()
    assert not app.exception
    html = " ".join(str(h.proto.body) for h in app.get("html"))
    assert "Option 2 is the best value" in html
    assert app.dataframe[0].value.iloc[0]["Option"] == "Option 2"


def test_unit_comparison_requires_inputs():
    """Missing inputs produce a validation message, not a crash."""
    app = application("views/compare.py")
    button(app, "Compare value").click().run()
    assert "Enter a price and a quantity" in app.error[0].value


def test_offline_food_lookup_flow():
    """Saved responses work offline and show their source badge."""
    app = application("views/food.py")
    assert not app.exception
    first = app.selectbox(key="food_product").value
    assert first["product_name"] and "India" in first["countries"]
    assert any("Saved response" in str(m.value) for m in app.markdown)


def test_pack_transfer_prefills_unit_comparison():
    """A structured pack size is carried into the unit comparison; its price is left to the user."""
    app = application("views/food.py")
    button(app, "Compare this pack's value").click().run()
    assert not app.exception
    assert app.session_state["quantity1"] > 0 and app.session_state["price1"] is None


def test_methods_lists_licences():
    """Attribution and licences are visible in the app."""
    app = application("views/methods.py")
    licences = next(d.value for d in app.dataframe if "Licence" in d.value.columns).Licence.tolist()
    assert "CC BY-NC-SA 4.0" in licences and "ODbL 1.0" in licences


def test_user_guide_page_embeds_the_guide():
    """The guide page embeds the illustrated HTML guide and offers it as a download."""
    app = application("views/user-guide.py")
    assert not app.exception
    assert any(b.proto.label == "Download guide" for b in app.get("download_button"))
    assert len(app.get("iframe")) == 1
