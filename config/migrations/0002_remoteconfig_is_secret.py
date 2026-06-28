"""Add is_secret field to RemoteConfig to support masking sensitive config values."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('remoteconfig', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='remoteconfig',
            name='is_secret',
            field=models.BooleanField(
                default=False,
                help_text='If True, default_value is treated as a secret and masked in list responses.',
            ),
        ),
    ]
