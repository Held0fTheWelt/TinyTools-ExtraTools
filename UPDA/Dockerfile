FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /opt/upda

COPY upda.py README.md ./
COPY static ./static

EXPOSE 8776

ENTRYPOINT ["python", "/opt/upda/upda.py", "--host", "0.0.0.0", "--port", "8776", "--state-root", "/workspace/Saved/UPDA"]
