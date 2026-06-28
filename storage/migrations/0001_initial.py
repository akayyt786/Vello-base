"""Initial migration for storage app."""

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
            name='StorageFile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('bucket', models.CharField(db_index=True, max_length=255)),
                ('path', models.TextField(db_index=True)),
                ('original_name', models.CharField(max_length=512)),
                ('content_type', models.CharField(default='application/octet-stream', max_length=255)),
                ('size', models.BigIntegerField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending upload'),
                        ('confirmed', 'Upload confirmed'),
                        ('processing', 'Processing'),
                        ('ready', 'Ready'),
                        ('error', 'Error'),
                    ],
                    db_index=True, default='pending', max_length=20,
                )),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('thumbnails', models.JSONField(blank=True, default=dict)),
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
                'db_table': 'storage_file',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='storagefile',
            constraint=models.UniqueConstraint(
                fields=['project', 'path'],
                name='unique_storage_file_per_project',
            ),
        ),
        migrations.AddIndex(
            model_name='storagefile',
            index=models.Index(fields=['project', 'status'], name='storage_file_project_status_idx'),
        ),
        migrations.AddIndex(
            model_name='storagefile',
            index=models.Index(fields=['project', 'content_type'], name='storage_file_project_ct_idx'),
        ),
    ]
