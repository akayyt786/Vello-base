"""Initial migration for analytics app."""

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
        # 1. Event                                                             #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user_id', models.CharField(
                    blank=True,
                    db_index=True,
                    help_text='Firebase UID or anonymous client-generated ID',
                    max_length=255,
                )),
                ('session_id', models.CharField(
                    blank=True,
                    db_index=True,
                    help_text='Session identifier grouping related events',
                    max_length=128,
                )),
                ('event_name', models.CharField(db_index=True, max_length=255)),
                ('event_params', models.JSONField(
                    blank=True,
                    default=dict,
                    help_text='Arbitrary key-value parameters attached to the event',
                )),
                ('platform', models.CharField(
                    choices=[
                        ('web', 'Web'),
                        ('android', 'Android'),
                        ('ios', 'iOS'),
                        ('server', 'Server'),
                    ],
                    db_index=True,
                    default='web',
                    max_length=32,
                )),
                ('app_version', models.CharField(blank=True, max_length=64)),
                ('device_id', models.CharField(blank=True, max_length=255)),
                ('geo_country', models.CharField(
                    blank=True,
                    help_text='ISO 3166-1 alpha-2 country code',
                    max_length=2,
                )),
                ('geo_city', models.CharField(blank=True, max_length=128)),
                ('occurred_at', models.DateTimeField(
                    db_index=True,
                    help_text='Client-side event timestamp',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='analytics_events',
                    to='core.project',
                )),
            ],
            options={
                'db_table': 'analytics_event',
                'ordering': ['-occurred_at'],
            },
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(
                fields=['project', 'event_name'],
                name='analytics_event_proj_name_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(
                fields=['project', 'user_id'],
                name='analytics_event_proj_user_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(
                fields=['project', 'occurred_at'],
                name='analytics_event_proj_occurred_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(
                fields=['project', 'session_id'],
                name='analytics_event_proj_session_idx',
            ),
        ),

        # ------------------------------------------------------------------ #
        # 2. UserProperty                                                       #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='UserProperty',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user_id', models.CharField(db_index=True, max_length=255)),
                ('name', models.CharField(max_length=64)),
                ('value', models.CharField(max_length=256)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='analytics_user_properties',
                    to='core.project',
                )),
            ],
            options={
                'db_table': 'analytics_user_property',
            },
        ),
        migrations.AlterUniqueTogether(
            name='userproperty',
            unique_together={('project', 'user_id', 'name')},
        ),

        # ------------------------------------------------------------------ #
        # 3. ConversionEvent                                                   #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='ConversionEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='analytics_conversion_events',
                    to='core.project',
                )),
            ],
            options={
                'db_table': 'analytics_conversion_event',
            },
        ),
        migrations.AlterUniqueTogether(
            name='conversionevent',
            unique_together={('project', 'event_name')},
        ),
    ]
