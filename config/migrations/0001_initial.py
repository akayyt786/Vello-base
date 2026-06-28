"""Initial migration for Remote Config + A/B Testing app."""

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
        # ------------------------------------------------------------------ #
        # 1. RemoteConfig                                                      #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='RemoteConfig',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False,
                )),
                ('key', models.CharField(db_index=True, max_length=255)),
                ('value_type', models.CharField(
                    choices=[
                        ('string', 'String'),
                        ('number', 'Number'),
                        ('boolean', 'Boolean'),
                        ('json', 'JSON'),
                    ],
                    default='string',
                    max_length=16,
                )),
                ('default_value', models.TextField(blank=True)),
                ('description', models.CharField(blank=True, max_length=500)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='remote_configs',
                    to='core.project',
                )),
            ],
            options={
                'db_table': 'remoteconfig_parameter',
                'ordering': ['key'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='remoteconfig',
            unique_together={('project', 'key')},
        ),

        # ------------------------------------------------------------------ #
        # 2. ConfigCondition (depends on RemoteConfig)                        #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='ConfigCondition',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False,
                )),
                ('name', models.CharField(max_length=255)),
                ('condition_type', models.CharField(
                    choices=[
                        ('user_property', 'User Property'),
                        ('platform', 'Platform'),
                        ('app_version', 'App Version'),
                        ('percentage', 'Percentage'),
                        ('always', 'Always'),
                    ],
                    default='always',
                    max_length=32,
                )),
                ('condition_params', models.JSONField(
                    default=dict,
                    help_text=(
                        'Condition parameters, e.g. '
                        '{"property_name": "plan", "property_value": "pro"}'
                    ),
                )),
                ('value', models.TextField()),
                ('priority', models.IntegerField(
                    default=0,
                    help_text='Higher value = evaluated first',
                )),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('config', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='conditions',
                    to='remoteconfig.remoteconfig',
                )),
            ],
            options={
                'db_table': 'remoteconfig_condition',
                'ordering': ['-priority', 'created_at'],
            },
        ),

        # ------------------------------------------------------------------ #
        # 3. ConfigVersion (depends on Project + User)                        #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='ConfigVersion',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False,
                )),
                ('version_number', models.PositiveIntegerField()),
                ('params', models.JSONField(
                    help_text='Full snapshot of all config parameters at publish time: {key: value}',
                )),
                ('description', models.CharField(blank=True, max_length=500)),
                ('published_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='config_versions',
                    to='core.project',
                )),
                ('published_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='published_config_versions',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'remoteconfig_version',
                'ordering': ['-version_number'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='configversion',
            unique_together={('project', 'version_number')},
        ),

        # ------------------------------------------------------------------ #
        # 4. Experiment                                                        #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='Experiment',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False,
                )),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[
                        ('draft', 'Draft'),
                        ('running', 'Running'),
                        ('paused', 'Paused'),
                        ('completed', 'Completed'),
                    ],
                    db_index=True,
                    default='draft',
                    max_length=16,
                )),
                ('start_date', models.DateTimeField(blank=True, null=True)),
                ('end_date', models.DateTimeField(blank=True, null=True)),
                ('traffic_fraction', models.FloatField(
                    default=1.0,
                    help_text='Proportion of users enrolled in this experiment (0.0–1.0)',
                )),
                ('metric_event', models.CharField(
                    blank=True,
                    help_text='Conversion event to optimize for (e.g. "purchase", "signup")',
                    max_length=255,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='experiments',
                    to='core.project',
                )),
            ],
            options={
                'db_table': 'remoteconfig_experiment',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='experiment',
            unique_together={('project', 'name')},
        ),

        # ------------------------------------------------------------------ #
        # 5. ExperimentVariant (depends on Experiment)                        #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='ExperimentVariant',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False,
                )),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('is_control', models.BooleanField(
                    default=False,
                    help_text='Marks this as the control/baseline variant',
                )),
                ('traffic_weight', models.FloatField(
                    default=1.0,
                    help_text='Relative weight vs other variants — used for proportional assignment',
                )),
                ('config_overrides', models.JSONField(
                    default=dict,
                    help_text='Config key-value overrides applied when user is in this variant',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('experiment', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='variants',
                    to='remoteconfig.experiment',
                )),
            ],
            options={
                'db_table': 'remoteconfig_experiment_variant',
                'ordering': ['created_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='experimentvariant',
            unique_together={('experiment', 'name')},
        ),
    ]
