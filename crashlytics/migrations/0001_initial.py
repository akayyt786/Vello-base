"""Initial migration for the crashlytics app."""

import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        # ------------------------------------------------------------------ #
        # 1. CrashGroup                                                        #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='CrashGroup',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('signature', models.CharField(db_index=True, max_length=512)),
                ('title', models.CharField(max_length=512)),
                ('exception_type', models.CharField(max_length=255)),
                ('first_seen_at', models.DateTimeField()),
                ('last_seen_at', models.DateTimeField(db_index=True)),
                ('occurrence_count', models.PositiveIntegerField(default=0)),
                ('affected_users_count', models.PositiveIntegerField(default=0)),
                ('is_resolved', models.BooleanField(db_index=True, default=False)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='crash_groups',
                    to='core.project',
                )),
            ],
            options={
                'db_table': 'crashlytics_crash_group',
                'ordering': ['-last_seen_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='crashgroup',
            unique_together={('project', 'signature')},
        ),
        migrations.AddIndex(
            model_name='crashgroup',
            index=models.Index(
                fields=['project', 'is_resolved'],
                name='crash_grp_proj_resolved_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='crashgroup',
            index=models.Index(
                fields=['project', 'last_seen_at'],
                name='crash_grp_proj_last_seen_idx',
            ),
        ),

        # ------------------------------------------------------------------ #
        # 2. CrashReport (depends on CrashGroup)                              #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='CrashReport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user_id', models.CharField(blank=True, db_index=True, max_length=255)),
                ('session_id', models.CharField(blank=True, max_length=128)),
                ('platform', models.CharField(
                    choices=[
                        ('android', 'Android'),
                        ('ios', 'iOS'),
                        ('web', 'Web'),
                        ('flutter', 'Flutter'),
                    ],
                    default='android',
                    max_length=16,
                )),
                ('app_version', models.CharField(blank=True, max_length=64)),
                ('os_version', models.CharField(blank=True, max_length=64)),
                ('device_model', models.CharField(blank=True, max_length=128)),
                ('exception_type', models.CharField(max_length=255)),
                ('exception_message', models.TextField(blank=True)),
                ('stack_trace', models.TextField()),
                ('fatal', models.BooleanField(default=True)),
                ('breadcrumbs', models.JSONField(default=list)),
                ('custom_keys', models.JSONField(default=dict)),
                ('occurred_at', models.DateTimeField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='crash_reports',
                    to='core.project',
                )),
                ('group', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reports',
                    to='crashlytics.crashgroup',
                )),
            ],
            options={
                'db_table': 'crashlytics_crash_report',
                'ordering': ['-occurred_at'],
            },
        ),
        migrations.AddIndex(
            model_name='crashreport',
            index=models.Index(
                fields=['project', 'occurred_at'],
                name='crash_rpt_proj_occurred_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='crashreport',
            index=models.Index(
                fields=['project', 'user_id'],
                name='crash_rpt_proj_user_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='crashreport',
            index=models.Index(
                fields=['project', 'app_version'],
                name='crash_rpt_proj_version_idx',
            ),
        ),

        # ------------------------------------------------------------------ #
        # 3. PerformanceTrace                                                  #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='PerformanceTrace',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('trace_name', models.CharField(db_index=True, max_length=255)),
                ('duration_ms', models.PositiveIntegerField()),
                ('user_id', models.CharField(blank=True, max_length=255)),
                ('session_id', models.CharField(blank=True, max_length=128)),
                ('platform', models.CharField(
                    choices=[
                        ('android', 'Android'),
                        ('ios', 'iOS'),
                        ('web', 'Web'),
                    ],
                    default='web',
                    max_length=16,
                )),
                ('app_version', models.CharField(blank=True, max_length=64)),
                ('custom_attributes', models.JSONField(default=dict)),
                ('custom_metrics', models.JSONField(default=dict)),
                ('occurred_at', models.DateTimeField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='performance_traces',
                    to='core.project',
                )),
            ],
            options={
                'db_table': 'crashlytics_perf_trace',
                'ordering': ['-occurred_at'],
            },
        ),
        migrations.AddIndex(
            model_name='performancetrace',
            index=models.Index(
                fields=['project', 'trace_name'],
                name='perf_trace_proj_name_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='performancetrace',
            index=models.Index(
                fields=['project', 'occurred_at'],
                name='perf_trace_proj_occurred_idx',
            ),
        ),

        # ------------------------------------------------------------------ #
        # 4. NetworkRequest                                                    #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='NetworkRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.CharField(max_length=2048)),
                ('http_method', models.CharField(max_length=8)),
                ('response_code', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('request_size_bytes', models.PositiveBigIntegerField(default=0)),
                ('response_size_bytes', models.PositiveBigIntegerField(default=0)),
                ('duration_ms', models.PositiveIntegerField()),
                ('user_id', models.CharField(blank=True, max_length=255)),
                ('session_id', models.CharField(blank=True, max_length=128)),
                ('platform', models.CharField(
                    choices=[
                        ('android', 'Android'),
                        ('ios', 'iOS'),
                        ('web', 'Web'),
                    ],
                    default='web',
                    max_length=16,
                )),
                ('app_version', models.CharField(blank=True, max_length=64)),
                ('occurred_at', models.DateTimeField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='network_requests',
                    to='core.project',
                )),
            ],
            options={
                'db_table': 'crashlytics_network_request',
                'ordering': ['-occurred_at'],
            },
        ),
        migrations.AddIndex(
            model_name='networkrequest',
            index=models.Index(
                fields=['project', 'occurred_at'],
                name='net_req_proj_occurred_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='networkrequest',
            index=models.Index(
                fields=['project', 'response_code'],
                name='net_req_proj_resp_code_idx',
            ),
        ),
    ]
