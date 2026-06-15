# Copyright 2026 Process Control (https://www.processcontrol.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pc_tour_use_google = fields.Boolean(
        string="Use Google Maps for route calculation",
        config_parameter="pc_tour_builder.use_google",
        help="By default the free OSRM router is used. Enable this to use the "
             "Google Directions API (paid, requires an API key).",
    )
    pc_tour_google_key = fields.Char(
        string="Google Maps API Key",
        config_parameter="pc_tour_builder.google_key",
        help="API key for the Google Directions API.",
    )
