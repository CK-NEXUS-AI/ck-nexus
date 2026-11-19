from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from .config import RoutePolicy
from .errors import GatewayError


@dataclass(frozen=True, slots=True)
class RouteMatch:
    policy: RoutePolicy
    upstream_base: str

    def target_url(self, request_path: str) -> str:
        base = self.upstream_base.rstrip("/") + "/"
        relative = request_path.lstrip("/")
        target = urljoin(base, relative)
        parsed_base = urlsplit(base)
        parsed_target = urlsplit(target)
        if (
            parsed_target.scheme not in {"http", "https"}
            or parsed_target.hostname != parsed_base.hostname
            or parsed_target.port != parsed_base.port
            or parsed_target.username
            or parsed_target.password
        ):
            raise GatewayError("UPSTREAM_BLOCKED", "Unsafe upstream target was blocked.", 502)
        return target


class RouteRegistry:
    def __init__(self, routes: tuple[RoutePolicy, ...], upstreams: dict[str, str]) -> None:
        self._routes = routes
        self._upstreams = dict(upstreams)

    def match(self, path: str, method: str) -> RouteMatch:
        method = method.upper()
        candidates = [
            route
            for route in self._routes
            if path == route.path_prefix or path.startswith(route.path_prefix.rstrip("/") + "/")
        ]
        candidates.sort(key=lambda item: len(item.path_prefix), reverse=True)
        for route in candidates:
            if method in route.methods:
                return RouteMatch(route, self._upstreams[route.upstream])
        raise GatewayError("ROUTE_NOT_FOUND", "No gateway route matches this request.", 404)
