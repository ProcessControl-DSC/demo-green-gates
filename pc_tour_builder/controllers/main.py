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
        # Transport options drive the route duration and the suggestion of
        # intermediate stops, so the visitor can pick the vehicle.
        transports = []
        for cfg in request.env["pc.transport.config"].sudo().search(
            [("active", "=", True)], order="name"
        ):
            transports.append({
                "id": cfg.id,
                "name": cfg.name,
                "vehicle_type": cfg.vehicle_type or "",
                "avg_speed_kmh": cfg.avg_speed_kmh,
                "max_hours_leg": cfg.max_hours_leg,
            })
        return request.render(
            "pc_tour_builder.tour_page",
            {
                "stops_json": Markup(json.dumps(stops, ensure_ascii=False)),
                "extras_json": Markup(json.dumps(extras, ensure_ascii=False)),
                "transports_json": Markup(
                    json.dumps(transports, ensure_ascii=False)
                ),
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

    def _transport(self, transport_config_id):
        if not transport_config_id:
            return None
        try:
            cfg = request.env["pc.transport.config"].sudo().browse(
                int(transport_config_id)
            )
        except (TypeError, ValueError):
            return None
        return cfg if cfg.exists() else None

    @http.route(
        "/tour/route",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def tour_route(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.get_data() or b"{}")
        except ValueError:
            return request.make_json_response(
                {"error": "Invalid request"}, status=400
            )
        waypoints = payload.get("waypoints") or []
        transport = self._transport(payload.get("transport_config_id"))
        result = request.env["pc.tour.router"].sudo().compute_route(
            waypoints, transport
        )
        return request.make_json_response(result)

    @http.route(
        "/tour/suggest",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def tour_suggest(self, **kwargs):
        try:
            payload = json.loads(request.httprequest.get_data() or b"{}")
        except ValueError:
            return request.make_json_response(
                {"error": "Invalid request"}, status=400
            )
        origin = payload.get("origin")
        destination = payload.get("destination")
        transport = self._transport(payload.get("transport_config_id"))
        router = request.env["pc.tour.router"].sudo()
        suggestion = router.suggest_stops(origin, destination, transport)
        suggestions = suggestion["stops"]
        # Also return the full route so the client can draw the road
        # polyline in one round-trip.
        waypoints = [origin]
        waypoints += [[s["lat"], s["lng"]] for s in suggestions]
        waypoints.append(destination)
        route = router.compute_route(waypoints, transport)
        return request.make_json_response({
            "suggestions": suggestions,
            "route": route,
            "required_stops": suggestion["required_stops"],
            "network_insufficient": suggestion["network_insufficient"],
        })
