"""drf-spectacular OpenAPI authentication extension for TicketJWTAuthentication.

Enables the Swagger UI "Authorize" button (HTTP Bearer / JWT).
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class TicketJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "infrastructure.orm.auth_backends.TicketJWTAuthentication"
    name = "jwtAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
