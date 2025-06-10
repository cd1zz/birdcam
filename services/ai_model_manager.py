# services/ai_model_manager.py
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
        
        print(f"🤖 Loading {self.detection_config.model_name} model...")
        print(f"🎯 Detection classes: {', '.join(self.detection_config.classes)}")
        for cls in self.detection_config.classes:
            confidence = self.detection_config.get_confidence(cls)
            print(f"   {cls}: {confidence:.2f} confidence threshold")
        
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            self.model = torch.hub.load('ultralytics/yolov5', self.detection_config.model_name, force_reload=False)
            
            if self.device == 'cuda':
                self.model = self.model.cuda()
                print(f"🚀 Using GPU: {torch.cuda.get_device_name()}")
            else:
                print("💻 Using CPU for inference")
    
    def predict(self, frame) -> List[Dict]:
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            results = self.model(frame)
        
        detections = []
        results_df = results.pandas().xyxy[0]
        
        for _, row in results_df.iterrows():
            detection_class = row['name']
            confidence = float(row['confidence'])
            
            # Check if this detection class is enabled and meets confidence threshold
            if (detection_class in self.detection_config.classes and 
                confidence >= self.detection_config.get_confidence(detection_class)):
                
                detections.append({
                    'confidence': confidence,
                    'bbox': [int(row['xmin']), int(row['ymin']), 
                            int(row['xmax']), int(row['ymax'])],
                    'class': detection_class
                })
        
        return detections
    
    @property
    def is_loaded(self) -> bool:
        return self.model is not None
    
    @property
    def gpu_available(self) -> bool:
        return self.device == 'cuda'