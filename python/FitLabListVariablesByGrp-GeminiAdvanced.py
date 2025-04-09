import requests
import os
import json

def find_vault_url_no_gitlab_lib(gitlab_url, private_token, search_string="your_search_string"):
    """
    Examines GitLab groups and projects for a specific string within the VAULT_URL variable,
    without using the python-gitlab library.

    Args:
        gitlab_url: The URL of your GitLab instance.
        private_token: Your GitLab private access token.
        search_string: The string to search for within the VAULT_URL variable.

    Returns:
        A list of dictionaries, each containing information about a matching variable.
    """

    results = []
    headers = {"PRIVATE-TOKEN": private_token}

    def process_project(project, group_path=""):
        """Processes a project and its variables."""
        project_id = project.get("id")
        variables_url = f"{gitlab_url}/api/v4/projects/{project_id}/variables"
        try:
            response = requests.get(variables_url, headers=headers)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            variables = response.json()
            for var in variables:
                if var.get("key") == "VAULT_URL" and search_string in var.get("value", ""):
                    results.append({
                        "group": group_path,
                        "project": project.get("path_with_namespace"),
                        "variable_name": var.get("key"),
                        "variable_value": var.get("value"),
                    })

        except requests.exceptions.RequestException as e:
            print(f"Error getting variables for project {project.get('path_with_namespace')}: {e}")

    def process_group(group, parent_path=""):
        """Processes a group, its projects, and sub-groups."""
        group_path = f"{parent_path}/{group.get('path')}" if parent_path else group.get('path')
        group_id = group.get("id")

        # Process projects
        projects_url = f"{gitlab_url}/api/v4/groups/{group_id}/projects?per_page=100" # increased page size
        try:
            projects = []
            page = 1
            while True:
              current_projects_url = projects_url + f"&page={page}"
              response = requests.get(current_projects_url, headers=headers)
              response.raise_for_status()
              current_page_projects = response.json()
              if not current_page_projects:
                break
              projects.extend(current_page_projects)
              page += 1

            for project in projects:
                process_project(project, group_path)

        except requests.exceptions.RequestException as e:
            print(f"Error getting projects for group {group.get('path')}: {e}")

        # Process subgroups
        subgroups_url = f"{gitlab_url}/api/v4/groups/{group_id}/subgroups?per_page=100" #increased page size
        try:
            subgroups = []
            page = 1
            while True:
              current_subgroups_url = subgroups_url + f"&page={page}"
              response = requests.get(current_subgroups_url, headers=headers)
              response.raise_for_status()
              current_page_subgroups = response.json()
              if not current_page_subgroups:
                break
              subgroups.extend(current_page_subgroups)
              page += 1

            for subgroup in subgroups:
                process_group(subgroup, group_path)

        except requests.exceptions.RequestException as e:
            print(f"Error getting subgroups for group {group.get('path')}: {e}")

    # Process top-level groups
    groups_url = f"{gitlab_url}/api/v4/groups?per_page=100" # increased page size
    try:
        top_level_groups = []
        page = 1
        while True:
            current_groups_url = groups_url + f"&page={page}"
            response = requests.get(current_groups_url, headers=headers)
            response.raise_for_status()
            current_page_groups = response.json()
            if not current_page_groups:
                break
            top_level_groups.extend(current_page_groups)
            page += 1

        for group in top_level_groups:
            process_group(group)

    except requests.exceptions.RequestException as e:
        print(f"Error getting top-level groups: {e}")

    # Process top level projects
    top_level_projects_url = f"{gitlab_url}/api/v4/projects?top_level_only=true&per_page=100"
    try:
      top_level_projects = []
      page = 1
      while True:
        current_projects_url = top_level_projects_url + f"&page={page}"
        response = requests.get(current_projects_url, headers=headers)
        response.raise_for_status()
        current_page_projects = response.json()
        if not current_page_projects:
          break
        top_level_projects.extend(current_page_projects)
        page += 1
      for project in top_level_projects:
        process_project(project)
    except requests.exceptions.RequestException as e:
        print(f"Error getting top-level projects: {e}")

    return results

if __name__ == "__main__":
    gitlab_url = os.environ.get("GITLAB_URL", "https://your.gitlab.com")
    private_token = os.environ.get("GITLAB_TOKEN", "your_private_token")
    search_string = "your_string_to_search"

    if not private_token:
        print("Error: GITLAB_TOKEN environment variable is not set.")
        exit(1)
    if not gitlab_url:
        print("Error: GITLAB_URL environment variable is not set.")
        exit(1)

    results = find_vault_url_no_gitlab_lib(gitlab_url, private_token, search_string)

    if results:
        for result in results:
            print(f"Group: {result['group']}")
            print(f"Project: {result['project']}")
            print(f"Variable Name: {result['variable_name']}")
            print(f"Variable Value: {result['variable_value']}")
            print("-" * 20)
    else:
        print(f"No variables with VAULT_URL containing '{search_string}' found.")