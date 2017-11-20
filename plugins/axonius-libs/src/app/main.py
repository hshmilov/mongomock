from flask import Flask
wsgi_main = Flask(__name__)
number = 0


@wsgi_main.route("/")
def hello():
    global number
    number = number + 1
    return """Hello there! This is the default page of axonius-docker-image, indicating everything is okay.
            <br>To run your own app, change main.py.<br><br>Run number: %d""" % (number, )


if __name__ == "__main__":
    wsgi_main.run(host='0.0.0.0')
