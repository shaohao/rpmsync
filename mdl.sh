#!/bin/bash

plst=$1
lloc=$2
rloc=$3
njob=$4

cat <<EOC | make -f - -s -j$njob
PHONY=JOBS
JOBS = \$(shell xargs -a $plst)
all: \${JOBS}
\${JOBS}:
	p=$lloc/\$@; \
	d=\`dirname \$\$p\`; \
	f=\`basename \$\$p\`; \
	mkdir -p \$\$d; \
	if [ ! -f \$\$p -o -f \$\$p.aria2 ]; then \
		aria2c -R -s5 $rloc/\$@ --dir=\$\$d; \
	else \
		echo "\$\$f exists, skipping..."; \
	fi
EOC
