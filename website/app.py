import os
import re
import uuid
from datetime import date
from functools import wraps

import bcrypt
import pymysql
from dotenv import load_dotenv
from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.exceptions import RequestEntityTooLarge

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_IMAGES = {"png", "jpg", "jpeg", "gif", "webp"}
TITLE_MAX = 200
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$")
EMAIL_INVALID = "Enter a valid email address (like name@gmail.com)"


def connect(database):
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=database,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        charset="utf8mb4",
    )


def get_db():
    if "db" not in g:
        g.db = connect(os.getenv("DB_NAME", "registration"))
    return g.db


def get_library_db():
    if "library_db" not in g:
        g.library_db = connect(os.getenv("LIBRARY_DB_NAME", "library"))
    return g.library_db


@app.teardown_appcontext
def close_db(_error):
    for name in ("db", "library_db"):
        conn = g.pop(name, None)
        if conn is not None:
            conn.close()


def query(conn, sql, params=(), one=False):
    with conn.cursor() as cur:
        count = cur.execute(sql, params)
        if cur.description is None:
            return count
        return cur.fetchone() if one else cur.fetchall()


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def check_title(title):
    if not title.strip():
        return "Title is required"
    if len(title.strip()) > TITLE_MAX:
        return "Title is too long (200 characters at most)"
    return None


def parse_due_date(text):
    text = text.strip()
    if not text:
        return None
    try:
        date.fromisoformat(text)
        return text
    except ValueError:
        return False


def log_in(user_id, name):
    session.clear()
    session["user_id"] = user_id
    session["name"] = name


def save_image(file, folder):
    if file is None or file.filename == "":
        return None, None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_IMAGES:
        return None, "Image must be a PNG, JPG, GIF or WEBP file"
    name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(os.path.join(UPLOAD_DIR, folder), exist_ok=True)
    file.save(os.path.join(UPLOAD_DIR, folder, name))
    return name, None


def delete_image(folder, name):
    if name:
        path = os.path.join(UPLOAD_DIR, folder, os.path.basename(name))
        if os.path.isfile(path):
            os.remove(path)


@app.route("/")
def index():
    return redirect(url_for("todos" if session.get("user_id") else "login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("todos"))
    form = {"name": "", "email": ""}
    errors = {}
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        form = {"name": name, "email": email}

        if not name:
            errors["name"] = "Name is required"
        if not email:
            errors["email"] = "Email is required"
        elif not EMAIL_PATTERN.match(email) or len(email) > 255:
            errors["email"] = EMAIL_INVALID
        if not password:
            errors["password"] = "Password is required"
        if not confirm:
            errors["confirm_password"] = "Confirm password is required"
        elif password and password != confirm:
            errors["confirm_password"] = "Passwords do not match"

        if not errors:
            password_hash = bcrypt.hashpw(password.encode("utf-8"),
                                          bcrypt.gensalt(rounds=12)).decode("utf-8")
            db = get_db()
            try:
                query(db, "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s)",
                      (email, name, password_hash))
            except pymysql.err.IntegrityError as e:
                if e.args[0] == 1062:
                    errors["email"] = "Email Already Exists"
                else:
                    raise
            else:
                user = query(db, "SELECT user_id, name, password_hash FROM users WHERE email = %s",
                             (email,), one=True)
                log_in(user["user_id"], user["name"])
                flash(f"Welcome, {name}! Your account was created.", "success")
                return redirect(url_for("todos"))
    return render_template("register.html", form=form, errors=errors)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("todos"))
    form = {"email": ""}
    errors = {}
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        form = {"email": email}

        if not email:
            errors["email"] = "Email is required"
        elif not EMAIL_PATTERN.match(email):
            errors["email"] = EMAIL_INVALID
        if not password:
            errors["password"] = "Password is required"

        if not errors:
            user = query(get_db(),
                         "SELECT user_id, name, password_hash FROM users WHERE email = %s",
                         (email,), one=True)
            if user and bcrypt.checkpw(password.encode("utf-8"),
                                       user["password_hash"].encode("utf-8")):
                log_in(user["user_id"], user["name"])
                return redirect(url_for("todos"))
            errors["form"] = "Invalid email or password"
    return render_template("login.html", form=form, errors=errors)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/todos")
@login_required
def todos():
    user_id = session["user_id"]
    show = request.args.get("show", "all")
    search = request.args.get("q", "").strip()

    sql = ("SELECT todo_id, title, is_done, created_at, due_date "
           "FROM todos WHERE user_id = %s")
    params = [user_id]
    if show == "open":
        sql += " AND is_done = 0"
    elif show == "done":
        sql += " AND is_done = 1"
    else:
        show = "all"
    if search:
        sql += " AND title LIKE %s"
        params.append("%" + search.replace("\\", "\\\\").replace("%", "\\%")
                      .replace("_", "\\_") + "%")
    sql += " ORDER BY todo_id DESC"

    db = get_db()
    items = query(db, sql, params)
    counts = query(db, "SELECT COUNT(*) AS total, COALESCE(SUM(is_done = 0), 0) AS open_count "
                       "FROM todos WHERE user_id = %s", (user_id,), one=True)
    return render_template("todos.html", items=items, show=show, search=search,
                           counts=counts, today=date.today(),
                           errors=session.pop("todo_errors", {}),
                           add_form=session.pop("todo_add_form", {}))


@app.route("/todos/add", methods=["POST"])
@login_required
def add_todo():
    title = request.form.get("title", "")
    due = parse_due_date(request.form.get("due_date", ""))
    errors = {}
    error = check_title(title)
    if error:
        errors["add_title"] = error
    if due is False:
        errors["add_due"] = "Due date is not a valid date"
    if errors:
        session["todo_errors"] = errors
        session["todo_add_form"] = {"title": title, "due_date": request.form.get("due_date", "")}
    else:
        query(get_db(), "INSERT INTO todos (user_id, title, due_date) VALUES (%s, %s, %s)",
              (session["user_id"], title.strip(), due))
        flash("To-do added.", "success")
    return redirect(url_for("todos"))


@app.route("/todos/<int:todo_id>/edit", methods=["POST"])
@login_required
def edit_todo(todo_id):
    title = request.form.get("title", "")
    due = parse_due_date(request.form.get("due_date", ""))
    error = check_title(title)
    if error is None and due is False:
        error = "Due date is not a valid date"
    if error:
        session["todo_errors"] = {f"edit_{todo_id}": error}
        return redirect(url_for("todos"))
    db = get_db()
    query(db, "UPDATE todos SET title = %s WHERE todo_id = %s AND user_id = %s",
          (title.strip(), todo_id, session["user_id"]))
    query(db, "UPDATE todos SET due_date = %s WHERE todo_id = %s AND user_id = %s",
          (due, todo_id, session["user_id"]))
    flash("To-do saved.", "success")
    return redirect(url_for("todos"))


@app.route("/todos/<int:todo_id>/done", methods=["POST"])
@login_required
def mark_todo(todo_id):
    is_done = 1 if request.form.get("is_done") == "1" else 0
    query(get_db(), "UPDATE todos SET is_done = %s WHERE todo_id = %s AND user_id = %s",
          (is_done, todo_id, session["user_id"]))
    return redirect(request.referrer or url_for("todos"))


@app.route("/todos/<int:todo_id>/delete", methods=["POST"])
@login_required
def delete_todo(todo_id):
    deleted = query(get_db(), "DELETE FROM todos WHERE todo_id = %s AND user_id = %s",
                    (todo_id, session["user_id"]))
    if deleted:
        flash("To-do deleted.", "success")
    return redirect(url_for("todos"))


def author_form_errors(name, country):
    errors = {}
    if not name:
        errors["name"] = "Name is required"
    elif len(name) > 100:
        errors["name"] = "Name is too long (100 characters at most)"
    if not country:
        errors["country"] = "Country is required"
    elif len(country) > 50:
        errors["country"] = "Country is too long (50 characters at most)"
    return errors


def book_form_errors(title, price, author_id, authors):
    errors = {}
    error = check_title(title)
    if error:
        errors["title"] = error
    if not price:
        errors["price"] = "Price is required"
    else:
        try:
            value = float(price)
            if value < 0 or value >= 100000000:
                errors["price"] = "Price must be between 0 and 99999999.99"
        except ValueError:
            errors["price"] = "Price must be a number"
    if not author_id:
        errors["author_id"] = "Author is required"
    elif not author_id.isdigit() or int(author_id) not in {a["author_id"] for a in authors}:
        errors["author_id"] = "Choose an existing author"
    return errors


def all_authors():
    return query(get_library_db(),
                 "SELECT author_id, name, country, photo FROM AUTHOR ORDER BY author_id")


@app.route("/library")
@login_required
def library():
    authors = all_authors()
    books = query(get_library_db(),
                  "SELECT book_id, title, price, author_id, cover FROM BOOK ORDER BY book_id")
    author_names = {a["author_id"]: a["name"] for a in authors}
    return render_template("library.html", authors=authors, books=books,
                           author_names=author_names)


@app.route("/authors/new", methods=["GET", "POST"])
@login_required
def new_author():
    form = {"name": "", "country": ""}
    errors = {}
    if request.method == "POST":
        form = {"name": request.form.get("name", "").strip(),
                "country": request.form.get("country", "").strip()}
        errors = author_form_errors(form["name"], form["country"])
        if not errors:
            photo, error = save_image(request.files.get("photo"), "authors")
            if error:
                errors["photo"] = error
            else:
                query(get_library_db(),
                      "INSERT INTO AUTHOR (name, country, photo) VALUES (%s, %s, %s)",
                      (form["name"], form["country"], photo))
                flash(f"Author \"{form['name']}\" added.", "success")
                return redirect(url_for("library"))
    return render_template("author_form.html", form=form, errors=errors, author=None)


@app.route("/authors/<int:author_id>/edit", methods=["GET", "POST"])
@login_required
def edit_author(author_id):
    db = get_library_db()
    author = query(db, "SELECT author_id, name, country, photo FROM AUTHOR WHERE author_id = %s",
                   (author_id,), one=True)
    if author is None:
        abort(404)
    form = {"name": author["name"], "country": author["country"]}
    errors = {}
    if request.method == "POST":
        form = {"name": request.form.get("name", "").strip(),
                "country": request.form.get("country", "").strip()}
        errors = author_form_errors(form["name"], form["country"])
        if not errors:
            photo, error = save_image(request.files.get("photo"), "authors")
            if error:
                errors["photo"] = error
            else:
                new_photo = author["photo"]
                if photo or request.form.get("remove_photo"):
                    delete_image("authors", author["photo"])
                    new_photo = photo
                query(db, "UPDATE AUTHOR SET name = %s, country = %s, photo = %s "
                          "WHERE author_id = %s",
                      (form["name"], form["country"], new_photo, author_id))
                flash("Author saved.", "success")
                return redirect(url_for("library"))
    return render_template("author_form.html", form=form, errors=errors, author=author)


@app.route("/authors/<int:author_id>/delete", methods=["POST"])
@login_required
def delete_author(author_id):
    db = get_library_db()
    author = query(db, "SELECT author_id, name, photo FROM AUTHOR WHERE author_id = %s",
                   (author_id,), one=True)
    if author is None:
        abort(404)
    covers = query(db, "SELECT cover FROM BOOK WHERE author_id = %s", (author_id,))
    count = query(db, "DELETE FROM AUTHOR WHERE author_id = %s", (author_id,))
    if count:
        delete_image("authors", author["photo"])
        for row in covers:
            delete_image("books", row["cover"])
        flash(f"Author \"{author['name']}\" and {len(covers)} book(s) removed.", "success")
    return redirect(url_for("library"))


@app.route("/books/new", methods=["GET", "POST"])
@login_required
def new_book():
    authors = all_authors()
    form = {"title": "", "price": "", "author_id": request.args.get("author_id", "")}
    errors = {}
    if request.method == "POST":
        form = {"title": request.form.get("title", "").strip(),
                "price": request.form.get("price", "").strip(),
                "author_id": request.form.get("author_id", "").strip()}
        errors = book_form_errors(form["title"], form["price"], form["author_id"], authors)
        if not errors:
            cover, error = save_image(request.files.get("cover"), "books")
            if error:
                errors["cover"] = error
            else:
                query(get_library_db(),
                      "INSERT INTO BOOK (title, price, author_id, cover) VALUES (%s, %s, %s, %s)",
                      (form["title"], form["price"], int(form["author_id"]), cover))
                flash(f"Book \"{form['title']}\" added.", "success")
                return redirect(url_for("library"))
    return render_template("book_form.html", form=form, errors=errors, authors=authors, book=None)


@app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@login_required
def edit_book(book_id):
    db = get_library_db()
    book = query(db, "SELECT book_id, title, price, author_id, cover FROM BOOK WHERE book_id = %s",
                 (book_id,), one=True)
    if book is None:
        abort(404)
    authors = all_authors()
    form = {"title": book["title"], "price": str(book["price"]),
            "author_id": str(book["author_id"])}
    errors = {}
    if request.method == "POST":
        form = {"title": request.form.get("title", "").strip(),
                "price": request.form.get("price", "").strip(),
                "author_id": request.form.get("author_id", "").strip()}
        errors = book_form_errors(form["title"], form["price"], form["author_id"], authors)
        if not errors:
            cover, error = save_image(request.files.get("cover"), "books")
            if error:
                errors["cover"] = error
            else:
                new_cover = book["cover"]
                if cover or request.form.get("remove_cover"):
                    delete_image("books", book["cover"])
                    new_cover = cover
                query(db, "UPDATE BOOK SET title = %s, price = %s, author_id = %s, cover = %s "
                          "WHERE book_id = %s",
                      (form["title"], form["price"], int(form["author_id"]), new_cover, book_id))
                flash("Book saved.", "success")
                return redirect(url_for("library"))
    return render_template("book_form.html", form=form, errors=errors, authors=authors, book=book)


@app.route("/books/<int:book_id>/delete", methods=["POST"])
@login_required
def delete_book(book_id):
    db = get_library_db()
    book = query(db, "SELECT book_id, title, cover FROM BOOK WHERE book_id = %s",
                 (book_id,), one=True)
    if book is None:
        abort(404)
    if query(db, "DELETE FROM BOOK WHERE book_id = %s", (book_id,)):
        delete_image("books", book["cover"])
        flash(f"Book \"{book['title']}\" removed.", "success")
    return redirect(url_for("library"))


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404,
                           message="The page you are looking for does not exist."), 404


@app.errorhandler(RequestEntityTooLarge)
def too_large(_e):
    return render_template("error.html", code=413,
                           message="The image is too big (2 MB at most)."), 413


@app.errorhandler(500)
def server_error(_e):
    return render_template("error.html", code=500,
                           message="Something went wrong on our side. Please try again."), 500


@app.errorhandler(pymysql.err.OperationalError)
def db_down(_e):
    return render_template("error.html", code=503,
                           message="The database is not reachable. Check that MySQL is "
                                   "running and that the values in .env are right."), 503


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1",
            port=int(os.getenv("PORT", "5000")))
