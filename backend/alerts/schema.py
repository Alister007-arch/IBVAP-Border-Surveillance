"""
backend/alerts/schema.py
--------------------------
Pydantic schema for the 6-Tier Intelligence & Alerting System.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AlertPriority(str, Enum):
    RED   = "RED"    # Critical: Boundary Crossing / Mass Incursion / Hostile Aerial
    AMBER = "AMBER"  # High: Group Activity / Drone / Re-ID Target Match
    BLUE  = "BLUE"   # Medium: Standard Entity Detection (Person / Vehicle / Animal)
    GRAY  = "GRAY"   # Low: Verified unidentified object


class AlertCategory(str, Enum):
    PERSON              = "Person"
    WEAPON              = "Weapon"
    INFILTRATION        = "Infiltration"
    VEHICLE             = "Vehicle"
    ANIMAL              = "Animal"
    DRONE               = "Drone"
    GROUP               = "Group"
    REID_MATCH          = "ReID-Match"
    MULTI_SECTOR        = "Multi-Sector"
    UNIDENTIFIED        = "Unidentified"
    VIRTUAL_FENCE       = "Virtual Fence"
    FACE_RECOGNITION    = "Face Recognition"
    ANPR_PLATE          = "ANPR Plate"
    SUSPICIOUS_ACTIVITY = "Suspicious Activity"
    NIGHT_MOVEMENT      = "Night Movement"
    SYSTEM              = "System"


class SectionType(int, Enum):
    SECTION_1_KNOWN_OBJECTS  = 1  # Person, Vehicle, Animal
    SECTION_2_DRONE_SMALL    = 2  # Drone & Small Aerial Objects
    SECTION_3_MASS_GROUP     = 3  # Group of People / Large Numbers
    SECTION_4_REID_MATCH     = 4  # Cross-Frame / Camera Identity Matcher
    SECTION_5_MULTI_POINT    = 5  # Multi-Sector Simultaneous Activity
    SECTION_6_UNIDENTIFIED   = 6  # Verified unidentified object


SECTION_TITLES: Dict[int, str] = {
    1: "Recon: Person / Vehicle / Animal",
    2: "Aerial: Drones & Small Objects",
    3: "Mass Incursions: Group Clusters",
    4: "Identity Memory: Re-ID Matcher",
    5: "Multi-Sector: Dispersed Activity",
    6: "Unidentified: Verified Object",
}


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class Alert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    section: int = 1
    section_title: str = "Recon: Person / Vehicle / Animal"
    camera_id: str
    location: str
    category: str                  # Person, Vehicle, Animal, Drone, Group, ReID-Match, Multi-Sector, Unidentified
    priority: AlertPriority
    description: str
    bboxes: List[BoundingBox] = Field(default_factory=list)
    track_ids: List[int] = Field(default_factory=list)
    global_id: Optional[str] = None
    group_size: int = 1
    is_crossing: bool = False
    is_active: bool = True
    similarity_score: Optional[float] = None
    unidentified_confidence: Optional[float] = None
    incursion_points_count: Optional[int] = None
    plate_number: Optional[str] = None
    face_name: Optional[str] = None
    snapshot_b64: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SystemStatus(BaseModel):
    total_cameras: int
    cameras_online: int
    active_tracks: int
    active_alerts: int
    section_counts: Dict[int, int] = Field(default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0})
    last_update: datetime = Field(default_factory=datetime.utcnow)
    zone_name: str = "Border Sector North (Alpha-7)"


class WSMessage(BaseModel):
    type: str
    camera_id: Optional[str] = None
    payload: dict
