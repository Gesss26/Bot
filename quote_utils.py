# ============================================================
# quote_utils.py
# Modulo condiviso per parsing quote Marathonbet (PDF)
# Versione 5: parser one-line (formato reale Marathonbet)
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
    # Spagna
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
    'granada': 'granada', 'eibar': 'eibar',
    'huesca': 'huesca', 'lugo': 'lugo', 'mirandes': 'mirandes',
    'oviedo': 'oviedo', 'ponferradina': 'ponferradina', 'sporting gijon': 'sportinggijon',
    'tenerife': 'tenerife', 'zaragoza': 'zaragoza', 'real oviedo': 'realoviedo',
    'cartagena': 'cartagena', 'albacete': 'albacete', 'andorra': 'andorra',
    'burgos': 'burgos', 'ibiza': 'ibiza', 'leganes': 'leganes',
    'pontevedra': 'pontevedra', 'sabadell': 'sabadell', 'castellon': 'castellon',
    'cordoba': 'cordoba', 'cordoba cf': 'cordoba',

    # Italia
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
    'ascoli': 'ascoli', 'benevento': 'benevento', 'brescia': 'brescia',
    'cittadella': 'cittadella', 'cosenza': 'cosenza', 'feralpisalo': 'feralpisalo',
    'feralpi salo': 'feralpisalo', 'juve stabia': 'juvestabia',
    'modena': 'modena', 'perugia': 'perugia', 'pisa': 'pisa',
    'pordenone': 'pordenone', 'reggina': 'reggina', 'renate': 'renate',
    'sudtirol': 'sudtirol', 'ternana': 'ternana', 'trento': 'trento',
    'vicenza': 'vicenza', 'virtus entella': 'virtusentella',
    'alessandria': 'alessandria', 'avellino': 'avellino', 'catanzaro': 'catanzaro',
    'foggia': 'foggia', 'latina': 'latina', 'monopoli': 'monopoli',
    'picerno': 'picerno', 'potenza': 'potenza', 'taranto': 'taranto',
    'turris': 'turris', 'viterbese': 'viterbese', 'messina': 'messina',
    'giugliano': 'giugliano', 'monterosi': 'monterosi', 'recina': 'recina',

    # Inghilterra
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
    'yeovil': 'yeovil', 'crewe': 'crewe', 'grimsby': 'grimsby',
    'newport': 'newport', 'northampton': 'northampton', 'oldham': 'oldham',
    'port vale': 'portvale', 'rochdale': 'rochdale', 'swindon': 'swindon',

    # Germania
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
    'hannover': 'hannover', 'karlsruhe': 'karlsruhe',
    'dusseldorf': 'dusseldorf', 'fortuna dusseldorf': 'fortunadusseldorf',
    'nurnberg': 'nurnberg', 'norimberga': 'nurnberg',
    'paderborn': 'paderborn', 'sandhausen': 'sandhausen', 'darmstadt': 'darmstadt',
    'heidenheim': 'heidenheim', 'regensburg': 'regensburg', 'magdeburg': 'magdeburg',
    'magdeburgo': 'magdeburg', 'rostock': 'rostock', 'hansa rostock': 'hansarostock',
    'braunschweig': 'braunschweig', 'eintracht braunschweig': 'eintrachtbraunschweig',
    'kiel': 'kiel', 'holstein kiel': 'holsteinkiel', 'bielefeld': 'bielefeld',
    'arminia bielefeld': 'arminiabielefeld', 'ingolstadt': 'ingolstadt',
    'wurzburg': 'wurzburg', 'wuerzburg': 'wurzburg',
    'greuther furth': 'greutherfurth', 'furth': 'greutherfurth',
    'kaiserslautern': 'kaiserslautern', 'osnabruck': 'osnabruck',
    'vfl osnabruck': 'osnabruck', 'vfl 1899 osnabruck': 'osnabruck',
    'sv darmstadt 98': 'darmstadt', 'darmstadt 98': 'darmstadt',

    # Francia
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
    'metz': 'metz', 'dijon': 'dijon', 'digione': 'dijon', 'caen': 'caen',
    'le havre': 'lehavre', 'amiens': 'amiens', 'grenoble': 'grenoble',
    'grenoble foot 38': 'grenoble', 'guingamp': 'guingamp', 'nancy': 'nancy',
    'niort': 'niort', 'paris fc': 'parisfc', 'pau': 'pau', 'pau fc': 'pau',
    'quevilly': 'quevilly', 'rodez': 'rodez', 'rodez aveyron football': 'rodez',
    'sochaux': 'sochaux', 'sochaux-montbeliard': 'sochaux',
    'valenciennes': 'valenciennes', 'fc annecy': 'annecy', 'annecy': 'annecy',
    'usl dunkerque': 'dunkerque', 'dunkerque': 'dunkerque',
    'stade lavallois mfc': 'laval', 'laval': 'laval',
    'us boulogne': 'boulogne', 'boulogne': 'boulogne',

    # Portogallo
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

    # Olanda
    'ajax': 'ajax', 'psv': 'psv', 'psv eindhoven': 'psv', 'feyenoord': 'feyenoord',
    'az alkmaar': 'azalkmaar', 'az': 'azalkmaar', 'twente': 'twente',
    'utrecht': 'utrecht', 'vitesse': 'vitesse', 'heerenveen': 'heerenveen',
    'groningen': 'groningen', 'sparta rotterdam': 'spartarotterdam',
    'nijmegen': 'nijmegen', 'nec': 'nec', 'go ahead eagles': 'goaheadeagles',
    'rkc waalwijk': 'rkcwaalwijk', 'waalwijk': 'rkcwaalwijk',
    'fortuna sittard': 'fortunasittard', 'sittard': 'fortunasittard',
    'cambuur': 'cambuur', 'excelsior': 'excelsior', 'volendam': 'volendam',
    'emmen': 'emmen', 'almere city': 'almerecity', 'almere': 'almerecity',
    'almere city fc': 'almerecity', 'hercules': 'hercules',
    'den bosch': 'denbosch', 'eindhoven': 'eindhoven', 'fc eindhoven': 'eindhoven',
    'de graafschap': 'degraafschap', 'graafschap': 'degraafschap',
    'roda jc': 'rodajc', 'roda': 'rodajc', 'vvv venlo': 'vvvvenlo',
    'venlo': 'vvvvenlo', 'dordrecht': 'dordrecht', 'helmond sport': 'helmondsport',
    'jong ajax': 'jongajax', 'jong ajax amsterdam': 'jongajax',
    'jong psv': 'jongpsv', 'jong az': 'jongaz', 'jong az alkmaar': 'jongaz',
    'jong utrecht': 'jongutrecht', 'jong fc utrecht': 'jongutrecht',
    'jong twente': 'jongtwente', 'top oss': 'toposs', 'mvv maastricht': 'mvv',
    'mvv': 'mvv', 'heracles': 'heracles', 'heracles almelo': 'heracles',

    # Belgio
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

    # Scozia
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

    # Turchia
    'galatasaray': 'galatasaray', 'fenerbahce': 'fenerbahce',
    'besiktas': 'besiktas', 'trabzonspor': 'trabzonspor',
    'basaksehir': 'basaksehir', 'istanbul basaksehir': 'basaksehir',
    'adana demirspor': 'adanademirspor', 'adana': 'adanademirspor',
    'konyaspor': 'konyaspor', 'konya': 'konyaspor', 'konyaspor club': 'konyaspor',
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
# PARSING PDF (one-line: formato reale Marathonbet)
# ============================================================

GIORNI = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
MESI = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
MESI_NUM = {'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4, 'maggio': 5, 'giugno': 6,
            'luglio': 7, 'agosto': 8, 'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12}


def estrai_righe_da_pdf(contenuto_pdf: bytes) -> List[str]:
    """
    Estrae righe dal PDF. Usa pypdf (leggero) come primario, pdfplumber come fallback.
    """
    # Tentativo 1: pypdf
    try:
        from pypdf import PdfReader
        logger.info("📄 [PDF] Uso pypdf (leggero)...")
        reader = PdfReader(BytesIO(contenuto_pdf))
        logger.info(f"📄 [PDF] {len(reader.pages)} pagine")
        righe = []
        for i, page in enumerate(reader.pages, 1):
            try:
                testo = page.extract_text()
                if testo:
                    for riga in testo.split('\n'):
                        riga = riga.strip()
                        if riga:
                            righe.append(riga)
            except Exception as e:
                logger.warning(f"⚠️ [PDF] pypdf pagina {i}: {e}")
        logger.info(f"📄 [PDF] pypdf OK: {len(righe)} righe")
        if righe:
            return righe
    except ImportError:
        logger.warning("⚠️ [PDF] pypdf non installato, uso pdfplumber")
    except Exception as e:
        logger.warning(f"⚠️ [PDF] pypdf fallito: {e}")

    # Tentativo 2: pdfplumber
    try:
        import pdfplumber
        logger.info("📄 [PDF] Uso pdfplumber (fallback)...")
        righe = []
        with pdfplumber.open(BytesIO(contenuto_pdf)) as pdf:
            logger.info(f"📄 [PDF] {len(pdf.pages)} pagine")
            for i, page in enumerate(pdf.pages, 1):
                try:
                    testo = page.extract_text()
                    if testo:
                        for riga in testo.split('\n'):
                            riga = riga.strip()
                            if riga:
                                righe.append(riga)
                except Exception as e:
                    logger.warning(f"⚠️ [PDF] pdfplumber pagina {i}: {e}")
        logger.info(f"📄 [PDF] pdfplumber OK: {len(righe)} righe")
        return righe
    except ImportError:
        logger.error("❌ [PDF] Né pypdf né pdfplumber installati")
        return []
    except Exception as e:
        logger.error(f"❌ [PDF] pdfplumber fallito: {e}")
        return []


def is_riga_data(testo: str) -> Optional[str]:
    """Riconosce una riga data tipo 'Giovedì 17 Settembre' e restituisce ISO"""
    pattern = r'^(' + '|'.join(GIORNI) + r')\s+(\d{1,2})\s+(' + '|'.join(MESI) + r')\s*$'
    match = re.match(pattern, testo.strip(), re.IGNORECASE)
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


# Regex per una riga partita completa:
# ALIAS ORA CASA - OSPITI Q1 Q2 Q3 Q4 Q5 Q6 Q7 Q8 Q9 Q10 Q11 Q12 Q13 Q14 Q15 Q16
_RE_PARTITA = re.compile(
    r'^(\d{1,6})\s+'                                  # 1: alias
    r'(\d{1,2}:\d{2})\s+'                             # 2: ora
    r'(.+?)\s+-\s+(.+?)\s+'                           # 3: casa, 4: ospiti
    r'(\d+\.\d{2})\s+'                                # 5: 1
    r'(\d+\.\d{2})\s+'                                # 6: X
    r'(\d+\.\d{2})\s+'                                # 7: 2
    r'(\d+\.\d{2})\s+'                                # 8: 1X
    r'(\d+\.\d{2})\s+'                                # 9: 12
    r'(\d+\.\d{2})\s+'                                # 10: X2
    r'(\d+\.\d{2})\s+'                                # 11: GOAL
    r'(\d+\.\d{2})\s+'                                # 12: NOGOAL
    r'(\d+\.\d{2})\s+'                                # 13: UNDER 1.5
    r'(\d+\.\d{2})\s+'                                # 14: OVER 1.5
    r'(\d+\.\d{2})\s+'                                # 15: UNDER 2.5
    r'(\d+\.\d{2})\s+'                                # 16: OVER 2.5
    r'(\d+\.\d{2})\s+'                                # 17: UNDER 3.5
    r'(\d+\.\d{2})\s+'                                # 18: OVER 3.5
    r'(\d+\.\d{2})\s+'                                # 19: UNDER 4.5
    r'(\d+\.\d{2})\s*$'                               # 20: OVER 4.5
)


def parse_marathonbet_pdf(righe: List[str]) -> List[Dict]:
    """
    Parser per formato Marathonbet one-line:
    ALIAS ORA CASA - OSPITI Q1 QX Q2 Q1X Q12 QX2 QGOAL QNOGOAL
    QU1.5 QO1.5 QU2.5 QO2.5 QU3.5 QO3.5 QU4.5 QO4.5
    
    Esempio:
    2600 20:30 Manchester City - Norwich 1.10 9.80 19.00 1.02 1.05 5.75 1.95 1.76 7.40 1.06 3.75 1.23 2.18 1.61 1.54 2.33
    """
    partite = []
    data_iso_corrente = None
    data_corrente = None

    for riga in righe:
        # Riga data?
        data_iso = is_riga_data(riga)
        if data_iso:
            data_iso_corrente = data_iso
            data_corrente = riga
            continue

        # Riga partita?
        m = _RE_PARTITA.match(riga)
        if not m:
            continue

        try:
            alias = m.group(1)
            ora = m.group(2)
            casa = m.group(3).strip()
            ospiti = m.group(4).strip()
            # 16 quote
            q_vals = [float(m.group(i)) for i in range(5, 21)]
        except (ValueError, IndexError) as e:
            logger.warning(f"⚠️ [PDF] Errore parsing riga: {e} | {riga[:120]}")
            continue

        quote_mappate = {
            '1': q_vals[0], 'X': q_vals[1], '2': q_vals[2],
            '1X': q_vals[3], '12': q_vals[4], 'X2': q_vals[5],
            'GG': q_vals[6], 'NG': q_vals[7],
            'U1.5': q_vals[8], 'O1.5': q_vals[9],
            'U2.5': q_vals[10], 'O2.5': q_vals[11],
            'U3.5': q_vals[12], 'O3.5': q_vals[13],
            'U4.5': q_vals[14], 'O4.5': q_vals[15],
            'MG14_SI': None, 'MG14_NO': None,
            'MG25_SI': None, 'MG25_NO': None,
        }

        partite.append({
            'alias': alias,
            'ora': ora,
            'casa': casa,
            'ospiti': ospiti,
            'quote': quote_mappate,
            'campionato': None,
            'data': data_corrente,
            'dataISO': data_iso_corrente,
            'fonte': 'Marathonbet',
        })

    return partite


# ============================================================
# CARICAMENTO QUOTE DA GITHUB (multi-PDF con merge)
# ============================================================

def _download_and_parse_pdf(url: str) -> List[Dict]:
    """Scarica e parsa un singolo PDF di quote"""
    try:
        logger.info(f"📂 [PDF] Download: {url}")
        t0 = time.time()
        response = requests.get(url, timeout=(10, 60))
        logger.info(f"📂 [PDF] Download OK in {time.time()-t0:.1f}s "
                    f"(status={response.status_code}, {len(response.content)} bytes)")

        if response.status_code != 200:
            logger.error(f"❌ [PDF] HTTP {response.status_code} per {url}")
            return []

        if not response.content.startswith(b'%PDF'):
            logger.error(f"❌ [PDF] Non è un PDF")
            return []

        logger.info(f"📂 [PDF] Estrazione righe...")
        t0 = time.time()
        righe = estrai_righe_da_pdf(response.content)
        logger.info(f"📂 [PDF] Estratte {len(righe)} righe in {time.time()-t0:.1f}s")

        if not righe:
            logger.error(f"❌ [PDF] Nessuna riga estratta")
            return []

        logger.info(f"📂 [PDF] Parsing partite...")
        t0 = time.time()
        partite = parse_marathonbet_pdf(righe)
        logger.info(f"📂 [PDF] Parsate {len(partite)} partite in {time.time()-t0:.1f}s")

        if len(partite) == 0:
            logger.warning(f"⚠️ [PDF] 0 partite parsate! Prime 20 righe:")
            for i, r in enumerate(righe[:20]):
                logger.warning(f"   {i:3d}: {repr(r)}")

        return partite
    except requests.exceptions.Timeout:
        logger.error(f"❌ [PDF] TIMEOUT su {url}")
        return []
    except Exception as e:
        logger.error(f"❌ [PDF] Errore {url}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def _chiave_partita(p: Dict) -> Tuple[str, str, str, str]:
    return (
        normalizza_nome(p.get('casa', '')),
        normalizza_nome(p.get('ospiti', '')),
        p.get('dataISO', '') or '',
        p.get('ora', '') or '',
    )


def load_quote_from_github() -> List[Dict]:
    """Scarica e parsa tutti i PDF, unendo i risultati"""
    tutte_partite: List[Dict] = []
    indice: Dict[Tuple[str, str, str, str], Dict] = {}

    for url in QUOTE_PDF_URLS:
        logger.info(f"📂 [QUOTE] Processo: {url.split('/')[-1]}")
        partite = _download_and_parse_pdf(url)
        logger.info(f"📂 [QUOTE] {url.split('/')[-1]}: {len(partite)} partite")

        for p in partite:
            chiave = _chiave_partita(p)
            if chiave in indice:
                esistente = indice[chiave]
                for k, v in p['quote'].items():
                    if esistente['quote'].get(k) is None and v is not None:
                        esistente['quote'][k] = v
            else:
                indice[chiave] = p
                tutte_partite.append(p)

    logger.info(f"✅ [QUOTE] Totale partite (unite): {len(tutte_partite)}")
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
    if family_id == 'dc_over' and '+' in giocata:
        parts = giocata.split('+')
        if len(parts) == 2:
            dc_q = quote.get(parts[0])
            over_q = quote.get(parts[1])
            if dc_q and over_q:
                return round(dc_q * over_q, 2)
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