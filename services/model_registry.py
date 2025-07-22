"""
Model Registry Service
Manages available AI models and their metadata
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ModelSpeed(Enum):
    FASTEST = "fastest"
    FAST = "fast"
    BALANCED = "balanced"
    ACCURATE = "accurate"
    MOST_ACCURATE = "most_accurate"


@dataclass
class ModelInfo:
    """Information about an available model"""
    id: str
    name: str
    description: str
    architecture: str
    speed: ModelSpeed
    size_mb: Optional[float] = None
    map50: Optional[float] = None  # mAP@0.5 accuracy metric
    fps_estimate: Optional[int] = None  # Estimated FPS on typical hardware


class ModelRegistry:
    """Registry of available AI models"""
    
    # Define available models with their metadata
    # This can be extended to load from config file or auto-discover
    MODELS = [
        # Standard COCO models
        ModelInfo(
            id="yolov8n",
            name="YOLOv8 Nano",
            description="Fastest inference, suitable for real-time on edge devices",
            architecture="YOLOv8",
            speed=ModelSpeed.FASTEST,
            size_mb=6.3,
            map50=37.3,
            fps_estimate=120
        ),
        ModelInfo(
            id="yolov8s",
            name="YOLOv8 Small",
            description="Balanced speed and accuracy for general use",
            architecture="YOLOv8",
            speed=ModelSpeed.FAST,
            size_mb=22.5,
            map50=44.9,
            fps_estimate=90
        ),
        ModelInfo(
            id="yolov8m",
            name="YOLOv8 Medium",
            description="Good accuracy with reasonable speed",
            architecture="YOLOv8",
            speed=ModelSpeed.BALANCED,
            size_mb=52.0,
            map50=50.2,
            fps_estimate=50
        ),
        ModelInfo(
            id="yolov8l",
            name="YOLOv8 Large",
            description="High accuracy for detailed detection",
            architecture="YOLOv8",
            speed=ModelSpeed.ACCURATE,
            size_mb=87.7,
            map50=52.9,
            fps_estimate=30
        ),
        ModelInfo(
            id="yolov8x",
            name="YOLOv8 XLarge",
            description="Maximum accuracy, requires significant compute",
            architecture="YOLOv8",
            speed=ModelSpeed.MOST_ACCURATE,
            size_mb=137.0,
            map50=53.9,
            fps_estimate=15
        ),
        
        # Open Images V7 models (600+ classes including wildlife)
        ModelInfo(
            id="yolov8n-oiv7",
            name="YOLOv8 Nano OIV7",
            description="Fastest OIV7 model with 600+ classes including wildlife",
            architecture="YOLOv8-OIV7",
            speed=ModelSpeed.FASTEST,
            size_mb=12.0,
            map50=None,  # Different metrics for OIV7
            fps_estimate=100
        ),
        ModelInfo(
            id="yolov8s-oiv7",
            name="YOLOv8 Small OIV7",
            description="Balanced OIV7 model with extended wildlife detection",
            architecture="YOLOv8-OIV7",
            speed=ModelSpeed.FAST,
            size_mb=28.0,
            map50=None,
            fps_estimate=80
        ),
        ModelInfo(
            id="yolov8m-oiv7",
            name="YOLOv8 Medium OIV7",
            description="Accurate OIV7 model for diverse wildlife and object detection",
            architecture="YOLOv8-OIV7",
            speed=ModelSpeed.BALANCED,
            size_mb=52.0,
            map50=None,
            fps_estimate=45
        ),
        ModelInfo(
            id="yolov8l-oiv7",
            name="YOLOv8 Large OIV7",
            description="High accuracy OIV7 model with comprehensive class coverage",
            architecture="YOLOv8-OIV7",
            speed=ModelSpeed.ACCURATE,
            size_mb=87.0,
            map50=None,
            fps_estimate=25
        ),
        ModelInfo(
            id="yolov8x-oiv7",
            name="YOLOv8 XLarge OIV7",
            description="Maximum accuracy OIV7 model for detailed detection",
            architecture="YOLOv8-OIV7",
            speed=ModelSpeed.MOST_ACCURATE,
            size_mb=137.0,
            map50=None,
            fps_estimate=12
        ),
    ]
    
    @classmethod
    def get_available_models(cls) -> List[ModelInfo]:
        """Get list of all available models"""
        return cls.MODELS
    
    @classmethod
    def get_model_info(cls, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        for model in cls.MODELS:
            if model.id == model_id:
                return model
        return None
    
    @classmethod
    def get_models_by_architecture(cls, architecture: str) -> List[ModelInfo]:
        """Get all models for a specific architecture"""
        return [m for m in cls.MODELS if m.architecture.lower() == architecture.lower()]
    
    @classmethod
    def to_dict(cls, model: ModelInfo) -> Dict:
        """Convert ModelInfo to dictionary for JSON serialization"""
        return {
            "id": model.id,
            "name": model.name,
            "description": model.description,
            "architecture": model.architecture,
            "speed": model.speed.value,
            "size_mb": model.size_mb,
            "map50": model.map50,
            "fps_estimate": model.fps_estimate
        }
    
    @classmethod
    def validate_model_id(cls, model_id: str) -> bool:
        """Check if a model ID is valid"""
        return any(m.id == model_id for m in cls.MODELS)
    
    @classmethod
    def get_default_model(cls) -> str:
        """Get the default model ID"""
        return "yolov8n"  # Default to fastest model