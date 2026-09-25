"""The one place to change what the pipeline covers. fetch.py and build.py both read this.

To add a neighborhood: add a (name, cluster) row below using the exact name from Denver's
Statistical Neighborhood layer (78 names; see handbook/DATA.md), then push. The next run pulls it.
Order here is the display order on the dashboard (grouped by cluster).
"""

NEIGHBORHOODS = [
    ("Berkeley", "Northwest"), ("Sunnyside", "Northwest"), ("West Highland", "Northwest"),
    ("Highland", "Northwest"), ("Sloan Lake", "Northwest"),
    ("City Park West", "Central"), ("City Park", "Central"), ("Congress Park", "Central"),
    ("Cheesman Park", "Central"), ("Cherry Creek", "Central"),
    ("Washington Park West", "Southeast"), ("Washington Park", "Southeast"), ("Platt Park", "Southeast"),
    ("University", "Southeast"), ("University Park", "Southeast"), ("Cory - Merrill", "Southeast"),
    ("Belcaro", "Southeast"),
]

# Denver's official names that read badly on screen.
DISPLAY = {"Cory - Merrill": "Cory-Merrill"}

# Deed types treated as market sales: warranty, special warranty, general warranty, estate (personal rep).
MARKET_DEEDS = {"WD", "SW", "GW", "PR"}

TARGETS = dict(NEIGHBORHOODS)  # name -> cluster
