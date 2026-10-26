import io
import os
import re
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, connect

LIBRARY_DB = os.getenv("LIBRARY_DB_NAME", "library")
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
       b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe"
       b"\x02\xfe\xa7V\xbd\xfa\x00\x00\x00\x00IEND\xaeB`\x82")


def new_email():
    return f"test-{uuid.uuid4().hex[:10]}@test.com"


class Base(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def register(self, client=None, name="Sara", email=None, password="secret1"):
        client = client or self.client
        email = email or new_email()
        r = client.post("/register", data={"name": name, "email": email, "password": password,
                                           "confirm_password": password})
        return email, r

    def text(self, r):
        return r.get_data(as_text=True)


class AuthTests(Base):
    def test_private_list_redirects_to_login(self):
        r = self.client.get("/todos")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_register_empty_form_messages(self):
        page = self.text(self.client.post("/register", data={}))
        for msg in ["Name is required", "Email is required", "Password is required",
                    "Confirm password is required"]:
            self.assertIn(msg, page)

    def test_passwords_do_not_match(self):
        page = self.text(self.client.post("/register", data={
            "name": "A", "email": new_email(), "password": "a", "confirm_password": "b"}))
        self.assertIn("Passwords do not match", page)

    def test_register_logs_in_and_duplicate_email(self):
        email, r = self.register()
        self.assertEqual(r.status_code, 302)
        self.assertIn("/todos", r.headers["Location"])
        other = app.test_client()
        _, r2 = self.register(client=other, email=email)
        self.assertIn("Email Already Exists", self.text(r2))

    def test_password_is_bcrypt_hash(self):
        email, _ = self.register()
        conn = connect(os.getenv("DB_NAME", "registration"))
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM users WHERE email = %s", (email,))
            stored = cur.fetchone()["password_hash"]
        conn.close()
        self.assertTrue(stored.startswith("$2b$12$"))

    def test_same_login_error(self):
        email, _ = self.register(client=app.test_client())
        wrong_pw = self.text(self.client.post("/login", data={"email": email, "password": "nope"}))
        unknown = self.text(self.client.post("/login", data={"email": new_email(), "password": "x"}))
        injection = self.text(self.client.post("/login", data={"email": "' OR '1'='1' -- ",
                                                               "password": "x"}))
        for page in (wrong_pw, unknown, injection):
            self.assertIn("Invalid email or password", page)

    def test_email_must_be_a_real_address(self):
        for bad in ["www.com", "sara", "sara@", "@gmail.com", "sara@gmail", "sara gmail.com"]:
            page = self.text(self.client.post("/register", data={
                "name": "Sara", "email": bad, "password": "a", "confirm_password": "a"}))
            self.assertIn("Enter a valid email address", page, bad)
            page = self.text(self.client.post("/login", data={"email": bad, "password": "a"}))
            self.assertIn("Enter a valid email address", page, bad)

    def test_login_messages_and_logout(self):
        page = self.text(self.client.post("/login", data={}))
        self.assertIn("Email is required", page)
        self.assertIn("Password is required", page)
        email, _ = self.register(client=app.test_client())
        r = self.client.post("/login", data={"email": email, "password": "secret1"})
        self.assertEqual(r.status_code, 302)
        self.client.post("/logout")
        self.assertEqual(self.client.get("/todos").status_code, 302)


class TodoTests(Base):
    def ids(self, client):
        return [int(x) for x in re.findall(r'/todos/(\d+)/delete', self.text(client.get("/todos")))]

    def test_empty_state_and_add_edit_done_delete(self):
        self.register()
        self.assertIn("Your list is empty", self.text(self.client.get("/todos")))

        self.client.post("/todos/add", data={"title": "Buy oat milk"})
        self.client.post("/todos/add", data={"title": "Finish the lab", "due_date": "2030-01-01"})
        first, second = self.ids(self.client)[1], self.ids(self.client)[0]
        page = self.text(self.client.get("/todos"))
        self.assertLess(page.index("Finish the lab"), page.index("Buy oat milk"))

        self.client.post(f"/todos/{first}/edit", data={"title": "Buy almond milk", "due_date": ""})
        self.client.post(f"/todos/{second}/done", data={"is_done": "1"})
        page = self.text(self.client.get("/todos?show=done"))
        self.assertIn("Finish the lab", page)
        self.assertNotIn("almond", page)
        self.assertIn("1 open", self.text(self.client.get("/todos")))
        self.assertIn("almond", self.text(self.client.get("/todos?q=almond")))

        self.client.post(f"/todos/{first}/delete")
        self.assertEqual(self.ids(self.client), [second])

    def test_title_rules(self):
        self.register()
        page = self.text(self.client.post("/todos/add", data={"title": "   "}, follow_redirects=True))
        self.assertIn("Title is required", page)
        page = self.text(self.client.post("/todos/add", data={"title": "x" * 201},
                                          follow_redirects=True))
        self.assertIn("Title is too long (200 characters at most)", page)

    def test_users_cannot_touch_each_others_todos(self):
        sara = app.test_client()
        omar = app.test_client()
        self.register(client=sara, name="Sara")
        self.register(client=omar, name="Omar")
        sara.post("/todos/add", data={"title": "Sara's secret"})
        sara_id = self.ids(sara)[0]

        self.assertNotIn("Sara's secret", self.text(omar.get("/todos")))
        omar.post(f"/todos/{sara_id}/edit", data={"title": "hacked"})
        omar.post(f"/todos/{sara_id}/done", data={"is_done": "1"})
        omar.post(f"/todos/{sara_id}/delete")
        page = self.text(sara.get("/todos"))
        self.assertIn("Sara&#39;s secret", page)
        self.assertIn("1 open", page)


class LibraryTests(Base):
    def setUp(self):
        super().setUp()
        self.register()

    def lib(self, sql, params=()):
        conn = connect(LIBRARY_DB)
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        conn.close()
        return rows

    def test_library_requires_login(self):
        self.assertEqual(app.test_client().get("/library").status_code, 302)

    def test_tables_are_shown(self):
        page = self.text(self.client.get("/library"))
        self.assertIn("Books", page)
        self.assertIn("Authors", page)
        self.assertIn("Author ID", page)

    def test_author_and_book_crud_with_images_and_cascade(self):
        name = f"Test Author {uuid.uuid4().hex[:6]}"
        r = self.client.post("/authors/new", data={
            "name": name, "country": "Egypt",
            "photo": (io.BytesIO(PNG), "me.png")}, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 302)
        author = self.lib("SELECT author_id, photo FROM AUTHOR WHERE name = %s", (name,))[0]
        self.assertTrue(author["photo"].endswith(".png"))
        aid = author["author_id"]

        self.client.post(f"/authors/{aid}/edit", data={"name": name, "country": "Japan"},
                         content_type="multipart/form-data")
        self.assertEqual(self.lib("SELECT country FROM AUTHOR WHERE author_id = %s",
                                  (aid,))[0]["country"], "Japan")

        for title in ("Book A", "Book B"):
            self.client.post("/books/new", data={
                "title": title, "price": "10.50", "author_id": str(aid),
                "cover": (io.BytesIO(PNG), "c.png")}, content_type="multipart/form-data")
        books = self.lib("SELECT book_id, cover FROM BOOK WHERE author_id = %s ORDER BY book_id",
                         (aid,))
        self.assertEqual(len(books), 2)

        self.client.post(f"/books/{books[0]['book_id']}/edit", data={
            "title": "Book A2", "price": "11", "author_id": str(aid), "remove_cover": "1"},
            content_type="multipart/form-data")
        edited = self.lib("SELECT title, price, cover FROM BOOK WHERE book_id = %s",
                          (books[0]["book_id"],))[0]
        self.assertEqual((edited["title"], float(edited["price"]), edited["cover"]),
                         ("Book A2", 11.0, None))

        self.client.post(f"/books/{books[0]['book_id']}/delete")
        self.assertEqual(len(self.lib("SELECT book_id FROM BOOK WHERE author_id = %s", (aid,))), 1)

        self.client.post(f"/authors/{aid}/delete")
        self.assertEqual(self.lib("SELECT author_id FROM AUTHOR WHERE author_id = %s", (aid,)), ())
        self.assertEqual(self.lib("SELECT book_id FROM BOOK WHERE author_id = %s", (aid,)), ())

    def test_validation_messages(self):
        page = self.text(self.client.post("/authors/new", data={}))
        self.assertIn("Name is required", page)
        self.assertIn("Country is required", page)
        page = self.text(self.client.post("/books/new", data={"price": "abc", "author_id": "999999"}))
        self.assertIn("Title is required", page)
        self.assertIn("Price must be a number", page)
        self.assertIn("Choose an existing author", page)
        page = self.text(self.client.post("/authors/new", data={
            "name": "X", "country": "Y", "photo": (io.BytesIO(b"hello"), "virus.exe")},
            content_type="multipart/form-data"))
        self.assertIn("Image must be a PNG, JPG, GIF or WEBP file", page)

    def test_missing_rows_give_friendly_404(self):
        r = self.client.get("/books/99999999/edit")
        self.assertEqual(r.status_code, 404)
        self.assertIn("does not exist", self.text(r))


if __name__ == "__main__":
    unittest.main()
