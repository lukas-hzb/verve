from flask import Flask, render_template

app = Flask(__name__)

@app.route('/debug')
def debug():
    return render_template('debug.html')

if __name__ == '__main__':
    app.run(debug=True)
