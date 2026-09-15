import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import psycopg2 as pg
from DbCredentials import database_credentials 

try:
    conn = pg.connect(**database_credentials)
    cursor = conn.cursor()

except Exception as error:
    print("Error: ",error)


data = pd.read_sql('Select * from Transactions',conn, parse_dates=['Date'], index_col= ['Transaction_ID'])
start_date = data['Date'].min()
end_date = data["Date"].max()

print(data)

def categorical_purchases():
    value = data['Category'].value_counts()
    plt.pie(value,labels = value.index ,autopct='%1.1f%%')
    plt.show()

def categorical_expense():
    group = data.groupby('Category')
    value = group['Amount'].sum()
    plt.pie(value,labels=value.index,autopct='%1.1f%%')
    plt.show()

def expense_trend():
    data2 = data.copy(deep=True)
    data2 = data2.groupby(['Category','Date'])['Amount'].sum()
    date_range = np.array(pd.date_range(start_date,end_date))
    data2 = data2.unstack(level = 0)
    data2 = data2.reindex(date_range)
    data2 = data2.fillna(0)
    categories = list(data2.columns)
    index = data2.index
    for i in categories:
        plt.plot(index,data2[i],marker = 'o',label=i)
    plt.xlabel("Date")
    plt.ylabel("Amount")
    plt.title("Expense Trend by Category")
    plt.xticks(rotation=45)
    plt.legend()
    plt.show()

def expense_summary():
    total_spent = data['Amount'].sum()
    categorical_spending = data.groupby(['Category'])['Amount'].sum()
    average_spending = data['Amount'].mean()
    return {
    "total": total_spent,
    "average": average_spending,
    "category": categorical_spending
    } 

def monthly_spending():
    data2 = data.copy(deep=True)
    total_monthly = data2.set_index('Date').resample('ME')['Amount'].sum()
    monthly_categorical = data2.copy(deep=True)
    monthly_categorical['Month'] = monthly_categorical['Date'].dt.to_period('M')
    monthly_categorical = monthly_categorical.groupby(['Month','Category'])['Amount'].sum()
    return{
        'total_monthly':total_monthly,
        'monthly_categorical':monthly_categorical
           }


def largest_transaction():
    data2 = data.copy(deep=True)
    data2['Month'] = data2["Date"].dt.to_period('M')
    data2 = data2.groupby(['Month','Category'])['Amount'].sum()
    data2 = data2.groupby(level='Month').max()
    return {
        'largest_transaction':data2
        }







cursor.close()
conn.close()