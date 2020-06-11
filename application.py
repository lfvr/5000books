import os
import requests

from flask import flash, Flask, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from functools import wraps
from helpers import login_required
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

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


@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        search = request.form.get("search")
        results = db.execute("SELECT * FROM books WHERE LOWER(isbn) LIKE LOWER(:search) OR LOWER(title) LIKE LOWER(:search) OR LOWER(author) LIKE LOWER(:search)", {"search": f'%{search}%'}).fetchall()
        db.commit()

        # Render search results template with results list passed to display
        return render_template("results.html", results=results)

    # User reached via GET or other method
    else:
        return render_template("index.html")

@app.route("/api/<isbn>")
def api(isbn):
    # Check book exists
    book = db.execute("SELECT * FROM books WHERE LOWER(isbn) = LOWER(:isbn)", {"isbn": isbn}).fetchone()
    db.commit()
    if book == None:
        return jsonify({"error": "Invalid ISBN"}), 404

    # Get review info
    reviews = db.execute("SELECT * FROM reviews WHERE LOWER(isbn) = LOWER(:isbn)", {"isbn": isbn}).fetchall()
    total_reviews = 0
    review_sum = 0
    for review in reviews:
        total_reviews += 1
        review_sum += review["rating"]
    average = review_sum / total_reviews

    # Return JSON
    return jsonify({
        "title": book["title"],
        "author": book["author"],
        "year": book["year"],
        "isbn": book["isbn"],
        "review_count": total_reviews,
        "average_score": average
    })

@app.route("/book_details/<isbn>")
@login_required
def book_details(isbn): 

    # Get book details and reviews for selected title
    info = db.execute("SELECT * FROM books WHERE LOWER(isbn) = LOWER(:isbn)", {"isbn": isbn}).fetchone()
    reviews = db.execute("SELECT * FROM reviews WHERE LOWER(isbn) = LOWER(:isbn)", {"isbn": isbn}).fetchall()
    db.commit()

    # Get details from Goodreads api
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "uSDXou73Om4UkYnVARA", "isbns": info["isbn"]})
    if res.status_code != 200:
        raise Exception("ERROR: API request unsuccessful.")
    data = res.json()
    rating = data["books"][0]["average_rating"]
    total = data["books"][0]["work_ratings_count"]

    # Get details from Google Books api
    # returning goodreads
    google_res = requests.get("https://www.googleapis.com/books/v1/volumes", params={"q": f"inauthor:{info['author']}+intitle:{info['title']}", "key": "AIzaSyC_ts2uAu72rCYoiUgzsgAV8U8LKGNKyPY"})
    google_data = google_res.json()
    img = google_data["items"][0]["volumeInfo"]["imageLinks"]["thumbnail"].replace('"', '')
    synopsis = google_data["items"][0]["volumeInfo"]["description"]
    return render_template("book_details.html", info=info, reviews=reviews, rating=rating, total=total, img=img, synopsis=synopsis)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Query database for username
        check = db.execute("SELECT * FROM users WHERE name = :username", {"username": request.form.get("username")}).fetchone()

        # Ensure username exists and password is correct
        if not check or not check_password_hash(check[2], request.form.get("password")):
            flash("Invalid username and/or password", "error")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = check["id"]

        # Redirect user to home page
        flash("Successfully logged in!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check password fields match
        if request.form.get("password") != request.form.get("confirmation"):
            flash("Passwords must match", "error")
            return render_template("register.html")
        
        # check for existing user
        username = request.form.get("username")
        users = db.execute("SELECT * FROM users")
        for user in users:
            if user["name"] == username:
                flash("Username already taken", "error")
                return render_template("register.html")

        # hash password and add user to database
        hashed = generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users (name, password) VALUES (:user, :hashed)", {"user": username, "hashed": hashed})
        db.commit()
        # log in user who has just registered
        session["user_id"] = db.execute("SELECT * FROM users WHERE name = :name", {"name": username}).fetchone()[0]

        # redirect to homepage
        flash("Registered!")
        return redirect("/")
        
    # any method other than POST
    else:
        return render_template("register.html")

@app.route("/submit_review/<isbn>", methods=["POST"])
@login_required
def submit_review(isbn):

    # Check whether user has previously submitted review
    check = db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND isbn = :isbn", {"user_id": session["user_id"], "isbn": isbn}).fetchone()
    db.commit()
    if check != None:
        flash("You've already reviewed this book!", "error")
        return redirect(url_for('book_details', isbn = isbn))

    if "submit" in request.form:
        # Get review text and rating from submission
        text = request.form["review-text"]
        rating = request.form["review-rating"]

        # Update reviews database
        db.execute("INSERT INTO reviews (isbn, rating, text, user_id) VALUES (:isbn, :rating, :text, :user_id)", {"isbn": isbn, "rating": rating, "text": text, "user_id": session.get("user_id")})
        db.commit()

        # Confirm review submitted
        flash("Thanks for the review!")
        return redirect(url_for('book_details', isbn = isbn))
