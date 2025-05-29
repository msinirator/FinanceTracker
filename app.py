from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

import os
import datetime

from sqlalchemy.sql import text
from sqlalchemy.sql import functions


#AWS bucket
import boto3
import json


#AWS bucket
bucketName = "taskscheduler-bucket"

#AWS Secret
def get_db_secret(secret_name, region_name='us-east-2'):
    client = boto3.client('secretsmanager', region_name=region_name)
    response = client.get_secret_value(SecretId=secret_name)

    secret = response['SecretString']
    return json.loads(secret)


#AWS secret
#Fetch credentials from secrets manager
secret = get_db_secret('prod/rds/mydb')


app = Flask(__name__)

# Get the directory of the current file
basedir = os.path.abspath(os.path.dirname(__file__))

#AWS secret
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{secret['username']}:{secret['password']}@{secret['host']}/{secret['dbname']}"
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

                       
db = SQLAlchemy(app)


#AWS bucket
def upload_to_s3(file_path, s3_key):

    s3 = boto3.client('s3')
    
    try:
        s3.upload_file(file_path, bucketName, s3_key)
        print(f"File {file_path} uploaded to S3 bucket {bucketName} with key {s3_key}")
        return f"https://{bucketName}.s3.amazonaws.com/{s3_key}"

    except Exception as e:
        print(e)


class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    day = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric, nullable=False)
    description = db.Column(db.String(100), nullable=False)
    expenseDate = db.Column(db.String(10), nullable=False)
    week = db.Column(db.String(10), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    receipt_name = db.Column(db.String(100), nullable=True)
    receipt_url = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f'<Expense {self.amount} - {self.description}>'


class User(db.Model):
    __tablename__ = 'users'
    userID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    userName = db.Column(db.String(20), nullable=False)
    userPass = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<User {self.userName}>'
    

@app.before_request
def create_tables():
    db.create_all()



@app.route('/')
def home():
    return render_template('login.html')


@app.route('/signIn')
def signIn():

    userName = request.args['userName']
    userPass = request.args['userPass']
    
    results = db.session.query(User).where(User.userName == userName).where(User.userPass == userPass).all()
    
    if results:
        return render_template('expenses.html', year=datetime.datetime.now().year)
    else:
        return render_template('login.html', message = "Login failed")
    

@app.route('/signUp', methods=['POST'])
def signUp():

    userName = request.form['userName']
    userPass = request.form['userPass']

    new_user = User(userName=userName, userPass=userPass)

    db.session.add(new_user)
    db.session.commit()

    return render_template('login.html', message = "Registration Succesfull")



@app.route('/add', methods=['POST'])
def add_expense():

    day = request.form['finDay']
    month = request.form['finMonth']
    year = request.form['finYear']
    week = request.form['finWeek']
    amount = request.form['finAmount']
    description = request.form['finDescription'] 
    showWeek = request.form.get('chkShowWeek')
    showMonth = request.form.get('chkShowMonth')

    amount = amount.replace('$','')
    
    arr = week.split(":")
    weekStr = arr[0]

    arr = arr[1].strip().split(" - ")        
    fromDate = arr[0]

    arr = fromDate.split("/")

    startDay = int(arr[1])
    day = int(day)

    startDay = startDay + day - 1
    expenseDate = arr[0] + '/' + str(startDay) + '/' + arr[2]

    match day:
        case 1:
            dayStr="Friday"
        case 2:
            dayStr="Saturday"
        case 3:
            dayStr="Sunday"
        case 4:
            dayStr="Monday"
        case 5:
            dayStr="Tuesday"
        case 6:
            dayStr="Wednesday"
        case 7:
            dayStr="Thursday"
        
        
    new_expense = Expense(day=dayStr, amount=amount, description=description, expenseDate=expenseDate, week=weekStr, month=month, year=year)
    
    db.session.add(new_expense)
    db.session.commit()


    #Refresh template
    results = show_day(day, month, week, year, showWeek, showMonth)
    
    expenses = results[0]
    total = results[1]
    showWeek = results[3]
    showMonth = results[4]
    
    return render_template('expenses.html', expenses=expenses, day=day, week=week, month=month, year=year, showWeek=showWeek, showMonth=showMonth, total=total)


@app.route('/showDay', methods=['POST'])
def show_day():

    day = request.form.get('finDay')
    month = request.form['finMonth']
    year = request.form['finYear']
    week = request.form['finWeek'] 
    showWeek = request.form.get('chkShowWeek')
    showMonth = request.form.get('chkShowMonth')

    #Refresh template
    results = show_day(day, month, week, year, showWeek, showMonth)
    
    expenses = results[0]
    total = results[1]
    day = results[2]
    showWeek = results[3]
    showMonth = results[4]

    return render_template('expenses.html', expenses=expenses, day=day, week=week, month=month, year=year, showWeek=showWeek, showMonth=showMonth, total=total)



@app.route('/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    
    day = request.form.get('finDay')
    month = request.form['finMonth']
    year = request.form['finYear']
    week = request.form['finWeek']
    showWeek = request.form.get('chkShowWeek')
    showMonth = request.form.get('chkShowMonth')
    

    #Delete record
    expense = Expense.query.get(expense_id)

    if expense:
        db.session.delete(expense)
        db.session.commit()


    #Refresh template
    results = show_day(day, month, week, year, showWeek, showMonth)
    
    expenses = results[0]
    total = results[1]
    day = results[2]
    showWeek = results[3]
    showMonth = results[4]

    return render_template('expenses.html', expenses=expenses, day=day, week=week, month=month, year=year, showWeek=showWeek, showMonth=showMonth, total=total)



@app.route('/edit/<int:expense_id>', methods=['POST'])
def edit_expense(expense_id):

    day = request.form.get('finDay')
    month = request.form['finMonth']
    year = request.form['finYear']
    week = request.form['finWeek']
    showWeek = request.form.get('chkShowWeek')
    showMonth = request.form.get('chkShowMonth')

    editText = request.form['txtEdit_' + str(expense_id)]


    #Edit record
    expense = Expense.query.get(expense_id)
    expense.description = editText
    
    db.session.commit()


    #Refresh template
    results = show_day(day, month, week, year, showWeek, showMonth)
    
    expenses = results[0]
    total = results[1]
    day = results[2]
    showWeek = results[3]
    showMonth = results[4]

    return render_template('expenses.html', expenses=expenses, day=day, week=week, month=month, year=year, showWeek=showWeek, showMonth=showMonth, total=total)



@app.route('/clear', methods=['POST'])
def clearExpenses():
    
    clear = request.form['clear']

    day = request.form.get('finDay')
    month = request.form['finMonth']
    year = request.form['finYear']
    week = request.form['finWeek']
    showWeek = request.form.get('chkShowWeek')
    showMonth = request.form.get('chkShowMonth')

    arr = week.split(":")
    weekStr = arr[0]

    if day:
        day = int(day)

        match day:
            case 1:
                dayStr="Friday"
            case 2:
                dayStr="Saturday"
            case 3:
                dayStr="Sunday"
            case 4:
                dayStr="Monday"
            case 5:
                dayStr="Tuesday"
            case 6:
                dayStr="Wednesday"
            case 7:
                dayStr="Thursday"
    
            
    if clear == 'month':
        SQL = "Select * From expenses Where month = " + month + " AND year = " + year + " Order By week, day"
                
    elif clear == 'week':
        SQL = "Select * From expenses Where week = '" + weekStr + "' AND month = " + month + " AND year = " + year + " Order By day"

    elif clear == 'day':
        SQL = "Select * From expenses Where day = '" + dayStr + "' AND week = '" + weekStr + "' AND month = " + month + " AND year = " + year


    #Clear records
    expenses = db.session.query(Expense).from_statement(text(SQL)).all()

    for expense in expenses:
        db.session.delete(expense)

    db.session.commit()


    #Refresh template
    results = show_day(day, month, week, year, showWeek, showMonth)
    
    expenses = results[0]
    total = results[1]
    day = results[2]
    showWeek = results[3]
    showMonth = results[4]

    return render_template('expenses.html', expenses=expenses, day=day, week=week, month=month, year=year, showWeek=showWeek, showMonth=showMonth, total=total)



@app.route('/attach/<int:expense_id>', methods=['POST'])
def attach_receipt(expense_id):

    day = request.form.get('finDay')
    month = request.form['finMonth']
    year = request.form['finYear']
    week = request.form['finWeek']
    showWeek = request.form.get('chkShowWeek')
    showMonth = request.form.get('chkShowMonth')

    attachFile = request.files['fcReceipt_' + str(expense_id)]
    receipt_name = attachFile.filename

    file_path = os.path.join(basedir, attachFile.filename)
    attachFile.save(file_path)

    #Local
    # receipt_url = file_path
        
    #AWS bucket
    receipt_url = upload_to_s3(file_path, attachFile.filename)
    os.remove(file_path)


    #Edit record
    expense = Expense.query.get(expense_id)

    expense.receipt_name = receipt_name
    expense.receipt_url = receipt_url
    
    db.session.commit()


    #Refresh template
    results = show_day(day, month, week, year, showWeek, showMonth)
    
    expenses = results[0]
    total = results[1]
    day = results[2]
    showWeek = results[3]
    showMonth = results[4]

    return render_template('expenses.html', expenses=expenses, day=day, week=week, month=month, year=year, showWeek=showWeek, showMonth=showMonth, total=total, receipt_name=receipt_name, receipt_url=receipt_url)



def show_day(day, month, week, year, showWeek, showMonth):

    if showWeek == "on":
        showWeek = "true"
    else:
        showWeek = "false"

    if showMonth == "on":
        showMonth = "true"
    else:
        showMonth = "false"

    if week:
        arr = week.split(":")
        weekStr = arr[0]        
        
    if day:
        day = int(day)

        match day:
            case 1:
                dayStr="Friday"
            case 2:
                dayStr="Saturday"
            case 3:
                dayStr="Sunday"
            case 4:
                dayStr="Monday"
            case 5:
                dayStr="Tuesday"
            case 6:
                dayStr="Wednesday"
            case 7:
                dayStr="Thursday"
    else:
        day = 0    


    # Get Main dataset
    if showMonth == "true":
        SQL = "Select * From expenses Where month = " + month + " AND year = " + year + " Order By week, day"

    elif showWeek == "true":
        SQL = "Select * From expenses Where week = '" + weekStr + "' AND month = " + month + " AND year = " + year + " Order By day"

    else:
        SQL = "Select * From expenses Where day = '" + dayStr + "' AND week = '" + weekStr + "' AND month = " + month + " AND year = " + year

    expenses = db.session.query(Expense).from_statement(text(SQL)).all()


    #Get Totals
    if showMonth == "true":

        total = db.session.query(functions.sum(Expense.amount))\
                          .where(Expense.month == month)\
                          .where(Expense.year == year).scalar()

    elif showWeek == "true":
        
        total = db.session.query(functions.sum(Expense.amount))\
                          .where(Expense.week == weekStr)\
                          .where(Expense.month == month)\
                          .where(Expense.year == year).scalar()

    else:

        total = db.session.query(functions.sum(Expense.amount))\
                          .where(Expense.day == dayStr)\
                          .where(Expense.week == weekStr)\
                          .where(Expense.month == month)\
                          .where(Expense.year == year).scalar()
                
    return expenses, total, day, showWeek, showMonth



if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)



