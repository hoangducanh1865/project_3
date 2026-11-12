FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir numpy pandas pyarrow fastapi "uvicorn[standard]" huggingface_hub
RUN git clone https://github.com/jackwilkie/CLOSR /opt/CLOSR && git -C /opt/CLOSR checkout 79da4d1f2a6f4e5ecf92c4588195aaf163df40f8
ENV CLOSR_DIR=/opt/CLOSR PYTHONUNBUFFERED=1
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
COPY --chown=user . .
USER user
EXPOSE 7860
CMD ["uvicorn", "app:api", "--host", "0.0.0.0", "--port", "7860"]
