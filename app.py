from flask import Flask, render_template, jsonify, request, session, redirect
import firebase_admin
from firebase_admin import credentials, firestore, db
from datetime import datetime, timedelta
from flask_cors import CORS
import json
import uuid
from functools import wraps
cred = credentials.Certificate("./serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://ibm-hackathon-f5e60-default-rtdb.asia-southeast1.firebasedatabase.app'
})

database = firestore.client()
ref = db.reference("UsersData")
data = ref.get()
app = Flask(__name__)
cors = CORS(app)
app.secret_key = "gccy7dfiygivlucxr7s76680tg9ug"


def extract_arrays(data):
    timestamps = [unix_timestamp_to_hours_minutes(entry['timestamp']) for entry in data.values()]
    turbidity_array = []
    tds_array = []
    ph_array = []
    ec_array = []
    flow_array = []
    temperature_array = []

    for key, entry in data.items():
        # timestamps.append(unix_timestamp_to_hours_minutes(entry['timestamp']))
        turbidity_array.append(float(entry['turbidityvalue']))
        tds_array.append(float(entry['tdsvalue']))
        ph_array.append(float(entry['phvalue']))
        ec_array.append(float(entry['ecvalue']))
        flow_array.append(float(entry['flowrate']))
        temperature_array.append(float(entry['temperature']))

    return {
        'timestamps': timestamps,
        'turbidity_array': turbidity_array,
        'tds_array': tds_array,
        'ph_array': ph_array,
        'ec_array': ec_array,
        'flow_array': flow_array,
        'temperature_array': temperature_array,
    }

def unix_timestamp_to_hours_minutes(unix_timestamp):
    unix_timestamp = int(unix_timestamp)
    # Convert the Unix timestamp to a datetime object
    dt_object = datetime.fromtimestamp(unix_timestamp)
    
    # Extract hours and minutes from the datetime object and format them
    hours = str(dt_object.hour).zfill(2)
    minutes = str(dt_object.minute).zfill(2)
    
    return f"{hours}:{minutes}"


realTimeValues = extract_arrays(data["qAHwREgZneMJ6pxPUfOrZ1wcOBY2"]['readings'])
print(realTimeValues)


def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if 'email' not in session:
            return redirect('/')
        return func(*args, **kwargs)
    return decorated_view

def time_difference(timestamp):
    # Convert the timestamp to a datetime object
    timestamp_datetime = datetime.fromtimestamp(timestamp)

    # Get the current time as a datetime object
    current_time = datetime.now()

    # Calculate the time difference
    time_delta = current_time - timestamp_datetime

    # Calculate the time difference in minutes
    minutes_difference = time_delta.total_seconds() / 60

    if minutes_difference < 60:
        return f"{int(minutes_difference)} min"
    elif minutes_difference < 1440:  # Less than 24 hours
        return f"{int(minutes_difference / 60)} hours"
    elif minutes_difference < 10080:  # Less than 7 days (1 week)
        return f"{int(minutes_difference / 1440)} days"
    elif minutes_difference < 43800:  # Less than 30 days (1 month)
        return f"{int(minutes_difference / 10080)} weeks"
    else:
        return f"{int(minutes_difference / 43800)} months"

@app.route('/society/<society_id>')
@login_required
def society_homepage(society_id):
    complaints_ref = database.collection('complaints')
    documents = complaints_ref.where("society_id", "==", int(society_id)).stream()
    complaints = []
    for doc in documents:
        curr = doc.to_dict()
        diff = time_difference(curr['timestamp'])
        complaints.append({'complaint': curr['complaint'], 'diff': diff})

    return render_template('index.html', title='Home', realtime_values=json.dumps(realTimeValues),society_id=society_id, complaints=complaints[-5:])


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        user_ref = database.collection('user')
        documents = user_ref.where('email', '==', email).stream()
        user = {}
        for doc in documents:
            user = doc.to_dict()
        if len(user) >= 2 and user['password'] == password:
            session.clear()
            session['email'] = user['email']
            print("logged in")
            if user['role'] == 'secretary':
                session['society_id'] = user['society_id']
                return redirect('/society/'+str(user['society_id']))
            else:
                return redirect('/government')

        else:
            return render_template('pages-login.html', message="Login failed. Please check your credentials.")
    return render_template('pages-login.html')


@app.route('/complaints')
def complaints():
    complaints_ref = database.collection('complaints')
    loginType = 0             # 0 for government, 1 for society
    if 'society_id' in session:
        loginType = 1
        documents = complaints_ref.where(
            'society_id', '==', session['society_id']).stream()
    else:
        documents = complaints_ref.where('level','==','government').stream()
    complaints = []
    for doc in documents:
        curr = doc.to_dict()
        date = datetime.fromtimestamp(curr['timestamp'])
        formatted_date = date.strftime("%d-%m-%Y")
        curr['date'] = formatted_date
        complaints.append(curr)
    return render_template('complaints.html', login_type=loginType ,complaints=complaints, society_id=session.get('society_id', None))

# Accept complaint for society and government
@app.route('/acceptcomplaint/<complaint_id>')
def accept_complaint(complaint_id):
    complaint_ref = database.collection('complaints').where('id', '==', complaint_id).limit(1).get()

    if not complaint_ref:
        print("No matching document found")
        return "No matching document found"

    complaint_doc = list(complaint_ref)[0].reference
    complaint = complaint_doc.get().to_dict()

    if complaint['level'] == 'government':
        complaint_doc.update({'status': 'Accepted'})
    else:
        complaint_doc.update({'level': 'government'})
    return redirect('/complaints')

# Reject complaint for society and government
@app.route('/rejectcomplaint/<complaint_id>')
def reject_complaint(complaint_id):
    complaint_ref = database.collection('complaints').where(
        'id', '==', complaint_id).limit(1).get()
    
    if not complaint_ref:
        return "No matching document found"
    
    complaint_doc = list(complaint_ref)[0].reference

    complaint_doc.update({'status': 'Rejected'})

    return redirect('/complaints')


@app.route('/logcomplaint', methods=['GET', 'POST'])
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
        complaints_ref = database.collection('complaints')
        complaints_ref.add(data)
        return render_template('logcomplaint.html', message="Complaint logged successfully")
    return render_template('logcomplaint.html')


# Last 7 days
@app.route('/api/society/week/<society_id>/<value_type>')
def societyApi(society_id, value_type):
    society_id = int(society_id)
    society_ref = database.collection('society')
    documents = society_ref.where('society_id', '==', society_id).stream()

    values = []
    timestamps = []

    for doc in documents:
        data = doc.to_dict()
        timestamp = data.get('timestamp')
        # Replace 'ph' with the actual field name for pH value
        ph_value = round(data.get(value_type), 2)

        if timestamp is not None and ph_value is not None:
            timestamps.append(timestamp)
            values.append(ph_value)

    if len(timestamps) == 0 or len(values) == 0:
        return jsonify({value_type: [], 'timestamps': []})

    # Sort the data by timestamps
    sorted_data = sorted(zip(timestamps, values),
                         key=lambda x: x[0], reverse=True)

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
    society_ref = database.collection('society')
    documents = society_ref.stream()

    data = []
    for doc in documents:
        data.append(doc.to_dict())
    data = sorted(data, key=lambda x: x["timestamp"], reverse=True)
    return jsonify(data[-7:])


@app.route('/api/month/district/<district>/<year>/<month>/<value_type>')
def calculate_average_district_weekly_data(district, year, month, value_type):
    year = int(year)
    month = int(month)

    society_ref = database.collection('society')
    documents = society_ref.where('district', '==', district).stream()

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
                key_averages[key_to_average] = round(
                    key_averages[key_to_average], 2)

        key_averages["timestamp"] = values[0]["timestamp"]
        averages[key] = key_averages
        week_labels.append(f'wk{key}')  # Create week labels

    # Check if averages is empty, and return the empty response if there's no data
    if not averages:
        return jsonify({'weeks': [], 'values': []})

    # Sort week labels and values based on week numbers
    sorted_weeks_and_values = sorted(zip(week_labels, [
                                     entry[value_type] for entry in averages.values()]), key=lambda x: int(x[0][2:]))
    sorted_week_labels, sorted_values = zip(*sorted_weeks_and_values)

    response_data = {
        'weeks': sorted_week_labels,
        'values': sorted_values
    }

    return jsonify(response_data)


# Get month data
@app.route('/api/month/<society_id>/<year>/<month>/<value_type>')
def calculate_average_weekly_data(society_id, year, month, value_type):
    society_id = int(society_id)
    year = int(year)
    month = int(month)

    society_ref = database.collection('society')
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
                key_averages[key_to_average] = round(
                    key_averages[key_to_average], 2)

        key_averages["timestamp"] = values[0]["timestamp"]
        averages[key] = key_averages
        week_labels.append(f'wk{key}')  # Create week labels

    # Check if averages is empty, and return the empty response if there's no data
    # if not averages:
    #     return jsonify({'weeks': [], 'values': []})

    # Sort week labels and values based on week numbers
    sorted_weeks_and_values = sorted(zip(week_labels, [
                                     entry[value_type] for entry in averages.values()]), key=lambda x: int(x[0][2:]))
    sorted_week_labels, sorted_values = zip(*sorted_weeks_and_values)

    response_data = {
        'weeks': sorted_week_labels,
        'values': sorted_values
    }

    return jsonify(response_data)

# Get year data for district
@app.route('/api/year/district/<district>/<year>/<value_type>')
def calculate_average_monthly_district_data(district, year, value_type):
    year = int(year)
    keys_to_average = [value_type]

    society_ref = database.collection('society')
    documents = society_ref.where('district', '==', district).stream()

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
        filtered_data = [entry for entry in data if start_date <=
                         datetime.fromtimestamp(entry["timestamp"]) < end_date]

        if filtered_data:
            key_averages = {}
            for key_to_average in keys_to_average:
                key_averages[key_to_average] = round(
                    sum(entry[key_to_average] for entry in filtered_data) / len(filtered_data), 2)

            key_averages["timestamp"] = filtered_data[0]["timestamp"]
            # Create month labels mnth1, mnth2, ...
            monthly_label = f'mnth{month}'
            monthly_data[monthly_label] = key_averages

    # Sort the month labels and values based on month numbers
    sorted_months_and_values = sorted(
        [(int(month_label[4:]), monthly_data[month_label][value_type])
         for month_label in monthly_data],
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


# Get year data for society
@app.route('/api/year/<society_id>/<year>/<value_type>')
def calculate_average_monthly_data(society_id, year, value_type):
    society_id = int(society_id)
    year = int(year)
    keys_to_average = [value_type]

    society_ref = database.collection('society')
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
        filtered_data = [entry for entry in data if start_date <=
                         datetime.fromtimestamp(entry["timestamp"]) < end_date]

        if filtered_data:
            key_averages = {}
            for key_to_average in keys_to_average:
                key_averages[key_to_average] = round(
                    sum(entry[key_to_average] for entry in filtered_data) / len(filtered_data), 2)

            key_averages["timestamp"] = filtered_data[0]["timestamp"]
            # Create month labels mnth1, mnth2, ...
            monthly_label = f'mnth{month}'
            monthly_data[monthly_label] = key_averages

    # Sort the month labels and values based on month numbers
    sorted_months_and_values = sorted(
        [(int(month_label[4:]), monthly_data[month_label][value_type])
         for month_label in monthly_data],
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


# Get year data for locality
@app.route('/api/year/locality/<locality>/<year>/<value_type>')
def calculate_average_monthly_locality_data(locality, year, value_type):
    year = int(year)
    keys_to_average = [value_type]

    society_ref = database.collection('society')
    documents = society_ref.where('locality', '==', locality).stream()

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
        filtered_data = [entry for entry in data if start_date <=
                         datetime.fromtimestamp(entry["timestamp"]) < end_date]

        if filtered_data:
            key_averages = {}
            for key_to_average in keys_to_average:
                key_averages[key_to_average] = round(
                    sum(entry[key_to_average] for entry in filtered_data) / len(filtered_data), 2)

            key_averages["timestamp"] = filtered_data[0]["timestamp"]
            # Create month labels mnth1, mnth2, ...
            monthly_label = f'mnth{month}'
            monthly_data[monthly_label] = key_averages

    # Sort the month labels and values based on month numbers
    sorted_months_and_values = sorted(
        [(int(month_label[4:]), monthly_data[month_label][value_type])
         for month_label in monthly_data],
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

# Get district month data
@app.route('/api/month/locality/<locality>/<year>/<month>/<value_type>')
def calculate_average_locality_weekly_data(locality, year, month, value_type):
    year = int(year)
    month = int(month)

    society_ref = database.collection('society')
    documents = society_ref.where('locality', '==', locality).stream()

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
                key_averages[key_to_average] = round(
                    key_averages[key_to_average], 2)

        key_averages["timestamp"] = values[0]["timestamp"]
        averages[key] = key_averages
        week_labels.append(f'wk{key}')  # Create week labels

    # Check if averages is empty, and return the empty response if there's no data
    if not averages:
        return jsonify({'weeks': [], 'values': []})

    # Sort week labels and values based on week numbers
    sorted_weeks_and_values = sorted(zip(week_labels, [
                                     entry[value_type] for entry in averages.values()]), key=lambda x: int(x[0][2:]))
    sorted_week_labels, sorted_values = zip(*sorted_weeks_and_values)

    response_data = {
        'weeks': sorted_week_labels,
        'values': sorted_values
    }

    return jsonify(response_data)


# Open new district page
@app.route('/district/<district>')
def district_homepage(district):
    return render_template('district.html', title='District', district=district)

# Open new locality page
@app.route('/locality/<locality>')
def locality_homepage(locality):
    return render_template('locality.html', title='Locality', locality=locality)

# Government Route
@app.route('/government')
def government_homepage():
    society_ref = database.collection('society')
    documents = society_ref.stream()
    unique_localities = set()
    unique_districts = set()
    for doc in documents:
        curr = doc.to_dict()
        unique_localities.add(curr['locality'])
        unique_districts.add(curr['district'])
    return render_template('government.html', title='Government', localities=unique_localities, districts=unique_districts)

# Enable debug mode
app.debug = True

# Your Flask app routes and other configurations go here

if __name__ == '__main__':
    app.run(debug=True)
