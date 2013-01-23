#!/bin/bash

# Migrate to a new Fedora

# check arguments
if [[ $# -lt 3 ]]; then
    echo "USAGE: ./migrate.sh new_everything_db old_db new_db"
    exit -1
fi

e_new_db=$1
i_old_db=$2
i_new_db=$3

# check sqlite3
if ! which sqlite3 &>/dev/null; then
    echo "Make sure sqlite3 command line utility is installed properly."
    exit -1
fi

# Database protection
read -p """
The old database will be deleted permanently!
Are you sure to migrate to the new database? [y/N]""" ans
if [[ x"$ans" != x"y" && x"$ans" != x"Y" ]]; then
    echo "Migration aborted!"
    exit 0
fi

# Remove old database
rm -rf $i_new_db

# MIGRATION
sqlite3 $i_new_db <<EOC
ATTACH DATABASE "$e_new_db" AS enew;
ATTACH DATABASE "$i_old_db" AS iold;

CREATE TABLE packages (
    name TEXT,
    version TEXT,
    release TEXT,
    arch TEXT,
    time_build INTEGER
);
CREATE INDEX packagename ON packages (name);
CREATE INDEX packagearch ON packages (arch);

INSERT INTO packages
    SELECT enew.packages.name, enew.packages.version, enew.packages.release, enew.packages.arch, enew.packages.time_build
    FROM enew.packages
    INNER JOIN iold.packages
    ON
        enew.packages.name = iold.packages.name
        AND
        enew.packages.arch = iold.packages.arch
;
EOC

# ex: et ts=4 sw=4
