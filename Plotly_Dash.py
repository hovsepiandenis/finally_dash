import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Загрузка данных
df = pd.read_csv('WA_Fn-UseC_-Telco-Customer-Churn.csv')
churn_counts = df['Churn'].value_counts()

# Преобразуем столбец SeniorCitizen в категориальные значения
df['SeniorCitizen'] = df['SeniorCitizen'].apply(lambda x: 'Yes' if x == 1 else 'No')

# Обновляем список категориальных столбцов
excluded_columns = ['customerID', 'TotalCharges']
categorical_columns = [col for col in df.columns if df[col].dtype == 'object' and col not in excluded_columns]

# Инициализация приложения Dash с suppress_callback_exceptions
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Создание круговой диаграммы
fig = go.Figure(
    go.Pie(
        values=churn_counts,
        labels=churn_counts.index,
        hole=0.6,
        marker=dict(colors=['#4682B4', '#FF7F50']),
        textinfo='percent',
        textposition='outside'
    )
)

# Добавляем аннотацию для общего количества клиентов
fig.update_layout(
    showlegend=False,
    title="Total counts of customers",
    annotations=[
        dict(
            text=f"Total counts of customers:<br>{df.shape[0]}",
            x=0.5, y=0.5, font_size=12, showarrow=False,
            font=dict(color="#000080")
        )
    ]
)

# Основной макет приложения
app.layout = html.Div([
    html.H1("Telco Customer Churn"),

    # Раздел с круговой диаграммой
    html.Div([
        dcc.Graph(id='churn-pie-chart', figure=fig)
    ], style={'display': 'flex', 'justify-content': 'center', 'margin-bottom': '40px'}),

    html.Hr(),

    # Dropdown для первого графика с постоянным заголовком
    html.Div([
        html.H3("Select a column for analysis"),
        dcc.Dropdown(
            id='dropdown',
            options=[{'label': col, 'value': col} for col in categorical_columns],
            value='gender',  # Значение по умолчанию
            placeholder="Select a column for analysis"
        ),
        dcc.Graph(id='bar-graph', config={'scrollZoom': False})
    ]),
    
    html.Hr(),

    # Второй график - гистограмма с динамическими бинами
    html.Div([
        html.H1("Customer Tenure Histogram"),
        dcc.Graph(id='dynamic-histogram', config={'scrollZoom': True})
    ]),

    html.Hr(),

    # Третий график - распределение оттока по месячному доходу
    html.Div([
        html.H1("Churn by Monthly Charges"),
        dcc.Graph(id='monthly-charges-churn')
    ]),

    html.Hr(),

    # Четвертый график - анализ TotalCharges для клиентов с высоким значением
    html.Div([
        html.H1("High TotalCharges Customer Retention Analysis"),
        dcc.Graph(id='high-totalcharges-graph', config={'scrollZoom': True})
    ])
])

# Callback для четвертого графика
@app.callback(
    Output('high-totalcharges-graph', 'figure'),
    Input('high-totalcharges-graph', 'relayoutData')
)
def update_high_totalcharges_graph(relayout_data):
    # Обработка пустых значений и преобразование в числовой тип
    df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce')
    high_totalcharges_df = df.dropna(subset=['TotalCharges'])
    high_totalcharges_df = high_totalcharges_df[high_totalcharges_df['TotalCharges'] > 3000]

    bin_size = 100
    if relayout_data and 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
        x_range = [relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']]
        range_span = x_range[1] - x_range[0]
        if range_span < 500:
            bin_size = 50
        elif range_span < 1000:
            bin_size = 100
        else:
            bin_size = 200

    fig = go.Figure()
    for churn_value, color in zip(['Yes', 'No'], ['#FF7F50', '#4682B4']):
        fig.add_trace(
            go.Histogram(
                x=high_totalcharges_df[high_totalcharges_df['Churn'] == churn_value]['TotalCharges'],
                name=f"{churn_value} - Churn",
                marker_color=color,
                xbins=dict(size=bin_size),
                opacity=0.6
            )
        )

    fig.update_layout(
        title="Distribution of High TotalCharges Customers by Churn Status",
        xaxis_title="Total Charges",
        yaxis_title="Count of Customers",
        plot_bgcolor="white",
        bargap=0.1,
        barmode="overlay"
    )
    return fig

# Callback для первого графика
@app.callback(
    Output('bar-graph', 'figure'),
    [Input('dropdown', 'value')]
)
def update_graph(selected_column):
    grouped_df = df.groupby([selected_column, 'Churn']).size().reset_index(name='count')
    total_df = df.groupby([selected_column]).size().reset_index(name='count')
    total_df['Churn'] = 'Total'
    grouped_df = pd.concat([grouped_df, total_df], ignore_index=True)
    grouped_df['Churn'] = pd.Categorical(grouped_df['Churn'], categories=['Total', 'No', 'Yes'], ordered=True)
    grouped_df = grouped_df.sort_values(['Churn', selected_column])
    
    fig = px.bar(
        grouped_df, 
        x=selected_column, 
        y='count', 
        color='Churn', 
        barmode='group', 
        title=f"Churn Count by {selected_column}",
        color_discrete_map={'Total': '#808080', 'No': '#4682B4', 'Yes': '#FF7F50'}
    )
    fig.update_traces(hovertemplate='<br>%{x}<br>Count: %{y}<extra></extra>')
    fig.update_layout(
        xaxis_title=selected_column,
        yaxis_title="Count",
        bargap=0.2,
        hovermode='closest'
    )
    return fig

# Callback для второго графика - гистограммы с динамическими бинами
@app.callback(
    Output('dynamic-histogram', 'figure'),
    [Input('dynamic-histogram', 'relayoutData')]
)
def update_histogram(relayout_data):
    bin_size = 5
    if relayout_data and 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
        x_range = [relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']]
        range_span = x_range[1] - x_range[0]
        if range_span < 20:
            bin_size = 1
        elif range_span < 50:
            bin_size = 2
        elif range_span < 100:
            bin_size = 5
        else:
            bin_size = 10

    fig = go.Figure()
    for churn_value, color in zip(['Yes', 'No'], ['#FF7F50', '#4682B4']):
        fig.add_trace(
            go.Histogram(
                x=df[df['Churn'] == churn_value]['tenure'],
                name=f"{churn_value} - Churn",
                marker_color=color,
                xbins=dict(size=bin_size),
                opacity=0.6
            )
        )
    fig.update_layout(
        title='Customer Tenure Histogram',
        xaxis_title='Tenure',
        yaxis_title='Count',
        plot_bgcolor='white',
        bargap=0.1,
        barmode='overlay'
    )
    return fig

# Callback для третьего графика - распределение оттока по месячному доходу
@app.callback(
    Output('monthly-charges-churn', 'figure')
)
def update_monthly_charges_chart():
    fig = px.histogram(
        df, 
        x='MonthlyCharges', 
        color='Churn', 
        barmode='overlay',
        title="Distribution of Churn by Monthly Charges",
        color_discrete_map={'Yes': '#FF7F50', 'No': '#4682B4'}
    )
    fig.update_layout(
        xaxis_title='Monthly Charges',
        yaxis_title='Count',
        bargap=0.1,
        hovermode='x'
    )
    return fig

if __name__ == "__main__":
    app.run(debug = True)
