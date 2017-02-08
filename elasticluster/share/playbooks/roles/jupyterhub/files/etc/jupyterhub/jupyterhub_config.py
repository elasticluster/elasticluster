# THIS FILE IS CONTROLLED BY ELASTICLUSTER
# local modifications will be overwritten
# the next time `elasticluster setup` is run!
#

#
# Configuration file for jupyterhub.
#

#------------------------------------------------------------------------------
# JupyterHub(Application) configuration
#------------------------------------------------------------------------------

## An Application for starting a Multi-User Jupyter Notebook server.

## Grant admin users permission to access single-user servers.
#
#  Users should be properly informed if this is enabled.
#c.JupyterHub.admin_access = False

## Class for authenticating users.
#
c.JupyterHub.authenticator_class = 'jupyterhub.auth.PAMAuthenticator'

## The base URL of the entire application
c.JupyterHub.base_url = '/'

## Whether to shutdown the proxy when the Hub shuts down.
#
#c.JupyterHub.cleanup_proxy = True

## Whether to shutdown single-user servers when the Hub shuts down.
#
#c.JupyterHub.cleanup_servers = True

## The config file to load
c.JupyterHub.config_file = '/etc/jupyterhub/jupyterhub_config.py'

## Number of days for a login cookie to be valid. Default is two weeks.
#
#c.JupyterHub.cookie_max_age_days = 14

## The cookie secret to use to encrypt cookies.
#
#  Loaded from the JPY_COOKIE_SECRET env variable by default.
c.JupyterHub.cookie_secret = open('/var/lib/jupyterhub/jupyterhub_cookie_secret', 'rb').read().strip()

## File in which to store the cookie secret.
c.JupyterHub.cookie_secret_file = 'jupyterhub_cookie_secret'

## The location of jupyterhub data files (e.g. /usr/local/share/jupyter/hub)
c.JupyterHub.data_files_path = '/opt/anaconda3/share/jupyter/hub'

## Include any kwargs to pass to the database connection. See
#  sqlalchemy.create_engine for details.
#c.JupyterHub.db_kwargs = {}

## url for the database. e.g. `sqlite:///jupyterhub.sqlite`
c.JupyterHub.db_url = 'sqlite:////var/lib/jupyterhub/jupyterhub.sqlite'

## show debug output in configurable-http-proxy
#c.JupyterHub.debug_proxy = False

## File to write PID Useful for daemonizing jupyterhub.
c.JupyterHub.pid_file = '/var/run/jupyterhub.pid'

## The public facing port of the proxy
c.JupyterHub.port = 443

## The Proxy Auth token.
#
#  Loaded from the CONFIGPROXY_AUTH_TOKEN env variable by default.
c.JupyterHub.proxy_auth_token = open('/var/lib/jupyterhub/jupyterhub_proxy_auth_token', 'rb').read().strip()

## The command to start the http proxy.
#
#  Only override if configurable-http-proxy is not on your PATH
c.JupyterHub.proxy_cmd = ['/usr/local/lib/node_modules/configurable-http-proxy/bin/configurable-http-proxy']

## Dict of token:servicename to be loaded into the database.
#
#  Allows ahead-of-time generation of API tokens for use by externally managed
#  services.
#c.JupyterHub.service_tokens = {}

## List of service specification dictionaries.
#
#  A service
#
#  For instance::
#
#      services = [
#          {
#              'name': 'cull_idle',
#              'command': ['/path/to/cull_idle_servers.py'],
#          },
#          {
#              'name': 'formgrader',
#              'url': 'http://127.0.0.1:1234',
#              'token': 'super-secret',
#              'environment':
#          }
#      ]
#c.JupyterHub.services = []

## The class to use for spawning single-user servers.
#
c.JupyterHub.spawner_class = 'jupyterhub.spawner.LocalProcessSpawner'

## Path to SSL certificate file for the public facing interface of the proxy
#
#  Use with ssl_key
c.JupyterHub.ssl_cert = '/etc/jupyterhub/jupyterhub.crt.pem'

## Path to SSL key file for the public facing interface of the proxy
#
#  Use with ssl_cert
c.JupyterHub.ssl_key = '/etc/jupyterhub/jupyterhub.key.pem'

#------------------------------------------------------------------------------
# Spawner(LoggingConfigurable) configuration
#------------------------------------------------------------------------------

## The command used for starting the single-user server.
#
#  Provide either a string or a list containing the path to the startup script
#  command. Extra arguments, other than this path, should be provided via `args`.
#
#  This is usually set if you want to start the single-user server in a different
#  python environment (with virtualenv/conda) than JupyterHub itself.
#
#  Some spawners allow shell-style expansion here, allowing you to use
#  environment variables. Most, including the default, do not. Consult the
#  documentation for your spawner to verify!
c.Spawner.cmd = ['/opt/anaconda3/bin/jupyterhub-singleuser']

## Minimum number of cpu-cores a single-user notebook server is guaranteed to
#  have available.
#
#  If this value is set to 0.5, allows use of 50% of one CPU. If this value is
#  set to 2, allows use of up to 2 CPUs.
#
#  Note that this needs to be supported by your spawner for it to work.
#c.Spawner.cpu_guarantee = None

## Maximum number of cpu-cores a single-user notebook server is allowed to use.
#
#  If this value is set to 0.5, allows use of 50% of one CPU. If this value is
#  set to 2, allows use of up to 2 CPUs.
#
#  The single-user notebook server will never be scheduled by the kernel to use
#  more cpu-cores than this. There is no guarantee that it can access this many
#  cpu-cores.
#
#  This needs to be supported by your spawner for it to work.
#c.Spawner.cpu_limit = None

## Enable debug-logging of the single-user server
#c.Spawner.debug = False

## The URL the single-user server should start in.
#
#  `{username}` will be expanded to the user's username
#
#  Example uses:
#  - You can set `notebook_dir` to `/` and `default_url` to `/home/{username}` to allow people to
#    navigate the whole filesystem from their notebook, but still start in their home directory.
#  - You can set this to `/lab` to have JupyterLab start by default, rather than Jupyter Notebook.
#c.Spawner.default_url = ''

## Disable per-user configuration of single-user servers.
#
#  When starting the user's single-user server, any config file found in the
#  user's $HOME directory will be ignored.
#
#  Note: a user could circumvent this if the user modifies their Python
#  environment, such as when they have their own conda environments / virtualenvs
#  / containers.
#c.Spawner.disable_user_config = False

## Whitelist of environment variables for the single-user server to inherit from
#  the JupyterHub process.
#
#  This whitelist is used to ensure that sensitive information in the JupyterHub
#  process's environment (such as `CONFIGPROXY_AUTH_TOKEN`) is not passed to the
#  single-user server's process.
#c.Spawner.env_keep = ['PATH', 'PYTHONPATH', 'CONDA_ROOT', 'CONDA_DEFAULT_ENV', 'VIRTUAL_ENV', 'LANG', 'LC_ALL']

## Extra environment variables to set for the single-user server's process.
#
#  Environment variables that end up in the single-user server's process come from 3 sources:
#    - This `environment` configurable
#    - The JupyterHub process' environment variables that are whitelisted in `env_keep`
#    - Variables to establish contact between the single-user notebook and the hub (such as JUPYTERHUB_API_TOKEN)
#
#  The `enviornment` configurable should be set by JupyterHub administrators to
#  add installation specific environment variables. It is a dict where the key is
#  the name of the environment variable, and the value can be a string or a
#  callable. If it is a callable, it will be called with one parameter (the
#  spawner instance), and should return a string fairly quickly (no blocking
#  operations please!).
#
#  Note that the spawner class' interface is not guaranteed to be exactly same
#  across upgrades, so if you are using the callable take care to verify it
#  continues to work after upgrades!
#c.Spawner.environment = {}

## Timeout (in seconds) before giving up on a spawned HTTP server
#
#  Once a server has successfully been spawned, this is the amount of time we
#  wait before assuming that the server is unable to accept connections.
#c.Spawner.http_timeout = 30

## The IP address (or hostname) the single-user server should listen on.
#
#  The JupyterHub proxy implementation should be able to send packets to this
#  interface.
#c.Spawner.ip = '127.0.0.1'

## Minimum number of bytes a single-user notebook server is guaranteed to have
#  available.
#
#  Allows the following suffixes:
#    - K -> Kilobytes
#    - M -> Megabytes
#    - G -> Gigabytes
#    - T -> Terabytes
#
#  This needs to be supported by your spawner for it to work.
#c.Spawner.mem_guarantee = None

## Maximum number of bytes a single-user notebook server is allowed to use.
#
#  Allows the following suffixes:
#    - K -> Kilobytes
#    - M -> Megabytes
#    - G -> Gigabytes
#    - T -> Terabytes
#
#  If the single user server tries to allocate more memory than this, it will
#  fail. There is no guarantee that the single-user notebook server will be able
#  to allocate this much memory - only that it can not allocate more than this.
#
#  This needs to be supported by your spawner for it to work.
#c.Spawner.mem_limit = None

## Path to the notebook directory for the single-user server.
#
#  The user sees a file listing of this directory when the notebook interface is
#  started. The current interface does not easily allow browsing beyond the
#  subdirectories in this directory's tree.
#
#  `~` will be expanded to the home directory of the user, and {username} will be
#  replaced with the name of the user.
#
#  Note that this does *not* prevent users from accessing files outside of this
#  path! They can do so with many other means.
c.Spawner.notebook_dir = '~'

#------------------------------------------------------------------------------
# Authenticator(LoggingConfigurable) configuration
#------------------------------------------------------------------------------

## Base class for implementing an authentication provider for JupyterHub

## Set of users that will have admin rights on this JupyterHub.
#
#  Admin users have extra privilages:
#   - Use the admin panel to see list of users logged in
#   - Add / remove users in some authenticators
#   - Restart / halt the hub
#   - Start / stop users' single-user servers
#   - Can access each individual users' single-user server (if configured)
#
#  Admin access should be treated the same way root access is.
#
#  Defaults to an empty set, in which case no user has admin access.
#c.Authenticator.admin_users = set()

## Whitelist of usernames that are allowed to log in.
#
#  Use this with supported authenticators to restrict which users can log in.
#  This is an additional whitelist that further restricts users, beyond whatever
#  restrictions the authenticator has in place.
#
#  If empty, does not perform any additional restriction.
#c.Authenticator.whitelist = set()

#------------------------------------------------------------------------------
# LocalAuthenticator(Authenticator) configuration
#------------------------------------------------------------------------------

## Base class for Authenticators that work with local Linux/UNIX users
#
#  Checks for local users, and can attempt to create them if they exist.

## The command to use for creating users as a list of strings
#
#  For each element in the list, the string USERNAME will be replaced with the
#  user's username. The username will also be appended as the final argument.
#
#  For Linux, the default value is:
#
#      ['adduser', '-q', '--gecos', '""', '--disabled-password']
#
#  To specify a custom home directory, set this to:
#
#      ['adduser', '-q', '--gecos', '""', '--home', '/customhome/USERNAME', '--
#  disabled-password']
#
#  This will run the command:
#
#      adduser -q --gecos "" --home /customhome/river --disabled-password river
#
#  when the user 'river' is created.
#c.LocalAuthenticator.add_user_cmd = []

## If set to True, will attempt to create local system users if they do not exist
#  already.
#
#  Supports Linux and BSD variants only.
c.LocalAuthenticator.create_system_users = False

## Whitelist all users from this UNIX group.
#
#  This makes the username whitelist ineffective.
#c.LocalAuthenticator.group_whitelist = set()

#------------------------------------------------------------------------------
# PAMAuthenticator(LocalAuthenticator) configuration
#------------------------------------------------------------------------------

## Authenticate local UNIX users with PAM

## The text encoding to use when communicating with PAM
#c.PAMAuthenticator.encoding = 'utf8'

## Whether to open a new PAM session when spawners are started.
#
#  This may trigger things like mounting shared filsystems, loading credentials,
#  etc. depending on system configuration, but it does not always work.
#
#  If any errors are encountered when opening/closing PAM sessions, this is
#  automatically set to False.
#c.PAMAuthenticator.open_sessions = True

## The name of the PAM service to use for authentication
#c.PAMAuthenticator.service = 'login'
