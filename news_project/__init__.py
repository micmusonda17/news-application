"""
This file runs before anything else in the project.

Django normally talks to MariaDB with a package called mysqlclient, but
that one has to be compiled and it did not want to install on my
computer. So I use PyMySQL instead, which is written in pure python.
The two lines below tell PyMySQL to pretend that it is mysqlclient so
that django is happy.
"""

try:
    import pymysql

    # django checks the version and wants at least 1.4.3, so I tell it
    # that this is version 1.4.6
    pymysql.version_info = (1, 4, 6, 'final')
    pymysql.install_as_MySQLdb()
except ImportError:
    # PyMySQL is not installed. That is fine if I am using sqlite.
    pass
