# Data migration: Create default security policies for new projects

from django.db import migrations


def create_default_policies(apps, schema_editor):
    """
    Create default policies for Phase 1 MVP.

    Default read rule: Allow if authenticated
    Default write rule: Allow if owner
    Default delete rule: Allow if owner or admin
    """
    SecurityPolicy = apps.get_model('rules', 'SecurityPolicy')
    Project = apps.get_model('core', 'Project')

    # Default policies to create for each project
    default_policies = [
        {
            'collection': 'documents',
            'rule_type': 'read',
            'condition_json': {
                'operator': 'and',
                'conditions': [
                    {
                        'type': 'auth_check',
                        'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                    }
                ]
            },
            'active': True,
            'priority': 100,
            'description': 'Default: Allow read if authenticated'
        },
        {
            'collection': 'documents',
            'rule_type': 'write',
            'condition_json': {
                'operator': 'and',
                'conditions': [
                    {
                        'type': 'auth_check',
                        'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                    },
                    {
                        'type': 'owner_check',
                        'value': {'field': 'owner_id'}
                    }
                ]
            },
            'active': True,
            'priority': 100,
            'description': 'Default: Allow write if owner'
        },
        {
            'collection': 'documents',
            'rule_type': 'delete',
            'condition_json': {
                'operator': 'and',
                'conditions': [
                    {
                        'type': 'auth_check',
                        'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                    },
                    {
                        'type': 'owner_check',
                        'value': {'field': 'owner_id'}
                    }
                ]
            },
            'active': True,
            'priority': 100,
            'description': 'Default: Allow delete if owner'
        },
    ]

    # For Phase 1 MVP, only create defaults for existing projects
    # In production, you'd create these per-project on project creation
    for project in Project.objects.all():
        for policy_template in default_policies:
            # Only create if not already exists
            existing = SecurityPolicy.objects.filter(
                project=project,
                collection=policy_template['collection'],
                rule_type=policy_template['rule_type'],
            ).exists()

            if not existing:
                SecurityPolicy.objects.create(
                    project=project,
                    collection=policy_template['collection'],
                    rule_type=policy_template['rule_type'],
                    condition_json=policy_template['condition_json'],
                    active=policy_template['active'],
                    priority=policy_template['priority'],
                    description=policy_template['description'],
                )


def remove_default_policies(apps, schema_editor):
    """Reverse migration: remove default policies."""
    SecurityPolicy = apps.get_model('rules', 'SecurityPolicy')
    SecurityPolicy.objects.filter(
        description__startswith='Default:'
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('rules', '0001_initial'),
        ('core', '0002_document'),
    ]

    operations = [
        migrations.RunPython(create_default_policies, remove_default_policies),
    ]
