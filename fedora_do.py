#!/usr/bin/env python3

import fnmatch
import hashlib
import lzma
import os
from subprocess import Popen, PIPE
import sys
import sqlite3
import time
import xml.dom.minidom

#------------------------------------------------------------------------------

RELEASEVER = '23'
BASEARCH = 'x86_64'

#------------------------------------------------------------------------------

UPDATES_D = os.path.join(
    'updates',
    RELEASEVER, BASEARCH,
)
RELEASES_D = os.path.join(
    'releases',
    RELEASEVER,
    'Everything',
    BASEARCH,
    'os'
)

REPODATA_D = os.path.join(
    UPDATES_D,
    'repodata',
)
UPDATEINFO_F = os.path.join(
    REPODATA_D,
    'updateinfo.xml.xz', # Should be updated from repomd.xml
)
REPOMD_F = os.path.join(
    REPODATA_D,
    'repomd.xml',
)

DOWNLOAD_REPS = [UPDATES_D, RELEASES_D]

INSTALLED_DB_F = 'installed.db'
EVERYTHING_DB_F = '-'.join(('everything', RELEASEVER, BASEARCH)) + '.db'
UPDATES_DB_F = os.path.join(
    UPDATES_D,
    'repodata',
    'primary.db',
)

CHECKSUM_METHOD = 'lib' # 'shell' or 'lib'

#------------------------------------------------------------------------------

class PackageDB(object):
    '''
    Wrapped to operate sqlite3 database
    '''
    def __init__(self, db_fn):
        self.fname = db_fn
        self.con = sqlite3.connect(db_fn)
        # Use row plugin in
        self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()

    def execute(self, *args, **kwargs):
        self.cur.execute(*args, **kwargs)

    def fetchone(self):
        return self.cur.fetchone()

    def commit(self):
        self.con.commit()

    def close(self):
        self.con.close()

    def get_href_from_namearch(self, name, arches):
        self.cur.execute('''
SELECT location_href
FROM   packages
WHERE  name=? AND arch in %s
''' % str(arches),
            (name,),
        )
        results = self.cur.fetchall()
        return [r['location_href'] for r in results]

    def get_buildtime_from_namearch(self, name, arch):
        '''
        Get time build from name and arch
        '''
        self.cur.execute('''
SELECT time_build
FROM   packages
WHERE  name=? AND arch=?
''',
            (name, arch),
        )
        results = self.cur.fetchall()
        return results[0] if results else None

    def get_pkg_count_from_navr(self, name, arch, version, release):
        self.cur.execute('''
SELECT count(*)
FROM   packages
WHERE  name=? AND version=? AND release=? AND arch=?
''',
            (name, version, release, arch),
        )
        return self.cur.fetchall()[0][0]

    def get_checksum_from_href(self, href):
        self.cur.execute('''
SELECT pkgId, checksum_type
FROM   packages
WHERE  location_href=?
''',
            (href,),
        )
        results = self.cur.fetchall()
        return results[0] if results else None

    def get_requires_from_href(self, href):
        self.cur.execute('''
SELECT requires.name
FROM   requires INNER JOIN packages ON requires.pkgKey=packages.pkgKey
WHERE  packages.location_href=?
''',
            (href,),
        )
        return [r['name'] for r in self.cur.fetchall()]

    def get_packages_from_provide(self, prov, arches):
        self.cur.execute('''
SELECT packages.*
FROM   provides INNER JOIN packages ON provides.pkgKey=packages.pkgKey
WHERE  provides.name=? AND packages.arch in %s
''' % str(arches),
            (prov,),
        )
        return self.cur.fetchall()

    def get_info_from_href(self, href):
        self.cur.execute('''
SELECT *
FROM packages
WHERE location_href=?
''',
            (href,),
        )
        results = self.cur.fetchall()
        return results[0] if results else None

#-----------------------------------------------------------------------------

def myshasum(ck_type, ifn, ck_method=CHECKSUM_METHOD):
    if ck_type == 'sha':
        ck_type = 'sha1'
    if ck_method == 'shell':
        result = Popen([ck_type + 'sum', ifn], stdout=PIPE).communicate()[0]
        result = result.split(' ')[0]
    elif ck_method == 'lib':
        result = -1
        with open(ifn, 'rb') as f:
            sha = getattr(hashlib, ck_type)()
            sha.update(f.read())
            result = sha.hexdigest()
    else:
        result = '-1'
    return result

#-----------------------------------------------------------------------------
# Check environment

def check_env():
    if not os.path.exists(INSTALLED_DB_F):
        sys.exit("Missing installed.db file! Do 'lget' first!")

    if not os.path.exists(REPOMD_F):
        sys.exit("Do 'rget' first!")

    global UPDATEINFO_F
    with open(REPOMD_F) as xmlfile:
        dom = xml.dom.minidom.parse(xmlfile)
        href = ''
        for node in dom.getElementsByTagName('location'):
            h = node.getAttribute('href')
            if 'updateinfo' in h:
                href = h
                break
        dom.unlink()
        if href:
            UPDATEINFO_F = os.path.join(UPDATES_D, href)

    if not os.path.exists(UPDATEINFO_F):
        sys.exit("Do 'rget' first!")

#-----------------------------------------------------------------------------
# Process repomd.xml

def get_upkgs_dict(ifn, installed_db, lupdate=False):
    udb = {}
    # Open the gziped xml file
    xmlfile = lzma.open(ifn)
    dom = xml.dom.minidom.parse(xmlfile)
    # Update all packages based on each issue
    for node_issued in dom.getElementsByTagName('issued'):
        # Get issued time in integer format
        new_ti = int(time.mktime(time.strptime(
            node_issued.getAttribute('date').split('.')[0],
            '%Y-%m-%d %H:%M:%S'
        )))
        # Parse all packages on that issued
        node_p = node_issued.parentNode
        for node_pkg in node_p.getElementsByTagName('package'):
            n, a = (
                node_pkg.getAttribute('name'),
                node_pkg.getAttribute('arch'),
            )
            one = installed_db.get_buildtime_from_namearch(n, a)
            if one:
                old_ti = one['time_build']
                if (n, a) in udb:
                    old_ti = udb[(n, a)][0]
                if new_ti > old_ti:
                    new_v = node_pkg.getAttribute('version')
                    new_r = node_pkg.getAttribute('release')
                    if lupdate:
                        installed_db.execute('''
UPDATE packages
SET version=?, release=?, time_build=?
WHERE name=? AND arch=?
''',
                            (
                                new_v, new_r, new_ti,
                                n, a,
                            ),
                        )
                    fn_ele = node_pkg.getElementsByTagName('filename')[0]
                    fn_data = fn_ele.firstChild.data
                    if fn_data[1] != '/': # support Fedroa21's updateinfo db
                        fn_data = os.path.join(fn_data[0].lower(), fn_data)
                    udb[(n, a)] = (new_ti, fn_data)
    xmlfile.close()
    dom.unlink()
    return udb


def get_repodata_list(ifn):
    # Open the xml file
    with open(ifn) as xmlfile:
        dom = xml.dom.minidom.parse(xmlfile)
        for node in dom.getElementsByTagName('location'):
            yield node.getAttribute('href')
        dom.unlink()
    # repomd.xml file
    yield 'repodata/repomd.xml'


def check_repodata(idn, ifn):
    '''
    Check repodata directory
    '''
    success = True
    pdbfn = ''
    rep_dir = idn
    dom = xml.dom.minidom.parse(os.path.join(idn, ifn))
    for ele in dom.getElementsByTagName('data'):
        location_node = ele.getElementsByTagName('location')[0]
        location_href = location_node.getAttribute('href')

        checksum_node = ele.getElementsByTagName('checksum')[0]
        checksum_type = checksum_node.getAttribute('type')
        checksum_exp = checksum_node.firstChild.data

        rep_href = os.path.join(rep_dir, location_href)

        if ele.getAttribute('type') == 'primary_db':
            pdbfn = rep_href

        checksum_real = myshasum(checksum_type, rep_href)

        if checksum_real != checksum_exp:
            print('Checksum error on: {}'.format(rep_href))
            success = True
    dom.unlink()
    return success, pdbfn


def check_pkgs(dlpkgs, installed_db, everything_db, update_db):
    for lpkg in dlpkgs:
        pkg_from = UPDATES_D
        result = update_db.get_checksum_from_href(lpkg)
        if result:
            pkg_from = UPDATES_D
        else:
            result = everything_db.get_checksum_from_href(lpkg)
            if result:
                pkg_from = RELEASES_D

        lpkg_path = os.path.join(pkg_from, lpkg)
        if result:
            ck, ck_type = result
            rck = myshasum(ck_type, lpkg_path, CHECKSUM_METHOD)
            if rck != ck:
                print('Checksum error on: {}'.format(lpkg_path))
        else:
            print('Unknown package: {}'.format(lpkg_path))


def resolve_package(
    pkg, dlpkgs,
    arches,
    installed_db,
    everything_db,
    update_db,
    req_list,
):

    real_dlpkgs = get_all_dl_pkgs()

    def get_pkg_db_from_href(href):
        pkg_db = update_db.get_info_from_href(href)
        pkg_from = UPDATES_D
        if not pkg_db:
            pkg_db = everything_db.get_info_from_href(href)
            pkg_from = RELEASES_D
        return pkg_from, pkg_db

    def check_pkg_avail(pkg_db):
        href = pkg_db['location_href']
        name = pkg_db['name']
        arch = pkg_db['arch']
        version = pkg_db['version']
        release = pkg_db['release']
        is_available = False
        if href in real_dlpkgs:
            # Package is downloaded
            is_available = True
        else:
            # Package is installed or included in iso
            if installed_db.get_pkg_count_from_navr(
                name, arch, version, release
            ) > 0:
                is_available = True
        return is_available

    def get_req_pkgs_from_href(href, pkg_reqs):
        # Get requires
        reqs = update_db.get_requires_from_href(href)
        if not reqs:
            reqs = everything_db.get_requires_from_href(href)
        # Get package from its provides which suplied by the requires
        for prov in reqs:
            pdbs = update_db.get_packages_from_provide(prov, arches)
            pkg_from = UPDATES_D
            if not pdbs:
                pdbs = everything_db.get_packages_from_provide(prov, arches)
                pkg_from = RELEASES_D
            # Filter the installed package
            if pdbs and not [pdb for pdb in pdbs if check_pkg_avail(pdb)]:
                p = pdbs[0]
                p_href = p['location_href']
                if not [
                    req for req in pkg_reqs \
                        if req[1]['location_href'] == p_href
                ]:
                    pkg_reqs.append((pkg_from, p))

    # Get all hierarchical requires packages
    pkg_from, pkg_db = get_pkg_db_from_href(pkg)
    if not pkg_db:
        print('Unknown package: {}'.format(pkg))
        return

    pkg_reqs = [(pkg_from, pkg_db)]
    get_req_pkgs_from_href(pkg, pkg_reqs)
    # Check each requier's availability
    for req in pkg_reqs:
        if req[1] and not check_pkg_avail(req[1]):
            href = req[1]['location_href']
            rs = [r for r in req_list if r[:2] == (req[0], href)]
            if not rs:
                req_list.append((req[0], href, [pkg]))
            else:
                rs[0][2].append(pkg)


def update_lpkgs_db(installed_db):
    try:
        import rpm
    except:
        sys.exit('Make sure the rpm-python package has been installed!')

    # Clear the old database
    try:
        installed_db.execute('DELETE FROM packages')
    except:
        pass

    # Create a new database
    try:
        installed_db.execute('''
CREATE TABLE packages (
    name TEXT,
    version TEXT,
    release TEXT,
    arch TEXT,
    time_build INTEGER
)
''',
        )
        installed_db.execute(
            'CREATE INDEX packagename ON packages (name)',
        )
        installed_db.execute(
            'CREATE INDEX packagearch ON packages (arch)',
        )
    except:
        pass

    ts = rpm.TransactionSet()
    mi = ts.dbMatch()
    for h in mi:
        installed_db.execute('''
INSERT INTO packages VALUES(
    :name,
    :version,
    :release,
    :arch,
    :time_build
)
''',
            {
                'name': h[rpm.RPMTAG_NAME],
                'version': h[rpm.RPMTAG_VERSION],
                'release': h[rpm.RPMTAG_RELEASE],
                'arch': h[rpm.RPMTAG_ARCH],
                'time_build': h[rpm.RPMTAG_BUILDTIME],
            },
        )


def get_all_dl_pkgs():
    pkgs = []
    for rep in DOWNLOAD_REPS:
        for root,dirs,files in os.walk(rep):
            for f in files:
                if fnmatch.fnmatch(f, '*.rpm'):
                    pkg_path = os.path.join(root, f)
                    pkg = pkg_path.replace(rep + '/', '')
                    pkgs.append(pkg)
    return pkgs

#-----------------------------------------------------------------------------

if __name__ == '__main__':
    available_args = [
        'list', 'check', 'resolve', 'lupdate', 'lget', 'parse',
    ]

    if len(sys.argv) < 2 or sys.argv[1] not in available_args:
        sys.exit('Usage: ./fedora_do.py %s' % '|'.join(available_args))
    else:
        optype = sys.argv[1]

    # Open db all
    installed_db = PackageDB(INSTALLED_DB_F)
    everything_db = PackageDB(EVERYTHING_DB_F)
    update_db = None

    if optype == 'list':
        check_env()
        udb = get_upkgs_dict(UPDATEINFO_F, installed_db)
        if len(udb):
            for f in [udb[k][1] for k in sorted(udb.keys())]:
                print(os.path.join(UPDATES_D, f))
            for f in [x for x in get_repodata_list(REPOMD_F)]:
                print(os.path.join(UPDATES_D, f))

    elif optype == 'check':
        check_env()
        dlpkgs = get_all_dl_pkgs()
        if len(dlpkgs):
            # Check repodata
            success, pdbfn = check_repodata(
                UPDATES_D,
                'repodata/repomd.xml',
            )
            # Check downloaded updating package
            if success and pdbfn:
                with lzma.open(pdbfn) as xzf:
                    xzdata = xzf.read()
                with open(UPDATES_DB_F, 'wb') as tempfn:
                    tempfn.write(xzdata)

                update_db = PackageDB(UPDATES_DB_F)
                check_pkgs(
                    dlpkgs,
                    installed_db,
                    everything_db,
                    update_db,
                )
            else:
                sys.exit('Fix the repodata first!')

    elif optype == 'resolve':
        check_env()
        udb = get_upkgs_dict(UPDATEINFO_F, installed_db)
        uppkgs = [udb[p][1] for p in udb]
        req_list = []
        if not os.path.exists(UPDATES_DB_F):
            sys.exit('Do check first!')
        update_db = PackageDB(UPDATES_DB_F)
        for pkg in uppkgs:
            resolve_package(
                pkg, uppkgs,
                (BASEARCH, 'noarch', 'x86_64'),
                installed_db,
                everything_db,
                update_db,
                req_list,
            )
        for req in req_list:
            print('{} ==> {}'.format(
                os.path.join(req[0], req[1]),
                req[2],
            ))

    elif optype == 'lupdate':
        check_env()
        udb = get_upkgs_dict(UPDATEINFO_F, installed_db, True)
        installed_db.commit()

    elif optype == 'lget':
        update_lpkgs_db(installed_db)
        installed_db.commit()

    elif optype == 'parse':
        pkg_names = sys.argv[2:]
        update_db = PackageDB(UPDATES_DB_F)

        for pkg_name in pkg_names:
            name = pkg_name
            arches = ('i686', 'x86_64', 'noarch')
            if '.' in name:
                name, arch = name.split('.')
                arches = (arch, arch)
            pkgs = update_db.get_href_from_namearch(name, arches)
            pkg_from = UPDATES_D
            if not pkgs:
                pkgs = everything_db.get_href_from_namearch(name, arches)
                pkg_from = RELEASES_D

            if not pkgs:
                print('Unknown package name. Please input a valid package name!')
            else:
                # Filtering based on the arch
                for pkg in pkgs:
                    href = pkg
                    # Resolve the package
                    dlpkgs = get_all_dl_pkgs()
                    req_list = []
                    resolve_package(
                        href, dlpkgs,
                        arches,
                        installed_db,
                        everything_db,
                        update_db,
                        req_list,
                    )
                for req in req_list:
                    print(os.path.join(req[0], req[1]))

    # Close db all
    if update_db:
        update_db.close()
    everything_db.close()
    installed_db.close()

