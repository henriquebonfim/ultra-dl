# UltraDL

UltraDL is a modern, high-performance video downloader web application. It leverages the power of `yt-dlp` for robust media extraction, wrapping it in a sleek, responsive React frontend and a scalable Flask backend.

![image](image.gif)

## 🚀 Features

-   **High-Quality Downloads**: Support for various video and audio formats.
-   **Advanced Trimming**: Trim videos before downloading with precision.
-   **Real-time Progress**: Live updates on download and conversion status via WebSocket.
-   **Queue Management**: Background processing with Celery for handling multiple downloads.
-   **Modern UI**: Beautiful, dark-mode first interface built with React, TailwindCSS, and shadcn/ui.
-   **Architecture**: Built with scalability in mind using Docker, Redis, and Feature-Sliced Design (FSD).

## 🛠 Tech Stack

### Frontend
-   **Framework**: React 18
-   **Build Tool**: Vite + Bun
-   **Styling**: TailwindCSS, shadcn/ui
-   **State/Query**: React Query
-   **Architecture**: Feature-Sliced Design (FSD)

### Backend
-   **Framework**: Flask (Python)
-   **Core Engine**: yt-dlp
-   **Task Queue**: Celery
-   **Broker/Cache**: Redis
-   **Real-time**: Flask-SocketIO

### Infrastructure
-   **Containerization**: Docker & Docker Compose
-   **Reverse Proxy**: Traefik

## 🏁 Getting Started

### Prerequisites
-   Docker and Docker Compose installed on your machine.
-   (Optional) Bun and Python 3.10+ for local development without Docker.

### Quick Start (Docker)

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/henriquebonfim/ultra-dl.git
    cd ultra-dl
    ```

2.  **Start the services**:
    ```bash
    docker-compose up -d --build
    ```

3.  **Access the application**:
    -   Frontend: [http://localhost](http://localhost) (via Traefik) or [http://localhost:8080](http://localhost:8080) (direct)
    -   Backend API: [http://localhost/api/v1](http://localhost/api/v1)

### Local Development

#### Frontend
```bash
cd frontend
bun install
bun run dev
```

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```
*Note: You will need a running Redis instance for the backend to function fully.*

## 📂 Project Structure

```
ultra-dl/
├── backend/                # Flask application
│   ├── src/                # Source code
│   └── tests/              # Pytest tests
├── frontend/               # React application
│   └── src/                # FSD structure (app, pages, features, etc.)
├── docker-compose.yml      # Service orchestration
└── ...
```

## 🤝 Contributing

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

Free for personal use, but commercial use requires a license from the author.
