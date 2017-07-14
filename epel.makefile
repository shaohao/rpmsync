# vim:ts=4:sw=4

VER?=7
MOD?=x86_64
JOBS?=20

RREPO=rsync://mirrors.kernel.org/fedora-epel
#RREPO=rsync://mirrors.yun-idc.com/fedora-epel
#RREPO=msync.fedora-epel.org::CentOS
#RREPO=rsync://rsync.arcticnetwork.ca/fedora-epel
#RREPO=rsync://mirrros.tuna.tsinghua.edu.cn/fedora-epel
DLREPO={http://mirrors.aliyun.com/epel,http://mirrors.kernel.org/fedora-epel}
LREPO=fedora-epel

RSYNC=rsync -avPh --no-motd --exclude=SRPMS/ --exclude=drpms/ --exclude=i386/ --exclude=debug/

TMP_LST=/tmp/fedora-epel-$(VER)-$(MOD)-pkgs.lst

#------------------------------------------------------------------------------

.PHONY: usage fetch pull check

usage:
	@echo "Usage: make fetch|pull|check"

fetch:
	@echo "Fetching the package list file to $(TMP_LST)"
	@$(RSYNC) $(RREPO)/$(VER)/$(MOD) | sed -n '/^-r/p' | sed -e "s,.*\s$(MOD),$(MOD),g" >$(TMP_LST)

pull: $(TMP_LST)
	./mdl.sh $(TMP_LST) "$(LREPO)/$(VER)" "$(DLREPO)/$(VER)" $(JOBS)

check:
	@$(RSYNC) --delete $(RREPO)/$(VER)/$(MOD) $(LREPO)/$(VER)/

