#!/bin/bash

ver=7
rrepurl=msync.centos.org::CentOS/$ver/
#rrepurl=rsync://rsync.arcticnetwork.ca/centos/$ver/
dlurl=http://msync.centos.org/centos
lrepurl=~ftp/centos/$ver/
lreplstf="local_rep.lst"
rreplstf="remote_rep.lst"

retrieve_rep_content () {
	rsync -avPh --exclude=SRPMS/ --exclude=isos/ --exclude=i386/ $* | \
	awk '{ printf "%s|%s|%s|%s\n", $5, $3, $4, $2 }' \
	    - | \
	sort
}

update_rep_content() {
	exec 3<&0

	while read line <&3; do
	{
		d=`dirname $line`
		f=`basename $line`
		mkdir -p $ver/$d
		if [ ! -f $ver/$line -o -f $ver/$line.aria2 ]; then
			aria2c -s5 $dlurl/$ver/$line --dir=$ver/$d
		else
			echo "$f exists, skipping..."
		fi
	}&
	done

	exec 0<&3 3>&-
}

print_usage () {
	echo "
Export the content of package repository to standard out
or
Download updated packages from remote server based on the list file from stdin.

Usage: ./repsync export|rsync|update

  export: Export local reposiroty content.
  rsync : Export remote repository content.
  update: Download updated packages from remote server. The updated packages
          are read from stdin.
"
}

case $1 in
export)
	shift
	if [ $# -ge 1 ]; then
		retrieve_rep_content $*
	else
		retrieve_rep_content $lrepurl $*
	fi
	;;
rsync)
	shift
	if [ $# -ge 1 ]; then
		retrieve_rep_content --no-motd $*
	else
		retrieve_rep_content --no-motd $rrepurl $*
	fi
	;;
update)
	shift
	update_rep_content $*
	;;
*)
	print_usage
	exit
	;;
esac

# vim:ts=4:sw=4

