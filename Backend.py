
import matplotlib
from datetime import datetime, date
import base64
matplotlib.use("Agg")
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import psycopg2 as pg
from DbCredentials import database_credentials
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
import json
import os
from dotenv import load_dotenv
from google import genai
from io import BytesIO


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def load_user_data(username):
    try:
        conn = pg.connect(**database_credentials)
        cursor = conn.cursor()

    except Exception as error:
        print("Error: ", error)

    data = pd.read_sql(
        'SELECT * FROM Transactions WHERE Username = %(user)s',
        conn,
        params={"user": username},
        parse_dates=['Date'],
        index_col=['transaction_id']
    )

    cursor.close()
    conn.close()

    return data



def categorical_expense(data):
    buffer = BytesIO()

    values = data.groupby('Category')['Amount'].sum()
    values = values[values > 0].sort_values(ascending=False)

    if values.empty:
        return buffer

    fig, ax = plt.subplots(figsize=(7, 5.5), dpi=140)
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#ffffff')

    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        autopct='%1.1f%%',
        startangle=90,
        pctdistance=0.7,
        wedgeprops={
            'width': 0.42,
            'edgecolor': '#ffffff',
            'linewidth': 2
        },
        textprops={'fontsize': 10}
    )

    for text in autotexts:
        text.set_color('#30265c')
        text.set_fontweight('bold')
        text.set_fontsize(9)

    ax.legend(
        wedges,
        [f'{category}  (₹{amount:,.0f})'
         for category, amount in values.items()],
        title='Categories',
        loc='center left',
        bbox_to_anchor=(0.98, 0.5),
        frameon=False,
        fontsize=9,
        title_fontsize=10
    )

    ax.set_title(
        'Where Your Money Goes',
        fontsize=15,
        fontweight='bold',
        color='#30265c',
        pad=18
    )

    ax.axis('equal')
    fig.tight_layout()

    fig.savefig(
        buffer,
        format='png',
        dpi=160,
        bbox_inches='tight',
        facecolor='white'
    )

    plt.close(fig)
    buffer.seek(0)

    return buffer


def monthly_history(data):
    df = data.copy(deep = True)
    df = df.set_index("Date")
    df = df.groupby([pd.Grouper(freq = "MS"),"Category"])["Amount"].sum()
    df = df.unstack(level = 1)
    df.index = df.index.strftime('%Y-%m')
    return df.to_dict(orient = 'index')

def expense_trend(data):
    buffer = BytesIO()

    data2 = data[['Date', 'Category', 'Amount']].copy()
    data2['Date'] = pd.to_datetime(data2['Date']).dt.normalize()

    grouped = (
        data2.groupby(['Date', 'Category'])['Amount']
        .sum()
        .unstack(fill_value=0)
        .sort_index()
    )

    if grouped.empty:
        return buffer

    date_range = pd.date_range(
        start=grouped.index.min(),
        end=grouped.index.max(),
        freq='D'
    )
    grouped = grouped.reindex(date_range, fill_value=0)

    fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#ffffff')

    for category in grouped.columns:
        ax.plot(
            grouped.index,
            grouped[category],
            marker='o',
            markersize=3,
            linewidth=2,
            label=str(category)
        )

    ax.set_title('Expense Trend by Category', fontsize=15, pad=18)
    ax.set_xlabel('Date', fontsize=10)
    ax.set_ylabel('Amount (₹)', fontsize=10)

    ax.grid(axis='y', linestyle='--', alpha=0.25)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    ax.legend(frameon=False, loc='best')
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()

    fig.savefig(
        buffer,
        format='png',
        dpi=150,
        bbox_inches='tight',
        facecolor=fig.get_facecolor()
    )

    plt.close(fig)
    buffer.seek(0)

    return buffer


def expense_summary(data):
    total_spent = data['Amount'].sum()
    categorical_spending = data.groupby('Category')['Amount'].sum()
    average_transaction = data['Amount'].mean()

    return {
        "total": total_spent,
        "average_transaction": average_transaction,
        "category": categorical_spending
    }


def monthly_spending(data):
    data2 = data.copy(deep=True)

    total_monthly = (
        data2.set_index('Date')
        .resample('ME')['Amount']
        .sum()
    )

    monthly_categorical = data2.copy(deep=True)
    monthly_categorical['Month'] = monthly_categorical['Date'].dt.to_period('M')

    monthly_categorical = monthly_categorical.groupby(
        ['Month', 'Category']
    )['Amount'].sum()

    return {
        'total_monthly': total_monthly,
        'monthly_categorical': monthly_categorical
    }


def highest_category_spending_per_month(data):
    data2 = data.copy(deep=True)
    data2['Month'] = data2['Date'].dt.to_period('M')

    data2 = data2.groupby(['Month', 'Category'])['Amount'].sum()
    data2 = data2.groupby(level='Month').max()

    return {
        'highest_category_total': data2
    }

def spending_data(data):
    summary = expense_summary(data)
    monthly = monthly_spending(data)

    category = summary["category"].index
    spending = summary["category"].values

    category_spending = dict(zip(category, spending))

    total_monthly = {str(month):amount for month,amount in monthly['total_monthly'].items()}
    monthly_categorical = {str(month):details.to_dict() for month,details in monthly['monthly_categorical'].unstack(level = 1).iterrows()}


    financial_report = {
        'total_spent': summary["total"],
        'average_transaction': summary["average_transaction"],
        'category_spending': category_spending,
        'monthly_spending_data' : {"total_monthly":total_monthly,"monthly_categorical":monthly_categorical}
    }


    json_report = json.dumps(financial_report,default=str)

    return json_report


def ai_financial_summary(data):

    json_report = spending_data(data)
   
    prompt = f"""
You are a personal finance analyst. Generate a clear, concise
spending summary using only the financial report provided below.

Financial Report:
{json_report}

Organize your response into these sections:

1. OVERALL SPENDING
   - Total spending and average transaction amount.
   - Number of months covered by the report, if available.
   - A brief overview of the user's spending.

2. MONTHLY BREAKDOWN
   - Summarize spending for each month.
   - Compare consecutive months and report the absolute and
     percentage change when possible.
   - Describe the change neutrally, without assuming it is
     good, bad, or part of a long-term trend.

3. CATEGORY BREAKDOWN
   - Rank spending categories from highest to lowest.
   - Include each category's total and percentage of total spending
     when the required data is available.
   - Highlight the largest spending categories.

4. KEY OBSERVATIONS
   - State 2-3 important patterns directly supported by the data.
   - Mention notable increases, decreases, or stable categories
     only when supported by the report.
   - Do not speculate about the reasons behind these patterns.

5. DATA LIMITATIONS
   - Briefly identify missing information that affects interpretation.
   - Do not infer income, savings, affordability, budgets, or
     financial goals when those details are not provided.
   - Do not claim that short-term changes establish long-term trends.

Rules:
- Use only figures present in or directly calculable from the report.
- Do not invent transactions, categories, or financial circumstances.
- Preserve the currency specified in the data; never guess it.
- If information is missing, explicitly say so.
- Avoid budgeting recommendations, saving strategies,
  anomaly detection, and future spending predictions.
- Use clear headings, concise bullet points, and readable formatting.
- Prioritize accuracy over length.
-Ensure response is detailed but short
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )

    return response.text


def ai_budgeting(data):

    json_report = spending_data(data)

    prompt = f"""
You are a personal budgeting assistant. Use the financial report
below to suggest realistic, provisional monthly budgets based on
the user's historical spending.

Financial Report:
{json_report}

Your tasks:

1. PROPOSED MONTHLY BUDGETS
   - Suggest a provisional monthly budget for each spending category.
   - Use the available monthly category spending as your baseline.
   - Explain briefly why each suggested amount is reasonable.
   - Distinguish relatively predictable expenses, such as housing,
     from variable expenses, such as entertainment and dining.
   - Do not arbitrarily cut essential expenses to make the budget
     look better.

2. OPPORTUNITIES TO REVIEW
   - Identify up to three categories where reviewing spending
     may be worthwhile.
   - Use actual figures and observed changes to support each point.
   - Do not assume that higher spending is unnecessary or wasteful.
   - Avoid recommending cuts that are unsupported by the data.

3. PRACTICAL BUDGETING ACTIONS
   - Suggest specific actions for managing variable expenses.
   - Recommend tracking spending against the proposed budgets.
   - Keep the suggestions achievable and relevant to the report.

4. ASSUMPTIONS AND LIMITATIONS
   - Clearly label all suggested budgets as provisional estimates.
   - Explain that income, savings goals, debts, and financial
     obligations were not provided.
   - Do not claim that the proposed budgets are affordable.
   - If only a short period of data is available, acknowledge
     that it may not represent typical monthly spending.
   - Do not invent financial information or guaranteed savings.

Output format:
- Start with a brief explanation of the budgeting approach.
- Present the proposed budgets in a table with these columns:
  Category | Historical Monthly Spending | Proposed Monthly
  Budget | Reasoning
- Follow with a short list of priorities and practical actions.
- End with assumptions and limitations.

Rules:
- Use only information provided or directly calculated from the report.
- Preserve the currency if it is explicitly identified; never guess it.
- Ensure all amounts are non-negative and internally consistent.
- Do not provide investment, tax, or debt-management advice.
- Be specific, concise, and transparent about uncertainty.
"""

    response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=prompt
    )

    return response.text


def ano_detect(category_data):
    category_data = category_data.copy()
    amount = pd.DataFrame(category_data['Amount'])
    model = IsolationForest(contamination = 0.01)
    category_data['Type'] = model.fit_predict(amount)
    category_data = category_data[(category_data['Type'] == -1) & (category_data['user_anomaly_override'] != False)]
    category_data = category_data[['Date', 'Category', 'Description', 'Amount']]
    return category_data.to_dict(orient='index')



def anomaly_detection(data):
    threshold = 5
    df = data.copy(deep=True)
    category_size = df.groupby(["Category"]).size()
    anomalies = {}
    for col,value in category_size.items():
        if value >= threshold:
            category_data = df[df["Category"] == col]
            result = ano_detect(category_data)
            anomalies.update(result)

    return anomalies


def override_anomaly(details):
    try:
        conn = pg.connect(**database_credentials)
        cursor = conn.cursor()
        query = 'Update transactions set user_anomaly_override = %(override)s where transaction_id = %(transaction_id)s AND username = %(username)s'
        cursor.execute(query,details)
        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as error:
        print("Error: ", error) 
        cursor.close()
        conn.close()
        return False



def add_transactions(trans_data):
    try:
        conn = pg.connect(**database_credentials)
        cursor = conn.cursor()

    except Exception as error:
        print("Error: ", error)

    query = '''insert into Transactions (username,"Date","Category","Description","Amount","Payment_Method","Account_Type") 
    values ( %(username)s, %(date)s, %(category)s, %(description)s, %(amount)s, %(payment_method)s, %(account_type)s ) '''

    cursor.execute(query,trans_data)

    conn.commit()
    cursor.close()
    conn.close()


def sign_up(credentials):
    try:
        conn = pg.connect(**database_credentials)
        cursor = conn.cursor()
        query = 'insert into users (username,password) values (%(username)s, %(password)s)'
        cursor.execute(query,credentials)
        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as error:
        print("Error: ", error)
        cursor.close()
        conn.close()
        return False

def log_in(credentials):
    try:
        conn = pg.connect(**database_credentials)
        cursor = conn.cursor()
        query = 'select * from users where username = %(username)s'
        cursor.execute(query,credentials)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            if result[1] == credentials['password']:
                return True
            else:
                return False
            
        else:
            return False

    except Exception as error:
        print("Error: ", error)
        cursor.close()
        conn.close()
        return False


def get_recent_transactions(data, limit=None):
    if data.empty:
        return []
    df = data.copy()
    df = df.reset_index()
    df = df.sort_values(by='Date', ascending=False)
    df['Month_Str'] = df['Date'].dt.strftime('%Y-%m')
    df = df[['transaction_id', 'Month_Str', 'Date', 'Category', 'Description', 'Amount', 'Payment_Method', 'Account_Type']]
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    if limit:
        df = df.head(limit)
    return df.to_dict(orient='records')


def delete_transaction(details):
    tx_date = datetime.strptime(details['date'], '%Y-%m-%d').date()
    if tx_date > date.today():
        return False

    try:
        conn = pg.connect(**database_credentials)
        cursor = conn.cursor()
        query = 'delete from transactions where username = %(username)s and transaction_id = %(transaction_id)s'
        cursor.execute(query,details)
        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as error:
        print("Error: ", error)
        cursor.close()
        conn.close()
        return False


def update_transaction(details):
    tx_date = datetime.strptime(details['date'], '%Y-%m-%d').date()
    if tx_date > date.today():
        return False
    try:
        conn = pg.connect(**database_credentials)
        cursor = conn.cursor()
        query = '''
        UPDATE transactions SET 
        "Date" = %(date)s, 
        "Category" = %(category)s, 
        "Description" = %(description)s, 
        "Amount" = %(amount)s, 
        "Payment_Method" = %(payment_method)s, 
        "Account_Type" = %(account_type)s 
        WHERE transaction_id = %(transaction_id)s AND username = %(username)s'''        
        cursor.execute(query,details)
        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as error:
        print("Error: ", error)
        cursor.close()
        conn.close()
        return False


def predict_spending(data):
    if data.empty:
        return False

    buffer = BytesIO()
    df = data.copy(deep=True)
    df = df.set_index("Date")

    monthly_totals = df.resample("MS")["Amount"].sum()
    y = monthly_totals.values
    
    if len(y) > 3:
        X = np.arange(1, len(y) + 1).reshape(-1, 1)
        next_month = np.array([[len(y) + 1]])
        month_labels = monthly_totals.index.strftime('%Y-%m').tolist()

        model = LinearRegression()
        model.fit(X, y)
        
        raw_prediction = model.predict(next_month)[0]
        clean_prediction = max(0.0, round(float(raw_prediction), 2))

        plt.figure(figsize=(8, 4.2), dpi=100)
        ax = plt.gca()
        ax.set_facecolor('#f8f9fa')
        
        all_X = np.vstack([X, next_month])
        trendline_y = np.maximum(0, model.predict(all_X))
        plt.plot(all_X, trendline_y, color='#6558d9', linestyle='--', alpha=0.5, linewidth=2, label='Spending Trend')

        plt.scatter(X, y, color='#6558d9', s=75, zorder=4, label='Actual Monthly Spending')

        plt.scatter(next_month, [clean_prediction], color='#d9534f', s=110, zorder=5, edgecolors='black', linewidth=1.2, label='Next Month Forecast')

        all_labels = month_labels + ['Next Month']
        plt.xticks(all_X.flatten(), all_labels, rotation=30, fontsize=9, color='#333333')
        plt.yticks(fontsize=9, color='#333333')

        plt.title('Monthly Spending Trajectory & Forecast', fontsize=12, fontweight='bold', color='#333333', pad=12)
        plt.ylabel('Total Spending (₹)', fontsize=10, fontweight='bold', color='#555555')
        plt.grid(True, linestyle=':', alpha=0.6, color='#cccccc', zorder=0)
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#cccccc')
        ax.spines['bottom'].set_color('#cccccc')
        
        plt.legend(frameon=True, facecolor='white', edgecolor='#e0e0e0', fontsize=9)
        plt.tight_layout()

        plt.savefig(buffer, format='png')
        plt.close()
        buffer.seek(0)
        graph_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        result = {}
        result['Prediction'] = clean_prediction
        result['Graph'] = graph_base64

        return result

    else:
        return False



if __name__ == "__main__":
    my_data = load_user_data('0')






