# Generated migration for Document model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('collection', models.CharField(db_index=True, max_length=255)),
                ('data', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    blank=True,
                    help_text='User who created this row',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL
                )),
                ('owner', models.ForeignKey(
                    blank=True,
                    help_text='Document owner for rule evaluation',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='owned_documents',
                    to=settings.AUTH_USER_MODEL
                )),
                ('project', models.ForeignKey(
                    db_index=True,
                    help_text='Multi-tenant isolation: every row belongs to a project',
                    on_delete=django.db.models.deletion.CASCADE,
                    to='core.project'
                )),
                ('updated_by', models.ForeignKey(
                    blank=True,
                    help_text='User who last updated this row',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'db_table': 'core_document',
            },
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['project', 'collection'], name='core_docume_project_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['project', 'collection', 'created_at'], name='core_docume_created_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['owner', 'collection'], name='core_docume_owner_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['created_by', 'collection'], name='core_docume_created_by_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='document',
            unique_together={('project', 'collection', 'id')},
        ),
    ]
