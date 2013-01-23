# vim:ts=4:sw=4

RELEASEVER=18
BASEARCH=x86_64

# HTTP URL for 'http' mode
REMOTE=http://dl.fedoraproject.org/pub/fedora/linux
REMOTE_ALT={http://mirrors.163.com/fedora,http://mirrors.sohu.com/fedora,http://mirrors.kernel.org/fedora}
LOCAL=~ftp/pub/fedora/linux
UPDATES=updates/$(RELEASEVER)/$(BASEARCH)

REPOMD_F=$(UPDATES)/repodata/repomd.xml
UPDATEINFO_F=$(UPDATES)/repodata/updateinfo.xml.gz

#------------------------------------------------------------------------------

.PHONY: usage
usage:
	$(info "Usage: make lget|rget|list|rsync|check|resolve|lsync|lupdate|parse")

.PHONY: lget
lget:
#	rpm -qa --qf "%{NAME}|%{ARCH}|%{VERSION}|%{RELEASE}\n" | sort
	@./fedora_do.py $@

$(REPOMD_F):
	wget -N -P $(UPDATES)/repodata $(REMOTE)/$@

$(UPDATEINFO_F):
	wget -N -P $(UPDATES)/repodata $(REMOTE)/$@

.PHONY: rget
rget: $(REPOMD_F) $(UPDATEINFO_F)

.PHONY: list
list: rget
	@./fedora_do.py $@

.PHONY: rsync
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

.PHONY: check
check:
	@./fedora_do.py $@

.PHONY: resolve
resolve:
	@./fedora_do.py $@ | uniq | sort

.PHONY: lsync
lsync:
	@if [ -d updates ]; then \
		rm -rf $(LOCAL)/$(UPDATES)/repodata; \
		find updates -type f | xargs chmod 644; \
		find updates -type d | xargs chmod 755; \
		mv $(UPDATES)/* $(LOCAL)/$(UPDATES); \
		echo "The new updates has been moved to desination."; \
	fi

.PHONY: lupdate
lupdate:
	@./fedora_do.py $@

.PHONY: parse
parse:
	@./fedora_do.py $@ | uniq | sort

