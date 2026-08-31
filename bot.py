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

# ============================================================
# CONFIGURAZIONE
# ============================================================

TOKEN = "7674593142:AAGhP_A5x9XIHQ1BKKufDA0jwjn2k2KerJg"
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
    label: str
    pct: int
    is_bomb: bool

@dataclass
class MatchAnalysis:
    match: Match
    giocata: Giocata
    score: int
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
    """Verifica se la partita è futura rispetto all'orario corrente"""
    if match.stato != "Futura":
        return False
    
    try:
        # Combina data e ora
        match_datetime_str = f"{match.data} {match.ora}"
        # Prova diversi formati di ora
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H", "%Y-%m-%d"]:
            try:
                match_datetime = datetime.strptime(match_datetime_str, fmt)
                # Se l'ora non è specificata, considera mezzogiorno come default
                if fmt == "%Y-%m-%d":
                    match_datetime = match_datetime.replace(hour=12, minute=0)
                return match_datetime > datetime.now()
            except ValueError:
                continue
        
        # Se non riesce a parsare, considera la data
        match_date = datetime.strptime(match.data, "%Y-%m-%d")
        return match_date >= datetime.now().date()
    except Exception as e:
        logger.warning(f"Errore nel filtraggio ora per {match.casa} vs {match.ospiti}: {e}")
        # Fallback: considera solo la data
        try:
            match_date = datetime.strptime(match.data, "%Y-%m-%d")
            return match_date >= datetime.now().date()
        except:
            return True

# ============================================================
# CARICAMENTO DATI DAL FILE EXCEL
# ============================================================

def load_excel_from_github() -> Optional[pd.DataFrame]:
    """Carica il file Excel dal repository GitHub"""
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
        return {'form': '-----', 'pct': 50, 'media_gol_fatti': 0, 'media_gol_subiti': 0, 'partite': 0}
    
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
    
    return {
        'form': form or '-----',
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
        'p1': round(p1),
        'pX': round(pX),
        'p2': round(p2),
        'p1X': round(p1X),
        'p12': round(p12),
        'pX2': round(pX2),
        'gg': round(gg),
        'ng': round(ng),
        'under_over': under_over,
        'total_games': total
    }

# ============================================================
# CALCOLO GIOCATA
# ============================================================

def get_giocata_pct(giocata: str, stats: Dict) -> int:
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
    
    if giocata == '1':
        return p1
    if giocata == 'X':
        return pX
    if giocata == '2':
        return p2
    if giocata == '1X':
        return p1X
    if giocata == '12':
        return p12
    if giocata == 'X2':
        return pX2
    if giocata == 'GG':
        return gg
    if giocata == 'NG':
        return ng
    if giocata == 'Over 1.5':
        return under_over[0]['over'] if len(under_over) > 0 else 0
    if giocata == 'Over 2.5':
        return under_over[1]['over'] if len(under_over) > 1 else 0
    if giocata == 'Under 1.5':
        return under_over[0]['under'] if len(under_over) > 0 else 0
    if giocata == 'Under 2.5':
        return under_over[1]['under'] if len(under_over) > 1 else 0
    if giocata == 'Under 3.5':
        return under_over[2]['under'] if len(under_over) > 2 else 0
    if giocata == 'Under 4.5':
        return under_over[3]['under'] if len(under_over) > 3 else 0
    
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

def get_best_bet_for_family(family_id: str, stats: Dict) -> Optional[Dict]:
    family = FAMIGLIE_GIOCATE.get(family_id)
    if not family:
        return None
    
    best = None
    best_pct = -1
    
    for opt in family['options']:
        pct = get_giocata_pct(opt, stats)
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

def analyze_matches(matches: List[Match], family_id: str, days_range: int) -> List[MatchAnalysis]:
    # Filtra per stato futuro
    future_matches = [m for m in matches if m.stato == "Futura"]
    today = get_today_str()
    limit_date = (datetime.now() + timedelta(days=days_range)).strftime("%Y-%m-%d")
    future_matches = [m for m in future_matches if m.data >= today and m.data <= limit_date]
    
    # FILTRA PER ORARIO - ESCLUDE PARTITE GIA' INIZIATE O PASSATE
    future_matches = [m for m in future_matches if is_match_future(m)]
    
    logger.info(f"🔍 Trovate {len(future_matches)} partite future (filtrate per data e ora) fino al {limit_date}")
    
    results = []
    
    for match in future_matches:
        stats = compute_match_stats(match, matches)
        if stats.get('error'):
            continue
        
        home_form = calc_form_and_stats(matches, match.casa)
        away_form = calc_form_and_stats(matches, match.ospiti)
        
        best = get_best_bet_for_family(family_id, stats)
        if not best:
            continue
        
        giocata = Giocata(
            famiglia=best['family_label'],
            label=best['giocata'],
            pct=best['pct'],
            is_bomb=best['is_bomb']
        )
        
        results.append(MatchAnalysis(
            match=match,
            giocata=giocata,
            score=best['pct'],
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
    """Invia un messaggio e restituisce True se ha successo"""
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
# GENERAZIONE REPORT - CORRETTA
# ============================================================

def generate_report(analyses: List[MatchAnalysis], count: int) -> str:
    """Genera il report in formato HTML per Telegram"""
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
        g = analysis.giocata
        
        # Colore in base alla percentuale
        if g.pct >= 90:
            color = '#f39c12'
            emoji = '💣'
        elif g.pct >= 67:
            color = '#6fcf97'
            emoji = '🟢'
        elif g.pct >= 34:
            color = '#8b949e'
            emoji = '⚪'
        else:
            color = '#eb5757'
            emoji = '🔴'
        
        bomb = ' 💣' if g.is_bomb else ''
        
        lines.append(f"<b>#{i} - {match.campionato}</b>")
        lines.append(f"📅 {format_date_eu(match.data)} - ⏰ {match.ora}")
        lines.append(f"<b>⚔️ {match.casa} vs {match.ospiti}</b>")
        lines.append(f"📊 Forma: {match.casa} {format_form(analysis.home_form['form'])} ({analysis.home_form['pct']}%) | {match.ospiti} {format_form(analysis.away_form['form'])} ({analysis.away_form['pct']}%)")
        lines.append(f"⚽ xG: {match.casa} {analysis.home_form['media_gol_fatti']} | {match.ospiti} {analysis.away_form['media_gol_fatti']}")
        lines.append("")
        lines.append(f"🎯 <b>{g.famiglia}</b>: {g.label} {emoji} <b><font color='{color}'>{g.pct}%</font></b>{bomb}")
        lines.append(f"📊 Score: {analysis.score}%")
        
        if i < len(top):
            lines.append("")
            lines.append("─" * 30)
            lines.append("")
    
    return "\n".join(lines)

def format_form(form: str) -> str:
    if not form:
        return '❌'
    return ''.join(['✅' if f == 'V' else '➖' if f == 'P' else '❌' for f in form])

# ============================================================
# GESTIONE STATO UTENTE
# ============================================================

class UserState:
    def __init__(self):
        self.step = 'start'
        self.selected_family = None
        self.selected_days = 3
        self.selected_count = 5

# ============================================================
# GESTIONE COMANDI
# ============================================================

def handle_start(chat_id: str):
    user_states[chat_id] = UserState()
    
    text = """<b>🤖 GesssAI-Pro Bot</b>

Benvenuto! Scegli una famiglia di giocate e ti mostrerò le migliori partite.

<b>📋 Come funziona:</b>

1️⃣ <b>Scegli 1 famiglia</b> di giocate
2️⃣ <b>Scegli il range di giorni</b> (1-5)
3️⃣ <b>Scegli quante partite</b> vedere (1-10)"""

    keyboard = create_inline_keyboard([{'text': '🎯 INIZIA', 'callback_data': 'start_setup'}])
    send_telegram_message(chat_id, text, reply_markup=keyboard)

def handle_start_setup(chat_id: str):
    if chat_id not in user_states:
        user_states[chat_id] = UserState()
    
    state = user_states[chat_id]
    state.step = 'selecting_family'
    state.selected_family = None
    
    text = """<b>🎯 Scegli una famiglia di giocate</b>

Clicca su una famiglia per selezionarla."""
    
    keyboard = create_family_keyboard()
    send_telegram_message(chat_id, text, reply_markup=keyboard)

def handle_family_selection(chat_id: str, family_id: str):
    if chat_id not in user_states:
        return
    
    state = user_states[chat_id]
    state.selected_family = family_id
    
    text = f"""<b>✅ Famiglia selezionata: {FAMIGLIE_GIOCATE[family_id]['label']}</b>

Ora scegli il <b>range di giorni</b> (1-5)."""
    
    keyboard = create_days_keyboard()
    send_telegram_message(chat_id, text, reply_markup=keyboard)

def handle_days_selection(chat_id: str, days: int):
    if chat_id not in user_states:
        return
    
    state = user_states[chat_id]
    state.selected_days = days
    state.step = 'selecting_count'
    
    text = f"""<b>📅 Range giorni: {days} giorni</b>
Famiglia: {FAMIGLIE_GIOCATE[state.selected_family]['label']}

Scegli <b>quante partite</b> vedere (1-10)."""
    
    keyboard = create_count_keyboard()
    send_telegram_message(chat_id, text, reply_markup=keyboard)

def handle_count_selection(chat_id: str, count: int):
    if chat_id not in user_states:
        return
    
    state = user_states[chat_id]
    state.selected_count = count
    
    # Invia messaggio di caricamento
    send_telegram_message(chat_id, "⏳ <b>Caricamento dati in corso...</b>")
    
    try:
        # Carica i dati
        df = load_excel_from_github()
        if df is None:
            send_telegram_message(chat_id, "❌ <b>Errore:</b> Impossibile caricare il file Excel.")
            return
        
        matches = parse_matches_from_excel(df)
        if not matches:
            send_telegram_message(chat_id, "❌ <b>Errore:</b> Nessuna partita trovata nel file.")
            return
        
        logger.info(f"📊 Caricate {len(matches)} partite totali")
        
        # Analizza
        analyses = analyze_matches(matches, state.selected_family, state.selected_days)
        
        if not analyses:
            send_telegram_message(chat_id, f"📅 <b>Nessuna partita nei prossimi {state.selected_days} giorni.</b>")
            return
        
        # Genera report
        report = generate_report(analyses, count)
        
        # Invia report (con split se troppo lungo)
        if len(report) > 4000:
            chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
            for chunk in chunks:
                send_telegram_message(chat_id, chunk)
        else:
            send_telegram_message(chat_id, report)
        
        # Pulsante nuova ricerca
        keyboard = create_inline_keyboard([
            {'text': '🔄 NUOVA RICERCA', 'callback_data': 'new_search'}
        ])
        send_telegram_message(chat_id, "✅ <b>Analisi completata!</b>", reply_markup=keyboard)
        
    except Exception as e:
        error_msg = f"❌ <b>Errore:</b> {str(e)}\n\n{traceback.format_exc()[:200]}"
        logger.error(f"Errore: {e}")
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
            
            # Rispondi al callback per rimuovere il loading
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
Famiglia: {FAMIGLIE_GIOCATE[state.selected_family]['label']}
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