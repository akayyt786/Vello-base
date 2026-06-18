# Generated migration for initial models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('slug', models.SlugField(db_index=True, max_length=255, unique=True)),
                ('description', models.TextField(blank=True)),
                ('api_key', models.CharField(db_index=True, editable=False, max_length=255, unique=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_projects', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'core_project',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProjectMembership',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('role', models.CharField(choices=[('owner', 'Owner'), ('editor', 'Editor'), ('viewer', 'Viewer')], default='viewer', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='core.project')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'core_project_membership',
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sign_in_provider', models.CharField(choices=[('password', 'Email/Password'), ('google', 'Google'), ('github', 'GitHub'), ('anonymous', 'Anonymous')], db_index=True, default='password', max_length=50)),
                ('email_verified', models.BooleanField(default=False)),
                ('email_verified_at', models.DateTimeField(blank=True, null=True)),
                ('phone_number', models.CharField(blank=True, db_index=True, max_length=20)),
                ('phone_verified', models.BooleanField(default=False)),
                ('avatar_url', models.URLField(blank=True)),
                ('bio', models.TextField(blank=True)),
                ('custom_claims', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'core_user_profile',
            },
        ),
        migrations.CreateModel(
            name='RefreshTokenBlacklist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jti', models.TextField(db_index=True, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(help_text='Token expiration time; after this, the entry can be pruned from the database')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blacklisted_tokens', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'core_refresh_token_blacklist',
            },
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['owner', 'is_active'], name='core_project_owner_is_active_idx'),
        ),
        migrations.AddIndex(
            model_name='projectmembership',
            index=models.Index(fields=['project', 'role'], name='core_project_project_role_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='projectmembership',
            unique_together={('project', 'user')},
        ),
        migrations.AddIndex(
            model_name='refreshtokenblacklist',
            index=models.Index(fields=['jti'], name='core_refresh_jti_idx'),
        ),
        migrations.AddIndex(
            model_name='refreshtokenblacklist',
            index=models.Index(fields=['user', 'created_at'], name='core_refresh_user_created_idx'),
        ),
    ]
