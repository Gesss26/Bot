# ============================================================
# quote_utils.py
# Modulo condiviso per parsing quote Marathonbet (PDF)
# Versione 2: parser multi-riga per pdfplumber
# ============================================================

import re
import time
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
    # ... (resto identico)
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

# Righe da ignorare (intestazioni tabella)
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
                logger.info(f"📄 Pagina {i} estratta")
    except Exception as e:
        logger.error(f"❌ Errore estrazione PDF: {e}")
        return []

    logger.info(f"✅ Estratte {len(righe)} righe totali")
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
    """Riconosce una quota (numero decimale come 2.35 o 11.10)"""
    if re.match(r'^\d+\.\d{1,2}$', testo):
        try:
            return float(testo)
        except:
            return None
    return None


def parse_marathonbet_pdf(righe: List[str]) -> List[Dict]:
    """
    Parser multi-riga: ogni partita è composta da più righe consecutive:
    alias / ora / evento / quota1 / quotaX / quota2 / ...
    """
    partite = []
    campionato_corrente = None
    data_corrente = None
    data_iso_corrente = None

    i = 0
    n = len(righe)

    while i < n:
        riga = righe[i]

        # Intestazione campionato
        camp = is_intestazione_campionato(riga)
        if camp:
            campionato_corrente = camp
            i += 1
            continue

        # Riga data
        data_iso = is_riga_data(riga)
        if data_iso:
            data_corrente = riga
            data_iso_corrente = data_iso
            i += 1
            continue

        # Ignora righe di intestazione tabella
        if riga in RIGHE_IGNORE:
            i += 1
            continue

        # Prova a riconoscere una partita:
        # alias (numero 3-6 cifre) / ora (HH:MM) / evento (X - Y) / quote...
        if re.match(r'^\d{3,6}$', riga):
            alias = riga
            # Controlla che le prossime righe siano ora + evento
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

            # Parsing evento
            sep_idx = evento_candidate.rfind(' - ')
            casa = evento_candidate[:sep_idx].strip()
            ospiti = evento_candidate[sep_idx + 3:].strip()

            if not casa or not ospiti:
                i += 1
                continue

            # Raccogli quote successive (fino a 20, o fino a riga non-quota)
            quote_list = []
            j = i + 3
            while j < n and len(quote_list) < 20:
                q = is_quota(righe[j])
                if q is not None:
                    quote_list.append(q)
                    j += 1
                elif righe[j] == '-':
                    # Quota mancante (es. Cittadella - Juventus Next Gen)
                    quote_list.append(None)
                    j += 1
                else:
                    break

            # Se abbiamo trovato almeno 3 quote, è una partita valida
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
# CARICAMENTO QUOTE DA GITHUB
# ============================================================

def load_quote_from_github() -> List[Dict]:
    try:
        logger.info(f"📂 [1/3] Download PDF da: {QUOTE_PDF_URL}")
        t0 = time.time()
        response = requests.get(QUOTE_PDF_URL, timeout=60)
        logger.info(f"📂 [1/3] Download OK in {time.time()-t0:.1f}s (status={response.status_code}, {len(response.content)} bytes)")

        if response.status_code != 200:
            logger.error(f"❌ HTTP {response.status_code}")
            return []

        logger.info("📂 [2/3] Estrazione righe dal PDF...")
        t0 = time.time()
        righe = estrai_righe_da_pdf(response.content)
        logger.info(f"📂 [2/3] Estratte {len(righe)} righe in {time.time()-t0:.1f}s")

        if not righe:
            logger.error("❌ Nessuna riga estratta")
            return []

        logger.info("📂 [3/3] Parsing partite...")
        t0 = time.time()
        partite = parse_marathonbet_pdf(righe)
        logger.info(f"📂 [3/3] Parsate {len(partite)} partite in {time.time()-t0:.1f}s")

        return partite
    except Exception as e:
        logger.error(f"❌ Errore caricamento quote: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

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