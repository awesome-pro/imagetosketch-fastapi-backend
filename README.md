# 🎨 ImageToSketch FastAPI Backend

## [🔗 API Documentation](https://sketchbackend.abhinandan.pro/docs)
<img width="720" height="404" alt="Screenshot 2025-09-11 at 7 48 25 AM" src="https://github.com/user-attachments/assets/b5e78439-e548-4984-9e21-78a5c9f82a2d" />


[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-009485?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![AWS S3](https://img.shields.io/badge/AWS_S3-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)](https://aws.amazon.com/s3/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

> **A high-performance, production-ready FastAPI backend service that transforms images into artistic sketches using advanced computer vision algorithms and modern cloud architecture.**

## 🚀 Features

### 🔥 Core Capabilities
- **Advanced Image Processing**: Convert images to sketches using OpenCV and NumPy algorithms
- **Real-time Processing**: Asynchronous image processing with progress tracking
- **Cloud Storage**: Seamless AWS S3 integration for scalable file storage
- **WebSocket Notifications**: Real-time in-session updates for processing status
- **Background Tasks**: Non-blocking image processing with FastAPI's background tasks

### 🔐 Authentication & Security
- **Google OAuth 2.0**: Secure social authentication integration
- **JWT Tokens**: Stateless authentication with refresh token support
- **Redis Session Management**: High-performance session storage and caching
- **Rate Limiting**: Built-in protection against abuse and DDoS attacks

### 📊 Database & Performance
- **PostgreSQL**: Robust relational database with ACID compliance
- **SQLAlchemy 2.0**: Modern async ORM with type safety
- **Alembic Migrations**: Version-controlled database schema management
- **Connection Pooling**: Optimized database connections for scalability

### 🛠 Developer Experience
- **Type Safety**: Full Pydantic integration with automatic validation
- **API Documentation**: Auto-generated Swagger/OpenAPI documentation
- **Code Quality**: Black, isort, and MyPy for consistent, type-safe code
- **Testing**: Comprehensive test suite with pytest
- **Docker Ready**: Production-optimized containerization

## 🏗 Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Next.js       │    │   FastAPI        │    │   PostgreSQL    │
│   Frontend      │◄──►│   Backend        │◄──►│   Database      │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                           
                              ▼                           
                    ┌──────────────────┐                  
                    │   Redis Cache    │                  
                    │   & Sessions     │                  
                    └──────────────────┘                  
                              │                           
                              ▼                           
                    ┌──────────────────┐                  
                    │   AWS S3         │                  
                    │   File Storage   │                  
                    └──────────────────┘                  
```

## 📦 Tech Stack

| Category | Technologies |
|----------|-------------|
| **Framework** | FastAPI 0.116.1, Uvicorn, Starlette |
| **Database** | PostgreSQL, SQLAlchemy 2.0, Alembic |
| **Cache** | Redis 5.2.1 |
| **Authentication** | Google OAuth 2.0, JWT (python-jose) |
| **Image Processing** | OpenCV 4.10.0, NumPy 1.26.4, Pillow |
| **Cloud Storage** | AWS S3 (boto3), AWS SDK |
| **Development** | Black, isort, MyPy, pytest |
| **Deployment** | Docker, Docker Compose |

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose (optional)

### 1. Clone & Setup

```bash
git clone https://github.com/awesome-pro/imagetosketch-fastapi-backend.git
cd imagetosketch-fastapi-backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/imagetosketch
DATABASE_TEST_URL=postgresql://username:password@localhost:5432/imagetosketch_test

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
SECRET_KEY=your-super-secret-jwt-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/callback

# AWS S3
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=imagetosketch-storage

# Application
ENVIRONMENT=development
API_V1_STR=/api/v1
PROJECT_NAME="ImageToSketch API"
CORS_ORIGINS=["http://localhost:3000"]
```

### 3. Database Setup

```bash
# Run migrations
alembic upgrade head

# Create initial data (optional)
python -m app.core.init_db
```

### 4. Run the Application

```bash
# Development mode with hot reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 5. Docker Deployment (Recommended)

```bash
# Build and run with Docker Compose
docker-compose up --build -d

# View logs
docker-compose logs -f api
```

## 📡 API Endpoints

### Authentication
- `POST /api/v1/auth/google` - Google OAuth authentication
- `POST /api/v1/auth/refresh` - Refresh JWT tokens
- `POST /api/v1/auth/logout` - Logout user

### Image Processing
- `POST /api/v1/images/upload` - Upload image for processing
- `GET /api/v1/images/{image_id}` - Get image details
- `POST /api/v1/images/{image_id}/process` - Convert image to sketch
- `GET /api/v1/images/{image_id}/download` - Download processed sketch

### User Management
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update user profile
- `GET /api/v1/users/me/images` - Get user's images

### WebSocket
- `WS /ws/{user_id}` - Real-time notifications and progress updates

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Run tests in parallel
pytest -n auto
```

## 🔧 Development Tools

### Code Quality

```bash
# Format code
black app tests
isort app tests

# Type checking
mypy app

# Run all quality checks
make lint  # If using Makefile
```

### Database Operations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 🐳 Docker Configuration

### Multi-stage Dockerfile

```dockerfile
# Production-optimized build
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🔒 Security Features

- **Input Validation**: Pydantic models with comprehensive validation
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries  
- **XSS Prevention**: Automatic request/response sanitization
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Rate Limiting**: Redis-based request throttling
- **File Upload Security**: Mime type validation and size limits
- **JWT Security**: Secure token generation with proper expiration

## 📊 Monitoring & Observability

### Health Checks
- `GET /health` - Application health status
- `GET /health/db` - Database connectivity check
- `GET /health/redis` - Redis connectivity check
- `GET /health/s3` - AWS S3 connectivity check

### Metrics & Logging

```python
# Structured logging configuration
import logging
from app.core.logging import setup_logging

setup_logging(level=logging.INFO)
```

## 🚀 Performance Optimizations

### Async/Await Pattern
- Fully asynchronous request handling
- Non-blocking database operations
- Concurrent image processing

### Caching Strategy
- Redis caching for frequently accessed data
- Image metadata caching
- Session-based caching

### Background Processing
- FastAPI background tasks for heavy operations
- Celery integration ready (optional)
- Progress tracking with WebSocket updates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write comprehensive tests for new features
- Update documentation for API changes
- Use conventional commit messages

## 📁 Project Structure

```
app/
├── api/                    # API route handlers
│   ├── v1/
│   │   ├── endpoints/     # Individual endpoint modules
│   │   └── api.py         # API router aggregation
├── core/                   # Core application configuration
│   ├── config.py          # Settings and configuration
│   ├── security.py        # Authentication utilities
│   └── database.py        # Database connection
├── models/                 # SQLAlchemy models
├── schemas/                # Pydantic schemas
├── services/               # Business logic services
│   ├── auth.py            # Authentication service
│   ├── sketch.py # Image processing service
│   └── s3.py         # File storage service
├── utils/                  # Utility functions
├── routers/                # FastAPI routers
├── database/               # Database utilities
│   └── migrations/        # Alembic migrations
└── main.py                # Application entry point

tests/                      # Test modules
├── conftest.py            # Test configuration
├── test_auth.py           # Authentication tests
└── test_image_processing.py # Image processing tests

docker-compose.yml          # Docker services configuration
Dockerfile                 # Container definition
requirements.txt           # Python dependencies
alembic.ini                # Alembic configuration
README.md                  # This file
```

## 📋 Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | ✅ | - |
| `REDIS_URL` | Redis connection string | ✅ | - |
| `SECRET_KEY` | JWT secret key | ✅ | - |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | ✅ | - |
| `AWS_ACCESS_KEY_ID` | AWS access key | ✅ | - |
| `S3_BUCKET_NAME` | S3 bucket name | ✅ | - |
| `ENVIRONMENT` | Application environment | ❌ | `development` |
| `API_V1_STR` | API version prefix | ❌ | `/api/v1` |

## 🐛 Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U username -d imagetosketch
```

**Redis Connection Issues**
```bash
# Check Redis status
sudo systemctl status redis

# Test connection
redis-cli ping
```

**Image Processing Errors**
```bash
# Install system dependencies for OpenCV
sudo apt-get update
sudo apt-get install libgl1-mesa-glx libglib2.0-0
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** team for the incredible framework
- **OpenCV** community for computer vision tools
- **SQLAlchemy** for the powerful ORM
- **Pydantic** for data validation

---

<div align="center">

**[🔗 API Documentation](https://sketchbackend.abhinandan.pro/docs) | [📊 Redoc](https://sketchbackend.abhinandan.pro/redoc) | [🐳 Docker Hub](https://hub.docker.com)**

*Built with ❤️ using FastAPI and modern Python*

</div>
