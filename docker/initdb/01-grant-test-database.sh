#!/bin/bash
#
# Lets the application user create Django's test database.
#
# The MariaDB image creates one database (news_application) and grants the
# application user rights on that database only. But "manage.py test" does
# not use it: Django builds a separate, throwaway database called
# "test_news_application", runs the tests inside it, and drops it again so
# that the real data is never touched.
#
# Creating that database needs a privilege the user does not have by
# default, so the tests fail with:
#
#   (1044, "Access denied for user 'news_user'@'%' to database
#           'test_news_application'")
#
# The grant below fixes that. "test\_%" matches any database whose name
# starts with "test_" - the backslash escapes the underscore, which would
# otherwise be a single-character wildcard. The database does not have to
# exist yet for the grant to be valid.
#
# Any .sh or .sql file in /docker-entrypoint-initdb.d is run by the MariaDB
# image, but ONLY the first time the data directory is created. If you
# change this file you must run "docker compose down -v" to wipe the volume
# before it takes effect again.

set -e

mariadb --protocol=socket -uroot -p"${MARIADB_ROOT_PASSWORD}" <<-EOSQL
    GRANT ALL PRIVILEGES ON \`test\_%\`.* TO '${MARIADB_USER}'@'%';
    FLUSH PRIVILEGES;
EOSQL

echo "Granted ${MARIADB_USER} rights on Django's test databases (test_*)."
