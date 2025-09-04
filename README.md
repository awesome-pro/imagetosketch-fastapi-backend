# Image to Sketch API Backend

A complete FastAPI backend for converting images to sketches with JWT cookie authentication, S3 integration, and real-time notifications.

## 🚀 Features

### Authentication
- **JWT Cookie-based Authentication**: Secure authentication using HTTP-only cookies
- **User Management**: Registration, login, logout, and profile management
- **Role-based Access Control**: Admin and user roles

### File Upload & Processing
- **Direct S3 Upload**: Frontend uploads directly to S3 using presigned URLs
- **Multiple Sketch Styles**: Pencil, charcoal, watercolor, ink, etc.
- **Three Processing Methods**: Basic, advanced, and artistic sketch conversion
- **Background Processing**: Async task processing optimized for Cloud Run

### Real-time Features
- **WebSocket Notifications**: Real-time updates on processing status
- **Task Management**: Background task tracking with Redis
- **Status Updates**: Live progress updates via WebSocket

### Cloud-Ready
- **Google Cloud Run Optimized**: Stateless design with Redis for coordination
- **Scalable Architecture**: Handles concurrent processing efficiently
- **Health Checks**: Built-in health monitoring endpoints

## 🛠 Technology Stack

- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: Async ORM with PostgreSQL
- **Redis**: Task coordination and real-time messaging
- **OpenCV**: Image processing and sketch conversion
- **AWS S3**: File storage and CDN
- **WebSockets**: Real-time communication
- **JWT**: Secure authentication

## 📁 Project Structure

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py          # Application settings
│   │   ├── deps.py            # Cookie-based auth dependencies
│   │   └── security.py        # JWT and password utilities
│   ├── database/
│   │   └── connection.py      # Database and Redis connections
│   ├── models/
│   │   ├── user.py           # User model
│   │   └── sketch.py         # Sketch model with styles
│   ├── routers/
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── upload.py         # S3 upload endpoints
│   │   ├── sketch.py         # Sketch processing endpoints
│   │   └── websocket.py      # WebSocket notifications
│   ├── schemas/
│   │   ├── user.py           # User Pydantic models
│   │   └── sketch.py         # Sketch Pydantic models
│   ├── services/
│   │   ├── auth.py           # Authentication service
│   │   ├── s3.py             # S3 integration service
│   │   ├── sketch.py         # Image processing service
│   │   └── background_tasks.py # Task management service
│   └── main.py               # FastAPI application
├── requirements.txt          # Dependencies
└── README.md                # This file
```

## 🔧 Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/imagetosketch

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Application
APP_NAME=Image to Sketch API
APP_VERSION=1.0.0
DEBUG=false
BASE_URL=https://your-domain.com
ALLOWED_ORIGINS=["http://localhost:3000","https://your-frontend-domain.com"]

# AWS S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=your-region
AWS_BUCKET_NAME=your-bucket-name
AWS_PRESIGNED_URL_EXPIRATION=900

# Processing
TEMP_DIR=/tmp
MAX_FILE_SIZE=10485760
ALLOWED_FILE_TYPES=["image/jpeg","image/png","image/webp","image/gif"]
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT=300
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Up Database

```bash
# Install and start PostgreSQL
# Create database
createdb imagetosketch

# Run migrations (you'll need to create these)
alembic upgrade head
```

### 3. Set Up Redis

```bash
# Install and start Redis
redis-server
```

### 4. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 API Documentation

### Authentication Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login (sets cookie)
- `POST /api/auth/logout` - Logout (clears cookie)
- `GET /api/auth/me` - Get current user info

### Upload Endpoints

- `POST /api/upload/presigned-url` - Get S3 presigned upload URL
- `POST /api/upload/confirm` - Confirm successful upload
- `GET /api/upload/download-url/{key}` - Get download URL

### Sketch Processing Endpoints

- `POST /api/sketch/create` - Create sketch processing job
- `GET /api/sketch/{sketch_id}` - Get sketch details
- `GET /api/sketch/` - List user sketches
- `GET /api/sketch/task/{task_id}` - Get task status
- `GET /api/sketch/styles/available` - Get available styles
- `DELETE /api/sketch/{sketch_id}` - Delete sketch

### WebSocket Endpoint

- `WS /ws?token=jwt_token` - Real-time notifications

## 🎨 Sketch Styles & Methods

### Available Styles
- **PENCIL**: Classic pencil sketch
- **CHARCOAL**: Dark, textured charcoal effect
- **WATERCOLOR**: Soft, blended watercolor style
- **INK**: Sharp, high-contrast ink drawing
- **PASTEL**: Soft pastel colors
- **OIL**: Oil painting effect
- **ACRYLIC**: Acrylic paint style

### Processing Methods
- **Basic**: Simple edge detection with basic processing
- **Advanced**: High-quality with edge preservation and texture enhancement
- **Artistic**: Enhanced details with sharpening and artistic effects

## 🔄 Workflow

1. **User Authentication**: Login via cookie-based JWT
2. **File Upload**: Get presigned S3 URL and upload directly
3. **Process Request**: Submit processing job with style preferences
4. **Background Processing**: Async task processes the image
5. **Real-time Updates**: WebSocket notifications on progress
6. **Download**: Get processed sketch via download URL

## ☁️ Google Cloud Run Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
```

### Deploy Commands

```bash
# Build and deploy to Cloud Run
gcloud builds submit --tag gcr.io/PROJECT_ID/imagetosketch-api
gcloud run deploy imagetosketch-api \
    --image gcr.io/PROJECT_ID/imagetosketch-api \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --concurrency 100 \
    --timeout 900
```

## 🔒 Security Features

- **HTTP-only Cookies**: Prevents XSS attacks
- **CORS Configuration**: Proper cross-origin settings
- **Input Validation**: File type and size validation
- **User Isolation**: Files are organized by user ID
- **Presigned URLs**: Secure, time-limited S3 access

## 📊 Monitoring & Logging

- **Health Check Endpoint**: `/health` with system metrics
- **Structured Logging**: JSON logs for production
- **Task Status Tracking**: Redis-based task monitoring
- **Error Handling**: Comprehensive error responses

## 🔧 Configuration

The application is highly configurable via environment variables. Key settings include:

- **Concurrency**: Control max concurrent tasks
- **File Limits**: Set upload size and type restrictions
- **Timeouts**: Configure processing timeouts
- **S3 Settings**: Bucket configuration and presigned URL expiration

## 🤝 Frontend Integration

### Authentication Flow
1. Frontend sends login credentials to `/api/auth/login`
2. Backend sets HTTP-only cookie with JWT
3. All subsequent requests automatically include the cookie
4. Frontend can check auth status via `/api/auth/me`

### File Upload Flow
1. Get presigned URL from `/api/upload/presigned-url`
2. Upload directly to S3 using the presigned URL
3. Confirm upload via `/api/upload/confirm`
4. Submit processing job via `/api/sketch/create`

### Real-time Updates
1. Connect to WebSocket with JWT token
2. Listen for task update messages
3. Update UI based on processing status

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Database Connection**: Check PostgreSQL is running and accessible
3. **Redis Connection**: Ensure Redis server is running
4. **S3 Permissions**: Verify AWS credentials and bucket permissions
5. **File Processing**: Check OpenCV installation and temp directory permissions

### Logs

Check application logs for detailed error information:
```bash
# Local development
tail -f app.log

# Cloud Run
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

This implementation provides a production-ready, scalable backend for your image-to-sketch application with modern best practices and Google Cloud Run optimization.
