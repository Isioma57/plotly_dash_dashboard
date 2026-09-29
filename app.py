"""Standalone Supermart Dash application for local use and Render deployment."""

from pathlib import Path
import os

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html


# -----------------------------------------------------------------------------
# 1. Load and prepare the data
# -----------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "Supermart Grocery Sales.csv"


def load_data():
    """Load the CSV and safely convert its two date formats."""
    data = pd.read_csv(DATA_PATH)

    date_text = data["Order Date"].astype("string").str.strip()
    slash_dates = date_text.str.contains("/", regex=False)

    parsed_dates = pd.Series(pd.NaT, index=data.index, dtype="datetime64[ns]")
    parsed_dates.loc[slash_dates] = pd.to_datetime(
        date_text.loc[slash_dates],
        format="%m/%d/%Y",
        errors="coerce",
    )
    parsed_dates.loc[~slash_dates] = pd.to_datetime(
        date_text.loc[~slash_dates],
        format="%d-%m-%Y",
        errors="coerce",
    )

    if parsed_dates.isna().any():
        failed_rows = int(parsed_dates.isna().sum())
        raise ValueError(f"{failed_rows} order dates could not be converted.")

    data["Order Date"] = parsed_dates
    data["Year"] = data["Order Date"].dt.year.astype(int)
    return data


df = load_data()


# -----------------------------------------------------------------------------
# 2. Reusable calculations and Plotly figures
# -----------------------------------------------------------------------------

# NEW PALETTE: teal family with coral, indigo and amber accents.
COLORS = {
    "navy": "#102A43",
    "text": "#243B53",
    "sales": "#8FD3C3",    # soft mint teal
    "profit": "#0F766E",   # deep teal
    "coral": "#F26B5B",
    "indigo": "#4F46E5",
    "amber": "#F5A524",
}


def calculate_kpis(data):
    total_sales = data["Sales"].sum()
    total_profit = data["Profit"].sum()
    total_orders = data["Order ID"].nunique()
    profit_margin = total_profit / total_sales if total_sales else 0
    return total_sales, total_profit, total_orders, profit_margin


def polish_figure(figure):
    """Apply the same professional appearance to every Plotly figure."""
    figure.update_layout(
        height=390,
        margin=dict(l=35, r=25, t=65, b=40),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Segoe UI, Arial, sans-serif", color=COLORS["text"]),
        title=dict(x=0.02, xanchor="left", font=dict(size=18, color=COLORS["navy"])),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title_text="",
        ),
        bargap=0.25,
        bargroupgap=0.05,
    )
    figure.update_xaxes(showgrid=False, zeroline=False)
    figure.update_yaxes(gridcolor="#EEF2F7", zeroline=False)
    return figure


def make_category_chart(data):
    category_data = (
        data.groupby("Category", as_index=False)
        .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
    )

    figure = px.bar(
        category_data,
        x="Category",
        y=["Sales", "Profit"],
        barmode="group",
        title="Sales and Profit by Category",
        labels={"value": "Amount", "variable": "Measure"},
        color_discrete_sequence=[COLORS["sales"], COLORS["profit"]],
    )
    return polish_figure(figure)


def make_region_chart(data):
    region_data = (
        data.groupby("Region", as_index=False)
        .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
        .sort_values("Sales", ascending=True)
    )

    # UPDATED CHART 1: The treemap was replaced with a clearer bar chart.
    figure = px.bar(
        region_data,
        y="Region",
        x=["Sales", "Profit"],
        orientation="h",
        barmode="group",
        title="Sales and Profit by Region",
        labels={"value": "Amount", "variable": "Measure"},
        color_discrete_sequence=[COLORS["sales"], COLORS["profit"]],
    )
    return polish_figure(figure)


def make_customer_chart(data):
    customer_data = (
        data.groupby("Customer Name", as_index=False)
        .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
    )

    figure = px.scatter(
        customer_data,
        x="Sales",
        y="Profit",
        size="Sales",
        color="Profit",
        hover_name="Customer Name",
        size_max=22,
        # Light points start at a mint that is still visible on white.
        color_continuous_scale=["#99F6E4", "#14B8A6", "#0F766E", "#134E4A"],
        title="Customer Value: Sales and Profit",
    )
    figure.update_traces(opacity=0.76, marker_line_width=0)
    return polish_figure(figure)


def make_sales_trend_chart(data):
    monthly_sales = (
        data.assign(Month=data["Order Date"].dt.to_period("M").dt.to_timestamp())
        .groupby("Month", as_index=False)
        .agg(Sales=("Sales", "sum"))
        .sort_values("Month")
    )

    figure = px.line(
        monthly_sales,
        x="Month",
        y="Sales",
        markers=True,
        title="Monthly Sales Trend",
        labels={"Month": "Month", "Sales": "Sales"},
        color_discrete_sequence=[COLORS["profit"]],
    )
    figure.update_traces(
        line=dict(width=3),
        marker=dict(size=7),
        hovertemplate="<b>%{x|%b %Y}</b><br>Sales: %{y:,.0f}<extra></extra>",
    )
    figure.update_xaxes(tickformat="%b\n%Y")
    return polish_figure(figure)


def dashboard_values(data):
    sales, profit, orders, margin = calculate_kpis(data)
    return (
        f"{sales:,.0f}",
        f"{profit:,.2f}",
        f"{orders:,}",
        f"{margin:.2%}",
        make_category_chart(data),
        make_region_chart(data),
        make_customer_chart(data),
        make_sales_trend_chart(data),
    )


# Calculate the starting values shown when the page first opens.
initial_values = dashboard_values(df)


# -----------------------------------------------------------------------------
# 3. Create the Dash application and layout
# -----------------------------------------------------------------------------

app = Dash(__name__, title="Supermart Sales Dashboard")
server = app.server  # Gunicorn uses this variable when Render starts the app.

year_options = [
    {"label": "All Years", "value": "All Years"},
] + [
    {"label": str(year), "value": int(year)}
    for year in sorted(df["Year"].unique())
]


def kpi_card(title, value, note, colour_class, component_id):
    return html.Div(
        [
            html.P(title.upper(), className="kpi-label"),
            html.H2(value, id=component_id, className="kpi-value"),
            html.P(note, className="kpi-note"),
        ],
        className=f"kpi-card {colour_class}",
    )


def graph_card(component_id, figure):
    return html.Div(
        dcc.Graph(
            id=component_id,
            figure=figure,
            config={"displayModeBar": False, "responsive": True},
        ),
        className="chart-card",
    )


app.layout = html.Div(
    html.Div(
        [
            html.Header(
                [
                    html.P("RETAIL PERFORMANCE", className="eyebrow"),
                    html.H1("Supermart Sales Dashboard"),
                    html.P(
                        "A clear view of sales, profit and customer performance",
                        className="header-subtitle",
                    ),
                    html.Span(
                        f"{df['Year'].min()}–{df['Year'].max()}",
                        className="period-badge",
                    ),
                ],
                className="dashboard-header",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H2("Dashboard filter"),
                            html.P("Choose a year to update every result"),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("YEAR"),
                            dcc.Dropdown(
                                id="year-filter",
                                options=year_options,
                                value="All Years",
                                clearable=False,
                            ),
                        ],
                        className="filter-control",
                    ),
                ],
                className="filter-card",
            ),
            html.Div(
                [
                    kpi_card(
                        "Total Sales", initial_values[0], "Across the selected period",
                        "blue", "total-sales",
                    ),
                    kpi_card(
                        "Total Profit", initial_values[1], "Profit",
                        "teal", "total-profit",
                    ),
                    kpi_card(
                        "Total Orders", initial_values[2], "Orders",
                        "purple", "total-orders",
                    ),
                    kpi_card(
                        "Profit Margin", initial_values[3], "Profit as a share of sales",
                        "gold", "profit-margin",
                    ),
                ],
                className="kpi-grid",
            ),
            html.Div(
                [
                    html.H2("Performance overview"),
                    html.P("Explore category, region and customer results"),
                ],
                className="section-heading",
            ),
            html.Div(
                [
                    graph_card("category-chart", initial_values[4]),
                    graph_card("trend-chart", initial_values[7]),
                    graph_card("customer-chart", initial_values[6]),
                    graph_card("region-chart", initial_values[5]),
                ],
                className="chart-grid",
            ),
            html.P(
                "Source: Supermart Grocery Sales dataset",
                className="source-note",
            ),
        ],
        className="dashboard-content",
    ),
    className="page-background",
)


# -----------------------------------------------------------------------------
# 4. Connect the Year dropdown to the KPIs and charts
# -----------------------------------------------------------------------------

@app.callback(
    Output("total-sales", "children"),
    Output("total-profit", "children"),
    Output("total-orders", "children"),
    Output("profit-margin", "children"),
    Output("category-chart", "figure"),
    Output("region-chart", "figure"),
    Output("customer-chart", "figure"),
    Output("trend-chart", "figure"),
    Input("year-filter", "value"),
)
def update_dashboard(selected_year):
    if selected_year == "All Years":
        filtered_data = df
    else:
        filtered_data = df[df["Year"] == selected_year]

    return dashboard_values(filtered_data)


# -----------------------------------------------------------------------------
# 5. Run locally with: python app.py
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)