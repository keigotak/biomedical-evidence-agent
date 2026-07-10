# BioClaim Auditor UI — containerized Streamlit front-end.
# The image installs the package with only the [ui] extra, so the default
# dependency-free core stays intact and no local Streamlit install is needed.
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for layer caching: copy only what the build needs.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir '.[ui]'

# App code + data (corpus/ontology) the UI reads at runtime.
COPY app.py ./
COPY data ./data

# Pin the data root explicitly: the package is installed non-editably into
# site-packages, so the ontology/corpus path must not depend on the module's
# location. Guarantees resolution to /app/data.
ENV BIOCLAIM_ROOT=/app

EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Bind to all interfaces so the port maps out of the container.
CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
