import os
from functools import lru_cache

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
import pandas as pd
from sqlalchemy import create_engine


VERSION = '2020.2.1'
PAGE_SIZE = 10
BASE_URL = 'https://digi.kansalliskirjasto.fi/'
DATA_DIR = 'https://raw.githubusercontent.com/AnttiHaerkoenen/' \
           'grand_duchy/master/data/processed/frequencies_fi_newspapers/'

DATABASE_URL = os.environ.get('database_url')

if DATABASE_URL:
    sql_engine = create_engine(DATABASE_URL)
else:
    sql_engine = None

freq_lemma_data_rel = pd.read_csv(DATA_DIR + 'lemma_rel.csv')
freg_lemma_data_abs = pd.read_csv(DATA_DIR + 'lemma_abs.csv')
freq_regex_data_rel = pd.read_csv(DATA_DIR + 'regex_rel.csv')
freg_regex_data_abs = pd.read_csv(DATA_DIR + 'regex_abs.csv')

keywords = sorted(set(freq_lemma_data_rel.columns) - {'year', 'Unnamed: 0'})


@lru_cache(maxsize=32)
def query_kwics(
        keyword,
        years,
):
    sql_query = f"SELECT * FROM kwic_fi_newspapers WHERE term = '{keyword}'"

    if len(years) == 1:
        sql_query += f" AND year = {years[0]}"
    elif len(years) > 1:
        sql_query += f" AND year IN {years}"

    df = pd.read_sql(
        sql_query,
        con=sql_engine,
    )
    df['url'] = [BASE_URL + url for url in df.url]

    return df


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__)
app.title = "Finnish newspapers"

application = app.server

options = [{'label': k, 'value': k} for k in keywords]

app.layout = html.Div(children=[
    html.H1(children=f'{app.title}'),

    html.H2(children='Keyword'),

    html.Div([
        dcc.Dropdown(
            id='keyword-picker',
            options=options,
            value=options[0]['value'],
        ),
    ]),

    html.H2(children='Frequency'),
    html.Div([
        dcc.RadioItems(
            id='abs-picker',
            options=[
                {'label': i.capitalize(), 'value': i}
                for i in ['absolute', 'relative']
            ],
            value='absolute',
            labelStyle={'display': 'inline-block'}
        ),
    ]),

    html.H2(children='Lemma'),
    html.Div([
        dcc.RadioItems(
            id='lemma-picker',
            options=[
                {'label': i.capitalize(), 'value': i}
                for i in ['lemma', 'regex']
            ],
            value='regex',
            labelStyle={'display': 'inline-block'}
        ),
    ]),

    html.Div([
        html.H2(children='Frequency plot'),
        dcc.Graph(
            id='bar-plot',
        ),
    ]),


    html.Div([
        html.H2(children='Keywords in context'),
        dash_table.DataTable(
            id='kwic-table',
            columns=[
                {
                    'name': col.capitalize(),
                    'id': col,
                    'type': 'text',
                    'presentation': 'markdown',
                }
                for col
                in ['publication', 'year', 'context', 'link']
            ],
            style_cell_conditional=[
                {'if': {'column_id': 'publication'}, 'width': '10%'},
                {'if': {'column_id': 'year'}, 'width': '5%'},
                {'if': {'column_id': 'context'}, 'width': '50%'},
            ],
            page_size=PAGE_SIZE,
            style_data={
                'whiteSpace': 'normal',
                'height': 'auto',
                'text-align': 'left',
            },
            style_header={
                'text-align': 'left',
            },
            export_format='xlsx',
            row_deletable=True,
            sort_action='native',
            filter_action='native',
        ),
    ]),

    html.P(
        children=f"Version {VERSION}",
        style={
            'font-style': 'italic'
        },
    ),
])


@app.callback(
    Output('bar-plot', 'figure'),
    [Input('keyword-picker', 'value'),
     Input('abs-picker', 'value'),
     Input('lemma-picker', 'value')]
)
def update_graph(
        keyword,
        abs_or_rel,
        lemma_or_regex,
):
    if abs_or_rel == 'absolute' and lemma_or_regex == 'lemma':
        data = freg_lemma_data_abs
    elif abs_or_rel == 'relative' and lemma_or_regex == 'lemma':
        data = freq_lemma_data_rel
    elif abs_or_rel == 'absolute' and lemma_or_regex == 'regex':
        data = freg_regex_data_abs
    else:
        data = freq_regex_data_rel

    x = data['year']
    y = data[keyword]

    return {
        'data': [{
            'x': x,
            'y': y,
            'type': 'bar',
            'name': keyword,
        }]
    }


@app.callback(
    Output('kwic-table', 'data'),
    [Input('keyword-picker', 'value'),
     Input('bar-plot', 'selectedData')]
)
def update_table(
        keyword,
        selection,
):
    if not keyword or not sql_engine:
        raise PreventUpdate

    if selection is None:
        points = []
    else:
        points = selection.get('points', [])

    years = tuple(point['x'] for point in points)

    data = query_kwics(
        keyword=keyword,
        years=years,
    )
    data['link'] = [
        f"[{url}]({url})"
        for url in data['url']
    ]

    return data.to_dict('records')


if __name__ == '__main__':
    app.run_server(
        port=8080,
        host='0.0.0.0',
        debug=False,
    )
