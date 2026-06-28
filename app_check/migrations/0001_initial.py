"""Initial migration for app_check app."""

import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppCheckConfig',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('platform', models.CharField(
                    choices=[('web', 'Web'), ('android', 'Android'), ('ios', 'iOS')],
                    max_length=10,
                )),
                ('provider', models.CharField(
                    choices=[
                        ('recaptcha_v3', 'reCAPTCHA v3'),
                        ('recaptcha_enterprise', 'reCAPTCHA Enterprise'),
                        ('play_integrity', 'Play Integrity'),
                        ('device_check', 'DeviceCheck'),
                        ('debug', 'Debug (Development Only)'),
                    ],
                    max_length=30,
                )),
                ('config', models.JSONField(default=dict, help_text='Provider-specific config (site key, etc.)')),
                ('is_enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='app_check_configs',
                    to='core.project',
                )),
            ],
            options={
                'ordering': ['platform'],
                'unique_together': {('project', 'platform')},
            },
        ),
        migrations.CreateModel(
            name='AppCheckToken',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('token_hash', models.CharField(max_length=64, unique=True)),
                ('platform', models.CharField(
                    choices=[('web', 'Web'), ('android', 'Android'), ('ios', 'iOS')],
                    max_length=10,
                )),
                ('app_id', models.CharField(blank=True, max_length=255)),
                ('is_revoked', models.BooleanField(default=False)),
                ('expires_at', models.DateTimeField()),
                ('issued_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='app_check_tokens',
                    to='core.project',
                )),
            ],
            options={
                'ordering': ['-issued_at'],
            },
        ),
        migrations.AddIndex(
            model_name='appchecktoken',
            index=models.Index(fields=['project', 'token_hash'], name='app_check_tok_proj_hash_idx'),
        ),
        migrations.AddIndex(
            model_name='appchecktoken',
            index=models.Index(fields=['expires_at'], name='app_check_tok_expires_idx'),
        ),
        migrations.CreateModel(
            name='DebugToken',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('token', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('name', models.CharField(default='Debug Token', max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='debug_tokens',
                    to='core.project',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
