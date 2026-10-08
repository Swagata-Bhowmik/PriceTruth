FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MPLCONFIGDIR=/tmp/price-truth-matplotlib XDG_CACHE_HOME=/tmp/price-truth-cache
WORKDIR /app
COPY pyproject.toml requirements.txt requirements.lock ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.lock && useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser app.py ./
COPY --chown=appuser:appuser views ./views
COPY --chown=appuser:appuser assets ./assets
COPY --chown=appuser:appuser docs/USER-GUIDE.html ./docs/USER-GUIDE.html
COPY --chown=appuser:appuser .streamlit ./.streamlit
COPY --chown=appuser:appuser datasets ./datasets
COPY --chown=appuser:appuser artifacts ./artifacts
COPY --chown=appuser:appuser reports/data_audit.json reports/model_evaluation.json reports/discount_model_evaluation.json ./reports/
COPY --chown=appuser:appuser reports/current/model_audit.json reports/current/collection_status.json ./reports/current/
RUN mkdir -p /app/reports && chown -R appuser:appuser /app
USER appuser
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
