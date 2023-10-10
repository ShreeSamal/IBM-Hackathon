from flask import Flask, render_template

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

# Enable debug mode
app.debug = True

# Your Flask app routes and other configurations go here

if __name__ == '__main__':
    app.run()