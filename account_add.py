#!/usr/bin/python3

import requests
import sys
import os
import json
import mysql.connector
from dotenv import load_dotenv
import concurrent.futures
from functools import partial

# Load environment variables from .env file
load_dotenv()

CPANEL_API_TOKEN = os.getenv("CPANEL_API_TOKEN")
CPANEL_HOST = os.getenv("CPANEL_URL")
CPANEL_USERNAME = os.getenv("CPANEL_USER_NAME")

def create_dns_record(zone_id, record):
    try:
        CLOUDFLARE_API_TOKEN = os.getenv("API_TOKEN")
        headers = {
            'Authorization': f'Bearer {CLOUDFLARE_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        response = requests.post(
            f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records',
            headers=headers,
            json=record
        )
        return record['name'], response.status_code, response.json()
    
    except Exception as e:
        raise Exception("Error: " + str(e)) 

def load_payload_data():
    try:    
        # Parse the input JSON directly
        input_data = sys.stdin.read()
        payload = json.loads(input_data)
        
        # Extract 'user' and 'domain' directly from the payload
        username = payload.get("data", {}).get("user", "Unknown User")
        domain = payload.get("data", {}).get("domain", "Unknown Domain")

        # Print the extracted user and domain
        print(f"User: {username}")
        print(f"Domain: {domain}")

        return {'username': username, 'domain': domain}

    except json.JSONDecodeError as e:
        raise Exception("Error: " + str(e))

def add_domain_to_cloudflare(db_connection,cursor, username, domain):
    try:
        CLOUDFLARE_API_TOKEN = os.getenv("API_TOKEN")
        CLOUDFLARE_API_ACCOUNT_ID = os.getenv("API_ACCOUNT")
        CLOUDFLARE_ACCOUNT_EMAIL = os.getenv("CLOUDFLARE_ACCOUNT_EMAIL")
        MYSQL_TABLE=os.getenv("MYSQL_TABLE")
        if not MYSQL_TABLE or not MYSQL_TABLE.isidentifier():
            raise ValueError("Invalid table name")
        url = "https://api.cloudflare.com/client/v4/zones"
        headers = {
            'Authorization': f'Bearer {CLOUDFLARE_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        data = {
            'name': domain,
            'account': {
                "id":CLOUDFLARE_API_ACCOUNT_ID
            }
        }
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        if response_data.get("success"):
            nameserver = response_data["result"]["name_servers"]
            ns1 = nameserver[0]
            ns2 = nameserver[1]
            cp_id = 2
            cp_user = username
            insert_query = f"INSERT INTO {MYSQL_TABLE} (domain, ns1, ns2, cf_account, cp_id, cp_user) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(insert_query, (domain, ns1, ns2, CLOUDFLARE_ACCOUNT_EMAIL, cp_id, cp_user))
            db_connection.commit()
            return response_data["result"]["id"]
        else:
            print("Failed to add domain to Cloudflare", response_data)
            raise Exception("Failed to add domain to Cloudflare") 

    except Exception as e:
        raise Exception("Error: " + str(e))

def get_cpanel_dns_records(username, domain):
    try:
        url = f"{CPANEL_HOST}/json-api/cpanel"
        headers = {
            'Authorization': f'whm {CPANEL_USERNAME}:{CPANEL_API_TOKEN}'
        }
        # Data for WHM API 1
        data = {
            'cpanel_jsonapi_user': username,  # The cPanel username
            'cpanel_jsonapi_module': 'ZoneEdit',
            'cpanel_jsonapi_func': 'fetchzone_records',
            'domain': domain  # The domain whose zone records you want to fetch
        }

        response = requests.post(url, headers=headers, data=data)
        decodedRes = response.json()
        if decodedRes and decodedRes.get('cpanelresult'):
            return response.json()
        else: 
            raise Exception("No cpanel account found!!!") 
        
    except Exception as e:
        raise Exception("Error: " + str(e))

def update_cloudflare_dns(records, zone_id):
    try:

        dns_records = []
        for record in records:
            dns_record = {}
            if record['type'] == 'A':
                dns_record = {
                    'type': 'A',
                    'name': record['name'],
                    'content': record['address'],
                    'ttl': int(record['ttl']),
                    'proxied': False
                }
            elif record['type'] == 'AAAA':
                dns_record = {
                    'type': 'AAAA',
                    'name': record['name'],
                    'content': record['address'],
                    'ttl': int(record['ttl']),
                    'proxied': False
                }
            elif record['type'] == 'CNAME':
                dns_record = {
                    'type': 'CNAME',
                    'name': record['name'],
                    'content': record['cname'].rstrip('.'),
                    'ttl': int(record['ttl'])
                }
            elif record['type'] == 'TXT':
                dns_record = {
                    'type': 'TXT',
                    'name': record['name'],
                    'content': record['txtdata'],
                    'ttl': int(record['ttl'])
                }
            elif record['type'] == 'MX':
                dns_record = {
                    'type': 'MX',
                    'name': record['name'],
                    'content': record['exchange'].rstrip('.'),
                    'priority': int(record['preference']),
                    'ttl': int(record['ttl'])
                }
            elif record['type'] == 'NS':
                dns_record = {
                    'type': 'NS',
                    'name': record['name'],
                    'content': record['nsdname'].rstrip('.'),
                    'ttl': int(record['ttl'])
                }
            elif record['type'] == 'SRV':
                dns_record = {
                    'type': 'SRV',
                    'name': record['name'],
                    'content': {
                        'priority': int(record['priority']),
                        'weight': int(record['weight']),
                        'port': int(record['port']),
                        'target': record['target'].rstrip('.')
                    },
                    'ttl': int(record['ttl'])
                }
            elif record['type'] == 'CAA':
                dns_record = {
                    'type': 'CAA',
                    'name': record['name'],
                    'content': {
                        'flags': int(record['flags']),
                        'tag': record['tag'],
                        'value': record['value']
                    },
                    'ttl': int(record['ttl'])
                }
            
            if dns_record:
                dns_records.append(dns_record)


        if len(dns_records) > 0:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # Use partial to bind account and zone_id to create_dns_record
                create_dns_record_with_args = partial(create_dns_record,  zone_id)
                
                # Execute the function in parallel with the provided DNS records
                results = executor.map(create_dns_record_with_args, dns_records)
            for name, status, response in results:
                if status == 200 and response.get("success"):
                    print(f"✅ Successfully created record: {name}")
                else:
                    print(f"❌ Failed to create record: {name}, Error: {response}")
        else:
            print("No Data")
        
    except Exception as e:
        raise Exception("Error: " + str(e))

def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE")
        )
        return connection
    except mysql.connector.Error as err:
        raise Exception("Error connecting to the database: " + str(err))

def main():
    try:
        # Load user data from the payload
        user_data = load_payload_data()
        username = user_data["username"]
        domain = user_data["domain"]

        # Establish connection to the database
        db_connection = connect_to_database()
        cursor = db_connection.cursor()

        # Get DNS records from cPanel
        print(f"Fetching DNS records for {domain} from cPanel...")
        dns_records = get_cpanel_dns_records(username, domain)

        # Add domain to cloudflare
        print(f"Adding domain {domain} to Cloudflare...")
        zone_id = add_domain_to_cloudflare( db_connection, cursor, username, domain)
        print(f"Cloudflare Zone ID: {zone_id}")

        # Update DNS records in Cloudflare
        print(f"Updating Cloudflare DNS for {domain}...")
        update_cloudflare_dns(dns_records['cpanelresult']['data'], zone_id)

        cursor.close()
        db_connection.close()
    except Exception as e:
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    main()