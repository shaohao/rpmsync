#!/bin/bash

# output the package list which should be downloaded from everything repo
# after migrating to new version.

# check arguments
if [[ $# -lt 2 ]]; then
    echo "USAGE: ./migrate_diff.sh new_fedora_db new_everything_db"
    exit -1
fi

f_new_db=$1
e_new_db=$2

cat <<EOC >dl.sh
#!/bin/bash

RELEASEVER=19
BASEARCH=x86_64

REMOTE=http://dl.fedoraproject.org/pub/fedora/linux
REMOTE_ALT={http://mirrors.163.com/fedora,http://mirrors.sohu.com/fedora,http://mirrors.kernel.org/fedora}

PKG_DIR=releases/\$RELEASEVER/Everything/\$BASEARCH/os

pkgs=(
EOC

pkgs=$(
sqlite3 -separator '|' <<EOC
ATTACH DATABASE "installed.db" AS inst;
ATTACH DATABASE "$f_new_db" AS fdb;

SELECT inst.packages.name, inst.packages.arch
FROM inst.packages
LEFT JOIN fdb.packages
ON inst.packages.name = fdb.packages.name AND
   inst.packages.arch = fdb.packages.arch
WHERE fdb.packages.location_href IS NULL
;
EOC
)

for pkg in $pkgs; do
    IFS='|' read -a na <<< "$pkg"
    sqlite3 $e_new_db <<EOC >>dl.sh
SELECT location_href
FROM packages
WHERE name = "${na[0]}" AND
      arch = "${na[1]}"
ORDER BY name
;
EOC
done

cat <<EOC >>dl.sh
)

for pkg in \${pkgs[*]}; do
{
	line=\$PKG_DIR/\$pkg
	d=\$(dirname \$line)
	f=\$(basename \$line)
	mkdir -p \$d
	if [ ! -f \$line -o -f \$line.aria2 ]; then
		aria2c -R -s5 \$REMOTE/\$line \$REMOTE_ALT/\$line --dir=\$d
	else
		echo "\$f exists, skipping..."
	fi
}&
done
EOC

chmod +x dl.sh

# ex: et ts=4 sw=4

