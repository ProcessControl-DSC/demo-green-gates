# Copyright 2026 Process Control (https://www.processcontrol.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from datetime import datetime, timedelta

from odoo import _, api, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def pc_create_tour_order(self, customer, stops):
        """Create a draft quotation from a tour builder request.

        :param dict customer: {'name', 'email', 'phone'}
        :param list stops: [{'template_id', 'plaza' ('box'|'grass'),
                             'date' 'YYYY-MM-DD', 'nights', 'horses'}]
        :return dict: {'id', 'name', 'amount_total'}
        """
        if not stops:
            raise UserError(_("A tour needs at least one stop."))
        email = (customer.get("email") or "").strip().lower()
        name = (customer.get("name") or "").strip()
        if not email or not name:
            raise UserError(_("Name and email are required."))

        partner = self.env["res.partner"].search(
            [("email", "=ilike", email)], limit=1
        )
        if not partner:
            partner = self.env["res.partner"].create(
                {
                    "name": name,
                    "email": email,
                    "phone": customer.get("phone"),
                    "customer_rank": 1,
                }
            )

        lines = []
        stops = sorted(stops, key=lambda s: s.get("date") or "")
        for index, stop in enumerate(stops, start=1):
            template = self.env["product.template"].browse(
                int(stop.get("template_id"))
            )
            if not template.exists() or not template.is_tour_stop:
                raise UserError(_("Stop %s is not available.") % index)
            nights = max(1, int(stop.get("nights") or 1))
            horses = max(1, int(stop.get("horses") or 1))
            plaza = stop.get("plaza") or "box"
            wanted = "Box" if plaza == "box" else "hierba"
            variant = template.product_variant_ids.filtered(
                lambda v: wanted.lower() in v.display_name.lower()
            )[:1] or template.product_variant_ids[:1]
            prices = template.pc_tour_stop_data()["prices"]
            price_night = prices["box"] if plaza == "box" else prices["grass"]
            try:
                start = datetime.strptime(stop.get("date"), "%Y-%m-%d")
            except (TypeError, ValueError):
                raise UserError(_("Stop %s has an invalid date.") % index)
            end = start + timedelta(days=nights)
            lines.append(
                (0, 0, {
                    "product_id": variant.id,
                    "product_uom_qty": horses,
                    "price_unit": price_night * nights,
                    "name": _(
                        "%(product)s\nStop %(index)s · %(start)s 12:00 → "
                        "%(end)s 12:00 · %(horses)s horses × %(nights)s "
                        "night(s) · %(code)s",
                        product=variant.display_name,
                        index=index,
                        start=start.strftime("%d/%m/%Y"),
                        end=end.strftime("%d/%m/%Y"),
                        horses=horses,
                        nights=nights,
                        code=template.default_code
                        or variant.default_code or "",
                    ),
                })
            )

        order = self.create(
            {
                "partner_id": partner.id,
                "origin": "Tour Builder Web",
                "client_order_ref": _("WEB TOUR · %s stops") % len(stops),
                "require_signature": True,
                "require_payment": True,
                "order_line": lines,
            }
        )
        order.activity_schedule(
            "mail.mail_activity_data_todo",
            summary=_("Validate web tour request"),
            note=_(
                "Tour requested from the website by %s. Review the stops, "
                "adjust if needed and send the quotation for signature and "
                "down payment."
            ) % partner.name,
        )
        return {
            "id": order.id,
            "name": order.name,
            "amount_total": order.amount_total,
        }
