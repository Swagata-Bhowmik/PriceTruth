"""End-to-end widget interactions using Streamlit's official AppTest harness."""
import pytest
from streamlit.testing.v1 import AppTest

from price_truth.paths import ROOT

PAGES = ["views/dashboard.py", "views/food.py", "views/observations.py", "views/catalogue.py", "views/methods.py",
         "views/user-guide.py"]
KPI_LABELS = ["Price verdict", "Fair price estimate", "Advertised discount", "Real saving", "Inflation risk",
              "Best place to buy"]


def application(page="views/dashboard.py"):
    """Load a page through the same entrypoint and navigation users run."""
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    app.session_state["food_offline"] = True  # tests never call live APIs or rewrite saved responses
    app.run()
    if page != "views/dashboard.py":
        app.switch_page(page).run()
    return app


def button(app, label):
    """Find a button by its visible label."""
    return next(b for b in app.button if b.label == label)


def html(app) -> str:
    """All custom HTML on the page, as one string."""
    return " ".join(str(h.proto.body) for h in app.get("html"))


@pytest.mark.parametrize("page", PAGES)
def test_pages_render(page):
    """Every navigation destination loads without a Python exception."""
    app = application(page)
    assert not app.exception


def test_dashboard_shows_real_coverage_and_every_section():
    """The default product is analysed at once: six headline figures and every section anchor."""
    app = application()
    body = html(app)
    assert "21,267" in body
    assert all(label in body for label in KPI_LABELS)
    for anchor in ["verdict", "discount", "history", "buy", "packs", "shrink", "export"]:
        assert f'id="{anchor}"' in body and f'href="#{anchor}"' in body
    assert "pt-verdict" in body and len(app.get("plotly_chart")) >= 6


def test_dropdowns_narrow_the_product_list():
    """Choosing a platform and category limits products to that platform and category."""
    app = application()
    app.selectbox(key="dash_platform").set_value("Flipkart").run()
    app.selectbox(key="dash_category").set_value("Footwear").run()
    assert not app.exception
    heading = next(str(h.proto.body) for h in app.get("html") if "Selected product" in str(h.proto.body))
    assert "Flipkart" in heading and "Footwear" in heading


def test_changing_the_price_updates_the_verdict():
    """A far-above-range quote turns the verdict to 'Above expected'."""
    app = application()
    key = app.selectbox(key="dash_product").value
    app.number_input(key=f"listed_{key}").set_value(2_000_000)
    app.number_input(key=f"selling_{key}").set_value(999_999).run()
    assert not app.exception
    assert "Above expected" in html(app)


def test_price_above_mrp_is_rejected_with_a_message():
    """Validation: a selling price above the listed MRP is refused, not analysed."""
    app = application()
    key = app.selectbox(key="dash_product").value
    app.number_input(key=f"selling_{key}").set_value(999_999).run()
    assert not app.exception
    assert "cannot exceed the listed reference price" in app.error[0].value


def test_filter_with_no_match_shows_empty_state():
    """An impossible name filter explains what to do instead of failing."""
    app = application()
    app.text_input(key="dash_filter").set_value("zzzzqqqxxx").run()
    assert not app.exception
    assert "No products match" in html(app)


def test_unit_comparison_flow():
    """Comparable packs produce a best-value verdict and ranked table."""
    app = application()
    app.number_input(key="price1").set_value(10)
    app.number_input(key="quantity1").set_value(100)
    app.number_input(key="price2").set_value(15)
    app.number_input(key="quantity2").set_value(200)
    button(app, "Compare value").click().run()
    assert not app.exception
    assert "Option 2 is the best value" in html(app)
    ranked = next(d.value for d in app.dataframe if "Option" in d.value.columns)
    assert ranked.iloc[0]["Option"] == "Option 2"


def test_unit_comparison_requires_inputs():
    """Missing inputs produce a validation message, not a crash."""
    app = application()
    button(app, "Compare value").click().run()
    assert "Enter a price and a quantity" in app.error[0].value


def test_shrinkflation_case_shows_hidden_increase():
    """The default cited case shows the pack reduction and its source."""
    app = application()
    assert "real price per" in html(app)
    assert any(b.proto.label == "Read the original report" for b in app.get("link_button"))


def test_offline_food_lookup_flow():
    """Saved responses work offline and show their source badge."""
    app = application("views/food.py")
    assert not app.exception
    first = app.selectbox(key="food_product").value
    assert first["product_name"] and "India" in first["countries"]
    assert any("Saved response" in str(m.value) for m in app.markdown)


def test_pack_transfer_prefills_unit_comparison():
    """A structured pack size is carried into the dashboard's unit comparison; its price is left to the user."""
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
