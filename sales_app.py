import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from dash.dependencies import Input, Output, State
import datetime



pd.options.display.float_format = '{:,.2f}'.format # show only 2 decimal places

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.title = 'Sales and Inventory Trends'

# Load data

df = pd.read_csv('encoded_df.csv', parse_dates=['Date'])
# Variables:
available_categories = sorted(df['Category'].unique())

# Functions
def generate_table(dataframe, max_rows=10):

    return (
        # Header
        [html.Tr([html.Th(col) for col in dataframe.columns])] +
        # html.Th() is dash html syntax
        # list comprehension feeds a list to html.Tr()

        # Body
        [html.Tr([
            html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
            ]) for i in range(min(len(dataframe), max_rows))]
            # for loop of table rows
    )

# Set web elements
app.layout = html.Div([

        # 1. Recent Sales Table
        html.Div([
            html.H4(children='Recent Sales'),

            dcc.Dropdown(
                id='filter-category',
                options=[{'label': i, 'value':i} for i in available_categories],
                value=available_categories,
                multi=True
            ),
            dcc.Markdown('Rows to display'),
            dcc.Input(id='num-rows', type='text', value=10),


            html.Table(id='table1',
                        children=generate_table(df))
        ]), # END Recent Sales


        # 2. Historic Quantity Sold Table
        html.Div([
            # storage
            html.Div(id='filter-df', style={'display':'none'}),

            html.H4(children='Quantity Sold of Select Item'),
            # Filter product category
            dcc.Dropdown(
                id='select-agg-cat',
                options=[{'label': i, 'value':i} for i in available_categories],
                value='Beef'
            ),
            # Dynamic dropdown based on select-agg-cat
            dcc.Dropdown(
                id='select-agg-item'
            ),
            # date filter
            dcc.Markdown('Look back _ days (Leave blank for all-time records):'),
            dcc.Input(
                id='select-days-back',
                inputmode='numeric',
                placeholder=90
            ),
            # Pass states from [select-agg-cat, select-agg-item, select-days-back]
            html.Button(id='submit-button', n_clicks=0, children='Submit'),

            # Output avg and max sold as table
            html.Table(id='agg_table',
                children=None),
            # Visualize sales with chart
            dcc.Graph(id='sales-line')


        ]), # END Historic Quantity Sold Table

        # 3. Estimate yield from an animal
        html.Div([
            html.H4(children='Estimated Yield'),
            dcc.Markdown(children='Select category'),
            dcc.Dropdown(
                id='yield-category',
                options=[{'label': i, 'value':i} for i in available_categories],
                value=available_categories[0],
            ),

            # Date filter
            dcc.Markdown(children='Select dates for when product came back and ran out:'),
            dcc.DatePickerRange(
                id='yield-date-picker-range',
                min_date_allowed = min(df['Date']),
                max_date_allowed = max(df['Date']),
                initial_visible_month = min(df['Date']),
                end_date = max(df['Date'])
            ),
            # Divide product sold by number of animals
            dcc.Markdown(children='Enter number of animals sent between above dates'),
            dcc.Input(
                id='yield-num-animals',
                inputmode='numeric',
                min=1
            ),
            dcc.Markdown(children='Select Yield Units'),
            dcc.RadioItems(
                id = 'yield-units',
                options=[
                    {'label': 'Pounds', 'value': 'Lbs'},
                    {'label': 'Dollars', 'value': 'Dollars'}],
                value='Lbs'
            ),
            dcc.Markdown(children='Select level of aggregation'),
            dcc.RadioItems(
                id = 'yield-groupby',
                options=[
                    {'label': 'Tier', 'value': 'Tier'},
                    {'label': 'Item', 'value': 'Item'},
                    {'label': 'Total', 'value': 'Total'}],
                value='Tier'
            ),
            html.Button(id='yield-submit', n_clicks=0, children='Submit'),

            dcc.Graph(id='yield-bar-plot')




        ]) # END Estimate Yield




    ]) # END app.layout

# CALLBACKS

# Recent Sales Table
@app.callback(
    Output('table1', 'children'),
    [Input('filter-category', 'value'),
    Input('num-rows', 'value')]
)
def update_sales_table(categories, num_rows):
    dff = df[df['Category'].isin(categories)]
    dff = dff.sort_values('Date', ascending=False)
    return generate_table(dff, max_rows=int(num_rows))
# END Recent Sales


# Historic Quantity Sold Table
@app.callback(
    Output('select-agg-item', 'options'),
    [Input('select-agg-cat', 'value')]
)
def set_item_options(category):
    return [{'label': i, 'value':i} for i in \
             sorted(df[df['Category'] == category]['Item'].unique())]


@app.callback(
    Output('filter-df', 'children'),
    [Input('submit-button', 'n_clicks')],
    [State('select-agg-cat', 'value'),
    State('select-agg-item', 'value'),
    State('select-days-back', 'value')]
)
def filter_df2item(n_clicks, category, item, days_back):
    '''Designed to see check how an item has been performing and if it would be okay
        to pack less of that item'''

    # 1. Filter down to item: requires both category and individual item selected
        # This allows not having to group by item
    dff = df[(df['Category'] == category) & (df['Item'] == item)]
    dff = dff.drop(columns='Tier')
    if days_back:
        cutoff_date = pd.Timestamp.today() - datetime.timedelta(days=int(days_back))
        dff = dff[dff['Date'] > cutoff_date]
        # else: return all-time sales
    return dff.to_json(date_format='iso', orient='split')

@app.callback(
     Output('agg_table', 'children'),
     [Input('filter-df', 'children')]
 )
def update_agg_Table(jsonified_cleaned_data):

    dff = pd.read_json(jsonified_cleaned_data, orient='split')
    # 2. Count number sold of each item at each market
    counts = dff.groupby(['Location', 'Date'], as_index=False)\
                        .agg({'Weight':'count'})

    # 3. Aggregate those counts within each market location
    performance = counts.groupby(['Location'])\
                    .agg({'Weight': ['max', 'count', 'sum', 'mean']})\
                    .reset_index()\
                    .rename(columns={
                                    'count': 'Number of days with at least one sale',
                                    'sum': 'Total Sold',
                                    'mean': 'Average sold per market',
                                    'max': 'Max sold at one market'
                                    })
    # list comprehension for condensing multi level column index
    performance.columns = [col[0] if col[1] == '' else col[1] for col in performance.columns]

    # 4. Show most recent date when the maximum sold occurred
        # a. Join on Location and Maximum Sold (aliases: Weight, Max sold at one market),
        #       giving dates of when Maximum Sold occurred
        # b. Take the max to get the most recent date
    with_dates = performance.merge(counts,
                            right_on=[ 'Location', 'Weight'],
                            left_on=['Location', 'Max sold at one market'])\
                    .groupby(['Location', 'Number of days with at least one sale',
                                'Total Sold', 'Average sold per market',
                                'Max sold at one market']) \
                    .agg({'Date': 'max'})\
                    .reset_index()
    with_dates['Average sold per market'] = round(with_dates['Average sold per market'], 2)
    with_dates = with_dates.sort_values('Location')

    return generate_table(with_dates)

@app.callback(
    Output('sales-line', 'figure'),
    [Input('filter-df', 'children')]
)
def sales_trends(jsonified_cleaned_data):
    '''Visualize the actual sales to see if there's any nuance to the avg calculated
    '''
    dff = pd.read_json(jsonified_cleaned_data, orient='split')
    item = dff['Item'].values[0] # should all be same item
    glo_cnts = dff.groupby('Date')['Net Sales'].count()
    traces = []

    for location in dff['Location'].unique():
        counts = dff[dff['Location'] == location].groupby('Date')['Net Sales'].count()
        traces.append(go.Scatter(x=counts.index,
                                 y=counts.values,
                                 mode = 'markers',
                                 name = location
                                ))

    return {
        'data': traces,
        'layout': go.Layout(
            title = f'Recent Sales Trends for {item}',
            yaxis = dict(title='Quantity Sold',
                    range=[0, glo_cnts.max()+1]),

            xaxis=dict(title='Date')
        )
    }


# END Quantity Sold

# Estimate Yield
@app.callback(
    Output('yield-bar-plot', 'figure'),
    [Input('yield-submit', 'n_clicks')],
    [State('yield-date-picker-range', 'start_date'),
    State('yield-date-picker-range', 'end_date'),
    State('yield-num-animals', 'value'),
    State('yield-category', 'value'),
    State('yield-units', 'value'),
    State('yield-groupby', 'value')]
)
def estimate_yield(n_clicks, start_date, end_date, num_animals, category, units, grp):
    '''Plot bar chart of estimated yield, calculated by product sold
    between dates given divided by number of animals sent to slaughter
    '''
    # Filter
        # note: check how long this takes and if numpy is notably faster

    dff = df[(df['Date'] >= start_date) & \
              (df['Date'] <= end_date) & \
              (df['Category'] == category)]

    n =  int(num_animals)

    # Set units col
    if units == 'Lbs':
        col = 'Weight'

    elif units == 'Dollars':
        col = 'Net Sales'

    # Show total as a number
    if grp=='Total':
        return {
            'data': [
                go.Pie(labels=[category],
                       values=[np.round(dff[col].sum()/n, 2)],
                       textinfo='value',
                       textfont=dict(size=24, ),
                       marker=dict(colors=['#006400'],line=dict(color='#000000', width=2)))
        ],
        'layout': go.Layout(
            title=f'Estimated Yield in {units} from Slaughter, on per animal basis')
        }
    else:
        by_tier = dff.groupby(grp)[col].sum().sort_values(ascending=False)



    return {
        'data': [
            go.Bar(
                y = by_tier.index[:10],
                x =np.round(by_tier.values/n, 2)[:10],
                name = 'Estimated Yield (Top 10)',
                orientation ='h'
            )
            ],
        'layout': go.Layout(
            title=f'Estimated Yield in {units} from Slaughter, on per animal basis',
            yaxis = dict(
                title = f'{grp}',
                automargin=True,
                type='category'
            ),
            xaxis = dict(
                title= f'Yield in {units}'
            )

            # showlegend=True,
            # legend=go.layout.Legend(
            #     x=0,
            #     y=1
            # )
            )
    }






# RUN APP

if __name__ == '__main__':
    app.run_server(debug=True)

