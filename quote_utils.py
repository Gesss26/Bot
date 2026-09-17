# ============================================================
# quote_utils.py
# Modulo condiviso per parsing quote Marathonbet (PDF)
# Versione 3: multi-PDF + merge quote + traduzioni complete
# ============================================================

import re
import time
import logging
import unicodedata
from typing import List, Dict, Optional, Tuple
from io import BytesIO
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURAZIONE
# ============================================================

QUOTE_PDF_URLS = [
    "https://raw.githubusercontent.com/Gesss26/GesssAI-Pro---Auto/master/quote/marathonbet.pdf",
    "https://raw.githubusercontent.com/Gesss26/GesssAI-Pro---Auto/master/quote/marathonbet-2.pdf",
]
SOGLIA_MATCH_QUOTE = 0.62

# ============================================================
# DIZIONARIO TRADUZIONI SQUADRE
# ============================================================

TRADUZIONI_SQUADRE = {
    # ============ SPAGNA ============
    'siviglia': 'sevilla', 'barcellona': 'barcelona', 'real madrid': 'realmadrid',
    'atletico madrid': 'atleticomadrid', 'athletic bilbao': 'athleticbilbao',
    'real betis': 'realbetis', 'real sociedad': 'realsociedad',
    'valencia': 'valencia', 'villarreal': 'villarreal', 'getafe': 'getafe',
    'osasuna': 'osasuna', 'elche': 'elche', 'levante': 'levante',
    'espanyol': 'espanyol', 'rayo vallecano': 'rayovallecano',
    'alaves': 'alaves', 'malaga': 'malaga', 'cf malaga': 'malaga',
    'racing santander': 'racingsantander', 'deportivo la coruna': 'deportivolacoruna',
    'girona': 'girona', 'las palmas': 'laspalmas', 'almeria': 'almeria',
    'cadice': 'cadiz', 'cadiz': 'cadiz', 'maiorca': 'mallorca', 'mallorca': 'mallorca',
    'celta vigo': 'celtavigo', 'real valladolid': 'realvalladolid',
    'granada': 'granada', 'alaves': 'alaves', 'eibar': 'eibar',
    'huesca': 'huesca', 'lugo': 'lugo', 'mirandes': 'mirandes',
    'oviedo': 'oviedo', 'ponferradina': 'ponferradina', 'sporting gijon': 'sportinggijon',
    'tenerife': 'tenerife', 'zaragoza': 'zaragoza', 'real oviedo': 'realoviedo',
    'cartagena': 'cartagena', 'albacete': 'albacete', 'andorra': 'andorra',
    'burgos': 'burgos', 'ibiza': 'ibiza', 'leganes': 'leganes',
    'pontevedra': 'pontevedra', 'sabadell': 'sabadell', 'castellon': 'castellon',

    # ============ ITALIA ============
    'inter': 'inter', 'inter milano': 'intermilano', 'milan': 'milan',
    'ac milan': 'milan', 'juventus': 'juventus', 'napoli': 'napoli',
    'roma': 'roma', 'lazio': 'lazio', 'atalanta': 'atalanta',
    'fiorentina': 'fiorentina', 'torino': 'torino', 'bologna': 'bologna',
    'genoa': 'genoa', 'cagliari': 'cagliari', 'cagliari calcio': 'cagliari',
    'udinese': 'udinese', 'venezia': 'venezia', 'como': 'como',
    'verona': 'verona', 'hellas verona': 'verona', 'parma': 'parma',
    'parma calcio': 'parma', 'lecce': 'lecce', 'monza': 'monza',
    'ac monza': 'monza', 'sassuolo': 'sassuolo', 'sassuolo calcio': 'sassuolo',
    'frosinone': 'frosinone', 'frosinone calcio': 'frosinone', 'empoli': 'empoli',
    'salernitana': 'salernitana', 'us salernitana': 'salernitana',
    'sampdoria': 'sampdoria', 'spezia': 'spezia', 'spezia calcio': 'spezia',
    'cremonese': 'cremonese', 'palermo': 'palermo', 'palermo fc': 'palermo',
    'bari': 'bari', 'ssc bari': 'bari', 'catania': 'catania',
    'catania fc': 'catania', 'crotone': 'crotone',
    'inter u23': 'interu23', 'juventus u23': 'juventusu23',
    'atalanta u23': 'atalantau23', 'milan u23': 'milanu23',
    # Serie B
    'ascoli': 'ascoli', 'benevento': 'benevento', 'brescia': 'brescia',
    'cittadella': 'cittadella', 'cosenza': 'cosenza', 'feralpisalo': 'feralpisalo',
    'feralpi salo': 'feralpisalo', 'juve stabia': 'juvestabia',
    'modena': 'modena', 'napoli primavera': 'napoliprimavera',
    'palermo': 'palermo', 'perugia': 'perugia', 'pisa': 'pisa',
    'pordenone': 'pordenone', 'reggina': 'reggina', 'renate': 'renate',
    'sudtirol': 'sudtirol', 'ternana': 'ternana', 'trento': 'trento',
    'vicenza': 'vicenza', 'virtus entella': 'virtusentella',
    'alessandria': 'alessandria', 'avellino': 'avellino', 'catanzaro': 'catanzaro',
    'foggia': 'foggia', 'latina': 'latina', 'monopoli': 'monopoli',
    'picerno': 'picerno', 'potenza': 'potenza', 'taranto': 'taranto',
    'turris': 'turris', 'viterbese': 'viterbese', 'messina': 'messina',
    'giugliano': 'giugliano', 'monterosi': 'monterosi', 'recina': 'recina',

    # ============ INGHILTERRA ============
    'manchester united': 'manchesterunited', 'manchester city': 'manchestercity',
    'liverpool': 'liverpool', 'chelsea': 'chelsea', 'arsenal': 'arsenal',
    'tottenham': 'tottenham', 'tottenham hotspur': 'tottenham',
    'newcastle': 'newcastle', 'newcastle united': 'newcastle',
    'aston villa': 'astonvilla', 'everton': 'everton', 'west ham': 'westham',
    'west ham united': 'westham', 'leicester': 'leicester', 'leicester city': 'leicester',
    'leeds': 'leeds', 'leeds united': 'leeds', 'wolves': 'wolves',
    'wolverhampton': 'wolves', 'brighton': 'brighton', 'crystal palace': 'crystalpalace',
    'fulham': 'fulham', 'brentford': 'brentford', 'nottingham forest': 'nottinghamforest',
    'bournemouth': 'bournemouth', 'southampton': 'southampton', 'ipswich': 'ipswich',
    'sheffield united': 'sheffieldunited', 'sheffield wednesday': 'sheffieldwednesday',
    'burnley': 'burnley', 'watford': 'watford', 'norwich': 'norwich',
    'norwich city': 'norwich', 'west bromwich': 'westbromwich', 'west brom': 'westbromwich',
    'middlesbrough': 'middlesbrough', 'stoke': 'stoke', 'stoke city': 'stoke',
    'swansea': 'swansea', 'cardiff': 'cardiff', 'cardiff city': 'cardiff',
    'hull': 'hull', 'hull city': 'hull', 'coventry': 'coventry', 'coventry city': 'coventry',
    'bristol city': 'bristolcity', 'preston': 'preston', 'millwall': 'millwall',
    'blackburn': 'blackburn', 'reading': 'reading', 'sunderland': 'sunderland',
    'portsmouth': 'portsmouth', 'derby': 'derby', 'derby county': 'derby',
    'qpr': 'qpr', 'queens park rangers': 'qpr', 'luton': 'luton',
    'rotherham': 'rotherham', 'wycombe': 'wycombe', 'milton keynes': 'miltonkeynes',
    'cambridge': 'cambridge', 'oxford': 'oxford', 'oxford united': 'oxford',
    'charlton': 'charlton', 'bolton': 'bolton', 'wigan': 'wigan',
    'barnsley': 'barnsley', 'shrewsbury': 'shrewsbury', 'fleetwood': 'fleetwood',
    'accrington': 'accrington', 'burton': 'burton', 'doncaster': 'doncaster',
    'gillingham': 'gillingham', 'ipswich town': 'ipswich', 'lincoln': 'lincoln',
    'mk dons': 'mkdons', 'morecambe': 'morecambe', 'plymouth': 'plymouth',
    'salford': 'salford', 'scunthorpe': 'scunthorpe', 'stevenage': 'stevenage',
    'sutton': 'sutton', 'tranmere': 'tranmere', 'walsall': 'walsall',
    'yeovil': 'yeovil', 'crewe': 'crewe', 'grismby': 'grimsby', 'grimsby': 'grimsby',
    'newport': 'newport', 'northampton': 'northampton', 'oldham': 'oldham',
    'port vale': 'portvale', 'rochdale': 'rochdale', 'swindon': 'swindon',

    # ============ GERMANIA ============
    'bayern monaco': 'bayernmonaco', 'bayern munich': 'bayernmonaco',
    'borussia dortmund': 'borussiadortmund', 'dortmund': 'borussiadortmund',
    'rb lipsia': 'rblipsia', 'leipzig': 'rblipsia',
    'bayer leverkusen': 'bayerleverkusen', 'leverkusen': 'bayerleverkusen',
    'eintracht francoforte': 'eintrachtfrancoforte', 'francoforte': 'eintrachtfrancoforte',
    'borussia monchengladbach': 'borussiamonchengladbach', 'gladbach': 'borussiamonchengladbach',
    'wolfsburg': 'wolfsburg', 'union berlino': 'unionberlino', 'union berlin': 'unionberlino',
    'friburgo': 'friburgo', 'freiburg': 'friburgo',
    'stoccarda': 'stoccarda', 'stuttgart': 'stoccarda',
    'mainz': 'mainz', 'augsburg': 'augsburg', 'werder brema': 'werderbrema',
    'werder bremen': 'werderbrema', 'hoffenheim': 'hoffenheim', 'bochum': 'bochum',
    'colonia': 'colonia', 'koln': 'colonia', 'cologne': 'colonia',
    'hertha berlino': 'herthaberlino', 'hertha berlin': 'herthaberlino',
    'schalke 04': 'schalke04', 'schalke': 'schalke04',
    'amburgo': 'amburgo', 'hamburger sv': 'amburgo', 'hamburg': 'amburgo',
    'hannover': 'hannover', 'karlsruhe': 'karlsruhe', 'karlsruher': 'karlsruhe',
    'dusseldorf': 'dusseldorf', 'fortuna dusseldorf': 'fortunadusseldorf',
    'nurnberg': 'nurnberg', 'norimberga': 'nurnberg',
    'paderborn': 'paderborn', 'sandhausen': 'sandhausen', 'darmstadt': 'darmstadt',
    'heidenheim': 'heidenheim', 'regensburg': 'regensburg', 'magdeburg': 'magdeburg',
    'rostock': 'rostock', 'hansa rostock': 'hansarostock', 'braunschweig': 'braunschweig',
    'kiel': 'kiel', 'holstein kiel': 'holsteinkiel', 'bielefeld': 'bielefeld',
    'arminia bielefeld': 'arminiabielefeld', 'ingolstadt': 'ingolstadt',
    'wurzburg': 'wurzburg', 'wuerzburg': 'wurzburg',

    # ============ FRANCIA ============
    'psg': 'psg', 'paris saint germain': 'psg', 'paris sg': 'psg',
    'marsiglia': 'marsiglia', 'marseille': 'marsiglia',
    'lione': 'lione', 'lyon': 'lione', 'olympique lyon': 'lione',
    'monaco': 'monaco', 'as monaco': 'monaco',
    'lille': 'lille', 'losc lille': 'lille',
    'rennes': 'rennes', 'stade rennais': 'rennes',
    'nizza': 'nizza', 'nice': 'nizza', 'ogc nice': 'nizza',
    'lens': 'lens', 'rc lens': 'lens',
    'reims': 'reims', 'stade reims': 'reims',
    'montpellier': 'montpellier', 'strasburgo': 'strasburgo', 'strasbourg': 'strasburgo',
    'nantes': 'nantes', 'toulouse': 'toulouse', 'bordeaux': 'bordeaux',
    'saint etienne': 'saintetienne', 'asse': 'saintetienne',
    'angers': 'angers', 'brest': 'brest', 'lorient': 'lorient',
    'troyes': 'troyes', 'auxerre': 'auxerre', 'ajaccio': 'ajaccio',
    'clermont': 'clermont', 'clermont foot': 'clermont',
    'metz': 'metz', 'dijon': 'dijon', 'caen': 'caen',
    'le havre': 'lehavre', 'amiens': 'amiens', 'grenoble': 'grenoble',
    'guingamp': 'guingamp', 'nancy': 'nancy', 'niort': 'niort',
    'paris fc': 'parisfc', 'pau': 'pau', 'quevilly': 'quevilly',
    'rodez': 'rodez', 'sochaux': 'sochaux', 'valenciennes': 'valenciennes',

    # ============ PORTOGALLO ============
    'benfica': 'benfica', 'porto': 'porto', 'fc porto': 'porto',
    'sporting lisbona': 'sportinglisbona', 'sporting lisbon': 'sportinglisbona',
    'sporting cp': 'sportinglisbona', 'braga': 'braga', 'sc braga': 'braga',
    'vitoria guimaraes': 'vitoriaguimaraes', 'guimaraes': 'vitoriaguimaraes',
    'boavista': 'boavista', 'famalicao': 'famalicao', 'gil vicente': 'gilvicente',
    'estoril': 'estoril', 'portimonense': 'portimonense', 'maritimo': 'maritimo',
    'rio ave': 'rioave', 'santa clara': 'santaclara', 'vizela': 'vizela',
    'arouca': 'arouca', 'casa pia': 'casapia', 'chaves': 'chaves',
    'moreirense': 'moreirense', 'paços ferreira': 'pacosferreira',
    'pacos ferreira': 'pacosferreira', 'academico viseu': 'academicoviseu',
    'leixoes': 'leixoes', 'nacional': 'nacional', 'penafiel': 'penafiel',
    'tondela': 'tondela', 'vilafranquense': 'vilafranquense',

    # ============ OLANDA ============
    'ajax': 'ajax', 'psv': 'psv', 'psv eindhoven': 'psv', 'feyenoord': 'feyenoord',
    'az alkmaar': 'azalkmaar', 'az': 'azalkmaar', 'twente': 'twente',
    'utrecht': 'utrecht', 'vitesse': 'vitesse', 'heerenveen': 'heerenveen',
    'groningen': 'groningen', 'sparta rotterdam': 'spartarotterdam',
    'nijmegen': 'nijmegen', 'nec': 'nec', 'go ahead eagles': 'goaheadeagles',
    'rkc waalwijk': 'rkcwaalwijk', 'waalwijk': 'rkcwaalwijk',
    'fortuna sittard': 'fortunasittard', 'sittard': 'fortunasittard',
    'cambuur': 'cambuur', 'excelsior': 'excelsior', 'volendam': 'volendam',
    'emmen': 'emmen', 'almere city': 'almerecity', 'almere': 'almerecity',
    'hercules': 'hercules', 'den bosch': 'denbosch', 'eindhoven': 'eindhoven',
    'de graafschap': 'degraafschap', 'graafschap': 'degraafschap',
    'roda jc': 'rodajc', 'roda': 'rodajc', 'vvv venlo': 'vvvvenlo',
    'venlo': 'vvvvenlo', 'dordrecht': 'dordrecht', 'helmond sport': 'helmondsport',
    'jong ajax': 'jongajax', 'jong psv': 'jongpsv', 'jong az': 'jongaz',
    'jong utrecht': 'jongutrecht', 'jong twente': 'jongtwente',

    # ============ BELGIO ============
    'anderlecht': 'anderlecht', 'club bruges': 'clubbruges', 'bruges': 'clubbruges',
    'standard liegi': 'standardliegi', 'standard liege': 'standardliegi',
    'genk': 'genk', 'krc genk': 'genk', 'gent': 'gent', 'kaa gent': 'gent',
    'royal antwerp': 'royalantwerp', 'antwerp': 'royalantwerp',
    'charleroi': 'charleroi', 'sporting charleroi': 'charleroi',
    'cercle bruges': 'cerclebruges', 'kv mechelen': 'kvmechelen', 'mechelen': 'kvmechelen',
    'kv kortrijk': 'kvkortrijk', 'kortrijk': 'kvkortrijk',
    'oh leuven': 'ohleuven', 'leuven': 'ohleuven', 'oud heverlee': 'ohleuven',
    'sint truiden': 'sinttruiden', 'stvv': 'sinttruiden',
    'westerlo': 'westerlo', 'kvc westerlo': 'westerlo',
    'zulte waregem': 'zultewaregem', 'waregem': 'zultewaregem',
    'eupen': 'eupen', 'kasp eupen': 'eupen', 'beerschot': 'beerschot',
    'union saint gilloise': 'unionsaintgilloise', 'union sg': 'unionsaintgilloise',
    'rwdm': 'rwdm', 'molenbeek': 'rwdm',

    # ============ SCOZIA ============
    'celtic': 'celtic', 'rangers': 'rangers', 'aberdeen': 'aberdeen',
    'hearts': 'hearts', 'heart of midlothian': 'hearts',
    'hibernian': 'hibernian', 'hibernians': 'hibernian',
    'dundee': 'dundee', 'dundee united': 'dundeeunited',
    'motherwell': 'motherwell', 'kilmarnock': 'kilmarnock',
    'st mirren': 'stmirren', 'ross county': 'rosscounty',
    'livingston': 'livingston', 'st johnstone': 'stjohnstone',
    'dunfermline': 'dunfermline', 'falkirk': 'falkirk',
    'inverness': 'inverness', 'partick thistle': 'partickthistle',
    'queen of south': 'queenofsouth', 'raith rovers': 'raithrovers',
    'ayr united': 'ayrunited', 'greenock morton': 'greenockmorton',
    'arbroath': 'arbroath', 'alloa': 'alloa', 'cove rangers': 'coverangers',

    # ============ TURCHIA ============
    'galatasaray': 'galatasaray', 'fenerbahce': 'fenerbahce',
    'besiktas': 'besiktas', 'trabzonspor': 'trabzonspor',
    'basaksehir': 'basaksehir', 'istanbul basaksehir': 'basaksehir',
    'adana demirspor': 'adanademirspor', 'adana': 'adanademirspor',
    'konyaspor': 'konyaspor', 'konya': 'konyaspor',
    'kayserispor': 'kayserispor', 'kayseri': 'kayserispor',
    'alanyaspor': 'alanyaspor', 'alanya': 'alanyaspor',
    'antalyaspor': 'antalyaspor', 'antalya': 'antalyaspor',
    'sivasspor': 'sivasspor', 'sivas': 'sivasspor',
    'gaziantep': 'gaziantep', 'gaziantep fk': 'gaziantep',
    'kasimpasa': 'kasimpasa', 'rizespor': 'rizespor', 'rizes': 'rizespor',
    'hatayspor': 'hatayspor', 'hatay': 'hatayspor',
    'istanbulspor': 'istanbulspor', 'umraniye': 'umraniye',
    'pendikspor': 'pendikspor', 'samsunspor': 'samsunspor',
    'bodrum': 'bodrum', 'bodrumspor': 'bodrumspor',
}

# ============================================================
# NORMALIZZAZIONE NOMI
# ============================================================

_SUFFISSI_SOCIETARI = re.compile(
    r'\b(fc|ac|ssc|as|us|ss|asd|ssd|calcio|sportiva|società|societa|'
    r'1919|1929|1937|1908|1911|u23|u21|u19|cf|sk|sv|sc|vv|kvc|fk|bk|if|ff|cd|sd|ud|rc|rcd|afc|cfc)\b'
)

def normalizza_nome(nome: str) -> str:
    if not nome:
        return ''
    n = str(nome).lower()
    n = unicodedata.normalize('NFD', n)
    n = ''.join(c for c in n if unicodedata.category(c) != 'Mn')
    n = _SUFFISSI_SOCIETARI.sub('', n)
    n = re.sub(r'[^a-z0-9]', '', n)
    n = n.strip()
    if n in TRADUZIONI_SQUADRE:
        n = TRADUZIONI_SQUADRE[n]
    return n

def similarita(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    bigrams_a = set(a[i:i+2] for i in range(len(a)-1))
    bigrams_b = set(b[i:i+2] for i in range(len(b)-1))
    if not bigrams_a or not bigrams_b:
        return 0.0
    intersection = len(bigrams_a & bigrams_b)
    return (2 * intersection) / (len(bigrams_a) + len(bigrams_b))

# ============================================================
# PARSING PDF (multi-riga)
# ============================================================

GIORNI = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
MESI = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
MESI_NUM = {'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4, 'maggio': 5, 'giugno': 6,
            'luglio': 7, 'agosto': 8, 'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12}

RIGHE_IGNORE = {
    'Calcio', '1X2', 'DOPPIA CHANCE', 'GG/NG',
    'U/O 1,5', 'U/O 2,5', 'U/O 3,5', 'U/O 4,5',
    'MG 1-4', 'MG 2-5', 'Codice alias',
    '1', 'x', '2', '1x', '12', 'x2', 'g', 'n',
    'u1', 'o1', 'u', 'o', 'u3', 'o3', 'u4', 'o4', '1-4', '2-5',
    'Alias', 'Ora', 'Evento', '1X', '12', 'X2', 'GOAL', 'NOGOAL',
    'UNDER', 'OVER', 'SI', 'NO', 'X',
}

def estrai_righe_da_pdf(contenuto_pdf: bytes) -> List[str]:
    try:
        import pdfplumber
    except ImportError:
        logger.error("❌ pdfplumber non installato")
        return []

    righe = []
    try:
        with pdfplumber.open(BytesIO(contenuto_pdf)) as pdf:
            logger.info(f"📄 PDF con {len(pdf.pages)} pagine")
            for i, page in enumerate(pdf.pages, 1):
                testo = page.extract_text()
                if testo:
                    for riga in testo.split('\n'):
                        riga = riga.strip()
                        if riga:
                            righe.append(riga)
    except Exception as e:
        logger.error(f"❌ Errore estrazione PDF: {e}")
        return []

    return righe


def is_intestazione_campionato(testo: str) -> Optional[str]:
    pattern = r'^([A-Z][a-zà-ù]+(?:\s+di\s+[A-Z][a-zà-ù]+)?)\s+-\s+(.+)$'
    match = re.match(pattern, testo)
    if not match:
        return None
    if any(g in testo for g in GIORNI):
        return None
    return testo.strip()


def is_riga_data(testo: str) -> Optional[str]:
    pattern = r'^(' + '|'.join(GIORNI) + r')\s+(\d{1,2})\s+(' + '|'.join(MESI) + r')'
    match = re.match(pattern, testo, re.IGNORECASE)
    if not match:
        return None
    giorno = match.group(2).zfill(2)
    mese = MESI_NUM.get(match.group(3).lower(), 1)
    mese_str = str(mese).zfill(2)
    oggi = datetime.now()
    anno = oggi.year
    mese_corrente = oggi.month
    if mese_corrente == 1 and mese == 12:
        anno = oggi.year - 1
    elif mese < mese_corrente - 1:
        anno = oggi.year + 1
    return f"{anno}-{mese_str}-{giorno}"


def is_quota(testo: str) -> Optional[float]:
    if re.match(r'^\d+\.\d{1,2}$', testo):
        try:
            return float(testo)
        except:
            return None
    return None


def parse_marathonbet_pdf(righe: List[str]) -> List[Dict]:
    partite = []
    campionato_corrente = None
    data_corrente = None
    data_iso_corrente = None

    i = 0
    n = len(righe)

    while i < n:
        riga = righe[i]

        camp = is_intestazione_campionato(riga)
        if camp:
            campionato_corrente = camp
            i += 1
            continue

        data_iso = is_riga_data(riga)
        if data_iso:
            data_corrente = riga
            data_iso_corrente = data_iso
            i += 1
            continue

        if riga in RIGHE_IGNORE:
            i += 1
            continue

        if re.match(r'^\d{3,6}$', riga):
            alias = riga
            if i + 2 >= n:
                i += 1
                continue

            ora_candidate = righe[i + 1]
            evento_candidate = righe[i + 2]

            if not re.match(r'^\d{1,2}:\d{2}$', ora_candidate):
                i += 1
                continue

            if ' - ' not in evento_candidate:
                i += 1
                continue

            sep_idx = evento_candidate.rfind(' - ')
            casa = evento_candidate[:sep_idx].strip()
            ospiti = evento_candidate[sep_idx + 3:].strip()

            if not casa or not ospiti:
                i += 1
                continue

            quote_list = []
            j = i + 3
            while j < n and len(quote_list) < 20:
                q = is_quota(righe[j])
                if q is not None:
                    quote_list.append(q)
                    j += 1
                elif righe[j] == '-':
                    quote_list.append(None)
                    j += 1
                else:
                    break

            if len(quote_list) >= 3:
                def q(idx):
                    return quote_list[idx] if len(quote_list) > idx else None

                quote_mappate = {
                    '1': q(0), 'X': q(1), '2': q(2),
                    '1X': q(3), '12': q(4), 'X2': q(5),
                    'GG': q(6), 'NG': q(7),
                    'U1.5': q(8), 'O1.5': q(9),
                    'U2.5': q(10), 'O2.5': q(11),
                    'U3.5': q(12), 'O3.5': q(13),
                    'U4.5': q(14), 'O4.5': q(15),
                    'MG14_SI': q(16), 'MG14_NO': q(17),
                    'MG25_SI': q(18), 'MG25_NO': q(19),
                }

                partite.append({
                    'alias': alias,
                    'ora': ora_candidate,
                    'casa': casa,
                    'ospiti': ospiti,
                    'quote': quote_mappate,
                    'campionato': campionato_corrente,
                    'data': data_corrente,
                    'dataISO': data_iso_corrente,
                    'fonte': 'Marathonbet',
                })

                i = j
                continue

        i += 1

    return partite

# ============================================================
# CARICAMENTO QUOTE DA GITHUB (multi-PDF con merge)
# ============================================================

def _download_and_parse_pdf(url: str) -> List[Dict]:
    """Scarica e parsa un singolo PDF di quote"""
    try:
        logger.info(f"📂 Download PDF da: {url}")
        t0 = time.time()
        response = requests.get(url, timeout=60)
        elapsed = time.time() - t0
        logger.info(f"📂 Download OK in {elapsed:.1f}s (status={response.status_code}, {len(response.content)} bytes)")

        if response.status_code != 200:
            logger.error(f"❌ HTTP {response.status_code} per {url}")
            return []

        # Verifica che sia un PDF
        content_type = response.headers.get('content-type', '')
        is_pdf_header = response.content.startswith(b'%PDF')
        if 'pdf' not in content_type.lower() and not is_pdf_header:
            logger.error(f"❌ Il file non è un PDF valido (content-type={content_type})")
            logger.error(f"   Prime 200 chars: {response.text[:200]}")
            return []

        logger.info(f"📂 Estrazione righe dal PDF...")
        t0 = time.time()
        righe = estrai_righe_da_pdf(response.content)
        logger.info(f"📂 Estratte {len(righe)} righe in {time.time()-t0:.1f}s")

        if not righe:
            logger.error(f"❌ Nessuna riga estratta da {url}")
            return []

        logger.info(f"📂 Parsing partite...")
        t0 = time.time()
        partite = parse_marathonbet_pdf(righe)
        logger.info(f"📂 Parsate {len(partite)} partite in {time.time()-t0:.1f}s")

        return partite
    except Exception as e:
        logger.error(f"❌ Errore caricamento {url}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def _chiave_partita(p: Dict) -> Tuple[str, str, str, str]:
    """Chiave univoca per una partita (per deduplicazione)"""
    return (
        normalizza_nome(p.get('casa', '')),
        normalizza_nome(p.get('ospiti', '')),
        p.get('dataISO', '') or '',
        p.get('ora', '') or '',
    )


def load_quote_from_github() -> List[Dict]:
    """
    Scarica e parsa TUTTI i PDF di quote configurati in QUOTE_PDF_URLS.
    Unisce i risultati: se una partita appare in più PDF, unisce le quote
    (preferendo valori non-None).
    """
    tutte_partite: List[Dict] = []
    indice: Dict[Tuple[str, str, str, str], Dict] = {}

    for url in QUOTE_PDF_URLS:
        partite = _download_and_parse_pdf(url)
        logger.info(f"📂 Da {url.split('/')[-1]}: {len(partite)} partite")

        for p in partite:
            chiave = _chiave_partita(p)
            if chiave in indice:
                # Partita già presente: unisci le quote (preferisci non-None)
                esistente = indice[chiave]
                for k, v in p['quote'].items():
                    if esistente['quote'].get(k) is None and v is not None:
                        esistente['quote'][k] = v
                # Aggiorna campionato se mancante
                if not esistente.get('campionato') and p.get('campionato'):
                    esistente['campionato'] = p['campionato']
            else:
                indice[chiave] = p
                tutte_partite.append(p)

    logger.info(f"✅ Totale partite quote (unite da {len(QUOTE_PDF_URLS)} PDF): {len(tutte_partite)}")
    return tutte_partite

# ============================================================
# TROVA QUOTA PER GIOCATA
# ============================================================

_MAPPING_QUOTE = {
    ('fisse', '1'): '1', ('fisse', 'X'): 'X', ('fisse', '2'): '2',
    ('dc', '1X'): '1X', ('dc', '12'): '12', ('dc', 'X2'): 'X2',
    ('gg_ng', 'GG'): 'GG', ('gg_ng', 'NG'): 'NG',
    ('over_15', 'Over 1.5'): 'O1.5',
    ('over_25', 'Over 2.5'): 'O2.5',
    ('under', 'Under 1.5'): 'U1.5',
    ('under', 'Under 2.5'): 'U2.5',
    ('under', 'Under 3.5'): 'U3.5',
    ('under', 'Under 4.5'): 'U4.5',
    ('multigol', '1-4'): 'MG14_SI',
    ('multigol', '2-5'): 'MG25_SI',
}

def _trova_entry_quota(match, partite_quote: List[Dict]) -> Optional[Dict]:
    if not partite_quote:
        return None
    casa_norm = normalizza_nome(match.casa)
    ospiti_norm = normalizza_nome(match.ospiti)
    best_match = None
    best_score = 0
    for p in partite_quote:
        score_casa = similarita(casa_norm, normalizza_nome(p['casa']))
        score_ospiti = similarita(ospiti_norm, normalizza_nome(p['ospiti']))
        score = (score_casa + score_ospiti) / 2
        if score > best_score and score > SOGLIA_MATCH_QUOTE:
            best_score = score
            best_match = p
    return best_match

def trova_quota_per_giocata(match, family_id: str, giocata: str,
                             partite_quote: List[Dict]) -> Optional[float]:
    entry = _trova_entry_quota(match, partite_quote)
    if not entry:
        return None
    quote = entry['quote']
    key = (family_id, giocata)
    if key in _MAPPING_QUOTE:
        return quote.get(_MAPPING_QUOTE[key])
    # DC+Over
    if family_id == 'dc_over' and '+' in giocata:
        parts = giocata.split('+')
        if len(parts) == 2:
            dc_q = quote.get(parts[0])
            over_q = quote.get(parts[1].replace('O', 'O'))
            if dc_q and over_q:
                return round(dc_q * over_q, 2)
    # DC+Under
    if family_id == 'dc_under' and '+' in giocata:
        parts = giocata.split('+')
        if len(parts) == 2:
            dc_q = quote.get(parts[0])
            under_q = quote.get(parts[1])
            if dc_q and under_q:
                return round(dc_q * under_q, 2)
    return None

def get_quota_or_fallback(match, family_id: str, giocata: str,
                          partite_quote: List[Dict]) -> float:
    quota = trova_quota_per_giocata(match, family_id, giocata, partite_quote)
    if quota is None or quota <= 1:
        return 1.0
    return quota

# ============================================================
# VALUE BET
# ============================================================

def calcola_value_bet(pct_tua: float, quota_book: float) -> Dict:
    if not quota_book or quota_book <= 1 or pct_tua <= 0:
        return {'edge': 0, 'quota_fair': 0, 'kelly': 0,
                'is_value': False, 'classificazione': '⚪', 'livello': 'no-value'}
    quota_fair = 100 / pct_tua
    edge = ((quota_book * pct_tua / 100) - 1) * 100
    b = quota_book - 1
    p = pct_tua / 100
    q = 1 - p
    kelly = max(0, (b * p - q) / b) if b > 0 else 0
    if edge > 20:
        classificazione = '💎 VALUE ECCELLENTE'; livello = 'excellent'
    elif edge > 10:
        classificazione = '✅ VALUE BUONO'; livello = 'good'
    elif edge > 5:
        classificazione = '🟡 VALUE MARGINALE'; livello = 'marginal'
    elif edge > 0:
        classificazione = '⚪ Quota fair'; livello = 'fair'
    else:
        classificazione = '🔴 No value'; livello = 'no-value'
    return {'edge': round(edge, 1), 'quota_fair': round(quota_fair, 2),
            'kelly': round(kelly * 100, 2), 'is_value': edge > 5,
            'classificazione': classificazione, 'livello': livello}

def calcola_quota_colonna(giocate: List[Dict]) -> Dict:
    if not giocate:
        return {'quota_totale': 0, 'prob_combinata': 0, 'edge': 0,
                'kelly': 0, 'classificazione': '⚪ N/D', 'livello': 'no-value',
                'n_partite': 0, 'n_quote_mancanti': 0}
    quota_totale = 1.0
    prob_combinata_dec = 1.0
    n_mancanti = 0
    for g in giocate:
        quota = g.get('quota')
        if quota is None or quota <= 1:
            quota = 1.0
            n_mancanti += 1
        quota_totale *= quota
        prob_combinata_dec *= (g.get('pct', 0) / 100)
    prob_combinata = prob_combinata_dec * 100
    edge = ((quota_totale * prob_combinata / 100) - 1) * 100 if quota_totale > 1 and prob_combinata > 0 else 0
    b = quota_totale - 1
    p = prob_combinata_dec
    q = 1 - p
    kelly = max(0, (b * p - q) / b) if b > 0 else 0
    if edge > 20:
        classificazione = '💎 VALUE ECCELLENTE'; livello = 'excellent'
    elif edge > 10:
        classificazione = '✅ VALUE BUONO'; livello = 'good'
    elif edge > 5:
        classificazione = '🟡 VALUE MARGINALE'; livello = 'marginal'
    elif edge > 0:
        classificazione = '⚪ Quota fair'; livello = 'fair'
    else:
        classificazione = '🔴 No value'; livello = 'no-value'
    return {'quota_totale': round(quota_totale, 2), 'prob_combinata': round(prob_combinata, 2),
            'edge': round(edge, 1), 'kelly': round(kelly * 100, 2),
            'classificazione': classificazione, 'livello': livello,
            'n_partite': len(giocate), 'n_quote_mancanti': n_mancanti}

def calcola_quota_sistema(colonne: List[Dict]) -> Dict:
    if not colonne:
        return {'quota_sistema': 0, 'prob_sistema': 0, 'edge_sistema': 0,
                'kelly_sistema': 0, 'classificazione': '⚪ N/D', 'livello': 'no-value'}
    quota_sistema = 1.0
    prob_sistema_dec = 1.0
    for c in colonne:
        if c['quota_totale'] > 0:
            quota_sistema *= c['quota_totale']
        if c['prob_combinata'] > 0:
            prob_sistema_dec *= (c['prob_combinata'] / 100)
    prob_sistema = prob_sistema_dec * 100
    edge_sistema = ((quota_sistema * prob_sistema / 100) - 1) * 100 if quota_sistema > 1 and prob_sistema > 0 else 0
    b = quota_sistema - 1
    p = prob_sistema_dec
    q = 1 - p
    kelly_sistema = max(0, (b * p - q) / b) if b > 0 else 0
    if edge_sistema > 20:
        classificazione = '💎 VALUE ECCELLENTE'; livello = 'excellent'
    elif edge_sistema > 10:
        classificazione = '✅ VALUE BUONO'; livello = 'good'
    elif edge_sistema > 5:
        classificazione = '🟡 VALUE MARGINALE'; livello = 'marginal'
    elif edge_sistema > 0:
        classificazione = '⚪ Quota fair'; livello = 'fair'
    else:
        classificazione = '🔴 No value'; livello = 'no-value'
    return {'quota_sistema': round(quota_sistema, 2), 'prob_sistema': round(prob_sistema, 2),
            'edge_sistema': round(edge_sistema, 1), 'kelly_sistema': round(kelly_sistema * 100, 2),
            'classificazione': classificazione, 'livello': livello}