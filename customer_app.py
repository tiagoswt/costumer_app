import os
import re
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
PASSWORD = os.getenv("STREAMLIT_PASSWORD")

#######################
# Streamlit App Title
#######################
st.title("Customer Purchase Analysis Dashboard")


#######################
# Password Protection
#######################
def check_password():
    """Prompt user for password, compare with env value, and allow/deny access."""

    def password_entered():
        """Update session state based on password correctness."""
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


# Only show the rest of the page if the password is correct
if check_password():

    ####################################
    # Upload CSV in the Sidebar
    ####################################
    uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=["csv"])

    if uploaded_file is not None:
        # Read the CSV
        df = pd.read_csv(uploaded_file, delimiter=";")

        # OPTIONAL: rename userID -> userId for consistency with original code logic
        if "userID" in df.columns:
            df.rename(columns={"userID": "userId"}, inplace=True)

        ####################################
        # Check if "date" column is present
        ####################################
        if "date" not in df.columns:
            st.error(
                "The CSV does not have a 'date' column. "
                "Please check the file or rename the date column to 'date'."
            )
            st.stop()
        else:
            # Convert "date" to datetime
            try:
                df["date"] = pd.to_datetime(df["date"])
            except ValueError:
                st.error(
                    "The 'date' column has invalid date formats. "
                    "Please check your CSV or transform the date column."
                )
                st.stop()

        ####################################
        # Create 'brand' column from 'ref'
        ####################################
        df["brand"] = df["ref"].str.replace(r"[^a-zA-Z]+", "", regex=True)

        # Sidebar Filters
        st.sidebar.header("Filters")

        # Date Range
        selected_date_range = st.sidebar.date_input(
            "Select Date Range:", value=[df["date"].min(), df["date"].max()]
        )

        # Customer Filter
        # If you want to handle large DataFrames more efficiently,
        # you might want to convert userId to str before creating the list
        unique_customers = df["userId"].unique().tolist()
        # Sort if you like
        # unique_customers.sort()
        selected_customer = st.sidebar.selectbox(
            "Select Customer (userId):", ["All Customers"] + list(unique_customers)
        )

        # Brand Filter
        unique_brands = df["brand"].unique().tolist()
        selected_brand = st.sidebar.multiselect(
            "Select Brand:",
            ["All Brands"] + unique_brands,
            default="All Brands",
        )

        ####################################
        # Filter the Data
        ####################################
        filtered_df = df.copy()

        # Filter by Brand
        if "All Brands" not in selected_brand:
            filtered_df = filtered_df[filtered_df["brand"].isin(selected_brand)]

        # Filter by Customer
        if selected_customer != "All Customers":
            filtered_df = filtered_df[filtered_df["userId"] == selected_customer]

        # Filter by Date
        start_date, end_date = selected_date_range
        filtered_df = filtered_df[
            filtered_df["date"].between(
                pd.to_datetime(start_date), pd.to_datetime(end_date)
            )
        ]

        ####################################
        # Dropdown to Select Analysis Type
        ####################################
        analysis_type = st.selectbox(
            "Select Analysis Type:",
            ["Customer Analysis", "Brand Analysis", "Product Analysis"],
        )

        ############################################################################
        # CUSTOMER ANALYSIS
        ############################################################################
        if analysis_type == "Customer Analysis":
            st.header("Key Metrics")

            total_sales = filtered_df["quantity"].sum()
            total_customers = filtered_df["userId"].nunique()

            # Compute monthly sales
            monthly_sales = (
                filtered_df.groupby(filtered_df["date"].dt.to_period("M"))["quantity"]
                .sum()
                .reset_index()
            )

            st.metric("Total Sales Quantity", total_sales)
            st.metric("Total Unique Customers", total_customers)

            # Sales Trend Over Time
            st.header("Sales Trend Over Time")
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

            # Group by (userId, email)
            # We'll keep max(date) for Recency, count of 'ref' as Frequency, sum of 'quantity' as Monetary
            customer_summary = (
                filtered_df.groupby(["userId", "email"])
                .agg({"date": "max", "ref": "count", "quantity": "sum"})
                .reset_index()
            )
            # Rename columns
            customer_summary.rename(
                columns={
                    "date": "LastPurchaseDate",
                    "ref": "Frequency",
                    "quantity": "Monetary",
                },
                inplace=True,
            )
            # Compute Recency
            max_date = df["date"].max()
            customer_summary["Recency"] = (
                max_date - customer_summary["LastPurchaseDate"]
            ).dt.days

            # Segment based on Recency
            customer_summary["Segment"] = pd.cut(
                customer_summary["Recency"],
                bins=[0, 30, 90, 180, 9999],
                labels=["Active", "Warm", "Cold", "Lost"],
            )
            st.write(customer_summary)
            with st.expander("Explanation of Columns"):
                st.write("**userId**: Unique identifier for the customer.")
                st.write("**email**: Email address associated with userId.")
                st.write("**LastPurchaseDate**: Most recent purchase date.")
                st.write("**Frequency**: Number of purchases made by the customer.")
                st.write("**Monetary**: Total quantity purchased by the customer.")
                st.write("**Recency**: Number of days since the last purchase.")
                st.write("**Segment**: Customer classification based on Recency.")

            # Segmentation by Brand
            st.header("Customer Segmentation by Brand")
            view_type = st.selectbox("Select View Type:", ["Total Value", "Percentage"])

            segmentation_summary = (
                filtered_df.groupby(["brand", "userId", "email"])
                .agg({"date": "max", "ref": "count", "quantity": "sum"})
                .reset_index()
            )
            segmentation_summary.rename(
                columns={
                    "date": "LastPurchaseDate",
                    "ref": "Frequency",
                    "quantity": "Monetary",
                },
                inplace=True,
            )
            segmentation_summary["Recency"] = (
                max_date - segmentation_summary["LastPurchaseDate"]
            ).dt.days
            segmentation_summary["Segment"] = pd.cut(
                segmentation_summary["Recency"],
                bins=[0, 30, 90, 180, 9999],
                labels=["Active", "Warm", "Cold", "Lost"],
            )

            brand_segment_summary = (
                segmentation_summary.groupby(["brand", "Segment"])
                .size()
                .unstack(fill_value=0)
            )
            # Convert to percentages if needed
            if view_type == "Percentage":
                brand_segment_summary = brand_segment_summary.apply(
                    lambda x: (x / x.sum()) * 100, axis=1
                )
            st.write(brand_segment_summary)
            with st.expander("Explanation of Columns"):
                st.write("**brand**: Derived from `ref` (letters only).")
                st.write("**Active**: Customers who purchased in the last 30 days.")
                st.write("**Warm**: 31-90 days ago.")
                st.write("**Cold**: 91-180 days ago.")
                st.write("**Lost**: More than 180 days ago.")

            # Interactive Histogram (Customer Purchase Patterns Across Time Periods)
            st.header("Customer Purchase Pattern Analysis")
            st.write(
                "Compare the volume purchased by customers across different time periods."
            )

            period_1 = st.date_input(
                "Select Start and End Date for Period 1:",
                value=[df["date"].min(), df["date"].max()],
                key="period_1",
            )
            period_2 = st.date_input(
                "Select Start and End Date for Period 2:",
                value=[df["date"].min(), df["date"].max()],
                key="period_2",
            )

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

            period_1_sales = period_1_data.groupby("userId")["quantity"].sum()
            period_2_sales = period_2_data.groupby("userId")["quantity"].sum()

            # Determine bin sizes
            max_val = max(
                period_1_sales.max() if not period_1_sales.empty else 0,
                period_2_sales.max() if not period_2_sales.empty else 0,
            )
            bins = list(range(0, int(max_val) + 1000, 1000))

            period_1_hist = (
                pd.cut(period_1_sales, bins=bins).value_counts().sort_index()
            )
            period_2_hist = (
                pd.cut(period_2_sales, bins=bins).value_counts().sort_index()
            )

            fig_hist = go.Figure()
            fig_hist.add_trace(
                go.Bar(
                    x=period_1_hist.index.astype(str),
                    y=period_1_hist.values,
                    name="Period 1",
                    marker_color="blue",
                )
            )
            fig_hist.add_trace(
                go.Bar(
                    x=period_2_hist.index.astype(str),
                    y=period_2_hist.values,
                    name="Period 2",
                    marker_color="red",
                )
            )
            fig_hist.update_layout(
                title="Customer Purchase Patterns Comparison",
                xaxis_title="Total Sales (Buckets)",
                yaxis_title="Number of Customers",
                barmode="overlay",
                bargap=0.1,
                hovermode="x unified",
            )
            fig_hist.update_traces(opacity=0.7)
            st.plotly_chart(fig_hist)

        ############################################################################
        # BRAND ANALYSIS
        ############################################################################
        elif analysis_type == "Brand Analysis":
            st.header("Brand Analysis")

            # Sales by Brand
            st.header("Sales by Brand")
            brand_sales = (
                filtered_df.groupby("brand")["quantity"]
                .sum()
                .sort_values(ascending=False)
            )
            st.bar_chart(brand_sales)

            # Top Customers by Quantity (for Each Brand)
            st.header("Top Customers by Quantity Bought for Each Brand")
            top_k = st.slider(
                "Select Number of Top Customers to Display:",
                min_value=1,
                max_value=20,
                value=5,
            )
            top_customers_by_brand = (
                filtered_df.groupby(["brand", "userId", "email"])["quantity"]
                .sum()
                .reset_index()
                .sort_values(["brand", "quantity"], ascending=[True, False])
                .groupby("brand")
                .head(top_k)
            )
            st.write(top_customers_by_brand)
            with st.expander("Explanation of Columns"):
                st.write("**brand**: The new brand name derived from `ref`.")
                st.write("**userId**: Unique identifier of the customer.")
                st.write("**email**: Email address of the customer.")
                st.write(
                    "**quantity**: Total quantity purchased by the customer for that brand."
                )

        ############################################################################
        # PRODUCT ANALYSIS
        ############################################################################
        elif analysis_type == "Product Analysis":
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
                ["All Brands"] + list(df["brand"].unique()),
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
                st.write("**brand**: The new brand name derived from `ref`.")
                st.write("**ref**: Product reference code.")
                st.write(
                    "**quantity**: Total quantity of the product purchased for the specific brand."
                )

            # Top Products by Brand by Customer
            st.header("Top Products by Brand by Customer")
            top_products_by_brand_by_customer = (
                filtered_df.groupby(["brand", "ref", "userId", "email"])["quantity"]
                .sum()
                .reset_index()
                .sort_values(
                    by=["brand", "ref", "quantity"], ascending=[True, True, False]
                )
            )
            st.write(top_products_by_brand_by_customer)
            with st.expander("Explanation of Columns"):
                st.write("**brand**: The new brand name derived from `ref`.")
                st.write("**ref**: Product reference code.")
                st.write("**userId**: Unique identifier of the customer.")
                st.write("**email**: Email address of the customer.")
                st.write(
                    "**quantity**: Total quantity purchased by the customer for the specific product."
                )

            # Insights Summary
            st.header("Product Analysis Summary")
            st.write(
                "This section helps identify the top products by brand, by customer reach, "
                "and by sales volume. Use these insights to optimize inventory, marketing focus, "
                "and product offerings based on data-driven decisions."
            )

        # Footer / closing remarks
        st.write(
            "This dashboard provides insights into customer purchasing behaviors and "
            "sales trends for better decision making."
        )
