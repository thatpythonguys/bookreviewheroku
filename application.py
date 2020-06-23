import os

from flask import Flask, session, render_template, request, redirect, url_for, flash, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
#import flask.ext.login




app = Flask(__name__)


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#--------------------------------------------------------------------------------------------------------------------------------------
#HOME PAGE
@app.route("/")
def index():
    if "logged_in" not in session or session.get("logged_in") == False:
        username = "Guest"
    else:
        username = session["USERNAME"]
    return render_template("index.html", username=username)

#REGISTER
@app.route("/register", methods = ["GET", "POST"])
def register():
    if "logged_in" in session and session.get("logged_in") == True:
        return redirect('/')
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username")
    password = request.form.get("password")

#Check that the username does not already exist
    if db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).rowcount > 0:
        return render_template("register.html", errorMessage="That username already exists. please try again.")

#Register the user by adding them to the database.
    db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                    {"username": username, "password": password})
    db.commit()

#render the success of their registration.
    return render_template('success.html', username=username, password=password, message="You have registered!")

@app.route("/login", methods=["GET", "POST"])
def login():
#Checking if user is already logged in or not.
    if session.get("logged_in") == True:
        return redirect('/')
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username")
    password = request.form.get("password")
#Check if user exists in the database.
    current_user = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()
# if the user does not exist in the database
    if current_user is None:
        return render_template("login.html", errorMessage="There is no such user." )
# check if the password is incorrect
    if current_user[2] != password:
        return render_template("login.html", errorMessage="Wrong password for this user.")

    session["user_id"] = current_user[0]
    session["USERNAME"] = current_user[1]
    session["logged_in"] = True
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    #forget all variables
    session.clear()
    #redirect them to the home Page
    return redirect(url_for("index"))

#Search for books
@app.route("/search", methods=["POST","GET"])
def search():
    #Standard check to see if user is logged in
    if "logged_in" not in session or session.get("logged_in") == False:
        return redirect('/login')

    if request.method == "GET":
        return render_template("search.html")
    elif request.method == "POST":
        user_input = request.form.get("booktitle")
        # adding the "wildcard" bits around the variable
        new_user_input = "%" + user_input + "%"
        new_user_input = new_user_input.title() #Capitalizing the first letters of each word
        #return all books that are like the input
        booklist = db.execute("SELECT isbn, title, author, year FROM books WHERE \
        title LIKE :user_input LIMIT 20",
         {"user_input": new_user_input})
         #no books found in search
        if booklist.rowcount == 0:
            return render_template("search.html", message="No books matched your search.")
        else:
            books = booklist.fetchall()
            return render_template("booklist.html", user_input=user_input, books=books)

@app.route("/book/<isbn>", methods=["GET", "POST"])
def book(isbn):
    users = db.execute("SELECT * FROM users").fetchall()
    book = db.execute("SELECT * from books WHERE isbn = :isbn", {"isbn": isbn }).fetchone()
    book_id = book["id"]
    reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id",
    {"book_id": book_id})
    #reviews = db.execute("SELECT * from reviews JOIN passengers ON reviews.id = flights.id WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
    if book is None:
        return render_template("error.html", errorMessage="That isbn does not exist.")

    if request.method == "POST":
        written_review = request.form.get("written_review")
        rating = int(request.form.get("rating"))
        user_id = session["user_id"]
        alreadywritten = db.execute("SELECT * FROM reviews WHERE user_id = :user_id",
        {"user_id": user_id})
        if alreadywritten.rowcount > 0:
            redirect(f"/book/{isbn}")

        db.execute("INSERT INTO reviews (book_id, user_id, rating, review) VALUES (:book_id, :user_id, :rating, :review)",
        {"book_id": book_id, "user_id": user_id, "rating": rating, "review": written_review})
        db.commit()
    """
    key = ZsSFeL3NzlS8icVo8ApD4Q
    info = requests.get("https://www.goodreads.com/book/review_counts.json",
                params={"key": key, "isbns": isbn})
    info = info.json()
    """
    return render_template("individualbook.html", book=book, reviews=reviews, users = users)
#returns a JSON object if anyone wants my data
@app.route("/api/<isbn>")
def api(isbn):
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn})
    book = book.fetchone()
    if book is None:
        return jsonify({"error": "invalid isbn"}), 422
    reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book["id"]})
    review_count = reviews.rowcount
    average_rating = 0
    for review in reviews.fetchall():
        average_rating += review["rating"]
    average_rating = average_rating / reviews.rowcount

    return jsonify({
    "title": book["title"],
    "author": book["author"],
    "year": book["year"],
    "isbn": book["isbn"],
    "review_count": review_count,
    "average_score": average_rating
    })
#Debug tool. Sessions was not working so this was the way of checking if the variables actually existed.
@app.route("/check")
def check():
    if "logged_in" in session:
        username = session["logged_in"]
        return "{{ username }}"
    else:
        return "it does not exist"
# The basic settings of the app.
if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    os.environ["DATABASE_URL"] = "postgres://shjixyayiodyzn:a0bbe886916e5285df43b7a8541b002a2b15a77f9c814b41983db58ddf072e28@ec2-3-222-150-253.compute-1.amazonaws.com:5432/dam4gjck8fv3mh"
    app.run(debug=True,host='127.0.0.1', port=5000)
