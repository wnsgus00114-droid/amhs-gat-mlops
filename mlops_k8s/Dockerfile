FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY mlops_k8s/requirements.txt mlops_k8s/requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install -r mlops_k8s/requirements.txt

COPY mlops_k8s mlops_k8s
COPY pororo pororo
COPY outputs/fab_oht_blue_congestion_original_layout_1600x900_no_overlap_v3.gif outputs/fab_oht_blue_congestion_original_layout_1600x900_no_overlap_v3.gif

EXPOSE 8501

CMD ["streamlit", "run", "mlops_k8s/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
