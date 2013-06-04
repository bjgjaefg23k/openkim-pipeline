from flask import Flask
from kimquery import query
app = Flask(__name__)

@app.route("/")
def main():
    return "hello world"

@app.route("/test/")
def test():
    return "this is a test."

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=8080)
