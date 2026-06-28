"""Add choices constraint to NetworkRequest.http_method."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crashlytics', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='networkrequest',
            name='http_method',
            field=models.CharField(
                choices=[
                    ('GET', 'GET'),
                    ('POST', 'POST'),
                    ('PUT', 'PUT'),
                    ('PATCH', 'PATCH'),
                    ('DELETE', 'DELETE'),
                    ('HEAD', 'HEAD'),
                    ('OPTIONS', 'OPTIONS'),
                ],
                max_length=8,
            ),
        ),
    ]
