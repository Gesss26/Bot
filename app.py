from flask import Flask, request, jsonify
import requests
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import pandas as pd
from io import BytesIO
import re
import time
import traceback

from quote_utils import (
    load_quote_from_github,
    trova_quota_per_giocata,
    get_quota_or_fallback,
    calcola_value_bet,
    calcola_quota_colonna,
    calcola_quota_sistema,
)

# ============================================================
# CREAZIONE APP FLASK
# ============================================================

app = Flask(__name__)

# ============================================================
# CONFIGURAZIONE
# ============================================================

TOKEN = "8889221419:AAEgOICSM7aLhVGBoFEDs8e-CKW5zKCExVc"
EXCEL_URL = "https://raw.githubusercontent.com/Gesss26/GesssAI-Pro---Auto/master/excel/GesssAI_Input.xlsx"
SPLASH_URL = "https://raw.githubusercontent.com/Gesss26/Bot/main/Splashscreen.png"

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(level=logging.INFO)
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
_QUOTE_CACHE_TTL = 3600

def get_quote_cached() -> List[Dict]:
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
        logger.warning(f"Errore filtraggio ora {match.casa} vs {match.ospiti}: {e}")
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
# CARICAMENTO DATI
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
        if team_goals > opp_goals: home_wins += 1
        elif team_goals == opp_goals: home_draws += 1
        else: home_losses += 1

    for g in away_games:
        is_home = g.casa == away_team
        team_goals = g.golCasa if is_home else g.golOspite
        opp_goals = g.golOspite if is_home else g.golCasa
        if team_goals > opp_goals: away_wins += 1
        elif team_goals == opp_goals: away_draws += 1
        else: away_losses += 1

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

def get_giocata_pct(giocata: str, stats: Dict, home_media_gol: float = None, away_media_gol: float = None) -> int:
    if stats.get('error'):
        return 0

    p1 = stats.get('p1', 0); pX = stats.get('pX', 0); p2 = stats.get('p2', 0)
    p1X = stats.get('p1X', 0); p12 = stats.get('p12', 0); pX2 = stats.get('pX2', 0)
    gg = stats.get('gg', 0); ng = stats.get('ng', 0)
    under_over = stats.get('under_over', [])

    # MG CASA+OSPITE
    if '+' in giocata and '-' in giocata:
        parts = giocata.split('+')
        if len(parts) == 2 and '-' in parts[0] and '-' in parts[1]:
            if home_media_gol is not None and away_media_gol is not None:
                home_range = get_multigol_range(home_media_gol)
                away_range = get_multigol_range(away_media_gol)
                expected = f"{home_range}+{away_range}"
                if giocata == expected: return 90
                h1, h2 = giocata.split('+')[0].split('-')
                a1, a2 = giocata.split('+')[1].split('-')
                eh1, eh2 = home_range.split('-')
                ea1, ea2 = away_range.split('-')
                diff = (abs(int(h1)-int(eh1)) + abs(int(h2)-int(eh2)) + abs(int(a1)-int(ea1)) + abs(int(a2)-int(ea2)))
                if diff == 0: return 90
                elif diff <= 2: return 80
                elif diff <= 4: return 65
                elif diff <= 6: return 50
                else: return 35
        return 50

    # MULTIGOL TOTALE
    if giocata in ['0-2', '1-3', '2-5']:
        if home_media_gol is not None and away_media_gol is not None:
            expected = get_multigol_total_range(home_media_gol, away_media_gol)
            if giocata == expected: return 85
            g1, g2 = giocata.split('-')
            e1, e2 = expected.split('-')
            diff = abs(int(g1)-int(e1)) + abs(int(g2)-int(e2))
            if diff <= 2: return 70
            elif diff <= 4: return 50
            else: return 30
        return 50

    # DC+MULTIGOL
    if giocata.startswith('1X+') and giocata[3:] in ['0-2', '1-3', '2-5']:
        return round((p1X + get_giocata_pct(giocata[3:], stats, home_media_gol, away_media_gol)) / 2)
    if giocata.startswith('12+') and giocata[3:] in ['0-2', '1-3', '2-5']:
        return round((p12 + get_giocata_pct(giocata[3:], stats, home_media_gol, away_media_gol)) / 2)
    if giocata.startswith('X2+') and giocata[3:] in ['0-2', '1-3', '2-5']:
        return round((pX2 + get_giocata_pct(giocata[3:], stats, home_media_gol, away_media_gol)) / 2)

    # STANDARD
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
        return round((p1X + get_giocata_pct(giocata.replace('1X+O', 'Over '), stats)) / 2)
    if giocata.startswith('12+O'):
        return round((p12 + get_giocata_pct(giocata.replace('12+O', 'Over '), stats)) / 2)
    if giocata.startswith('X2+O'):
        return round((pX2 + get_giocata_pct(giocata.replace('X2+O', 'Over '), stats)) / 2)
    if giocata.startswith('1X+U'):
        return round((p1X + get_giocata_pct(giocata.replace('1X+U', 'Under '), stats)) / 2)
    if giocata.startswith('12+U'):
        return round((p12 + get_giocata_pct(giocata.replace('12+U', 'Under '), stats)) / 2)
    if giocata.startswith('X2+U'):
        return round((pX2 + get_giocata_pct(giocata.replace('X2+U', 'Under '), stats)) / 2)

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

    if days_range == 1:
        future_matches = [m for m in future_matches if m.data == today]
    else:
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
            match=match, giocate=giocate, score=score, has_bomb=has_bomb,
            home_form=home_form, away_form=away_form
        ))

    results.sort(key=lambda x: x.score, reverse=True)
    logger.info(f"✅ Analizzate {len(results)} partite")
    return results

# ============================================================
# GENERAZIONE REPORT (Markdown)
# ============================================================

def generate_report(analyses: List[MatchAnalysis], count: int, family_ids: List[str]) -> str:
    if not analyses:
        return "📅 Nessuna partita trovata nei giorni selezionati."

    top = analyses[:count]
    lines = []
    lines.append("📊 *GesssAI-Pro*")
    lines.append(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    lines.append(f"🏟️ {len(top)} partite")
    lines.append("")
    lines.append("─" * 25)
    lines.append("")

    for i, analysis in enumerate(top, 1):
        match = analysis.match

        lines.append(f"*#{i} {match.campionato}*")
        lines.append(f"📅 {format_date_eu(match.data)} {match.ora}")
        lines.append("")
        lines.append(f"🏠 {match.casa}")
        lines.append(f"✈️ {match.ospiti}")
        lines.append("")
        lines.append(f"📊 {match.casa}")
        lines.append(f"{analysis.home_form['form_pallini']} = {analysis.home_form['pct']}%")
        lines.append("")
        lines.append(f"⚽️ Media gol: {analysis.home_form['media_gol_fatti']} - Fascia: {get_multigol_range(analysis.home_form['media_gol_fatti'])}")
        lines.append("")
        lines.append(f"📊 {match.ospiti}")
        lines.append(f"{analysis.away_form['form_pallini']} = {analysis.away_form['pct']}%")
        lines.append("")
        lines.append(f"⚽️ Media gol: {analysis.away_form['media_gol_fatti']} - Fascia: {get_multigol_range(analysis.away_form['media_gol_fatti'])}")
        lines.append("")
        lines.append(f"⚽️ xG: {analysis.home_form['media_gol_fatti']} - {analysis.away_form['media_gol_fatti']}")
        lines.append("")

        # Mostra le giocate per colonna
        for idx_col, family_id in enumerate(family_ids, 1):
            family_label = FAMIGLIE_GIOCATE.get(family_id, {}).get('label', family_id)
            g = next((gg for gg in analysis.giocate if gg.family_id == family_id), None)
            if not g:
                continue

            if g.pct >= 90: emoji = '💣'
            elif g.pct >= 67: emoji = '🟢'
            elif g.pct >= 34: emoji = '🟡'
            else: emoji = '🔴'

            bomb = ' 💣' if g.is_bomb else ''
            lines.append(f"🎯 Colonna {idx_col} - {family_label}: {g.label} {emoji} *{g.pct}%*{bomb}")

            if g.quota:
                edge_str = f"{g.edge:+.1f}%" if g.edge is not None else "N/D"
                edge_emoji = "💎" if g.edge and g.edge > 20 else "✅" if g.edge and g.edge > 10 else "🟡" if g.edge and g.edge > 5 else "⚪"
                lines.append(f"💰 Quota: {g.quota} | Fair: {g.quota_fair} | Edge: {edge_str} {edge_emoji}")
                if g.kelly and g.kelly > 0:
                    lines.append(f"📈 Kelly: {g.kelly}%")
                if g.classificazione and g.edge and g.edge > 5:
                    lines.append(f"{g.classificazione}")
            else:
                lines.append("💰 Quota: non disponibile")

        lines.append("")
        lines.append(f"📊 Score: *{analysis.score}%*")
        if analysis.has_bomb:
            lines.append("💣 *BOMBA!*")

        if i < len(top):
            lines.append("")
            lines.append("─" * 25)
            lines.append("")

    # ============================================================
    # SEZIONE QUOTE TOTALI PER COLONNA
    # ============================================================
    lines.append("")
    lines.append("━" * 25)
    lines.append("🎫 *QUOTE TOTALI PER COLONNA*")
    lines.append("━" * 25)
    lines.append("")

    colonne_stats = []

    for idx_col, family_id in enumerate(family_ids, 1):
        family_label = FAMIGLIE_GIOCATE.get(family_id, {}).get('label', family_id)

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

        lines.append(f"🎯 *COLONNA {idx_col} - {family_label}*")
        lines.append(f"Partite: {stats_col['n_partite']}")
        lines.append(f"💰 Quota totale: *{stats_col['quota_totale']}*")
        lines.append(f"📊 Probabilità combinata: {stats_col['prob_combinata']}%")
        lines.append(f"📈 Edge: {stats_col['edge']:+.1f}%")
        if stats_col['kelly'] > 0:
            lines.append(f"📈 Kelly: {stats_col['kelly']}%")
        lines.append(f"{stats_col['classificazione']}")
        if stats_col['n_quote_mancanti'] > 0:
            lines.append(f"⚠️ {stats_col['n_quote_mancanti']} quote mancanti (1.00)")
        lines.append("")

    if colonne_stats:
        sistema = calcola_quota_sistema(colonne_stats)
        lines.append("━" * 25)
        lines.append("🔥 *SISTEMA COMPLETO (tutte le colonne)*")
        lines.append(f"💰 Quota sistema: *{sistema['quota_sistema']}*")
        lines.append(f"📊 Probabilità sistema: {sistema['prob_sistema']}%")
        lines.append(f"📈 Edge: {sistema['edge_sistema']:+.1f}%")
        if sistema['kelly_sistema'] > 0:
            lines.append(f"📈 Kelly: {sistema['kelly_sistema']}%")
        lines.append(f"{sistema['classificazione']}")
        lines.append("━" * 25)

    return "\n".join(lines)

# ============================================================
# FUNZIONI TELEGRAM
# ============================================================

def send_message(chat_id: str, text: str, parse_mode: str = 'Markdown', reply_markup: dict = None) -> bool:
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
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return {'inline_keyboard': keyboard}

def create_family_keyboard() -> dict:
    buttons = []
    for family_id, label in FAMIGLIE_LIST:
        buttons.append({'text': label, 'callback_data': f"fam_{family_id}"})
    return create_inline_keyboard(buttons)

def create_days_keyboard() -> dict:
    buttons = [{'text': f"{days} giorni", 'callback_data': f"days_{days}"} for days in range(1, 6)]
    return create_inline_keyboard(buttons)

def create_count_keyboard() -> dict:
    buttons = [{'text': str(count), 'callback_data': f"count_{count}"} for count in [1, 2, 3, 4, 5, 6, 7, 8, 9]]
    buttons.append({'text': '10', 'callback_data': 'count_10'})
    buttons.append({'text': '✅ CONFERMA', 'callback_data': 'count_confirm'})
    return create_inline_keyboard(buttons)

# ============================================================
# SPLASHSCREEN
# ============================================================

def send_splashscreen(chat_id: str):
    caption = """🚀 *GESSsAI-PRO* 🚀

⚽ *Benvenuto nel Bot di Analisi Calcio!*

💡 *Come funziona:*
1️⃣ Scegli 3 famiglie di giocate
2️⃣ Seleziona il periodo (1-5 giorni)
3️⃣ Ricevi le previsioni con percentuali e *quote*

💰 *Value Bet integrate!*
💎 Edge > 20% | ✅ > 10% | 🟡 > 5%

🎫 *In fondo trovi le quote totali per colonna!*

🎯 *Preparati all'azione!*"""

    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {'chat_id': chat_id, 'photo': SPLASH_URL, 'caption': caption, 'parse_mode': 'Markdown'}

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            keyboard = create_inline_keyboard([
                {'text': '🎯 INIZIA ORA', 'callback_data': 'start_setup'},
                {'text': 'ℹ️ INFO', 'callback_data': 'show_info'}
            ])
            send_message(chat_id, "✨ *Cosa vuoi fare?*", parse_mode='Markdown', reply_markup=keyboard)
        else:
            logger.warning(f"Errore caricamento immagine: {response.text}")
            send_splashscreen_text(chat_id)
    except Exception as e:
        logger.error(f"Errore invio splashscreen: {e}")
        send_splashscreen_text(chat_id)

def send_splashscreen_text(chat_id: str):
    splash_text = """🚀 *GESSsAI-PRO* 🚀

╔════════════════════════════════╗
║   🤖 *Benvenuto nel Bot!*     ║
║                                ║
║   ⚽ *Analisi Calcio Avanzata* ║
║   📊 *Statistiche in Tempo Reale* ║
║   💰 *Quote e Value Bet*      ║
║                                ║
║   💡 *Come funziona:*          ║
║   1️⃣ Scegli 3 famiglie       ║
║   2️⃣ Seleziona il periodo     ║
║   3️⃣ Ricevi le previsioni     ║
║                                ║
╚════════════════════════════════╝

✨ *Preparati all'azione!* ✨

🇮🇹 *Scegli le tue giocate!*"""

    keyboard = create_inline_keyboard([
        {'text': '🎯 INIZIA ORA', 'callback_data': 'start_setup'},
        {'text': 'ℹ️ INFO', 'callback_data': 'show_info'}
    ])
    send_message(chat_id, splash_text, parse_mode='Markdown', reply_markup=keyboard)

def handle_info(chat_id: str):
    info_text = """ℹ️ *GESSsAI-PRO - Info*

📌 *Cos'è GESSsAI-PRO?*
Bot di analisi calcistica con dati statistici e quote Marathonbet.

🎯 *Famiglie di giocate:*
• 🎯 Fisse (1, X, 2)
• 🛡️ Doppia Chance (1X, 12, X2)
• ⚽ GG-NG
• ⬆️ Over (1.5, 2.5)
• ⬇️ Under (1.5, 2.5, 3.5, 4.5)
• 🔗 DC+Under/Over
• 📊 Multigol Totale
• ⚔️ MG Casa+Ospite
• 🔗 DC+Multigol

💰 *Value Bet:*
Quota bookmaker vs quota fair (100 / %).
• 💎 Edge > 20% → VALUE ECCELLENTE
• ✅ Edge > 10% → VALUE BUONO
• 🟡 Edge > 5% → VALUE MARGINALE
• ⚪ Edge ≤ 5% → Quota fair

📈 *Kelly stake*: % bankroll consigliata.

🎫 *Quote totali per colonna:*
In fondo al report trovi la quota totale di ogni colonna (multipla di tutte le partite) e del sistema completo.

⚠️ *Quote mancanti* (es. Multigol non nel PDF) → sostituite con 1.00

💣 *BOMBA!* = Giocata con % ≥ 90%

👨‍💻 *Creato con passione per il calcio!*"""

    keyboard = create_inline_keyboard([
        {'text': '🎯 INIZIA', 'callback_data': 'start_setup'},
        {'text': '⬅️ INDIETRO', 'callback_data': 'start_setup'}
    ])
    send_message(chat_id, info_text, parse_mode='Markdown', reply_markup=keyboard)

# ============================================================
# GESTIONE COMANDI
# ============================================================

def handle_start(chat_id: str):
    user_states[chat_id] = {
        'step': 'splash',
        'giocate': [],
        'selected_days': 3,
        'selected_count': 5
    }
    send_splashscreen(chat_id)

def handle_start_setup(chat_id: str):
    if chat_id not in user_states:
        user_states[chat_id] = {
            'step': 'selecting_giocata1',
            'giocate': [],
            'selected_days': 3,
            'selected_count': 5
        }
    state = user_states[chat_id]
    state['step'] = 'selecting_giocata1'
    state['giocate'] = []
    text = "🎯 *Colonna 1 (di 3)*\n\nScegli la prima famiglia di giocate."
    keyboard = create_family_keyboard()
    send_message(chat_id, text, parse_mode='Markdown', reply_markup=keyboard)

def handle_family_selection(chat_id: str, family_id: str):
    if chat_id not in user_states: return
    state = user_states[chat_id]

    if family_id in state['giocate']:
        send_message(chat_id, "⚠️ Hai già scelto questa famiglia! Scegline un'altra.")
        return

    state['giocate'].append(family_id)

    if state['step'] == 'selecting_giocata1':
        state['step'] = 'selecting_giocata2'
        text = f"✅ *Colonna 1: {FAMIGLIE_GIOCATE[family_id]['label']}*\n\n🎯 *Colonna 2 (di 3)*\n\nScegli la seconda famiglia."
        keyboard = create_family_keyboard()
        send_message(chat_id, text, parse_mode='Markdown', reply_markup=keyboard)
    elif state['step'] == 'selecting_giocata2':
        state['step'] = 'selecting_giocata3'
        text = f"✅ *Colonna 1: {FAMIGLIE_GIOCATE[state['giocate'][0]]['label']}*\n✅ *Colonna 2: {FAMIGLIE_GIOCATE[family_id]['label']}*\n\n🎯 *Colonna 3 (di 3)*\n\nScegli la terza famiglia."
        keyboard = create_family_keyboard()
        send_message(chat_id, text, parse_mode='Markdown', reply_markup=keyboard)
    elif state['step'] == 'selecting_giocata3':
        state['step'] = 'selecting_days'
        text = f"✅ *Colonna 1: {FAMIGLIE_GIOCATE[state['giocate'][0]]['label']}*\n✅ *Colonna 2: {FAMIGLIE_GIOCATE[state['giocate'][1]]['label']}*\n✅ *Colonna 3: {FAMIGLIE_GIOCATE[family_id]['label']}*\n\n📅 Scegli il *range di giorni* (1-5)."
        keyboard = create_days_keyboard()
        send_message(chat_id, text, parse_mode='Markdown', reply_markup=keyboard)

def handle_days_selection(chat_id: str, days: int):
    if chat_id not in user_states: return
    state = user_states[chat_id]
    state['selected_days'] = days
    state['step'] = 'selecting_count'
    text = f"📅 *Range giorni: {days} giorni*\n\n🔢 Scegli *quante partite* vedere (1-10)."
    keyboard = create_count_keyboard()
    send_message(chat_id, text, parse_mode='Markdown', reply_markup=keyboard)

def handle_count_selection(chat_id: str, count: int):
    if chat_id not in user_states: return
    state = user_states[chat_id]
    state['selected_count'] = count
    text = f"📋 *RIEPILOGO*\n\nColonne: {', '.join(FAMIGLIE_GIOCATE[g]['label'] for g in state['giocate'])}\n📅 Giorni: {state['selected_days']}\n🔢 Partite: {count}\n\nConfermi?"
    keyboard = create_inline_keyboard([
        {'text': '✅ CONFERMA', 'callback_data': 'confirm_analysis'},
        {'text': '❌ ANNULLA', 'callback_data': 'cancel_analysis'}
    ])
    send_message(chat_id, text, parse_mode='Markdown', reply_markup=keyboard)

def handle_confirm_analysis(chat_id: str):
    if chat_id not in user_states: return
    state = user_states[chat_id]
    send_message(chat_id, "⏳ *Caricamento Excel...*", parse_mode='Markdown')

    try:
        df = load_excel_from_github()
        if df is None:
            send_message(chat_id, "❌ *Errore:* File Excel non trovato.")
            return

        matches = parse_matches_from_excel(df)
        if not matches:
            send_message(chat_id, "❌ *Errore:* Nessuna partita.")
            return

        send_message(chat_id, "⏳ *Caricamento quote PDF...*", parse_mode='Markdown')

        try:
            partite_quote = get_quote_cached()
            logger.info(f"💰 Quote disponibili per {len(partite_quote)} partite")
            if not partite_quote:
                send_message(chat_id, "⚠️ *Attenzione:* Quote non disponibili.")
        except Exception as e:
            logger.error(f"❌ Errore quote: {e}")
            partite_quote = []
            send_message(chat_id, f"⚠️ *Quote non disponibili:* {str(e)[:100]}")

        send_message(chat_id, "⏳ *Analisi in corso...*", parse_mode='Markdown')

        family_ids = state['giocate']
        analyses = analyze_matches(matches, family_ids, state['selected_days'], partite_quote)

        if not analyses:
            send_message(chat_id, f"📅 *Nessuna partita nei prossimi {state['selected_days']} giorni.*", parse_mode='Markdown')
            return

        report = generate_report(analyses, state['selected_count'], family_ids)

        if len(report) > 4000:
            chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
            for chunk in chunks:
                send_message(chat_id, chunk, parse_mode='Markdown')
        else:
            send_message(chat_id, report, parse_mode='Markdown')

        keyboard = create_inline_keyboard([
            {'text': '🔄 NUOVA RICERCA', 'callback_data': 'new_search'}
        ])
        send_message(chat_id, "✅ *Analisi completata!*", parse_mode='Markdown', reply_markup=keyboard)

    except Exception as e:
        error_msg = f"❌ *Errore:* {str(e)[:200]}"
        logger.error(f"Errore: {e}\n{traceback.format_exc()}")
        send_message(chat_id, error_msg, parse_mode='Markdown')

def handle_cancel_analysis(chat_id: str):
    send_message(chat_id, "❌ *Operazione annullata.* Ricomincia con /start", parse_mode='Markdown')

def handle_new_search(chat_id: str):
    if chat_id in user_states:
        user_states[chat_id] = {'step': 'splash', 'giocate': [], 'selected_days': 3, 'selected_count': 5}
    send_splashscreen(chat_id)

# ============================================================
# WEBHOOK
# ============================================================

@app.route('/', methods=['GET'])
def home():
    return "🤖 GesssAI-Pro Bot è attivo!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'ok'})

        if 'message' in data:
            message = data['message']
            chat_id = str(message['chat']['id'])
            text = message.get('text', '')
            if text == '/start':
                handle_start(chat_id)
            else:
                send_message(chat_id, "❓ Usa /start")

        elif 'callback_query' in data:
            callback = data['callback_query']
            chat_id = str(callback['message']['chat']['id'])
            callback_data = callback['data']

            try:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery",
                              json={'callback_query_id': callback['id']}, timeout=5)
            except:
                pass

            if callback_data == 'start_setup': handle_start_setup(chat_id)
            elif callback_data == 'show_info': handle_info(chat_id)
            elif callback_data == 'new_search': handle_new_search(chat_id)
            elif callback_data == 'confirm_analysis': handle_confirm_analysis(chat_id)
            elif callback_data == 'cancel_analysis': handle_cancel_analysis(chat_id)
            elif callback_data == 'count_confirm':
                if chat_id in user_states and user_states[chat_id].get('selected_count'):
                    handle_count_selection(chat_id, user_states[chat_id]['selected_count'])
                else:
                    send_message(chat_id, "⚠️ Scegli prima il numero!")
            elif callback_data.startswith('fam_'):
                family_id = callback_data[4:]
                if family_id in FAMIGLIE_GIOCATE:
                    handle_family_selection(chat_id, family_id)
            elif callback_data.startswith('days_'):
                handle_days_selection(chat_id, int(callback_data[5:]))
            elif callback_data.startswith('count_'):
                if callback_data == 'count_10': count = 10
                else: count = int(callback_data[6:])
                if chat_id in user_states:
                    state = user_states[chat_id]
                    state['selected_count'] = count
                    text = f"📋 *RIEPILOGO*\n\nColonne: {', '.join(FAMIGLIE_GIOCATE[g]['label'] for g in state['giocate'])}\n📅 Giorni: {state['selected_days']}\n🔢 Partite: {count}\n\nConfermi?"
                    keyboard = create_inline_keyboard([
                        {'text': '✅ CONFERMA', 'callback_data': 'confirm_analysis'},
                        {'text': '❌ ANNULLA', 'callback_data': 'cancel_analysis'}
                    ])
                    send_message(chat_id, text, parse_mode='Markdown', reply_markup=keyboard)

        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Errore webhook: {e}")
        return jsonify({'status': 'error'}), 500

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)