import pynetbox
import os
import sys

# --- Configuration ---
# Best practice: Use environment variables for sensitive info like tokens.
# Or replace placeholders directly (less secure).
NETBOX_URL = os.getenv('NETBOX_URL', 'YOUR_NETBOX_URL') # e.g., 'http://netbox.example.com'
NETBOX_TOKEN = os.getenv('NETBOX_TOKEN', 'YOUR_NETBOX_API_TOKEN')

# Input: Specify the prefix you want to get IPs from
TARGET_PREFIX = '192.168.1.0/24' # <--- CHANGE THIS TO YOUR DESIRED PREFIX

# Input: List of hostnames needing IP addresses
HOSTNAMES = [
    'webserver-prod-01',
    'dbserver-prod-01',
    'appserver-dev-05',
    'monitoring-server',
    # Add more hostnames as needed
]

# Optional: Disable SSL verification if using self-signed certs (use with caution)
DISABLE_SSL_VERIFY = False
# --- End Configuration ---

# --- Script Logic ---

def get_next_available_ips(nb_api, prefix_str, hostname_list):
    """
    Finds the next available IP address in NetBox for each hostname in the list.

    Args:
        nb_api: Initialized pynetbox API object.
        prefix_str: The IP prefix string (e.g., '192.168.1.0/24').
        hostname_list: A list of hostnames to find IPs for.

    Returns:
        A dictionary mapping hostnames to their proposed next available IP addresses
        or an error message string. Returns None if connection or prefix lookup fails.
    """
    assigned_ips = {}

    # 1. Find the Prefix object in NetBox
    try:
        prefix_obj = nb_api.ipam.prefixes.get(prefix=prefix_str)
        if not prefix_obj:
            print(f"Error: Prefix '{prefix_str}' not found in NetBox.", file=sys.stderr)
            return None
        print(f"Found Prefix: {prefix_obj.prefix} (ID: {prefix_obj.id})")
    except Exception as e:
        print(f"Error retrieving prefix '{prefix_str}' from NetBox: {e}", file=sys.stderr)
        return None

    # 2. Request the next available IP for each hostname
    print(f"\nAttempting to find the next {len(hostname_list)} available IP(s) in prefix {prefix_obj.prefix}...")
    for hostname in hostname_list:
        try:
            # Use the available-ips endpoint's create() method with an empty payload.
            # This tells NetBox to find and return the *next* available IP.
            # Note: This typically makes a POST request to /api/ipam/prefixes/{id}/available-ips/
            # It *doesn't* permanently assign the IP in this script, but NetBox calculates
            # the next available one based on current assignments.
            next_ip_data = prefix_obj.available_ips.create({}) # Returns a dict representing the IP

            if next_ip_data and 'address' in next_ip_data:
                ip_address_cidr = next_ip_data['address']
                ip_address = ip_address_cidr.split('/')[0] # Extract IP from CIDR format (e.g., '192.168.1.5/24' -> '192.168.1.5')
                assigned_ips[hostname] = ip_address
                print(f"  - Found next available IP: {ip_address} (for {hostname})")
            else:
                print(f"  - Warning: Could not retrieve next available IP for {hostname}. NetBox response: {next_ip_data}", file=sys.stderr)
                assigned_ips[hostname] = "Error retrieving IP"
                # Decide if you want to stop or continue if one fails
                # break # Uncomment to stop if one hostname fails

        except pynetbox.RequestError as e:
            # This often indicates the prefix is full or another API issue.
            error_message = f"Error finding next available IP (prefix '{prefix_str}' might be full?)"
            print(f"  - {error_message}: {e}", file=sys.stderr)
            assigned_ips[hostname] = error_message
            # Stop trying for more IPs if we hit a significant error like prefix full
            break
        except Exception as e:
            print(f"  - An unexpected error occurred requesting IP for {hostname}: {e}", file=sys.stderr)
            assigned_ips[hostname] = "Unexpected Error"
            break # Stop on unexpected errors

    return assigned_ips

# --- Main Execution ---
if __name__ == "__main__":
    if NETBOX_URL == 'YOUR_NETBOX_URL' or NETBOX_TOKEN == 'YOUR_NETBOX_API_TOKEN':
        print("Error: Please configure NETBOX_URL and NETBOX_TOKEN either in the script "
              "or as environment variables.", file=sys.stderr)
        sys.exit(1)

    # Initialize NetBox API connection
    try:
        nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
        if DISABLE_SSL_VERIFY:
            print("Warning: SSL verification disabled.", file=sys.stderr)
            import requests
            requests.packages.urllib3.disable_warnings()
            nb.http_session.verify = False

        print(f"Successfully connected to NetBox at {NETBOX_URL}")
    except Exception as e:
        print(f"Error connecting to NetBox: {e}", file=sys.stderr)
        sys.exit(1)

    # Get the proposed IP assignments
    ip_plan = get_next_available_ips(nb, TARGET_PREFIX, HOSTNAMES)

    # Print the results
    print("\n--- Proposed IP Address Plan ---")
    if ip_plan:
        max_len = max(len(h) for h in ip_plan.keys()) if ip_plan else 10
        for hostname, ip in ip_plan.items():
            print(f"Hostname: {hostname:<{max_len}}  -> Proposed IP: {ip}")
    else:
        print("Could not generate IP plan due to previous errors.")

    print("\nNote: This script only *identifies* the next available IPs.")
    print("It does *not* assign them in NetBox. You would need to extend the script")
    print("or use this list to manually or automatically assign them.")
