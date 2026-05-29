from django.core.management.base import BaseCommand

from forum.models import Board


class Command(BaseCommand):
    help = '创建论坛初始板块'

    def handle(self, *args, **options):
        boards = [
            {
                'name': '化工学习',
                'slug': 'chemical-study',
                'icon': '🧪',
                'description': '交流化工课程、实验、资料和学习问题。',
            },
            {
                'name': 'AI 工具',
                'slug': 'ai-tools',
                'icon': '🤖',
                'description': '分享 AI 工具使用经验、提示词和效率方法。',
            },
            {
                'name': '项目交流',
                'slug': 'project-exchange',
                'icon': '🚀',
                'description': '讨论项目想法、开发进度和实践问题。',
            },
        ]

        created_count = 0
        for board_data in boards:
            board, created = Board.objects.get_or_create(
                slug=board_data['slug'],
                defaults={
                    'name': board_data['name'],
                    'description': board_data['description'],
                    'icon': board_data['icon'],
                },
            )
            if created:
                created_count += 1
            else:
                board.name = board_data['name']
                board.description = board_data['description']
                board.icon = board_data['icon']
                board.save(update_fields=['name', 'description', 'icon'])

        self.stdout.write(self.style.SUCCESS(f'初始板块处理完成，新建 {created_count} 个板块。'))
