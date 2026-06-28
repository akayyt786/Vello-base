"""Initial migration for functions app."""

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CloudFunction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('trigger_type', models.CharField(
                    choices=[
                        ('http', 'HTTP (callable via REST)'),
                        ('on_create', 'Document Created'),
                        ('on_update', 'Document Updated'),
                        ('on_delete', 'Document Deleted'),
                        ('scheduled', 'Scheduled (cron)'),
                        ('on_storage', 'Storage Object Event'),
                        ('on_auth', 'Auth Event'),
                    ],
                    db_index=True, max_length=20,
                )),
                ('collection_path', models.TextField(blank=True)),
                ('endpoint_url', models.URLField(max_length=2048)),
                ('schedule', models.CharField(blank=True, max_length=100)),
                ('is_enabled', models.BooleanField(db_index=True, default=True)),
                ('timeout_seconds', models.IntegerField(default=30)),
                ('retry_count', models.IntegerField(default=0)),
                ('secret_header', models.CharField(blank=True, max_length=255)),
                ('extra_headers', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to='core.project',
                )),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'functions_cloudfunction',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='FunctionLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('trigger_data', models.JSONField(default=dict)),
                ('status', models.CharField(
                    choices=[
                        ('running', 'Running'),
                        ('success', 'Success'),
                        ('error', 'Error'),
                        ('timeout', 'Timeout'),
                    ],
                    db_index=True, default='running', max_length=20,
                )),
                ('response_status', models.IntegerField(blank=True, null=True)),
                ('response_body', models.TextField(blank=True)),
                ('duration_ms', models.IntegerField(blank=True, null=True)),
                ('error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('function', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='logs',
                    to='functions.cloudfunction',
                )),
            ],
            options={
                'db_table': 'functions_log',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='cloudfunction',
            constraint=models.UniqueConstraint(
                fields=['project', 'name'],
                name='unique_function_per_project',
            ),
        ),
        migrations.AddIndex(
            model_name='cloudfunction',
            index=models.Index(fields=['project', 'trigger_type'], name='fn_project_trigger_idx'),
        ),
        migrations.AddIndex(
            model_name='cloudfunction',
            index=models.Index(
                fields=['project', 'trigger_type', 'collection_path'],
                name='fn_project_trigger_col_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='functionlog',
            index=models.Index(fields=['function', 'status'], name='fnlog_function_status_idx'),
        ),
        migrations.AddIndex(
            model_name='functionlog',
            index=models.Index(fields=['function', 'created_at'], name='fnlog_function_created_idx'),
        ),
    ]
