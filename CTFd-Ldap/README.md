A plugin for CTFd that adds ldap support.

Simply replace the settings object in __init__.py with settings that correspond to the settings for your desired ldap server and you can now login via ldap, no registration required!

The ldap login is meant to replace the default user login system for CTFd. This plugin disables regular registration and oauth login. If you want to re-enable you just have to remove some lines from the code (read comments).