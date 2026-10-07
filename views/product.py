"""Price check page."""
from price_truth.resources import catalogue, discount_model, model
from price_truth.ui import product_page

product_page(catalogue(), model, discount_model)
