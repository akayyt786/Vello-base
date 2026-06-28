"""Initial migration for push notifications app."""

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
        # 1. DeviceToken                                                       #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='DeviceToken',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('platform', models.CharField(
                    choices=[
                        ('fcm', 'FCM (Firebase Cloud Messaging)'),
                        ('apns', 'APNs (Apple Push Notification service)'),
                        ('web', 'Web Push'),
                    ],
                    db_index=True,
                    max_length=10,
                )),
                ('token', models.TextField(
                    help_text='FCM registration token, APNs device token, or Web Push subscription JSON',
                )),
                ('app_id', models.CharField(
                    blank=True,
                    help_text='Application identifier (bundle ID for APNs, sender ID for FCM)',
                    max_length=100,
                )),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='device_tokens',
                    to='core.project',
                )),
                ('user', models.ForeignKey(
                    blank=True,
                    help_text='Optional: associate this token with an authenticated user',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='device_tokens',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'push_device_token',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='devicetoken',
            unique_together={('project', 'platform', 'token')},
        ),
        migrations.AddIndex(
            model_name='devicetoken',
            index=models.Index(
                fields=['project', 'platform', 'is_active'],
                name='push_devtok_proj_platform_active_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='devicetoken',
            index=models.Index(
                fields=['project', 'user'],
                name='push_devtok_proj_user_idx',
            ),
        ),

        # ------------------------------------------------------------------ #
        # 2. Topic                                                             #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=100)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='push_topics',
                    to='core.project',
                )),
            ],
            options={
                'db_table': 'push_topic',
                'ordering': ['name'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='topic',
            unique_together={('project', 'name')},
        ),
        migrations.AddIndex(
            model_name='topic',
            index=models.Index(
                fields=['project', 'name'],
                name='push_topic_proj_name_idx',
            ),
        ),

        # ------------------------------------------------------------------ #
        # 3. TopicSubscription (depends on DeviceToken + Topic)               #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='TopicSubscription',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('device_token', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subscriptions',
                    to='push.devicetoken',
                )),
                ('topic', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subscriptions',
                    to='push.topic',
                )),
            ],
            options={
                'db_table': 'push_topic_subscription',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='topicsubscription',
            unique_together={('topic', 'device_token')},
        ),
        migrations.AddIndex(
            model_name='topicsubscription',
            index=models.Index(
                fields=['topic', 'device_token'],
                name='push_topicsub_topic_token_idx',
            ),
        ),

        # ------------------------------------------------------------------ #
        # 4. PushNotification (depends on DeviceToken + Topic)                #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='PushNotification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('data', models.JSONField(
                    blank=True,
                    default=dict,
                    help_text='Arbitrary key-value payload attached to the notification',
                )),
                ('image_url', models.URLField(
                    blank=True,
                    help_text='Optional image shown in the notification',
                )),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('queued', 'Queued'),
                        ('delivered', 'Delivered'),
                        ('failed', 'Failed'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20,
                )),
                ('error', models.TextField(blank=True)),
                ('delivered_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='push_notifications',
                    to='core.project',
                )),
                ('device_token', models.ForeignKey(
                    blank=True,
                    help_text='Send to a specific device token',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='notifications',
                    to='push.devicetoken',
                )),
                ('topic', models.ForeignKey(
                    blank=True,
                    help_text='Send to all subscribers of this topic',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='notifications',
                    to='push.topic',
                )),
            ],
            options={
                'db_table': 'push_notification',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='pushnotification',
            index=models.Index(
                fields=['project', 'status'],
                name='push_notif_proj_status_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='pushnotification',
            index=models.Index(
                fields=['project', 'created_at'],
                name='push_notif_proj_created_idx',
            ),
        ),

        # ------------------------------------------------------------------ #
        # 5. NotificationCampaign (depends on Topic)                          #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name='NotificationCampaign',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(
                    help_text='Internal campaign name',
                    max_length=255,
                )),
                ('title', models.CharField(
                    help_text='Notification title shown to users',
                    max_length=255,
                )),
                ('body', models.TextField(help_text='Notification body shown to users')),
                ('data', models.JSONField(
                    blank=True,
                    default=dict,
                    help_text='Arbitrary key-value payload attached to each notification',
                )),
                ('image_url', models.URLField(blank=True)),
                ('target_platforms', models.JSONField(
                    default=list,
                    help_text='List of platforms to target, e.g. ["fcm", "apns", "web"]. Empty means all.',
                )),
                ('status', models.CharField(
                    choices=[
                        ('draft', 'Draft'),
                        ('scheduled', 'Scheduled'),
                        ('sending', 'Sending'),
                        ('sent', 'Sent'),
                    ],
                    db_index=True,
                    default='draft',
                    max_length=20,
                )),
                ('scheduled_at', models.DateTimeField(
                    blank=True,
                    help_text='When to send (future scheduling)',
                    null=True,
                )),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('total_sent', models.IntegerField(default=0)),
                ('total_failed', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notification_campaigns',
                    to='core.project',
                )),
                ('topic', models.ForeignKey(
                    blank=True,
                    help_text='If set, send only to subscribers of this topic',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='campaigns',
                    to='push.topic',
                )),
            ],
            options={
                'db_table': 'push_campaign',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notificationcampaign',
            index=models.Index(
                fields=['project', 'status'],
                name='push_campaign_proj_status_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='notificationcampaign',
            index=models.Index(
                fields=['project', 'scheduled_at'],
                name='push_campaign_proj_sched_idx',
            ),
        ),
    ]
