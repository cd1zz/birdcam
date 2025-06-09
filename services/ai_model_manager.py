# services/ai_model_manager.py
import torch
import warnings
from typing import Optional

class AIModelManager:
    def __init__(self, model_name: str = 'yolov5n', confidence: float = 0.35):
        self.model_name = model_name
        self.confidence = confidence
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
        
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            self.model = torch.hub.load('ultralytics/yolov5', self.model_name, force_reload=False)
            self.model.conf = self.confidence
            
            if self.device == 'cuda':
                self.model = self.model.cuda()
    
    def predict(self, frame) -> list:
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            results = self.model(frame)
        
        detections = []
        results_df = results.pandas().xyxy[0]
        
        for _, row in results_df.iterrows():
            if row['name'] == 'bird' and row['confidence'] > self.confidence:
                detections.append({
                    'confidence': float(row['confidence']),
                    'bbox': [int(row['xmin']), int(row['ymin']), 
                            int(row['xmax']), int(row['ymax'])],
                    'class': row['name']
                })
        
        return detections
    
    @property
    def is_loaded(self) -> bool:
        return self.model is not None
    
    @property
    def gpu_available(self) -> bool:
        return self.device == 'cuda'