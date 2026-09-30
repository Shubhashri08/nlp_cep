"""Domain vocabulary shared by the NLP components."""

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
    "OTHER",
]

# Maps complaint categories to the infrastructure-gap sectors they signal
CATEGORY_TO_SECTOR = {
    "WATER_SUPPLY": "Water Supply",
    "DRAINAGE": "Drainage & Storm Water",
    "FLOODING": "Drainage & Storm Water",
    "WASTE_MANAGEMENT": "Waste Management",
    "HEALTHCARE": "Healthcare Capacity",
    "EDUCATION": "Education",
    "PUBLIC_TRANSPORT": "Public Transit Access",
    "TRAFFIC": "Public Transit Access",
    "PARKS": "Open Space",
    "ROAD_INFRASTRUCTURE": "Roads",
    "STREETLIGHT": "Roads",
}

# Romanised Hindi / Marathi (Hinglish) urban vocabulary -> English concept.
# Only non-English tokens belong here: English words like "leakage" or "divider" must not be listed,
# otherwise plain English complaints get tagged as code-mixed.
HINGLISH_LEXICON = {
    # water & drainage
    "paani": "water", "pani": "water", "nal": "tap", "jal": "water",
    "gatar": "drain", "naala": "drain", "nala": "drain", "naali": "drain", "nali": "drain",
    "paani bhara": "waterlogging", "pani bharla": "waterlogging", "paani bharla": "waterlogging",
    "jalsangrah": "waterlogging", "tutla": "broken", "phutla": "burst", "futla": "burst",
    "ganda pani": "contaminated water", "ganda paani": "contaminated water", "gandha pani": "contaminated water",
    "tanki": "water tank", "tankar": "water tanker",
    # roads & traffic
    "khadde": "potholes", "khadda": "pothole", "khaddyat": "in pothole", "padlet": "developed",
    "sadak": "road", "rasta": "road", "rastya": "road", "rastyavar": "on the road", "raste": "roads",
    "traffic jaam": "traffic congestion", "chakka jam": "traffic gridlock", "pul": "bridge", "gaadi": "vehicle",
    "gaadiyan": "vehicles", "rickshaw wale": "rickshaw drivers",
    # waste
    "kachra": "garbage", "kachara": "garbage", "kachra peti": "garbage bin", "kuda": "garbage", "kooda": "garbage",
    "safai": "cleaning", "durgandhi": "foul smell", "badbu": "foul smell", "vaas": "smell", "ghan": "filth",
    # electricity & light
    "batti": "light", "bijli": "electricity", "vij": "electricity", "light gayi": "power cut",
    "andhera": "darkness", "andhar": "darkness", "taar": "wire", "khamba": "pole",
    # health & safety
    "dawaakhana": "dispensary", "davakhana": "dispensary", "rugnalay": "hospital", "aspatal": "hospital",
    "haspatal": "hospital", "machhar": "mosquitoes", "rograi": "disease", "chori": "theft",
    "kutte": "dogs", "kutre": "dogs", "bhatke kutte": "stray dogs", "bhatki kutre": "stray dogs",
    # education, housing, general
    "shala": "school", "shaala": "school", "vidyalaya": "school", "ghar": "house", "imarat": "building",
    "zopadpatti": "slum", "jhopdi": "hut", "bagicha": "garden", "baag": "garden", "udyan": "park",
    "dhool": "dust", "dhuan": "smoke", "dhur": "smoke", "hawa": "air", "pradushan": "pollution",
    # function words that signal code-mixing
    "nahi": "not", "nahin": "not", "hai": "is", "hain": "are", "aahe": "is", "nahiye": "is not",
    "bahut": "very", "khup": "very", "din": "days", "divas": "days", "se": "since", "kab": "when",
    "kuch": "any", "koi": "nobody", "karo": "do", "kara": "do", "please jaldi": "please quickly", "jaldi": "quickly",
    "yaha": "here", "yahan": "here", "ithe": "here", "roz": "every day", "raat": "night", "sakali": "morning",
}

# Devanagari markers that separate Marathi from Hindi
MARATHI_MARKERS = ["आहे", "नाही", "झाला", "झाले", "रस्त्यावर", "येतोय", "आमच्या", "खूप", "दिवसांपासून", "पाहिजे"]
HINDI_MARKERS = ["है", "नहीं", "हैं", "बहुत", "दिन", "से", "कोई", "हमारे", "सड़क", "पानी नहीं"]

# Devanagari keywords -> English concept (used for classification of Hindi / Marathi text)
DEVANAGARI_LEXICON = {
    "पानी": "water", "पाणी": "water", "नल": "tap", "गटर": "drain", "नाला": "drain", "नाली": "drain",
    "सड़क": "road", "रस्ता": "road", "रस्त्यावर": "on road", "गड्ढे": "potholes", "खड्डे": "potholes",
    "कचरा": "garbage", "कूड़ा": "garbage", "बदबू": "foul smell", "दुर्गंधी": "foul smell",
    "बिजली": "electricity", "वीज": "electricity", "बत्ती": "light", "अंधेरा": "darkness", "अंधार": "darkness",
    "बाढ़": "flood", "पूर": "flood", "जलभराव": "waterlogging", "पाऊस": "rain", "बारिश": "rain",
    "अस्पताल": "hospital", "रुग्णालय": "hospital", "दवाखाना": "dispensary", "मच्छर": "mosquitoes", "डास": "mosquitoes",
    "स्कूल": "school", "शाळा": "school", "बस": "bus", "ट्रैफिक": "traffic", "वाहतूक": "traffic", "जाम": "jam",
    "पेड़": "trees", "झाडे": "trees", "प्रदूषण": "pollution", "धूल": "dust", "धूर": "smoke", "धुआं": "smoke",
    "कुत्ते": "dogs", "कुत्रे": "dogs", "चोरी": "theft", "इमारत": "building", "घर": "house", "बगीचा": "garden", "उद्यान": "park",
    "लीकेज": "leakage", "गळती": "leakage", "टूटा": "broken", "तुटलेला": "broken", "बंद": "not working",
}

MUNICIPAL_ORGS = [
    "BMC", "MCGM", "MMRDA", "BEST", "MSEDCL", "Adani Electricity", "Tata Power", "MHADA", "SRA",
    "Mumbai Police", "Traffic Police", "PWD", "MPCB", "Mumbai Fire Brigade", "Western Railway", "Central Railway",
    "MMRCL", "Mumbai Metro",
]
