# vim:ts=4:sw=4

VER?=7
MOD?=updates

RREPO=rsync://mirrors.kernel.org/centos
#RREPO=rsync://mirrors.yun-idc.com/centos
#RREPO=msync.centos.org::CentOS
#RREPO=rsync://rsync.arcticnetwork.ca/centos
#RREPO=rsync://mirrros.tuna.tsinghua.edu.cn/centos
DLREPO={http://mirrors.aliyun.com/centos,http://msync.centos.org/centos}
LREPO=centos

RSYNC=rsync -avPh --no-motd --exclude=SRPMS/ --exclude=drpms/ --exclude=i386/

TMP_LST=/tmp/centos-$(VER)-$(MOD)-pkgs.lst

#------------------------------------------------------------------------------

.PHONY: usage fetch pull check

usage:
	@echo "Usage: make list|rsync|check"

fetch:
	@echo "Fetching the package list file to $(TMP_LST)"
	@$(RSYNC) $(RREPO)/$(VER)/$(MOD) | sed -n '/^-r/p' | sed -e "s,.*\s$(MOD),$(MOD),g" >$(TMP_LST)

pull: $(TMP_LST)
	@cat $(TMP_LST) | while read line; do \
	{ \
		p=$(LREPO)/$(VER)/$$line; \
		d=`dirname $$p`; \
		f=`basename $$p`; \
		mkdir -p $$d; \
		if [ ! -f $$p -o -f $$p.aria2 ]; then \
			aria2c -R -s5 $(DLREPO)/$(VER)/$$line --dir=$$d; \
		else \
			echo "$$f exists, skipping..."; \
		fi \
	}& \
	done

check:
	@$(RSYNC) --delete $(RREPO)/$(VER)/$(MOD) $(LREPO)/$(VER)/

