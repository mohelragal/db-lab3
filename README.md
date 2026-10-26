# DB Lab 2 + Lab 3: Login & To-Do + Library (Books and Authors)

A small website with a MySQL database behind it:

* **Lab 2**: sign-up, login, logout and a private to-do list for every user.
* **Lab 3 – Problem 2**: a library with two tables, `AUTHOR` and `BOOK`: show, add, edit and remove books and authors.
* **Bonus**: due dates, filters and search, an open-to-do counter, dark mode, automated tests (Lab 2), and image upload for book covers and author photos (Lab 3).

---

## 1. Team
Mohamed hassan elragal 2304246
Mohamed Ashraf kamel 2304059

## 2. Technology

| Part | Technology |
|------|------------|
| Back end | Python 3 + Flask (plain SQL through PyMySQL, every value sent as a `%s` parameter, no ORM) |
| Front end | HTML (Jinja templates) + my own CSS + plain JavaScript |
| Database | MySQL 8 (databases `registration` and `library`) |
| Passwords | bcrypt (cost 12) |
| Tools | MySQL Workbench (run the SQL scripts), Visual Studio Code (code + terminal) |

## 3. Files

```
lab3-<student-id>/
  problem2_DDL.sql          # Lab 3 Problem 2: CREATE the library database (AUTHOR, BOOK)
  problem2_DML.sql          # Lab 3 Problem 2: seed data, 4 authors and 8 books
  README.md                 # this file
  .gitignore                # .env, uploaded images, __pycache__
  screenshots/              # screenshots of the site
  website/                  # the Lab 2 website with the new Lab 3 pages
    app.py                  # the whole server (routes + SQL)
    requirements.txt
    .env.example            # fake values only; copy to .env
    database/schema.sql     # Lab 2 DDL: users + todos (re-runnable, no data)
    templates/              # HTML pages
    static/style.css        # one style for every page (light + dark)
    static/app.js           # browser checks, "are you sure?", dark mode, image preview
    static/uploads/         # uploaded covers and photos (bonus)
    tests/test_app.py       # automated tests (bonus)
```

## 4. How to run it (from an empty machine)

You need **MySQL Server + MySQL Workbench**, **Python 3.10+** and **Visual Studio Code**.

### Step 1: build the databases in MySQL Workbench

1. Open MySQL Workbench and connect to your local MySQL server (e.g. `Local instance`, user `root`).
2. **File → Open SQL Script…** → choose `website/database/schema.sql` → press **Execute** (the lightning icon ⚡).
3. Do the same for `problem2_DDL.sql`, then `problem2_DML.sql` (in this order).
4. Click the refresh icon in the **Schemas** panel: you should see `registration` (tables `users`, `todos`) and `library` (tables `author`, `book`).

> Same thing from a terminal, if you prefer the MySQL client:
> `mysql -u root -p < website/database/schema.sql`, then `mysql -u root -p < problem2_DDL.sql`, then `mysql -u root -p < problem2_DML.sql`.

All three scripts can be run again at any time: the DDL scripts start with `DROP DATABASE IF EXISTS …`.

### Step 2: start the website in Visual Studio Code

1. **File → Open Folder…** → choose this project folder.
2. **Terminal → New Terminal**, then:

```bash
cd website
python -m pip install -r requirements.txt
copy .env.example .env
```

(on macOS / Linux use `cp .env.example .env`)

3. Open `website/.env` in VS Code and set `DB_PASSWORD` to your MySQL root password (and `DB_USER` if it is not `root`). Put any long random text in `SECRET_KEY`.
4. Start the server:

```bash
python app.py
```

5. Open **http://localhost:5000** in a browser. Register an account, then use **My list** and **Library** in the top bar.

### Step 3 (optional): run the automated tests

With the databases built and `.env` filled in:

```bash
python -m unittest discover -s tests -v
```

15 tests check registration, login, the exact error messages, privacy between two users, the to-do actions, the library pages, image upload and the cascade delete.

## 5. Features

### Lab 2: Login & To-Do

| # | Requirement | Done |
|---|-------------|------|
| R1 | Register with name, e-mail, password, confirm password; duplicate e-mail → **Email Already Exists**; after sign-up the user is logged in and sees the list | ✅ |
| R2 | Login; wrong e-mail and wrong password both show **Invalid email or password**; Logout ends the session | ✅ |
| R3 | The list is private: not logged in → redirected to the login page; each user sees only their own to-dos, newest first | ✅ |
| R4–R7 | Add, edit the title, mark done / not done, delete (with an "are you sure?" dialog) | ✅ |
| R8 | The same checks in the browser (JavaScript) and on the server, with the exact messages; on an error the server shows the page again and does not touch the database | ✅ |
| R9 | bcrypt hashes; only parameterised queries; `user_id` always taken from the session | ✅ |
| R10 | One consistent style, works at 360 px wide, error messages next to the fields, done to-dos are crossed out, friendly empty list, name + logout button, styled error pages (404 / 413 / 500 / database down) | ✅ |

### Lab 3 – Problem 2: Library

| # | Page | Done |
|---|------|------|
| F2.1 | **Library** page: a table of the books (with the `author_id` of each book) and a table of the authors | ✅ |
| F2.2 | **+ Add book** and **+ Add author** | ✅ |
| F2.3 | **Edit** a book / an author | ✅ |
| F2.4 | **Remove** a book (asks first) | ✅ |
| F2.5 | **Remove** an author (asks first; the author's books go too, `ON DELETE CASCADE`) | ✅ |

The book form chooses the author from a list of the existing authors, so a book can only point at a real author (and the server checks it again). No JOIN is used: the author's name next to the `author_id` comes from the authors list that is already loaded for the page.

### Bonus

* **Lab 3 – images**: upload a **cover** for each book and a **photo** for each author (PNG / JPG / GIF / WEBP, 2 MB max), with a preview before upload, replace or remove on the edit page. Files are saved in `website/static/uploads/` under a random name; the database stores only the file name (`BOOK.cover`, `AUTHOR.photo`). Removing a book or an author also removes its image files.
* **Lab 2 – due date**: a new column `todos.due_date DATE NULL`; overdue to-dos are shown in red.
* **Lab 2 – filters and search**: All / Open / Done tabs and a search box.
* **Lab 2 – counter**: "N open · M total" on the list.
* **Lab 2 – dark mode**: follows the system setting; the ◐ button switches it and remembers the choice.
* **Lab 2 – automated tests**: `website/tests/test_app.py`.

## 6. The SQL

### Lab 2 (given queries; `%s` is the placeholder in PyMySQL)

```sql
INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s);
SELECT user_id, name, password_hash FROM users WHERE email = %s;
SELECT todo_id, title, is_done, created_at FROM todos WHERE user_id = %s ORDER BY todo_id DESC;
INSERT INTO todos (user_id, title) VALUES (%s, %s);
UPDATE todos SET title = %s WHERE todo_id = %s AND user_id = %s;
UPDATE todos SET is_done = %s WHERE todo_id = %s AND user_id = %s;
DELETE FROM todos WHERE todo_id = %s AND user_id = %s;
```

Bonus additions: the list query also selects `due_date` and may add `AND is_done = 0/1` and `AND title LIKE %s`; adding a to-do also inserts `due_date`; `UPDATE todos SET due_date = %s WHERE todo_id = %s AND user_id = %s`; and `SELECT COUNT(*) …, SUM(is_done = 0) … FROM todos WHERE user_id = %s` for the counter.

### Lab 3 (simple SELECT / INSERT / UPDATE / DELETE only)

```sql
SELECT author_id, name, country, photo FROM AUTHOR ORDER BY author_id;
SELECT book_id, title, price, author_id, cover FROM BOOK ORDER BY book_id;
INSERT INTO AUTHOR (name, country, photo) VALUES (%s, %s, %s);
INSERT INTO BOOK (title, price, author_id, cover) VALUES (%s, %s, %s, %s);
UPDATE AUTHOR SET name = %s, country = %s, photo = %s WHERE author_id = %s;
UPDATE BOOK SET title = %s, price = %s, author_id = %s, cover = %s WHERE book_id = %s;
DELETE FROM BOOK WHERE book_id = %s;
DELETE FROM AUTHOR WHERE author_id = %s;   -- its books are deleted by ON DELETE CASCADE
```

## 7. Screenshots

Put them in `screenshots/` and they show up here:

| Register page with error messages | Login page |
|---|---|
| ![register](screenshots/register-errors.png) | ![login](screenshots/login.png) |
| **To-do list (one done)** | **Phone-sized window** |
| ![list](screenshots/todo-list.png) | ![phone](screenshots/phone.png) |
| **Library: books and authors** | **Add a book with a cover** |
| ![library](screenshots/library.png) | ![add book](screenshots/add-book.png) |

## 8. Answers (Lab 2)

**(a) Why do `UPDATE` and `DELETE` contain `AND user_id = ?`, and what changes if you remove it?**
The `todo_id` comes from the browser, so anybody can change it in the address or the request and send the number of somebody else's to-do. With `AND user_id = ?` (the id of the logged-in user, taken from the session), the statement only matches a row that is both that to-do **and** owned by that user; for somebody else's to-do it changes zero rows. Without it, any logged-in user could edit, mark or delete every user's to-dos just by guessing numbers.

**(b) What happens if you insert a to-do for a `user_id` that does not exist, and which constraint is that?**
MySQL rejects the insert with error **1452**: *Cannot add or update a child row: a foreign key constraint fails (`registration`.`todos`, CONSTRAINT `todos_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`))*. This is the **referential integrity constraint** (the foreign key): a foreign key value must be equal to an existing primary key value of the referenced table (`user_id` is also `NOT NULL`, so it can't be NULL either).

**(c) Why do you store a hash and not the password?**
If the database is ever leaked or read by someone who should not see it, the real passwords are not there; people often reuse passwords on other sites. bcrypt is one-way (it can't be turned back into the password), it is salted (two equal passwords give different hashes, so precomputed tables do not work) and slow on purpose (guessing millions of passwords takes very long). To log in, the library hashes the typed password with the stored salt and compares.

**(d) The `name` column is `NOT NULL`: why did you still need your own check for an empty name?**
`NOT NULL` only refuses a missing value (`NULL`). An empty text `''` (or only spaces) is a real value, so MySQL accepts it. The form always sends the field, even when it is empty, so only our own checks (in the browser and on the server, after `strip()`) can refuse an empty name with the message **Name is required**.

## 9. Check yourself (all tested)

| Try this | Result |
|---|---|
| Open `/todos` without logging in | sent to the login page |
| Press **Register** on an empty form | one message per empty field, before anything is sent; with JavaScript off the same messages come from the server |
| Register the same e-mail twice | **Email Already Exists** |
| Wrong password / unknown e-mail | the same **Invalid email or password** |
| `' OR '1'='1' --` as the login e-mail | not logged in |
| Two users in two browsers | each sees only their own to-dos; posting the other's to-do number changes nothing |
| `SELECT password_hash FROM users;` | only values like `$2b$12$...` |
| Remove an author | the author and all of their books disappear |
