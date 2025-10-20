Docker run instructions

This project can be run inside a Python 3.11 Docker container to avoid local Python version issues when building binary packages like numpy/scipy.

Quick start (requires Docker and docker-compose):

1. Build the image and start the container:

```bash
docker-compose up --build
```

2. Open your browser at http://localhost:8000

Notes / troubleshooting:
- If port 8000 is already in use on your host, stop the service using it or edit `docker-compose.yml` to map a different host port (for example `"8001:8000"`).
- The container uses Python 3.11 and installs the packages from `requirements.txt`. If you still see build failures, post the full container log here and I'll help debug.
