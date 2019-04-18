I spent some time checking the OS packages for Lmod and environment-modules; here's a few notes, mainly for reference when implementing a "module" role:

## CentOS 7

Lmod:
- default module directory (used by other OS packages) is `/etc/modulefiles`
- module search path set in `/etc/profile.d/00-modulepath.sh` to `/etc/modulefiles:/usr/share/modulefiles`
- SH-like shells load `/etc/profile.d/z00_lmod.sh` (i.e., `/usr/share/lmod/lmod/init/profile`)
- CSH-like shells load `/etc/profile.d/z00_lmod.csh` (i.e., `/usr/share/lmod/lmod/init/cshrc`)
- EPEL needed

environment-modules:
- default module directory (used by other OS packages) is `/etc/modulefiles`
- module search path must be customized using shell profile script
- SH-like shells load `/etc/profile.d/modules.sh`
- CSH-like shells load `/etc/profile.d/modules.csh`
- in main OS repositories (i.e., no EPEL needed)

The two packages *do not conflict*, so both can be installed at the same time.


## Ubuntu 18.04 ("bionic"), Debian 9 ("stretch")

Lmod:
- symlink `/usr/share/lmod/lmod -> 5.8`
- default module search path defined by adding lines to `/etc/lmod/modulespath`
- SH-like shells load `/etc/profile.d/lmod.sh`

environment-modules:
- default module search path defined by adding lines to `/etc/environment-modules/modulespath`
- SH-like shells load `/etc/profile.d/modules.sh`
- CSH-like shells load `/etc/csh/login.d/modules`
- version is 4.1.1 on Ubuntu 18.04 and 3.2.10 on Debian 9
- on Debian 9, installing the package brings in a world of dependencies (including GCC, bzip2 and a bunch of libraries...)

The two packages conflict, so installing `lmod` will wipe out `environment-modules` (save for the config files in `/etc`)


## Ubuntu 16.04 ("xenial")

Lmod:
- symlink `/usr/share/lmod/lmod -> 5.8`
- no shell snippet to load it by default in login shells
- no default system-wide module files directory

environment-modules:
- default module search path defined by adding lines to `/etc/environment-modules/modulespath`
- SH-like shells load `/etc/profile.d/lmod.sh`
- CSH-like shells load `/etc/csh/login.d/modules`
- installing the package brings in a world of dependencies (including GCC, bzip2 and a bunch of libraries...)

The two packages *do not conflict*, so both can be installed at the same time.


## Debian 8 ("jessie")

Lmod:
- **version 5.6.2 is not enough for EasyBuild!**
- no shell snippet to load it by default in login shells
- no default system-wide module files directory

environment-modules:
- default module search path defined by adding lines to `/etc/environment-modules/modulespath`
- SH-like shells load `/etc/profile.d/lmod.sh`
- CSH-like shells load `/etc/csh/login.d/modules`
- installing the package brings in a world of dependencies (including GCC, bzip2 and a bunch of libraries...)

The two packages *do not conflict*, so both can be installed at the same time.


## CentOS 6

Lmod:
- default module directory (used by other OS packages) is `/etc/modulefiles`
- module search path must be customized using shell profile script
- SH-like shells load `/etc/profile.d/z00_lmod.sh`
- CSH-like shells load `/etc/profile.d/z00_lmod.csh`
- EPEL needed

environment-modules:
- default module directory (used by other OS packages) is `/etc/modulefiles`
- module search path must be customized using shell profile script
- SH-like shells load `/etc/profile.d/modules.sh`
- CSH-like shells load `/etc/profile.d/modules.csh`
- in main OS repositories (i.e., no EPEL needed)

The two packages *do not conflict*, so both can be installed at the same time.
