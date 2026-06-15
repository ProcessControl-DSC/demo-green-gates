# Copyright 2026 Process Control (https://www.processcontrol.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import fields, models


class PcTransportConfig(models.Model):
    _name = "pc.transport.config"
    _description = "Tour Transport Configuration"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    vehicle_type = fields.Char(string="Vehicle Type")
    avg_speed_kmh = fields.Float(
        string="Average Speed (km/h)",
        default=75.0,
        help="Average driving speed used to estimate the tour duration.",
    )
    max_hours_leg = fields.Float(
        string="Max Driving Hours per Leg",
        default=6.0,
        help="Maximum continuous driving hours before a rest stop is needed "
             "for the animals. Used to suggest intermediate stables.",
    )
    rest_hours = fields.Float(
        string="Rest Hours",
        default=1.0,
        help="Rest time after each driving leg (informative).",
    )
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
