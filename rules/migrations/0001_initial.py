# Generated migration for Security Rules models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SecurityPolicy',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('collection', models.CharField(db_index=True, max_length=255)),
                ('rule_type', models.CharField(
                    choices=[('read', 'Read'), ('write', 'Write'), ('delete', 'Delete')],
                    db_index=True,
                    max_length=20
                )),
                ('condition_json', models.JSONField(blank=True, default=dict)),
                ('active', models.BooleanField(db_index=True, default=True)),
                ('description', models.TextField(blank=True)),
                ('priority', models.IntegerField(db_index=True, default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL
                )),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to='core.project'
                )),
                ('updated_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'db_table': 'rules_security_policy',
                'ordering': ['-priority', 'collection', 'rule_type'],
                'unique_together': {('project', 'collection', 'rule_type', 'id')},
            },
        ),
        migrations.CreateModel(
            name='PolicyAuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('collection', models.CharField(db_index=True, max_length=255)),
                ('operation', models.CharField(
                    choices=[('read', 'Read'), ('write', 'Write'), ('delete', 'Delete')],
                    max_length=20
                )),
                ('document_id', models.CharField(blank=True, db_index=True, max_length=255)),
                ('allowed', models.BooleanField(default=False)),
                ('reason', models.TextField(blank=True)),
                ('matched_policies', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='policy_audit_logs',
                    to='core.project'
                )),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'db_table': 'rules_policy_audit_log',
            },
        ),
        migrations.AddIndex(
            model_name='securitypolicy',
            index=models.Index(fields=['project', 'collection', 'rule_type', 'active'], name='rules_secu_project_idx'),
        ),
        migrations.AddIndex(
            model_name='securitypolicy',
            index=models.Index(fields=['project', 'active', 'priority'], name='rules_secu_active_idx'),
        ),
        migrations.AddIndex(
            model_name='policyauditlog',
            index=models.Index(fields=['project', 'created_at'], name='rules_polic_project_idx'),
        ),
        migrations.AddIndex(
            model_name='policyauditlog',
            index=models.Index(fields=['user', 'created_at'], name='rules_polic_user_idx'),
        ),
        migrations.AddIndex(
            model_name='policyauditlog',
            index=models.Index(fields=['collection', 'operation'], name='rules_polic_coll_idx'),
        ),
    ]
