import bs4
import urllib
import urllib3
import re
import pandas as pd
import numpy as np
import io
import geocoder
import geopandas as gp
import csv 
import json

def scrape_datasets(main_url):
	pattern_ev = r'.+(?=/browse)'
	url_pre = re.findall(pattern_ev, main_url)[0]

	pm = urllib3.PoolManager()

	soup = bs4.BeautifulSoup(make_html(pm,main_url),'html.parser')

	all_results = [url_pre+x['href'] for x in soup.find_all('a','pageLink') if x['href']]

	return [[x['href'].strip(url_pre) for x in bs4.BeautifulSoup(make_html(pm,results),'html.parser').find_all('a','browse2-result-name-link') if x['href']] for results in all_results]


def make_one_column(datasets, name):
    return pd.concat([pd.Series(d) for d in datasets]).to_frame().rename(columns={0:name})


def from_txt(f_name,pattern,name):
    f = open(f_name)
    items = []
    for line in f.readlines():
        topic = re.findall(pattern, line)
        if len(topic) != 0:
            items.append(topic)
    return pd.DataFrame(items).rename(columns={0:name})


def make_html(pm,url):
	return pm.urlopen(url= url, method="GET").data

def basic_scrape(url, tag_type1, tag_type2, name):
    pm = urllib3.PoolManager()
    soup = bs4.BeautifulSoup(make_html(pm,url),'html.parser')
    data = []
    for s in soup.find_all(tag_type1):
        dataset = s.find_all(tag_type2)
        if len(dataset):
            data.append(dataset[0].string)
    return pd.DataFrame(data).rename(columns={0:name})

def data_to_csv(df,v):
    return df.to_csv(v)


def check_na(df):
    df_lng = pd.melt(df)
    null_vars = df_lng.value.isnull()
    return pd.crosstab(df_lng.variable, null_vars)

def get_lat_long(series, coord):
    if coord == 'latitude':
        return series['coordinates'][1] 
    return series['coordinates'][0]

def get_zip(s):
    pattern = r'(?<![A-Z])[\d]{5}' 
    return re.search(pattern, s).group()

def strip_address(s):
    return s[:-6]

def get_soup(url):
    pm = urllib3.PoolManager()
    html = pm.urlopen(url= url, method="GET").data
    return bs4.BeautifulSoup(make_html(pm,url),'html.parser')

def camel_to_snake(column_name):
    """
    converts a string that is camelCase into snake_case
    Example:
        print camel_to_snake("javaLovesCamelCase")
        > java_loves_camel_case
    See Also:
        http://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-camel-case
    """
    
    if ' ' in column_name:
    	if '.' in column_name:
    		return re.sub('(.)([A-Z][a-z]+)', r'\1\2', column_name).lower().replace(' ','_').replace('.','')
    	return re.sub('(.)([A-Z][a-z]+)', r'\1\2', column_name).lower().replace(' ','_')
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', column_name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def combine_cols(series):
    if type(series[1]) != float:
        return ' '.join(series)
    else:
        return series[0]

def read(file_name):
    '''
    This was to experiment with uploading a csv using python csv library.
    Needless to say it is pretty slow.
    '''
    df = pd.DataFrame()

    pattern = r'[(?!=.)]([a-z]*)'
    file_type = re.findall(pattern, file_name)[0]

    assert file_type == 'csv'
    with open(file_name, 'rt') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for index,row in enumerate(reader):
            print(row)
            df = pd.concat([df,pd.DataFrame(row).transpose()])

def parse_df_dict(series):
    return pd.DataFrame([[series.values()]], columns = [list(series.keys())])

def ckan_to_df(soup):
    new_dict ={}
    for d in json.loads(str(soup))['result']['records']:
        for key in  json.loads(str(soup))['result']['records'][0].keys():
            if key in new_dict:
                new_dict[key].append(d[key])
            else: 
                new_dict[key]=[d[key]]
    return pd.DataFrame(new_dict)

def make_dfs(file_name):
    permit_dfs = {}
    with open(file_name, 'rt') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for index,row in enumerate(reader):
            print(row)
            url = row[1]
            if row[0] == 'Location':
                continue
            elif 'json' in url:
                df = pd.read_json(url)
            elif 'csv' in url:
                df = pd.read_csv(url)
            elif 'civicdata' in url:
                df = ckan_to_df(get_soup(url))
            else:
                return 'file in unknown format'
            permit_dfs[row[0]]=df
    return permit_dfs

def get_same_cols(dfs):
    headers_dict= {} 
    for key,vals in dfs.items():
        for col in vals.columns:
            if col in headers_dict:
                headers_dict[col]['count']+=1
                headers_dict[col]['datasets'].append(key)
            else:
                headers_dict[col] = {'count':1,'datasets':[key]}
    return headers_dict, pd.DataFrame(headers_dict).transpose().sort_values(by=['count'], ascending=False)
