import os
import pickle
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline
from backend.app.core.config import settings

# Comprehensive list of Urban Planning Issue Categories
CATEGORIES = [
    "ROAD_INFRASTRUCTURE",
    "TRAFFIC",
    "PUBLIC_TRANSPORT",
    "WASTE_MANAGEMENT",
    "WATER_SUPPLY",
    "DRAINAGE",
    "FLOODING",
    "STREETLIGHT",
    "ELECTRICITY",
    "PUBLIC_SAFETY",
    "HEALTHCARE",
    "EDUCATION",
    "PARKS",
    "ENVIRONMENT",
    "AIR_QUALITY",
    "HOUSING",
    "OTHER"
]

class UrbanNLPClassifier:
    def __init__(self, model_version: str = "v1.0-tfidf-ovr"):
        self.model_version = model_version
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.clf: Optional[OneVsRestClassifier] = None
        self.category_names = CATEGORIES
        self.model_path = os.path.join(settings.MODELS_DIR, f"nlp_classifier_{model_version}.pkl")
        self._initialize_or_load()

    def _initialize_or_load(self):
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    data = pickle.load(f)
                    self.vectorizer = data["vectorizer"]
                    self.clf = data["classifier"]
                    self.category_names = data.get("category_names", CATEGORIES)
                    return
            except Exception:
                pass
        self._train_baseline_model()

    def _train_baseline_model(self):
        """
        Trains and calibrates a real multi-label OneVsRest Logistic Regression classifier
        on representative domain vocabulary and citizen grievance formulations across all categories.
        """
        training_corpus = [
            # ROAD_INFRASTRUCTURE
            ("Deep potholes on the main road causing accidents and severe vehicle damage", ["ROAD_INFRASTRUCTURE"]),
            ("Road surface completely broken and cratered after monsoon rains khadde rasta", ["ROAD_INFRASTRUCTURE"]),
            ("Pavements and footpath broken causing pedestrians to walk on busy road", ["ROAD_INFRASTRUCTURE"]),
            ("Dangerous open trench dug up for cable laying and left uncovered on street", ["ROAD_INFRASTRUCTURE", "PUBLIC_SAFETY"]),
            ("Road divider broken and dangerous for vehicles at night", ["ROAD_INFRASTRUCTURE", "TRAFFIC"]),
            
            # TRAFFIC
            ("Severe traffic jam and gridlock during peak hours at junction chakka jam", ["TRAFFIC"]),
            ("Traffic signal not working at major intersection causing chaos and near misses", ["TRAFFIC", "ROAD_INFRASTRUCTURE"]),
            ("Illegal vehicle parking on both sides choking the narrow road", ["TRAFFIC"]),
            ("Heavy commercial trucks blocking the bypass road causing long queues", ["TRAFFIC"]),
            
            # PUBLIC_TRANSPORT
            ("Bus frequency is extremely poor during morning rush hours no buses for 45 minutes", ["PUBLIC_TRANSPORT"]),
            ("Bus stop shelter damaged with no seating and broken roof", ["PUBLIC_TRANSPORT", "INFRASTRUCTURE"]),
            ("Metro feeder bus service needed from residential colony to station", ["PUBLIC_TRANSPORT"]),
            ("Overcrowded public buses missing scheduled timings", ["PUBLIC_TRANSPORT"]),
            
            # WASTE_MANAGEMENT
            ("Garbage pile accumulating on street corner not cleared for five days kachra durgandhi", ["WASTE_MANAGEMENT"]),
            ("Overflowing waste bins with foul smell attracting stray animals and pests", ["WASTE_MANAGEMENT", "ENVIRONMENT"]),
            ("Illegal garbage dumping on open plot creating health hazard kachra peti", ["WASTE_MANAGEMENT", "HEALTHCARE"]),
            ("Door to door garbage collection vehicle has not visited this week", ["WASTE_MANAGEMENT"]),
            
            # WATER_SUPPLY
            ("No municipal tap water supply for last three days paani nahi nal pipeline", ["WATER_SUPPLY"]),
            ("Contaminated muddy foul-smelling drinking water coming from pipeline ganda pani", ["WATER_SUPPLY", "HEALTHCARE"]),
            ("Main drinking water pipeline leakage wasting thousands of liters of clean water", ["WATER_SUPPLY"]),
            ("Low water pressure on top floors pipeline replacement required", ["WATER_SUPPLY"]),
            
            # DRAINAGE
            ("Underground sewer drain blocked with sewage overflowing on road naala blocked", ["DRAINAGE"]),
            ("Drainage pipeline choked with plastic waste causing dirty water backflow gutter", ["DRAINAGE", "WASTE_MANAGEMENT"]),
            ("Open storm water drain without safety slabs naali cover missing", ["DRAINAGE", "PUBLIC_SAFETY"]),
            ("Sewage line broken and leaking into storm water drain", ["DRAINAGE", "ENVIRONMENT"]),
            
            # FLOODING
            ("Severe waterlogging and knee deep flood water during monsoon rain paani bharla", ["FLOODING", "DRAINAGE"]),
            ("Low-lying residential area submerged in flood water after heavy rains", ["FLOODING"]),
            ("Road near the school is flooded with stagnant rain water and garbage", ["FLOODING", "ROAD_INFRASTRUCTURE", "WASTE_MANAGEMENT"]),
            ("Underpass completely waterlogged and closed for vehicular traffic", ["FLOODING", "TRAFFIC"]),
            
            # STREETLIGHT
            ("Streetlights not working on entire avenue complete darkness at night andhera batti", ["STREETLIGHT"]),
            ("Flickering streetlight pole creating dangerous dark spots for pedestrians", ["STREETLIGHT", "PUBLIC_SAFETY"]),
            ("New LED streetlight required on dark alley near residential park", ["STREETLIGHT"]),
            
            # ELECTRICITY
            ("Exposed high voltage electrical wire hanging dangerously low on footpath current", ["ELECTRICITY", "PUBLIC_SAFETY"]),
            ("Frequent power cuts and voltage fluctuations in the ward area", ["ELECTRICITY"]),
            ("Transformer sparking near market area danger of fire", ["ELECTRICITY", "PUBLIC_SAFETY"]),
            
            # PUBLIC_SAFETY
            ("Lack of police patrolling and poor lighting leading to unsafe streets at night", ["PUBLIC_SAFETY", "STREETLIGHT"]),
            ("Aggressive pack of stray dogs chasing two-wheelers and children bhatki kutre", ["PUBLIC_SAFETY"]),
            ("Broken safety railings on bridge over railway tracks", ["PUBLIC_SAFETY", "ROAD_INFRASTRUCTURE"]),
            
            # HEALTHCARE
            ("Primary health center dispensary lacks doctors and basic medicines dawaakhana", ["HEALTHCARE"]),
            ("High mosquito breeding due to stagnant water creating dengue and malaria risk rograi", ["HEALTHCARE", "DRAINAGE", "ENVIRONMENT"]),
            ("Municipal clinic needs emergency ambulance service and maternal ward", ["HEALTHCARE"]),
            
            # EDUCATION
            ("Municipal primary school building has broken windows and leaking ceiling", ["EDUCATION"]),
            ("Lack of clean drinking water toilets and sanitation in government high school", ["EDUCATION", "WATER_SUPPLY"]),
            ("Need public library and digital study room in ward community center", ["EDUCATION"]),
            
            # PARKS
            ("Public garden and children park in neglected condition with broken swings and overgrown grass", ["PARKS"]),
            ("Encroachment on municipal park land and lack of maintenance", ["PARKS"]),
            ("Need jogging track and tree plantation in community open space", ["PARKS", "ENVIRONMENT"]),
            
            # ENVIRONMENT
            ("Illegal cutting of mature trees on avenue road without permission", ["ENVIRONMENT"]),
            ("Industrial effluents discharged into local lake causing fish deaths", ["ENVIRONMENT", "WATER_SUPPLY"]),
            ("Open burning of municipal solid waste and dry leaves causing smoke", ["ENVIRONMENT", "AIR_QUALITY"]),
            
            # AIR_QUALITY
            ("Severe air pollution PM2.5 dust from unmonitored construction site", ["AIR_QUALITY", "ENVIRONMENT"]),
            ("Heavy smog and vehicle emissions causing breathing difficulties", ["AIR_QUALITY", "HEALTHCARE"]),
            ("Dust pollution on unpaved road requiring regular water sprinkling", ["AIR_QUALITY", "ROAD_INFRASTRUCTURE"]),
            
            # HOUSING
            ("Dilapidated old building in dangerous condition risking collapse", ["HOUSING", "PUBLIC_SAFETY"]),
            ("Slum rehabilitation project basic amenities missing", ["HOUSING", "INFRASTRUCTURE"]),
            
            # OTHER
            ("Inquiry regarding property tax assessment and municipal trade license renewal", ["OTHER"]),
            ("General public feedback on ward administrative committee meeting", ["OTHER"])
        ]
        
        X_texts = [item[0] for item in training_corpus]
        # Multi-hot encode labels
        Y_labels = np.zeros((len(training_corpus), len(CATEGORIES)), dtype=int)
        for i, (_, labels) in enumerate(training_corpus):
            for lbl in labels:
                if lbl in CATEGORIES:
                    idx = CATEGORIES.index(lbl)
                    Y_labels[i, idx] = 1
                    
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True
        )
        X_vec = self.vectorizer.fit_transform(X_texts)
        
        self.clf = OneVsRestClassifier(LogisticRegression(C=2.0, max_iter=500, class_weight='balanced'))
        self.clf.fit(X_vec, Y_labels)
        
        # Save trained artifact
        os.makedirs(settings.MODELS_DIR, exist_ok=True)
        with open(self.model_path, "wb") as f:
            pickle.dump({
                "vectorizer": self.vectorizer,
                "classifier": self.clf,
                "category_names": CATEGORIES,
                "version": self.model_version
            }, f)

    def predict(self, text: str, threshold: float = 0.25) -> Tuple[str, float, List[Dict[str, Any]]]:
        """
        Classifies input text.
        Returns:
            primary_category: str (highest probability category)
            top_confidence: float
            categories: List[Dict[str, Any]] with all categories meeting multi-label threshold
        """
        if not text or not text.strip():
            return "OTHER", 0.0, [{"category": "OTHER", "confidence": 0.0}]
            
        X_vec = self.vectorizer.transform([text])
        # Predict probability for each class
        probs = self.clf.predict_proba(X_vec)[0]
        
        ranked_indices = np.argsort(probs)[::-1]
        top_idx = ranked_indices[0]
        primary_category = self.category_names[top_idx]
        top_confidence = float(probs[top_idx])
        
        # Multi-label list: categories >= threshold or at least top category
        multi_categories = []
        for idx in ranked_indices:
            score = float(probs[idx])
            if score >= threshold or len(multi_categories) == 0:
                multi_categories.append({
                    "category": self.category_names[idx],
                    "confidence": round(score, 4)
                })
                
        return primary_category, round(top_confidence, 4), multi_categories

nlp_classifier = UrbanNLPClassifier()
