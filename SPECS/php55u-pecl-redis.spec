# IUS spec file for php56u-pecl-redis, forked from:

# Fedora spec file for php-pecl-redis
#
# Copyright (c) 2012-2013 Remi Collet
# License: CC-BY-SA
# http://creativecommons.org/licenses/by-sa/3.0/
#
# Please, preserve the changelog entries
#

%global pecl_name  redis
%global with_zts   0%{?__ztsphp:1}
%global with_tests 0
# after 40-igbinary
%global ini_name    50-%{pecl_name}.ini

%global php_base php55u

Summary:       Extension for communicating with the Redis key-value store
Name:          %{php_base}-pecl-redis
Version:       2.2.8
Release:       1.ius%{?dist}
License:       PHP
Group:         Development/Languages
URL:           http://pecl.php.net/package/redis
Source0:       http://pecl.php.net/get/%{pecl_name}-%{version}.tgz

BuildRequires: %{php_base}-devel
BuildRequires: %{php_base}-pear
BuildRequires: %{php_base}-pecl-igbinary-devel
# to run Test suite
%if %{with_tests}
# should use redis28u
BuildRequires: redis >= 2.6
%endif

Requires:      %{php_base}(zend-abi) = %{php_zend_api}
Requires:      %{php_base}(api) = %{php_core_api}
Requires:      %{php_base}-pecl-igbinary%{?_isa}

Requires(post): %{php_base}-pear
Requires(postun): %{php_base}-pear

# provide the stock name
Provides:      php-pecl-%{pecl_name} = %{version}
Provides:      php-pecl-%{pecl_name}%{?_isa} = %{version}

# provide the stock and IUS names without pecl
Provides:      php-%{pecl_name} = %{version}
Provides:      php-%{pecl_name}%{?_isa} = %{version}
Provides:      %{php_base}-%{pecl_name} = %{version}
Provides:      %{php_base}-%{pecl_name}%{?_isa} = %{version}

# provide the stock and IUS names in pecl() format
Provides:      php-pecl(%{pecl_name}) = %{version}
Provides:      php-pecl(%{pecl_name})%{?_isa} = %{version}
Provides:      %{php_base}-pecl(%{pecl_name}) = %{version}
Provides:      %{php_base}-pecl(%{pecl_name})%{?_isa} = %{version}

# conflict with the stock name
Conflicts:     php-pecl-%{pecl_name} < %{version}

%if 0%{?fedora} < 20 && 0%{?rhel} < 7
# Filter private shared object
%{?filter_provides_in: %filter_provides_in %{_libdir}/.*\.so$}
%{?filter_setup}
%endif


%description
The phpredis extension provides an API for communicating
with the Redis key-value store.

This Redis client implements most of the latest Redis API.
As method only only works when also implemented on the server side,
some doesn't work with an old redis server version.


%prep
%setup -q -c

# rename source folder
mv %{pecl_name}-%{version} nts

# Sanity check, really often broken
extver=$(sed -n '/#define PHP_REDIS_VERSION/{s/.* "//;s/".*$//;p}' nts/php_redis.h)
if test "x${extver}" != "x%{version}"; then
   : Error: Upstream extension version is ${extver}, expecting %{version}.
   exit 1
fi

%if %{with_zts}
# duplicate for ZTS build
cp -pr nts zts
%endif

# Drop in the bit of configuration
cat > %{ini_name} << 'EOF'
; Enable %{pecl_name} extension module
extension = %{pecl_name}.so

; phpredis can be used to store PHP sessions.
; To do this, uncomment and configure below

; RPM note : save_handler and save_path are defined
; for mod_php, in /etc/httpd/conf.d/php.conf
; for php-fpm, in %{_sysconfdir}/php-fpm.d/*conf

;session.save_handler = %{pecl_name}
;session.save_path = "tcp://host1:6379?weight=1, tcp://host2:6379?weight=2&timeout=2.5, tcp://host3:6379?weight=2"
EOF


%build
pushd nts
%{_bindir}/phpize
%configure \
    --enable-redis \
    --enable-redis-session \
    --enable-redis-igbinary \
    --with-php-config=%{_bindir}/php-config
make %{?_smp_mflags}
popd

%if %{with_zts}
pushd zts
%{_bindir}/zts-phpize
%configure \
    --enable-redis \
    --enable-redis-session \
    --enable-redis-igbinary \
    --with-php-config=%{_bindir}/zts-php-config
make %{?_smp_mflags}
popd
%endif


%install
# Install the NTS stuff
make -C nts install INSTALL_ROOT=%{buildroot}
install -D -m 644 %{ini_name} %{buildroot}%{php_inidir}/%{ini_name}

# Install the ZTS stuff
%if %{with_zts}
make -C zts install INSTALL_ROOT=%{buildroot}
install -D -m 644 %{ini_name} %{buildroot}%{php_ztsinidir}/%{ini_name}
%endif

# Install the package XML file
install -D -m 644 package.xml %{buildroot}%{pecl_xmldir}/%{name}.xml

# Test & Documentation
cd nts
for i in $(grep 'role="doc"' ../package.xml | sed -e 's/^.*name="//;s/".*$//')
do install -Dpm 644 $i %{buildroot}%{pecl_docdir}/%{pecl_name}/$i
done


%check
# simple module load test
%{__php} --no-php-ini \
    --define extension=igbinary.so \
    --define extension=%{buildroot}%{php_extdir}/%{pecl_name}.so \
    --modules | grep %{pecl_name}

%if %{with_zts}
%{__ztsphp} --no-php-ini \
    --define extension=igbinary.so \
    --define extension=%{buildroot}%{php_ztsextdir}/%{pecl_name}.so \
    --modules | grep %{pecl_name}
%endif

%if %{with_tests}
cd nts/tests

# this test requires redis >= 2.6.9
# https://github.com/nicolasff/phpredis/pull/333
sed -e s/testClient/SKIP_testClient/ \
    -i TestRedis.php

# this test requires redis >= 2.8.0
# self-described as "problematic"
sed -e s/testPubSub/SKIP_testPubSub/ \
    -i TestRedis.php

# Launch redis server
mkdir -p {run,log,lib}/redis
sed -e "s:/^pidfile.*$:/pidfile $PWD/run/redis.pid:" \
    -e "s:/var:$PWD:" \
    -e "/daemonize/s/no/yes/" \
    /etc/redis.conf >redis.conf
# port number to allow 32/64 build at same time
# and avoid conflict with a possible running server
%if 0%{?__isa_bits}
port=$(expr %{__isa_bits} + 6350)
%else
%ifarch x86_64
port=6414
%else
port=6382
%endif
%endif
sed -e "s/6379/$port/" -i redis.conf
sed -e "s/6379/$port/" -i TestRedis.php
%{_bindir}/redis-server ./redis.conf

# Run the test Suite
ret=0
%{__php} --no-php-ini \
    --define extension=igbinary.so \
    --define extension=%{buildroot}%{php_extdir}/%{pecl_name}.so \
    TestRedis.php || ret=1

# Cleanup
if [ -f run/redis.pid ]; then
   kill $(cat run/redis.pid)
fi

exit $ret

%else
: Upstream test suite disabled
%endif


%post
%{pecl_install} %{pecl_xmldir}/%{name}.xml >/dev/null || :


%postun
if [ $1 -eq 0 ] ; then
    %{pecl_uninstall} %{pecl_name} >/dev/null || :
fi


%files
%{?_licensedir:%license nts/COPYING}
%doc %{pecl_docdir}/%{pecl_name}
%{pecl_xmldir}/%{name}.xml

%{php_extdir}/%{pecl_name}.so
%config(noreplace) %{php_inidir}/%{ini_name}

%if %{with_zts}
%{php_ztsextdir}/%{pecl_name}.so
%config(noreplace) %{php_ztsinidir}/%{ini_name}
%endif


%changelog
* Thu Jun 09 2016 Carl George <carl.george@rackspace.com> - 2.2.8-1.ius
- Latest upstream
- Clean up provides and conflicts

* Sat Feb 13 2016 Carl George <carl.george@rackspace.com> - 2.2.7-2.ius
- Remove Source1, tests are now included in Source0
- Add pear as a build requirement
- Only provide version for stock name, not release
- Wrap filter provides in conditional
- Mark COPYING file with %%license when possible

* Wed Mar 04 2015 Carl George <carl.george@rackspace.com> - 2.2.7-1.ius
- Latest upstream

* Mon Oct 06 2014 Carl George <carl.george@rackspace.com> - 2.2.5-1.ius
- Update to 2.2.5
- Add numerical prefix to extension configuration file
- Enable test suite
- Move doc in pecl_docdir
- Re-enable igbinary
- Change pear to a post/postun dependency

* Fri Jan 03 2014 Ben Harper <ben.harper@rackspace.com> - 2.2.4-4.ius
- porting from php54-pecl-redis

* Thu Oct 24 2013 Ben Harper <ben.harper@rackspace.com> - 2.2.4-3.ius
- add prodives for php-pecl-redis

* Wed Oct 02 2013 Ben Harper <ben.harper@rackspace.com> - 2.2.4-2.ius
- porting from EPEL
- removing igbinary requirements

* Mon Sep 09 2013 Remi Collet <remi@fedoraproject.org> - 2.2.4-1
- Update to 2.2.4

* Tue Apr 30 2013 Remi Collet <remi@fedoraproject.org> - 2.2.3-1
- update to 2.2.3
- upstream moved to pecl, rename from php-redis to php-pecl-redis

* Tue Sep 11 2012 Remi Collet <remi@fedoraproject.org> - 2.2.2-5.git6f7087f
- more docs and improved description

* Sun Sep  2 2012 Remi Collet <remi@fedoraproject.org> - 2.2.2-4.git6f7087f
- latest snahot (without bundled igbinary)
- remove chmod (done upstream)

* Sat Sep  1 2012 Remi Collet <remi@fedoraproject.org> - 2.2.2-3.git5df5153
- run only test suite with redis > 2.4

* Fri Aug 31 2012 Remi Collet <remi@fedoraproject.org> - 2.2.2-2.git5df5153
- latest master
- run test suite

* Wed Aug 29 2012 Remi Collet <remi@fedoraproject.org> - 2.2.2-1
- update to 2.2.2
- enable ZTS build

* Tue Aug 28 2012 Remi Collet <remi@fedoraproject.org> - 2.2.1-1
- initial package

