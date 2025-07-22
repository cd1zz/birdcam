"""
Class Registry Service
Manages available classes for different YOLO models
"""
from typing import List, Dict, Optional, Set
from dataclasses import dataclass


@dataclass
class ClassInfo:
    """Information about a detection class"""
    id: int
    name: str
    category: str
    description: Optional[str] = None


class ClassRegistry:
    """Registry of available classes for different models"""
    
    # COCO classes used by YOLOv8 (80 classes)
    COCO_CLASSES = [
        ClassInfo(0, "person", "people", "Human beings"),
        ClassInfo(1, "bicycle", "vehicles", "Two-wheeled vehicle"),
        ClassInfo(2, "car", "vehicles", "Automobile"),
        ClassInfo(3, "motorcycle", "vehicles", "Motorized two-wheeler"),
        ClassInfo(4, "airplane", "vehicles", "Aircraft"),
        ClassInfo(5, "bus", "vehicles", "Large passenger vehicle"),
        ClassInfo(6, "train", "vehicles", "Railway vehicle"),
        ClassInfo(7, "truck", "vehicles", "Large cargo vehicle"),
        ClassInfo(8, "boat", "vehicles", "Watercraft"),
        ClassInfo(9, "traffic light", "street", "Traffic control signal"),
        ClassInfo(10, "fire hydrant", "street", "Water supply for firefighting"),
        ClassInfo(11, "stop sign", "street", "Traffic stop sign"),
        ClassInfo(12, "parking meter", "street", "Parking payment device"),
        ClassInfo(13, "bench", "furniture", "Outdoor seating"),
        ClassInfo(14, "bird", "animals", "Avian species"),
        ClassInfo(15, "cat", "animals", "Feline pet"),
        ClassInfo(16, "dog", "animals", "Canine pet"),
        ClassInfo(17, "horse", "animals", "Equine animal"),
        ClassInfo(18, "sheep", "animals", "Wool-bearing livestock"),
        ClassInfo(19, "cow", "animals", "Bovine livestock"),
        ClassInfo(20, "elephant", "animals", "Large mammal with trunk"),
        ClassInfo(21, "bear", "animals", "Large omnivorous mammal"),
        ClassInfo(22, "zebra", "animals", "Striped equine"),
        ClassInfo(23, "giraffe", "animals", "Tall African mammal"),
        ClassInfo(24, "backpack", "accessories", "Bag worn on back"),
        ClassInfo(25, "umbrella", "accessories", "Rain protection device"),
        ClassInfo(26, "handbag", "accessories", "Small carrying bag"),
        ClassInfo(27, "tie", "accessories", "Necktie"),
        ClassInfo(28, "suitcase", "accessories", "Travel luggage"),
        ClassInfo(29, "frisbee", "sports", "Flying disc toy"),
        ClassInfo(30, "skis", "sports", "Snow sport equipment"),
        ClassInfo(31, "snowboard", "sports", "Snow sport board"),
        ClassInfo(32, "sports ball", "sports", "Various sport balls"),
        ClassInfo(33, "kite", "sports", "Wind-powered flying toy"),
        ClassInfo(34, "baseball bat", "sports", "Baseball equipment"),
        ClassInfo(35, "baseball glove", "sports", "Baseball catching mitt"),
        ClassInfo(36, "skateboard", "sports", "Four-wheeled board"),
        ClassInfo(37, "surfboard", "sports", "Wave riding board"),
        ClassInfo(38, "tennis racket", "sports", "Tennis equipment"),
        ClassInfo(39, "bottle", "kitchen", "Container for liquids"),
        ClassInfo(40, "wine glass", "kitchen", "Stemmed glass for wine"),
        ClassInfo(41, "cup", "kitchen", "Drinking vessel"),
        ClassInfo(42, "fork", "kitchen", "Eating utensil"),
        ClassInfo(43, "knife", "kitchen", "Cutting utensil"),
        ClassInfo(44, "spoon", "kitchen", "Eating utensil"),
        ClassInfo(45, "bowl", "kitchen", "Round dish"),
        ClassInfo(46, "banana", "food", "Yellow curved fruit"),
        ClassInfo(47, "apple", "food", "Round fruit"),
        ClassInfo(48, "sandwich", "food", "Bread with filling"),
        ClassInfo(49, "orange", "food", "Citrus fruit"),
        ClassInfo(50, "broccoli", "food", "Green vegetable"),
        ClassInfo(51, "carrot", "food", "Orange root vegetable"),
        ClassInfo(52, "hot dog", "food", "Sausage in bun"),
        ClassInfo(53, "pizza", "food", "Italian flatbread dish"),
        ClassInfo(54, "donut", "food", "Fried dough pastry"),
        ClassInfo(55, "cake", "food", "Sweet baked dessert"),
        ClassInfo(56, "chair", "furniture", "Seat with back"),
        ClassInfo(57, "couch", "furniture", "Long upholstered seat"),
        ClassInfo(58, "potted plant", "furniture", "Plant in container"),
        ClassInfo(59, "bed", "furniture", "Sleeping furniture"),
        ClassInfo(60, "dining table", "furniture", "Table for meals"),
        ClassInfo(61, "toilet", "furniture", "Bathroom fixture"),
        ClassInfo(62, "tv", "electronics", "Television set"),
        ClassInfo(63, "laptop", "electronics", "Portable computer"),
        ClassInfo(64, "mouse", "electronics", "Computer pointing device"),
        ClassInfo(65, "remote", "electronics", "Remote control"),
        ClassInfo(66, "keyboard", "electronics", "Computer input device"),
        ClassInfo(67, "cell phone", "electronics", "Mobile phone"),
        ClassInfo(68, "microwave", "appliances", "Cooking appliance"),
        ClassInfo(69, "oven", "appliances", "Baking appliance"),
        ClassInfo(70, "toaster", "appliances", "Bread toasting device"),
        ClassInfo(71, "sink", "appliances", "Basin with water tap"),
        ClassInfo(72, "refrigerator", "appliances", "Food cooling appliance"),
        ClassInfo(73, "book", "indoor", "Printed publication"),
        ClassInfo(74, "clock", "indoor", "Time display device"),
        ClassInfo(75, "vase", "indoor", "Decorative container"),
        ClassInfo(76, "scissors", "indoor", "Cutting tool"),
        ClassInfo(77, "teddy bear", "indoor", "Stuffed toy bear"),
        ClassInfo(78, "hair drier", "indoor", "Hair drying device"),
        ClassInfo(79, "toothbrush", "indoor", "Dental hygiene tool"),
    ]
    
    # Open Images V7 wildlife and nature-related classes (subset of 600+ classes)
    OIV7_WILDLIFE_CLASSES = [
        # Birds
        ClassInfo(0, "bird", "animals", "General bird species"),
        ClassInfo(1, "duck", "animals", "Duck species"),
        ClassInfo(2, "chicken", "animals", "Domestic chicken"),
        ClassInfo(3, "goose", "animals", "Goose species"),
        ClassInfo(4, "swan", "animals", "Swan species"),
        ClassInfo(5, "owl", "animals", "Owl species"),
        ClassInfo(6, "eagle", "animals", "Eagle species"),
        ClassInfo(7, "parrot", "animals", "Parrot species"),
        ClassInfo(8, "sparrow", "animals", "Sparrow species"),
        ClassInfo(9, "raven", "animals", "Raven species"),
        ClassInfo(10, "woodpecker", "animals", "Woodpecker species"),
        ClassInfo(11, "turkey", "animals", "Turkey"),
        
        # Common mammals
        ClassInfo(20, "squirrel", "animals", "Squirrel species"),
        ClassInfo(21, "cat", "animals", "Feline species"),
        ClassInfo(22, "dog", "animals", "Canine species"),
        ClassInfo(23, "rabbit", "animals", "Rabbit species"),
        ClassInfo(24, "hamster", "animals", "Hamster"),
        ClassInfo(25, "mouse", "animals", "Mouse species"),
        ClassInfo(26, "rat", "animals", "Rat species"),
        ClassInfo(27, "fox", "animals", "Fox species"),
        ClassInfo(28, "raccoon", "animals", "Raccoon"),
        ClassInfo(29, "deer", "animals", "Deer species"),
        ClassInfo(30, "bear", "animals", "Bear species"),
        ClassInfo(31, "hedgehog", "animals", "Hedgehog"),
        ClassInfo(32, "bat", "animals", "Bat species"),
        ClassInfo(33, "skunk", "animals", "Skunk"),
        ClassInfo(34, "chipmunk", "animals", "Chipmunk"),
        
        # Reptiles and amphibians
        ClassInfo(40, "lizard", "animals", "Lizard species"),
        ClassInfo(41, "snake", "animals", "Snake species"),
        ClassInfo(42, "turtle", "animals", "Turtle species"),
        ClassInfo(43, "frog", "animals", "Frog species"),
        ClassInfo(44, "tortoise", "animals", "Tortoise species"),
        
        # Insects
        ClassInfo(50, "butterfly", "animals", "Butterfly species"),
        ClassInfo(51, "bee", "animals", "Bee species"),
        ClassInfo(52, "ladybug", "animals", "Ladybug"),
        ClassInfo(53, "dragonfly", "animals", "Dragonfly"),
        ClassInfo(54, "ant", "animals", "Ant species"),
        ClassInfo(55, "spider", "animals", "Spider species"),
        
        # Farm animals
        ClassInfo(60, "horse", "animals", "Horse"),
        ClassInfo(61, "cattle", "animals", "Cattle/Cow"),
        ClassInfo(62, "sheep", "animals", "Sheep"),
        ClassInfo(63, "goat", "animals", "Goat"),
        ClassInfo(64, "pig", "animals", "Pig"),
        
        # People and vehicles (for comparison with COCO)
        ClassInfo(70, "person", "people", "Human being"),
        ClassInfo(71, "car", "vehicles", "Automobile"),
        ClassInfo(72, "bicycle", "vehicles", "Two-wheeled vehicle"),
        
        # Note: This is a subset. Full OIV7 has 600+ classes
    ]
    
    # Map model architectures to their class lists
    MODEL_CLASSES = {
        "YOLOv8": COCO_CLASSES,
        "YOLOv5": COCO_CLASSES,  # YOLOv5 also uses COCO classes
        "YOLOv8-OIV7": OIV7_WILDLIFE_CLASSES,  # Open Images V7 models
    }
    
    @classmethod
    def get_classes_for_model(cls, model_id: str) -> List[ClassInfo]:
        """Get available classes for a specific model"""
        # Extract architecture from model_id
        if model_id.endswith("-oiv7"):
            # Open Images V7 models
            architecture = "YOLOv8-OIV7"
        elif model_id.startswith("yolov8"):
            architecture = "YOLOv8"
        elif model_id.startswith("yolov5"):
            architecture = "YOLOv5"
        else:
            # Default to COCO classes
            architecture = "YOLOv8"
        
        return cls.MODEL_CLASSES.get(architecture, cls.COCO_CLASSES)
    
    @classmethod
    def get_categories(cls, model_id: str) -> List[str]:
        """Get unique categories for a model's classes"""
        classes = cls.get_classes_for_model(model_id)
        categories = sorted(set(c.category for c in classes))
        return categories
    
    @classmethod
    def get_class_by_name(cls, model_id: str, class_name: str) -> Optional[ClassInfo]:
        """Get class info by name"""
        classes = cls.get_classes_for_model(model_id)
        for class_info in classes:
            if class_info.name == class_name:
                return class_info
        return None
    
    @classmethod
    def get_class_by_id(cls, model_id: str, class_id: int) -> Optional[ClassInfo]:
        """Get class info by ID"""
        classes = cls.get_classes_for_model(model_id)
        for class_info in classes:
            if class_info.id == class_id:
                return class_info
        return None
    
    @classmethod
    def to_dict(cls, class_info: ClassInfo) -> Dict:
        """Convert ClassInfo to dictionary for JSON serialization"""
        return {
            "id": class_info.id,
            "name": class_info.name,
            "category": class_info.category,
            "description": class_info.description
        }
    
    @classmethod
    def get_wildlife_preset(cls) -> List[str]:
        """Get preset list of wildlife-related classes"""
        return ["bird", "squirrel", "cat", "dog", "rabbit", "deer", "raccoon",
                "fox", "bear", "duck", "goose", "owl", "eagle", "woodpecker",
                "chipmunk", "skunk", "butterfly", "bee"]
    
    @classmethod
    def get_people_preset(cls) -> List[str]:
        """Get preset list of people-related classes"""
        return ["person", "bicycle", "car", "motorcycle", "bus", "truck"]
    
    @classmethod
    def get_all_animal_classes(cls) -> List[str]:
        """Get all animal classes from COCO"""
        animal_classes = []
        for class_info in cls.COCO_CLASSES:
            if class_info.category == "animals":
                animal_classes.append(class_info.name)
        return animal_classes