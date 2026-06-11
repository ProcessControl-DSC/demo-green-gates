# Copyright 2026 Process Control (https://www.processcontrol.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
{
    "name": "Tour Builder (Process Control)",
    "version": "19.0.1.0.0",
    "summary": "Multi-stop tour booking landing: build a route on the map "
               "and request the whole tour in one quotation",
    "description": """
Landing page (/tour) where the visitor builds a multi-stop tour on an
interactive map (one stop per night, choosing place type and number of
horses) and submits the whole route as a single quotation, ready for the
internal validation, online signature and 50% down payment flow.

Solución desarrollada por Process Control.
    """,
    "author": "Process Control",
    "website": "https://www.processcontrol.es",
    "license": "LGPL-3",
    "category": "Website/Website",
    "depends": ["website_sale"],
    "data": [
        "views/product_views.xml",
        "views/tour_templates.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
