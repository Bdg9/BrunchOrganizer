FROM python:3.12-slim

# Utilisateur sans privilèges ; /data est le seul dossier où l'application écrit.
RUN useradd --system --uid 10001 --no-create-home brunch \
    && mkdir /data && chown brunch /data

WORKDIR /app
COPY server.py ./
COPY static ./static

ENV HOST=0.0.0.0 \
    PORT=8080 \
    DATA_FILE=/data/data.json \
    PYTHONUNBUFFERED=1

USER brunch
VOLUME /data
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/state', timeout=2)"

CMD ["python", "server.py"]
