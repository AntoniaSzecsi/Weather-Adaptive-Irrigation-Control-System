# CN Project - Multi-Service Architecture

A full-stack application with authentication, weather data, and sensor monitoring. Built with FastAPI, React, PostgreSQL, and Docker.

## Architecture

- **Auth & Weather Server** (Port 8000): FastAPI server handling user authentication and weather API integration
- **Sensor Microservice** (Port 8001): FastAPI service generating random sensor data
- **Frontend** (Port 5173): React app with Vite, Axios, Zod, and React Query
- **PostgreSQL**: Database for users and sensor data

## Prerequisites

- Docker and Docker Compose
- Node.js and npm (for frontend development)
- Python 3.11+ (if running services locally)
- OpenWeatherMap API key (free at https://openweathermap.org/api)

**Important:** Set your weather API key as an environment variable before running docker-compose:
```bash
export WEATHER_API_KEY=your_api_key_here
```

## Setup

### 1. Environment Variables

Create a `.env` file in the root directory (optional, defaults are provided):

```env
WEATHER_API_KEY=your_openweathermap_api_key_here
```

Or set it when running docker-compose:

```bash
WEATHER_API_KEY=your_key docker-compose up
```

### 2. Start Services with Docker Compose

```bash
docker-compose up --build
```

This will start:
- PostgreSQL on port 5432
- Auth & Weather server on port 8000
- Sensor microservice on port 8001

### 3. Start Frontend

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Usage

1. **Sign Up**: Create a new account with username, email, and password
2. **Login**: Use your credentials to log in
3. **Dashboard**: 
   - View weather data for any city (default: London)
   - View real-time sensor data (updates every 5 seconds)
   - All sensors are assigned to all users (simplified for this project)

## API Endpoints

### Auth & Weather Server (Port 8000)

- `POST /signup` - Create new user account
- `POST /token` - Login and get JWT token
- `GET /me` - Get current user info (requires auth)
- `GET /weather?city={city}` - Get weather data (requires auth)
- `GET /sensors` - Get all sensors (requires auth)
- `GET /health` - Health check

### Sensor Microservice (Port 8001)

- `GET /health` - Health check

## Project Structure

```
CN_Project/
├── auth-weather-server/    # Main FastAPI server
│   ├── main.py             # API routes and logic
│   ├── models.py           # Database models
│   ├── schemas.py          # Pydantic schemas
│   ├── database.py         # Database connection
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile
├── sensor-service/         # Sensor microservice
│   ├── main.py             # Sensor data generation
│   ├── models.py           # Sensor model
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile
├── frontend/               # React application
│   ├── src/
│   │   ├── api/           # API client and endpoints
│   │   ├── components/    # React components
│   │   ├── contexts/      # React contexts
│   │   └── App.jsx        # Main app component
│   └── package.json
├── docker-compose.yml      # Docker orchestration
└── README.md
```

## Technologies

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, JWT authentication
- **Frontend**: React, Vite, Axios, Zod, React Query, React Router
- **Infrastructure**: Docker, Docker Compose
- **Database**: PostgreSQL

## Notes

- The sensor service generates random sensor data every 5 seconds
- Weather data is fetched from OpenWeatherMap API
- JWT tokens are stored in localStorage
- All sensors are visible to all users (simplified assignment)
- Weather data refreshes every minute
- Sensor data refreshes every 5 seconds

## Development

To run services individually (without Docker):

1. Start PostgreSQL:
```bash
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=cn_project postgres:15-alpine
```

2. Start auth-weather server:
```bash
cd auth-weather-server
pip install -r requirements.txt
uvicorn main:app --reload
```

3. Start sensor service:
```bash
cd sensor-service
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

4. Start frontend:
```bash
cd frontend
npm install
npm run dev
```

## Troubleshooting

- If ports are already in use, modify the ports in `docker-compose.yml`
- Make sure Docker has enough resources allocated
- Check logs: `docker-compose logs [service-name]`
- For frontend CORS issues, ensure the backend CORS settings include your frontend URL

