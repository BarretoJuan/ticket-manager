FROM postgres:18

# Defaults (overridable via docker-compose environment / .env)
ENV POSTGRES_DB=ticket_manager \
    POSTGRES_USER=ticket_user \
    POSTGRES_PASSWORD=ticket_password

HEALTHCHECK --interval=5s --timeout=3s --retries=12 \
    CMD pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}