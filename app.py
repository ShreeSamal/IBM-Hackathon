from flask import Flask, render_template,jsonify,request,session,redirect
import firebase_admin
from firebase_admin import credentials,firestore
from datetime import datetime, timedelta
from flask_cors import CORS
import uuid
from functools import wraps
cred = credentials.Certificate("./serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()
app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "http://127.0.0.1:5000"}})
app.secret_key = "gccy7dfiygivlucxr7s76680tg9ug"

def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if 'email' not in session:
            return redirect('/login')
        return func(*args, **kwargs)
    return decorated_view

@app.route('/')
@login_required
def index():
    return render_template('index.html',title='Home')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        user_ref = db.collection('user')
        documents = user_ref.where('email', '==', email).stream()
        user = {}
        for doc in documents:
            user = doc.to_dict()
        if len(user)>=2 and user['password'] == password:
            session['email'] = user['email']
            return redirect('/')
        else:
            return render_template('pages-login.html',message="Login failed. Please check your credentials.")
    return render_template('pages-login.html')

@app.route('/complaints')
def complaints():
    
    return render_template('complaints.html')

@app.route('/logcomplaint',methods=['GET','POST'])
def logcomplaint():
    if request.method == "POST":
        data = {}
        data['id'] = str(uuid.uuid4())
        data['name'] = request.form['name']
        data['email'] = request.form['email']
        data['phone'] = request.form['phone']
        data['complaint'] = request.form['complaint']
        data['society_id'] = int(request.form['society_id'])
        data['timestamp'] = int(datetime.now().timestamp())
        data['district'] = request.form['district']
        data['status'] = 'pending'
        data['level'] = 'society'
        complaints_ref = db.collection('complaints')
        complaints_ref.add(data)
        return render_template('logcomplaint.html',message="Complaint logged successfully")
    return render_template('logcomplaint.html')


# Last 7 days
# @app.route('/api/society/week/<society_id>')
# def societyApi(society_id):
#     society_id = int(society_id)
#     society_ref = db.collection('society')
#     documents = society_ref.where('society_id', '==', society_id).stream()

#     data = []
#     for doc in documents:
#         data.append(doc.to_dict())
#     data = sorted(data, key=lambda x: x["timestamp"], reverse=True)
#     print("done")
#     return jsonify(data[-7:])


# Last 7 days
@app.route('/api/society/week/<society_id>/<value_type>')
def societyApi(society_id,value_type):
    society_id = int(society_id)
    society_ref = db.collection('society')
    documents = society_ref.where('society_id', '==', society_id).stream()

    values = []
    timestamps = []

    for doc in documents:
        data = doc.to_dict()
        timestamp = data.get('timestamp')
        ph_value = round(data.get(value_type),2)  # Replace 'ph' with the actual field name for pH value

        if timestamp is not None and ph_value is not None:
            timestamps.append(timestamp)
            values.append(ph_value)

    if len(timestamps) == 0 or len(values) == 0:
        return jsonify({"error": "No valid data found for the specified society_id"})

    # Sort the data by timestamps
    sorted_data = sorted(zip(timestamps, values), key=lambda x: x[0], reverse=True)

    # Separate the sorted data into two lists
    timestamps, values = zip(*sorted_data)

    # Return the last 7 elements of each list
    response_data = {
        'timestamps': timestamps[-7:],
        value_type: values[-7:]
    }

    return jsonify(response_data)



# Last 7 days
@app.route('/api/society')
def societyAll():
    society_ref = db.collection('society')
    documents = society_ref.stream()

    data = []
    for doc in documents:
        data.append(doc.to_dict())
    data = sorted(data, key=lambda x: x["timestamp"], reverse=True)
    return jsonify(data[-7:])

# Get month data
# @app.route('/api/month/<society_id>/<year>/<month>')
# def calculate_average_weekly_data(society_id, year, month):
#     society_id = int(society_id)
#     year = int(year)
#     month = int(month)
#     society_ref = db.collection('society')
#     documents = society_ref.where('society_id', '==', society_id).stream()

#     data = []
#     for doc in documents:
#         data.append(doc.to_dict())
#     weekly_data = {}
#     start_date = datetime(year, month, 1)
#     if month == 12:
#         end_date = datetime(year + 1, 1, 1)
#     else:
#         end_date = datetime(year, month + 1, 1)

#     # Iterate through the data, filter it for the specified month and year, and group it by week
#     for entry in data:
#         entry_date = datetime.fromtimestamp(entry["timestamp"])
        
#         if start_date <= entry_date < end_date:
#             week_number = entry_date.strftime("%U")
            
#             if week_number not in weekly_data:
#                 weekly_data[week_number] = []
            
#             weekly_data[week_number].append(entry)

#     averages = {}
#     keys_to_average = ["ecvalue", "flowrate", "phvalue", "tdsvalue", "temperature", "turbidityvalue"]

#     for key, values in weekly_data.items():
#         key_averages = {}
#         for entry in values:
#             for key_to_average in keys_to_average:
#                 if key_to_average not in key_averages:
#                     key_averages[key_to_average] = 0
#                 key_averages[key_to_average] += entry[key_to_average]

#         if len(values) > 0:
#             for key_to_average in keys_to_average:
#                 key_averages[key_to_average] /= len(values)

#         key_averages["timestamp"] = values[0]["timestamp"]
#         averages[key] = key_averages
#     return jsonify(averages)


# Get month data
@app.route('/api/month/<society_id>/<year>/<month>/<value_type>')
def calculate_average_weekly_data(society_id, year, month, value_type):
    society_id = int(society_id)
    year = int(year)
    month = int(month)

    society_ref = db.collection('society')
    documents = society_ref.where('society_id', '==', society_id).stream()

    data = []
    for doc in documents:
        data.append(doc.to_dict())
    
    weekly_data = {}
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    # Iterate through the data, filter it for the specified month and year, and group it by week
    for entry in data:
        entry_date = datetime.fromtimestamp(entry["timestamp"])
        
        if start_date <= entry_date < end_date:
            week_number = (entry_date - start_date).days // 7 + 1
            
            if week_number not in weekly_data:
                weekly_data[week_number] = []
            
            weekly_data[week_number].append(entry)

    averages = {}
    keys_to_average = [value_type]  # Use the specified value_type
    week_labels = []  # Store week labels

    for key, values in weekly_data.items():
        key_averages = {}
        for entry in values:
            for key_to_average in keys_to_average:
                if key_to_average not in key_averages:
                    key_averages[key_to_average] = 0
                key_averages[key_to_average] += entry[key_to_average]

        if len(values) > 0:
            for key_to_average in keys_to_average:
                key_averages[key_to_average] /= len(values)
                key_averages[key_to_average] = round(key_averages[key_to_average], 2)

        key_averages["timestamp"] = values[0]["timestamp"]
        averages[key] = key_averages
        week_labels.append(f'wk{key}')  # Create week labels

    # Sort week labels and values based on week numbers
    sorted_weeks_and_values = sorted(zip(week_labels, [entry[value_type] for entry in averages.values()]), key=lambda x: int(x[0][2:]))
    sorted_week_labels, sorted_values = zip(*sorted_weeks_and_values)

    response_data = {
        'weeks': sorted_week_labels,
        'values': sorted_values
    }

    return jsonify(response_data)



# # Months of year
# @app.route('/api/year/<society_id>/<year>')
# def calculate_average_monthly_data(society_id, year):
#     keys_to_average = ["ecvalue", "flowrate", "phvalue", "tdsvalue", "temperature", "turbidityvalue"]
#     society_id = int(society_id)
#     year = int(year)
#     society_ref = db.collection('society')
#     documents = society_ref.where('society_id', '==', society_id).stream()

#     data = []
#     for doc in documents:
#         data.append(doc.to_dict())
    
#     monthly_data = {}
#     for month in range(1, 13):
#         start_date = datetime(year, month, 1)
#         if month == 12:
#             end_date = datetime(year + 1, 1, 1)
#         else:
#             end_date = datetime(year, month + 1, 1)
        
#         # Filter data for the specified month and year
#         filtered_data = [entry for entry in data if start_date <= datetime.fromtimestamp(entry["timestamp"]) < end_date]
        
#         if filtered_data:
#             key_averages = {}
#             for key_to_average in keys_to_average:
#                 key_averages[key_to_average] = sum(entry[key_to_average] for entry in filtered_data) / len(filtered_data)
            
#             key_averages["timestamp"] = filtered_data[0]["timestamp"]
#             monthly_data[str(month)] = key_averages
    
#     return jsonify(monthly_data)

@app.route('/api/year/<society_id>/<year>/<value_type>')
def calculate_average_monthly_data(society_id, year, value_type):
    society_id = int(society_id)
    year = int(year)
    keys_to_average = [value_type]

    society_ref = db.collection('society')
    documents = society_ref.where('society_id', '==', society_id).stream()

    data = []
    for doc in documents:
        data.append(doc.to_dict())

    monthly_data = {}

    for month in range(1, 13):
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # Filter data for the specified month and year
        filtered_data = [entry for entry in data if start_date <= datetime.fromtimestamp(entry["timestamp"]) < end_date]

        if filtered_data:
            key_averages = {}
            for key_to_average in keys_to_average:
                key_averages[key_to_average] = round(sum(entry[key_to_average] for entry in filtered_data) / len(filtered_data), 2)

            key_averages["timestamp"] = filtered_data[0]["timestamp"]
            monthly_label = f'mnth{month}'  # Create month labels mnth1, mnth2, ...
            monthly_data[monthly_label] = key_averages


    # Sort the month labels and values based on month numbers
    sorted_months_and_values = sorted(
        [(int(month_label[4:]), monthly_data[month_label][value_type]) for month_label in monthly_data],
        key=lambda x: x[0]
    )

    # Check if the list is empty and return empty arrays
    if not sorted_months_and_values:
        return jsonify({'months': [], 'values': []})

    sorted_month_labels, sorted_values = zip(*sorted_months_and_values)

    return jsonify({
        'months': sorted_month_labels,
        'values': sorted_values
    })


# Enable debug mode
app.debug = True

# Your Flask app routes and other configurations go here

if __name__ == '__main__':
    app.run(debug=True)