"""
Initial migration for data app: Collection and Document models.
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.contrib.postgres.indexes
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_initial'),
    ]

    operations = [
        # Collection model
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('path', models.TextField(db_index=True, unique=True)),
                ('schema', models.JSONField(blank=True, default=dict, help_text='Optional schema metadata: field types, indexes, validation rules')),
                ('document_count', models.IntegerField(default=0, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, help_text='User who created this row', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(db_index=True, help_text='Multi-tenant isolation: every row belongs to a project', on_delete=django.db.models.deletion.CASCADE, to='core.project')),
                ('updated_by', models.ForeignKey(blank=True, help_text='User who last updated this row', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'data_collection',
                'ordering': ['path'],
            },
        ),

        # Document model
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('collection_path', models.TextField(db_index=True)),
                ('doc_id', models.TextField()),
                ('data', models.JSONField(default=dict)),
                ('version', models.IntegerField(default=0, db_column='version')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('created_by', models.ForeignKey(blank=True, help_text='User who created this row', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(db_index=True, help_text='Multi-tenant isolation: every row belongs to a project', on_delete=django.db.models.deletion.CASCADE, to='core.project')),
                ('updated_by', models.ForeignKey(blank=True, help_text='User who last updated this row', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'data_document',
                'ordering': ['-updated_at'],
            },
        ),

        # Add unique constraint
        migrations.AddConstraint(
            model_name='collection',
            constraint=models.UniqueConstraint(fields=['project', 'path'], name='unique_collection_per_project'),
        ),

        migrations.AddConstraint(
            model_name='document',
            constraint=models.UniqueConstraint(fields=['project', 'collection_path', 'doc_id'], name='unique_document_per_collection'),
        ),

        # Add indexes
        migrations.AddIndex(
            model_name='collection',
            index=models.Index(fields=['project', 'name'], name='data_collection_project_name_idx'),
        ),

        migrations.AddIndex(
            model_name='collection',
            index=models.Index(fields=['project', 'created_at'], name='data_collection_project_created_idx'),
        ),

        # GIN index for JSONB queries
        migrations.AddIndex(
            model_name='document',
            index=django.contrib.postgres.indexes.GinIndex(fields=['data'], name='document_data_gin'),
        ),

        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['project', 'collection_path', 'created_at'], name='data_doc_project_collection_created_idx'),
        ),

        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['project', 'collection_path', 'updated_at'], name='data_doc_project_collection_updated_idx'),
        ),
    ]
