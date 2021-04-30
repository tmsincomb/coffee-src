#!/usr/bin/env python3
"""
Usage:
  app.py [-d FILE]
  app.py (-h | --help)

Options:
  -h, --help
  -d, --db_url=FILE
"""

from flask import Flask, render_template, render_template_string, request, redirect, url_for
from coffee_src import MysqlConnector
from coffee_src import dynamic_form
import os
from werkzeug.datastructures import MultiDict
from docopt import docopt
import geopandas
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib
import pandas as pd 
import seaborn as sns
from io import BytesIO
matplotlib.use('Agg')
args=docopt(__doc__)

SECRET_KEY = os.urandom(32)
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
db_url = open(args['--db_url']).read() if args.get('--db_url') else None
db = MysqlConnector(app, db_url)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

header = """
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Schema</title>
    <link rel=stylesheet type=text/css href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
<a href="/">&#8592; BACK HOME</a><br></br>
</body>
"""

def get_lineplot(usda, country_name):
    metrics =  [
        'Imports',
        'Exports',
        'Domestic Consumption',
        'Arabica Production',
        'Robusta Production',
        'Other Production',
    ]
    df = usda[usda.Country_Name == country_name]
    return sns.lineplot(data=df[df.Attribute_Description.isin(metrics)], y='Value', x='Market_Year', hue='Attribute_Description')


def cagr(series):
    start_val = series.iloc[0]
    if not start_val:
        return None
    end_val = series.iloc[-1]
    num_vals = len(series)
    CAGR = (end_val/start_val)**(1/num_vals)-1
    return CAGR


def create_map():
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    world = geopandas.read_file(geopandas.datasets.get_path('naturalearth_lowres'))
    world_map = world[world.name != 'Antarctica']
    world_map = world_map[['name', 'geometry']]
    world_map.set_index('name', inplace=True)

    fig, ax = plt.subplots(figsize=(20,8))
    ax.set_aspect('equal')
    ax.margins(0)
    ax.axis('off')
    world_map.plot(color='#f2f2f2', edgecolor="Grey", ax=ax)

    world_production = attribute_query('Domestic Consumption')
    world_production.fillna(0,inplace=True)
    world_production = world_production.iloc[:,-25:]

    european_union = [
        'Austria',
        'Italy',
        'Belgium',
        'Latvia',
        'Bulgaria',
        'Lithuania',
        'Croatia',
        'Luxembourg',
        'Cyprus',
        'Malta',
        'Czechia',
        'Netherlands',
        'Denmark',
        'Poland',
        'Estonia',
        'Portugal',
        'Finland',
        'Romania',
        'France',
        'Slovakia',
        'Germany',
        'Slovenia',
        'Greece',
        'Spain',
        'Hungary',
        'Sweden',
        'Ireland',
    ]

    for eu in european_union:
        world_production.loc[eu] = world_production.loc['European Union']

    world_production.rename({
        "Cote d'Ivoire": "Côte d'Ivoire",
        "Central African Republic": "Central African Rep.",
        "Congo (Kinshasa)": "Dem. Rep. Congo",
        "Dominican Republic": "Dominican Rep.",
        "United States": "United States of America",
        "Laos": "Lao PDR",
    }, inplace=True)

    # world_production['CAGR'] = world_production.apply(cagr, axis=1)
    world_production['CAGR'] = world_production.apply(sum, axis=1)

    world_production.dropna(inplace=True)
    world_production = world_production[world_production.CAGR != -1]

    cagr_map = pd.concat([world_map, world_production], axis=1, sort=True)
    cagr_map.update(cagr_map[cagr_map.columns[1:]].fillna(0))
    # cagr_map.plot(column='CAGR', ax=ax, legend=True)

    growing_map = cagr_map[cagr_map.CAGR > 0]
    growing_map.plot(column='CAGR', cmap='YlGn', scheme='fisher_jenks', edgecolor='black', ax=ax, legend=True)
    
    # buf = BytesIO()
    # fig.savefig(buf, format="png")
    
    plt.savefig('static/map.png')


def attribute_query(attribute):
    code, df = db.get('select * from trade, has_trade, country '
                       'where has_trade.trade_id = trade.id and country.code = has_trade.country_code')
    df = df[df.type==attribute]
    df = df.pivot(index='name', columns='year', values='value')
    df = df.fillna(0)
    return df


@app.route('/', methods=['GET', 'POST'])
def index():
    create_map()
    if request.method == 'POST':
        if request.form.get('query'):
            sql_command = request.form['query']
            resp_code, df = db.get(sql_command)
            if resp_code == 0:
                result = f'FAILED -> {df}'
                return render_template('message.html', result=result)
            return render_template_string(header + df.to_html())
        if request.form.get('command'):
            sql_command = request.form['command']
            resp_code, resp = db.post(sql_command)
            if resp_code == 1:
                result = f'SUCCESS -> affected {resp.rowcount} rows'
            else:
                result = f'FAILED -> {resp}'
            return render_template('message.html', result=result)
        if request.form.get('insert'):
            tablename = request.form['insert']
            return redirect(url_for('insert', tablename=tablename))
        if request.form.get('update'):
            entity_meta = request.form['update']
            return redirect(url_for('update', entity_meta=entity_meta))
        if request.form.get('delete'):
            entity_meta = request.form['delete']
            return delete_entity(entity_meta)
    database = db.descibe_database()
    tablenames, tables = zip(*database)
    rows=[]
    for tablename in tablenames:
        sql_command = f'SELECT * FROM {tablename}' # WHERE LIKE %{value}%'
        status, table = db.get(sql_command)
        for i, row in table.iterrows():
            values = list(row.to_dict().values())
            rows.append(tablename+':'+str(i)+','+str(values))
    return render_template('index.html', tablenames=tablenames, rows=rows)

@app.route('/schema', methods=['GET', 'POST'])
def schema():
    database = db.descibe_database()
    tablenames, tables = zip(*database)
    for table in tables:
        table['type'] = table['type'].apply(lambda t: str(t).split()[0])
    # Need na for white space problem
    tablenames =  ['na'] + list(tablenames)
    tables = [table.to_html() for table in tables]
    return render_template('schema.html', tables=tables, tablenames=tablenames)

@app.route('/insert/<string:tablename>', methods=['GET', 'POST'])
def insert(tablename):
    table = db.get_table(tablename)
    table['type'] = table['type'].apply(lambda t: str(t).split()[0])
    headers = list(table['name'])
    types = [t.lower () for t in list(table['type'])]
    sform = dynamic_form(table)
    form = sform()
    if form.validate_on_submit():
        values = []
        for i, field in enumerate(headers):
            if 'integer' in types[i] or 'float' in types[i] or 'double' in types[i]:
                values.append(form[field].data)
            else:
                values.append("'" + str(form[field].data) + "'")
        sql_command = f"INSERT INTO {tablename} ({', '.join(headers)}) VALUES ({', '.join(values)});"
        resp_code, resp = db.post(sql_command)
        if resp_code == 1:
            result = f'SUCCESS -> affected {resp.rowcount} rows'
        else:
            result = f'FAILED -> {resp}'
        return render_template('message.html', result=result)
    return render_template('insert_form.html', form=form, headers=headers, types=types, table_len=len(headers))

@app.route('/update/<string:entity_meta>', methods=['GET', 'POST'])
def update(entity_meta):
    tablename, index = entity_meta.split(':')
    table_schema = db.get_table(tablename)
    table_schema['type'] = table_schema['type'].apply(lambda t: str(t).split()[0])
    headers = list(table_schema['name'])
    types = [t.lower () for t in list(table_schema['type'])]
    status, table = db.get(f'SELECT * FROM {tablename};')
    row = table.iloc[int(index)]
    row = row.to_dict()
    sform = dynamic_form(table_schema)
    form = sform(**row)
    if form.validate_on_submit():
        new_conditions = []
        old_conditions = []
        for i, field in enumerate(headers):
            if 'integer' in types[i] or 'float' in types[i] or 'double' in types[i]:
                new_conditions.append(field+' = '+str(form[field].data))
                old_conditions.append(field+' = '+str(row[field]))
            else:
                new_conditions.append(field+' = '+"'"+str(form[field].data)+"'")
                old_conditions.append(field+' = '+"'"+str(row[field])+"'")
        sql_command = f"UPDATE {tablename} SET {', '.join(new_conditions)} WHERE {' and '.join(old_conditions)};"
        resp_code, resp = db.post(sql_command)
        if resp_code == 1:
            result = f'SUCCESS -> affected {resp.rowcount} rows'
        else:
            result = f'FAILED -> {resp}'
        return render_template('message.html', result=result)
    return render_template('update_form.html', form=form, headers=headers, types=types, table_len=len(headers))

@app.route('/update/<string:entity_meta>', methods=['GET', 'POST'])
def delete_entity(entity_meta):
    tablename, index = entity_meta.split(':')
    table_schema = db.get_table(tablename)
    table_schema['type'] = table_schema['type'].apply(lambda t: str(t).split()[0])
    headers = list(table_schema['name'])
    types = [t.lower () for t in list(table_schema['type'])]
    status, table = db.get(f'SELECT * FROM {tablename};')
    row = table.iloc[int(index)]
    row = row.to_dict()

    conditions = []
    for i, field in enumerate(headers):
        if 'integer' in types[i] or 'float' in types[i] or 'double' in types[i]:
            conditions.append(field+' = '+str(row[field]))
        else:
            conditions.append(field+' = '+"'"+str(row[field])+"'")
    sql_command = f"DELETE FROM {tablename} WHERE {' and '.join(conditions)};"
    resp_code, resp = db.post(sql_command)
    if resp_code == 1:
        result = f'SUCCESS -> affected {resp.rowcount} rows'
    else:
        result = f'FAILED -> {resp}'
    return render_template('message.html', result=result)


def main():
    app.run(debug=True)


if __name__ == '__main__':
    main()
