# Copyright 2026 Process Control (https://www.processcontrol.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
import json
import logging
import math
import urllib.parse
import urllib.request

from odoo import models

_logger = logging.getLogger(__name__)

# Maximum number of geometry points returned to the browser. Real road
# geometries (OSRM full overview) can have tens of thousands of points;
# we downsample to keep the payload light for the Leaflet polyline.
MAX_GEOMETRY_POINTS = 400
# A suggested intermediate stable is only proposed if a real stop is found
# within this radius (km) of the ideal rest point along the route.
SUGGEST_MAX_DISTANCE_KM = 60.0
HTTP_TIMEOUT = 15


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in kilometres between two WGS84 points."""
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (math.sin(d_phi / 2.0) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2)
    return radius * 2.0 * math.asin(math.sqrt(a))


def _downsample(points, limit=MAX_GEOMETRY_POINTS):
    """Reduce a list of [lat, lng] points to at most ``limit`` items,
    always keeping the first and the last."""
    count = len(points)
    if count <= limit:
        return points
    step = count / float(limit)
    out = []
    index = 0.0
    while int(index) < count:
        out.append(points[int(index)])
        index += step
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


class PcTourRouter(models.AbstractModel):
    _name = "pc.tour.router"
    _description = "Tour Route Engine"

    # -- public API ----------------------------------------------------

    def compute_route(self, waypoints, transport=None):
        """Return the driving route across ``waypoints``.

        :param list waypoints: ordered list of ``[lat, lng]`` pairs.
        :param transport: optional ``pc.transport.config`` record whose
            average speed drives the duration estimate.
        :return dict: ``{provider, distance_km, duration_h, geometry}``
            where ``geometry`` is a list of ``[lat, lng]`` points.
        """
        clean = self._clean_waypoints(waypoints)
        if len(clean) < 2:
            return {
                "provider": "fallback",
                "distance_km": 0.0,
                "duration_h": 0.0,
                "geometry": clean,
            }

        result = None
        use_google = self._param_bool("pc_tour_builder.use_google")
        google_key = self._param("pc_tour_builder.google_key")
        if use_google and google_key:
            result = self._google_route(clean, google_key)
        if result is None:
            result = self._osrm_route(clean)
        if result is None:
            result = self._fallback_route(clean)

        result["geometry"] = _downsample(result["geometry"])
        result["distance_km"] = round(result["distance_km"], 1)
        result["duration_h"] = round(
            self._duration_h(result["distance_km"], transport), 2
        )
        return result

    def suggest_stops(self, origin, destination, transport):
        """Suggest intermediate stables along the origin→destination route.

        Splits the total distance into legs of ``max_hours_leg *
        avg_speed_kmh`` km and, at every cut point, picks the nearest
        published tour stop (never repeating one). Returns the ordered list
        of ``pc_tour_stop_data()`` dicts.
        """
        origin = self._point(origin)
        destination = self._point(destination)
        if origin is None or destination is None:
            return []
        route = self.compute_route([origin, destination], transport)
        geometry = route.get("geometry") or [origin, destination]

        speed = (transport.avg_speed_kmh if transport else 0) or 75.0
        max_hours = (transport.max_hours_leg if transport else 0) or 6.0
        leg_km = max(1.0, speed * max_hours)
        total_km = route.get("distance_km") or self._geometry_length(geometry)
        if total_km <= leg_km:
            return []

        cut_points = self._cut_points(geometry, leg_km)
        stops = self.env["product.template"].sudo().search([
            ("is_tour_stop", "=", True),
            ("is_published", "=", True),
            ("tour_latitude", "!=", 0),
        ])
        suggestions = []
        used = set()
        for cut_lat, cut_lng in cut_points:
            best = None
            best_dist = None
            for stop in stops:
                if stop.id in used:
                    continue
                dist = haversine_km(
                    cut_lat, cut_lng, stop.tour_latitude, stop.tour_longitude
                )
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best = stop
            if best is None:
                continue
            if best_dist is None or best_dist > SUGGEST_MAX_DISTANCE_KM:
                continue
            used.add(best.id)
            suggestions.append(best.pc_tour_stop_data())
        return suggestions

    # -- helpers -------------------------------------------------------

    def _duration_h(self, distance_km, transport):
        speed = (transport.avg_speed_kmh if transport else 0) or 75.0
        return distance_km / speed

    def _clean_waypoints(self, waypoints):
        out = []
        for raw in waypoints or []:
            point = self._point(raw)
            if point is not None:
                out.append(point)
        return out

    def _point(self, raw):
        try:
            lat = float(raw[0])
            lng = float(raw[1])
        except (TypeError, ValueError, IndexError, KeyError):
            return None
        if lat == 0.0 and lng == 0.0:
            return None
        return [lat, lng]

    def _geometry_length(self, geometry):
        total = 0.0
        for i in range(1, len(geometry)):
            total += haversine_km(
                geometry[i - 1][0], geometry[i - 1][1],
                geometry[i][0], geometry[i][1],
            )
        return total

    def _cut_points(self, geometry, leg_km):
        """Walk the geometry and return points at every ``leg_km`` of
        accumulated distance (excluding the final destination)."""
        cuts = []
        target = leg_km
        accumulated = 0.0
        for i in range(1, len(geometry)):
            prev = geometry[i - 1]
            curr = geometry[i]
            seg = haversine_km(prev[0], prev[1], curr[0], curr[1])
            while accumulated + seg >= target:
                ratio = 0.0
                if seg > 0:
                    ratio = (target - accumulated) / seg
                lat = prev[0] + (curr[0] - prev[0]) * ratio
                lng = prev[1] + (curr[1] - prev[1]) * ratio
                cuts.append([lat, lng])
                target += leg_km
            accumulated += seg
        return cuts

    def _param(self, key):
        return self.env["ir.config_parameter"].sudo().get_param(key)

    def _param_bool(self, key):
        value = self._param(key)
        return str(value).lower() in ("1", "true", "yes")

    def _http_json(self, url):
        request = urllib.request.Request(
            url, headers={"User-Agent": "pc_tour_builder/1.0"}
        )
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))

    def _osrm_route(self, waypoints):
        try:
            coords = ";".join(
                "%s,%s" % (point[1], point[0]) for point in waypoints
            )
            url = (
                "https://router.project-osrm.org/route/v1/driving/%s"
                "?overview=full&geometries=geojson" % coords
            )
            data = self._http_json(url)
            route = (data.get("routes") or [None])[0]
            if not route:
                return None
            geometry = [
                [coord[1], coord[0]]
                for coord in route["geometry"]["coordinates"]
            ]
            return {
                "provider": "osrm",
                "distance_km": route["distance"] / 1000.0,
                "duration_h": route["duration"] / 3600.0,
                "geometry": geometry or waypoints,
            }
        except Exception as error:  # noqa: BLE001 - demo must never break
            _logger.warning("OSRM route failed, falling back: %s", error)
            return None

    def _google_route(self, waypoints, key):
        try:
            origin = "%s,%s" % (waypoints[0][0], waypoints[0][1])
            destination = "%s,%s" % (waypoints[-1][0], waypoints[-1][1])
            params = {
                "origin": origin,
                "destination": destination,
                "key": key,
                "mode": "driving",
            }
            middle = waypoints[1:-1]
            if middle:
                params["waypoints"] = "|".join(
                    "%s,%s" % (point[0], point[1]) for point in middle
                )
            url = (
                "https://maps.googleapis.com/maps/api/directions/json?%s"
                % urllib.parse.urlencode(params)
            )
            data = self._http_json(url)
            route = (data.get("routes") or [None])[0]
            if not route:
                return None
            distance_m = 0.0
            geometry = []
            for leg in route.get("legs", []):
                for step in leg.get("steps", []):
                    distance_m += step.get("distance", {}).get("value", 0)
                    start = step.get("start_location") or {}
                    geometry.append([start.get("lat"), start.get("lng")])
                    end = step.get("end_location") or {}
                    geometry.append([end.get("lat"), end.get("lng")])
            geometry = [p for p in geometry if p[0] is not None]
            return {
                "provider": "google",
                "distance_km": distance_m / 1000.0,
                "duration_h": 0.0,
                "geometry": geometry or waypoints,
            }
        except Exception as error:  # noqa: BLE001 - demo must never break
            _logger.warning("Google route failed, falling back: %s", error)
            return None

    def _fallback_route(self, waypoints):
        return {
            "provider": "fallback",
            "distance_km": self._geometry_length(waypoints),
            "duration_h": 0.0,
            "geometry": waypoints,
        }
