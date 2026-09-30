"""Labelled training corpus for the grievance classifier.

No public, labelled, Mumbai-specific grievance corpus is openly licensed, so the training set is
built from category-specific phrase inventories combined by templates (English, Hinglish and
Devanagari variants, plus multi-label combinations). A *separate* hand-written gold set (GOLD_SET)
never used in training gives an honest estimate of generalisation.

The synthetic citizen-complaint generator used for demo data (scripts/synthetic.py) uses its own,
different phrase inventory so the classifier is not evaluated on its own training templates.
"""
import random
from typing import List, Tuple

from backend.app.nlp.lexicon import CATEGORIES

PHRASES = {
    "ROAD_INFRASTRUCTURE": {
        "en": ["deep potholes on the road", "road surface completely broken", "cratered asphalt after the rains",
               "footpath paver blocks are uprooted", "road divider is broken", "open trench dug for cable work left uncovered",
               "uneven road with loose gravel", "manhole cover sunk below road level", "speed breaker without markings",
               "road cave-in near the junction", "resurfacing work left half done", "broken pavement forcing people onto the road"],
        "hi": ["rasta mein bahut khadde hai", "sadak puri tut gayi hai", "khadde padlet rastyavar", "footpath tuta hua hai"],
        "dev": ["सड़क पर बहुत गड्ढे हैं", "रस्त्यावर खड्डे पडले आहेत"],
    },
    "TRAFFIC": {
        "en": ["severe traffic jam during peak hours", "traffic signal not working at the junction", "illegal parking on both sides of the lane",
               "vehicles driving on the wrong side", "gridlock every evening near the flyover", "heavy trucks blocking the road",
               "no traffic police at the busy intersection", "autorickshaws blocking the station road", "double parking choking the street",
               "long queues of vehicles at the toll naka"],
        "hi": ["roz chakka jam hota hai", "traffic jaam se bahut pareshani hai", "signal band hai aur gaadiyan fasi hai"],
        "dev": ["यहां रोज ट्रैफिक जाम होता है", "वाहतूक कोंडी खूप आहे"],
    },
    "PUBLIC_TRANSPORT": {
        "en": ["bus frequency is very poor in the morning", "no BEST bus for forty minutes", "bus stop shelter is damaged",
               "need a feeder bus to the metro station", "overcrowded local trains and no extra services", "bus route was withdrawn without notice",
               "metro station has no escalator working", "no bus stop within walking distance", "railway foot overbridge is overcrowded",
               "buses skip our stop during rush hour"],
        "hi": ["bus bahut der se aati hai", "bus stop ka shed tut gaya hai", "local train mein bahut bheed hai"],
        "dev": ["बस बहुत देर से आती है", "बस थांब्यावर निवारा नाही"],
    },
    "WASTE_MANAGEMENT": {
        "en": ["garbage not collected for five days", "overflowing waste bins on the corner", "illegal dumping of debris on the open plot",
               "door to door garbage collection van has not come", "burning of garbage behind the market", "rotting waste attracting rats",
               "community bin missing from the lane", "construction debris dumped on the footpath", "plastic waste piling near the nullah",
               "wet and dry waste mixed and left on the street"],
        "hi": ["kachra kai din se nahi utha", "kachra peti bhar gayi hai aur durgandhi aa rahi hai", "yahan kuda dala jata hai"],
        "dev": ["कचरा कई दिनों से नहीं उठाया गया", "कचरा उचलला नाही, दुर्गंधी येते"],
    },
    "WATER_SUPPLY": {
        "en": ["no municipal water supply for three days", "contaminated muddy drinking water from the tap", "main water pipeline leakage wasting water",
               "very low water pressure on upper floors", "water supply timing changed without notice", "water tanker has not arrived",
               "yellow smelly water in the taps", "illegal water connections reducing supply", "burst water main flooding the lane",
               "water comes only for twenty minutes a day"],
        "hi": ["paani nahi aa raha teen din se", "nal mein ganda pani aa raha hai", "paani ki pipeline phutla hai"],
        "dev": ["तीन दिन से पानी नहीं आ रहा", "नळाला गढूळ पाणी येत आहे"],
    },
    "DRAINAGE": {
        "en": ["sewer line blocked and overflowing", "drain choked with plastic", "open drain without cover slabs",
               "sewage water flowing on the road", "manhole overflowing with sewage", "nullah not desilted before monsoon",
               "gutter water entering houses", "broken drainage chamber emitting stench", "storm water drain clogged with silt",
               "sewage leaking into the storm drain"],
        "hi": ["gatar jam ho gaya hai", "naala saaf nahi hua", "naali ka ganda paani rastyavar"],
        "dev": ["गटर तुंबले आहे", "नाली जाम है और गंदा पानी सड़क पर"],
    },
    "FLOODING": {
        "en": ["knee deep waterlogging during heavy rain", "low lying area submerged after rains", "underpass flooded and closed",
               "rain water entering ground floor homes", "flooding every monsoon near the station", "waterlogged road for two days after rain",
               "subway fills with rain water", "high tide and rain causing flooding", "water accumulation on the highway service road",
               "chawl flooded after overnight downpour"],
        "hi": ["baarish mein paani bhara hai", "pani bharla aahe gharat", "har monsoon mein yahan paani bharta hai"],
        "dev": ["बारिश में जलभराव हो गया है", "पावसात पाणी साचले आहे"],
    },
    "STREETLIGHT": {
        "en": ["streetlights not working on the entire lane", "flickering street lamp", "street light pole damaged",
               "dark stretch near the park due to no lights", "streetlight on during the day and off at night", "new LED streetlight required",
               "lights near the bus stop have been off for weeks", "streetlight wires exposed at the base"],
        "hi": ["street light band hai", "batti nahi jal rahi raat ko andhera", "khamba ki light kharab hai"],
        "dev": ["रात को स्ट्रीट लाइट बंद रहती है", "रस्त्यावरील दिवे बंद आहेत"],
    },
    "ELECTRICITY": {
        "en": ["frequent power cuts in the area", "exposed high voltage wire hanging low", "transformer sparking at night",
               "voltage fluctuation damaging appliances", "electric meter box open and dangerous", "power outage for six hours",
               "cable fault after digging work", "live wire fallen on the footpath"],
        "hi": ["bijli baar baar jaati hai", "light gayi hai subah se", "taar latak raha hai khatarnak"],
        "dev": ["बार बार बिजली जाती है", "वीज पुरवठा खंडित झाला आहे"],
    },
    "PUBLIC_SAFETY": {
        "en": ["stray dogs attacking children", "chain snatching incidents near the station", "no police patrolling at night",
               "broken railing on the bridge", "drunk people creating nuisance", "unsafe for women after dark",
               "dilapidated wall about to fall on the footpath", "fire hazard from illegal gas cylinders", "eve teasing near the college",
               "open manhole is a danger to pedestrians"],
        "hi": ["bhatke kutte bahut hai bacchon ko kaat te hai", "raat ko chori hoti hai", "yahan koi police nahi aati"],
        "dev": ["आवारा कुत्ते बच्चों पर हमला करते हैं", "रात्री चोरी होते"],
    },
    "HEALTHCARE": {
        "en": ["dispensary has no doctor", "municipal hospital out of medicines", "mosquito breeding causing dengue cases",
               "long queues at the health post", "need a maternity ward nearby", "ambulance took two hours to arrive",
               "malaria cases rising in the colony", "no fogging done this monsoon", "hospital beds are always full"],
        "hi": ["dawaakhana mein doctor nahi hai", "machhar bahut hai dengue ho raha hai", "aspatal mein dawai nahi milti"],
        "dev": ["दवाखान्यात डॉक्टर नाहीत", "मच्छर बहुत हैं डेंगू फैल रहा है"],
    },
    "EDUCATION": {
        "en": ["municipal school building has leaking roof", "no toilets for girls in the school", "school needs more classrooms",
               "no teacher for mathematics this year", "school playground occupied by vehicles", "need a public library in the ward",
               "anganwadi centre is closed", "classrooms overcrowded with sixty students"],
        "hi": ["shala ki chhat tapakti hai", "school mein toilet nahi hai", "bacchon ke liye school door hai"],
        "dev": ["शाळेचे छत गळते", "स्कूल में शौचालय नहीं है"],
    },
    "PARKS": {
        "en": ["public garden is neglected with broken swings", "encroachment on the playground", "park gates locked all day",
               "need a jogging track and benches", "overgrown grass and no gardener", "open space being used for parking",
               "children's play area equipment rusted", "garden lights not working"],
        "hi": ["bagicha ki halat kharab hai", "baag mein jhoole tute hai", "udyan band rehta hai"],
        "dev": ["बगीचे की हालत खराब है", "उद्यानातील झोके तुटले आहेत"],
    },
    "ENVIRONMENT": {
        "en": ["illegal tree cutting on the avenue", "mangroves being destroyed by dumping", "industrial effluent discharged into the creek",
               "noise pollution from construction at night", "lake water turned green and smelly", "hill slope being cleared illegally",
               "loudspeakers beyond permitted hours", "sand mining along the creek"],
        "hi": ["ped kaat diye gaye", "nadi mein ganda paani chhoda jata hai", "raat bhar shor hota hai"],
        "dev": ["अवैध रूप से पेड़ काटे गए", "खाडीत रसायन सोडले जाते"],
    },
    "AIR_QUALITY": {
        "en": ["heavy dust from construction site", "smog and breathing problems", "smoke from waste burning every night",
               "factory chimney releasing black smoke", "dust on unpaved road needs water sprinkling", "air pollution very high this winter",
               "ready mix concrete plant causing dust", "vehicle exhaust fumes at the junction"],
        "hi": ["bahut dhool udti hai", "dhuan se saans lena mushkil hai", "hawa bahut kharab hai"],
        "dev": ["बहुत धूल उड़ती है", "धुरामुळे श्वास घेणे कठीण"],
    },
    "HOUSING": {
        "en": ["dilapidated building at risk of collapse", "slum rehabilitation project delayed for years", "illegal construction on the floor above",
               "no basic amenities in the transit camp", "building repair not done by the society", "encroachment by unauthorized structures",
               "redevelopment tenants not paid rent", "cracks in the walls of the chawl"],
        "hi": ["imarat bahut purani hai girne ka dar hai", "zopadpatti mein suvidha nahi", "ghar ki deewar mein daraar hai"],
        "dev": ["इमारत जीर्ण झाली आहे", "झोपडपट्टी में सुविधा नहीं है"],
    },
    "OTHER": {
        "en": ["query about property tax assessment", "request for birth certificate", "trade license renewal status",
               "suggestion for ward committee meeting", "complaint about staff behaviour at the ward office", "need information about a municipal scheme",
               "noise from a wedding hall", "request for a copy of the building plan"],
        "hi": ["property tax ka bill galat hai", "janm pramanpatra chahiye", "ward office mein koi jawab nahi deta"],
        "dev": ["मालमत्ता कराबाबत चौकशी", "जन्म प्रमाणपत्र चाहिए"],
    },
}

LOCATIONS = [
    "near Andheri station", "on SV Road", "in Kurla West", "near Dadar TT", "opposite Sion hospital", "on LBS Marg",
    "behind Ghatkopar market", "at Goregaon east", "near Borivali national park gate", "in Dharavi", "on Linking Road",
    "near Chembur naka", "in our society", "in the lane", "near the school", "outside our building", "near Powai lake",
    "on Western Express Highway", "near Mulund check naka", "in Govandi", "at Malad subway", "near Bandra station",
    "in Colaba market", "near Byculla zoo", "in Worli koliwada", "", "", "",
]
DURATIONS = ["", "", "for the last week", "since Monday", "for over a month", "every monsoon", "since yesterday",
             "for many days", "every night", "during peak hours", "kab se", "roz"]
PLEAS = ["", "", "Please take action.", "Kindly resolve urgently.", "Nobody from BMC has come.", "Please send someone.",
         "Complained twice already.", "jaldi karo please", "This is dangerous.", "Ward office is not responding."]
TEMPLATES = [
    "{p} {loc} {dur}. {plea}",
    "There is {p} {loc}. {plea}",
    "{loc} {p} {dur}",
    "Complaint: {p} {loc}. {plea}",
    "{p} {dur} {loc}. {plea}",
    "Dear sir, {p} {loc} {dur}. {plea}",
]


def _render(rng: random.Random, phrase: str) -> str:
    t = rng.choice(TEMPLATES)
    text = t.format(p=phrase, loc=rng.choice(LOCATIONS), dur=rng.choice(DURATIONS), plea=rng.choice(PLEAS))
    text = " ".join(text.split())
    return text[0].upper() + text[1:] if text else text


def generate_training_corpus(per_category: int = 110, multi_label_fraction: float = 0.18, seed: int = 7) -> List[Tuple[str, List[str]]]:
    rng = random.Random(seed)
    corpus: List[Tuple[str, List[str]]] = []
    for cat in CATEGORIES:
        inv = PHRASES[cat]
        for _ in range(per_category):
            r = rng.random()
            pool = inv["en"] if r < 0.62 else (inv["hi"] if r < 0.87 else inv["dev"])
            corpus.append((_render(rng, rng.choice(pool)), [cat]))
    # Multi-label combinations reflect how citizens often report co-occurring issues
    n_multi = int(len(corpus) * multi_label_fraction)
    pairs = [("FLOODING", "DRAINAGE"), ("DRAINAGE", "WASTE_MANAGEMENT"), ("HEALTHCARE", "DRAINAGE"), ("STREETLIGHT", "PUBLIC_SAFETY"),
             ("ROAD_INFRASTRUCTURE", "TRAFFIC"), ("WASTE_MANAGEMENT", "AIR_QUALITY"), ("FLOODING", "TRAFFIC"),
             ("WATER_SUPPLY", "HEALTHCARE"), ("ENVIRONMENT", "AIR_QUALITY"), ("PARKS", "PUBLIC_SAFETY"),
             ("HOUSING", "PUBLIC_SAFETY"), ("PUBLIC_TRANSPORT", "TRAFFIC"), ("ELECTRICITY", "PUBLIC_SAFETY"),
             ("ROAD_INFRASTRUCTURE", "FLOODING"), ("EDUCATION", "WATER_SUPPLY")]
    for _ in range(n_multi):
        a, b = rng.choice(pairs)
        pa = rng.choice(PHRASES[a]["en"] + PHRASES[a]["hi"])
        pb = rng.choice(PHRASES[b]["en"] + PHRASES[b]["hi"])
        text = _render(rng, f"{pa} and also {pb}")
        corpus.append((text, [a, b]))
    rng.shuffle(corpus)
    return corpus


# Hand-written evaluation sentences (never used for training). Written independently of the templates.
GOLD_SET: List[Tuple[str, List[str]]] = [
    ("Deep potholes on the main road causing accidents and vehicle damage", ["ROAD_INFRASTRUCTURE"]),
    ("Road surface completely broken and cratered after monsoon rains khadde rasta", ["ROAD_INFRASTRUCTURE"]),
    ("Road divider broken and dangerous for vehicles at night", ["ROAD_INFRASTRUCTURE", "TRAFFIC"]),
    ("Severe gridlock during peak hours at the junction", ["TRAFFIC"]),
    ("Traffic signal not working at major intersection causing chaos", ["TRAFFIC"]),
    ("Heavy commercial trucks parked on the bypass causing long queues", ["TRAFFIC"]),
    ("No buses for 45 minutes during morning rush hours", ["PUBLIC_TRANSPORT"]),
    ("Metro feeder bus service needed from our colony to the station", ["PUBLIC_TRANSPORT"]),
    ("Garbage pile accumulating on street corner not cleared for five days kachra durgandhi", ["WASTE_MANAGEMENT"]),
    ("Door to door garbage collection vehicle has not visited this week", ["WASTE_MANAGEMENT"]),
    ("No municipal tap water supply for last three days paani nahi", ["WATER_SUPPLY"]),
    ("Contaminated foul-smelling drinking water coming from pipeline", ["WATER_SUPPLY"]),
    ("Low water pressure on top floors, pipeline replacement required", ["WATER_SUPPLY"]),
    ("Underground sewer blocked with sewage overflowing on road naala blocked", ["DRAINAGE"]),
    ("Open storm water drain without safety slabs, naali cover missing", ["DRAINAGE", "PUBLIC_SAFETY"]),
    ("Severe waterlogging and knee deep water during monsoon rain", ["FLOODING"]),
    ("Low-lying residential area submerged in flood water after heavy rains", ["FLOODING"]),
    ("Underpass completely waterlogged and closed for vehicles", ["FLOODING", "TRAFFIC"]),
    ("Streetlights not working on entire avenue, complete darkness at night", ["STREETLIGHT"]),
    ("Flickering streetlight pole creating dark spots for pedestrians", ["STREETLIGHT"]),
    ("Exposed high voltage electrical wire hanging dangerously low on footpath", ["ELECTRICITY", "PUBLIC_SAFETY"]),
    ("Frequent power cuts and voltage fluctuations in the area", ["ELECTRICITY"]),
    ("Transformer sparking near the market, danger of fire", ["ELECTRICITY"]),
    ("Aggressive pack of stray dogs chasing two-wheelers and children", ["PUBLIC_SAFETY"]),
    ("Lack of police patrolling leading to unsafe streets at night", ["PUBLIC_SAFETY"]),
    ("Primary health centre lacks doctors and basic medicines", ["HEALTHCARE"]),
    ("High mosquito breeding creating dengue and malaria risk", ["HEALTHCARE"]),
    ("Municipal primary school building has broken windows and leaking ceiling", ["EDUCATION"]),
    ("Lack of clean toilets in the government high school", ["EDUCATION"]),
    ("Children's park in neglected condition with broken swings and overgrown grass", ["PARKS"]),
    ("Encroachment on municipal park land and lack of maintenance", ["PARKS"]),
    ("Illegal cutting of mature trees on the avenue without permission", ["ENVIRONMENT"]),
    ("Industrial effluents discharged into the local lake causing fish deaths", ["ENVIRONMENT"]),
    ("Severe PM2.5 dust pollution from an unmonitored construction site", ["AIR_QUALITY"]),
    ("Heavy smog and vehicle emissions causing breathing difficulties", ["AIR_QUALITY"]),
    ("Dilapidated old building in dangerous condition risking collapse", ["HOUSING"]),
    ("Slum rehabilitation project with basic amenities missing", ["HOUSING"]),
    ("Inquiry regarding property tax assessment and trade license renewal", ["OTHER"]),
    ("सड़क पर बड़े गड्ढे हैं और रोज़ दुर्घटना होती है", ["ROAD_INFRASTRUCTURE"]),
    ("आमच्या भागात तीन दिवसांपासून पाणी नाही", ["WATER_SUPPLY"]),
    ("कचरा उचलला जात नाही, खूप दुर्गंधी येते", ["WASTE_MANAGEMENT"]),
    ("बारिश के बाद पूरी गली में पानी भर गया है", ["FLOODING"]),
    ("Bhai yahan roz raat ko street light band rehti hai, bahut andhera", ["STREETLIGHT"]),
    ("Gatar ka paani ghar ke andar aa raha hai please jaldi saaf karo", ["DRAINAGE"]),
    ("Bus stop pe koi shed nahi hai aur bus bhi time pe nahi aati", ["PUBLIC_TRANSPORT"]),
    ("Hospital mein bed nahi mila, ambulance bhi late aayi", ["HEALTHCARE"]),
]
