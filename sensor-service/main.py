from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.middleware.cors import CORSMiddleware
import random
import os
from datetime import datetime
from models import Field, Checkpoint, Sensor, Pump, TriggerTask, Base
from pydantic import BaseModel
from typing import Optional, List

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cn_project")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI(title="Irrigation Sensor Microservice")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_sensors_for_checkpoint(db: Session, checkpoint_id: int):
    """Create initial sensor readings for a checkpoint"""
    for sensor_type_info in SENSOR_TYPES:
        value = round(
            random.uniform(sensor_type_info["min"], sensor_type_info["max"]),
            2
        )
        sensor = Sensor(
            checkpoint_id=checkpoint_id,
            sensor_type=sensor_type_info["type"],
            value=value,
            unit=sensor_type_info["unit"],
            timestamp=datetime.utcnow()
        )
        db.add(sensor)
    db.commit()


# Irrigation sensor types and their ranges
SENSOR_TYPES = [
    {"type": "soil_moisture", "min": 20.0, "max": 80.0, "unit": "%"},
    {"type": "temperature", "min": 15.0, "max": 35.0, "unit": "°C"},
    {"type": "humidity", "min": 40.0, "max": 90.0, "unit": "%"},
    {"type": "light", "min": 0.0, "max": 1000.0, "unit": "lux"},
]

def generate_sensor_data(db: Session):
    """Update sensor data for all checkpoints - replaces existing readings instead of appending"""
    checkpoints = db.query(Checkpoint).all()
    
    if not checkpoints:
        print("No checkpoints found - skipping sensor data generation")
        return
    
    updated_count = 0
    created_count = 0
    
    for checkpoint in checkpoints:
        for sensor_type_info in SENSOR_TYPES:
            value = round(
                random.uniform(sensor_type_info["min"], sensor_type_info["max"]),
                2
            )
            
            existing_sensor = db.query(Sensor).filter(
                Sensor.checkpoint_id == checkpoint.id,
                Sensor.sensor_type == sensor_type_info["type"]
            ).first()
            
            if existing_sensor:
                existing_sensor.value = value
                existing_sensor.timestamp = datetime.utcnow()
                updated_count += 1
            else:
                sensor = Sensor(
                    checkpoint_id=checkpoint.id,
                    sensor_type=sensor_type_info["type"],
                    value=value,
                    unit=sensor_type_info["unit"],
                    timestamp=datetime.utcnow()
                )
                db.add(sensor)
                created_count += 1
    
    db.commit()
    print(f"Updated {updated_count} and created {created_count} sensor readings for {len(checkpoints)} checkpoints")

db_session = next(get_db())
db_session.close()

def scheduled_generate():
    db = SessionLocal()
    try:
        generate_sensor_data(db)
    except Exception as e:
        print(f"Error generating sensor data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

scheduler = BackgroundScheduler()

@app.on_event("startup")
def startup_event():
    """Initialize scheduler on startup"""
    scheduler.add_job(
        scheduled_generate,
        'interval',
        seconds=10,
        id='generate_sensor_data'
    )
    scheduler.start()
    print("Scheduler started - sensor data will be generated every 10 seconds")

class PumpControl(BaseModel):
    is_on: bool

class FieldCreate(BaseModel):
    name: str
    city: str
    user_id: int

class FieldUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None

class CheckpointCreate(BaseModel):
    name: str
    field_id: int

class CheckpointUpdate(BaseModel):
    name: Optional[str] = None

class TriggerTaskCreate(BaseModel):
    name: str
    field_id: int
    weather_metric: str  # temperature, humidity, wind_speed
    condition: str  # greater_than, less_than, equals
    threshold: float
    action: str  # power_on_all_pumps, power_off_all_pumps
    is_active: bool = True

class TriggerTaskUpdate(BaseModel):
    name: Optional[str] = None
    weather_metric: Optional[str] = None
    condition: Optional[str] = None
    threshold: Optional[float] = None
    action: Optional[str] = None
    is_active: Optional[bool] = None

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "irrigation-sensor-microservice"}

@app.get("/fields")
def get_fields(user_id: int, db: Session = Depends(get_db)):
    """Get all fields with their checkpoints, sensors, and pumps for a specific user"""
    try:
        fields = db.query(Field).filter(Field.user_id == user_id).all()
        
        if not fields:
            return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    result = []
    for field in fields:
        field_data = {
            "id": field.id,
            "name": field.name,
            "city": field.city,
            "checkpoints": []
        }
        for checkpoint in field.checkpoints:
            latest_sensors = {}
            for sensor_type in ["soil_moisture", "temperature", "humidity", "light"]:
                sensor = db.query(Sensor).filter(
                    Sensor.checkpoint_id == checkpoint.id,
                    Sensor.sensor_type == sensor_type
                ).first()
                
                if sensor:
                    latest_sensors[sensor_type] = {
                        "value": sensor.value,
                        "unit": sensor.unit,
                        "timestamp": sensor.timestamp.isoformat()
                    }
                else:
                    latest_sensors[sensor_type] = {
                        "value": 0,
                        "unit": "%" if sensor_type in ["soil_moisture", "humidity"] else "°C" if sensor_type == "temperature" else "lux",
                        "timestamp": datetime.utcnow().isoformat()
                    }
            
            checkpoint_data = {
                "id": checkpoint.id,
                "name": checkpoint.name,
                "sensors": latest_sensors,
                "pump": None
            }
            
            pump = db.query(Pump).filter(Pump.checkpoint_id == checkpoint.id).first()
            if pump:
                checkpoint_data["pump"] = {
                    "id": pump.id,
                    "name": pump.name,
                    "is_on": pump.is_on,
                    "last_activated": pump.last_activated.isoformat() if pump.last_activated else None
                }
            
            field_data["checkpoints"].append(checkpoint_data)
        result.append(field_data)
    return result

@app.post("/pumps/{pump_id}/control")
def control_pump(pump_id: int, control: PumpControl, db: Session = Depends(get_db)):
    """Turn pump on or off"""
    pump = db.query(Pump).filter(Pump.id == pump_id).first()
    if not pump:
        raise HTTPException(status_code=404, detail="Pump not found")
    
    pump.is_on = control.is_on
    if control.is_on:
        pump.last_activated = datetime.utcnow()
    
    db.commit()
    db.refresh(pump)
    
    return {
        "id": pump.id,
        "name": pump.name,
        "is_on": pump.is_on,
        "last_activated": pump.last_activated.isoformat() if pump.last_activated else None
    }

@app.get("/pumps")
def get_all_pumps(db: Session = Depends(get_db)):
    """Get all pumps"""
    pumps = db.query(Pump).all()
    return [
        {
            "id": pump.id,
            "checkpoint_id": pump.checkpoint_id,
            "name": pump.name,
            "is_on": pump.is_on,
            "last_activated": pump.last_activated.isoformat() if pump.last_activated else None
        }
        for pump in pumps
    ]

# Field CRUD endpoints
@app.post("/fields", status_code=201)
def create_field(field_data: FieldCreate, db: Session = Depends(get_db)):
    """Create a new field"""
    existing = db.query(Field).filter(
        Field.name == field_data.name,
        Field.user_id == field_data.user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Field with this name already exists for this user")
    
    field = Field(name=field_data.name, city=field_data.city, user_id=field_data.user_id)
    db.add(field)
    db.commit()
    db.refresh(field)
    
    return {
        "id": field.id,
        "name": field.name,
        "city": field.city,
        "created_at": field.created_at.isoformat()
    }

@app.put("/fields/{field_id}")
def update_field(field_id: int, field_data: FieldUpdate, user_id: int, db: Session = Depends(get_db)):
    """Update a field"""
    field = db.query(Field).filter(Field.id == field_id, Field.user_id == user_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    if field_data.name is not None:
        existing = db.query(Field).filter(
            Field.name == field_data.name,
            Field.id != field_id,
            Field.user_id == user_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Field with this name already exists for this user")
        field.name = field_data.name
    
    if field_data.city is not None:
        field.city = field_data.city
    
    db.commit()
    db.refresh(field)
    
    return {
        "id": field.id,
        "name": field.name,
        "city": field.city,
        "created_at": field.created_at.isoformat()
    }

@app.delete("/fields/{field_id}")
def delete_field(field_id: int, user_id: int, db: Session = Depends(get_db)):
    """Delete a field (cascades to checkpoints, sensors, and pumps)"""
    field = db.query(Field).filter(Field.id == field_id, Field.user_id == user_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    db.delete(field)
    db.commit()
    return {"message": "Field deleted successfully"}

# Checkpoint CRUD endpoints
@app.post("/checkpoints", status_code=201)
def create_checkpoint(checkpoint_data: CheckpointCreate, user_id: int, db: Session = Depends(get_db)):
    """Create a new checkpoint with sensors and pump"""
    field = db.query(Field).filter(
        Field.id == checkpoint_data.field_id,
        Field.user_id == user_id
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found or access denied")
    
    checkpoint = Checkpoint(name=checkpoint_data.name, field_id=checkpoint_data.field_id)
    db.add(checkpoint)
    db.commit()
    db.refresh(checkpoint)
    
    # Create sensors for the checkpoint
    create_sensors_for_checkpoint(db, checkpoint.id)
    
    # Create a pump for the checkpoint
    pump = Pump(checkpoint_id=checkpoint.id, name=f"Pump {checkpoint.name}")
    db.add(pump)
    db.commit()
    
    return {
        "id": checkpoint.id,
        "name": checkpoint.name,
        "field_id": checkpoint.field_id,
        "created_at": checkpoint.created_at.isoformat()
    }

@app.put("/checkpoints/{checkpoint_id}")
def update_checkpoint(checkpoint_id: int, checkpoint_data: CheckpointUpdate, user_id: int, db: Session = Depends(get_db)):
    """Update a checkpoint"""
    checkpoint = db.query(Checkpoint).join(Field).filter(
        Checkpoint.id == checkpoint_id,
        Field.user_id == user_id
    ).first()
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found or access denied")
    
    if checkpoint_data.name is not None:
        checkpoint.name = checkpoint_data.name
    
    db.commit()
    db.refresh(checkpoint)
    
    return {
        "id": checkpoint.id,
        "name": checkpoint.name,
        "field_id": checkpoint.field_id,
        "created_at": checkpoint.created_at.isoformat()
    }

@app.delete("/checkpoints/{checkpoint_id}")
def delete_checkpoint(checkpoint_id: int, user_id: int, db: Session = Depends(get_db)):
    """Delete a checkpoint (cascades to sensors and pump)"""
    checkpoint = db.query(Checkpoint).join(Field).filter(
        Checkpoint.id == checkpoint_id,
        Field.user_id == user_id
    ).first()
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found or access denied")
    
    db.delete(checkpoint)
    db.commit()
    return {"message": "Checkpoint deleted successfully"}

# Trigger Task CRUD endpoints
@app.get("/trigger-tasks")
def get_trigger_tasks(user_id: int, field_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get all trigger tasks for a user, optionally filtered by field_id"""
    query = db.query(TriggerTask).join(Field).filter(Field.user_id == user_id)
    if field_id:
        query = query.filter(TriggerTask.field_id == field_id)
    
    tasks = query.all()
    return [
        {
            "id": task.id,
            "name": task.name,
            "field_id": task.field_id,
            "weather_metric": task.weather_metric,
            "condition": task.condition,
            "threshold": task.threshold,
            "action": task.action,
            "is_active": task.is_active,
            "created_at": task.created_at.isoformat(),
            "last_triggered": task.last_triggered.isoformat() if task.last_triggered else None
        }
        for task in tasks
    ]

@app.post("/trigger-tasks", status_code=201)
def create_trigger_task(task_data: TriggerTaskCreate, user_id: int, db: Session = Depends(get_db)):
    """Create a new trigger task"""
    field = db.query(Field).filter(
        Field.id == task_data.field_id,
        Field.user_id == user_id
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found or access denied")
    
    task = TriggerTask(
        name=task_data.name,
        field_id=task_data.field_id,
        weather_metric=task_data.weather_metric,
        condition=task_data.condition,
        threshold=task_data.threshold,
        action=task_data.action,
        is_active=task_data.is_active
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    return {
        "id": task.id,
        "name": task.name,
        "field_id": task.field_id,
        "weather_metric": task.weather_metric,
        "condition": task.condition,
        "threshold": task.threshold,
        "action": task.action,
        "is_active": task.is_active,
        "created_at": task.created_at.isoformat(),
        "last_triggered": task.last_triggered.isoformat() if task.last_triggered else None
    }

@app.put("/trigger-tasks/{task_id}")
def update_trigger_task(task_id: int, task_data: TriggerTaskUpdate, user_id: int, db: Session = Depends(get_db)):
    """Update a trigger task"""
    task = db.query(TriggerTask).join(Field).filter(
        TriggerTask.id == task_id,
        Field.user_id == user_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Trigger task not found or access denied")
    
    if task_data.name is not None:
        task.name = task_data.name
    if task_data.weather_metric is not None:
        task.weather_metric = task_data.weather_metric
    if task_data.condition is not None:
        task.condition = task_data.condition
    if task_data.threshold is not None:
        task.threshold = task_data.threshold
    if task_data.action is not None:
        task.action = task_data.action
    if task_data.is_active is not None:
        task.is_active = task_data.is_active
    
    db.commit()
    db.refresh(task)
    
    return {
        "id": task.id,
        "name": task.name,
        "field_id": task.field_id,
        "weather_metric": task.weather_metric,
        "condition": task.condition,
        "threshold": task.threshold,
        "action": task.action,
        "is_active": task.is_active,
        "created_at": task.created_at.isoformat(),
        "last_triggered": task.last_triggered.isoformat() if task.last_triggered else None
    }

@app.delete("/trigger-tasks/{task_id}")
def delete_trigger_task(task_id: int, user_id: int, db: Session = Depends(get_db)):
    """Delete a trigger task"""
    task = db.query(TriggerTask).join(Field).filter(
        TriggerTask.id == task_id,
        Field.user_id == user_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Trigger task not found or access denied")
    
    db.delete(task)
    db.commit()
    return {"message": "Trigger task deleted successfully"}

@app.post("/trigger-tasks/{task_id}/evaluate")
def evaluate_trigger_task(task_id: int, weather_data: dict, db: Session = Depends(get_db)):
    """Evaluate a trigger task against weather data and execute action if condition is met"""
    task = db.query(TriggerTask).filter(TriggerTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Trigger task not found")
    
    if not task.is_active:
        return {"triggered": False, "message": "Task is not active"}
    
    # Get weather value
    weather_value = weather_data.get(task.weather_metric)
    if weather_value is None:
        raise HTTPException(status_code=400, detail=f"Weather metric {task.weather_metric} not found in weather data")
    
    # Check condition
    triggered = False
    if task.condition == "greater_than":
        triggered = weather_value > task.threshold
    elif task.condition == "less_than":
        triggered = weather_value < task.threshold
    elif task.condition == "equals":
        triggered = abs(weather_value - task.threshold) < 0.01
    
    if triggered:
        # Execute action
        field = db.query(Field).filter(Field.id == task.field_id).first()
        if not field:
            raise HTTPException(status_code=404, detail="Field not found")
        
        # Get all pumps for this field
        pumps = []
        for checkpoint in field.checkpoints:
            pump = db.query(Pump).filter(Pump.checkpoint_id == checkpoint.id).first()
            if pump:
                pumps.append(pump)
        
        # Execute action
        if task.action == "power_on_all_pumps":
            for pump in pumps:
                pump.is_on = True
                pump.last_activated = datetime.utcnow()
        elif task.action == "power_off_all_pumps":
            for pump in pumps:
                pump.is_on = False
        
        task.last_triggered = datetime.utcnow()
        db.commit()
        
        return {
            "triggered": True,
            "message": f"Action {task.action} executed for {len(pumps)} pumps",
            "weather_value": weather_value,
            "threshold": task.threshold
        }
    
    return {
        "triggered": False,
        "message": "Condition not met",
        "weather_value": weather_value,
        "threshold": task.threshold
    }

@app.on_event("shutdown")
def shutdown_event():
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler stopped")
