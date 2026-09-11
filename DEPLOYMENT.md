# BeAstar.io - Production Deployment Guide

## 🚀 Overview

This guide provides step-by-step instructions for deploying BeAstar.io to production. The application is designed for **global scale** with a complete viral retention loop: **Create → Share → Follow → Encourage → Return**.

---

## 📋 Prerequisites

### Required Infrastructure

| Service | Purpose | Provider Options | Notes |
|---------|---------|-----------------|-------|
| **Domain Name** | Public access | Any registrar | Required for SSL |
| **Server/VPS** | Hosting | AWS EC2, DigitalOcean, Linode, etc. | 4+ vCPUs, 8GB+ RAM recommended |
| **Docker** | Container runtime | Docker Engine 20.10+ | [Install Docker](https://docs.docker.com/engine/install/) |
| **Docker Compose** | Orchestration | Docker Compose 2.0+ | [Install Compose](https://docs.docker.com/compose/install/) |
| **Supabase** | Database & Storage | Supabase Cloud | Free tier available, paid for production |
| **Redis** | Message queue | Managed or self-hosted | Included in docker-compose |

### Required API Keys & Credentials

Create a `.env` file in the project root with the following **required** environment variables:

```bash
# Copy the template to get started
cp .env.example .env
```

See [CONFIGURATION.md](CONFIGURATION.md) for a complete list of all environment variables and their descriptions.

---

## 🎯 Quick Start (Local Development)

### 1. Clone the Repository

```bash
git clone https://github.com/clyde6205/beastar.git
cd beastar
```

### 2. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Install FFmpeg (required for video watermarking)
# Ubuntu/Debian:
sudo apt-get update && sudo apt-get install -y ffmpeg

# macOS:
brew install ffmpeg

# Windows: Download from https://ffmpeg.org/
```

### 4. Install face_recognition Library

```bash
# This requires dlib and cmake
pip install face-recognition>=1.3.0
```

If you encounter issues, see the [face_recognition installation guide](https://github.com/ageitgey/face_recognition#installation).

### 5. Run with Docker Compose (Development)

```bash
# Start all services (backend, redis, celery worker, celery beat)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down
```

### 6. Test the API

```bash
# Health check
curl http://localhost:8000/health

# API documentation (Swagger UI)
# Open in browser: http://localhost:8000/docs
```

---

## 🏗️ Production Deployment

### Option A: Single Server Deployment (Recommended for Start)

#### 1. Prepare the Server

```bash
# SSH into your server
ssh root@your-server-ip

# Install Docker and Docker Compose
# For Ubuntu/Debian:
apt-get update && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common \
    git

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
curl -SL https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version
```

#### 2. Clone the Repository

```bash
cd /opt
git clone https://github.com/clyde6205/beastar.git
cd beastar
```

#### 3. Configure Environment

```bash
# Copy production environment template
cp .env.example .env

# Edit .env with production credentials
nano .env

# Set strong passwords
# Generate a secure SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Generate Redis password
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 4. Create Required Directories

```bash
# Create directories for logs, temp files, and data
mkdir -p logs temp data/redis nginx/conf.d nginx/ssl nginx/logs scripts

# Set proper permissions
chmod -R 755 logs temp data nginx
```

#### 5. Configure SSL Certificates (HTTPS)

**Option A: Let's Encrypt (Recommended - Free)**

```bash
# Install Certbot
apt-get install -y certbot python3-certbot-nginx

# Stop any running services

# Request certificate (replace with your domain)
certbot certonly --standalone -d beastar.io -d api.beastar.io

# Copy certificates to nginx/ssl
cp /etc/letsencrypt/live/beastar.io/fullchain.pem nginx/ssl/certificate.crt
cp /etc/letsencrypt/live/beastar.io/privkey.pem nginx/ssl/private.key
cp /etc/letsencrypt/live/beastar.io/chain.pem nginx/ssl/chain.crt

# Set permissions
chmod 600 nginx/ssl/private.key
```

**Option B: Self-Signed (Development Only)**

```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/private.key \
    -out nginx/ssl/certificate.crt \
    -subj "/C=US/ST=California/L=San Francisco/O=BeAstar/OU=Dev/CN=beastar.io"
```

#### 6. Configure Nginx

The `nginx/nginx.conf` file is already configured for production. You can customize it if needed.

Create a custom configuration for your domain:

```bash
cat > nginx/conf.d/beastar.conf << 'EOF'
server {
    listen 443 ssl http2;
    server_name beastar.io api.beastar.io;

    ssl_certificate /etc/nginx/ssl/certificate.crt;
    ssl_certificate_key /etc/nginx/ssl/private.key;
    ssl_trusted_certificate /etc/nginx/ssl/chain.crt;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req zone=api burst=200 nodelay;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    # Static files
    location /static/ {
        alias /app/backend/app/static/;
        expires 30d;
    }

    # Health check
    location /health {
        proxy_pass http://backend:8000/health;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name beastar.io api.beastar.io;
    return 301 https://$host$request_uri;
}
EOF
```

#### 7. Configure Redis

Create a Redis configuration file:

```bash
cat > redis.conf << 'EOF'
# Redis configuration for BeAstar production

# Network
bind 0.0.0.0
protected-mode yes

# Security
requirepass ${REDIS_PASSWORD}

# Persistence
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec

# Memory management
maxmemory 1gb
maxmemory-policy allkeys-lru

# Performance
tcp-keepalive 300
timeout 0
tcp-nodelay yes

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Replication (if using multiple Redis instances)
# replicaof master-ip master-port

# Security - disable dangerous commands
rename-command FLUSHALL ""
rename-command FLUSHDB ""
rename-command CONFIG ""
rename-command SHUTDOWN ""
EOF
```

#### 8. Build and Start Containers

```bash
# Build the Docker images
docker-compose -f docker-compose.prod.yml build

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Verify all containers are running
docker-compose -f docker-compose.prod.yml ps
```

#### 9. Verify Deployment

```bash
# Check health endpoint
curl https://beastar.io/health

# Check API documentation
# Open in browser: https://beastar.io/docs

# View logs
# Backend logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Celery worker logs
docker-compose -f docker-compose.prod.yml logs -f celery-worker

# Nginx logs
docker-compose -f docker-compose.prod.yml logs -f nginx
```

---

### Option B: Kubernetes Deployment (For Large Scale)

For Kubernetes deployment, see [k8s/](k8s/) directory (not yet created - contact for setup).

---

## 🔧 Post-Deployment Configuration

### 1. Set Up Supabase Database

1. Go to [Supabase Dashboard](https://app.supabase.com/) and create a new project
2. Get your project URL and anon/public key from Settings > API
3. Update `.env` with:
   ```bash
   SUPABASE_URL=your-project-url
   SUPABASE_KEY=your-anon-key
   ```

4. Run the database schema:
   ```bash
   # Connect to your Supabase database and run schema.sql
   psql -h your-db-host -U postgres -d your-db-name -f backend/schema.sql
   ```

### 2. Configure Payment Providers

#### PayMongo (GCash - Philippines)

1. Sign up at [PayMongo Dashboard](https://dashboard.paymongo.com/)
2. Get your API keys from Developers > API Keys
3. Update `.env`:
   ```bash
   PAYMONGO_SECRET_KEY=your-secret-key
   PAYMONGO_WEBHOOK_SECRET=your-webhook-secret
   ```
4. Configure webhook in PayMongo Dashboard:
   - URL: `https://beastar.io/webhooks/paymongo`
   - Events: `source.chargeable`, `payment.paid`, `payment.failed`

#### Stripe (Global)

1. Sign up at [Stripe Dashboard](https://dashboard.stripe.com/)
2. Get your API keys from Developers > API Keys
3. Update `.env`:
   ```bash
   STRIPE_SECRET_KEY=your-secret-key
   STRIPE_WEBHOOK_SECRET=your-webhook-secret
   ```
4. Configure webhook in Stripe Dashboard:
   - URL: `https://beastar.io/webhooks/stripe`
   - Events: `invoice.payment_succeeded`, `invoice.payment_failed`, `customer.subscription.created`, `customer.subscription.updated`

### 3. Configure AI Providers

#### Runway (Primary Video Generation)

1. Sign up at [Runway](https://runwayml.com/)
2. Get your API key from Account > API Keys
3. Update `.env`:
   ```bash
   RUNWAY_API_KEY=your-api-key
   ```

#### Kling AI (Fallback Video Generation)

1. Sign up at [Kling AI](https://kling.ai/)
2. Get your API key
3. Update `.env`:
   ```bash
   KLING_API_KEY=your-api-key
   ```

### 4. Configure AWS (Face Verification & Moderation)

1. Sign up at [AWS Console](https://console.aws.amazon.com/)
2. Create an IAM user with permissions for:
   - Amazon Rekognition (full access)
   - Amazon S3 (if using for temporary storage)
3. Get Access Key ID and Secret Access Key
4. Update `.env`:
   ```bash
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_REGION=us-east-1
   ```

### 5. Configure Hive AI (Fallback Moderation)

1. Sign up at [Hive AI](https://hive.ai/)
2. Get your API key
3. Update `.env`:
   ```bash
   HIVE_API_KEY=your-api-key
   ```

---

## 📊 Monitoring and Maintenance

### Health Checks

```bash
# Check backend health
curl https://beastar.io/health

# Check Celery worker health
docker-compose -f docker-compose.prod.yml exec celery-worker celery -A app.worker inspect ping

# Check Redis health
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
```

### Logs

```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f celery-worker
docker-compose -f docker-compose.prod.yml logs -f celery-beat
```

### Backups

```bash
# Backup Redis data
# Redis data is persisted to ./data/redis on the host
# Backup this directory regularly

# Backup Supabase data
# Use Supabase's backup features or pg_dump
pg_dump -h your-db-host -U postgres -d your-db-name > backup.sql
```

### Scaling

#### Scale Celery Workers

```bash
# Scale to 4 Celery workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=4
```

#### Scale Backend

For higher traffic, consider:
- Running multiple backend instances behind a load balancer
- Using Kubernetes for auto-scaling
- Implementing horizontal pod autoscaling (HPA)

---

## 🚨 Troubleshooting

### Common Issues

#### 1. Docker Build Fails

**Error:** `ERROR: Service 'backend' failed to build`

**Solution:**
```bash
# Clean and rebuild
docker-compose -f docker-compose.prod.yml down
docker system prune -a
docker-compose -f docker-compose.prod.yml build --no-cache
```

#### 2. FFmpeg Not Found

**Error:** `ffmpeg: command not found`

**Solution:**
```bash
# Install FFmpeg on the host (for development)
# Ubuntu/Debian:
sudo apt-get install -y ffmpeg

# For Docker, ensure it's installed in the Dockerfile
# The provided Dockerfile already includes FFmpeg
```

#### 3. face_recognition Import Error

**Error:** `ModuleNotFoundError: No module named 'face_recognition'`

**Solution:**
```bash
# Install face_recognition
pip install face-recognition>=1.3.0

# If you get dlib errors:
# Ubuntu/Debian:
sudo apt-get install -y cmake dlib-dev

# macOS:
brew install cmake dlib
```

#### 4. Redis Connection Error

**Error:** `ConnectionError: Error connecting to redis`

**Solution:**
```bash
# Check if Redis is running
docker-compose -f docker-compose.prod.yml ps | grep redis

# Check Redis logs
docker-compose -f docker-compose.prod.yml logs redis

# Verify Redis password in .env
# REDIS_PASSWORD should be set and match the password in docker-compose.prod.yml
```

#### 5. Supabase Connection Error

**Error:** `ConnectionError: Failed to connect to Supabase`

**Solution:**
```bash
# Verify SUPABASE_URL and SUPABASE_KEY in .env
# Test connection manually
curl -H "apikey: YOUR_SUPABASE_KEY" \
     -H "Authorization: Bearer YOUR_SUPABASE_KEY" \
     https://YOUR_SUPABASE_URL/rest/v1/
```

#### 6. API Key Not Configured

**Error:** `API key not configured for Runway/Kling/AWS`

**Solution:**
```bash
# Verify all API keys are set in .env
# Check for missing keys
grep -E "RUNWAY_API_KEY|KLING_API_KEY|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY" .env
```

---

## 🔒 Security Checklist

- [ ] All API keys are stored in environment variables (not in code)
- [ ] HTTPS is enabled with valid SSL certificates
- [ ] Security headers are configured in Nginx
- [ ] Rate limiting is enabled
- [ ] Redis has a password set
- [ ] Supabase has row-level security (RLS) enabled
- [ ] All sensitive endpoints require authentication
- [ ] Content moderation is configured and working
- [ ] Face verification is configured and working
- [ ] Payment webhooks have signature verification enabled
- [ ] Regular backups are configured
- [ ] Monitoring is in place (logs, health checks)
- [ ] Firewall rules restrict access to necessary ports only

---

## 📈 Performance Optimization

### Caching

- Enable Redis caching for frequently accessed data
- Consider using a CDN for static assets
- Implement response caching for API endpoints

### Database Optimization

- Add indexes for frequently queried columns
- Consider using Supabase's connection pooling
- Monitor slow queries and optimize them

### Video Processing

- Consider using a dedicated video processing service for heavy workloads
- Implement queue prioritization for premium users
- Use FFmpeg's hardware acceleration if available

---

## 🚀 Going Live

### Pre-Launch Checklist

- [ ] All environment variables are configured
- [ ] Database schema is applied
- [ ] SSL certificates are valid
- [ ] All API endpoints are tested
- [ ] Payment webhooks are configured
- [ ] Content moderation is working
- [ ] Face verification is working
- [ ] Video generation pipeline is tested
- [ ] Mobile app is configured with the correct API URL
- [ ] Monitoring is in place
- [ ] Backups are configured
- [ ] Security checklist is complete
- [ ] Performance is acceptable under load

### Soft Launch

1. Deploy to a staging environment
2. Test with a small group of users
3. Monitor for issues and performance bottlenecks
4. Fix any critical issues
5. Gradually roll out to more users

### Full Launch

1. Announce on social media
2. Monitor closely for the first 24-48 hours
3. Scale up resources as needed
4. Continue monitoring and optimization

---

## 📞 Support

For issues, questions, or custom deployment configurations:

1. Check the [FAQ](#faq) section below
2. Review the [CONFIGURATION.md](CONFIGURATION.md) for environment variables
3. Check the logs for errors
4. Open an issue on GitHub with details about your problem

---

## ❓ FAQ

### Q: How do I update the application?

A: Pull the latest changes and rebuild:
```bash
cd /opt/beastar
git pull origin main
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Q: How do I add more Celery workers?

A: Scale the service:
```bash
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=4
```

### Q: How do I monitor the application?

A: Use the health check endpoints and logs:
```bash
# Health check
curl https://beastar.io/health

# Logs
docker-compose -f docker-compose.prod.yml logs -f

# For production monitoring, consider:
# - Prometheus + Grafana
# - Sentry for error tracking
# - Datadog for APM
```

### Q: How do I backup the data?

A: Backup Redis and Supabase:
```bash
# Redis (automatic persistence is configured)
# Backup the ./data/redis directory

# Supabase
# Use Supabase's backup features or run pg_dump
```

### Q: How do I restore from backup?

A: Stop services, restore data, and restart:
```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Restore data from backup
# (copy backup files to ./data/redis)

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

### Q: How do I rotate API keys?

A: Update the `.env` file and restart:
```bash
# Update .env with new keys
nano .env

# Rebuild and restart (to pick up new environment variables)
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Q: How do I enable debug mode?

A: Set `DEBUG=true` and `LOG_LEVEL=DEBUG` in `.env`, then restart:
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

---

## 📝 Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2024-XX-XX | 1.0.0 | Initial production deployment guide |

---

## 📄 Related Documents

- [CONFIGURATION.md](CONFIGURATION.md) - Complete environment variable reference
- [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) - Development roadmap and priorities
- [backend/schema.sql](backend/schema.sql) - Database schema
- [Makefile](Makefile) - Build and deployment commands
- [.env.example](.env.example) - Environment variable template

---

## 🎉 Congratulations!

You've successfully deployed BeAstar.io! 🎊

Your users can now:
1. **Create** their Star Moments with AI video generation
2. **Share** their videos with the viral QR code system
3. **Follow** other users' Dream Threads
4. **Encourage** others with likes and comments
5. **Return** to create more and track their journey

The viral retention loop is now fully operational!
