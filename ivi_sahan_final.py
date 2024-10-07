import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State, ALL
import pandas as pd
import plotly.express as px
import json
from plotly.colors import sample_colorscale
import re  # For natural sorting

# Helper function for natural sorting
def extract_number(district_name):
    """
    Extracts the numerical part from a district name.
    Example: "Kreis 10" -> 10
    """
    match = re.search(r'\d+', district_name)
    return int(match.group()) if match else float('inf')  # Push non-matching to end

# Load the data
csv_data = pd.read_csv('1_Zurich_Einbrueche_2009-2023.csv') 
population_data = pd.read_csv('Bevölkerungsanzahl.csv')
with open('stzh.adm_stadtkreise_a.json') as f:
    zurich_geojson = json.load(f)

# Ensure column names are consistent
population_data.rename(columns={'Jahr': 'Year'}, inplace=True)
csv_data.rename(columns={'Ausgangsjahr': 'Year'}, inplace=True)

# Convert 'Year' columns to integers if necessary
population_data['Year'] = population_data['Year'].astype(int)
csv_data['Year'] = csv_data['Year'].astype(int)

# Merge burglary data with population data on district and year
merged_data = pd.merge(
    csv_data,
    population_data[['KreisLang', 'Year', 'AnzBestWir']],
    left_on=['Stadtkreis_Name', 'Year'],
    right_on=['KreisLang', 'Year'],
    how='left'
)

# Handle missing population data
merged_data = merged_data.dropna(subset=['AnzBestWir'])

# Calculate normalized burglary rate (e.g., per 1000 inhabitants)
merged_data['Burglary_rate_per_1000'] = (merged_data['Straftaten_total'] / merged_data["AnzBestWir"]) * 1000

# Calculate total burglaries across all years (2009-2023)
total_burglaries_all_years = merged_data['Straftaten_total'].sum()
total_burglary_rate_all_years = merged_data['Burglary_rate_per_1000'].sum()

# Get sorted list of unique districts
districts_sorted = sorted(merged_data['Stadtkreis_Name'].unique(), key=extract_number)

# Initialize the app with a light Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

# App layout
app.layout = dbc.Container([
    dcc.Store(id='selected-metric', data='Burglary_rate_per_1000'),  # Store for selected metric
    dcc.Store(id='selected-districts', data=[]),  # Store for selected districts

    # Title and Cards Row
    dbc.Row([
        dbc.Col([
            # Main title in Helvetica and bold
            html.H1("🔍 Overview of Yearly Burglaries in Zurich", 
                    className="text-center mb-1",
                    style={"font-family": "Helvetica", "font-weight": "bold", "font-size": "36px"}
            ),
            # Subtitle in Times New Roman and italic
            html.H4("Data gathered from 2009 to 2023", 
                    className="text-center", 
                    style={"font-family": "Times New Roman", "font-style": "italic"}
            ),
            # Data source with hyperlink
            html.H5([
                html.Span(
                    "📑 Source: ",
                    style={"color": "grey", "font-size": "16px"}
                ),
                html.A(
                    "Stadt Zürich Open Data",
                    href="https://data.stadt-zuerich.ch/dataset/ktzh_pks_einbrueche_gemeinden_stadtkreise",
                    target="_blank",
                    style={"color": "grey", "font-size": "16px"}
                ),
                html.Span("|", style={'color':'grey', "margin": "5px"}), 
                html.Span(
                    "© Sahan Hatemo",
                    id="infosahan",
                    style={"color": "grey", "font-size": "16px", "cursor": "pointer",}
                ),
                dbc.Tooltip(
                    "sahan.hatemo@students.fhnw.ch",
                    target="infosahan",  # Reference the ID of the target span
                    placement="right",      # Position of the tooltip
                    className="custom-tooltip-style",
                    style={"color":"rgba(171, 226, 251, 0.9)"}
                )
            ],
                className="text-center",
                style={"font-family": "Times New Roman", "font-style": "italic", "font-size": "16px"}
            ),
        ], style={"margin-bottom": "5px", "margin-top": "20px"}, width=12)
    ]),
    
    html.Hr(style={
        'width': '66%',
        'borderWidth': '1.5px', 
        'borderColor': '#696969', 
        'marginLeft': 'auto', 
        'marginRight': 'auto'
    }),

    # Metric selection buttons with shadow added
    dbc.Row([
        dbc.Col([
            dbc.Button(
                "Normalized Burglary Rate", 
                id="button-burglary-rate",
                className="metric-button",  # Assign class for easier CSS targeting
                n_clicks=0,
                style={
                    "margin-right": "10px",  # Adds space to the right of this button
                    "padding": "10px 20px",
                    "border": "none"  # Remove default border
                }
            ),
            dbc.Button(
                "Total Burglaries", 
                id="button-total-burglaries",
                className="metric-button",  # Assign class for easier CSS targeting
                n_clicks=0,
                style={
                    "margin-left": "10px",  # Adds space to the left of this button
                    "padding": "10px 20px",
                    "border": "none"   # Remove default border
            }
            ),
        ], width=12, style={'text-align': 'center', 'margin-bottom': '0px'})
    ]),

    # Tooltips for buttons
    dbc.Tooltip(
        "This option shows the burglary rate per 1'000 inhabitants for each district",
        target="button-burglary-rate",
        placement="left"
    ),
    dbc.Tooltip(
        "This option shows the total number of burglaries reported in each district",
        target="button-total-burglaries",
        placement="right"
    ),

    html.Hr(style={
        'width': '66%',
        'borderWidth': '1.5px', 
        'borderColor': '#696969', 
        'marginLeft': 'auto', 
        'marginRight': 'auto'
    }),

    # Cards Row (Total Burglaries, Safest District, Vulnerable District)
    dbc.Row([
        dbc.Col([
            dbc.Card(
                html.Div([
                    # Card content
                    html.Div([
                        html.H4(id='dynamic-title', className="card-title text-center", style={
                            "font-family": "Helvetica", "font-weight": "bold", "font-size": "18px"
                        }),
                        html.Div([
                            html.H5(id="total-burglaries", className="card-text text-center", style={
                                "font-family": "Times New Roman", "font-style": "italic", "font-size": "16px",
                                "display": "inline-block"
                            }),
                            html.Span("|", style={"margin": "0 10px"}),                
                            html.H6(id="total-burglaries-percentage", className="text-success text-center", style={
                                "font-family": "Times New Roman", "font-style": "italic", "font-size": "16px",
                                "display": "inline-block"
                            }),
                        ], className="text-center")
                    ], className="d-flex flex-column align-items-center justify-content-center", style={"height": "100%"}),  # Added flex styling here

                    # Tooltip overlay
                    html.Div(
                        [
                            "This card displays the total number of burglaries in Zurich",
                            html.Br(),
                            "for the selected year range"
                        ],
                        className="card-tooltip"
                    )
                ], className="card-hover h-100 d-flex align-items-center justify-content-center"),  # Flex styling for card-hover container
                className="mb-4",
                id='total-burglaries-card',
                style={
                    "height": "90px",
                    "background-color": "#ffffff",  # White background
                    "padding": "10px",
                    "border-radius": "10px",
                    "box-shadow": "0 6px 10px 6px rgba(0, 0, 0, 0.1)", 
                    "border": "none",
                }
            )
        ], width=4),

        # Safest District Card (With hover effect)
        dbc.Col([
            dbc.Card(
                html.Div([
                    # Card content
                    html.Div([
                        html.H4("🔒 Safest District", className="card-title text-center", style={
                            "font-family": "Helvetica", "font-weight": "bold", "font-size": "18px"
                        }),
                        html.H5(id="safest-stadtkreis", className="card-text text-center", style={
                            "font-family": "Times New Roman", "font-style": "italic", "font-size": "16px"
                        })
                    ], className="d-flex flex-column align-items-center justify-content-center", style={"height": "100%"}), # Added flex styling here
                    # Tooltip overlay
                    html.Div(
                        "Safest district according to chosen metric and year range",
                        className="card-tooltip"
                    )
                ], className="card-hover h-100 d-flex align-items-center justify-content-center"),  # Flex styling for card-hover container
                className="mb-4",
                id='safest-stadtkreis-card',
                style={
                    "height": "90px",
                    "background-color": "#ffffff",  # White background
                    "padding": "10px",
                    "border-radius": "10px",
                    "box-shadow": "0 6px 10px 6px rgba(0, 0, 0, 0.1)", 
                    "border": "none",
                }
            )], width=2),

        # Vulnerable District Card (With hover effect)
        dbc.Col([
            dbc.Card(
                html.Div([
                    # Card content
                    html.Div([
                        html.H4("🔓 Vulnerable District", className="card-title text-center", style={
                            "font-family": "Helvetica", "font-weight": "bold", "font-size": "18px"
                        }),
                        html.H5(id="dangerous-stadtkreis", className="card-text text-center", style={
                            "font-family": "Times New Roman", "font-style": "italic", "font-size": "16px"
                        })
                    ], className="d-flex flex-column align-items-center justify-content-center", style={"height": "100%"}), # Added flex styling here
                    # Tooltip overlay
                    html.Div(
                        "Most vulnerable district according to chosen metric and year range",
                        className="card-tooltip"
                    )
                ], className="card-hover h-100 d-flex align-items-center justify-content-center"),  # Flex styling for card-hover container
                className="mb-4",
                id='dangerous-stadtkreis-card',
                style={
                    "height": "90px",
                    "background-color": "#ffffff",  # White background
                    "padding": "10px",
                    "border-radius": "10px",
                    "box-shadow": "0 6px 10px 6px rgba(0, 0, 0, 0.1)", 
                    "border": "none",
                }
            )], width=2),
    ], justify="center"),

    # Year slider and District Filter with Circles
    dbc.Row([
        # Year Slider Card
        dbc.Col([
            dbc.Card(
                [
                    html.H4(className="text-center", style={
                        "font-family": "Helvetica", "font-weight": "bold", "font-size": "18px", "margin-bottom": "15px"
                    }),
                    dcc.RangeSlider(
                        id='year-slider',
                        min=merged_data['Year'].min(),
                        max=merged_data['Year'].max(),
                        step=1,
                        marks={str(year): str(year) for year in sorted(merged_data['Year'].unique())},
                        value=[merged_data['Year'].min(), merged_data['Year'].max()],
                        className="mb-4",
                        tooltip={"placement": "bottom", "always_visible": False},
                    ),
                ],
                id='year-slider-card',
                style={
                    "padding": "20px",
                    "border-radius": "10px",
                    "box-shadow": "0 6px 10px 6px rgba(0, 0, 0, 0.1)",
                    "border": "none",
                    "height": "100px",  # Ensuring this matches the filter card
                    "background-color": "#ffffff" # White background
                }
            ),
                dbc.Tooltip(
                "Drag the year slider to select a range of years or pin point a single year",
                target="year-slider-card",
                placement="left"
                ),

        ], style={"margin-bottom": "5px"}, width=5),

        # District Filter Card with Circles
        dbc.Col([
            dbc.Card(
                [
                    # Circles for District Selection
                    html.Div(
                        [
                            dbc.Button(
                                f"{extract_number(district)}",
                                id={'type': 'district-button', 'index': district},
                                className='metric-button district-circle',  # Combined classes
                                n_clicks=0
                            )
                            for district in districts_sorted
                        ],
                        className='d-flex flex-wrap justify-content-center',
                        style={'gap': '10px',
                               'margin-top': '-10px',
                               'margin-bottom': '15px'
                               }
                    ),
                    # Reset Filters Button
                    dbc.Button(
                        id="button-reset-filters",
                        className="metric-button",
                        n_clicks=0,
                        style={
                            'display':"none"
                        }
                    ),
                ],
                id='district-filter-card',
                style={
                    "padding": "20px",
                    "border-radius": "10px",
                    "box-shadow": "0 6px 10px 6px rgba(0, 0, 0, 0.1)",
                    "border": "none",
                    "height": "100px",  # Match Year Slider height
                    "background-color": "#ffffff"
                }
            ),
            dbc.Tooltip(
                "Click on the circles to filter districts",
                target="district-filter-card",
                placement="right"
            ),
        ], style={"margin-bottom": "5px"}, width=3)
    
    ], justify="center"),

    # Horizontal Line
    html.Hr(style={
        'width': '66%',
        'borderWidth': '1.5px', 
        'borderColor': '#696969', 
        'marginLeft': 'auto', 
        'marginRight': 'auto'
    }),

    # Choropleth Map and Bar Chart Row
    dbc.Row([
        dbc.Col([
            html.Div(
                dcc.Graph(id='choropleth-map', style={
                    "padding": "10px", "margin": "0", "height": "400px", "width": "100%"
                }),
                style={
                    "border-radius": "10px",
                    "overflow": "hidden",
                    "box-shadow": "0 6px 10px 6px rgba(0, 0, 0, 0.1)",
                    "background-color": "#ffffff",  # White background
                    "border": "none", 
                    "width": "470px",
                    "height": "345px",
                }
            )
        ], width=4, style={"padding": "0", "margin-left": "35px"}),
        dbc.Col([
            html.Div(
                dcc.Graph(id='bar-chart', style={
                    "padding": "10px", "margin": "0", "width": "100%"
                }),
                style={
                    "border-radius": "10px",
                    "overflow": "hidden",
                    "box-shadow": "0 6px 10px 6px rgba(0, 0, 0, 0.1)",
                    "background-color": "#ffffff",  # White background
                    "border": "none",
                    "width": "470px",
                    "height": "345px",  
                }
            )
        ], width=4, style={"padding": "0px", "margin-left": "10px"}),
    ], justify="center", style={"width": "100%"})
], fluid=True)

# Callback to update metric button classes and selected metric
@app.callback(
    [Output("button-burglary-rate", "className"),
     Output("button-total-burglaries", "className"),
     Output("selected-metric", "data")],
    [Input("button-burglary-rate", "n_clicks"),
     Input("button-total-burglaries", "n_clicks")],
    [State("selected-metric", "data")]
)
def update_button_states(rate_clicks, total_clicks, selected_metric):
    # Set default class names
    rate_class = "metric-button"
    total_class = "metric-button"

    # Handle None values for n_clicks (initial state)
    rate_clicks = rate_clicks or 0
    total_clicks = total_clicks or 0

    # Determine which input triggered the callback
    ctx = dash.callback_context
    if not ctx.triggered:
        # App initialization (default state)
        rate_class += " active"
        selected_metric = "Burglary_rate_per_1000"
    else:
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if triggered_id == "button-burglary-rate":
            rate_class += " active"
            selected_metric = "Burglary_rate_per_1000"
        elif triggered_id == "button-total-burglaries":
            total_class += " active"
            selected_metric = "Straftaten_total"

    return rate_class, total_class, selected_metric

# Callback to handle district selection via circles and reset filters
@app.callback(
    Output('selected-districts', 'data'),
    [
        Input({'type': 'district-button', 'index': ALL}, 'n_clicks'),
        Input('button-reset-filters', 'n_clicks')
    ],
    [
        State({'type': 'district-button', 'index': ALL}, 'id'),
        State('selected-districts', 'data')
    ]
)
def update_selected_districts(district_n_clicks, reset_n_clicks, ids, selected_districts):
    ctx = dash.callback_context

    if not ctx.triggered:
        return selected_districts
    else:
        triggered = ctx.triggered[0]
        prop_id = triggered['prop_id'].split('.')[0]

        if prop_id == 'button-reset-filters':
            # Reset filters: deselect all districts
            return []
        else:
            # It must be a district button
            try:
                button_id = json.loads(prop_id)
                district_name = button_id['index']
            except:
                return selected_districts

            if district_name in selected_districts:
                selected_districts = [d for d in selected_districts if d != district_name]
            else:
                selected_districts = selected_districts + [district_name]

            return selected_districts

# Callback to update district button classes based on selection
@app.callback(
    Output({'type': 'district-button', 'index': ALL}, 'className'),
    [Input('selected-districts', 'data')],
    [State({'type': 'district-button', 'index': ALL}, 'id')]
)
def update_district_button_classes(selected_districts, button_ids):
    return [
        'metric-button district-circle active' if button_id['index'] in selected_districts else 'metric-button district-circle'
        for button_id in button_ids
    ]


def display_selected_districts(selected_districts):
    if not selected_districts:
        return "All Districts Selected"
    return f"Selected Districts: {', '.join(selected_districts)}"

# Callback for Reset Filters Button
# Already handled in the merged district selection callback above
# No separate callback is needed for resetting 'selected-districts'

# Separate callback for updating the dashboard
@app.callback(
    [
        Output('total-burglaries', 'children'),
        Output('total-burglaries-percentage', 'children'),
        Output('safest-stadtkreis', 'children'),
        Output('dangerous-stadtkreis', 'children'),
        Output('choropleth-map', 'figure'),
        Output('bar-chart', 'figure'),
        Output('dynamic-title', 'children'),
    ],
    [
        Input('year-slider', 'value'),
        Input('selected-metric', 'data'),
        Input('selected-districts', 'data')
    ]
)
def update_dashboard(selected_years, selected_metric, selected_districts):
    # Map the selected_metric to a label
    metric_label = 'Burglaries' if selected_metric == 'Straftaten_total' else 'Burglaries'

    # Filter data for the selected year range
    filtered_data = merged_data[
        (merged_data['Year'] >= selected_years[0]) &
        (merged_data['Year'] <= selected_years[1])
    ]
    
    # Handle district filter
    if selected_districts and selected_districts != []:
        filtered_data = filtered_data[filtered_data['Stadtkreis_Name'].isin(selected_districts)]
    else:
        # If no districts are selected, show all
        filtered_data = merged_data[
            (merged_data['Year'] >= selected_years[0]) &
            (merged_data['Year'] <= selected_years[1])
        ]

    # Handle missing population data
    filtered_data = filtered_data.dropna(subset=['AnzBestWir'])
    
    # Calculate total burglaries and percentage for the total burglaries card
    total_burglaries = filtered_data['Straftaten_total'].sum()
    percentage_of_total_burglaries = (total_burglaries / total_burglaries_all_years) * 100

    # Find the safest and most dangerous districts based on the selected metric
    if not filtered_data.empty:
        safest_stadtkreis = filtered_data.groupby('Stadtkreis_Name')[selected_metric].mean().idxmin()
        dangerous_stadtkreis = filtered_data.groupby('Stadtkreis_Name')[selected_metric].mean().idxmax()
    else:
        safest_stadtkreis = "N/A"
        dangerous_stadtkreis = "N/A"
    
    # Aggregate data for charts
    if selected_metric == 'Straftaten_total':
        filtered_data_agg = filtered_data.groupby('Stadtkreis_Name').agg({
            'Straftaten_total': 'sum',
            'Burglary_rate_per_1000': 'mean'
        }).reset_index()
    else:
        filtered_data_agg = filtered_data.groupby('Stadtkreis_Name').agg({
            'Burglary_rate_per_1000': 'mean',
            'Straftaten_total': 'sum'
        }).reset_index()
    
    # Define the continuous color scale (Blues)
    color_scale = px.colors.sequential.Blues
    
    # Choropleth Map
    fig_map = px.choropleth_mapbox(
        filtered_data_agg,
        geojson=zurich_geojson,
        locations='Stadtkreis_Name',
        featureidkey="properties.bezeichnung",
        color=selected_metric,
        custom_data=['Straftaten_total', 'Burglary_rate_per_1000'],
        labels={
            'Burglary_rate_per_1000': 'Burglary Rate per 1000',
            'Straftaten_total': 'Total Burglaries',
            'Stadtkreis_Name': 'District'
        },
        mapbox_style="carto-positron",
        zoom=10.3,
        center={"lat": 47.3769, "lon": 8.5417},
        color_continuous_scale=color_scale,
    )
    
    # Update hovertemplate
    fig_map.update_traces(
        hovertemplate="<b>District:</b> %{location}<br>" +
                      '<b>Burglary Rate per 1000:</b> %{customdata[1]:.0f}<br>' +
                      '<b>Total Burglaries:</b> %{customdata[0]:.0f}<br>' +
                      "<extra></extra>"
    )
    
    fig_map.update_layout(
        height=325,
        width=440,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_showscale=True,
        coloraxis_colorbar=dict(
            title=metric_label,
            ticks="outside",
        ),
        font=dict(family="Times New Roman", size=12, color="black", style="italic")
    )
    
    # Prepare data for the bar chart
    top12_data = filtered_data_agg.sort_values(by=selected_metric, ascending=False).head(12).reset_index(drop=True)
    top12_data['color'] = top12_data[selected_metric] / top12_data[selected_metric].max()
    
    # Round values if necessary
    if selected_metric == 'Burglary_rate_per_1000':
        top12_data['display_value'] = top12_data[selected_metric].round(0)
    else:
        top12_data['display_value'] = top12_data[selected_metric]
    
    # Calculate the average value
    if not filtered_data_agg.empty and len(filtered_data_agg) > 1:
        avg_value = filtered_data_agg[selected_metric].mean()
    else:
        avg_value = None  # No average line if only one district
    
    # Create the bar chart
    fig_bar = px.bar(
        top12_data,
        x='Stadtkreis_Name',
        y='display_value',
        custom_data=['Straftaten_total', 'Burglary_rate_per_1000'],
        labels={
            'display_value': metric_label,
            'Stadtkreis_Name': 'District'
        }
    )
    
    # Update the layout
    fig_bar.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(
            showgrid=True,
            gridcolor='#F0F0F0',
            gridwidth=1,
            title=None,
            showticklabels=False
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor='#F0F0F0',
            gridwidth=1,
            title=None
        ),
        height=325,
        width=450,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        font=dict(family="Times New Roman", size=12, color="black", style="italic")
    )
    
    # Update traces
    fig_bar.update_traces(
        marker_color=top12_data['color'].apply(lambda x: sample_colorscale(color_scale, x)[0]),
        texttemplate='%{y}',
        textposition='outside',
        hovertemplate='<b>District:</b> %{x}<br>' +
                      '<b>Burglary Rate per 1000:</b> %{customdata[1]:.0f}<br>' +
                      '<b>Total Burglaries:</b> %{customdata[0]:.0f}<br>' +
                      '<extra></extra>'
    )
    
    if avg_value is not None:
        fig_bar.add_hline(
            y=avg_value,
            line_dash="longdash",
            annotation_text=f"Average {selected_years[0]} - {selected_years[1]}: {avg_value:.0f}",
            annotation_font_color="red",
            annotation_position="top right",
            line_color="red",
            opacity=0.5
        )

    
    # Update total burglaries and percentage text
    total_burglaries_text = f"{int(total_burglaries):,} burglaries"
    percentage_text = f"{percentage_of_total_burglaries:.2f}% of total burglaries"
    safest_text = f"{safest_stadtkreis}"
    dangerous_text = f"{dangerous_stadtkreis}"
    
    # Dynamic title
    if selected_years[0] == selected_years[1]:
        dynamic_title = f"📌 Burglaries in {selected_years[0]}"
    else:
        dynamic_title = f"⛓️ Burglaries between {selected_years[0]} - {selected_years[1]}"
    
    # Return updated figures and text
    return (
        total_burglaries_text,
        percentage_text,
        safest_text,
        dangerous_text,
        fig_map,
        fig_bar,
        dynamic_title
    )

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, port=8110)
