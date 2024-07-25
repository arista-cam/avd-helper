ServerRoot "/usr/local/apache2"
Listen 80
LoadModule mpm_event_module modules/mod_mpm_event.so
LoadModule authn_core_module modules/mod_authn_core.so
LoadModule authz_core_module modules/mod_authz_core.so
LoadModule dir_module modules/mod_dir.so
LoadModule autoindex_module modules/mod_autoindex.so
LoadModule unixd_module modules/mod_unixd.so
LoadModule alias_module modules/mod_alias.so
LoadModule rewrite_module modules/mod_rewrite.so
LoadModule mime_module modules/mod_mime.so
LoadModule log_config_module modules/mod_log_config.so

User daemon
Group daemon

ServerAdmin you@example.com
DocumentRoot "/usr/local/apache2/htdocs"
<Directory />
    AllowOverride none
    Require all denied
</Directory>
<Directory "/usr/local/apache2/htdocs">
    Options Indexes FollowSymLinks
    AllowOverride None
    Require all granted
</Directory>

<IfModule dir_module>
    DirectoryIndex index.html
</IfModule>

ErrorLog /proc/self/fd/2
LogLevel warn
CustomLog /proc/self/fd/1 common
IncludeOptional conf.d/*.conf