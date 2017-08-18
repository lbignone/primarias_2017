from bs4 import BeautifulSoup
import requests
import pandas as pd
from tqdm import tqdm
import json


base_url = "http://www.resultados.gob.ar/99/resu/content/telegramas/"


def extract_info_mesa(soup):

    keys = ['Distrito', 'Sección', 'Circuito', 'Mesa', 'Estado']

    table = soup.find_all('table')[0]
    row = table.find_all('td')

    d = {}
    for i, k in enumerate(keys):
        d[k] = row[i].get_text()

    return d


def extract_total_values(soup):
    table = soup.find_all('table')[1]

    row_keys = ['Votos nulos', 'Votos en blanco', 'Votos recurridos']
    column_keys = ['Senadores Nacionales', 'Diputados Nacionales', 'Senadores Provinciales', 'Concejales']

    row_data = {}
    for i, r in enumerate(row_keys):
        row = table.find_all('tr')[i+1]
        data = row.find_all('td')

        column_data = {}
        for j, c in enumerate(column_keys):
            column_data[c] = int(data[j].get_text())
        row_data[r] = column_data

    return row_data


def extract_impugnados(soup):
    table = soup.find_all('table')[2]

    n = int(table.find_all('td')[0].get_text())
    
    return {'Votos impugnados': n}


def extract_results(soup):

    column_keys = ['Senadores Nacionales', 'Diputados Nacionales', 'Senadores Provinciales', 'Concejales']

    table = soup.find_all('table')[3]
    rows = table.find_all('tr')

    group_keys = [group.get_text() for group in table.find_all('th', class_="alaizquierda")]

    results = []
    for row in rows:
        record = {}
        group = row.select('th.alaizquierda')
        sub_group = row.select('th.aladerecha')
        if group:
            key = group[0].get_text()
        elif sub_group:

            record['group'] = key
            record['subgroup'] = sub_group[0].get_text()

            columns = row.select('td')
            for i, c in enumerate(column_keys):
                data = columns[i].get_text()
                if data == '\xa0':
                    data = None
                else:
                    data = int(data)
                record[c] = data
            results.append(record)

    return results


def get_mesa_df(soup):
    info = extract_info_mesa(soup)
    results = extract_results(soup)
    df = pd.DataFrame(results)
    for k in info:
        df[k] = len(df) * [info[k]]
    
    return df


def get_name_url(soup):
    data = soup.find_all('li', text=True)
    
    d = {}
    for row in data:
        name = row.get_text().strip()
        url = row.find_all('a')[0]['href']
        
        d[name] = url
        
    return d


def extract_secciones(soup, progressbar=tqdm):
    secciones = get_name_url(soup)

    for secc in progressbar(secciones):
        sec_url = secciones[secc]
        page = requests.get(base_url + sec_url)
        soup = BeautifulSoup(page.content, "lxml")
        
        circuitos = get_name_url(soup)
        
        for circ in progressbar(circuitos, leave=False):
            circ_url = circuitos[circ]
            page = requests.get(base_url + circ_url)
            soup = BeautifulSoup(page.content, "lxml")
            
            mesas = get_name_url(soup)
            
            circuitos[circ] = {'mesas': mesas, 'url': circ_url}
            
        secciones[secc] = {'circuitos': circuitos, 'url': sec_url}

    return secciones