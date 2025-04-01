#!/usr/bin/python3

import requests
import sys
import os
import json
import mysql.connector
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

CPANEL_API_TOKEN = os.getenv("CPANEL_API_TOKEN")
CPANEL_HOST = os.getenv("CPANEL_URL")
CPANEL_USERNAME = os.getenv("CPANEL_USER_NAME")

def load_payload_data():
    # Read all input at once from stdin
    input_data = sys.stdin.read()

    # Parse the input JSON directly
    try:
        payload = json.loads(input_data)
        print(payload)
        # Extract 'user' and 'domain' directly from the payload
        user = payload.get("data", {}).get("user", "Unknown Domain")

        # Print the extracted user and domain
        print(f"User: {user}")

        return user

    except json.JSONDecodeError as e:
        raise Exception("Error: " + str(e))  

def get_domain_from_cpanel(user):
    try:
        # Headers for Authentication
        headers = {
            "Authorization": f"whm {CPANEL_USERNAME}:{CPANEL_API_TOKEN}"
        }

        # Step 1: Get Primary Domain
        url_primary = f"{CPANEL_HOST}/json-api/listaccts?api.version=1&search={user}&searchtype=user"
        response_primary = requests.get(url_primary, headers=headers)
        data_primary = response_primary.json()
        print("data_primary: ", data_primary)
        all_domains = []

        if data_primary.get("metadata", {}).get("result") == 1:
            accounts = data_primary.get("data", {}).get("acct", [])
            if accounts:
                for item in accounts:
                    if item.get("user", "") == user:
                        primary_domain = item.get("domain", "")
                        if primary_domain:
                            all_domains.append(primary_domain)
                        break

        # Step 2: Get Addon, Parked (Alias), and Subdomains
        url_summary = f"{CPANEL_HOST}/json-api/accountsummary?api.version=1&user={user}"
        response_summary = requests.get(url_summary, headers=headers)
        data_summary = response_summary.json()
        print("data_summary: ", data_summary)
        if data_summary.get("metadata", {}).get("result") == 1:
            extra_domains = data_summary.get("data", {}).get("domain", [])
            all_domains.extend(extra_domains)

        # Remove duplicates
        all_domains = list(set(all_domains))

        print(f"All domains for {user}: {all_domains}")
        return all_domains
        
    except Exception as e:
        raise Exception("Error: " + str(e))


def delete_domain_from_cloudflare(domain, db_connection, cursor):
    try:
        CLOUDFLARE_API_TOKEN = os.getenv("API_TOKEN")
        MYSQL_TABLE=os.getenv("MYSQL_TABLE")
        if not MYSQL_TABLE or not MYSQL_TABLE.isidentifier():
            raise ValueError("Invalid table name")
        # Get the Zone ID
        url = f"https://api.cloudflare.com/client/v4/zones?name={domain}"
        headers = {
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json",
        }

        response = requests.get(url, headers=headers)
        zone_data = response.json()

        if zone_data["success"] and zone_data["result"]:
            ZONE_ID = zone_data["result"][0]["id"]
            print(f"Zone ID for {domain}: {ZONE_ID}")

            # Step 2: Delete the Domain from Cloudflare
            delete_url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}"
            delete_response = requests.delete(delete_url, headers=headers)
            delete_data = delete_response.json()

            if delete_data["success"]:
                print(f"Successfully deleted domain {domain}")
                delete_query = f"DELETE FROM {MYSQL_TABLE} WHERE domain = %s"
                cursor.execute(delete_query, (domain,))
                db_connection.commit()
            else:
                print("Error deleting domain:", delete_data)
                raise Exception("Error deleting domain from cloudflare") 
        else:
            print("Error deleting domain:", delete_data)
            raise Exception("Error getting domain from cloudflare") 

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
        # Load the payload data from stdin
        user = load_payload_data()

        # Connect to the database
        db_connection = connect_to_database()
        cursor = db_connection.cursor()

        # Get the all domain of the user from cPanel
        domainsList = get_domain_from_cpanel(user)
        if domainsList and len(domainsList) > 0:
            for item in domainsList:
                domain = item
                # Delete domain from cloudflare
                print(f"Deleting domain {domain} from Cloudflare...")
                delete_domain_from_cloudflare(domain, db_connection, cursor)
                print(f"Deleted: {domain} from cloudflare")
        else:
            raise Exception("No domain found under this user")

        cursor.close()
        db_connection.close()

    except Exception as e:
        print("Error: ", e)
        sys.exit(1)

if __name__ == "__main__":
    main()