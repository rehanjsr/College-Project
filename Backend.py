
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import psycopg2 as pg
from DbCredentials import database_credentials
import json
import os
from dotenv import load_dotenv
from google import genai


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)



try:
    conn = pg.connect(**database_credentials)
    cursor = conn.cursor()

except Exception as error:
    print("Error: ", error)

data = pd.read_sql(
    'SELECT * FROM Transactions',
    conn,
    parse_dates=['Date'],
    index_col=['Transaction_ID']
)


start_date = data['Date'].min()
end_date = data['Date'].max()



def categorical_purchases():
    value = data['Category'].value_counts()
    plt.pie(value, labels=value.index, autopct='%1.1f%%')
    plt.show()


def categorical_expense():
    group = data.groupby('Category')
    value = group['Amount'].sum()
    plt.pie(value, labels=value.index, autopct='%1.1f%%')
    plt.show()


def expense_trend():
    data2 = data.copy(deep=True)
    data2 = data2.groupby(['Category', 'Date'])['Amount'].sum()

    date_range = pd.date_range(start_date, end_date)

    data2 = data2.unstack(level=0)
    data2 = data2.reindex(date_range)
    data2 = data2.fillna(0)

    categories = list(data2.columns)
    index = data2.index

    for i in categories:
        plt.plot(index, data2[i], marker='o', label=i)

    plt.xlabel("Date")
    plt.ylabel("Amount")
    plt.title("Expense Trend by Category")
    plt.xticks(rotation=45)
    plt.legend()
    plt.show()


def expense_summary():
    total_spent = data['Amount'].sum()
    categorical_spending = data.groupby('Category')['Amount'].sum()
    average_transaction = data['Amount'].mean()

    return {
        "total": total_spent,
        "average_transaction": average_transaction,
        "category": categorical_spending
    }


def monthly_spending():
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


def highest_category_spending_per_month():
    data2 = data.copy(deep=True)
    data2['Month'] = data2['Date'].dt.to_period('M')

    data2 = data2.groupby(['Month', 'Category'])['Amount'].sum()
    data2 = data2.groupby(level='Month').max()

    return {
        'highest_category_total': data2
    }

def spending_data():
    summary = expense_summary()
    monthly = monthly_spending()

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


def ai_financial_summary():

    json_report = spending_data()
   
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


def ai_budgeting():

    json_report = spending_data()

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


if __name__ == "__main__":
    summary = ai_financial_summary()
    advice = ai_budgeting()

    print(summary)
    print(advice)


# cursor.close()
# conn.close()


df = data.groupby(["Category"])
print(data.head())
