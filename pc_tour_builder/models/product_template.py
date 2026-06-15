# Copyright 2026 Process Control (https://www.processcontrol.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_tour_stop = fields.Boolean(
        string="Tour Stop",
        help="Published on the tour builder landing as a bookable stop.",
    )
    tour_latitude = fields.Float(string="Latitude", digits=(10, 6))
    tour_longitude = fields.Float(string="Longitude", digits=(10, 6))
    tour_capacity = fields.Integer(
        string="Stop Capacity",
        help="Number of stalls available at this stop (informative).",
    )
    is_tour_extra = fields.Boolean(
        string="Tour Extra Service",
        help="Offered as a per-stop optional service on the tour builder.",
    )
    tour_extra_pricing = fields.Selection(
        [("flat", "Per booking"),
         ("per_night", "Per night"),
         ("per_horse_night", "Per horse and night")],
        string="Extra Charged",
        default="flat",
        help="How the optional service quantity is computed on the tour.",
    )

    def pc_tour_stop_data(self):
        """Return the JSON-serializable payload used by the /tour landing."""
        self.ensure_one()
        prices = {"grass": self.list_price, "box": self.list_price}
        for pricing in self.env["product.pricing"].search(
            [("product_template_id", "=", self.id)]
        ):
            names = ", ".join(pricing.product_variant_ids.mapped("display_name"))
            if "Box" in names:
                prices["box"] = pricing.price
            else:
                prices["grass"] = pricing.price
        # multi-variant templates do not expose default_code at template
        # level: fall back to the first variant's code
        code = self.default_code or self.product_variant_ids[:1].default_code
        return {
            "id": self.id,
            "name": self.name,
            "code": code or "",
            "lat": self.tour_latitude,
            "lng": self.tour_longitude,
            "capacity": self.tour_capacity,
            "prices": prices,
            "img": "/web/image/product.template/%s/image_512" % self.id,
        }
