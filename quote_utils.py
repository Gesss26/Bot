# ============================================================
# quote_utils.py
# Modulo condiviso per parsing quote Marathonbet (PDF)
# + normalizzazione nomi squadre
# + fuzzy matching con partite Excel
# + analisi value bet
# ============================================================

import re
import logging
import unicodedata
from typing import List, Dict, Optional
from io import BytesIO
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURAZIONE
# ============================================================

QUOTE_PDF_URL = "https://raw.githubusercontent.com/Gesss26/GesssAI-Pro---Auto/master/quote/marathonbet.pdf"
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
    # Inghilterra
    'manchester city': 'manchestercity', 'manchester united': 'manchesterunited',
    'newcastle': 'newcastle', 'newcastle united': 'newcastle',
    'tottenham': 'tottenham', 'chelsea': 'chelsea', 'arsenal': 'arsenal',
    'liverpool': 'liverpool', 'everton': 'everton', 'brighton': 'brighton',
    'aston villa': 'astonvilla', 'west ham': 'westham',
    'crystal palace': 'crystalpalace', 'wolverhampton': 'wolverhampton',
    'nottingham forest': 'nottinghamforest', 'bournemouth': 'bournemouth',
    'brentford': 'brentford', 'fulham': 'fulham', 'fulham fc': 'fulham',
    'leeds united': 'leedsunited', 'sunderland': 'sunderland',
    'hull city': 'hullcity', 'ipswich town': 'ipswichtown',
    'coventry city': 'coventrycity',
    # Germania
    'bayern monaco': 'bayernmonaco', 'bayern munich': 'bayernmonaco',
    'borussia dortmund': 'borussiadortmund',
    'borussia monchengladbach': 'borussiamonchengladbach',
    'eintracht francoforte': 'eintrachtfrancoforte',
    'bayer leverkusen': 'bayerleverkusen',
    'werder brema': 'werderbrema', 'werder bremen': 'werderbrema',
    'augsburg': 'augsburg', 'mainz': 'mainz',
    'amburgo': 'amburgo', 'hamburger sv': 'amburgo',
    'colonia': 'colonia', 'fc koln': 'colonia',
    'friburgo': 'friburgo', 'stoccarda': 'stoccarda',
    'union berlino': 'unionberlino', 'schalke 04': 'schalke04',
    'hoffenheim': 'hoffenheim', 'lipsia': 'lipsia', 'rb lipsia': 'lipsia',
    # Francia
    'paris saint-germain': 'psg', 'paris saint germain': 'psg', 'psg': 'psg',
    'olympique marsiglia': 'marsiglia', 'olympique marseille': 'marsiglia',
    'marsiglia': 'marsiglia', 'monaco': 'monaco',
    'lione': 'lione', 'lyon': 'lione', 'lilla': 'lilla', 'lille': 'lilla',
    'nizza': 'nizza', 'nice': 'nizza', 'lens': 'lens',
    'rennes': 'rennes', 'stade rennes fc': 'rennes',
    'strasburgo': 'strasburgo', 'strasbourg': 'strasburgo',
    'troyes': 'troyes', 'angers': 'angers', 'brest': 'brest',
    'auxerre': 'auxerre', 'toulouse': 'toulouse', 'tolosa fc': 'toulouse',
    'le havre ac': 'lehavre', 'le havre': 'lehavre',
    'lorient': 'lorient', 'le mans fc': 'lemans', 'le mans': 'lemans',
    'paris fc': 'parisfc',
    # Olanda
    'ajax': 'ajax', 'psv eindhoven': 'psveindhoven', 'psv': 'psveindhoven',
    'feyenoord': 'feyenoord', 'az alkmaar': 'azalkmaar', 'az': 'azalkmaar',
    'twente': 'twente', 'utrecht': 'utrecht', 'nec nimega': 'nec', 'nec': 'nec',
    'go ahead eagles': 'goaheadeagles', 'willem ii': 'willemii',
    'fortuna sittard': 'fortunasittard', 'sparta rotterdam': 'spartarotterdam',
    'heerenveen': 'heerenveen', 'groningen': 'groningen', 'zwolle': 'zwolle',
    'ado den haag': 'adodenhaag', 'cambuur': 'cambuur',
    'excelsior rotterdam': 'excelsior', 'telstar': 'telstar', 'den bosch': 'denbosch',
    # Portogallo
    'benfica': 'benfica', 'fc porto': 'porto', 'porto': 'porto',
    'sporting lisbona': 'sporting', 'sporting': 'sporting',
    'sporting braga': 'braga', 'braga': 'braga',
    'vitoria guimaraes': 'vitoriaguimaraes', 'moreirense': 'moreirense',
    'moreirense fc': 'moreirense', 'santa clara': 'santaclara',
    'estoril praia': 'estoril', 'casa pia lisbona': 'casapia',
    'casa pia': 'casapia', 'rio ave': 'rioave', 'famalicao': 'famalicao',
    'nacional da madeira': 'nacional', 'maritimo madeira': 'maritimo',
    'gil vicente': 'gilvicente', 'fc alverca sad': 'alverca', 'alverca': 'alverca',
    'arouca': 'arouca', 'estrela amadora': 'estrelaamadora',
    'academico de viseu fc': 'academicoviseu',
    # Belgio
    'club bruges': 'clubbruges', 'anderlecht': 'anderlecht', 'gent': 'gent',
    'genk': 'genk', 'standard liegi': 'standardliegi', 'standard': 'standardliegi',
    'anversa': 'anversa', 'antwerp': 'anversa',
    'union saint gilloise': 'unionsaintgilloise', 'cercle brugge': 'cerclebrugge',
    'royal charleroi': 'charleroi', 'charleroi': 'charleroi',
    'zulte waregem': 'zultewaregem', 'kortrijk': 'kortrijk',
    'sk beveren': 'beveren', 'oud-heverlee leuven': 'leuven',
    'raal la louviere': 'lalouviere', 'st. truidense vv': 'sinttruiden',
    'kvc westerlo': 'westerlo', 'lommel sk': 'lommel', 'mechelen': 'mechelen',
    # Turchia
    'galatasaray': 'galatasaray', 'fenerbahce': 'fenerbahce',
    'besiktas': 'besiktas', 'trabzonspor': 'trabzonspor',
    'basaksehir': 'basaksehir', 'istanbul basaksehir fk': 'basaksehir',
    'samsunspor': 'samsunspor', 'eyupspor': 'eyupspor',
    'konyaspor': 'konyaspor', 'konyaspor club': 'konyaspor',
    'antalyaspor': 'antalyaspor', 'alanyaspor': 'alanyaspor',
    'gaziantep fk': 'gaziantep', 'rizespor': 'rizespor',
    'kasimpasa': 'kasimpasa', 'goster': 'goster',
    # Scozia
    'celtic': 'celtic', 'glasgow rangers': 'rangers', 'rangers': 'rangers',
    'aberdeen': 'aberdeen', 'hearts': 'hearts',
    'heart of midlothian': 'hearts', 'heart of midlothian fc': 'hearts',
    'hibernian': 'hibernian', 'hibernian fc': 'hibernian',
    'dundee united': 'dundeeunited', 'dundee fc': 'dundee',
    'motherwell': 'motherwell', 'kilmarnock': 'kilmarnock',
    'st. johnstone fc': 'stjohnstone', 'st johnstone': 'stjohnstone',
    'st. mirren': 'stmirren', 'st mirren': 'stmirren', 'falkirk': 'falkirk',
    # Grecia
    'olympiacos': 'olympiacos', 'panathinaikos': 'panathinaikos',
    'aek atene': 'aek', 'aek': 'aek', 'paok': 'paok',
    # Corea
    'daejeon citizen': 'daejeon', 'daejeon': 'daejeon',
    'fc pohang steelers': 'pohang', 'pohang': 'pohang',
    'gimcheon sangmu': 'gimcheon', 'gangwon': 'gangwon',
    'gwangju': 'gwangju', 'anyang': 'anyang',
    # Giappone
    'kashima antlers': 'kashima', 'yokohama f marinos': 'yokohama',
    'kawasaki frontale': 'kawasaki',
}

# ============================================================
# NORMALIZZAZIONE NOMI
# ============================================================

_SUFFISSI_SOCIETARI = re.compile(
    r'\b(fc|ac|ssc|as|us|ss|asd|ssd|calcio|sportiva|società|societa|'
    r'1919|1929|1937|1908|1911|u23|u21|u19|cf|sk|sv|sc|vv|kvc|fk|bk|if|ff|cd|sd|ud|rc|rcd|afc|cfc)\b'
)


def normalizza_nome(nome: str) -> str:
    """Normalizza il nome della squadra per il matching"""
    if not nome:
        return ''
    n = str(nome).lower()
    # Rimuovi accenti
    n = unicodedata.normalize('NFD', n)
    n = ''.join(c for c in n if unicodedata.category(c) != 'Mn')
    # Rimuovi suffissi societari
    n = _SUFFISSI_SOCIETARI.sub('', n)
    # Rimuovi tutti i caratteri non alfanumerici
    n = re.sub(r'[^a-z0-9]', '', n)
    n = n.strip()
    # Applica traduzione
    if n in TRADUZIONI_SQUADRE:
        n = TRADUZIONI_SQUADRE[n]
    return n


def similarita(a: str, b: str) -> float:
    """Calcola la similarità tra due stringhe (Dice coefficient su bigrammi)"""
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
# PARSING PDF
# ============================================================

GIORNI = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
MESI = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
MESI_NUM = {'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4, 'maggio': 5, 'giugno': 6,
            'luglio': 7, 'agosto': 8, 'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12}


def estrai_righe_da_pdf(contenuto_pdf: bytes) -> List[str]:
    """Estrae le righe di testo dal PDF con pdfplumber"""
    try:
        import pdfplumber
    except ImportError:
        logger.error("❌ pdfplumber non installato. Aggiungi 'pdfplumber' a requirements.txt")
        return []

    righe = []
    try:
        with pdfplumber.open(BytesIO(contenuto_pdf)) as pdf:
            for page in pdf.pages:
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
    """Riconosce un'intestazione di campionato"""
    pattern = r'^([A-Z][a-zà-ù]+(?:\s+di\s+[A-Z][a-zà-ù]+)?)\s+-\s+(.+)$'
    match = re.match(pattern, testo)
    if not match:
        return None
    if any(g in testo for g in GIORNI):
        return None
    return testo.strip()


def is_riga_data(testo: str) -> Optional[str]:
    """Riconosce una riga data e restituisce la data ISO (YYYY-MM-DD)"""
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

    # Gestione Dicembre/Gennaio
    if mese_corrente == 1 and mese == 12:
        anno = oggi.year - 1
    elif mese < mese_corrente - 1:
        anno = oggi.year + 1

    return f"{anno}-{mese_str}-{giorno}"


def parse_riga_partita(testo: str) -> Optional[Dict]:
    """Parsa una riga partita del PDF Marathonbet"""
    pattern = r'^(\d{3,6})\s+(\d{1,2}:\d{2})\s+(.+)$'
    match = re.match(pattern, testo)
    if not match:
        return None

    alias, ora, resto = match.groups()

    quote_pattern = re.findall(r'\d+\.\d+', resto)
    if len(quote_pattern) < 3:
        return None

    quote = [float(q) for q in quote_pattern]

    prima_quota = resto.find(quote_pattern[0])
    evento_raw = resto[:prima_quota].strip()

    sep_idx = evento_raw.rfind(' - ')
    if sep_idx == -1:
        return None

    casa = evento_raw[:sep_idx].strip()
    ospiti = evento_raw[sep_idx + 3:].strip()

    if not casa or not ospiti:
        return None

    def q(idx):
        return quote[idx] if len(quote) > idx else None

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

    return {
        'alias': alias,
        'ora': ora,
        'casa': casa,
        'ospiti': ospiti,
        'quote': quote_mappate,
    }


def parse_marathonbet_pdf(righe: List[str]) -> List[Dict]:
    """Parsa tutte le righe del PDF e restituisce le partite con le quote"""
    partite = []
    campionato_corrente = None
    data_corrente = None
    data_iso_corrente = None

    for riga in righe:
        camp = is_intestazione_campionato(riga)
        if camp:
            campionato_corrente = camp
            continue

        data_iso = is_riga_data(riga)
        if data_iso:
            data_corrente = riga
            data_iso_corrente = data_iso
            continue

        # Salta intestazioni tabella
        if re.match(r'^(Alias|Codice|Evento|Calcio|1X2|DOPPIA|GG/NG|U/O|MG|SI|NO)', riga, re.IGNORECASE):
            continue

        partita = parse_riga_partita(riga)
        if partita:
            partita['campionato'] = campionato_corrente
            partita['data'] = data_corrente
            partita['dataISO'] = data_iso_corrente
            partita['fonte'] = 'Marathonbet'
            partite.append(partita)

    return partite

# ============================================================
# CARICAMENTO QUOTE DA GITHUB
# ============================================================


def load_quote_from_github() -> List[Dict]:
    """Scarica e parsa il PDF delle quote da GitHub"""
    try:
        logger.info(f"📂 Caricamento quote da: {QUOTE_PDF_URL}")
        response = requests.get(QUOTE_PDF_URL, timeout=30)
        if response.status_code != 200:
            logger.error(f"❌ HTTP {response.status_code}")
            return []

        righe = estrai_righe_da_pdf(response.content)
        if not righe:
            logger.error("❌ Nessuna riga estratta dal PDF")
            return []

        partite = parse_marathonbet_pdf(righe)
        logger.info(f"✅ Caricate {len(partite)} partite con quote")
        return partite
    except Exception as e:
        logger.error(f"❌ Errore caricamento quote: {e}")
        return []

# ============================================================
# TROVA QUOTA PER GIOCATA
# ============================================================

# Mappa (family_id, giocata) → chiave quota PDF
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
    """Trova l'entry quota corrispondente a un match (fuzzy matching)"""
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
    """
    Trova la quota per una specifica partita e giocata.
    Restituisce None se non trovata (il chiamante userà 1.00 come fallback).
    """
    entry = _trova_entry_quota(match, partite_quote)
    if not entry:
        return None

    quote = entry['quote']

    # Mapping diretto
    key = (family_id, giocata)
    if key in _MAPPING_QUOTE:
        return quote.get(_MAPPING_QUOTE[key])

    # DC+Over (es. 1X+O2.5)
    if family_id == 'dc_over' and '+' in giocata:
        parts = giocata.split('+')
        if len(parts) == 2:
            dc_q = quote.get(parts[0])
            over_key = parts[1]  # es. O2.5
            over_q = quote.get(over_key)
            if dc_q and over_q:
                return round(dc_q * over_q, 2)

    # DC+Under (es. 1X+U2.5)
    if family_id == 'dc_under' and '+' in giocata:
        parts = giocata.split('+')
        if len(parts) == 2:
            dc_q = quote.get(parts[0])
            under_key = parts[1]  # es. U2.5
            under_q = quote.get(under_key)
            if dc_q and under_q:
                return round(dc_q * under_q, 2)

    return None


def get_quota_or_fallback(match, family_id: str, giocata: str,
                          partite_quote: List[Dict]) -> float:
    """
    Restituisce la quota se disponibile, altrimenti 1.00 (fallback).
    Usata per il calcolo delle quote di colonna dove la quota mancante
    non deve alterare il prodotto.
    """
    quota = trova_quota_per_giocata(match, family_id, giocata, partite_quote)
    if quota is None or quota <= 1:
        return 1.0
    return quota

# ============================================================
# ANALISI VALUE BET
# ============================================================


def calcola_value_bet(pct_tua: float, quota_book: float) -> Dict:
    """
    Calcola edge, quota fair e Kelly stake.

    Args:
        pct_tua: percentuale stimata (0-100)
        quota_book: quota bookmaker

    Returns:
        Dict con edge, quota_fair, kelly, classificazione
    """
    if not quota_book or quota_book <= 1 or pct_tua <= 0:
        return {
            'edge': 0, 'quota_fair': 0, 'kelly': 0,
            'is_value': False, 'classificazione': '⚪', 'livello': 'no-value'
        }

    quota_fair = 100 / pct_tua
    edge = ((quota_book * pct_tua / 100) - 1) * 100

    # Kelly stake: f = (b*p - q) / b
    b = quota_book - 1
    p = pct_tua / 100
    q = 1 - p
    kelly = max(0, (b * p - q) / b) if b > 0 else 0

    if edge > 20:
        classificazione = '💎 VALUE ECCELLENTE'
        livello = 'excellent'
    elif edge > 10:
        classificazione = '✅ VALUE BUONO'
        livello = 'good'
    elif edge > 5:
        classificazione = '🟡 VALUE MARGINALE'
        livello = 'marginal'
    elif edge > 0:
        classificazione = '⚪ Quota fair'
        livello = 'fair'
    else:
        classificazione = '🔴 No value'
        livello = 'no-value'

    return {
        'edge': round(edge, 1),
        'quota_fair': round(quota_fair, 2),
        'kelly': round(kelly * 100, 2),
        'is_value': edge > 5,
        'classificazione': classificazione,
        'livello': livello,
    }


def calcola_quota_colonna(giocate: List[Dict]) -> Dict:
    """
    Calcola la quota totale di una colonna e le statistiche aggregate.

    Args:
        giocate: lista di dict con chiavi 'quota' (float o None), 'pct' (int)

    Returns:
        Dict con:
        - quota_totale: prodotto delle quote (fallback 1.0 per mancanti)
        - prob_combinata: prodotto delle probabilità in %
        - edge: edge della colonna
        - kelly: Kelly stake della colonna
        - classificazione: stringa con emoji
        - n_partite: numero di partite
        - n_quote_mancanti: numero di quote mancanti
    """
    if not giocate:
        return {
            'quota_totale': 0, 'prob_combinata': 0, 'edge': 0,
            'kelly': 0, 'classificazione': '⚪ N/D', 'livello': 'no-value',
            'n_partite': 0, 'n_quote_mancanti': 0,
        }

    quota_totale = 1.0
    prob_combinata_dec = 1.0
    n_mancanti = 0

    for g in giocate:
        quota = g.get('quota')
        if quota is None or quota <= 1:
            quota = 1.0
            n_mancanti += 1
        quota_totale *= quota

        pct = g.get('pct', 0) / 100
        prob_combinata_dec *= pct

    prob_combinata = prob_combinata_dec * 100

    # Edge
    if quota_totale > 1 and prob_combinata > 0:
        edge = ((quota_totale * prob_combinata / 100) - 1) * 100
    else:
        edge = 0

    # Kelly
    b = quota_totale - 1
    p = prob_combinata_dec
    q = 1 - p
    kelly = max(0, (b * p - q) / b) if b > 0 else 0

    if edge > 20:
        classificazione = '💎 VALUE ECCELLENTE'
        livello = 'excellent'
    elif edge > 10:
        classificazione = '✅ VALUE BUONO'
        livello = 'good'
    elif edge > 5:
        classificazione = '🟡 VALUE MARGINALE'
        livello = 'marginal'
    elif edge > 0:
        classificazione = '⚪ Quota fair'
        livello = 'fair'
    else:
        classificazione = '🔴 No value'
        livello = 'no-value'

    return {
        'quota_totale': round(quota_totale, 2),
        'prob_combinata': round(prob_combinata, 2),
        'edge': round(edge, 1),
        'kelly': round(kelly * 100, 2),
        'classificazione': classificazione,
        'livello': livello,
        'n_partite': len(giocate),
        'n_quote_mancanti': n_mancanti,
    }


def calcola_quota_sistema(colonne: List[Dict]) -> Dict:
    """
    Calcola la quota del sistema completo (prodotto delle quote delle colonne).

    Args:
        colonne: lista di dict restituiti da calcola_quota_colonna()

    Returns:
        Dict con quota_sistema, prob_sistema, edge_sistema, kelly_sistema, classificazione
    """
    if not colonne:
        return {
            'quota_sistema': 0, 'prob_sistema': 0, 'edge_sistema': 0,
            'kelly_sistema': 0, 'classificazione': '⚪ N/D', 'livello': 'no-value',
        }

    quota_sistema = 1.0
    prob_sistema_dec = 1.0

    for c in colonne:
        if c['quota_totale'] > 0:
            quota_sistema *= c['quota_totale']
        if c['prob_combinata'] > 0:
            prob_sistema_dec *= (c['prob_combinata'] / 100)

    prob_sistema = prob_sistema_dec * 100

    if quota_sistema > 1 and prob_sistema > 0:
        edge_sistema = ((quota_sistema * prob_sistema / 100) - 1) * 100
    else:
        edge_sistema = 0

    b = quota_sistema - 1
    p = prob_sistema_dec
    q = 1 - p
    kelly_sistema = max(0, (b * p - q) / b) if b > 0 else 0

    if edge_sistema > 20:
        classificazione = '💎 VALUE ECCELLENTE'
        livello = 'excellent'
    elif edge_sistema > 10:
        classificazione = '✅ VALUE BUONO'
        livello = 'good'
    elif edge_sistema > 5:
        classificazione = '🟡 VALUE MARGINALE'
        livello = 'marginal'
    elif edge_sistema > 0:
        classificazione = '⚪ Quota fair'
        livello = 'fair'
    else:
        classificazione = '🔴 No value'
        livello = 'no-value'

    return {
        'quota_sistema': round(quota_sistema, 2),
        'prob_sistema': round(prob_sistema, 2),
        'edge_sistema': round(edge_sistema, 1),
        'kelly_sistema': round(kelly_sistema * 100, 2),
        'classificazione': classificazione,
        'livello': livello,
    }