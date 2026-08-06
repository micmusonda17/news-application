# News Application - Capstone Project

This is my capstone project for the software engineering course. It is a
news website built with Django where journalists write articles, editors
approve them, and readers subscribe to publishers and journalists to get
the articles by email.

The project also has a RESTful API so that another program can get the
articles, and it has unit tests for that API.

## What the application does

* Three roles: **Reader**, **Editor** and **Journalist**. Every user is
  put into the group with the same name and the group has the
  permissions for that role.
* Journalists write articles and newsletters.
* Editors approve the articles before anybody can read them.
* When an editor approves an article a **Django signal** does two things:
  1. it emails the article to everybody subscribed to the journalist or
     to the publisher, and
  2. it sends a POST request to my own API endpoint `/api/approved/`
     using the `requests` module (this is how the article is "shared"
     outside the site).
* Readers subscribe to publishers and journalists and can see a feed
  with only their subscribed articles.
* A REST API with token authentication.

My plan for the project (the functional and non-functional requirements
and how I normalised the database) is in **DESIGN.md**.

## The files in the project

| File | What it is for |
| --- | --- |
| `news/models.py` | The CustomUser, Publisher, Article and Newsletter models |
| `news/views.py` | The views for the normal website pages |
| `news/urls.py` | The urls for the website |
| `news/forms.py` | The forms (register, article, newsletter, subscriptions) |
| `news/signals.py` | Creates the groups, and the email + POST when an article is approved |
| `news/serializers.py` | The DRF serializers for the API |
| `news/api_views.py` | The views for the API |
| `news/api_urls.py` | The urls for the API |
| `news/permissions.py` | My own permission classes (only editors can approve etc.) |
| `news/tests.py` | All my unit tests |
| `news/templates/news/` | The HTML templates |
| `news/static/news/style.css` | The CSS |

## How to run the project

### 1. Make a virtual environment and install everything

```bash
python3 -m venv venv
source venv/bin/activate      # on windows: venv\Scripts\activate
pip install -r requirements.txt
```

On a Mac the command is `python3`, not `python`. Once the virtual
environment is switched on you can use `python` again.

I use **PyMySQL** to talk to MariaDB instead of `mysqlclient`, because
`mysqlclient` has to be compiled and it needs extra tools installed
first. PyMySQL is pure python so it just installs. The little bit of
code that makes django accept PyMySQL is in `news_project/__init__.py`.

### 2. Set up MariaDB

The task said the database must be MariaDB. If you do not have it on a
Mac you can install it with homebrew:

```bash
brew install mariadb
brew services start mariadb
```

Then log in to MariaDB (`sudo mariadb` or `mariadb -u root`) and run:

```sql
CREATE DATABASE news_application CHARACTER SET utf8mb4;
CREATE USER 'news_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON news_application.* TO 'news_user'@'localhost';
FLUSH PRIVILEGES;
```

Then tell django to use MariaDB instead of sqlite by setting these
environment variables before you run the server:

```bash
export USE_SQLITE=False
export DB_NAME=news_application
export DB_USER=news_user
export DB_PASSWORD=your_password
export DB_HOST=127.0.0.1
export DB_PORT=3306
```

(On Windows use `set` instead of `export`.)

If you do not set `USE_SQLITE=False` the project uses sqlite. I did that
so that the unit tests can also run on a computer that does not have
MariaDB installed.

### 3. Make the tables and a superuser

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

The three groups (Reader, Editor, Journalist) and their permissions are
created automatically by a `post_migrate` signal, so you do not have to
make them by hand.

### 4. (Optional) Add some demo data

```bash
python manage.py create_demo_data
```

This makes a publisher and three users: `journalist1`, `editor1` and
`reader1`. The password for all of them is `Password123!`.

### 5. Run the server

```bash
python manage.py runserver
```

Then open http://127.0.0.1:8000/ in a browser.

The emails are printed in the terminal because I use the console email
backend while I am testing. To send real emails, set the environment
variable `EMAIL_BACKEND` to
`django.core.mail.backends.smtp.EmailBackend` and fill in
`EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`.

## The API

First get a token:

```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
     -d "username=reader1&password=Password123!"
```

Then put the token in the header of every request:

```bash
curl http://127.0.0.1:8000/api/articles/ \
     -H "Authorization: Token YOUR_TOKEN_HERE"
```

| Method | Endpoint | Who may use it |
| --- | --- | --- |
| POST | `/api/token/` | anybody with an account |
| GET | `/api/articles/` | any logged in user (only approved articles) |
| POST | `/api/articles/` | journalists only |
| GET | `/api/articles/subscribed/` | readers only (their subscriptions) |
| GET | `/api/articles/<id>/` | any logged in user |
| PUT | `/api/articles/<id>/` | editors, or the journalist who wrote it |
| DELETE | `/api/articles/<id>/` | editors, or the journalist who wrote it |
| POST | `/api/articles/<id>/approve/` | editors only |
| GET/POST | `/api/newsletters/` | everybody can read, journalists can create |
| GET/PUT/DELETE | `/api/newsletters/<id>/` | editors, or the author |
| GET | `/api/publishers/` | any logged in user |
| GET | `/api/me/` | the logged in user |
| GET/POST | `/api/approved/` | this is where my signal posts approved articles |

## The tests

Run all the unit tests with:

```bash
python manage.py test
```

There are 48 tests and they check:

* the users land in the correct group and the groups have the correct
  permissions,
* readers get `None` for the journalist fields and the other way around,
* the signal sends the email and the POST request (I use `mock` so no
  real request goes out),
* the email is not sent twice if the article is saved again,
* logging in with a token works and a wrong password fails,
* a reader only gets the articles of the publishers/journalists they are
  subscribed to,
* a journalist can create articles but a reader can not,
* an editor can approve and delete but a journalist can not approve,
* the newsletters work,
* requests that must fail really do fail (403, 400, 401 and 404).

## Roles and permissions

| Role | Group permissions on articles and newsletters |
| --- | --- |
| Reader | view |
| Editor | view, change, delete |
| Journalist | add, view, change, delete |
