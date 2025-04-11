#!/bin/bash

# Set your GitLab instance URL and access token
GITLAB_URL="https://gitlab.com"   # Change if you're using a self-hosted GitLab
ACCESS_TOKEN="your_access_token_here"

# Common curl function with pagination
fetch_all_pages() {
    local url=$1
    local page=1
    local results="[]"

    while :; do
        response=$(curl --silent --header "PRIVATE-TOKEN: $ACCESS_TOKEN" "${url}&page=$page&per_page=100")
        count=$(echo "$response" | jq 'length')
        if [[ "$count" -eq 0 ]]; then
            break
        fi
        results=$(echo "$results $response" | jq -s 'add')
        ((page++))
    done

    echo "$results"
}

# Get all top-level groups
get_groups() {
    fetch_all_pages "$GITLAB_URL/api/v4/groups?top_level_only=true"
}

# Get all subgroups of a group
get_subgroups() {
    local group_id=$1
    fetch_all_pages "$GITLAB_URL/api/v4/groups/$group_id/subgroups?"
}

# Get all projects of a group
get_projects() {
    local group_id=$1
    fetch_all_pages "$GITLAB_URL/api/v4/groups/$group_id/projects?"
}

# Recursive function to explore groups and subgroups
explore_group() {
    local group_id=$1
    local prefix=$2

    group_info=$(curl --silent --header "PRIVATE-TOKEN: $ACCESS_TOKEN" "$GITLAB_URL/api/v4/groups/$group_id")
    group_name=$(echo "$group_info" | jq -r '.full_path')
    echo "${prefix}Group: $group_name"

    # List all projects in this group
    get_projects "$group_id" | jq -r ".[] | \"${prefix}  Project: \(.name_with_namespace)\""

    # List all subgroups recursively
    get_subgroups "$group_id" | jq -r '.[].id' | while read -r subgroup_id; do
        explore_group "$subgroup_id" "  $prefix"
    done
}

# Main execution
main() {
    echo "Fetching all top-level groups with pagination..."
    get_groups | jq -r '.[].id' | while read -r group_id; do
        explore_group "$group_id" ""
    done
}

main
