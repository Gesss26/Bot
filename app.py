def get_giocata_pct(giocata: str, stats: Dict, home_media_gol: float = None, away_media_gol: float = None) -> int:
    """
    Calcola la percentuale per una giocata
    """
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
    
    # GESTIONE MG CASA+OSPITE
    # Formato: "0-2+0-2", "0-2+1-3", "1-3+2-5", ecc.
    if '+' in giocata and '-' in giocata:
        parts = giocata.split('+')
        if len(parts) == 2 and '-' in parts[0] and '-' in parts[1]:
            if home_media_gol is not None and away_media_gol is not None:
                # Calcola le fasce consigliate
                home_range = get_multigol_range(home_media_gol)
                away_range = get_multigol_range(away_media_gol)
                expected = f"{home_range}+{away_range}"
                
                # Se è esatta -> alta percentuale
                if giocata == expected:
                    return 90
                
                # Altrimenti calcola la vicinanza
                h1, h2 = giocata.split('+')[0].split('-')
                a1, a2 = giocata.split('+')[1].split('-')
                eh1, eh2 = home_range.split('-')
                ea1, ea2 = away_range.split('-')
                
                diff = (abs(int(h1)-int(eh1)) + abs(int(h2)-int(eh2)) + 
                       abs(int(a1)-int(ea1)) + abs(int(a2)-int(ea2)))
                
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
    
    # GESTIONE MULTIGOL TOTALE
    if giocata in ['0-2', '1-3', '2-5']:
        if home_media_gol is not None and away_media_gol is not None:
            expected = get_multigol_total_range(home_media_gol, away_media_gol)
            if giocata == expected:
                return 85
            # Calcola vicinanza
            g1, g2 = giocata.split('-')
            e1, e2 = expected.split('-')
            diff = abs(int(g1)-int(e1)) + abs(int(g2)-int(e2))
            if diff <= 2:
                return 70
            elif diff <= 4:
                return 50
            else:
                return 30
        return 50
    
    # GESTIONE DC+MULTIGOL
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
    
    # DC+UNDER/OVER
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