from flask import Flask, render_template,jsonify
import firebase_admin
from firebase_admin import credentials,firestore
from datetime import datetime, timedelta

cred = credentials.Certificate("./serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html',title='Home')

@app.route('/login')
def login():

    return render_template('pages-login.html')

@app.route('/complaints')
def complaints():
    
    return render_template('complaints.html')

@app.route('/logcomplaint')
def logcomplaint():
    
    return render_template('logcomplaint.html')


# Last 7 days
@app.route('/api/society/week/<society_id>')
def societyApi(society_id):
    society_id = int(society_id)
    society_ref = db.collection('society')
    documents = society_ref.where('society_id', '==', society_id).stream()

    data = []
    for doc in documents:
        data.append(doc.to_dict())
    data = sorted(data, key=lambda x: x["timestamp"], reverse=True)
    print("done")
    return jsonify(data[-7:])


# Weeks of months
@app.route('/api/month/<society_id>/<year>/<month>')
def calculate_average_weekly_data(society_id, year, month):
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
            week_number = entry_date.strftime("%U")
            
            if week_number not in weekly_data:
                weekly_data[week_number] = []
            
            weekly_data[week_number].append(entry)

    averages = {}
    keys_to_average = ["ecvalue", "flowrate", "phvalue", "tdsvalue", "temperature", "turbidityvalue"]

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

        key_averages["timestamp"] = values[0]["timestamp"]
        averages[key] = key_averages
    return jsonify(averages)


# Months of year
@app.route('/api/year/<society_id>/<year>')
def calculate_average_monthly_data(society_id, year):
    keys_to_average = ["ecvalue", "flowrate", "phvalue", "tdsvalue", "temperature", "turbidityvalue"]
    society_id = int(society_id)
    year = int(year)
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
                key_averages[key_to_average] = sum(entry[key_to_average] for entry in filtered_data) / len(filtered_data)
            
            key_averages["timestamp"] = filtered_data[0]["timestamp"]
            monthly_data[str(month)] = key_averages
    
    return jsonify(monthly_data)
# Enable debug mode
app.debug = True

# Your Flask app routes and other configurations go here

if __name__ == '__main__':
    app.run(debug=True)