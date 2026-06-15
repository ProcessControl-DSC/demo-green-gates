# Copyright 2026 Process Control (https://www.processcontrol.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from unittest.mock import patch

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.exceptions import UserError
from odoo.tests.common import HttpCase, TransactionCase


class TestTourBuilder(TransactionCase):
    """Tests for sale.order.pc_create_tour_order."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.stop_a = cls.env["product.template"].create(
            {
                "name": "Test Stop Burgos",
                "default_code": "TST-ES-01",
                "type": "service",
                "list_price": 60.0,
                "is_published": True,
                "is_tour_stop": True,
                "tour_latitude": 42.34,
                "tour_longitude": -3.68,
                "tour_capacity": 100,
            }
        )
        cls.stop_b = cls.env["product.template"].create(
            {
                "name": "Test Stop Dijon",
                "default_code": "TST-FR-01",
                "type": "service",
                "list_price": 60.0,
                "is_published": True,
                "is_tour_stop": True,
                "tour_latitude": 47.33,
                "tour_longitude": 5.16,
                "tour_capacity": 25,
            }
        )

    def test_create_tour_order_creates_one_line_per_stop(self):
        result = self.env["sale.order"].pc_create_tour_order(
            {"name": "Test Rider", "email": "rider@example.test"},
            [
                {"template_id": self.stop_b.id, "plaza": "box",
                 "date": "2026-07-02", "nights": 1, "horses": 4},
                {"template_id": self.stop_a.id, "plaza": "box",
                 "date": "2026-07-03", "nights": 2, "horses": 4},
            ],
        )
        order = self.env["sale.order"].browse(result["id"])
        self.assertEqual(order.state, "draft")
        self.assertEqual(len(order.order_line), 2)
        # stops are sorted by date: Dijon (02/07) first
        self.assertIn("TST-FR-01", order.order_line[0].name)
        self.assertEqual(order.order_line[0].product_uom_qty, 4)
        self.assertEqual(order.order_line[0].price_unit, 60.0)
        # second stop spans 2 nights -> price_unit doubled
        self.assertEqual(order.order_line[1].price_unit, 120.0)
        self.assertIn("02/07/2026", order.order_line[0].name)
        # visible in the Rental app, spanning the whole tour, prices intact
        self.assertTrue(order.is_rental_order)
        self.assertTrue(all(order.order_line.mapped("is_rental")))
        self.assertEqual(order.rental_start_date.strftime("%Y-%m-%d"),
                         "2026-07-02")
        self.assertEqual(order.rental_return_date.strftime("%Y-%m-%d"),
                         "2026-07-05")
        self.assertEqual(order.order_line[0].price_unit, 60.0)
        self.assertEqual(order.order_line[1].price_unit, 120.0)

    def test_partner_is_reused_by_email(self):
        payload = [{"template_id": self.stop_a.id, "plaza": "grass",
                    "date": "2026-07-10", "nights": 1, "horses": 1}]
        res1 = self.env["sale.order"].pc_create_tour_order(
            {"name": "Repeat Rider", "email": "repeat@example.test"}, payload)
        res2 = self.env["sale.order"].pc_create_tour_order(
            {"name": "Repeat Rider", "email": "REPEAT@example.test"}, payload)
        o1 = self.env["sale.order"].browse(res1["id"])
        o2 = self.env["sale.order"].browse(res2["id"])
        self.assertEqual(o1.partner_id, o2.partner_id)

    def test_stop_with_checkin_and_extras(self):
        extra = self.env["product.product"].create(
            {
                "name": "Test Electricity",
                "default_code": "SRV-TEST",
                "type": "service",
                "list_price": 5.0,
            }
        )
        result = self.env["sale.order"].pc_create_tour_order(
            {"name": "Extra Rider", "email": "extra@example.test",
             "rider": "John Groom", "stallion": "Sí",
             "payment_pref": "Tarjeta"},
            [{"template_id": self.stop_a.id, "plaza": "box",
              "date": "2026-07-05", "nights": 2, "horses": 3,
              "checkin": "Tarde",
              "extras": [{"code": "SRV-TEST", "qty": 2}]}],
        )
        order = self.env["sale.order"].browse(result["id"])
        self.assertEqual(len(order.order_line), 2)
        self.assertIn("Check-in: Tarde", order.order_line[0].name)
        self.assertEqual(order.order_line[1].product_id, extra)
        self.assertEqual(order.order_line[1].product_uom_qty, 2)
        self.assertIn("Stop 1", order.order_line[1].name)
        self.assertIn("John Groom", order.note or "")

    def test_empty_tour_raises(self):
        with self.assertRaises(UserError):
            self.env["sale.order"].pc_create_tour_order(
                {"name": "X", "email": "x@example.test"}, [])

    def test_missing_email_raises(self):
        with self.assertRaises(UserError):
            self.env["sale.order"].pc_create_tour_order(
                {"name": "X"},
                [{"template_id": self.stop_a.id, "plaza": "box",
                  "date": "2026-07-02", "nights": 1, "horses": 1}])


class TestTourPage(HttpCase):
    def test_tour_page_renders(self):
        response = self.url_open("/tour")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"pc_tour_map", response.content)


class TestTransportConfig(TransactionCase):
    """Tests for the pc.transport.config model and seed data."""

    def test_seed_records_exist(self):
        truck = self.env.ref(
            "pc_tour_builder.transport_config_large_truck"
        )
        van = self.env.ref(
            "pc_tour_builder.transport_config_small_van"
        )
        self.assertEqual(truck.avg_speed_kmh, 75.0)
        self.assertEqual(truck.max_hours_leg, 6.0)
        self.assertEqual(van.avg_speed_kmh, 90.0)
        self.assertEqual(van.max_hours_leg, 4.5)

    def test_create_transport_config(self):
        cfg = self.env["pc.transport.config"].create(
            {"name": "Test Lorry", "avg_speed_kmh": 80.0,
             "max_hours_leg": 5.0, "rest_hours": 1.0}
        )
        self.assertTrue(cfg.active)
        self.assertEqual(cfg.company_id, self.env.company)


class TestTourRouter(TransactionCase):
    """Tests for the pc.tour.router engine (no network: forced fallback)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.router = cls.env["pc.tour.router"]
        # force the external providers off so the engine uses the
        # haversine fallback and the tests stay offline-deterministic
        cls.env["ir.config_parameter"].sudo().set_param(
            "pc_tour_builder.use_google", "False"
        )
        cls.patcher_osrm = patch.object(
            type(cls.router), "_osrm_route", return_value=None
        )
        cls.patcher_google = patch.object(
            type(cls.router), "_google_route", return_value=None
        )
        cls.patcher_osrm.start()
        cls.patcher_google.start()
        cls.addClassCleanup(cls.patcher_osrm.stop)
        cls.addClassCleanup(cls.patcher_google.stop)
        # Origin (40,-4) -> Destination (44,4) is ~796 km on the straight
        # fallback geometry. A leg of 400 km (5 h x 80 km/h) puts the single
        # cut point at the midpoint (~42, 0), where MID sits ~2 km away.
        cls.origin = [40.0, -4.0]
        cls.destination = [44.0, 4.0]
        cls.mid = cls.env["product.template"].create({
            "name": "Router Mid", "default_code": "RT-MID",
            "type": "service", "is_published": True, "is_tour_stop": True,
            "tour_latitude": 42.0, "tour_longitude": 0.0,
        })
        # an unpublished stop must never be suggested
        cls.hidden = cls.env["product.template"].create({
            "name": "Router Hidden", "default_code": "RT-HID",
            "type": "service", "is_published": False, "is_tour_stop": True,
            "tour_latitude": 42.0, "tour_longitude": 0.05,
        })
        cls.transport = cls.env["pc.transport.config"].create({
            "name": "Router Truck", "avg_speed_kmh": 80.0,
            "max_hours_leg": 5.0, "rest_hours": 1.0,
        })

    def test_compute_route_fallback_has_distance(self):
        result = self.router.compute_route(
            [self.origin, self.destination], self.transport
        )
        self.assertEqual(result["provider"], "fallback")
        self.assertGreater(result["distance_km"], 0.0)
        # duration uses the transport speed, not the provider's
        expected = result["distance_km"] / 80.0
        self.assertAlmostEqual(result["duration_h"], round(expected, 2),
                               places=2)
        self.assertGreaterEqual(len(result["geometry"]), 2)

    def test_compute_route_too_few_points(self):
        result = self.router.compute_route([self.origin], self.transport)
        self.assertEqual(result["distance_km"], 0.0)

    def test_suggest_picks_intermediate_stop(self):
        suggestions = self.router.suggest_stops(
            self.origin, self.destination, self.transport
        )
        codes = [s["code"] for s in suggestions]
        # the published midpoint stop is suggested at the leg cut
        self.assertIn("RT-MID", codes)
        # the unpublished stop is never suggested
        self.assertNotIn("RT-HID", codes)

    def test_suggest_short_route_returns_empty(self):
        # a 400 km leg over a ~15 km route never needs an intermediate stop
        suggestions = self.router.suggest_stops(
            [42.0, 0.0], [42.1, 0.0], self.transport
        )
        self.assertEqual(suggestions, [])
