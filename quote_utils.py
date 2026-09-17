# ============================================================
# quote_utils.py
# Modulo condiviso per parsing quote Marathonbet (PDF)
# Versione 4: pypdf-first (leggero) + multi-PDF + merge
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
    'granada': 'granada', 'eibar': 'eibar',
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
    'yeovil': 'yeovil', 'crewe': 'crewe', 'grimsby': 'grimsby',
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
    'hannover': 'hannover', 'karlsruhe': 'karlsruhe',
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

    # ============ GRECIA ============
    'olympiakos': 'olympiakos', 'olympiacos': 'olympiakos',
    'panathinaikos': 'panathinaikos', 'aek atene': 'aekatene',
    'aek athens': 'aekatene', 'paok': 'paok', 'paok salonicco': 'paok',
    'aris salonicco': 'arissalonicco', 'aris': 'arissalonicco',
    'volos': 'volos', 'volos nfc': 'volos', 'of creta': 'ofcreta',
    'asteras tripolis': 'asterastripolis', 'asteras': 'asterastripolis',
    'atromitos': 'atromitos', 'ionikos': 'ionikos', 'lamia': 'lamia',
    'levadiakos': 'levadiakos', 'panaitolikos': 'panaitolikos',
    'panserraikos': 'panserraikos', 'kifisia': 'kifisia',

    # ============ RUSSIA ============
    'zenit': 'zenit', 'zenit san pietroburgo': 'zenit',
    'spartak mosca': 'spartakmosca', 'spartak moscow': 'spartakmosca',
    'cska mosca': 'cskamosca', 'cska moscow': 'cskamosca',
    'lokomotiv mosca': 'lokomotivmosca', 'lokomotiv moscow': 'lokomotivmosca',
    'dinamo mosca': 'dinamomosca', 'dinamo moscow': 'dinamomosca',
    'krasnodar': 'krasnodar', 'rostov': 'rostov', 'rubin kazan': 'rubinkazan',
    'kazan': 'rubinkazan', 'akhmat grozny': 'akhmatgrozny', 'grozny': 'akhmatgrozny',
    'sochi': 'sochi', 'pfc sochi': 'sochi', 'ural': 'ural',
    'ural ekaterinburg': 'ural', 'krylia sovetov': 'kryliasovetov',
    'samara': 'kryliasovetov', 'orenburg': 'orenburg',
    'fakel voronezh': 'fakelvoronezh', 'voronezh': 'fakelvoronezh',
    'baltika': 'baltika', 'baltika kaliningrad': 'baltika',
    'paris nn': 'parisnn', 'nizhny novgorod': 'parisnn',

    # ============ UCRAINA ============
    'shakhtar donetsk': 'shakhtardonetsk', 'shakhtar': 'shakhtardonetsk',
    'dinamo kiev': 'dinamokiev', 'dynamo kyiv': 'dinamokiev',
    'zorya luhansk': 'zoryaluhansk', 'zorya': 'zoryaluhansk',
    'dnipro': 'dnipro', 'dnipro-1': 'dnipro1', 'vorskla': 'vorskla',
    'vorskla poltava': 'vorskla', 'oleksandriya': 'oleksandriya',
    'kolos kovalivka': 'koloskovalivka', 'kolos': 'koloskovalivka',
    'rukh lviv': 'rukhlviv', 'lviv': 'rukhlviv', 'veres rivne': 'veresrivne',
    'rivne': 'veresrivne', 'metalist': 'metalist', 'metalist kharkiv': 'metalist',
    'minai': 'minai', 'inhulets': 'inhulet',
    'chornomorets': 'chornomorets', 'odesa': 'chornomorets',

    # ============ ALTRI EUROPA ============
    # Austria
    'salzburg': 'salzburg', 'rb salzburg': 'salzburg',
    'sturm graz': 'sturmgraz', 'graz': 'sturmgraz',
    'rapid vienna': 'rapidvienna', 'rapid wien': 'rapidvienna',
    'austria vienna': 'austriavienna', 'austria wien': 'austriavienna',
    'lask': 'lask', 'lask linz': 'lask', 'linz': 'lask',
    'wolfsberger': 'wolfsberger', 'wolfsberg': 'wolfsberger',
    'hartberg': 'hartberg', 'altach': 'altach', 'rheindorf altach': 'altach',
    'ried': 'ried', 'klagenfurt': 'klagenfurt', 'austria klagenfurt': 'klagenfurt',
    'tirol': 'tirol', 'wattens': 'wattens', 'wsg tirol': 'wattens',

    # Svizzera
    'young boys': 'youngboys', 'bsc young boys': 'youngboys',
    'basilea': 'basilea', 'basel': 'basilea', 'fc basel': 'basilea',
    'zurigo': 'zurigo', 'zurich': 'zurigo', 'fc zurich': 'zurigo',
    'grasshopper': 'grasshopper', 'gc zurigo': 'grasshopper',
    'servette': 'servette', 'lugano': 'lugano', 'lucerna': 'lucerna',
    'luzern': 'lucerna', 'st gallen': 'stgallen', 'san gallo': 'stgallen',
    'sion': 'sion', 'losanna': 'losanna', 'lausanne': 'losanna',
    'thun': 'thun', 'winterthur': 'winterthur', 'yverdon': 'yverdon',
    'stade lausanne': 'stadlausanne', 'lausanne ouchy': 'lausanneouchy',

    # Danimarca
    'copenhagen': 'copenhagen', 'fc copenhagen': 'copenhagen',
    'brondby': 'brondby', 'midtjylland': 'midtjylland', 'fcm': 'midtjylland',
    'aalborg': 'aalborg', 'randers': 'randers', 'nordsjaelland': 'nordsjaelland',
    'agf': 'agf', 'aarhus': 'agf', 'ob': 'ob', 'odense': 'ob',
    'silkeborg': 'silkeborg', 'viborg': 'viborg', 'vejle': 'vejle',
    'lyngby': 'lyngby', 'horsens': 'horsens',

    # Norvegia
    'bodo glimt': 'bodoglimt', 'bodo': 'bodoglimt',
    'molde': 'molde', 'rosenborg': 'rosenborg', 'viking': 'viking',
    'viking stavanger': 'viking', 'brann': 'brann', 'lillestrom': 'lillestrom',
    'valerenga': 'valerenga', 'tromso': 'tromso', 'sarpsborg': 'sarpsborg',
    'stromsgodset': 'stromsgodset', 'haugesund': 'haugesund',
    'kristiansund': 'kristiansund', 'hamkam': 'hamkam', 'sandefjord': 'sandefjord',
    'odd': 'odd', 'odd greenland': 'odd', 'jerv': 'jerv',

    # Svezia
    'malmo': 'malmo', 'malmo ff': 'malmo', 'aik': 'aik', 'aik solna': 'aik',
    'djurgarden': 'djurgarden', 'hammarby': 'hammarby', 'ifk goteborg': 'ifkgoteborg',
    'goteborg': 'ifkgoteborg', 'elfsborg': 'elfsborg', 'hacken': 'hacken',
    'norrkoping': 'norrkoping', 'kalmar': 'kalmar', 'mjallby': 'mjallby',
    'varberg': 'varberg', 'degerfors': 'degerfors', 'sundsvall': 'sundsvall',
    'helsingborg': 'helsingborg', 'halmstad': 'halmstad', 'sirius': 'sirius',
    'varnamo': 'varnamo', 'brommapojkarna': 'brommapojkarna',

    # Polonia
    'legia varsavia': 'legiavarsavia', 'legia warsaw': 'legiavarsavia',
    'lech poznan': 'lechpoznan', 'poznan': 'lechpoznan',
    'wisla cracovia': 'wisplacracovia', 'wisla krakow': 'wisplacracovia',
    'cracovia': 'cracovia', 'krakow': 'cracovia',
    'gornik zabrze': 'gornikzabrze', 'zabrze': 'gornikzabrze',
    'piast gliwice': 'piastgliwice', 'gliwice': 'piastgliwice',
    'jagiellonia': 'jagiellonia', 'jagiellonia bialystok': 'jagiellonia',
    'bialystok': 'jagiellonia', 'pogon szczecin': 'pogonszczecin',
    'szczecin': 'pogonszczecin', 'slask wroclaw': 'slaskwroclaw',
    'wroclaw': 'slaskwroclaw', 'radomiak': 'radomiak', 'radomiak radom': 'radomiak',
    'radom': 'radomiak', 'widzew lodz': 'widzewlodz', 'lodz': 'widzewlodz',
    'lks lodz': 'lkslodz', 'korona kielce': 'koronakielce', 'kielce': 'koronakielce',
    'stala mielec': 'stalamielec', 'mielec': 'stalamielec',
    'warta poznan': 'wartapoznan', 'ruch chorzow': 'ruchchorzow',
    'chorzow': 'ruchchorzow', 'zaglebie lubin': 'zaglebielubin',
    'lubin': 'zaglebielubin', 'nieciecza': 'nieciecza',

    # Repubblica Ceca
    'slavia praga': 'slaviapraga', 'slavia prague': 'slaviapraga',
    'viktoria plzen': 'viktoriaplzen', 'plzen': 'viktoriaplzen',
    'sparta praga': 'spartapraga', 'sparta prague': 'spartapraga',
    'banik ostrava': 'banikostrava', 'ostrava': 'banikostrava',
    'slovan liberec': 'slovanliberec', 'liberec': 'slovanliberec',
    'jablonec': 'jablonec', 'mlada boleslav': 'mladaboleslav',
    'bohemians 1905': 'bohemians1905', 'bohemians praga': 'bohemians1905',
    'sigma olomouc': 'sigmaolomouc', 'olomouc': 'sigmaolomouc',
    'teplice': 'teplice', 'zbrojovka brno': 'zbrojovkabrno', 'brno': 'zbrojovkabrno',
    'karvina': 'karvina', 'pardubice': 'pardubice', 'hradec kralove': 'hradeckralove',
    'ceske budovice': 'ceskebudovice', 'budovice': 'ceskebudovice',

    # Croazia
    'dinamo zagabria': 'dinamozagabria', 'dinamo zagreb': 'dinamozagabria',
    'hajduk spalato': 'hajdukspalato', 'hajduk split': 'hajdukspalato',
    'rijeka': 'rijeka', 'hajduk': 'hajdukspalato', 'lokomotiva zagabria': 'lokomotivazagabria',
    'osijek': 'osijek', 'nkg osijek': 'osijek', 'gorica': 'gorica',
    'istria': 'istria', 'istria 1961': 'istria', 'slaven belupo': 'slavenbelupo',
    'belupo': 'slavenbelupo', 'varazdin': 'varazdin', 'sibenik': 'sibenik',

    # Serbia
    'stella rossa': 'stellrossa', 'crvena zvezda': 'stellrossa',
    'partizan': 'partizan', 'partizan belgrado': 'partizan',
    'vojvodina': 'vojvodina', 'vojvodina novi sad': 'vojvodina',
    'cukaricki': 'cukaricki', 'radnicki nis': 'radnickinis', 'nis': 'radnickinis',
    'spartak subotica': 'spartaksubotica', 'subotica': 'spartaksubotica',
    'napredak': 'napredak', 'mladost lucani': 'mladostlucani',
    'backa topola': 'backatopola', 'topola': 'backatopola',
    'radnik': 'radnik', 'proleter': 'proleter', 'novi pazar': 'novipazar',

    # Romania
    'fcsb': 'fcsb', 'steaua': 'fcsb', 'steaua bucarest': 'fcsb',
    'cfr cluj': 'cfrcluj', 'cluj': 'cfrcluj', 'universitatea craiova': 'universitateacraiova',
    'craiova': 'universitateacraiova', 'rapid bucarest': 'rapidbucarest',
    'dinamo bucarest': 'dinamobucarest', 'astra giurgiu': 'astragiurgiu',
    'giurgiu': 'astragiurgiu', 'viitorul': 'viitorul', 'farul constanta': 'farulconstanta',
    'constanta': 'farulconstanta', 'sepsi': 'sepsi', 'seps osfk': 'sepsi',
    'botosani': 'botosani', 'fc botosani': 'botosani', 'gaz metan': 'gazmetan',
    'medias': 'medias', 'chindia targoviste': 'chindiatargoviste',
    'targoviste': 'chindiatargoviste', 'hermannstadt': 'hermannstadt',
    'sibiu': 'hermannstadt', 'uta arad': 'utaarad', 'arad': 'utaarad',
    'petrolul ploiesti': 'petrolulploiesti', 'ploiesti': 'petrolulploiesti',

    # Ungheria
    'ferencvaros': 'ferencvaros', 'ferencvaros budapest': 'ferencvaros',
    'mol fehervar': 'molfehervar', 'fehervar': 'molfehervar',
    'videoton': 'molfehervar', 'puskas akademia': 'puskasakademia',
    'puskas': 'puskasakademia', 'ujpest': 'ujpest', 'ujpest fc': 'ujpest',
    'honved': 'honved', 'budapest honved': 'honved', 'vidi': 'molfehervar',

    # Bulgaria
    'ludogorets': 'ludogorets', 'ludogorets razgrad': 'ludogorets',
    'razgrad': 'ludogorets', 'cska sofia': 'cskasofia', 'sofia': 'cskasofia',
    'levski sofia': 'levskisofia', 'levski': 'levskisofia',
    'botev plovdiv': 'botevplovdiv', 'plovdiv': 'botevplovdiv',
    'lokomotiv plovdiv': 'lokomotivplovdiv', 'cherno more': 'chernomore',
    'cherno more varna': 'chernomore', 'varna': 'chernomore',

    # Slovacchia
    'slovan bratislava': 'slovanbratislava', 'bratislava': 'slovanbratislava',
    'zilina': 'zilina', 'msk zilina': 'zilina', 'spartak trnava': 'spartaktrnava',
    'trnava': 'spartaktrnava', 'dunajska streda': 'dunajskastreda',
    'streda': 'dunajskastreda', 'trencin': 'trencin', 'as trencin': 'trencin',
    'ruzomberok': 'ruzomberok', 'mfk ruzomberok': 'ruzomberok',
    'pohronie': 'pohronie', 'zlate moravce': 'zlatemoravce',
    'moravce': 'zlatemoravce', 'senica': 'senica', 'fk senica': 'senica',
    'sere': 'sere', 'sport podbrezova': 'podbrezova', 'podbrezova': 'podbrezova',

    # Slovenia
    'maribor': 'maribor', 'nk maribor': 'maribor', 'olimpija ljubljana': 'olimpijaljubljana',
    'ljubljana': 'olimpijaljubljana', 'olimpija': 'olimpijaljubljana',
    'domzale': 'domzale', 'nk domzale': 'domzale', 'celje': 'celje',
    'nk celje': 'celje', 'koper': 'koper', 'fc koper': 'koper',
    'bravo': 'bravo', 'nk bravo': 'bravo', 'mura': 'mura', 'ns mura': 'mura',
    'radomlje': 'radomlje', 'kalcer radomlje': 'radomlje',
    'gorica': 'gorica', 'nd gorica': 'gorica', 'aluminij': 'aluminij',
    'nk aluminij': 'aluminij', 'tabor': 'tabor', 'tabor sezana': 'tabor',

    # Cipro
    'apoel': 'apoel', 'apoel nicosia': 'apoel', 'nicosia': 'apoel',
    'aek larnaca': 'aeklarnaca', 'larnaca': 'aeklarnaca',
    'anorthosis': 'anorthosis', 'anorthosis famagosta': 'anorthosis',
    'famagosta': 'anorthosis', 'apollon': 'apollon', 'apollon limassol': 'apollon',
    'limassol': 'apollon', 'ael limassol': 'aellimassol', 'omonia': 'omonia',
    'omonia nicosia': 'omonia', 'pafos': 'pafos', 'pafos fc': 'pafos',
    'aris limassol': 'arisslimassol', 'doxa': 'doxa', 'doxa katokopias': 'doxa',

    # Israele
    'maccabi tel aviv': 'maccabitelaviv', 'tel aviv': 'maccabitelaviv',
    'maccabi haifa': 'maccabihaifa', 'haifa': 'maccabihaifa',
    'hapoel tel aviv': 'hapoeltelaviv', 'hapoel haifa': 'hapoelhaifa',
    'hapoel beer sheva': 'hapoelbeersheva', 'beer sheva': 'hapoelbeersheva',
    'beitar gerusalemme': 'beitargerusalemme', 'beitar jerusalem': 'beitargerusalemme',
    'gerusalemme': 'beitargerusalemme', 'jerusalem': 'beitargerusalemme',
    'bnei yehuda': 'bneiyehuda', 'bnei sakhnin': 'bneisakhnin',
    'sakhnin': 'bneisakhnin', 'ashdod': 'ashdod', 'ms ashdod': 'ashdod',
    'netanya': 'netanya', 'maccabi netanya': 'netanya',

    # ============ SUD AMERICA ============
    # Brasile
    'flamengo': 'flamengo', 'palmeiras': 'palmeiras', 'corinthians': 'corinthians',
    'sao paulo': 'saopaulo', 'santos': 'santos', 'gremio': 'gremio',
    'internacional': 'internacional', 'atletico mineiro': 'atleticomineiro',
    'atletico mg': 'atleticomineiro', 'cruzeiro': 'cruzeiro',
    'fluminense': 'fluminense', 'botafogo': 'botafogo', 'vasco da gama': 'vascodagama',
    'vasco': 'vascodagama', 'bahia': 'bahia', 'fortaleza': 'fortaleza',
    'ceara': 'ceara', 'sport recife': 'sportrecife', 'recife': 'sportrecife',
    'athletico paranaense': 'athleticoparanaense', 'paranaense': 'athleticoparanaense',
    'bragantino': 'bragantino', 'rb bragantino': 'bragantino',
    'goias': 'goias', 'coritiba': 'coritiba', 'america mineiro': 'americamineiro',
    'america mg': 'americamineiro', 'cuiaba': 'cuiaba', 'juventude': 'juventude',

    # Argentina
    'boca juniors': 'bocajuniors', 'boca': 'bocajuniors',
    'river plate': 'riverplate', 'river': 'riverplate',
    'racing club': 'racingclub', 'racing': 'racingclub',
    'independiente': 'independiente', 'san lorenzo': 'sanlorenzo',
    'velez sarsfield': 'velezsarsfield', 'velez': 'velezsarsfield',
    'estudiantes': 'estudiantes', 'estudiantes la plata': 'estudiantes',
    'la plata': 'estudiantes', 'gimnasia la plata': 'gimnasialaplata',
    'gimnasia': 'gimnasialaplata', 'huracan': 'huracan', 'lanus': 'lanus',
    'banfield': 'banfield', 'talleres': 'talleres', 'talleres cordoba': 'talleres',
    'cordoba': 'talleres', 'newells old boys': 'newellsoldboys',
    'newells': 'newellsoldboys', 'rosario central': 'rosariocentral',
    'rosario': 'rosariocentral', 'argentinos juniors': 'argentinosjuniors',
    'defensa y justicia': 'defensayjusticia', 'defensa': 'defensayjusticia',
    'godoy cruz': 'godoycruz', 'colon': 'colon', 'colon santa fe': 'colon',
    'santa fe': 'colon', 'union santa fe': 'unionsantafe', 'union': 'unionsantafe',
    'central cordoba': 'centralcordoba', 'patronato': 'patronato',
    'atletico tucuman': 'atleticotucuman', 'tucuman': 'atleticotucuman',
    'platense': 'platense', 'arsenal sarandi': 'arsenalsarandi',
    'arsenal': 'arsenalsarandi', 'sarandi': 'arsenalsarandi',
    'aldosivi': 'aldosivi', 'barracas central': 'barracascentral',
    'barracas': 'barracascentral', 'tigre': 'tigre', 'sarmiento': 'sarmiento',
    'instituto': 'instituto', 'belgrano': 'belgrano',

    # Messico
    'america': 'america', 'club america': 'america',
    'guadalajara': 'guadalajara', 'chivas': 'guadalajara',
    'cruz azul': 'cruzazul', 'pumas': 'pumas', 'pumas unam': 'pumas',
    'unam': 'pumas', 'tigres': 'tigres', 'tigres uanl': 'tigres',
    'uanl': 'tigres', 'monterrey': 'monterrey', 'rayados': 'monterrey',
    'toluca': 'toluca', 'deportivo toluca': 'toluca',
    'santos laguna': 'santoslaguna', 'laguna': 'santoslaguna',
    'leon': 'leon', 'club leon': 'leon', 'pachuca': 'pachuca',
    'puebla': 'puebla', 'atlas': 'atlas', 'atlas guadalajara': 'atlas',
    'queretaro': 'queretaro', 'necaxa': 'necaxa', 'mazatlan': 'mazatlan',
    'juarez': 'juarez', 'fc juarez': 'juarez', 'tijuana': 'tijuana',
    'xolos': 'tijuana', 'xolos tijuana': 'tijuana', 'atletico san luis': 'atleticosanluis',
    'san luis': 'atleticosanluis',

    # ============ USA ============
    'inter miami': 'intermiami', 'miami': 'intermiami',
    'la galaxy': 'lagalaxy', 'galaxy': 'lagalaxy',
    'lafc': 'lafc', 'los angeles fc': 'lafc', 'los angeles': 'lafc',
    'seattle sounders': 'seattlesounders', 'sounders': 'seattlesounders',
    'atlanta united': 'atlantaunited', 'atlanta': 'atlantaunited',
    'portland timbers': 'portlandtimbers', 'portland': 'portlandtimbers',
    'austin fc': 'austinfc', 'austin': 'austinfc',
    'fc dallas': 'fcdallas', 'dallas': 'fcdallas',
    'houston dynamo': 'houstondynamo', 'houston': 'houstondynamo',
    'sporting kansas city': 'sportingkansascity', 'kansas city': 'sportingkansascity',
    'colorado rapids': 'coloradorapids', 'colorado': 'coloradorapids',
    'real salt lake': 'realsaltlake', 'salt lake': 'realsaltlake',
    'minnesota united': 'minnesotaunited', 'minnesota': 'minnesotaunited',
    'chicago fire': 'chicagofire', 'chicago': 'chicagofire',
    'columbus crew': 'columbuscrew', 'columbus': 'columbuscrew',
    'new england revolution': 'newenglandrevolution', 'new england': 'newenglandrevolution',
    'philadelphia union': 'philadelphiaunion', 'philadelphia': 'philadelphiaunion',
    'new york city fc': 'newyorkcityfc', 'nycfc': 'newyorkcityfc',
    'new york red bulls': 'newyorkredbulls', 'red bulls': 'newyorkredbulls',
    'dc united': 'dcunited', 'washington': 'dcunited',
    'orlando city': 'orlandocity', 'orlando': 'orlandocity',
    'nashville sc': 'nashvillesc', 'nashville': 'nashvillesc',
    'fc cincinnati': 'fccincinnati', 'cincinnati': 'fccincinnati',
    'toronto fc': 'torontofc', 'toronto': 'torontofc',
    'cf montreal': 'cfmontreal', 'montreal': 'cfmontreal',
    'vancouver whitecaps': 'vancouverwhitecaps', 'vancouver': 'vancouverwhitecaps',
    'st louis city': 'stlouiscity', 'st louis': 'stlouiscity',
    'charlotte fc': 'charlottefc', 'charlotte': 'charlottefc',
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
    """
    Estrae righe dal PDF.
    Usa pypdf (leggero, veloce, no dipendenze di sistema) come primario.
    pdfplumber come fallback.
    """
    # Tentativo 1: pypdf (leggero)
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

    # Tentativo 2: pdfplumber (fallback, pesante)
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
        import traceback
        logger.error(traceback.format_exc())
        return []


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
        logger.info(f"📂 [PDF] Download: {url}")
        t0 = time.time()
        response = requests.get(url, timeout=(10, 60))
        logger.info(f"📂 [PDF] Download OK in {time.time()-t0:.1f}s "
                    f"(status={response.status_code}, {len(response.content)} bytes)")

        if response.status_code != 200:
            logger.error(f"❌ [PDF] HTTP {response.status_code} per {url}")
            return []

        if not response.content.startswith(b'%PDF'):
            content_type = response.headers.get('content-type', '')
            logger.error(f"❌ [PDF] Non è un PDF (content-type={content_type})")
            logger.error(f"   Prime 200 chars: {response.text[:200]}")
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

        # LOG DIAGNOSTICO: prime righe se 0 partite
        if len(partite) == 0 and len(righe) > 0:
            logger.warning(f"⚠️ [PDF] 0 partite parsate! Prime 40 righe estratte:")
            for i, r in enumerate(righe[:40]):
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
    Unisce i risultati: se una partita appare in più PDF, unisce le quote.
    """
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
                if not esistente.get('campionato') and p.get('campionato'):
                    esistente['campionato'] = p['campionato']
            else:
                indice[chiave] = p
                tutte_partite.append(p)

    logger.info(f"✅ [QUOTE] Totale partite (unite da {len(QUOTE_PDF_URLS)} PDF): {len(tutte_partite)}")
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
            over_q = quote.get(parts[1])
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