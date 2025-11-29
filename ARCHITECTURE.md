# System Architecture Documentation

## Overview

This document describes the backend architecture of the Plant Irrigation Management System, focusing on the microservices architecture, networking, data storage, authentication, and system availability.

## System Architecture

The system follows a **microservices architecture** with three main backend services:

1. **Auth & Weather Server** - Handles authentication and weather data integration
2. **Sensor Service** - Manages irrigation fields, checkpoints, sensors, and automated triggers
3. **PostgreSQL Database** - Centralized data storage for all services

A React frontend application communicates with the backend services via REST APIs.

## Networking & Service Communication

### Port Allocation

- **Port 8000**: Auth & Weather Server 
- **Port 8001**: Sensor Service 
- **Port 5432**: PostgreSQL Database 
- **Port 5173**: Frontend Application 

### Docker Network Architecture

All services run within a **Docker bridge network** (`cn_network`) that enables:

- **Service Discovery**: Services communicate using container names as hostnames
- **Isolation**: Services are isolated from the host network but can communicate with each other
- **Internal Communication**: Services use internal Docker DNS (e.g., `http://sensor-service:8001`)

### Inter-Service Communication

#### Frontend → Auth & Weather Server
- **Protocol**: HTTP/HTTPS
- **Port**: 8000
- **Authentication**: JWT Bearer tokens in Authorization header
- **CORS**: Configured to allow requests from frontend origins

#### Auth & Weather Server → Sensor Service
- **Protocol**: HTTP (internal Docker network)
- **Hostname**: `sensor-service:8001`
- **Method**: Async HTTP requests using `httpx.AsyncClient`
- **Purpose**: Proxies requests from authenticated users to sensor service
- **User Context**: Auth server injects `user_id` into all requests to sensor service

#### Auth & Weather Server → OpenWeatherMap API
- **Protocol**: HTTPS
- **Endpoint**: `http://api.openweathermap.org/data/2.5/weather`
- **Method**: Async HTTP GET requests
- **Authentication**: API key passed as query parameter
- **Timeout**: 10 seconds with error handling

### Communication Flow Example

```
Frontend (Browser)
    ↓ HTTP + JWT Token
Auth & Weather Server (Port 8000)
    ↓ HTTP + user_id parameter
Sensor Service (Port 8001)
    ↓ SQL Queries
PostgreSQL (Port 5432)
```

## Data Storage

### PostgreSQL Database

**Single Database Instance**: All services share the same PostgreSQL database (`cn_project`) but use separate schemas/tables.

**Connection String**: `postgresql://postgres:postgres@postgres:5432/cn_project`

**Data Models**:

#### Auth & Weather Server Tables
- `users`: User accounts with hashed passwords

#### Sensor Service Tables
- `fields`: Irrigation fields (user-specific, includes city for weather lookup)
- `checkpoints`: Monitoring points within fields
- `sensors`: Sensor readings (soil_moisture, temperature, humidity, light)
- `pumps`: Pump control units for each checkpoint
- `trigger_tasks`: Automated trigger rules based on weather conditions

**Data Isolation**: User-specific data is isolated using `user_id` foreign keys. All queries filter by `user_id` to ensure data privacy.

**Persistence**: Database data is persisted using Docker volumes (`postgres_data`) to survive container restarts.

## Sensor Data Generation

### Separate Microservice Architecture

The **Sensor Service** is a completely independent microservice that:

- Runs on a separate port (8001)
- Has its own database models and business logic
- Operates independently from the auth server
- Can be scaled or replaced without affecting authentication

### Automated Data Generation

**Background Scheduler**: Uses `APScheduler` (Advanced Python Scheduler) to generate sensor data automatically.

**Generation Frequency**: Every **10 seconds**

**Process**:
1. Scheduler triggers `generate_sensor_data()` function
2. Function queries all checkpoints from database
3. For each checkpoint, generates random sensor readings:
   - Soil Moisture: 20-80%
   - Temperature: 15-35°C
   - Humidity: 40-90%
   - Light: 0-1000 lux
4. Updates existing sensor records (replaces old values)
5. Commits to database

**Initialization**: When a new checkpoint is created, sensors are automatically generated via `create_sensors_for_checkpoint()` function.

**Scheduler Lifecycle**:
- Starts on service startup
- Runs continuously in background thread
- Gracefully shuts down on service termination

## Authentication System

### JWT-Based Authentication

**Token Type**: JSON Web Tokens (JWT) using HS256 algorithm

**Token Storage**: Frontend stores tokens in `localStorage`

**Authentication Flow**:

1. **User Registration** (`POST /signup`):
   - Password hashed using bcrypt (12 rounds)
   - User stored in database
   - Returns user data (no token)

2. **User Login** (`POST /token`):
   - Validates username/password
   - Generates JWT token with username in payload
   - Token expires in 30 minutes
   - Returns `access_token` and `token_type`

3. **Protected Endpoints**:
   - Frontend includes token in `Authorization: Bearer <token>` header
   - Auth server validates token using `get_current_user()` dependency
   - Extracts username from token payload
   - Queries database for user record
   - Returns user object or raises 401 if invalid

4. **User Context Propagation**:
   - Auth server extracts `user_id` from authenticated user
   - Passes `user_id` to sensor service in all requests
   - Sensor service filters all data by `user_id`
   - Ensures complete data isolation between users

### Security Features

- **Password Hashing**: bcrypt with 12 rounds
- **Token Expiration**: 30-minute access tokens
- **CORS Protection**: Configured for specific frontend origins
- **Input Validation**: Pydantic schemas validate all inputs
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries

## Dockerization

### Container Architecture

All backend services are containerized using Docker:

**PostgreSQL Container**:
- Base Image: `postgres:15-alpine`
- Health Check: `pg_isready` command every 10 seconds
- Volume: Persistent storage for database files
- Network: `cn_network`

**Auth & Weather Server Container**:
- Base Image: Python (from Dockerfile)
- Build Context: `./auth-weather-server`
- Command: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- Environment Variables:
  - `DATABASE_URL`: Connection string to PostgreSQL
  - `WEATHER_API_KEY`: OpenWeatherMap API key
  - `SECRET_KEY`: JWT signing key
- Volume Mount: Source code mounted for hot-reload during development
- Dependencies: Waits for PostgreSQL health check

**Sensor Service Container**:
- Base Image: Python (from Dockerfile)
- Build Context: `./sensor-service`
- Command: `uvicorn main:app --host 0.0.0.0 --port 8001 --reload`
- Environment Variables:
  - `DATABASE_URL`: Connection string to PostgreSQL
- Volume Mount: Source code mounted for hot-reload
- Dependencies: Waits for PostgreSQL health check

### Docker Compose Orchestration

**Service Dependencies**:
- Both backend services depend on PostgreSQL with health check condition
- Ensures database is ready before services start

**Network Configuration**:
- All services on `cn_network` bridge network
- Enables service-to-service communication using container names

**Volume Management**:
- `postgres_data`: Named volume for database persistence
- Source code volumes: Bind mounts for development hot-reload

**Benefits of Dockerization**:
- **Isolation**: Each service runs in its own container
- **Portability**: Same environment across development/production
- **Scalability**: Easy to scale individual services
- **Dependency Management**: Automatic service startup order
- **Resource Management**: Container resource limits

## Third-Party API Integration

### OpenWeatherMap API

**Critical External Dependency**: The system integrates with OpenWeatherMap API for real-time weather data.

**Integration Details**:

**Endpoint**: `http://api.openweathermap.org/data/2.5/weather`

**Authentication**: API key passed as query parameter (`appid`)

**Request Flow**:
1. Frontend requests weather for a city
2. Auth server receives authenticated request
3. Auth server makes async HTTP request to OpenWeatherMap
4. Response parsed and transformed to internal format
5. Returns weather data to frontend

**Data Retrieved**:
- City name
- Temperature (Celsius)
- Weather description
- Humidity percentage
- Wind speed (m/s)

**Error Handling**:
- **Timeout**: 10-second timeout with `httpx.AsyncClient`
- **Connection Errors**: Returns 503 "Weather service unavailable"
- **API Errors**: Returns appropriate HTTP status with error details
- **Authentication Failures**: Detects 401 responses and provides clear error messages

**Availability Impact**: System availability depends on OpenWeatherMap API availability. Errors are gracefully handled to prevent cascading failures.

**Usage in System**:
- Weather data used for display in dashboard
- Weather data used for trigger task evaluation
- Each field has an associated city for weather lookup
- Weather data cached/refetched every 60 seconds

## System Availability

### Health Checks

**PostgreSQL Health Check**:
- Command: `pg_isready -U postgres`
- Interval: 10 seconds
- Timeout: 5 seconds
- Retries: 5 attempts
- Purpose: Ensures database is ready before dependent services start

**Service Health Endpoints**:
- `GET /health` on both services
- Returns service status
- Can be used for load balancer health checks

### Error Handling & Resilience

**Database Connection Resilience**:
- SQLAlchemy connection pooling
- Automatic connection retry on failure
- Graceful degradation on database errors

**Service Communication Resilience**:
- Async HTTP clients with timeouts
- Error handling for service unavailability
- Returns 503 status when downstream services fail
- Detailed error messages for debugging

**Third-Party API Resilience**:
- Timeout protection (10 seconds)
- Graceful error handling
- System continues operating even if weather API is down
- Clear error messages to users

### Service Dependencies

**Startup Order** (enforced by Docker Compose):
1. PostgreSQL starts first
2. PostgreSQL health check passes
3. Auth & Weather Server starts
4. Sensor Service starts

**Dependency Management**:
- Services wait for database health check
- Prevents connection errors during startup
- Ensures all dependencies are ready

### Data Persistence

**Database Persistence**:
- Docker named volume (`postgres_data`)
- Data survives container restarts
- Data survives service updates
- Can be backed up independently

**No Data Loss Scenarios**:
- Container restart: Data persists in volume
- Service update: Database volume remains
- System reboot: Volume data intact

### Monitoring & Observability

**Logging**:
- Service logs available via `docker-compose logs`
- Error logging in all exception handlers
- Scheduler activity logged

**Error Visibility**:
- Detailed error messages in API responses
- Console logging for debugging
- HTTP status codes indicate error types

## Summary

This system implements a robust microservices architecture with:

- **Clear service boundaries** between authentication and sensor management
- **Secure inter-service communication** using Docker networking
- **Centralized data storage** with user isolation
- **Automated sensor data generation** via background scheduler
- **JWT-based authentication** with proper user context propagation
- **Full Docker containerization** for portability and scalability
- **Resilient third-party API integration** with proper error handling
- **Health checks and dependency management** for high availability
- **Data persistence** through Docker volumes

The architecture supports horizontal scaling, independent service deployment, and maintains data integrity and user privacy throughout the system.

