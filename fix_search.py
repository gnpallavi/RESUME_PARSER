# Read app.py
with open('app.py', 'r') as f:
    content = f.read()

# Pattern to find and replace - use simple string
old = "    query = request.args.get('query', '').strip()\n    selected_skill = request.args.get('skill', '').strip()\n    \n    # Debug print statements\n    print('Selected Skill:', selected_skill)\n    \n    # Get all candidates from database with search and skill filter\n    # If no search input is given, it will return all candidates\n    candidates_list, total_count = database.get_all_candidates(\n        search=query,\n        skill=selected_skill,\n        sort_by='upload_date',\n        order='desc',\n        page=1,\n        per_page=50\n    )\n    \n    # Debug print statement to check number of results\n    print('Results count:', len(candidates_list))\n    \n    return render_template(\n        'search.html',\n        candidates=candidates_list,\n        search_query=query,\n        skill_filter=selected_skill,\n        total_count=total_count\n    )"

new = "    query = request.args.get('query', '').strip()\n    selected_skill = request.args.get('skill', '').strip()\n    \n    # Get all candidates from database (without any filters first)\n    all_candidates_data, total_candidates = database.get_all_candidates(\n        search='',\n        sort_by='upload_date',\n        order='desc',\n        page=1,\n        per_page=1000\n    )\n    \n    # Generate unique skills list from all candidates in database\n    skill_set = set()\n    for candidate in all_candidates_data:\n        if candidate.get('skills'):\n            for skill in candidate.get('skills').split(','):\n                skill_set.add(skill.strip().lower())\n    \n    skills_list = sorted(skill_set)\n    \n    # Filter candidates based on query and skill\n    candidates_query = all_candidates_data\n    \n    if query:\n        # Case-insensitive partial matching for name or email\n        candidates_query = [c for c in candidates_query \n            if (c.get('name') and query.lower() in c.get('name').lower()) or \n               (c.get('email') and query.lower() in c.get('email').lower())]\n    \n    if selected_skill and selected_skill != 'All Skills':\n        # Case-insensitive partial matching for skills\n        candidates_query = [c for c in candidates_query \n            if c.get('skills') and selected_skill.lower() in c.get('skills').lower()]\n    \n    results = candidates_query\n    \n    # Debug print statements\n    print('Selected Skill:', selected_skill)\n    print('Results count:', len(results))\n    \n    return render_template(\n        'search.html',\n        candidates=results,\n        search_query=query,\n        skill_filter=selected_skill,\n        all_skills=skills_list,\n        total_count=len(results)\n    )"

content = content.replace(old, new)

with open('app.py', 'w') as f:
    f.write(content)

print('Done')
