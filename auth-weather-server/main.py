from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
import httpx
import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import SessionLocal, engine, Base
from models import User
from schemas import UserCreate, UserResponse, Token, WeatherResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth & Weather API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12, deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "your_api_key_here")
WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/signup", response_model=UserResponse)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user_data.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/weather", response_model=WeatherResponse)
async def get_weather(
    city: str = "London",
    current_user: User = Depends(get_current_user)
):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                WEATHER_API_URL,
                params={
                    "q": city,
                    "appid": WEATHER_API_KEY,
                    "units": "metric"
                }
            )
            if response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail=f"Weather API authentication failed. Check API key. Status: {response.status_code}"
                )
            if response.status_code != 200:
                error_detail = response.text if hasattr(response, 'text') else "Weather API error"
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Weather API error: {error_detail}"
                )
            data = response.json()
            return WeatherResponse(
                city=data["name"],
                temperature=data["main"]["temp"],
                description=data["weather"][0]["description"],
                humidity=data["main"]["humidity"],
                wind_speed=data["wind"]["speed"]
            )
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Weather service unavailable")

@app.get("/fields")
async def get_fields(current_user: User = Depends(get_current_user)):
    """Get all fields with checkpoints, sensors, and pumps from sensor service"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "http://sensor-service:8001/fields",
                params={"user_id": current_user.id}
            )
            if response.status_code != 200:
                error_detail = response.text if hasattr(response, 'text') else "Unknown error"
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch fields from sensor service: {error_detail}"
                )
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Sensor service timeout - service may be unavailable")
    except httpx.ConnectError as e:
        raise HTTPException(status_code=503, detail=f"Cannot connect to sensor service: {str(e)}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Sensor service unavailable: {str(e)}")

@app.post("/pumps/{pump_id}/control")
async def control_pump(
    pump_id: int,
    control: dict,
    current_user: User = Depends(get_current_user)
):
    """Control pump on/off via sensor service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://sensor-service:8001/pumps/{pump_id}/control",
                json=control
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to control pump"
                )
            return response.json()
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Sensor service unavailable")

@app.post("/fields")
async def create_field(
    field_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Create a new field via sensor service"""
    try:
        async with httpx.AsyncClient() as client:
            # Add user_id to the field data
            field_data_with_user = {**field_data, "user_id": current_user.id}
            response = await client.post(
                "http://sensor-service:8001/fields",
                json=field_data_with_user
            )
            if response.status_code != 201:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to create field"
                )
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Sensor service unavailable: {str(e)}")

@app.put("/fields/{field_id}")
async def update_field(
    field_id: int,
    field_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update a field via sensor service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://sensor-service:8001/fields/{field_id}",
                json=field_data,
                params={"user_id": current_user.id}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to update field"
                )
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Sensor service unavailable: {str(e)}")

@app.delete("/fields/{field_id}")
async def delete_field(
    field_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a field via sensor service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"http://sensor-service:8001/fields/{field_id}",
                params={"user_id": current_user.id}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to delete field"
                )
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Sensor service unavailable: {str(e)}")

@app.post("/checkpoints")
async def create_checkpoint(
    checkpoint_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Create a new checkpoint via sensor service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://sensor-service:8001/checkpoints",
                json=checkpoint_data,
                params={"user_id": current_user.id}
            )
            if response.status_code != 201:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to create checkpoint"
                )
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Sensor service unavailable: {str(e)}")

@app.put("/checkpoints/{checkpoint_id}")
async def update_checkpoint(
    checkpoint_id: int,
    checkpoint_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update a checkpoint via sensor service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://sensor-service:8001/checkpoints/{checkpoint_id}",
                json=checkpoint_data,
                params={"user_id": current_user.id}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to update checkpoint"
                )
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Sensor service unavailable: {str(e)}")

@app.delete("/checkpoints/{checkpoint_id}")
async def delete_checkpoint(
    checkpoint_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a checkpoint via sensor service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"http://sensor-service:8001/checkpoints/{checkpoint_id}",
                params={"user_id": current_user.id}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to delete checkpoint"
                )
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Sensor service unavailable: {str(e)}")

@app.get("/trigger-tasks")
async def get_trigger_tasks(
    field_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get trigger tasks via sensor service"""
    try:
        async with httpx.AsyncClient() as client:
            params = {"user_id": current_user.id}
            if field_id:
                params["field_id"] = field_id
            response = await client.get(
                "http://sensor-service:8001/trigger-tasks",
                params=params
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to get trigger tasks"
                )
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Sensor service unavailable: {str(e)}")

@app.post("/trigger-tasks")
async def create_trigger_task(
    task_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Create a trigger task via sensor service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://sensor-service:8001/trigger-tasks",
                json=task_data,
                params={"user_id": current_user.id}
            )
            if response.status_code != 201:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to create trigger task"
                )
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Sensor service unavailable: {str(e)}")

@app.put("/trigger-tasks/{task_id}")
async def update_trigger_task(
    task_id: int,
    task_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update a trigger task via sensor service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://sensor-service:8001/trigger-tasks/{task_id}",
                json=task_data,
                params={"user_id": current_user.id}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to update trigger task"
                )
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Sensor service unavailable: {str(e)}")

@app.delete("/trigger-tasks/{task_id}")
async def delete_trigger_task(
    task_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a trigger task via sensor service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"http://sensor-service:8001/trigger-tasks/{task_id}",
                params={"user_id": current_user.id}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to delete trigger task"
                )
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Sensor service unavailable: {str(e)}")

@app.post("/trigger-tasks/{task_id}/evaluate")
async def evaluate_trigger_task(
    task_id: int,
    weather_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Evaluate a trigger task via sensor service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://sensor-service:8001/trigger-tasks/{task_id}/evaluate",
                json=weather_data
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to evaluate trigger task"
                )
            return response.json()
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Sensor service unavailable")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

