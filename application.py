import os


from flask import Flask, session,redirect, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
import requests
from helpers import login_required
res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "yDUp1iRko1aeLCJKiTx40A", "isbns": "9781632168146"})


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


@app.route("/", methods = ["GET","POST"])
@login_required
def index():
    p =''
    if request.method=="POST":
        if not request.form.get("search"):
            print("test")
            p ="Please enter a search term"
            return render_template("index.html",p=p)
    searches = 0
    print("searches",searches)
    input = str(request.form.get("search"))
    print("input",input)
    # credit https://stackoverflow.com/questions/19859282/check-if-a-string-contains-a-number
    def hasNumbers(inputString):
        return any(char.isdigit() for char in inputString)
        # functions for searching database
    def isbnSearch(search):
            return db.execute("SELECT * FROM books WHERE isbn LIKE :search ORDER BY isbn",{"search":search}).fetchall()
    def titleSearch(search):
            return db.execute("SELECT * FROM books WHERE title LIKE :search ORDER BY title",{"search":search}).fetchall()
    def authorSearch(search):
            return db.execute("SELECT * FROM books WHERE author LIKE :search ORDER BY author",{"search":search}).fetchall()
    result1=hasNumbers(input)
    # concaconates % for like search
    search = '%'+ input +'%'
    capssearch ='%'+ input.capitalize() +'%'
    capsallsearch ='%'+input.title()+'%'
    isbn = []
    alist = []
    author = []
    author1 = []
    author2 = []
    a =''
    t =''
    i =''
    # if contains numbers
    if result1 == True:
        isbn = isbnSearch(search)
        print(isbn)
        # title may contain a number
        # searches as user inputted, with first words caps and all words caps
        title = titleSearch(search)
        title1 = titleSearch(capssearch)
        title2 = titleSearch(capsallsearch)
        searches = 1
    else:
        # if does not contain number will be searching by author and title
        title = titleSearch(search)
        title1 = titleSearch(capssearch)
        title2 = titleSearch(capsallsearch)
        author = authorSearch(search)
        author1 = authorSearch(capssearch)
        author2 = authorSearch(capsallsearch)
        searches = 1
    # adds lists
    tlist = title + title1 + title2
    alist = author + author1 + author2
    # collates all results into a list to avoid duplication
    titlelist = []
    authorlist = []
    for x in tlist:
        if x not in titlelist:
            titlelist.append(x)
    for y in alist:
        if y not in authorlist:
            authorlist.append(y)
    print("TITLES",titlelist)
    print("AUTHORS",authorlist)
    print("searches2",searches)
    # only displayes results if there has been a search
    if input == "None":
        searches = 0
    print("searches3",searches)
    if(searches) == 1:
        if(len(isbn)) == 0:
            i ="No ISBNs under that term"
        else:
            i = "ISBNs"
        if(len(titlelist)) == 0:
            t = "No titles under that term"
        else:
            t = "Titles"
        if(len(authorlist)) == 0:
            a = "No authors under that term"
        else:
            a = "Authors"
    s = ''
    return render_template("index.html",s=s,i=i,p=p,a=a,t=t,isbn= isbn,titlelist = titlelist,authorlist=authorlist)

@app.route("/books/<int:book_id>", methods =["GET","POST"])
@login_required
def books(book_id):
    book = db.execute("SELECT * FROM books WHERE book_id=:id",{"id":book_id}).fetchone()
    average = db.execute("SELECT AVG(rating) FROM reviews WHERE book_id=:id",{"id":book_id}).fetchone()
    reviews = db.execute("SELECT * FROM reviews WHERE book_id=:book_id",{"book_id":book_id}).fetchall()
    average = average[0]
    if average != None:
        average = round(average,2)
    isbn = book["isbn"]
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "yDUp1iRko1aeLCJKiTx40A", "isbns": isbn})
    if res.status_code != 200:
        raise Exception("Error: API request unsuccessful.")
    data = res.json()
    grating = data["books"][0]["average_rating"]
    print(grating)
    count = data["books"][0]["work_ratings_count"]
    if book is None:
        error = "Error: Book does not exist"
        return render_template("error.html", error=error)
    if request.method=="POST":
        if not request.form.get("review"):
            error = "Error: Please enter a review"
            return render_template("error.html",error=error)
        if not request.form.get("inlineRadioOptions"):
            error = "Error: Please enter a 1-5 rating"
            return render_template("error.html",error=error)
        review = request.form.get("review")
        rating = request.form.get("inlineRadioOptions")
        user = session["user_id"]
        reviewed = db.execute("SELECT * FROM reviews WHERE user_id=:user_id AND book_id=:book_id",{"user_id":user,"book_id":book_id}).fetchone()
        if reviewed:
            error = "Error : You have already reviewed this book"
            return render_template("error.html",error=error)
        else:
            db.execute("INSERT INTO reviews(book_id,user_id,rating,review)VALUES(:book_id,:user_id,:rating,:review)"
            ,{"book_id":book_id,"user_id":user,"rating":rating,"review":review})
            db.commit()


    return render_template("books.html",book=book,reviews=reviews,average=average,grating=grating,count=count)

@app.route("/register", methods =["GET","POST"])
def register():
    if request.method =="POST":
        if not request.form.get("username"):
            error = "Error : Please enter a username"
            return render_template("error.html",error=error)
        if not request.form.get("password"):
            error = "Error : Plase enter a password"
            return render_template("error.html",error=error)
        if not request.form.get("confirmation"):
            error = "Error : Please retype password"
            return render_template("error.html",error=error)

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if password != confirmation:
            error = "Error : Passwords do not match"
            return render_template("error.html",error=error)
        passwordhash = generate_password_hash("password")

        rows = db.execute("SELECT * FROM users WHERE username=:username",{"username":username}).fetchone()
        if rows:
            error = "Error : Username is taken"
            return render_template("error.html",error=error)
        inserted = db.execute("INSERT INTO users(username,password)VALUES(:username,:password)",{"username":username,"password":passwordhash})
        db.commit()
        lastinsert = db.execute("SELECT * FROM users WHERE username=:username",{"username":username}).fetchone()
        if lastinsert:
            error ="Success you are registered"
            session['user_id']=lastinsert
            s = "Registration Sucesssful"
            return render_template("index.html", s=s)
        else:
            error = "Failure to register"
            return render_template("error.html", error=error)

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not request.form.get("username"):
            error ="Error: Please enter a username"
            return render_template("error.html", error=error)
        if not request.form.get("password"):
            error = "Error: Please enter a password"
            return render_template("error.html", error=error)

        username=request.form.get("username")
        password=request.form.get("password")

        user = db.execute("SELECT * FROM users WHERE username = :username",{"username":username}).fetchone()
        print(user)
        if not user:
            error = "Error : Username not recognised"
            return render_template("error.html", error = error)
# after lunch tidy this all up ad label maybe have a play and condense it.
            hash = check_password_hash(user["password"],password)
            print("h",hash)
            if hash == False:
                error = "Error : Incorrect Password"
                return render_template("error.html", error=error)
        else:
            session["user_id"]=user["user_id"]
            return redirect("/")
    else:
        return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/")
