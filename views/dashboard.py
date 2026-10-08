"""Product dashboard: dropdown selection, then every analysis on one scrolling page."""
from price_truth.dashboard import dashboard_page
from price_truth.resources import catalogue, discount_model

dashboard_page(catalogue(), discount_model)
