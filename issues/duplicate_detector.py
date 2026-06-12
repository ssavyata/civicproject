def find_duplicate_issue(new_issue):
    from .models import Issue

    # Only check against open issues of the same category
    existing_issues = Issue.objects.filter(
        category=new_issue.category,
        is_duplicate=False,
        status__in=['submitted', 'assigned', 'in_progress']
    ).exclude(id=new_issue.id)

    if not existing_issues.exists():
        return None

    new_location_words = set(new_issue.location.lower().split())
    new_description_words = set(new_issue.description.lower().split())

    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'there', 'near', 
                  'and', 'in', 'on', 'at', 'of', 'to', 'it', 'this', 'that'}

    for existing in existing_issues:
        score = 0

        # Check location similarity
        existing_location_words = set(existing.location.lower().split())
        location_overlap = new_location_words & existing_location_words
        if len(location_overlap) >= 1:
            score += 2

        # Check description similarity
        existing_description_words = set(existing.description.lower().split())
        description_overlap = (new_description_words & existing_description_words) - stop_words
        if len(description_overlap) >= 2:
            score += 2

        if score >= 2:
            return existing

    return None