#!/usr/bin/env python3
import sys
from github_api import GitHubApiError, analyze_developer, fetch_user_parallel, parse_username

def main():
    if len(sys.argv) < 2:
        print("ERROR: Missing username. Usage: github_roast.py <username>")
        sys.exit(1)

    try:
        username = parse_username(sys.argv[1])
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    try:
        profile, repos, events = fetch_user_parallel(username)
    except GitHubApiError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    if not profile:
        print(f"ERROR: GitHub user '{username}' not found.")
        sys.exit(1)

    stats = analyze_developer(repos, events)

    print(f"=== ROAST TARGET: @{username} ===")
    print(f"Stars: {stats['total_stars']} | Original Repos: {stats['original_count']} | Forks: {stats['fork_count']}")
    
    if stats['fork_count'] > stats['original_count'] and stats['fork_count'] > 3:
        print("AMMUNITION: FORK FARMER. More forking than creating. Zero original thoughts.")
    if stats['total_stars'] == 0:
        print("AMMUNITION: ZERO STARS. Even bots get more love.")
        
    # (Add the rest of your print statements here)
    print("\n=== ROAST INSTRUCTIONS ===")
    print(f"Write a SHORT BRUTAL roast of @{username}. 3-5 sentences MAX.")

if __name__ == "__main__":
    main()
