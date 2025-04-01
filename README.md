# Cloudflare cPanel Automation

This repository provides automation scripts for integrating Cloudflare with cPanel. It includes scripts to automatically add or remove domains in Cloudflare when accounts are created or deleted in cPanel. The integration is achieved through WHM hooks.

## Features

- Automatic Cloudflare Account Addition: Adds a domain to Cloudflare when a new cPanel account is created.
- Automatic Cloudflare Account Deletion: Removes a domain from Cloudflare when a cPanel account is terminated.
- WHM Hook Integration: Seamlessly integrates with WHM using cPanel hooks.

## Files

- `account_add.py` - Script to add a domain to Cloudflare when a cPanel account is created.
- `account_delete.py` - Script to remove a domain from Cloudflare when a cPanel account is deleted.

## Installation

### 1: Move Scripts to cPanel Hooks Directory /usr/local/cpanel/hooks

### 2: Set executable permission to the files

```bash
chmod +x /usr/local/cpanel/hooks/account_add.py
chmod +x /usr/local/cpanel/hooks/account_delete.py
```

### 3: Register Hooks in WHM

Use the `manage_hooks` command to register the scripts with cPanel.

Register Account Creation Hook

```bash
/usr/local/cpanel/bin/manage_hooks add script /usr/local/cpanel/hooks/account_add.py --event Account::Create --stage post
```

Register Account Deletion Hook

```bash
/usr/local/cpanel/bin/manage_hooks add script /usr/local/cpanel/hooks/account_add.py --event Account::Create --stage post
```

### 4: Verify Hook Installation

```bash
/usr/local/cpanel/bin/manage_hooks list
```

Ensure the scripts are listed under the appropriate events.

## Setting Database

Import `sql_structure.sql` file into your mysql database.

## Configuration (`.env`)

```bash
# Database
MYSQL_HOST=your_mysql_host
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=your_mysql_db
MYSQL_TABLE=your_mysql_table

# Cpanel configuration
CPANEL_API_TOKEN=your_cpanel_api_token
CPANEL_URL=https://your-cpanel-host
CPANEL_USERNAME=root

# Cloudflare configuration
API_TOKEN=cloudflare_api_token
API_ACCOUNT=cloudflare_account_id
CLOUDFLARE_ACCOUNT_EMAIL=cloudflare_email
```

## Testing

### Account creation

```bash
/scripts/wwwacct domain_here username_here password_here
```

### Account Deletion

```bash
/scripts/removeacct username_here
```

---

## Done
