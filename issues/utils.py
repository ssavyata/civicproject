from .models import Department

CATEGORY_PRIORITY = {
    'pothole': 'high',
    'streetlight': 'high',
    'water': 'critical',
    'waste': 'medium',
    'other': 'low',
}

CRITICAL_KEYWORDS = [
    'accident',
    'emergency',
    'flood',
    'fire',
    'dangerous',
    'urgent',
    'blood',
    'injury',
]

HIGH_KEYWORDS = [
    'major',
    'severe',
    'broken',
    'overflow',
    'blockage',
    'dark',
    'smells',
]

def assign_department(issue):
    departments = Department.objects.all()
    for department in departments:
         if issue.category in department.categories:
              return department           
    return None

def determine_priority(issue):
    base_priority = CATEGORY_PRIORITY.get(issue.category, 'medium')
    description_lower = issue.description.lower()

    for keyword in CRITICAL_KEYWORDS:
        if keyword in description_lower:
            return 'critical'
        
    for keyword in HIGH_KEYWORDS:
        if keyword in description_lower:
            if base_priority in ['low', 'medium']:
                return 'high'
    return base_priority

def assign_issue(issue):
    department = assign_department(issue)
    if department:
        issue.assigned_department = department
        issue.status = 'assigned'

    issue.priority = determine_priority(issue)
    issue.save()

    return issue