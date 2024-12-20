import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
PASSWORD = os.getenv("STREAMLIT_PASSWORD")

# Streamlit App with Password Protection
st.title("Customer Purchase Analysis Dashboard")


# Password Input
def check_password():
    def password_entered():
        if st.session_state["password"] == PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Remove password from session state
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Enter Password:",
            type="password",
            on_change=password_entered,
            key="password",
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Enter Password:",
            type="password",
            on_change=password_entered,
            key="password",
        )
        st.error("Password incorrect")
        return False
    else:
        # Password correct.
        return True


if check_password():
    # File Upload
    uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=["csv"])

    if uploaded_file is not None:
        # Load data
        df = pd.read_csv(uploaded_file)

        # Data Preprocessing
        df["date"] = pd.to_datetime(df["date"])

        # Sidebar for Filters
        st.sidebar.header("Filters")
        selected_date_range = st.sidebar.date_input(
            "Select Date Range:", value=[df["date"].min(), df["date"].max()]
        )
        selected_customer = st.sidebar.selectbox(
            "Select Customer:", options=["All Customers"] + list(df["userId"].unique())
        )
        selected_brand = st.sidebar.multiselect(
            "Select Brand:",
            options=["All Brands"] + list(df["brand"].unique()),
            default="All Brands",
        )

        # Filter data based on selection
        filtered_df = df[
            (selected_brand == ["All Brands"] or df["brand"].isin(selected_brand))
            & (
                (selected_customer == "All Customers")
                | (df["userId"] == selected_customer)
            )
            & (
                df["date"].between(
                    pd.to_datetime(selected_date_range[0]),
                    pd.to_datetime(selected_date_range[1]),
                )
            )
        ]

        # Dropdown to Select Analysis Type
        analysis_type = st.selectbox(
            "Select Analysis Type:",
            ["Customer Analysis", "Brand Analysis", "Product Analysis"],
        )

        if analysis_type == "Customer Analysis":
            # Customer Analysis Section

            # Main Dashboard Metrics
            st.header("Key Metrics")
            total_sales = filtered_df["quantity"].sum()
            total_customers = filtered_df["userId"].nunique()
            monthly_sales = filtered_df.groupby(
                filtered_df["date"].dt.to_period("M")
            ).agg({"quantity": "sum"})

            st.metric("Total Sales Quantity", total_sales)
            st.metric("Total Unique Customers", total_customers)

            # Sales Trend Over Time
            st.header("Sales Trend Over Time")
            # Interactive Sales Trend
            import plotly.express as px

            monthly_sales = monthly_sales.reset_index()
            monthly_sales["date"] = monthly_sales["date"].dt.to_timestamp()
            fig = px.line(
                monthly_sales,
                x="date",
                y="quantity",
                title="Monthly Sales Trend",
                labels={"date": "Month", "quantity": "Total Quantity Sold"},
            )
            fig.update_layout(
                xaxis_title="Month",
                yaxis_title="Total Quantity Sold",
                hovermode="x unified",
            )
            st.plotly_chart(fig)

            # Customer Segmentation (Simple RFM Analysis)
            st.header("Customer Segmentation")
            customer_summary = filtered_df.groupby("userId").agg(
                {"date": ["max"], "ref": ["count"], "quantity": ["sum"]}
            )
            customer_summary.columns = ["Recency", "Frequency", "Monetary"]
            customer_summary["Recency"] = (
                df["date"].max() - customer_summary["Recency"]
            ).dt.days

            # Segment Customers based on simple logic
            customer_summary["Segment"] = pd.cut(
                customer_summary["Recency"],
                bins=[-1, 30, 90, 180, 9999],
                labels=["Active", "Warm", "Cold", "Lost"],
            )
            st.write(customer_summary)
            with st.expander("Explanation of Columns"):
                st.write(
                    "**Recency**: Number of days since the last purchase by the customer."
                )
                st.write("**Frequency**: Number of purchases made by the customer.")
                st.write("**Monetary**: Total quantity purchased by the customer.")
                st.write(
                    "**Segment**: Customer classification based on recency into Active, Warm, Cold, or Lost."
                )

            # Customer Segmentation Summary by Brand
            st.header("Customer Segmentation by Brand")
            # Dropdown to choose between Total Value or Percentage
            view_type = st.selectbox("Select View Type:", ["Total Value", "Percentage"])
            segmentation_summary = filtered_df.groupby(["brand", "userId"]).agg(
                {"date": ["max"], "ref": ["count"], "quantity": ["sum"]}
            )
            segmentation_summary.columns = ["Recency", "Frequency", "Monetary"]
            segmentation_summary["Recency"] = (
                df["date"].max() - segmentation_summary["Recency"]
            ).dt.days

            # Segment Customers based on simple logic
            segmentation_summary["Segment"] = pd.cut(
                segmentation_summary["Recency"],
                bins=[-1, 30, 90, 180, 9999],
                labels=["Active", "Warm", "Cold", "Lost"],
            )

            # Aggregate by brand and segment
            brand_segment_summary = (
                segmentation_summary.reset_index()
                .groupby(["brand", "Segment"])
                .size()
                .unstack(fill_value=0)
            )

            # Adjust based on view type
            if view_type == "Percentage":
                brand_segment_summary = brand_segment_summary.apply(
                    lambda x: (x / x.sum()) * 100, axis=1
                )
            st.write(brand_segment_summary)
            with st.expander("Explanation of Columns"):
                st.write("**Brand**: The name of the product brand.")
                st.write(
                    "**Active**: Count of customers who purchased in the last 30 days."
                )
                st.write(
                    "**Warm**: Count of customers who purchased between 31 and 90 days ago."
                )
                st.write(
                    "**Cold**: Count of customers who purchased between 91 and 180 days ago."
                )
                st.write(
                    "**Lost**: Count of customers who haven't purchased for more than 180 days."
                )

            # Interactive Histogram to Study Customer Purchase Patterns Across Time Periods
            st.header("Customer Purchase Pattern Analysis")
            st.write(
                "Compare the volume purchased by customers across different time periods."
            )

            # Date input to select time periods for comparison
            period_1 = st.date_input(
                "Select Start and End Date for Period 1:",
                value=[df["date"].min(), df["date"].max()],
            )
            period_2 = st.date_input(
                "Select Start and End Date for Period 2:",
                value=[df["date"].min(), df["date"].max()],
            )

            # Filtering data for both periods
            period_1_data = filtered_df[
                filtered_df["date"].between(
                    pd.to_datetime(period_1[0]), pd.to_datetime(period_1[1])
                )
            ]
            period_2_data = filtered_df[
                filtered_df["date"].between(
                    pd.to_datetime(period_2[0]), pd.to_datetime(period_2[1])
                )
            ]

            # Creating an interactive histogram using Plotly
            import plotly.graph_objects as go

            # Define bins for both periods based on the number of sales per customer
            period_1_sales = period_1_data.groupby("userId")["quantity"].sum()
            period_2_sales = period_2_data.groupby("userId")["quantity"].sum()
            bins = list(
                range(0, max(max(period_1_sales), max(period_2_sales)) + 1000, 1000)
            )

            # Creating histograms for each period using the same bins
            period_1_hist = (
                pd.cut(period_1_sales, bins=bins).value_counts().sort_index()
            )
            period_2_hist = (
                pd.cut(period_2_sales, bins=bins).value_counts().sort_index()
            )

            # Creating the figure
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=period_1_hist.index.astype(str),
                    y=period_1_hist.values,
                    name="Period 1",
                    marker_color="blue",
                )
            )
            fig.add_trace(
                go.Bar(
                    x=period_2_hist.index.astype(str),
                    y=period_2_hist.values,
                    name="Period 2",
                    marker_color="red",
                )
            )

            # Updating layout for better visualization
            fig.update_layout(
                title="Customer Purchase Patterns Comparison",
                xaxis_title="Total Sales (Buckets)",
                yaxis_title="Number of Customers",
                barmode="overlay",
                bargap=0.1,
                hovermode="x unified",
            )
            fig.update_traces(opacity=0.7)

            # Displaying the interactive histogram
            st.plotly_chart(fig)

        elif analysis_type == "Brand Analysis":
            # Brand Analysis Section

            st.header("Brand Analysis")

            # Sales by Brand
            st.header("Sales by Brand")
            brand_sales = (
                filtered_df.groupby("brand")["quantity"]
                .sum()
                .sort_values(ascending=False)
            )
            st.bar_chart(brand_sales)

            # Top Customers by Quantity Bought for Each Brand
            st.header("Top Customers by Quantity Bought for Each Brand")
            top_k = st.slider(
                "Select Number of Top Customers to Display:",
                min_value=1,
                max_value=20,
                value=5,
            )
            top_customers_by_brand = (
                filtered_df.groupby(["brand", "userId"])["quantity"].sum().reset_index()
            )
            top_customers_by_brand = (
                top_customers_by_brand.sort_values(
                    ["brand", "quantity"], ascending=[True, False]
                )
                .groupby("brand")
                .head(top_k)
            )
            st.write(top_customers_by_brand)
            with st.expander("Explanation of Columns"):
                st.write("**Brand**: The name of the product brand.")
                st.write("**UserId**: Unique identifier of the customer.")
                st.write(
                    "**Quantity**: Total quantity purchased by the customer for the specific brand."
                )

        elif analysis_type == "Product Analysis":
            # Product Analysis Section

            # Top Products by Sales Volume
            st.header("Top Products by Sales Volume")
            top_k_products = st.slider(
                "Select Number of Top Products to Display:",
                min_value=1,
                max_value=50,
                value=10,
            )
            top_products = (
                filtered_df.groupby("ref")["quantity"]
                .sum()
                .sort_values(ascending=False)
                .head(top_k_products)
            )
            st.bar_chart(top_products)

            # Top Products by Brand
            st.header("Top Products by Brand")
            selected_top_brand = st.selectbox(
                "Select Brand for Product Analysis:",
                options=["All Brands"] + list(df["brand"].unique()),
            )
            top_k_brands = st.slider(
                "Select Number of Top Products to Display by Brand:",
                min_value=1,
                max_value=20,
                value=5,
            )
            if selected_top_brand == "All Brands":
                top_products_by_brand = (
                    filtered_df.groupby(["brand", "ref"])["quantity"]
                    .sum()
                    .reset_index()
                    .sort_values(["brand", "quantity"], ascending=[True, False])
                    .groupby("brand")
                    .head(top_k_brands)
                )
            else:
                top_products_by_brand = (
                    filtered_df[filtered_df["brand"] == selected_top_brand]
                    .groupby(["brand", "ref"])["quantity"]
                    .sum()
                    .reset_index()
                    .sort_values("quantity", ascending=False)
                    .head(top_k_brands)
                )
            st.write(top_products_by_brand)
            with st.expander("Explanation of Columns"):
                st.write("**Brand**: The name of the product brand.")
                st.write("**Ref**: Product reference code.")
                st.write(
                    "**Quantity**: Total quantity of the product purchased for the specific brand."
                )

            with st.expander("Explanation of Columns"):
                st.write("**Ref**: Product reference code.")
                st.write(
                    "**UserId**: Number of unique customers who purchased the product."
                )

            # Top Products by Brand by Customer
            st.header("Top Products by Brand by Customer")
            top_products_by_brand_by_customer = (
                filtered_df.groupby(["brand", "ref", "userId"])["quantity"]
                .sum()
                .reset_index()
                .sort_values(
                    by=["brand", "ref", "quantity"], ascending=[True, True, False]
                )
            )
            st.write(top_products_by_brand_by_customer)
            with st.expander("Explanation of Columns"):
                st.write("**Brand**: The name of the product brand.")
                st.write("**Ref**: Product reference code.")
                st.write(
                    "**UserId**: Unique identifier of the customer who purchased the product."
                )
                st.write(
                    "**Quantity**: Total quantity purchased by the customer for the specific product."
                )

            # Insights Summary
            st.header("Product Analysis Summary")
            st.write(
                "This section helps identify the top products by brand, by customer reach, and by sales volume. It can be used to gauge product popularity, performance, and contribution to overall sales. Use these insights to optimize inventory, marketing focus, and product offerings based on data-driven decisions."
            )

        st.write(
            "This dashboard provides insights into customer purchasing behaviors and sales trends for better decision making."
        )
