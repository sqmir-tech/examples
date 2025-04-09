import requests
import os
import sys
import time

# --- Configuration ---
# Your GitLab instance URL (e.g., "https://gitlab.com" or your self-hosted URL)
GITLAB_URL = "https://gitlab.com"
# Your Personal Access Token (PAT) with 'api' scope
# BEST PRACTICE: Store this as an environment variable, e.g., GITLAB_PAT
ACCESS_TOKEN = os.environ.get("GITLAB_PAT")
# The variable name you are looking for
SEARCH_VARIABLE_NAME = "VAULT_URL"
# The specific string you want to find within the VAULT_URL value
SPECIAL_STRING = "your_special_string_here" # <--- CHANGE THIS
# Optional: Delay between API calls to avoid rate limiting (seconds)
API_DELAY = 0.1
# --- End Configuration ---

if not ACCESS_TOKEN:
    print("Error: GITLAB_PAT environment variable not set.")
    sys.exit(1)

if SPECIAL_STRING == "your_special_string_here":
     print("Warning: Please change the 'SPECIAL_STRING' variable in the script.")
     # You might want to exit here depending on your workflow
     # sys.exit(1)


headers = {"PRIVATE-TOKEN": ACCESS_TOKEN}
found_variables = []

def check_variable(variable_data):
    """Checks if the variable matches the search criteria."""
    return (variable_data.get('key') == SEARCH_VARIABLE_NAME and
            SPECIAL_STRING in variable_data.get('value', '')) # Safely handle missing 'value'

def get_paginated_data(url):
    """Handles GitLab API pagination."""
    results = []
    next_url = url
    while next_url:
        try:
            time.sleep(API_DELAY) # Be polite to the API
            # print(f"Fetching: {next_url}") # Uncomment for debug
            response = requests.get(next_url, headers=headers, timeout=30)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            results.extend(response.json())
            # Check for 'next' link in headers
            next_url = response.links.get('next', {}).get('url')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {next_url or url}: {e}")
            # Decide if you want to stop or continue on error
            break # Stop processing this specific list on error
    return results

def process_project(project_data, group_path):
    """Checks variables for a specific project."""
    project_id = project_data['id']
    project_path = project_data['path_with_namespace']
    print(f"  Checking project: {project_path}")

    variables_url = f"{GITLAB_URL}/api/v4/projects/{project_id}/variables"
    project_variables = get_paginated_data(variables_url)

    for var in project_variables:
        # Important: API might not return value for masked variables depending on permissions!
        # The check might only confirm the variable *exists* if value isn't returned.
        if 'value' not in var:
             print(f"    Warning: Variable '{var.get('key')}' in project {project_path} might be masked. Cannot check value content via API.")
             # If you *only* care if VAULT_URL exists, regardless of content, adjust logic here.
             # Example: if var.get('key') == SEARCH_VARIABLE_NAME: # Just check existence

        if check_variable(var):
            print(f"    FOUND Match in Project: {project_path}")
            found_variables.append({
                "group_path": group_path, # Group it belongs to
                "project_path": project_path,
                "level": "Project",
                "variable_name": var['key'],
                "value": var.get('value', '[Masked or Value Not Available]') # Handle potentially missing value
            })

def process_group(group_id, current_group_path):
    """Recursively checks group variables, projects, and subgroups."""
    print(f"Processing group: {current_group_path} (ID: {group_id})")

    # 1. Check Group-Level Variables
    group_vars_url = f"{GITLAB_URL}/api/v4/groups/{group_id}/variables"
    group_variables = get_paginated_data(group_vars_url)
    print(f"  Checking group-level variables for: {current_group_path}")
    for var in group_variables:
        if 'value' not in var:
             print(f"    Warning: Variable '{var.get('key')}' in group {current_group_path} might be masked. Cannot check value content via API.")

        if check_variable(var):
            print(f"    FOUND Match in Group: {current_group_path}")
            found_variables.append({
                "group_path": current_group_path,
                "project_path": "(Group Level)", # Indicate it's a group var
                "level": "Group",
                "variable_name": var['key'],
                "value": var.get('value', '[Masked or Value Not Available]')
            })

    # 2. Process Projects within this Group
    # include_subgroups=false ensures we only get projects *directly* in this group
    projects_url = f"{GITLAB_URL}/api/v4/groups/{group_id}/projects?include_subgroups=false&archived=false" # Exclude archived projects
    projects = get_paginated_data(projects_url)
    for project in projects:
        process_project(project, current_group_path) # Pass the group path for context

    # 3. Process Subgroups (Recursion)
    subgroups_url = f"{GITLAB_URL}/api/v4/groups/{group_id}/subgroups"
    subgroups = get_paginated_data(subgroups_url)
    for subgroup in subgroups:
        # Use subgroup's full_path for the next level of recursion
        process_group(subgroup['id'], subgroup['full_path'])

# --- Main Execution ---
print("Starting GitLab variable audit...")
print(f"Searching for variable '{SEARCH_VARIABLE_NAME}' containing '{SPECIAL_STRING}'")

# Fetch top-level groups user has access to
top_level_groups_url = f"{GITLAB_URL}/api/v4/groups?top_level_only=true"
top_level_groups = get_paginated_data(top_level_groups_url)

if not top_level_groups:
    print("No top-level groups found or accessible with the provided token.")
else:
    for group in top_level_groups:
        process_group(group['id'], group['full_path'])

# --- Output Results ---
print("\n--- Audit Complete ---")
if found_variables:
    print(f"Found {len(found_variables)} instance(s) of '{SEARCH_VARIABLE_NAME}' containing '{SPECIAL_STRING}':")
    # SECURITY WARNING: Be cautious printing sensitive values like VAULT_URL.
    # Consider logging to a secure file or just confirming existence instead of printing values.
    for item in found_variables:
        print(f"- Group: {item['group_path']}, Project: {item['project_path']}, Level: {item['level']}, Variable: {item['variable_name']}, Value: {item['value']}")
else:
    print(f"No variable named '{SEARCH_VARIABLE_NAME}' containing '{SPECIAL_STRING}' was found.")

print("--- End of Script ---")