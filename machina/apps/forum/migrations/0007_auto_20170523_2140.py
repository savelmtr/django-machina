# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-05-24 02:40
from __future__ import unicode_literals

from django.db import migrations


def update_forum_last_post_on(apps, schema_editor):
    Forum = apps.get_model('forum', 'Forum')
    Topic = apps.get_model('forum_conversation', 'Topic')
    for forum in Forum.objects.all():
        topics = Topic.objects.filter(forum=forum, approved=True)
        forum.last_post_on = topics[0].last_post_on if topics.exists() else None
        forum.save()


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0006_auto_20170523_2036'),
    ]

    operations = [
        migrations.RunPython(update_forum_last_post_on, reverse_code=migrations.RunPython.noop),
    ]
