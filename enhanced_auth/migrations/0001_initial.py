# Generated migration for enhanced_auth initial models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PhoneVerification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('phone_number', models.CharField(max_length=20)),
                ('otp_code', models.CharField(max_length=6)),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('verified', 'Verified'), ('expired', 'Expired')],
                    default='pending',
                    max_length=10,
                )),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='phone_verifications',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MFADevice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('method', models.CharField(
                    choices=[('totp', 'TOTP (Authenticator App)'), ('sms', 'SMS')],
                    max_length=10,
                )),
                ('name', models.CharField(default='My Device', max_length=100)),
                ('totp_secret', models.CharField(blank=True, max_length=64)),
                ('phone_number', models.CharField(blank=True, max_length=20)),
                ('is_active', models.BooleanField(default=False)),
                ('confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='mfa_devices',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MFASMSCode',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=6)),
                ('expires_at', models.DateTimeField()),
                ('is_used', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('device', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sms_codes',
                    to='enhanced_auth.mfadevice',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MagicLink',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('token', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('redirect_url', models.URLField(blank=True)),
                ('is_used', models.BooleanField(default=False)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='magic_links',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CustomToken',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('uid', models.CharField(max_length=255)),
                ('claims', models.JSONField(default=dict)),
                ('token_hash', models.CharField(max_length=64, unique=True)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='custom_tokens',
                    to='core.project',
                )),
                ('issued_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='issued_custom_tokens',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='phoneverification',
            index=models.Index(fields=['phone_number', 'status'], name='eauth_phone_number_status_idx'),
        ),
        migrations.AddIndex(
            model_name='customtoken',
            index=models.Index(fields=['project', 'uid'], name='eauth_customtoken_project_uid_idx'),
        ),
    ]
