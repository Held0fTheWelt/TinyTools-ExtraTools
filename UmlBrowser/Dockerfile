FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

ARG PLANTUML_VERSION=1.2026.6
ARG PLANTUML_SHA256=89948f14c93756c7a3fb7b69078ff37e8489fd79dd430c582b931e2f65358690

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        default-jre-headless \
        graphviz \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/plantuml \
    && curl -fsSL -o /opt/plantuml/plantuml.jar "https://github.com/plantuml/plantuml/releases/download/v${PLANTUML_VERSION}/plantuml-${PLANTUML_VERSION}.jar" \
    && echo "${PLANTUML_SHA256}  /opt/plantuml/plantuml.jar" | sha256sum -c - \
    && printf '%s\n' '#!/bin/sh' 'exec java -Djava.awt.headless=true -jar /opt/plantuml/plantuml.jar "$@"' > /usr/local/bin/plantuml \
    && chmod +x /usr/local/bin/plantuml

WORKDIR /opt/uml-browser

COPY uml_browser.py README.md ./
COPY static ./static

EXPOSE 8765

ENTRYPOINT ["python", "/opt/uml-browser/uml_browser.py", "--host", "0.0.0.0", "--port", "8765", "--uml-root", "/workspace/UML", "--cache-root", "/workspace/Saved/UmlBrowser"]
