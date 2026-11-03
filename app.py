
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

    category_spending = {
        str(category): float(amount)
        for category, amount in summary["category"].items()
    }

    monthly_spending = {
        str(month): float(amount)
        for month, amount in monthly["total_monthly"].items()
    }

    return render_template(
        "index.html",
        total_spent=float(summary["total"]),
        average_transaction=float(summary["average_transaction"]),
        category_spending=category_spending,
        monthly_spending=monthly_spending
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
            data = Backend.load_user_data('0')
            
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



if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=5000)
