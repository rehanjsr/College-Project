
from flask import Flask, render_template, request, send_file, redirect, url_for,session
import Backend
import markdown


app = Flask(__name__)
app.secret_key = "finassist_secret_key"

@app.route("/login", methods=["GET", "POST"])
def login():
    # If the user clicked the "Log In" submit button on the form:
    if request.method == "POST":
        credentials = request.form.to_dict()
        
        # Send the dictionary to your Backend.log_in() function!
        if Backend.log_in(credentials):
            # It returned True! Put their username on the VIP wristband (session)
            session['username'] = credentials['username']
            return redirect(url_for('home'))
        else:
            # It returned False! Reload the login page with an error message
            return render_template("login.html", error="Invalid username or password.")
            
    # If they are just visiting the page normally, show the blank login form
    return render_template("login.html", error=None)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    # If the user clicked the "Sign Up" submit button on the form:
    if request.method == "POST":
        credentials = request.form.to_dict()
        
        # Send the dictionary to your Backend.sign_up() function!
        if Backend.sign_up(credentials):
            # It returned True! Log them in automatically and send them home
            session['username'] = credentials['username']
            return redirect(url_for('home'))
        else:
            # It returned False! (Usually means that username is already taken)
            return render_template("signup.html", error="Username already exists or could not be created.")
            
    return render_template("signup.html", error=None)


@app.route("/logout")
def logout():
    # Rip off the wristband and send them back to the login screen
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route("/charts/category-expenses")
def category_expenses_chart():
    data = Backend.load_user_data(session['username'])
    image_buffer = Backend.categorical_expense(data)
    return send_file(image_buffer, mimetype="image/png")

@app.route("/charts/expense-trend")
def expense_trend_chart():
    data = Backend.load_user_data(session['username'])
    image_buffer = Backend.expense_trend(data)
    return send_file(image_buffer, mimetype="image/png")


@app.route("/")
def home():
    if 'username' not in session:
        return redirect(url_for('login'))

    data = Backend.load_user_data(session['username'])
    
    summary = Backend.expense_summary(data)
    monthly = Backend.monthly_spending(data)
    history_data = Backend.monthly_history(data)
    recent_transactions = Backend.get_recent_transactions(data, limit=10)
    prediction_data = Backend.predict_spending(data)
    category_data = summary.get("category", summary.get("top_8_categories", {}))
    category_spending = {
        str(category): float(amount)
        for category, amount in category_data.items()
    }

    monthly_spending = {
        str(month): float(amount)
        for month, amount in monthly.get("total_monthly", {}).items()
    }

    return render_template(
        "index.html",
        summary_data=summary,  
        total_spent=float(summary.get("total", summary.get("total_ever", 0))),
        average_transaction=float(summary.get("average_transaction", 0)),
        category_spending=category_spending,
        monthly_spending=monthly_spending,
        recent_transactions=recent_transactions,
        monthly_history=history_data,
        prediction_data=prediction_data
    )



@app.route("/add_transaction", methods=["POST"])
def submit_transaction():
    trans_data = request.form.to_dict()
    trans_data['username'] = session['username'] 
    
    Backend.add_transactions(trans_data)
    
    return redirect(url_for('home'))


@app.route("/report/<report_type>", methods=["GET", "POST"])
def report(report_type):
    if request.method == "POST":
        try:
            data = Backend.load_user_data(session['username'])
            
            if report_type == "summary":
                raw_result = Backend.ai_financial_summary(data)
                # Translate to HTML
                result = markdown.markdown(raw_result, extensions=['tables'])
                title = "AI Spending Summary"

            elif report_type == "budget":
                raw_result = Backend.ai_budgeting(data)
                result = markdown.markdown(raw_result, extensions=['tables'])
                title = "AI Budget Recommendations"

            else:
                return "Report type not found", 404

            return render_template(
                "report.html",
                title=title,
                result=result,
                error=None
            )

        except Exception as e:
            app.logger.exception("Report generation failed")
            return render_template(
                "report.html",
                title="Report Error",
                result=None,
                error=f"The report could not be generated. Error: {str(e)}" 
            ), 500

    return "Please submit the report form from the dashboard.", 405


@app.route("/anomalies")
def view_anomalies():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    data = Backend.load_user_data(session['username'])
    
    if not data.empty:
        anomalies = Backend.anomaly_detection(data)
    else:
        anomalies = {}
        
    return render_template("anomalies.html", anomalies=anomalies)



@app.route("/override_anomaly", methods=["POST"])
def handle_anomaly_override():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    trans_id = request.form.get("transaction_id")
    user_choice = request.form.get("override")
    
    is_anomaly = True if user_choice == "true" else False
    
    details = {
        "transaction_id": int(trans_id),
        "override": is_anomaly,
        "username": session['username']
    }
    
    Backend.override_anomaly(details)
    return redirect(url_for('view_anomalies'))


@app.route("/transactions")
def view_all_transactions():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    data = Backend.load_user_data(session['username'])
    
    # Calling without limit=10 returns ALL transactions sorted by newest date
    all_transactions = Backend.get_recent_transactions(data)
    
    return render_template("transactions.html", transactions=all_transactions)



@app.route("/manage_action", methods=["POST"])
def manage_action():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    action = request.form.get('action')
    trans_id = request.form.get('transaction_id')
    
    if not trans_id:
        return redirect(url_for('view_all_transactions'))
        
    trans_id = int(trans_id)

    if action == 'delete':
        details = {
            'transaction_id': trans_id,
            'username': session['username']
        }
        Backend.delete_transaction(details)
        return redirect(url_for('view_all_transactions'))
        
    elif action == 'edit':
        data = Backend.load_user_data(session['username'])
        # Find the specific row by its index (transaction_id)
        if trans_id in data.index:
            row = data.loc[trans_id]
            # Package it up nicely for the HTML form
            item = {
                'transaction_id': trans_id,
                'Date': row['Date'].strftime('%Y-%m-%d'),
                'Category': row['Category'],
                'Description': row['Description'],
                'Amount': row['Amount'],
                'Payment_Method': row['Payment_Method'],
                'Account_Type': row['Account_Type']
            }
            return render_template("edit_transaction.html", item=item)
            
        return redirect(url_for('view_all_transactions'))

    

@app.route("/submit_edit", methods=["POST"])
def submit_edit():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    details = {
        "transaction_id": int(request.form.get("transaction_id")),
        "date": request.form.get("date"),
        "category": request.form.get("category"),
        "description": request.form.get("description"),
        "amount": float(request.form.get("amount")),
        "payment_method": request.form.get("payment_method"),
        "account_type": request.form.get("account_type"),
        "username": session['username']
    }
    
    Backend.update_transaction(details)
    return redirect(url_for('view_all_transactions'))


@app.route("/prediction", methods=["GET"])
def view_prediction():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    data = Backend.load_user_data(session['username'])
    prediction_data = Backend.predict_spending(data)
    
    return render_template("prediction.html", prediction_data=prediction_data)



if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=5000)
