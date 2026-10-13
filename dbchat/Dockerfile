FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

RUN mkdir -p /data
ENV METADATA_DB_PATH=/data/dbchat_metadata.db

EXPOSE 8501

CMD ["streamlit", "run", "src/dbchat/ui/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
