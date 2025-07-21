# services/ai_model_manager.py
import torch
import warnings
import os
import sys
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
        
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            warnings.filterwarnings("ignore", category=UserWarning)
            # Disable YOLOv5 auto-update
            os.environ['YOLO_VERBOSE'] = 'False'
            
            try:
                # Save original sys.path and clean it to avoid 'utils' module conflicts
                # This is a known issue with YOLOv5 when loaded via torch.hub
                original_path = sys.path.copy()
                sys.path = [p for p in sys.path if p not in ['', '.', os.getcwd()]]
                
                try:
                    # Clear any cached 'utils' module that might conflict
                    if 'utils' in sys.modules:
                        del sys.modules['utils']
                    
                    # Disable repository validation
                    torch.hub._validate_not_a_forked_repo = lambda a, b, c: None
                    
                    # Load the model
                    self.model = torch.hub.load('ultralytics/yolov5', self.detection_config.model_name,
                                              pretrained=True, force_reload=False, verbose=False,
                                              trust_repo=True, skip_validation=True)
                finally:
                    # Always restore the original path
                    sys.path = original_path
                    
            except Exception as e:
                print(f"ERROR: Failed to load AI model: {e}")
                raise RuntimeError(f"Could not load YOLOv5 model: {e}")
            
            if self.device == 'cuda':
                self.model = self.model.cuda()
                print(f"Using GPU: {torch.cuda.get_device_name()}")
            else:
                print("Using CPU for inference")
    
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