# services/ai_model_manager.py
from ultralytics import YOLO
import torch
import warnings
from typing import Optional, List, Dict
from config.settings import DetectionConfig

class AIModelManager:
    def __init__(self, detection_config: DetectionConfig):
        self.detection_config = detection_config
        self.model = None
        self.device = None
        self._determine_device()
    
    def _determine_device(self):
        if torch.cuda.is_available():
            self.device = 'cuda'
        else:
            self.device = 'cpu'
    
    def load_model(self):
        if self.model is not None:
            return
        
        print(f"Loading {self.detection_config.model_name} model...")
        print(f"Detection classes: {', '.join(self.detection_config.classes)}")
        for cls in self.detection_config.classes:
            confidence = self.detection_config.get_confidence(cls)
            print(f"  {cls}: {confidence:.2f} confidence threshold")
        
        try:
            # Load YOLO model directly using the configured name
            model_name = self.detection_config.model_name
            self.model = YOLO(f'{model_name}.pt')
            
            # Set device
            if self.device == 'cuda':
                print(f"Using GPU: {torch.cuda.get_device_name()}")
            else:
                print("Using CPU for inference")
                
        except Exception as e:
            print(f"ERROR: Failed to load AI model: {e}")
            raise RuntimeError(f"Could not load YOLOv8 model: {e}")
    
    def predict(self, frame) -> List[Dict]:
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        # Run YOLOv8 inference
        results = self.model(frame, device=self.device, verbose=False)
        
        detections = []
        
        # YOLOv8 returns a list of Results objects
        for result in results:
            if result.boxes is not None:
                boxes = result.boxes
                
                # Get class names from model
                names = result.names
                
                for i in range(len(boxes)):
                    # Get box coordinates, confidence, and class
                    box = boxes.xyxy[i].cpu().numpy()
                    confidence = float(boxes.conf[i].cpu().numpy())
                    class_id = int(boxes.cls[i].cpu().numpy())
                    detection_class = names[class_id]
                    
                    # Check if this detection class is enabled and meets confidence threshold
                    # Case-insensitive comparison for class names
                    config_classes_lower = [cls.lower() for cls in self.detection_config.classes]
                    if detection_class.lower() in config_classes_lower:
                        # Find the original config class name for confidence lookup
                        for config_class in self.detection_config.classes:
                            if config_class.lower() == detection_class.lower():
                                if confidence >= self.detection_config.get_confidence(config_class):
                                    detections.append({
                                        'confidence': confidence,
                                        'bbox': [int(box[0]), int(box[1]), 
                                                int(box[2]), int(box[3])],
                                        'class': detection_class  # Use the model's class name
                                    })
                                break
        
        return detections
    
    @property
    def is_loaded(self) -> bool:
        return self.model is not None
    
    @property
    def gpu_available(self) -> bool:
        return self.device == 'cuda'