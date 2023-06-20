from flask import Flask,render_template,redirect,session,request,url_for,jsonify
from  flask_sqlalchemy import SQLAlchemy
from constant import price,adminname,adminpassword
from sqlalchemy import LargeBinary,BINARY
import psycopg2
import base64
from io import BytesIO
from PIL import Image
from img2txt import extract_data

app = Flask(__name__)
app.secret_key = 'htet'

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:toor@localhost:5432/Cycle_Ticket'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.app_context().push()

class Users(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable= False)
    password = db.Column(db.String(100), nullable= False)
db.create_all()

class Orders(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, nullable= False)
    user_name = db.Column(db.String(100), nullable = False)
    tickets = db.Column(db.String(1000), nullable = False)
    image = db.Column(LargeBinary)
    verify = db.Column(db.String(50),nullable= True)
db.create_all()
    


@app.route('/')
def home():
    validate_user = None
    tickets = []
    selected_ticket = []
    if session and session['username']:
       validate_user = session['username']
       orders= Orders.query.all()
       if orders:
            for order in orders:
                pending_ticket = order.tickets.split(',')
                print(order.tickets)
                print(pending_ticket)
                for i in pending_ticket:
                    selected_ticket.append(i)
            print(selected_ticket)
       for i in range(1,101):
            tickets.append(f"{i:03}")
       return render_template('home.html',username = validate_user, tickets = tickets, selected_ticket = selected_ticket)
    elif session and session['admin_username']:
        validate_user = session['admin_username']
        return render_template('home.html',admin_name = validate_user)
    return render_template('home.html')

@app.route("/login", methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == adminname and password == adminpassword:
            session['admin_username']= adminname
            return redirect('/admin')
        user = Users.query.filter_by(username = username).first()
        if user:
            session['username'] =  user.username
            return redirect('/')            
    return render_template('login.html')

@app.route("/register", methods = ['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # user = Users.query.filter_by(username = name).first()
        user = Users(username = username, password = password)
        db.session.add(user)
        db.session.commit()
        return redirect('/')
    return render_template('register.html')

@app.route('/ticket_order', methods = ['POST','GET'])
def ticket_order():
    if request.method=='POST':
        form_selected_tickets = request.form.getlist("ticket[]")
        
        if len(form_selected_tickets):
            totalprice = len(form_selected_tickets) * price
            selected_ticket = ""
            for ticket in form_selected_tickets:
                if selected_ticket:
                    selected_ticket += ','
                selected_ticket += ticket
            print(selected_ticket)
            if session and session['username']:
                validUser = session['username']
                user = Users.query.filter_by(username = validUser).first()
                validUserId = user.id
                if validUser:
                    new_order = Orders(user_id = validUserId , user_name = validUser , tickets = selected_ticket)
                    db.session.add(new_order)
                    db.session.commit()
                    order= Orders.query.order_by(Orders.id.desc()).first()
                    order_id = order.id
                    return render_template('order.html',username = validUser,tickets = form_selected_tickets,totalprice=totalprice,price=price, orderId = order_id)
                else:
                    return redirect('/login')
            else:
                return redirect('/login')
        else:
            return redirect('/')
    

@app.route('/update/<int:orderId>' , methods=['POST'])
def update(orderId):
    if request.method == 'POST':
        image = request.files['img']
        upload_image = image.read()
        data = Orders.query.get(orderId)
        if data.image:
            data.image = upload_image
            db.session.add(data)
        else:
            data.image = upload_image
            db.session.commit()
        checkid = orderId
        return redirect(url_for('check',checkid = checkid))
    return render_template('order.html')  
 
@app.route('/reupdate/<int:oid>' , methods=['POST'])
def reupdate(oid):
    if request.method == 'POST':
        image = request.files['img']
        upload_image = image.read()
        data = Orders.query.get(oid)
        if data.image:
            data.image = upload_image
            data.verify = None
            db.session.add(data)
            db.session.commit()
        else:
            data.image = upload_image
            db.session.commit()
        checkid = oid
        return redirect(url_for('check',checkid = checkid))
    return redirect('/')  
            
@app.route('/check/<int:checkid>',methods=['GET','POST'])
def check(checkid):
    if session and session[' username ']:
        validate_user = session[' username ']
        data = Orders.query.get(checkid)
        if not data.verify :
            return render_template('check.html',username = validate_user,checking = None)
        if data.verify == 'Rejected':
            pending_tickets = data.tickets.split(',')
            total_price = len(pending_tickets) * price
            orderId = checkid
            return render_template('order.html',username = validate_user, checking=data.verify, data = data, pending_tickets= pending_tickets, price = price,total_price = total_price, oid = orderId)
    return render_template('check.html',checking = data.verify)

@app.route('/admin')
def admin():
    orders = Orders.query.all()
    if session and session['admin_username']:
        valid_user = session['admin_username']
    order_tickets = []
    order_pending = []
    if orders:
        for order in orders:
            if order.image :
                file = BytesIO(order.image)
                image = Image.open(file)
                image_string_read = extract_data(image)
                order.image = base64.b64encode(order.image).decode('utf-8')
                if order.verify:
                    temp_dict = order.__dict__
                    temp_dict.update({"payment_info": image_string_read})
                    order_tickets.append(temp_dict)
                if not order.verify:
                    temp_dict = order.__dict__
                    temp_dict.update({"payment_info": image_string_read})
                    order_pending.append(temp_dict)
        return render_template('admin_dashboard.html',order_tickets = order_tickets,admin_name = valid_user, order_pending = order_pending)
    return render_template('admin_dashboard.html')
    

@app.route('/admin_accept/<int:orderid>')
def admin_accept(orderid):
    if orderid:
        data = Orders.query.get(orderid)
        data.verify = 'Accepted'
        db.session.commit()
        return redirect('/admin')
    return redirect('/')




@app.route('/admin_reject/<int:orderid>')
def admin_reject(orderid):
    if orderid:
        data = Orders.query.get(orderid)
        data.verify = "Rejected"
        db.session.commit()
        return redirect('/admin')
    return redirect('/')




@app.route('/logout')
def logout():
    session.pop('username',False)
    return redirect('/')

@app.route('/adminlogout')
def adminlogout():
    session.pop('admin_username',False)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)