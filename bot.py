import requests
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import pandas as pd
from io import BytesIO
import re
import json
import traceback

# Importa il modulo quote
from quote_utils import (
    load_quote_from_github,
    trova_quota_per_giocata,
    get_quota_or_fallback,
    calcola_value_bet,
    calcola_quota_colonna,
    calcola_quota_sistema,
)

# ============================================================
# CONFIGURAZIONE
# ============================================================

TOKEN = "8889221419:AAEgOICSM7aLhVGBoFEDs8e-CKW5zKCExVc"
EXCEL_URL = "https://raw.githubusercontent.com/Gesss26/GesssAI-Pro---Auto/master/excel/GesssAI_Input.xlsx"

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
# DATACLASSES
# ============================================================

@dataclass
class Match:
    id: str
    campionato: str
    round: str
    data: str
    ora: str
    casa: str
    ospiti: str
    stato: str
    golCasa: int
    golOspite: int
    risultato: str

@dataclass
class Giocata:
    famiglia: str
    family_id: str
    label: str
    pct: int
    is_bomb: bool
    quota: Optional[float] = None
    edge: Optional[float] = None
    quota_fair: Optional[float] = None
    kelly: Optional[float] = None
    classificazione: Optional[str] = None

@dataclass
class MatchAnalysis:
    match: Match
    giocate: List[Giocata]
    score: int
    has_bomb: bool
    home_form: Dict
    away_form: Dict

# ============================================================
# FAMIGLIE GIOCATE
# ============================================================

FAMIGLIE_GIOCATE = {
    'fisse': {'id': 'fisse', 'label': '🎯 Fisse', 'options': ['1', 'X', '2']},
    'dc': {'id': 'dc', 'label': '🛡️ Doppia Chance', 'options': ['1X', '12', 'X2']},
    'gg_ng': {'id': 'gg_ng', 'label': '⚽ GG-NG', 'options': ['GG', 'NG']},
    'over_15': {'id': 'over_15', 'label': '⬆️ Over 1,5', 'options': ['Over 1.5']},
    'over_25': {'id': 'over_25', 'label': '⬆️ Over 2,5', 'options': ['Over 2.5']},
    'under': {'id': 'under', 'label': '⬇️ Under', 'options': ['Under 1.5', 'Under 2.5', 'Under 3.5', 'Under 4.5']},
    'dc_under': {'id': 'dc_under', 'label': '🔗 DC+Under', 'options': ['1X+U1.5', '12+U1.5', 'X2+U1.5', '1X+U2.5', '12+U2.5', 'X2+U2.5', '1X+U3.5', '12+U3.5', 'X2+U3.5', '1X+U4.5', '12+U4.5', 'X2+U4.5']},
    'dc_over': {'id': 'dc_over', 'label': '🔗 DC+Over', 'options': ['1X+O1.5', '12+O1.5', 'X2+O1.5', '1X+O2.5', '12+O2.5', 'X2+O2.5', '1X+O3.5', '12+O3.5', 'X2+O3.5', '1X+O4.5', '12+O4.5', 'X2+O4.5']},
    'multigol': {'id': 'multigol', 'label': '📊 Multigol Totale', 'options': ['0-2', '1-3', '1-4', '2-5']},
    'mg_casa_ospite': {'id': 'mg_casa_ospite', 'label': '⚔️ MG Casa+Ospite', 'options': ['0-1+0-1', '0-1+0-2', '0-1+1-3', '0-1+2-5', '0-2+0-1', '0-2+0-2', '0-2+1-3', '0-2+2-5', '1-3+0-1', '1-3+0-2', '1-3+1-3', '1-3+2-5', '2-5+0-1', '2-5+0-2', '2-5+1-3', '2-5+2-5']},
    'dc_multigol': {'id': 'dc_multigol', 'label': '🔗 DC+Multigol', 'options': ['1X+0-2', '12+0-2', 'X2+0-2', '1X+1-3', '12+1-3', 'X2+1-3', '1X+1-4', '12+1-4', 'X2+1-4', '1X+2-5', '12+2-5', 'X2+2-5']}
}

FAMIGLIE_LIST = [
    ('fisse', '🎯 Fisse'),
    ('dc', '🛡️ Doppia Chance'),
    ('gg_ng', '⚽ GG-NG'),
    ('over_15', '⬆️ Over 1,5'),
    ('over_25', '⬆️ Over 2,5'),
    ('under', '⬇️ Under'),
    ('dc_under', '🔗 DC+Under'),
    ('dc_over', '🔗 DC+Over'),
    ('multigol', '📊 Multigol Totale'),
    ('mg_casa_ospite', '⚔️ MG Casa+Ospite'),
    ('dc_multigol', '🔗 DC+Multigol')
]

user_states = {}

# Cache quote in memoria
_quote_cache = {'partite': [], 'timestamp': 0}
_QUOTE_CACHE_TTL = 3600  # 1 ora

def get_quote_cached() -> List[Dict]:
    """Restituisce le quote dalla cache o le ricarica se scadute"""
    global _quote_cache
    now = time.time()
    if now - _quote_cache['timestamp'] > _QUOTE_CACHE_TTL or not _quote_cache['partite']:
        logger.info("🔄 Ricarico quote...")
        _quote_cache['partite'] = load_quote_from_github()
        _quote_cache['timestamp'] = now
    return _quote_cache['partite']

# ============================================================
# FUNZIONI DI UTILITÀ
# ============================================================

def normalize_date(date_str: str) -> Optional[str]:
    if not date_str:
        return None

    if isinstance(date_str, (int, float)):
        excel_epoch = datetime(1899, 12, 30)
        date = excel_epoch + timedelta(days=float(date_str))
        return date.strftime("%Y-%m-%d")

    date_str = str(date_str).strip()
    if date_str.startswith('20') and '-' in date_str:
        return date_str[:10]

    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"

    try:
        date = pd.to_datetime(date_str)
        return date.strftime("%Y-%m-%d")
    except:
        return None

def format_date_eu(date_str: str) -> str:
    if not date_str:
        return "N/D"
    try:
        date = pd.to_datetime(date_str)
        return date.strftime("%d/%m/%Y")
    except:
        return date_str

def get_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def is_match_future(match: Match) -> bool:
    if match.stato != "Futura":
        return False

    try:
        match_datetime_str = f"{match.data} {match.ora}"
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H", "%Y-%m-%d"]:
            try:
                match_datetime = datetime.strptime(match_datetime_str, fmt)
                if fmt == "%Y-%m-%d":
                    match_datetime = match_datetime.replace(hour=12, minute=0)
                return match_datetime > datetime.now()
            except ValueError:
                continue

        match_date = datetime.strptime(match.data, "%Y-%m-%d")
        return match_date >= datetime.now().date()
    except Exception as e:
        logger.warning(f"Errore nel filtraggio ora per {match.casa} vs {match.ospiti}: {e}")
        try:
            match_date = datetime.strptime(match.data, "%Y-%m-%d")
            return match_date >= datetime.now().date()
        except:
            return True

def format_form(form: str) -> str:
    """Converte la stringa forma (V/P/S) in emoji per Telegram"""
    if not form:
        return '❌'
    return ''.join(['✅' if f == 'V' else '➖' if f == 'P' else '❌' for f in form])

def get_multigol_range(media_gol: float) -> str:
    if media_gol <= 1.0: return "0-2"
    elif media_gol <= 2.5: return "1-3"
    else: return "2-5"

def get_multigol_total_range(media_home: float, media_away: float) -> str:
    media_totale = media_home + media_away
    if media_totale <= 2.0: return "0-2"
    elif media_totale <= 4.0: return "1-3"
    else: return "2-5"

# ============================================================
# CARICAMENTO DATI DAL FILE EXCEL
# ============================================================

def load_excel_from_github() -> Optional[pd.DataFrame]:
    try:
        logger.info(f"📂 Caricamento Excel da: {EXCEL_URL}")
        response = requests.get(EXCEL_URL, timeout=30)

        if response.status_code != 200:
            logger.error(f"❌ HTTP {response.status_code}")
            return None

        df = pd.read_excel(BytesIO(response.content))
        logger.info(f"✅ Caricate {len(df)} righe")
        return df
    except Exception as e:
        logger.error(f"❌ Errore: {e}")
        return None

def find_column(headers: List[str], keywords: List[str]) -> Optional[str]:
    for keyword in keywords:
        for header in headers:
            if keyword.lower() in header.lower():
                return header
    return None

def parse_matches_from_excel(df: pd.DataFrame) -> List[Match]:
    if df is None or df.empty:
        return []

    matches = []
    headers = df.columns.tolist()
    logger.info(f"📋 Colonne: {headers}")

    col_campionato = find_column(headers, ['campionato', 'league', 'camp'])
    col_giornata = find_column(headers, ['giornata', 'round', 'giorn'])
    col_data = find_column(headers, ['data', 'date', 'giorno'])
    col_ora = find_column(headers, ['ora', 'time', 'orario'])
    col_casa = find_column(headers, ['squadra casa', 'home', 'casa'])
    col_ospite = find_column(headers, ['squadra ospite', 'away', 'ospite'])
    col_gol_casa = find_column(headers, ['gol casa', 'home goals'])
    col_gol_ospite = find_column(headers, ['gol ospite', 'away goals'])
    col_risultato = find_column(headers, ['risultato', 'result', 'score'])
    col_stato = find_column(headers, ['stato', 'status'])

    if not col_campionato or not col_data or not col_casa or not col_ospite:
        logger.error("❌ Colonne obbligatorie non trovate!")
        return []

    for idx, row in df.iterrows():
        try:
            campionato = str(row[col_campionato]) if pd.notna(row[col_campionato]) else "Sconosciuto"
            giornata = str(row[col_giornata]) if col_giornata and pd.notna(row[col_giornata]) else "N/A"
            data_raw = str(row[col_data]) if pd.notna(row[col_data]) else ""
            ora_raw = str(row[col_ora]) if col_ora and pd.notna(row[col_ora]) else "TBD"
            casa = str(row[col_casa]) if pd.notna(row[col_casa]) else ""
            ospite = str(row[col_ospite]) if pd.notna(row[col_ospite]) else ""

            if not casa or not ospite:
                continue

            data = normalize_date(data_raw)
            if not data:
                continue

            stato = "Futura"
            gol_casa = 0
            gol_ospite = 0
            risultato = ""

            if col_risultato and pd.notna(row[col_risultato]):
                risultato_raw = str(row[col_risultato]).strip()
                if risultato_raw:
                    match_res = re.search(r'(\d+)\s*[-–:.]\s*(\d+)', risultato_raw)
                    if match_res:
                        gol_casa = int(match_res.group(1))
                        gol_ospite = int(match_res.group(2))
                        risultato = f"{gol_casa}-{gol_ospite}"
                        stato = "Giocata"

            if not risultato and col_gol_casa and col_gol_ospite:
                if pd.notna(row[col_gol_casa]) and pd.notna(row[col_gol_ospite]):
                    try:
                        gol_casa = int(float(row[col_gol_casa]))
                        gol_ospite = int(float(row[col_gol_ospite]))
                        if gol_casa > 0 or gol_ospite > 0:
                            risultato = f"{gol_casa}-{gol_ospite}"
                            stato = "Giocata"
                    except:
                        pass

            if col_stato and pd.notna(row[col_stato]):
                stato_val = str(row[col_stato]).lower().strip()
                if stato_val in ['giocata', 'played', 'finished']:
                    stato = "Giocata"

            match = Match(
                id=f"{idx}_{int(time.time())}",
                campionato=campionato,
                round=giornata,
                data=data,
                ora=ora_raw,
                casa=casa,
                ospiti=ospite,
                stato=stato,
                golCasa=int(gol_casa) if stato == "Giocata" else 0,
                golOspite=int(gol_ospite) if stato == "Giocata" else 0,
                risultato=risultato
            )
            matches.append(match)

        except Exception as e:
            logger.warning(f"Errore riga {idx}: {e}")
            continue

    return matches

# ============================================================
# CALCOLO STATISTICHE
# ============================================================

def calc_form_and_stats(matches: List[Match], team_name: str) -> Dict:
    team_matches = [m for m in matches if m.stato == "Giocata" and (m.casa == team_name or m.ospiti == team_name)]

    if not team_matches:
        return {
            'form': '-----',
            'form_pallini': '🔘🔘🔘🔘🔘',
            'pct': 50,
            'media_gol_fatti': 0,
            'media_gol_subiti': 0,
            'partite': 0
        }

    team_matches.sort(key=lambda m: m.data, reverse=True)
    team_matches = team_matches[:5]

    form = ''
    points = 0
    gol_fatti = 0
    gol_subiti = 0

    for m in team_matches:
        is_home = m.casa == team_name
        team_goals = m.golCasa if is_home else m.golOspite
        opp_goals = m.golOspite if is_home else m.golCasa
        gol_fatti += team_goals
        gol_subiti += opp_goals

        if team_goals > opp_goals:
            form += 'V'
            points += 3
        elif team_goals == opp_goals:
            form += 'P'
            points += 1
        else:
            form += 'S'

    # Costruisci form_pallini
    form_pallini = ''
    for f in form:
        if f == 'V':
            form_pallini += '🟢'
        elif f == 'P':
            form_pallini += '🟡'
        else:
            form_pallini += '🔴'
    while len(form_pallini) < 5:
        form_pallini += '🔘'

    return {
        'form': form or '-----',
        'form_pallini': form_pallini,
        'pct': round((points / (len(team_matches) * 3)) * 100) if team_matches else 50,
        'media_gol_fatti': round(gol_fatti / len(team_matches), 1) if team_matches else 0,
        'media_gol_subiti': round(gol_subiti / len(team_matches), 1) if team_matches else 0,
        'partite': len(team_matches)
    }

def compute_match_stats(match: Match, all_matches: List[Match]) -> Dict:
    home_team = match.casa
    away_team = match.ospiti

    home_games = [m for m in all_matches if m.stato == "Giocata" and (m.casa == home_team or m.ospiti == home_team)]
    away_games = [m for m in all_matches if m.stato == "Giocata" and (m.casa == away_team or m.ospiti == away_team)]

    all_games_map = {}
    for g in home_games + away_games:
        all_games_map[g.id] = g
    all_games = list(all_games_map.values())

    if len(all_games) < 3:
        return {'error': 'Poche partite per queste squadre.'}

    home_wins = home_draws = home_losses = 0
    away_wins = away_draws = away_losses = 0

    for g in home_games:
        is_home = g.casa == home_team
        team_goals = g.golCasa if is_home else g.golOspite
        opp_goals = g.golOspite if is_home else g.golCasa
        if team_goals > opp_goals:
            home_wins += 1
        elif team_goals == opp_goals:
            home_draws += 1
        else:
            home_losses += 1

    for g in away_games:
        is_home = g.casa == away_team
        team_goals = g.golCasa if is_home else g.golOspite
        opp_goals = g.golOspite if is_home else g.golCasa
        if team_goals > opp_goals:
            away_wins += 1
        elif team_goals == opp_goals:
            away_draws += 1
        else:
            away_losses += 1

    total = len(all_games)
    p1 = ((home_wins + away_losses) / total) * 100 if total > 0 else 0
    pX = ((home_draws + away_draws) / total) * 100 if total > 0 else 0
    p2 = ((home_losses + away_wins) / total) * 100 if total > 0 else 0
    p1X = ((home_wins + home_draws) / total) * 100 if total > 0 else 0
    p12 = ((home_wins + away_wins) / total) * 100 if total > 0 else 0
    pX2 = ((home_losses + away_wins) / total) * 100 if total > 0 else 0

    goal_totals = [g.golCasa + g.golOspite for g in all_games]
    thresholds = [1.5, 2.5, 3.5, 4.5]
    under_over = []
    for t in thresholds:
        over = sum(1 for gt in goal_totals if gt > t) / len(goal_totals) * 100 if goal_totals else 0
        under = 100 - over
        under_over.append({'threshold': t, 'under': round(under), 'over': round(over)})

    gg = sum(1 for g in all_games if g.golCasa > 0 and g.golOspite > 0) / len(all_games) * 100 if all_games else 0
    ng = 100 - gg

    return {
        'p1': round(p1), 'pX': round(pX), 'p2': round(p2),
        'p1X': round(p1X), 'p12': round(p12), 'pX2': round(pX2),
        'gg': round(gg), 'ng': round(ng),
        'under_over': under_over, 'total_games': total
    }

# ============================================================
# CALCOLO GIOCATA
# ============================================================

def get_giocata_pct(giocata: str, stats: Dict, home_media_gol: float = None, away_media_gol: float = None) -> int:
    if stats.get('error'):
        return 0

    p1 = stats.get('p1', 0)
    pX = stats.get('pX', 0)
    p2 = stats.get('p2', 0)
    p1X = stats.get('p1X', 0)
    p12 = stats.get('p12', 0)
    pX2 = stats.get('pX2', 0)
    gg = stats.get('gg', 0)
    ng = stats.get('ng', 0)
    under_over = stats.get('under_over', [])

    # MG CASA+OSPITE (es. 0-2+1-3)
    if '+' in giocata and '-' in giocata:
        parts = giocata.split('+')
        if len(parts) == 2 and '-' in parts[0] and '-' in parts[1]:
            if home_media_gol is not None and away_media_gol is not None:
                home_range = get_multigol_range(home_media_gol)
                away_range = get_multigol_range(away_media_gol)
                expected = f"{home_range}+{away_range}"
                if giocata == expected:
                    return 90

                h1, h2 = giocata.split('+')[0].split('-')
                a1, a2 = giocata.split('+')[1].split('-')
                eh1, eh2 = home_range.split('-')
                ea1, ea2 = away_range.split('-')

                diff = (abs(int(h1) - int(eh1)) + abs(int(h2) - int(eh2)) +
                        abs(int(a1) - int(ea1)) + abs(int(a2) - int(ea2)))

                if diff == 0:
                    return 90
                elif diff <= 2:
                    return 80
                elif diff <= 4:
                    return 65
                elif diff <= 6:
                    return 50
                else:
                    return 35
        return 50

    # MULTIGOL TOTALE
    if giocata in ['0-2', '1-3', '2-5']:
        if home_media_gol is not None and away_media_gol is not None:
            expected = get_multigol_total_range(home_media_gol, away_media_gol)
            if giocata == expected:
                return 85
            g1, g2 = giocata.split('-')
            e1, e2 = expected.split('-')
            diff = abs(int(g1) - int(e1)) + abs(int(g2) - int(e2))
            if diff <= 2:
                return 70
            elif diff <= 4:
                return 50
            else:
                return 30
        return 50

    # DC+MULTIGOL
    if giocata.startswith('1X+') and giocata[3:] in ['0-2', '1-3', '2-5']:
        multigol_pct = get_giocata_pct(giocata[3:], stats, home_media_gol, away_media_gol)
        return round((p1X + multigol_pct) / 2)
    if giocata.startswith('12+') and giocata[3:] in ['0-2', '1-3', '2-5']:
        multigol_pct = get_giocata_pct(giocata[3:], stats, home_media_gol, away_media_gol)
        return round((p12 + multigol_pct) / 2)
    if giocata.startswith('X2+') and giocata[3:] in ['0-2', '1-3', '2-5']:
        multigol_pct = get_giocata_pct(giocata[3:], stats, home_media_gol, away_media_gol)
        return round((pX2 + multigol_pct) / 2)

    # GIOCATE STANDARD
    if giocata == '1': return p1
    if giocata == 'X': return pX
    if giocata == '2': return p2
    if giocata == '1X': return p1X
    if giocata == '12': return p12
    if giocata == 'X2': return pX2
    if giocata == 'GG': return gg
    if giocata == 'NG': return ng
    if giocata == 'Over 1.5': return under_over[0]['over'] if len(under_over) > 0 else 0
    if giocata == 'Over 2.5': return under_over[1]['over'] if len(under_over) > 1 else 0
    if giocata == 'Under 1.5': return under_over[0]['under'] if len(under_over) > 0 else 0
    if giocata == 'Under 2.5': return under_over[1]['under'] if len(under_over) > 1 else 0
    if giocata == 'Under 3.5': return under_over[2]['under'] if len(under_over) > 2 else 0
    if giocata == 'Under 4.5': return under_over[3]['under'] if len(under_over) > 3 else 0

    # DC+OVER / DC+UNDER
    if giocata.startswith('1X+O'):
        over = giocata.replace('1X+O', 'Over ')
        return round((p1X + get_giocata_pct(over, stats)) / 2)
    if giocata.startswith('12+O'):
        over = giocata.replace('12+O', 'Over ')
        return round((p12 + get_giocata_pct(over, stats)) / 2)
    if giocata.startswith('X2+O'):
        over = giocata.replace('X2+O', 'Over ')
        return round((pX2 + get_giocata_pct(over, stats)) / 2)

    if giocata.startswith('1X+U'):
        under = giocata.replace('1X+U', 'Under ')
        return round((p1X + get_giocata_pct(under, stats)) / 2)
    if giocata.startswith('12+U'):
        under = giocata.replace('12+U', 'Under ')
        return round((p12 + get_giocata_pct(under, stats)) / 2)
    if giocata.startswith('X2+U'):
        under = giocata.replace('X2+U', 'Under ')
        return round((pX2 + get_giocata_pct(under, stats)) / 2)

    return 0

def get_best_bet_for_family(family_id: str, stats: Dict, home_media_gol: float = None, away_media_gol: float = None) -> Optional[Dict]:
    family = FAMIGLIE_GIOCATE.get(family_id)
    if not family:
        return None

    best = None
    best_pct = -1

    for opt in family['options']:
        pct = get_giocata_pct(opt, stats, home_media_gol, away_media_gol)
        if pct > best_pct:
            best_pct = pct
            best = {'giocata': opt, 'pct': pct}

    if best and best['pct'] > 0:
        return {
            'giocata': best['giocata'],
            'pct': best['pct'],
            'is_bomb': best['pct'] >= 90,
            'family_label': family['label']
        }

    return None

def analyze_matches(matches: List[Match], family_ids: List[str], days_range: int,
                    partite_quote: List[Dict] = None) -> List[MatchAnalysis]:
    if partite_quote is None:
        partite_quote = []

    future_matches = [m for m in matches if m.stato == "Futura"]
    today = get_today_str()
    limit_date = (datetime.now() + timedelta(days=days_range)).strftime("%Y-%m-%d")
    future_matches = [m for m in future_matches if m.data >= today and m.data <= limit_date]
    future_matches = [m for m in future_matches if is_match_future(m)]

    logger.info(f"🔍 Trovate {len(future_matches)} partite future fino al {limit_date}")

    results = []

    for match in future_matches:
        stats = compute_match_stats(match, matches)
        if stats.get('error'):
            continue

        home_form = calc_form_and_stats(matches, match.casa)
        away_form = calc_form_and_stats(matches, match.ospiti)

        giocate = []

        for family_id in family_ids:
            family = FAMIGLIE_GIOCATE.get(family_id)
            if not family:
                continue

            best = get_best_bet_for_family(
                family_id, stats,
                home_media_gol=home_form['media_gol_fatti'],
                away_media_gol=away_form['media_gol_fatti']
            )
            if not best:
                continue

            # Quota e value bet (quota None se non trovata)
            quota = trova_quota_per_giocata(match, family_id, best['giocata'], partite_quote)
            edge = quota_fair = kelly = classificazione = None
            if quota:
                vb = calcola_value_bet(best['pct'], quota)
                edge = vb['edge']
                quota_fair = vb['quota_fair']
                kelly = vb['kelly']
                classificazione = vb['classificazione']

            giocate.append(Giocata(
                famiglia=family['label'],
                family_id=family_id,
                label=best['giocata'],
                pct=best['pct'],
                is_bomb=best['is_bomb'],
                quota=quota,
                edge=edge,
                quota_fair=quota_fair,
                kelly=kelly,
                classificazione=classificazione,
            ))

        if not giocate:
            continue

        giocate.sort(key=lambda x: x.pct, reverse=True)
        score = round(sum(g.pct for g in giocate) / len(giocate))
        has_bomb = any(g.is_bomb for g in giocate)

        results.append(MatchAnalysis(
            match=match,
            giocate=giocate,
            score=score,
            has_bomb=has_bomb,
            home_form=home_form,
            away_form=away_form
        ))

    results.sort(key=lambda x: x.score, reverse=True)
    logger.info(f"✅ Analizzate {len(results)} partite")
    return results

# ============================================================
# INVIO MESSAGGI TELEGRAM
# ============================================================

def send_telegram_message(chat_id: str, text: str, parse_mode: str = 'HTML', reply_markup: dict = None) -> bool:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            logger.error(f"❌ Errore invio: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Errore: {e}")
        return False

def create_inline_keyboard(buttons: List[Dict[str, str]]) -> dict:
    keyboard = []
    row = []
    for button in buttons:
        row.append({'text': button['text'], 'callback_data': button['callback_data']})
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return {'inline_keyboard': keyboard}

def create_family_keyboard(selected: str = None) -> dict:
    buttons = []
    for family_id, label in FAMIGLIE_LIST:
        if family_id == selected:
            label = f"✅ {label}"
        buttons.append({'text': label, 'callback_data': f"fam_{family_id}"})
    return create_inline_keyboard(buttons)

def create_days_keyboard() -> dict:
    buttons = []
    for days in range(1, 6):
        buttons.append({'text': f"{days} giorni", 'callback_data': f"days_{days}"})
    return create_inline_keyboard(buttons)

def create_count_keyboard() -> dict:
    buttons = []
    for count in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        buttons.append({'text': str(count), 'callback_data': f"count_{count}"})
    buttons.append({'text': '✅ CONFERMA', 'callback_data': 'count_confirm'})
    return create_inline_keyboard(buttons)

# ============================================================
# GENERAZIONE REPORT
# ============================================================

def generate_report(analyses: List[MatchAnalysis], count: int, family_ids: List[str]) -> str:
    if not analyses:
        return "<b>📅 Nessuna partita trovata nei giorni selezionati.</b>"

    top = analyses[:count]

    lines = []
    lines.append("📊 <b>GesssAI-Pro - Report Partite</b>")
    lines.append(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    lines.append(f"🏟️ {len(top)} partite su {len(analyses)} trovate")
    lines.append("")
    lines.append("━" * 30)
    lines.append("")

    for i, analysis in enumerate(top, 1):
        match = analysis.match

        lines.append(f"<b>#{i} - {match.campionato}</b>")
        lines.append(f"📅 {format_date_eu(match.data)} - ⏰ {match.ora}")
        lines.append(f"<b>⚔️ {match.casa} vs {match.ospiti}</b>")
        lines.append(f"📊 Forma: {match.casa} {format_form(analysis.home_form['form'])} ({analysis.home_form['pct']}%) | {match.ospiti} {format_form(analysis.away_form['form'])} ({analysis.away_form['pct']}%)")
        lines.append(f"⚽ xG: {match.casa} {analysis.home_form['media_gol_fatti']} | {match.ospiti} {analysis.away_form['media_gol_fatti']}")
        lines.append("")

        # Mostra le giocate raggruppate per famiglia (una per colonna)
        for idx_col, family_id in enumerate(family_ids, 1):
            family_label = FAMIGLIE_GIOCATE.get(family_id, {}).get('label', family_id)
            # Trova la giocata corrispondente in questa analisi
            g = next((gg for gg in analysis.giocate if gg.family_id == family_id), None)
            if not g:
                continue

            if g.pct >= 90:
                emoji = '💣'
            elif g.pct >= 67:
                emoji = '🟢'
            elif g.pct >= 34:
                emoji = '⚪'
            else:
                emoji = '🔴'

            bomb = ' 💣' if g.is_bomb else ''

            lines.append(f"🎯 <b>Colonna {idx_col} - {family_label}</b>: {g.label} {emoji} <b>{g.pct}%</b>{bomb}")

            if g.quota:
                edge_str = f"{g.edge:+.1f}%" if g.edge is not None else "N/D"
                edge_emoji = "💎" if g.edge and g.edge > 20 else "✅" if g.edge and g.edge > 10 else "🟡" if g.edge and g.edge > 5 else "⚪"
                lines.append(f"💰 Quota: <b>{g.quota}</b> | Fair: {g.quota_fair} | Edge: {edge_str} {edge_emoji}")
                if g.kelly and g.kelly > 0:
                    lines.append(f"📈 Kelly: {g.kelly}%")
                if g.classificazione and g.edge and g.edge > 5:
                    lines.append(f"{g.classificazione}")
            else:
                lines.append("💰 Quota: non disponibile (uso 1.00 per il calcolo colonna)")

        lines.append("")
        lines.append(f"📊 Score: {analysis.score}%")

        if analysis.has_bomb:
            lines.append("💣 <b>BOMBA!</b>")

        if i < len(top):
            lines.append("")
            lines.append("─" * 30)
            lines.append("")

    # ============================================================
    # SEZIONE QUOTE TOTALI PER COLONNA
    # ============================================================
    lines.append("")
    lines.append("━" * 30)
    lines.append("🎫 <b>QUOTE TOTALI PER COLONNA</b>")
    lines.append("━" * 30)
    lines.append("")

    colonne_stats = []

    for idx_col, family_id in enumerate(family_ids, 1):
        family_label = FAMIGLIE_GIOCATE.get(family_id, {}).get('label', family_id)

        # Raccogli tutte le giocate di questa colonna dalle top partite
        giocate_colonna = []
        for analysis in top:
            g = next((gg for gg in analysis.giocate if gg.family_id == family_id), None)
            if g:
                giocate_colonna.append({
                    'quota': g.quota,
                    'pct': g.pct,
                })

        if not giocate_colonna:
            continue

        stats_col = calcola_quota_colonna(giocate_colonna)
        colonne_stats.append(stats_col)

        lines.append(f"🎯 <b>COLONNA {idx_col} - {family_label}</b>")
        lines.append(f"Partite: {stats_col['n_partite']}")
        lines.append(f"💰 Quota totale: <b>{stats_col['quota_totale']}</b>")
        lines.append(f"📊 Probabilità combinata: {stats_col['prob_combinata']}%")
        lines.append(f"📈 Edge: {stats_col['edge']:+.1f}%")
        if stats_col['kelly'] > 0:
            lines.append(f"📈 Kelly: {stats_col['kelly']}%")
        lines.append(f"{stats_col['classificazione']}")
        if stats_col['n_quote_mancanti'] > 0:
            lines.append(f"⚠️ {stats_col['n_quote_mancanti']} quote mancanti (sostituite con 1.00)")
        lines.append("")

    # Sistema completo (3 colonne insieme)
    if colonne_stats:
        sistema = calcola_quota_sistema(colonne_stats)
        lines.append("━" * 30)
        lines.append("🔥 <b>SISTEMA COMPLETO (tutte le colonne)</b>")
        lines.append(f"💰 Quota sistema: <b>{sistema['quota_sistema']}</b>")
        lines.append(f"📊 Probabilità sistema: {sistema['prob_sistema']}%")
        lines.append(f"📈 Edge: {sistema['edge_sistema']:+.1f}%")
        if sistema['kelly_sistema'] > 0:
            lines.append(f"📈 Kelly: {sistema['kelly_sistema']}%")
        lines.append(f"{sistema['classificazione']}")
        lines.append("━" * 30)

    return "\n".join(lines)

# ============================================================
# GESTIONE STATO UTENTE
# ============================================================

class UserState:
    def __init__(self):
        self.step = 'start'
        self.selected_families = []
        self.selected_days = 3
        self.selected_count = 5

# ============================================================
# GESTIONE COMANDI
# ============================================================

def handle_start(chat_id: str):
    user_states[chat_id] = UserState()

    text = """<b>🤖 GesssAI-Pro Bot</b>

Benvenuto! Scegli <b>3 famiglie</b> di giocate e ti mostrerò le migliori partite con <b>quote e value bet</b>.

<b>📋 Come funziona:</b>

1️⃣ <b>Scegli 3 famiglie</b> (una per colonna)
2️⃣ <b>Scegli il range di giorni</b> (1-5)
3️⃣ <b>Scegli quante partite</b> vedere (1-10)

💎 <b>Value Bet</b>: edge > 20%
✅ <b>Buon value</b>: edge > 10%
🟡 <b>Marginale</b>: edge > 5%

🎫 <b>In fondo al report</b> troverai le quote totali di ogni colonna e del sistema completo!"""

    keyboard = create_inline_keyboard([{'text': '🎯 INIZIA', 'callback_data': 'start_setup'}])
    send_telegram_message(chat_id, text, reply_markup=keyboard)

def handle_start_setup(chat_id: str):
    if chat_id not in user_states:
        user_states[chat_id] = UserState()

    state = user_states[chat_id]
    state.step = 'selecting_family'
    state.selected_families = []

    text = """<b>🎯 Colonna 1 (di 3)</b>

Scegli la prima famiglia di giocate."""

    keyboard = create_family_keyboard()
    send_telegram_message(chat_id, text, reply_markup=keyboard)

def handle_family_selection(chat_id: str, family_id: str):
    if chat_id not in user_states:
        return

    state = user_states[chat_id]

    if family_id in state.selected_families:
        send_telegram_message(chat_id, "⚠️ Hai già scelto questa famiglia! Scegline un'altra.")
        return

    state.selected_families.append(family_id)
    n = len(state.selected_families)

    if n == 1:
        text = f"<b>✅ Colonna 1: {FAMIGLIE_GIOCATE[family_id]['label']}</b>\n\n🎯 <b>Colonna 2 (di 3)</b>\n\nScegli la seconda famiglia."
        keyboard = create_family_keyboard(selected=None)
        send_telegram_message(chat_id, text, reply_markup=keyboard)

    elif n == 2:
        text = (f"<b>✅ Colonna 1: {FAMIGLIE_GIOCATE[state.selected_families[0]]['label']}</b>\n"
                f"<b>✅ Colonna 2: {FAMIGLIE_GIOCATE[family_id]['label']}</b>\n\n"
                f"🎯 <b>Colonna 3 (di 3)</b>\n\nScegli la terza famiglia.")
        keyboard = create_family_keyboard(selected=None)
        send_telegram_message(chat_id, text, reply_markup=keyboard)

    elif n == 3:
        state.step = 'selecting_days'
        text = (f"<b>✅ Colonna 1: {FAMIGLIE_GIOCATE[state.selected_families[0]]['label']}</b>\n"
                f"<b>✅ Colonna 2: {FAMIGLIE_GIOCATE[state.selected_families[1]]['label']}</b>\n"
                f"<b>✅ Colonna 3: {FAMIGLIE_GIOCATE[family_id]['label']}</b>\n\n"
                f"📅 Scegli il <b>range di giorni</b> (1-5).")
        keyboard = create_days_keyboard()
        send_telegram_message(chat_id, text, reply_markup=keyboard)

def handle_days_selection(chat_id: str, days: int):
    if chat_id not in user_states:
        return

    state = user_states[chat_id]
    state.selected_days = days
    state.step = 'selecting_count'

    text = f"""<b>📅 Range giorni: {days} giorni</b>

Scegli <b>quante partite</b> vedere (1-10)."""

    keyboard = create_count_keyboard()
    send_telegram_message(chat_id, text, reply_markup=keyboard)

def handle_count_selection(chat_id: str, count: int):
    if chat_id not in user_states:
        return

    state = user_states[chat_id]
    state.selected_count = count

    send_telegram_message(chat_id, "⏳ <b>Caricamento Excel...</b>")

    try:
        df = load_excel_from_github()
        if df is None:
            send_telegram_message(chat_id, "❌ <b>Errore:</b> Impossibile caricare il file Excel.")
            return

        matches = parse_matches_from_excel(df)
        if not matches:
            send_telegram_message(chat_id, "❌ <b>Errore:</b> Nessuna partita trovata nel file.")
            return

        logger.info(f"📊 Caricate {len(matches)} partite totali")

        send_telegram_message(chat_id, "⏳ <b>Caricamento quote PDF...</b>")

        try:
            partite_quote = get_quote_cached()
            logger.info(f"💰 Quote disponibili per {len(partite_quote)} partite")
            if not partite_quote:
                send_telegram_message(chat_id, "⚠️ <b>Attenzione:</b> Quote non disponibili. Procedo senza value bet.")
        except Exception as e:
            logger.error(f"❌ Errore quote: {e}")
            partite_quote = []
            send_telegram_message(chat_id, f"⚠️ <b>Quote non disponibili:</b> {str(e)[:100]}")

        send_telegram_message(chat_id, "⏳ <b>Analisi in corso...</b>")

        analyses = analyze_matches(matches, state.selected_families, state.selected_days, partite_quote)

        if not analyses:
            send_telegram_message(chat_id, f"📅 <b>Nessuna partita nei prossimi {state.selected_days} giorni.</b>")
            return

        report = generate_report(analyses, count, state.selected_families)

        if len(report) > 4000:
            chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
            for chunk in chunks:
                send_telegram_message(chat_id, chunk)
        else:
            send_telegram_message(chat_id, report)

        keyboard = create_inline_keyboard([
            {'text': '🔄 NUOVA RICERCA', 'callback_data': 'new_search'}
        ])
        send_telegram_message(chat_id, "✅ <b>Analisi completata!</b>", reply_markup=keyboard)

    except Exception as e:
        error_msg = f"❌ <b>Errore:</b> {str(e)}"
        logger.error(f"Errore: {e}\n{traceback.format_exc()}")
        send_telegram_message(chat_id, error_msg)

def handle_new_search(chat_id: str):
    if chat_id in user_states:
        user_states[chat_id] = UserState()
    handle_start_setup(chat_id)

# ============================================================
# HANDLER UPDATE
# ============================================================

def handle_update(update: dict):
    try:
        if 'message' in update:
            message = update['message']
            chat_id = str(message['chat']['id'])

            if 'text' in message:
                text = message['text']
                if text == '/start':
                    handle_start(chat_id)
                else:
                    send_telegram_message(chat_id, "❓ Usa /start per iniziare")

        elif 'callback_query' in update:
            callback = update['callback_query']
            chat_id = str(callback['message']['chat']['id'])
            data = callback['data']

            try:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery",
                              json={'callback_query_id': callback['id']}, timeout=5)
            except:
                pass

            if data == 'start_setup':
                handle_start_setup(chat_id)
            elif data == 'new_search':
                handle_new_search(chat_id)
            elif data == 'count_confirm':
                if chat_id in user_states and user_states[chat_id].selected_count:
                    handle_count_selection(chat_id, user_states[chat_id].selected_count)
                else:
                    send_telegram_message(chat_id, "⚠️ Seleziona prima il numero di partite!")
            elif data.startswith('fam_'):
                family_id = data[4:]
                if family_id in FAMIGLIE_GIOCATE:
                    handle_family_selection(chat_id, family_id)
            elif data.startswith('days_'):
                days = int(data[5:])
                handle_days_selection(chat_id, days)
            elif data.startswith('count_'):
                count = int(data[6:])
                if chat_id in user_states:
                    state = user_states[chat_id]
                    state.selected_count = count
                    text = f"""<b>🔢 Numero partite: {count}</b>
Range giorni: {state.selected_days} giorni

Clicca su un numero per cambiare, poi <b>✅ CONFERMA</b>"""
                    keyboard = create_count_keyboard()
                    send_telegram_message(chat_id, text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Errore handle_update: {e}")

# ============================================================
# POLLING
# ============================================================

def run_polling():
    logger.info("🔄 Avvio bot...")
    logger.info(f"📂 Excel: {EXCEL_URL}")
    offset = None

    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            params = {'timeout': 30}
            if offset:
                params['offset'] = offset

            response = requests.get(url, params=params, timeout=35)
            response.raise_for_status()

            updates = response.json().get('result', [])

            for update in updates:
                handle_update(update)
                offset = update['update_id'] + 1

            if not updates:
                time.sleep(1)

        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            logger.error(f"Errore polling: {e}")
            time.sleep(5)

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("🤖 GesssAI-Pro Telegram Bot")
    print("=" * 40)
    print(f"📂 Excel: {EXCEL_URL}")
    print("")
    print("In attesa di messaggi...")
    print("Premi CTRL+C per fermare")
    print("=" * 40)

    try:
        run_polling()
    except KeyboardInterrupt:
        print("\n👋 Bot fermato")