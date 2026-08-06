News Application documentation
==============================

This is the documentation for my Django News Application capstone project.

The application lets readers subscribe to publishers and independent
journalists, lets journalists write articles and newsletters, and lets
editors approve them before they are published. There is also a REST API
that uses token authentication.

The pages below are generated automatically from the docstrings in the
code.

Apps and roles
--------------

There are three kinds of user, set by the ``role`` field on
``news.models.CustomUser``:

* **Reader** -- can read approved articles and subscribe to publishers
  and journalists.
* **Journalist** -- can write, edit and delete their own articles and
  newsletters.
* **Editor** -- can approve, edit and delete any article.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
