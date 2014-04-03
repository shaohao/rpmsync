# vim:ts=4:sw=4

RELEASEVER=20
BASEARCH=x86_64

# HTTP URL for 'http' mode
REMOTE=http://dl.fedoraproject.org/pub/fedora/linux
REMOTE_ALT={http://mirrors.163.com/fedora,http://mirrors.sohu.com/fedora,http://mirrors.kernel.org/fedora}
LOCAL=~ftp/pub/fedora/linux
UPDATES=updates/$(RELEASEVER)/$(BASEARCH)
REPODATA=$(UPDATES)/repodata

REPOMD_F=$(REPODATA)/repomd.xml
UPDATEINFO_F=$(REPODATA)/updateinfo.xml.gz

SED_EXPR='s^.*href="repodata/\(\w\+-updateinfo\.xml\.gz\)".*^\1\n^p'

#------------------------------------------------------------------------------

.PHONY: usage lget rget list rsync check resolve lsync lupdate parse

usage:
	$(info "Usage: make lget|rget|list|rsync|check|resolve|lsync|lupdate|parse")

lget:
	@./fedora_do.py $@

.PHONY: $(REPOMD_F)
$(REPOMD_F):
	wget -N -P $(REPODATA) $(REMOTE)/$@

.PHONY: $(UPDATEINFO_F)
$(UPDATEINFO_F): $(REPOMD_F)
	$(eval UPDATEINFO_F=$(REPODATA)/$(shell sed -n $(SED_EXPR) $(REPOMD_F)))
	wget -N -P $(REPODATA) $(REMOTE)/$(UPDATEINFO_F)

rget: $(REPOMD_F) $(UPDATEINFO_F)

list: rget
	@./fedora_do.py $@

rsync:
	@./fedora_do.py list | while read line; do \
	{ \
		d=`dirname $$line`; \
		f=`basename $$line`; \
		mkdir -p $$d; \
		if [ ! -f $$line -o -f $$line.aria2 ]; then \
			aria2c -R -s5 $(REMOTE)/$$line $(REMOTE_ALT)/$$line --dir=$$d; \
		else \
			echo "$$f exists, skipping..."; \
		fi \
	}& \
	done

check:
	@./fedora_do.py $@

resolve:
	@./fedora_do.py $@ | uniq | sort

lsync:
	@if [ -d updates ]; then \
		rm -rf $(LOCAL)/$(UPDATES)/repodata; \
		find updates -type f | xargs chmod 644; \
		find updates -type d | xargs chmod 755; \
		mv $(UPDATES)/* $(LOCAL)/$(UPDATES); \
		echo "The new updates has been moved to desination."; \
	fi

lupdate:
	@./fedora_do.py $@

parse:
	@./fedora_do.py $@ | uniq | sort

