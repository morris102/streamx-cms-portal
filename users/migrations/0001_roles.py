from django.db import migrations

ROLE_NAMES = ("Admin", "Editor", "Author")


def create_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ROLE_NAMES:
        Group.objects.get_or_create(name=name)


def remove_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("auth", "User")
    for name in ROLE_NAMES:
        if not User.objects.filter(groups__name=name).exists():
            Group.objects.filter(name=name).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_roles, remove_roles),
    ]
