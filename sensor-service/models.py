from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=False, default="Dublin")
    user_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    checkpoints = relationship("Checkpoint", back_populates="field", cascade="all, delete-orphan")

class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    name = Column(String, nullable=False)  # e.g., "Checkpoint A", "Checkpoint B"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    field = relationship("Field", back_populates="checkpoints")
    sensors = relationship("Sensor", back_populates="checkpoint", cascade="all, delete-orphan")
    pump = relationship("Pump", back_populates="checkpoint", uselist=False, cascade="all, delete-orphan")

class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    checkpoint_id = Column(Integer, ForeignKey("checkpoints.id"), nullable=False)
    sensor_type = Column(String, nullable=False)  # soil_moisture, temperature, humidity, light
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    checkpoint = relationship("Checkpoint", back_populates="sensors")

class Pump(Base):
    __tablename__ = "pumps"

    id = Column(Integer, primary_key=True, index=True)
    checkpoint_id = Column(Integer, ForeignKey("checkpoints.id"), nullable=False, unique=True)
    name = Column(String, nullable=False)  # e.g., "Pump A"
    is_on = Column(Boolean, default=False, nullable=False)
    last_activated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    checkpoint = relationship("Checkpoint", back_populates="pump")

class TriggerTask(Base):
    __tablename__ = "trigger_tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    weather_metric = Column(String, nullable=False)  # temperature, humidity, wind_speed
    condition = Column(String, nullable=False)  # greater_than, less_than, equals
    threshold = Column(Float, nullable=False)
    action = Column(String, nullable=False)  # power_on_all_pumps, power_off_all_pumps
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)
    
    field = relationship("Field")

