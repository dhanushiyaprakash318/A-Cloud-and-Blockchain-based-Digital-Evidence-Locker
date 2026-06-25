from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any
from datetime import datetime

class Accused(BaseModel):
    id: Optional[str] = None
    name: str
    fatherName: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    mobile: Optional[str] = None
    status: str
    photo: Optional[str] = None

class Evidence(BaseModel):
    id: Optional[str] = None
    name: str
    type: str
    url: Optional[str] = None
    uploadedAt: Optional[str] = None
    metadata: Optional[dict] = None

class CaseCreate(BaseModel):
    district: str
    unit: str
    lawSections: List[str]
    dateOfOffence: str
    dateOfReport: str
    sceneOfCrime: str
    latitude: float = Field(..., description="Latitude as decimal number")
    longitude: float = Field(..., description="Longitude as decimal number")
    contrabandType: Optional[str] = None
    contrabandQuantity: Optional[str] = None
    vehicleDetails: Optional[str] = None
    accused: List[Accused]
    customFields: List[Any] = []
    publicAlertEnabled: bool = False
    publicAlertMessage: Optional[str] = None
    publicAlertMobile: Optional[str] = None

    @validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v

class Case(BaseModel):
    id: str
    caseNumber: str
    district: str
    unit: str
    status: str
    lawSections: List[str]
    dateOfOffence: str
    dateOfReport: str
    sceneOfCrime: str
    latitude: float
    longitude: float
    description: Optional[str] = None
    accused: List[Accused]
    evidence: List[Evidence] = []
    createdAt: str
    updatedAt: str
    hash: Optional[str] = None
    tx_hash: Optional[str] = None
    customFields: List[Any] = []
    publicAlertEnabled: bool = False