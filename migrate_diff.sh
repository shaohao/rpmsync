#!/bin/bash

# output the package list which should be downloaded from everything repo
# after migrating to new version.

sqlite3 -separator '-' <<EOC
ATTACH DATABASE "installed.db" AS inst;
ATTACH DATABASE "fedora-18-x86_64.db" AS fdb;

SELECT fdb.packages.location_href
FROM fdb.packages
LEFT JOIN inst.packages
ON fdb.packages.name = inst.packages.name
WHERE inst.packages.name IS NULL
ORDER BY fdb.packages.name
;
EOC

# ex: et ts=4 sw=4

