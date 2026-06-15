# Copyright 2026 Process Control (https://www.processcontrol.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
import json

from markupsafe import Markup

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request


class TourBuilderController(http.Controller):

    @http.route("/tour", type="http", auth="public", website=True, sitemap=True)
    def tour_page(self, **kwargs):
        templates = request.env["product.template"].sudo().search(
            [
                ("is_tour_stop", "=", True),
                ("is_published", "=", True),
                ("tour_latitude", "!=", 0),
            ]
        )
        stops = [t.pc_tour_stop_data() for t in templates]
        # Optional services are configured per product with the
        # "Tour Extra Service" checkbox; each carries its own charge rule.
        extra_templates = request.env["product.template"].sudo().search(
            [("is_tour_extra", "=", True), ("sale_ok", "=", True)],
            order="name",
        )
        extras = []
        for tmpl in extra_templates:
            variant = tmpl.product_variant_ids[:1]
            if not variant:
                continue
            extras.append({
                "code": variant.default_code or "",
                "name": tmpl.name,
                "price": tmpl.list_price,
                "pricing": tmpl.tour_extra_pricing or "flat",
            })
        return request.render(
            "pc_tour_builder.tour_page",
            {
                "stops_json": Markup(json.dumps(stops, ensure_ascii=False)),
                "extras_json": Markup(json.dumps(extras, ensure_ascii=False)),
            },
        )

    @http.route(
        "/tour/submit",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def tour_submit(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.get_data() or b"{}")
        except ValueError:
            return request.make_json_response(
                {"error": "Invalid request"}, status=400
            )
        try:
            result = (
                request.env["sale.order"]
                .sudo()
                .pc_create_tour_order(
                    payload.get("customer") or {}, payload.get("stops") or []
                )
            )
            return request.make_json_response(result)
        except (UserError, ValidationError) as error:
            return request.make_json_response(
                {"error": str(error)}, status=400
            )
