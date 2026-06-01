from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


ROLE_PERMISSIONS = {
    '论坛管理员': {
        'board': {'view', 'add', 'change', 'delete'},
        'post': {'view', 'add', 'change', 'delete'},
        'reply': {'view', 'add', 'change', 'delete'},
        'report': {'view', 'change', 'delete'},
        'attachment': {'view', 'delete'},
        'userprofile': {'view', 'change'},
        'boardmoderator': {'view', 'add', 'change', 'delete'},
        'linkpreview': {'view', 'delete'},
    },
    '论坛版主': {
        'board': {'view'},
        'post': {'view', 'change', 'delete'},
        'reply': {'view', 'change', 'delete'},
        'report': {'view', 'change'},
        'attachment': {'view', 'delete'},
        'userprofile': {'view'},
    },
}


class Command(BaseCommand):
    help = '创建论坛后台角色，并可选地为用户授予论坛管理员或论坛版主权限'

    def add_arguments(self, parser):
        parser.add_argument('--administrator', metavar='USERNAME')
        parser.add_argument('--moderator', metavar='USERNAME')

    def handle(self, *args, **options):
        groups = {}
        for role_name, model_permissions in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            permissions = []
            for model, actions in model_permissions.items():
                for action in actions:
                    codename = f'{action}_{model}'
                    try:
                        permission = Permission.objects.get(
                            content_type__app_label='forum',
                            codename=codename,
                        )
                    except Permission.DoesNotExist as exc:
                        raise CommandError(f'找不到权限：forum.{codename}') from exc
                    permissions.append(permission)
            group.permissions.set(permissions)
            groups[role_name] = group
            self.stdout.write(self.style.SUCCESS(f'已配置角色：{role_name}'))

        assignments = [
            ('论坛管理员', options['administrator']),
            ('论坛版主', options['moderator']),
        ]
        user_model = get_user_model()
        for role_name, username in assignments:
            if not username:
                continue
            try:
                user = user_model.objects.get(username=username)
            except user_model.DoesNotExist as exc:
                raise CommandError(f'找不到用户：{username}') from exc
            user.groups.add(groups[role_name])
            if not user.is_staff:
                user.is_staff = True
                user.save(update_fields=['is_staff'])
            self.stdout.write(self.style.SUCCESS(f'已将 {username} 设置为{role_name}'))

        self.stdout.write(
            self.style.WARNING(
                '站长请继续使用超级管理员账号。角色不会获得修改用户密码或查看私信的权限。'
            )
        )
