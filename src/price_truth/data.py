"""Normalize real supplied listings and preserve an audit of every exclusion."""
import hashlib
import json
import re
from datetime import UTC, datetime

import pandas as pd

from price_truth.paths import DATA, PROCESSED, REPORTS

SOURCES = {
    "amazon": (DATA / "amazon/amazon.csv", "product_id", "actual_price"),
    "flipkart": (DATA / "flipkart/flipkart_com-ecommerce_sample.csv", "pid", "retail_price"),
}
ROOTS = {
    "Computers&Accessories": "Computers", "Computers": "Computers",
    "Electronics": "Electronics", "Mobiles & Accessories": "Electronics",
    "Cameras & Accessories": "Electronics", "Gaming": "Electronics", "Home Entertainment": "Electronics",
    "Wearable Smart Devices": "Electronics",
    "Home&Kitchen": "Home and kitchen", "Kitchen & Dining": "Home and kitchen",
    "Home Furnishing": "Home and kitchen", "Home & Kitchen": "Home and kitchen",
    "Household Supplies": "Home and kitchen",
    "Home Decor & Festive Needs": "Home decor and furniture", "Furniture": "Home decor and furniture",
    "Tools & Hardware": "Tools and home improvement", "Home Improvement": "Tools and home improvement",
    "HomeImprovement": "Tools and home improvement", "Automation & Robotics": "Tools and home improvement",
    "Automotive": "Automotive", "Car&Motorbike": "Automotive",
    "Watches": "Fashion accessories", "Bags, Wallets & Belts": "Fashion accessories",
    "Sunglasses": "Fashion accessories", "Eyewear": "Fashion accessories",
    "Baby Care": "Baby and kids", "Toys & School Supplies": "Baby and kids", "Toys&Games": "Baby and kids",
    "Sports & Fitness": "Sports and fitness",
    "Clothing": "Clothing", "Jewellery": "Jewellery", "Footwear": "Footwear",
    "OfficeProducts": "Office supplies", "Pens & Stationery": "Office supplies",
    "Beauty and Personal Care": "Personal care", "Health&PersonalCare": "Personal care",
    "Health & Personal Care Appliances": "Personal care",
}
# Some Flipkart rows carry the product title instead of a category tree. Classify those from
# whole words in the title, first match wins; anything unmatched stays "Other".
TITLE_RULES = [
    ("Footwear", r"flats|bellies|wedges|shoes|slippers|sandals|heels|lace up|floaters"),
    ("Clothing", r"bra|panty|panties|brief|boxer|vest|camisole|lingerie|kurta|kurti|sari|saree|salwar|"
                 r"leggings|jeans|t-shirt|shirt|top|dress|jumpsuit|jacket|sweater|sweatshirt|blazer|"
                 r"trousers|shorts|stole|socks|gloves|pyjama|capri|combo"),
    ("Jewellery", r"bangles?|rings?|necklace|earrings?|pendant|bracelet|anklet|mangalsutra"),
    ("Fashion accessories", r"sunglasses|clutch|wallet|belt|backpack|bag|watch|hair clip|hair band|cufflink"),
    ("Automotive", r"car|bike|steering|rear view mirror|bajaj|royal enfield|helmet|side stand|grill"),
    ("Home decor and furniture", r"tapestry|showpiece|lantern|candles?|artificial plant|sofa cover|"
                                 r"table cover|bedsheet|mat|mattress|incense|cushion|paper weights?"),
    ("Electronics", r"headset|binoculars|mixer|battery|lcd|mah|charging pack|pouch|screen guard|"
                    r"guard glass|tempered glass"),
    ("Home and kitchen", r"glass|bowl|wine cooler|cookware|bottle"),
    ("Tools and home improvement", r"faucet|pump controller|mcb|fittings|roller brush|work bench|"
                                   r"motion sensor|surge protector|seeds?"),
    ("Personal care", r"foundation brush|hair dryer|conditioner|shaving|nail cutter|pain relief"),
    ("Computers", r"keyboard"),
    ("Baby and kids", r"baby|walker|board game|quilling"),
    ("Sports and fitness", r"thigh guard|arm sleeve"),
]


SPEC_KEYS = ["Model ID", "Style Code", "Model Number", "Model Name", "Color", "Pattern", "Type", "Size"]
DESCRIPTION_CODE = re.compile(r"\b(?:model\s*(?:id|no\.?|number)|style\s*code)\s*[:\-]?\s*([A-Za-z0-9][\w\-/.]{2,30})",
                              re.IGNORECASE)


def spec_value(text: str, key: str) -> str:
    """Read one key from Flipkart's product_specifications text without evaluating it."""
    match = re.search(rf'"key"=>"{re.escape(key)}",\s*"value"=>"([^"]*)"', text or "")
    return match.group(1).strip() if match else ""


def flipkart_variant(specifications: str, description: str) -> str:
    """Distinguishing details for listings that share a title: specs first, then a model code in the text."""
    parts = []
    for key in SPEC_KEYS:
        value = spec_value(specifications, key)
        if value and value not in parts:
            parts.append(value)
    code = DESCRIPTION_CODE.search(description or "")
    if code and code.group(1) not in parts:
        parts.insert(0, code.group(1))
    return " · ".join(parts[:3])


def amazon_variant(name: str) -> str:
    """Amazon titles end with variant details in brackets, e.g. '(3 FT Pack of 1, Grey)'."""
    match = re.search(r"\(([^()]*)\)\s*$", name or "")
    return match.group(1).strip() if match else ""


def title_category(name: str) -> str:
    """Category group from whole words in a product title, or "Other" when nothing matches."""
    text = name.lower()
    for group, pattern in TITLE_RULES:
        if re.search(rf"\b(?:{pattern})\b", text):
            return group
    return "Other"


def numeric(series: pd.Series) -> pd.Series:
    """Parse source numeric strings; unavailable values stay missing."""
    cleaned = series.str.replace(r"[₹,%\s]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce").replace([float("inf"), -float("inf")], float("nan"))


def category_parts(value: str, platform: str) -> list[str]:
    """Read each source's category syntax without executing source text."""
    if platform == "amazon":
        return value.split("|")
    try:
        parsed = json.loads(value)
        return parsed[0].split(" >> ") if isinstance(parsed, list) and parsed else []
    except (ValueError, TypeError, AttributeError):
        return []


def name_group(name: str) -> str:
    """Group matching titles and colour/size variants conservatively for evaluation."""
    value = re.sub(r"\([^)]*\)", "", name.lower())
    value = re.sub(r"\b(black|white|blue|red|green|grey|gray|pink|gold|silver|navy)\b", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    return value


def amazon_observed_at(links: pd.Series) -> pd.Series:
    """Recover the crawl time from the Unix timestamp in Amazon search links (qid=...)."""
    seconds = pd.to_numeric(links.str.extract(r"[?&]qid=(\d{9,11})")[0], errors="coerce")
    return pd.to_datetime(seconds, unit="s", utc=True).astype(str).replace("NaT", "")


def title_brand(names: pd.Series) -> pd.Series:
    """Amazon titles start with the brand name; take the first word as a derived brand."""
    return names.str.strip().str.split(r"\s+", n=1).str[0].str.strip(" ,-|").fillna("")


def normalize(platform: str, raw: pd.DataFrame) -> pd.DataFrame:
    """Map a source to common fields; listed price is not a historical price."""
    _, id_field, list_field = SOURCES[platform]
    amazon = platform == "amazon"
    category_field = "category" if amazon else "product_category_tree"
    parts = raw[category_field].map(lambda v: category_parts(v, platform))
    out = pd.DataFrame({"platform": platform, "source_row": raw.index + 2,
                        "product_id": raw[id_field], "name": raw.product_name,
                        "listed_price": numeric(raw[list_field]),
                        "selling_price": numeric(raw.discounted_price), "currency": "INR"})
    out["key"] = platform + ":" + out.product_id
    out["category_path"] = parts.map(lambda p: " > ".join(p))
    out["category_root"] = parts.map(lambda p: p[0] if p else "Unknown")
    out["category_group"] = out.category_root.map(ROOTS)
    broken = out.category_group.isna() & (parts.map(len) <= 1)
    out.loc[broken, "category_group"] = out.loc[broken, "name"].map(title_category)
    out["category_group"] = out.category_group.fillna("Other")
    out["category_source"] = "source_tree"
    out.loc[broken, "category_source"] = "title_keywords"
    # Three levels avoid Flipkart's brand/product-name leaves; this is a source category,
    # not a claim that every member is an interchangeable product.
    out["subcategory"] = parts.map(lambda p: " > ".join(p[:3]) if len(p) > 1 else "Unknown")
    out["rating"] = numeric(raw["rating" if amazon else "product_rating"])
    out.loc[~out.rating.between(0, 5), "rating"] = float("nan")
    if amazon:
        out["rating_count"] = numeric(raw.rating_count)
    else:
        # Flipkart marks unrated products "No rating available": that is zero ratings, not unknown.
        # Rated products carry no count in the source, so their count stays missing.
        out["rating_count"] = (raw.product_rating.str.strip() == "No rating available").map({True: 0.0, False: float("nan")})
    if amazon:
        out["brand"], out["brand_source"] = title_brand(raw.product_name), "title_first_word"
        out["variant"] = raw.product_name.map(amazon_variant)
    else:
        missing = raw.brand.str.strip() == ""
        out["brand"] = raw.brand.where(~missing, title_brand(raw.product_name))
        out["brand_source"] = missing.map({True: "title_first_word", False: "source_field"})
        out["variant"] = [flipkart_variant(spec, text) for spec, text
                          in zip(raw.product_specifications, raw.description, strict=True)]
    out["observed_at"] = (amazon_observed_at(raw.product_link) if amazon
                          else pd.to_datetime(raw.crawl_timestamp, utc=True).astype(str))
    out["provenance"] = "real"
    out["product_url"] = raw["product_link" if amazon else "product_url"]
    out["name_group"] = out.name.map(name_group)
    return out


def clean_source(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Quarantine ambiguous prices and deduplicate IDs without fabricating recency."""
    bad_price = (frame.listed_price.isna() | frame.selling_price.isna()
                 | (frame.listed_price <= 0) | (frame.selling_price <= 0)
                 | (frame.selling_price > frame.listed_price))
    reasons = pd.Series("", index=frame.index)
    reasons.loc[bad_price] = "invalid_or_missing_price"
    conflicts = frame.groupby("key")[["listed_price", "selling_price"]].nunique().max(axis=1)
    conflict_keys = set(conflicts[conflicts > 1].index)
    reasons.loc[frame.key.isin(conflict_keys)] = "conflicting_prices_without_reliable_history"
    candidates = frame[reasons == ""].copy()
    duplicates = candidates.duplicated("key", keep="first")
    reasons.loc[candidates.index[duplicates]] = "repeated_product_id_first_source_row_retained"
    clean = frame[reasons == ""].copy()
    clean["discount_pct"] = 100 * (1 - clean.selling_price / clean.listed_price)
    excluded = frame[reasons != ""].copy()
    excluded["reason"] = reasons[reasons != ""]
    summary = {"raw_rows": len(frame), "raw_unique_products": frame.key.nunique(),
               "clean_rows": len(clean), "exclusions": reasons[reasons != ""].value_counts().to_dict(),
               "missing_rating": int(clean.rating.isna().sum()),
               "missing_rating_count": int(clean.rating_count.isna().sum()),
               "conflicting_product_ids": sorted(conflict_keys)}
    return clean, excluded, summary


def build_catalogue() -> dict:
    """Write the combined catalogue and source hashes, leaving both originals intact."""
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    clean_frames, excluded_frames, sources = [], [], {}
    for platform, (path, _, _) in SOURCES.items():
        raw = pd.read_csv(path, dtype=str, keep_default_na=False)
        clean, excluded, summary = clean_source(normalize(platform, raw))
        clean_frames.append(clean)
        excluded_frames.append(excluded)
        sources[platform] = {**summary, "file": str(path.relative_to(DATA.parent)),
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    catalogue = pd.concat(clean_frames, ignore_index=True)
    catalogue.to_csv(PROCESSED / "catalogue.csv", index=False)
    pd.concat(excluded_frames, ignore_index=True).to_csv(PROCESSED / "excluded.csv", index=False)
    report = {"generated_at": datetime.now(UTC).isoformat(), "sources": sources,
              "combined_rows": len(catalogue), "synthetic_observations": 0,
              "authenticity_labels": 0,
              "recovered_fields": {
                  "amazon.observed_at": "Unix timestamp in each product link's qid parameter",
                  "brand": "Amazon, and Flipkart rows without a brand: first word of the title "
                           "(brand_source=title_first_word)",
                  "variant": "Flipkart specification fields (model ID, style code, colour, pattern...) or a model "
                             "code in the description; Amazon bracketed title suffix",
                  "flipkart.rating_count": "0 where the source says 'No rating available'; otherwise unknown",
                  "category_group": "source category root mapped to 16 groups; rows whose category field holds "
                                    "the product title are classified by title keywords (category_source)"},
              "policy": "Keep platforms distinct; no currency conversion; recovered fields are derived from "
                        "source text, never generated; quarantine all conflicting price IDs; retain first "
                        "source row for other duplicate IDs. Synthetic data lives in datasets/final with "
                        "provenance='synthetic'."}
    (REPORTS / "data_audit.json").write_text(json.dumps(report, indent=2))
    return report


def load_catalogue() -> pd.DataFrame:
    """Load generated data, requiring an explicit build if it is missing."""
    frame = pd.read_csv(PROCESSED / "catalogue.csv", dtype={"product_id": str})
    for column in ["brand", "observed_at", "subcategory", "category_path", "brand_source", "category_source",
                   "variant"]:
        frame[column] = frame[column].fillna("")
    return frame


if __name__ == "__main__":
    print(json.dumps(build_catalogue(), indent=2))
