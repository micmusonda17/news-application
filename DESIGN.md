# Design of my news application

Before I started coding I wrote down what the program needs to do and how
I was going to build the database. This file is my plan.

## Functional requirements

These are the things the program must do:

1. A person can register and pick a role: reader, editor or journalist.
2. A person can log in and log out.
3. Each user goes into the group for their role, and the group has the
   permissions for that role.
4. A journalist can create, view, update and delete articles and
   newsletters.
5. An editor can view, update and delete articles and newsletters.
6. An editor approves an article before readers can see it.
7. When an article is approved the subscribers get it by email.
8. When an article is approved it is also sent to my own API endpoint
   `/api/approved/` with a POST request.
9. A reader can subscribe to publishers and to journalists.
10. A reader can see a feed with only the articles they subscribed to.
11. The API lets another program log in with a token and then get,
    create, update or delete articles depending on their role.

## Non-functional requirements

These are not things the program does, they are rules about the whole
system:

1. **Security** – django hashes the passwords, the API needs a token,
   and each page checks the role first. The database password is in an
   environment variable, not in my code.
2. **Usability** – the menu only shows the links that the user is
   allowed to use.
3. **Readability** – the code follows PEP 8 and every function has a
   docstring. I split the code into different files instead of one big
   file.
4. **Reliability** – if the email or the API does not work the website
   must not crash.
5. **Testability** – the unit tests must run without a real email
   server, so I use mocking.

## The database

| Table | What it stores |
| --- | --- |
| CustomUser | username, email, password, role |
| Publisher | name, description, email |
| Article | title, content, created_at, approved, author, publisher |
| Newsletter | title, description, created_at, author, publisher |
| ApprovedArticleLog | the articles my `/api/approved/` endpoint saved |

How they are joined:

* One journalist can write many articles and many newsletters.
* One publisher can have many articles and many newsletters.
* A newsletter can hold many articles, and an article can be in many
  newsletters (many to many).
* A reader can subscribe to many publishers and many journalists (many
  to many).

## Why the tables are normalised

**1NF** – every column only holds one value. I do not put a list of
subscriptions in one field. The subscriptions get their own table where
each row is one reader and one publisher.

**2NF** – the tables are in 1NF and there are no columns that only
belong to part of the key. The many to many tables only have the two
foreign keys in them.

**3NF** – I do not repeat information that already lives in another
table. The article only saves the id of the author and the id of the
publisher. If I also saved the publisher name in the article table then
I would have to change it in two places when the publisher changes its
name.

The only place I repeat data on purpose is `ApprovedArticleLog`, because
it is a log. It must keep the title and the author from the moment the
article was approved, even if the article is changed later.

## Roles and permissions

| Role | Can do this with articles and newsletters |
| --- | --- |
| Reader | view |
| Editor | view, update, delete |
| Journalist | create, view, update, delete |

The task said a journalist must have `None` for the reader fields and a
reader must have `None` for the journalist fields. A ManyToManyField
can not really be `None`, so I clear it in `save()` and I made the
methods `get_reader_fields()` and `get_journalist_fields()` that return
`None` when the role is wrong.

## The pages I planned

| Page | Who can see it |
| --- | --- |
| Home | everybody |
| Article detail | logged in users |
| Write / edit article | journalists and editors |
| My articles | journalists |
| Editor dashboard | editors |
| Newsletters | everybody |
| My feed | readers |
| Subscriptions | readers |
| Publishers | everybody |
| Register / log in | everybody |

Every template extends `base.html` so I do not have to write the menu
again on every page.

## Things I would add next time

* Pagination on the home page.
* Comments on the articles.
* A nicer 403 page.
